"""DebateAI desktop launcher: embedded Postgres + uvicorn + tray icon."""

import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from debateai_identity import INSTANCE_HEADER, canonical_updater


def _guarantee_standard_streams() -> None:
    """Give the windowed build real stdout/stderr objects.

    A PyInstaller bundle built with console=False has no console, so Python
    sets sys.stdout and sys.stderr to None. Any library that writes to them
    then raises AttributeError on None.write, and not every library unwinds
    cleanly when it does: tqdm's clear() and refresh() take its process-global
    write lock, touch the stream, and release only on the next line, so the
    exception escapes with that lock held forever and the next progress bar
    anywhere in the process deadlocks. That is what froze session creation in
    v0.6.1 (ALP-373), because a PII Shield model download sat in front of it.

    Discarding the writes is right for a GUI app: real diagnostics go to
    debateai.log through logging, which has its own file handler.

    Deliberately a copy of app.services.std_streams.ensure rather than an
    import of it: this has to run before the first backend import, and a
    launcher's safety net cannot depend on the thing it is protecting. The
    backend calls its own copy too, so every entry point is covered.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8", errors="replace"))
        # __stdout__/__stderr__ stay None otherwise, and libraries fall back to them.
        if getattr(sys, f"__{name}__", None) is None:
            setattr(sys, f"__{name}__", getattr(sys, name))


_guarantee_standard_streams()

# Dev checkout: make `app` (backend) importable. In the PyInstaller bundle
# the backend package is baked in and this directory does not exist.
_REPO_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if _REPO_BACKEND.exists():
    sys.path.insert(0, str(_REPO_BACKEND))

from debateai_desktop.paths import app_data_dir, free_port, resource
from debateai_desktop.gemini_web_bridge import GeminiWebBridge
from debateai_desktop.gemini_web_login import run_gemini_web_login
from debateai_desktop.chatgpt_web_login import run_chatgpt_web_login
from debateai_desktop.pg import EmbeddedPostgres
from debateai_desktop.lifecycle_ui import LifecycleSplash
from debateai_desktop.ollama_lifecycle import ManagedOllama
from debateai_desktop.subscription_bridge import SubscriptionBridge
from debateai_desktop.windows_console import (
    ConsoleWindowSuppressor,
    install_hidden_subprocess_policy,
    visible_popen,
)
from updater import validate_plan


def _set_env(name: str, value: str) -> None:
    os.environ[name] = value


def _env_value(name: str, default: str = "") -> str:
    return os.environ.get(name) or default

install_hidden_subprocess_policy()

LOCK_NAME = "launcher.json"
STOP_NAME = "stop"
OPEN_WINDOW_REQUEST_NAME = "open-window.request"
LOOPBACK_HOST = "127.0.0.1"
BROWSER_HOST = "localhost"
DEFAULT_APP_PORT = 8474
PRODUCT_DISPLAY_NAME = "Debate AI"
_PERSISTED_PROVIDER_ENVIRONMENT = (
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK",
    "SUBSCRIPTION_BRIDGE_FALLBACK_MODEL",
)
UPDATER_NAMES = {
    "win32": canonical_updater("win32"),
    "darwin": canonical_updater("darwin"),
    "linux": canonical_updater("linux"),
}
_embedded_windows: dict[str, subprocess.Popen] = {}
_embedded_windows_lock = threading.Lock()


def _acquire_instance_guard(data_dir: Path):
    """Own the launcher startup/lifetime or return None without touching services."""
    if sys.platform == "win32":
        identity = str(Path(data_dir).resolve()).casefold().encode("utf-8")
        name = "Local\\DebateAILauncher-" + hashlib.sha256(identity).hexdigest()[:24]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_bool
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise OSError(ctypes.get_last_error(), "CreateMutexW failed")
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return None
        return ("win32", kernel32, handle)

    guard_path = Path(data_dir) / "launcher.guard"
    guard_path.touch(exist_ok=True)
    handle = guard_path.open("r+b")
    if guard_path.stat().st_size == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return ("file", handle)


def _release_instance_guard(handle) -> None:
    if handle is None:
        return
    kind = handle[0]
    if kind == "win32":
        _kind, kernel32, native_handle = handle
        kernel32.CloseHandle(native_handle)
        return
    _kind, file_handle = handle
    if file_handle.closed:
        return
    try:
        import fcntl

        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
    finally:
        file_handle.close()


def app_url(port: int) -> str:
    return f"http://{BROWSER_HOST}:{port}"


def desktop_app_url(port: int, view: str | None = None) -> str:
    query = "desktop=1"
    if view:
        query += f"&view={view}"
    return f"{app_url(port)}/?{query}"


def health_url(port: int) -> str:
    return f"http://{LOOPBACK_HOST}:{port}/api/health"


def readiness_url(port: int) -> str:
    return f"http://{LOOPBACK_HOST}:{port}/api/ready"


def install_root() -> Path:
    executable = Path(sys.executable).resolve()
    return executable.parents[2] if sys.platform == "darwin" else executable.parent


def updater_path(root: Path) -> Path:
    platform_key = "linux" if sys.platform.startswith("linux") else sys.platform
    canonical = root / UPDATER_NAMES[platform_key]
    if canonical.exists():
        return canonical
    return canonical


def bind_app_socket() -> socket.socket:
    listener = socket.socket()
    try:
        listener.bind((LOOPBACK_HOST, DEFAULT_APP_PORT))
    except OSError:
        listener.close()
        listener = socket.socket()
        listener.bind((LOOPBACK_HOST, 0))
    return listener


def _embedded_webview_command(
    url: str,
    title: str,
    width: int,
    height: int,
    on_top: bool,
) -> list[str]:
    base = [sys.executable]
    if not getattr(sys, "frozen", False):
        base.append(str(Path(__file__).resolve()))
    return [
        *base,
        "--embedded-webview",
        url,
        title,
        str(width),
        str(height),
        "1" if on_top else "0",
    ]


def _is_restorable_process_window(
    *,
    owner_pid: int,
    process_id: int,
    visible: bool,
    title_length: int,
    title: str = "",
    class_name: str = "",
) -> bool:
    """Accept the real WebView host even while it is hidden in the tray."""
    del visible
    if owner_pid != process_id or title_length <= 0:
        return False
    identity = f"{title}\n{class_name}".casefold()
    if any(
        marker in identity
        for marker in (
            ".net-broadcasteventwindow",
            "gdi+ hook window",
            "gdi+ window",
            "msctfime ui",
            "default ime",
        )
    ):
        return False
    # Both native surfaces created by this launcher have stable explicit
    # titles. A non-empty framework/helper title must never win merely because
    # it happened to be enumerated before the real WebView form.
    return not title or title.startswith("Debate AI")


def _focus_process_window(process_id: int, *, hidden_only: bool = False) -> bool:
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )
    enum_windows = user32.EnumWindows
    # pywebview configures this shared ctypes function with its own callback
    # prototype. Rebind it before passing our callback so a prior WebView
    # import cannot make the otherwise valid function pointer fail at runtime.
    enum_windows.argtypes = [callback_type, wintypes.LPARAM]
    enum_windows.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [
        wintypes.HWND,
        wintypes.LPWSTR,
        ctypes.c_int,
    ]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [
        wintypes.HWND,
        wintypes.LPWSTR,
        ctypes.c_int,
    ]
    user32.GetClassNameW.restype = ctypes.c_int
    found = False

    @callback_type
    def activate(hwnd, _lparam):
        nonlocal found
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        title_length = user32.GetWindowTextLengthW(hwnd)
        title_buffer = ctypes.create_unicode_buffer(max(1, title_length + 1))
        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
        user32.GetClassNameW(hwnd, class_buffer, len(class_buffer))
        if _is_restorable_process_window(
            owner_pid=owner.value,
            process_id=process_id,
            visible=bool(user32.IsWindowVisible(hwnd)),
            title_length=title_length,
            title=title_buffer.value,
            class_name=class_buffer.value,
        ):
            if hidden_only and bool(user32.IsWindowVisible(hwnd)):
                return True
            found = True
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return False
        if (
            owner.value == process_id
            and bool(user32.IsWindowVisible(hwnd))
            and ".net-broadcasteventwindow" in (
                f"{title_buffer.value}\n{class_buffer.value}".casefold()
            )
        ):
            # Older builds could accidentally restore this WinForms framework
            # window while waiting for the real form. Hide it opportunistically
            # so a subsequent open also repairs the bad state in-process.
            user32.ShowWindow(hwnd, 0)  # SW_HIDE
        return True

    enum_windows(activate, 0)
    return found


def _restore_hidden_embedded_windows() -> None:
    """Repair a live WebView form that Windows hid without closing it.

    A minimized form remains visible according to IsWindowVisible, so this
    does not undo an intentional minimize. Closing the form ends its UI child,
    so it also stays closed in the tray until the next explicit Open request.
    """
    if sys.platform != "win32":
        return
    with _embedded_windows_lock:
        processes = list(_embedded_windows.values())
    for process in processes:
        if process.poll() is None:
            _focus_process_window(process.pid, hidden_only=True)


def _wait_for_process_window(process: subprocess.Popen, timeout: float = 3.0) -> bool:
    """Wait briefly for a packaged WebView child to expose a real window."""
    if sys.platform != "win32":
        # Other platforms do not expose a portable native-window lookup here,
        # but an already-exited child is never a successfully opened window.
        return process.poll() is None
    deadline = time.monotonic() + max(0.0, timeout)
    while process.poll() is None and time.monotonic() < deadline:
        if _focus_process_window(process.pid):
            return True
        time.sleep(0.05)
    return process.poll() is None and _focus_process_window(process.pid)


def _open_system_browser(url: str) -> bool:
    """Open a visible fallback when the embedded WebView cannot create a window."""
    try:
        if sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        return bool(webbrowser.open(url, new=1))
    except OSError:
        logging.getLogger("launcher").exception("system browser fallback failed")
        return False


def _request_owner_window(data_dir: Path) -> bool:
    """Ask the long-lived launcher to own the replacement WebView process."""
    request = Path(data_dir) / OPEN_WINDOW_REQUEST_NAME
    temporary = request.with_name(request.name + ".new")
    try:
        request.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(str(time.time_ns()), encoding="ascii")
        os.replace(temporary, request)
        return True
    except OSError:
        logging.getLogger("launcher").exception("desktop window request failed")
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _claim_owner_window_request(data_dir: Path) -> bool:
    request = Path(data_dir) / OPEN_WINDOW_REQUEST_NAME
    try:
        request.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        logging.getLogger("launcher").exception("desktop window request could not be claimed")
        return False


def open_desktop_window(
    url: str,
    *,
    title: str = "Debate AI",
    width: int = 1280,
    height: int = 820,
    on_top: bool = False,
    slot: str = "main",
) -> bool:
    """Open or focus an embedded WebView2 window owned by this installation."""
    with _embedded_windows_lock:
        process = _embedded_windows.get(slot)
        if process is not None and process.poll() is None:
            if sys.platform != "win32" or _focus_process_window(process.pid):
                return True
            try:
                process.terminate()
                process.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                pass
            _embedded_windows.pop(slot, None)
        try:
            process = visible_popen(
                _embedded_webview_command(url, title, width, height, on_top),
                cwd=str(install_root() if getattr(sys, "frozen", False) else Path(__file__).resolve().parent),
            )
        except OSError:
            logging.getLogger("launcher").exception("embedded desktop window failed to start")
            return False
        _embedded_windows[slot] = process
        if not _wait_for_process_window(process):
            logging.getLogger("launcher").warning(
                "embedded desktop child created no visible window; opening browser fallback"
            )
            _embedded_windows.pop(slot, None)
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            return _open_system_browser(url)
        return True


def _stop_embedded_windows() -> None:
    with _embedded_windows_lock:
        processes = list(_embedded_windows.values())
        _embedded_windows.clear()
    for process in processes:
        if process.poll() is not None:
            continue
        try:
            process.terminate()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass


def run_embedded_webview(
    url: str,
    title: str,
    width: int,
    height: int,
    on_top: bool,
) -> int:
    """Run the native pywebview GUI loop in a small child process."""
    try:
        import webview

        window = webview.create_window(
            title,
            url=url,
            width=width,
            height=height,
            min_size=(420, 560),
            on_top=on_top,
            background_color="#111318" if on_top else "#f7f8fa",
        )

        # Closing the form ends only this UI child. The long-lived launcher,
        # backend, PostgreSQL and tray stay alive; the tray owner creates a new
        # visible child on the next Open request. Keeping a closed form alive
        # via window.hide() left a healthy child process with no dependable
        # visible surface after WebView2 lifecycle events.
        webview.start(gui=_webview_gui(), debug=False)
        return 0
    except Exception:
        logging.getLogger("launcher").exception("embedded WebView2 failed")
        return 1


def _webview_gui() -> str:
    """Select the pywebview backend available on the current desktop OS."""
    if sys.platform == "win32":
        return "edgechromium"
    if sys.platform == "darwin":
        return "cocoa"
    return "gtk"


def open_debate_overlay(port: int) -> bool:
    """Open the compact live card in the native always-on-top WebView."""
    return open_desktop_window(
        f"{app_url(port)}/?overlay=1",
        title="Debate AI Overlay",
        width=500,
        height=720,
        on_top=True,
        slot="overlay",
    )


def instance_is_healthy(port: int, token: str) -> bool:
    def identified(response) -> bool:
        return (
            response.status == 200
            and response.headers.get(INSTANCE_HEADER) == token
        )

    try:
        req = urllib.request.urlopen(readiness_url(port), timeout=2)
        with req as resp:
            return identified(resp)
    except urllib.error.HTTPError as exc:
        # Releases before /api/ready still expose the authenticated liveness
        # endpoint. Only a genuine 404 gets this compatibility fallback; a
        # 503 from a new release means its database is unavailable.
        if exc.code != 404:
            return False
        try:
            req = urllib.request.urlopen(health_url(port), timeout=2)
            with req as resp:
                return identified(resp)
        except Exception:
            return False
    except Exception:
        return False


def existing_instance_port(data_dir: Path) -> int | None:
    """Port of a healthy already-running instance, else None."""
    lock = data_dir / LOCK_NAME
    if not lock.exists():
        return None
    try:
        instance = json.loads(lock.read_text())
        port = instance["port"]
        if instance_is_healthy(port, instance["token"]):
            return port
    except Exception:
        pass
    return None


def wait_for_other_instance(
    data_dir: Path, timeout: float = 60.0, interval: float = 2.0
) -> int | None:
    """Poll for another instance to publish a healthy port, else None."""
    deadline = time.monotonic() + timeout
    while True:
        port = existing_instance_port(data_dir)
        if port is not None:
            return port
        if time.monotonic() >= deadline:
            return None
        time.sleep(interval)


def wait_healthy(
    port: int, timeout: float = 90.0, token: str | None = None
) -> bool:
    if token is None:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if instance_is_healthy(port, token):
            return True
        time.sleep(0.5)
    return False


def _wait_for_stop_file(data_dir: Path) -> None:
    stop = data_dir / STOP_NAME
    stop.unlink(missing_ok=True)
    while not stop.exists():
        time.sleep(1)
    stop.unlink(missing_ok=True)


def _recover_postgres_once(pg: EmbeddedPostgres, port: int, log) -> bool:
    """Restart an unexpectedly stopped embedded database without a console."""
    if pg.is_running(port):
        return False
    log.warning("embedded postgres stopped unexpectedly; restarting on port %s", port)
    pg.recover_stale()
    pg.start(port)
    log.info("embedded postgres recovered on port %s", port)
    return True


def _prepare_postgres(pg: EmbeddedPostgres, preferred_port: int, log) -> int:
    """Start the embedded database or reclaim this app's orphaned instance."""
    pg.recover_stale()
    pg.ensure_initdb()
    running_port = pg.running_port()
    if running_port is not None:
        pg.adopt_running(running_port)
        pg.ensure_role(running_port)
        log.info("adopted existing embedded postgres on port %s", running_port)
        return running_port
    pg.start(preferred_port)
    pg.ensure_role(preferred_port)
    return preferred_port


