"""Private WebView2 login for the optional local Gemini web bridge."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections.abc import Callable, Iterable
from http.cookies import SimpleCookie
from pathlib import Path

REQUIRED_GEMINI_COOKIES = ("__Secure-1PSID", "__Secure-1PSIDTS")
GEMINI_LOGIN_URL = "https://gemini.google.com/app"


def cookie_header_from_webview(cookies: Iterable[SimpleCookie]) -> str:
    """Build a request Cookie header without exposing values to diagnostics."""
    pairs: dict[str, str] = {}
    for cookie in cookies:
        if not isinstance(cookie, SimpleCookie):
            continue
        for name, morsel in cookie.items():
            value = str(morsel.value or "")
            if name and value:
                pairs[name] = value
    if any(name not in pairs for name in REQUIRED_GEMINI_COOKIES):
        return ""
    return "; ".join(f"{name}={value}" for name, value in pairs.items())


def write_login_result(path: Path, payload: dict[str, str]) -> None:
    """Write the one-time handoff atomically with owner-only intent."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)


def wait_for_authenticated_cookie_header(
    get_cookies: Callable[[], Iterable[SimpleCookie]],
    *,
    completed: threading.Event | None = None,
    attempts: int = 2400,
    poll_seconds: float = 0.5,
) -> str:
    """Wait for the post-login navigation instead of trusting one load event."""
    for attempt in range(max(1, attempts)):
        if completed is not None and completed.is_set():
            return ""
        try:
            header = cookie_header_from_webview(get_cookies())
        except Exception:
            header = ""
        if header:
            return header
        if attempt + 1 < attempts and poll_seconds > 0:
            time.sleep(poll_seconds)
    return ""


def run_gemini_web_login(result_path: Path) -> int:
    """Open an isolated login window and hand the authenticated cookies back."""
    import webview

    result_path = Path(result_path)
    completed = threading.Event()
    poller_started = threading.Event()
    window = webview.create_window(
        "Gemini Pro anmelden",
        url=GEMINI_LOGIN_URL,
        width=1080,
        height=780,
        min_size=(720, 560),
        hidden=False,
        focus=True,
        on_top=True,
        background_color="#f7f8fa",
    )

    def finish_login(header: str) -> None:
        if completed.is_set():
            return
        if not header:
            return
        write_login_result(result_path, {"cookie": header})
        completed.set()
        window.destroy()

    def capture_authenticated_cookies(*_args) -> None:
        try:
            finish_login(cookie_header_from_webview(window.get_cookies()))
        except Exception:
            return

    def poll_authenticated_cookies() -> None:
        header = wait_for_authenticated_cookie_header(
            window.get_cookies,
            completed=completed,
        )
        finish_login(header)

    def start_cookie_poller() -> None:
        # Packaged WebView2 can finish creating its controller while the
        # top-level login window is still hidden.  Explicitly show it from the
        # GUI-ready callback so an expired session never leaves an invisible
        # helper polling forever with no way for the user to authenticate.
        try:
            window.restore()
            window.show()
            window.on_top = False
        except Exception:
            pass
        if poller_started.is_set():
            return
        poller_started.set()
        threading.Thread(
            target=poll_authenticated_cookies,
            name="gemini-login-cookie-watch",
            daemon=True,
        ).start()

    window.events.loaded += capture_authenticated_cookies
    webview.start(
        start_cookie_poller,
        gui=_webview_gui(),
        debug=False,
        private_mode=True,
    )
    if not completed.is_set():
        write_login_result(
            result_path,
            {
                "error": "Die Gemini-Anmeldung wurde abgebrochen oder blieb unvollstaendig."
            },
        )
        return 1
    return 0


def _webview_gui() -> str:
    """Select the pywebview backend available on the current desktop OS."""
    if sys.platform == "win32":
        return "edgechromium"
    if sys.platform == "darwin":
        return "cocoa"
    return "gtk"