def _watch_postgres(pg, port: int, stop: threading.Event, log) -> None:
    while not stop.wait(2.0):
        try:
            _recover_postgres_once(pg, port, log)
        except Exception:
            log.exception("embedded postgres recovery failed")


def _start_postgres_watchdog(pg, port: int, log):
    stop = threading.Event()
    thread = threading.Thread(
        target=_watch_postgres,
        args=(pg, port, stop, log),
        name="debateai-postgres-watchdog",
        daemon=True,
    )
    thread.start()
    return stop, thread


def _error_dialog(message: str) -> None:
    """Best-effort native error popup; falls back to stderr."""
    try:
        if sys.platform == "win32":
            ctypes.windll.user32.MessageBoxW(0, message, PRODUCT_DISPLAY_NAME, 0x10)
            return
        if sys.platform == "darwin":
            import subprocess

            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display alert "{PRODUCT_DISPLAY_NAME}" message "{message}"',
                ],
                check=False,
            )
            return
    except Exception:
        pass
    print(message, file=sys.stderr)


def _startup_retry_dialog(message: str) -> bool:
    """Offer one user-driven retry; never loop or delay on its own."""
    try:
        if sys.platform == "win32":
            # MB_RETRYCANCEL | MB_ICONERROR; IDRETRY == 4.
            return ctypes.windll.user32.MessageBoxW(
                0, message, "Debate AI", 0x5 | 0x10
            ) == 4
    except Exception:
        pass
    _error_dialog(message)
    return False


def _startup_failure(message: str, headless: bool) -> int:
    return 2 if not headless and _startup_retry_dialog(message) else 1


def _open_data_folder(data_dir: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(data_dir)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(["open", str(data_dir)], check=False)
        else:
            import subprocess

            subprocess.run(["xdg-open", str(data_dir)], check=False)
    except Exception:
        logging.getLogger("launcher").exception("failed to open data folder")


def _write_update_state(state_path: Path, value: dict) -> None:
    temporary = state_path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, state_path)


def _reset_stale_apply(data_dir: Path, marker: Path) -> None:
    marker.unlink(missing_ok=True)
    state_path = data_dir / "updates" / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(state, dict) and state.get("state") == "applying":
            state["state"] = "ready"
            state["error"] = ""
            _write_update_state(state_path, state)
    except Exception:
        pass


def _claim_update_marker(data_dir: Path) -> bool:
    marker = data_dir / "updates" / "apply.json"
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
        requested = datetime.strptime(
            value["requested_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - requested).total_seconds()
        if age < 0 or age >= 60:
            raise ValueError
        validate_plan(value, marker)
        return True
    except Exception:
        _reset_stale_apply(data_dir, marker)
        return False


def _watch_for_update(
    icon,
    data_dir: Path,
    port: int,
    requested: threading.Event,
    stopped: threading.Event,
) -> None:
    while not stopped.is_set():
        if _claim_owner_window_request(data_dir):
            open_desktop_window(desktop_app_url(port))
        _restore_hidden_embedded_windows()
        if _claim_update_marker(data_dir):
            requested.set()
            icon.stop()
            return
        stopped.wait(1)


def _update_status(port: int, token: str | None = None) -> dict:
    try:
        request = urllib.request.Request(
            f"http://{LOOPBACK_HOST}:{port}/api/updates",
            headers={INSTANCE_HEADER: token} if token else {},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            body = response.read(65_537)
        if response.status != 200 or len(body) > 65_536:
            return {}
        value = json.loads(body.decode("utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _update_menu_label(port: int, token: str | None = None) -> str:
    status = _update_status(port, token)
    if status.get("state") not in {
        "available",
        "authorizing",
        "downloading",
        "needs_authorization",
        "ready",
    }:
        return "Nach Updates suchen"
    version = status.get("available_version")
    notes = status.get("available_notes")
    if not isinstance(version, str) or not isinstance(notes, str):
        return "Nach Updates suchen"
    title = next((line.strip().lstrip("#").strip() for line in notes.splitlines() if line.strip()), "")
    return f"Update {version}: {title[:60]}" if title else f"Update {version}"


def _check_for_updates(port: int, token: str) -> None:
    try:
        request = urllib.request.Request(
            f"http://{LOOPBACK_HOST}:{port}/api/updates/check",
            data=b"",
            method="POST",
            headers={INSTANCE_HEADER: token},
        )
        with urllib.request.urlopen(request, timeout=5):
            pass
    except Exception:
        pass
    open_desktop_window(desktop_app_url(port, "about"))


def _launch_update_helper(data_dir: Path, helper_source: Path) -> Path:
    marker = (data_dir / "updates" / "apply.json").resolve(strict=True)
    value = json.loads(marker.read_text(encoding="utf-8"))
    plan = validate_plan(value, marker)
    source = helper_source.resolve(strict=True)
    if helper_source.is_symlink() or not source.is_file():
        raise RuntimeError("Update helper is unavailable.")
    destination = data_dir / "updates" / "bin" / plan.version / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)
    subprocess.Popen(
        [str(destination), str(marker)],
        cwd=str(destination.parent),
    )
    return destination


def _tray_image():
    from PIL import Image, ImageDraw

    icon_png = resource("assets") / "icon.png"
    try:
        with Image.open(icon_png) as brand:
            return brand.convert("RGBA")
    except Exception:
        logging.getLogger("launcher").exception(
            "brand icon unavailable at %s; using fallback", icon_png
        )
    image = Image.new("RGB", (64, 64), (30, 41, 59))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), fill=(56, 189, 248))
    return image


def _run_tray(
    port: int,
    data_dir: Path,
    instance_token: str | None = None,
    *,
    open_initial: bool = False,
) -> bool:
    import pystray

    image = _tray_image()
    requested = threading.Event()
    stopped = threading.Event()

    icon = pystray.Icon(
        "debateai",
        image,
        f"{PRODUCT_DISPLAY_NAME} - {BROWSER_HOST}:{port}",
        menu=pystray.Menu(
            pystray.MenuItem(
                "Debate AI öffnen",
                lambda _icon, _item: open_desktop_window(desktop_app_url(port)),
            ),
            pystray.MenuItem(
                "Kompaktes Overlay",
                lambda _icon, _item: open_debate_overlay(port),
            ),
            pystray.MenuItem(
                "Datenordner öffnen",
                lambda _icon, _item: _open_data_folder(data_dir),
            ),
            pystray.MenuItem(
                (
                    lambda _item: _update_menu_label(port, instance_token)
                    if instance_token
                    else "Nach Updates suchen"
                ),
                lambda _icon, _item: _check_for_updates(port, instance_token or ""),
            ),
            pystray.MenuItem("Beenden", lambda _icon, _item: icon.stop()),
        ),
    )
    watcher = threading.Thread(
        target=_watch_for_update,
        args=(icon, data_dir, port, requested, stopped),
        daemon=True,
    )
    watcher.start()
    try:
        if open_initial:
            # pystray invokes setup only after its native message loop is
            # initialized. Route the first open through the same owner watcher
            # as every later tray restore. Give the loop one short settle
            # interval: an immediate setup callback can still race the native
            # tray transition and leave the WebView form hidden.
            def request_initial_window(_icon) -> None:
                # A custom pystray setup replaces its default visibility step.
                _icon.visible = True
                if not stopped.wait(1.0):
                    _request_owner_window(data_dir)

            icon.run(setup=request_initial_window)
        else:
            icon.run()
    finally:
        stopped.set()
        watcher.join(timeout=2)
    return requested.is_set()


def _configure_update_environment(instance_token: str, headless: bool) -> None:
    root = install_root()
    packaged = bool(getattr(sys, "frozen", False))
    _set_env("DEBATEAI_DESKTOP", "1" if packaged else "0")
    _set_env("DEBATEAI_INSTANCE_TOKEN", instance_token)
    _set_env("DEBATEAI_INSTALL_DIR", str(root))
    _set_env(
        "DEBATEAI_UPDATE_KEYS",
        str(resource("release_signing_keys.json")),
    )
    _set_env("DEBATEAI_UPDATE_HELPER", str(updater_path(root)))
    _set_env(
        "DEBATEAI_UPDATE_APPLY_DISABLED",
        "1" if headless or not packaged else "0",
    )
    _set_env("DEBATEAI_BOUND_HOST", LOOPBACK_HOST)


def _windows_user_environment_value(name: str) -> str | None:
    """Read one non-secret provider setting from the current user's profile."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _kind = winreg.QueryValueEx(key, name)
        return str(value).strip() or None
    except (FileNotFoundError, OSError, ValueError):
        return None


def _hydrate_windows_provider_environment() -> None:
    """Repair stale Explorer inheritance after provider login configuration.

    A desktop shortcut inherits Explorer's old environment until Explorer is
    restarted. The approved settings already live in HKCU, so read only those
    explicit non-secret names and never override a value supplied to the app.
    """
    if sys.platform != "win32":
        return
    for name in _PERSISTED_PROVIDER_ENVIRONMENT:
        if name in os.environ:
            continue
        value = _windows_user_environment_value(name)
        if value:
            os.environ[name] = value


def _configure_gemini_web_login(data_dir: Path) -> None:
    """Expose a secret-free command that opens the dedicated login window."""
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable, str(Path(__file__).resolve())]
    result = Path(data_dir) / "gemini-web" / "login-result.json"
    _set_env("DEBATEAI_GEMINI_WEB_LOGIN_COMMAND", json.dumps(command))
    _set_env("DEBATEAI_GEMINI_WEB_LOGIN_RESULT", str(result))


def _chatgpt_oracle_runtime(data_dir: Path) -> Path:
    """Find an explicitly installed Oracle runtime before an optional bundle."""
    cli_relative = Path("node_modules") / "@steipete" / "oracle" / "dist" / "bin" / "oracle-cli.js"
    configured = _env_value("DEBATEAI_CHATGPT_WEB_RUNTIME").strip()
    optional = Path(data_dir) / "optional" / "chatgpt_oracle"
    candidates = ([Path(configured)] if configured else []) + [optional, resource("chatgpt_oracle")]
    for candidate in candidates:
        if candidate.joinpath(cli_relative).is_file():
            return candidate
    return optional


def _configure_chatgpt_web_login(data_dir: Path) -> None:
    """Configure the separate normal-ChatGPT browser provider."""
    runtime = _chatgpt_oracle_runtime(data_dir)
    bundled_node = runtime / "node" / "node.exe"
    if bundled_node.is_file():
        node = bundled_node
    else:
        candidate = shutil.which("node")
        node = Path(candidate) if candidate else bundled_node
    cli = runtime / "node_modules" / "@steipete" / "oracle" / "dist" / "bin" / "oracle-cli.js"
    web_dir = Path(data_dir) / "chatgpt-web"
    for canonical, value in (
        ("DEBATEAI_CHATGPT_WEB_NODE", str(node)),
        ("DEBATEAI_CHATGPT_WEB_ORACLE", str(cli)),
        ("DEBATEAI_CHATGPT_WEB_HOME", str(web_dir / "oracle-home")),
        ("DEBATEAI_CHATGPT_WEB_PROFILE", str(web_dir / "browser-profile")),
        ("DEBATEAI_CHATGPT_WEB_MARKER", str(web_dir / "verified.json")),
    ):
        _set_env(canonical, value)
    if not os.environ.get("CHROME_PATH", "").strip() and sys.platform == "win32":
        for browser in (
            Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ):
            if browser.is_file():
                os.environ["CHROME_PATH"] = str(browser)
                break
    command = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve())]
    _set_env("DEBATEAI_CHATGPT_WEB_LOGIN_COMMAND", json.dumps(command))
    _set_env("DEBATEAI_CHATGPT_WEB_LOGIN_RESULT", str(web_dir / "login-result.json"))


def _launch_requested_update(requested: bool, data_dir: Path, log) -> int:
    if not requested:
        return 0
    try:
        _launch_update_helper(
            data_dir, Path(_env_value("DEBATEAI_UPDATE_HELPER"))
        )
        return 0
    except Exception:
        log.exception("failed to start update helper")
        _error_dialog(
            f"Debate AI konnte das Update nicht starten. Protokoll: {data_dir / 'debateai.log'}"
        )
        return 1


def _cleanup_owned_runtime_files(data_dir: Path) -> None:
    """Remove only disposable files created by this desktop runtime."""
    files = (
        data_dir / "gemini-web" / "cookie.txt",
        data_dir / "gemini-web" / "cookie.txt.new",
        data_dir / "data" / "master.key.tmp",
        data_dir / "updates" / "state.tmp",
        data_dir / "updates" / "apply.tmp",
        data_dir / "chatgpt-web" / "login-result.json.new",
        data_dir / OPEN_WINDOW_REQUEST_NAME,
        data_dir / f"{OPEN_WINDOW_REQUEST_NAME}.new",
    )
    for path in files:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    shutil.rmtree(data_dir / "gemini-web" / ".cookies", ignore_errors=True)
    for pattern in (
        data_dir / "subscription-bridge",
        data_dir / "updates" / "bin",
    ):
        if pattern.is_dir():
            for path in pattern.rglob("*.new" if pattern.name == "subscription-bridge" else "*.tmp"):
                try:
                    path.unlink()
                except OSError:
                    pass


def _configure_launcher_logging(log_path: Path) -> Path | None:
    """Configure file logging without letting a restricted temp path abort startup."""
    candidates = [Path(log_path)]
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "DebateAI" / "debateai.log")
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.touch(exist_ok=True)
            candidate.chmod(0o600)
            logging.basicConfig(
                filename=str(candidate),
                level=logging.INFO,
                format="%(asctime)s %(name)s %(levelname)s %(message)s",
            )
            return candidate
        except OSError:
            continue
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    return None


def _run_owned(headless: bool = False) -> int:
    _hydrate_windows_provider_environment()
    data_dir = app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        data_dir.chmod(0o700)
    except OSError:
        pass
    _cleanup_owned_runtime_files(data_dir)
    oracle_jobs = data_dir / "chatgpt-web" / "oracle-home" / "jobs"
    if oracle_jobs.is_dir():
        for stale in oracle_jobs.glob("answer-*.md"):
            try:
                stale.unlink()
            except OSError:
                pass
    _configure_gemini_web_login(data_dir)
    _configure_chatgpt_web_login(data_dir)
    _configure_launcher_logging(data_dir / "debateai.log")
    log = logging.getLogger("launcher")

    port = existing_instance_port(data_dir)
    if port is not None:
        log.info("instance already running on port %s", port)
        if not headless:
            if not _request_owner_window(data_dir):
                _open_system_browser(desktop_app_url(port))
        return 0

    pg = EmbeddedPostgres(resource("pgsql"), data_dir)
    bridge = SubscriptionBridge(data_dir, log)
    gemini_web_bridge = GeminiWebBridge(data_dir, log)
    lifecycle = LifecycleSplash()
    if not headless:
        lifecycle.show_startup("Lokale Dienste werden vorbereitet ...")
    console_suppressor = ConsoleWindowSuppressor()
    console_suppressor.start()
    pg_port = free_port()
    pg_watch_stop = None
    pg_watch_thread = None
    foreign_postmaster = False
    try:
        if not headless:
            lifecycle.set_progress(8, "Lokale Datenbank wird vorbereitet ...")
        log.info("preparing postgres with preferred port %s", pg_port)
        if not headless:
            lifecycle.set_detail("Lokale Datenbank wird gestartet ...")
        pg_port = _prepare_postgres(pg, pg_port, log)
        pg_watch_stop, pg_watch_thread = _start_postgres_watchdog(
            pg, pg_port, log
        )
        if not headless:
            lifecycle.set_progress(25, "Lokale Datenbank ist bereit")
    except Exception:
        log.exception("postgres failed to start")
        # A remaining pidfile that we did not start or adopt may belong to
        # another launcher which has not published its healthy app port yet.
        foreign_postmaster = (
            (pg.pgdata / "postmaster.pid").exists()
            and pg.started_pid is None
        )
        if foreign_postmaster:
            log.warning(
                "postmaster.pid belongs to another instance; not stopping it"
            )
            other_port = wait_for_other_instance(data_dir)
            if other_port is not None:
                log.info("other instance is healthy on port %s", other_port)
                if not headless:
                    lifecycle.close()
                    if not _request_owner_window(data_dir):
                        _open_system_browser(desktop_app_url(other_port))
                console_suppressor.stop()
                return 0
            log.error("no other instance became healthy within timeout")
            if not headless:
                retry = _startup_failure(
                    "Debate AI wird möglicherweise bereits in einem anderen Fenster gestartet. "
                    f"Falls es nicht erscheint, prüfe das Protokoll: {data_dir / 'debateai.log'}",
                    headless,
                )
            console_suppressor.stop()
            lifecycle.close()
            return retry if not headless else 1
        try:
            pg.stop()
        except Exception:
            log.exception("cleanup stop failed")
        if not headless:
            retry = _startup_failure(
                f"Die lokale Datenbank konnte nicht gestartet werden. Protokoll: {pg.log}",
                headless,
            )
        console_suppressor.stop()
        lifecycle.close()
        return retry if not headless else 1

    ollama = ManagedOllama()
    if not headless:
        lifecycle.set_progress(30, "Lokales KI-Modell wird gestartet ...")
    ollama_status = ollama.start()
    log.info("local ollama lifecycle: %s", ollama_status)
    readiness = {"qwen": False, "subscription": False}
    warm_thread = None
    bridge_thread = None
    if not headless:
        lifecycle.set_progress(36, "Kernapp wird geoeffnet; Modelle laden im Hintergrund")

    listener = bind_app_socket()
    app_port = listener.getsockname()[1]
    instance_token = secrets.token_urlsafe()
    os.environ["DATABASE_URL"] = pg.database_url(pg_port)
    os.environ["DATA_DIR"] = str(data_dir / "data")
    if sys.platform == "win32":
        # Wrap the credentials master key with DPAPI so a copied AppData
        # folder cannot decrypt the stored provider keys (see
        # app.services.secrets). Only the same Windows user on this machine
        # can unwrap it; the file is upgraded in place on first read.
        os.environ.setdefault("CREDENTIALS_MASTER_KEY_PROTECTION", "dpapi")
    os.environ["FRONTEND_DIST"] = str(resource("frontend"))
    _configure_update_environment(instance_token, headless)
    ffmpeg = resource("ffmpeg") / (
        "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    )
    if ffmpeg.is_file():
        _set_env("DEBATEAI_FFMPEG", str(ffmpeg))

    # Export optional endpoint locations before backend import, but never wait
    # for these adapters before opening the core UI.
    try:
        bridge.prepare()
    except OSError:
        log.exception("optional subscription bridge preparation failed")
    if not gemini_web_bridge.start():
        log.warning("optional Gemini web bridge unavailable")

    # Import after env is set: app.config reads the environment at import.
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(
            "app.main:app",
            host=LOOPBACK_HOST,
            port=app_port,
            log_config=None,
            headers=[(INSTANCE_HEADER, instance_token)],
            ws_ping_timeout=90.0,
            ws_max_queue=2048,
            ws_max_size=65_536,
        )
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [listener]}, daemon=True
    )
    lock = data_dir / LOCK_NAME
    update_requested = False
    try:
        log.info("starting app on port %s", app_port)
        if not headless:
            lifecycle.set_progress(72, "Backend und Audiopipeline werden vorbereitet ...")
        thread.start()

        def warm_qwen() -> None:
            if ollama_status in {"started", "already_running"}:
                readiness["qwen"] = ollama.warm_model("qwen3:4b", timeout=45.0)
            log.info("local qwen warmup ready: %s", readiness["qwen"])

        def start_subscription_bridge() -> None:
            readiness["subscription"] = bridge.start()
            if not readiness["subscription"]:
                log.warning("subscription bridge unavailable; local Qwen remains active")

        warm_thread = threading.Thread(target=warm_qwen, name="qwen-warmup", daemon=True)
        bridge_thread = threading.Thread(
            target=start_subscription_bridge,
            name="subscription-bridge-start",
            daemon=True,
        )
        warm_thread.start()
        bridge_thread.start()
        lock.write_text(
            json.dumps(
                {"port": app_port, "pid": os.getpid(), "token": instance_token}
            )
        )
        if not wait_healthy(app_port, token=instance_token):
            log.error("app failed to become healthy; see postgres.log too")
            if not headless:
                retry = _startup_failure(
                    "Der Debatten-Assistent wurde nicht rechtzeitig bereit. "
                    f"Protokoll: {data_dir / 'debateai.log'}",
                    headless,
                )
            return retry if not headless else 1
        if not headless:
            lifecycle.set_progress(90, "Debatten-Assistent ist bereit")
        if headless:
            _wait_for_stop_file(data_dir)
        else:
            lifecycle.set_progress(96, "Oberfläche wird geöffnet ...")
            lifecycle.set_progress(
                100 if readiness["qwen"] else 94,
                "Debate AI ist startklar"
                if readiness["qwen"]
                else "Start eingeschränkt: Qwen ist noch nicht vorgeladen",
            )
            # Destroy the topmost startup surface before WebView2 creates its
            # native form. If the splash remains the active owner while the
            # form is created, destroying it immediately afterwards can leave
            # the healthy child alive with its only real window hidden.
            lifecycle.close()
            update_requested = _run_tray(
                app_port,
                data_dir,
                instance_token,
                open_initial=True,
            )
            lifecycle.show_shutdown("Sitzung und Hintergrunddienste werden beendet ...")
    finally:
        log.info("shutting down")
        if pg_watch_stop is not None:
            pg_watch_stop.set()
        if pg_watch_thread is not None:
            pg_watch_thread.join(timeout=5)
        if not headless:
            lifecycle.set_progress(25, "Debatten-Assistent wird beendet ...")
        server.should_exit = True
        if thread.is_alive():
            thread.join(timeout=15)
        if bridge_thread is not None:
            bridge_thread.join(timeout=9)
        bridge.stop()
        gemini_web_bridge.stop()
        _stop_embedded_windows()
        if not headless:
            lifecycle.set_progress(55, "Verbindungen und Fenster wurden geschlossen")
        listener.close()
        if not headless:
            lifecycle.set_progress(75, "Lokales KI-Modell wird beendet ...")
        ollama.stop()
        if not headless:
            lifecycle.set_progress(90, "Lokale Datenbank wird beendet ...")
        pg.stop()
        console_suppressor.stop()
        lock.unlink(missing_ok=True)
        lifecycle.close()
    return _launch_requested_update(update_requested, data_dir, log)


def run(headless: bool = False) -> int:
    """Start one service owner; later launches only wait for and reveal its UI."""
    _hydrate_windows_provider_environment()
    data_dir = app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    port = existing_instance_port(data_dir)
    if port is not None:
        if not headless:
            if not _request_owner_window(data_dir):
                _open_system_browser(desktop_app_url(port))
        return 0

    guard = _acquire_instance_guard(data_dir)
    if guard is None:
        waiting = None
        if not headless:
            waiting = LifecycleSplash()
            waiting.show_startup("Debate AI wird bereits gestartet ...")
        try:
            port = wait_for_other_instance(data_dir, timeout=90.0)
            if port is not None:
                if not headless:
                    if not _request_owner_window(data_dir):
                        _open_system_browser(desktop_app_url(port))
                return 0
            # If the first launcher exited during startup, this invocation may
            # safely take over. It must never adopt and later stop that first
            # launcher's database while the guard remains held.
            guard = _acquire_instance_guard(data_dir)
            if guard is None:
                if headless:
                    return 1
                return _startup_failure(
                    "Debate AI wird noch in einer anderen Instanz gestartet. "
                    f"Protokoll: {data_dir / 'debateai.log'}",
                    headless,
                )
        finally:
            if waiting is not None:
                waiting.close()

    try:
        return _run_owned(headless)
    finally:
        _release_instance_guard(guard)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--chatgpt-web-login":
        sys.exit(run_chatgpt_web_login(Path(sys.argv[2])))
    if len(sys.argv) == 3 and sys.argv[1] == "--gemini-web-login":
        sys.exit(run_gemini_web_login(Path(sys.argv[2])))
    if len(sys.argv) == 7 and sys.argv[1] == "--embedded-webview":
        sys.exit(run_embedded_webview(
            sys.argv[2],
            sys.argv[3],
            int(sys.argv[4]),
            int(sys.argv[5]),
            sys.argv[6] == "1",
        ))
    _headless = _env_value("DEBATEAI_HEADLESS") == "1"
    _result = run(headless=_headless)
    while _result == 2 and not _headless:
        _result = run(headless=False)
    sys.exit(_result)
