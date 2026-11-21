"""Lifecycle for the explicitly enabled local Gemini Web provider.

The pinned upstream binary discovers the models offered by the signed-in
consumer account and reports the resolved response model. It is started only
while the backend-owned runtime cookie file exists.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from debateai_identity import set_env

from debateai_desktop.paths import free_port, resource
from debateai_desktop.windows_console import hidden_startupinfo


class GeminiWebBridge:
    def __init__(self, data_dir: Path, logger):
        self.root = Path(data_dir) / "gemini-web"
        self.cookie_file = self.root / "cookie.txt"
        self.cookie_cache = self.root / ".cookies"
        self.key_file = self.root / "client-key"
        executable_name = (
            "gemini-web-to-api.exe" if sys.platform == "win32" else "gemini-web-to-api"
        )
        self.executable = resource("gemini_web_to_api") / executable_name
        self.log = logger
        self.port = free_port()
        self.process: subprocess.Popen | None = None
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        # Keep the encrypted-store handoff only in this process after the
        # plaintext file has been consumed.  If the upstream helper exits on a
        # failed request, the watcher can restart it without requiring another
        # browser login or leaving the credential on disk.
        self._restart_cookie = ""

    @property
    def client_key(self) -> str:
        if not self.key_file.is_file():
            return ""
        return self.key_file.read_text(encoding="utf-8").strip()

    def _ensure_key(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.client_key:
            self.key_file.write_text(secrets.token_urlsafe(32), encoding="utf-8")
            try:
                os.chmod(self.key_file, 0o600)
            except OSError:
                pass

    def _export_connection(self) -> None:
        set_env("DEBATEAI_GEMINI_WEB_URL", f"http://127.0.0.1:{self.port}/openai/v1")
        set_env("DEBATEAI_GEMINI_WEB_KEY", self.client_key)
        set_env("DEBATEAI_GEMINI_WEB_COOKIE_FILE", str(self.cookie_file))
        set_env("DEBATEAI_GEMINI_WEB_MODELS", "[]")

    def _request_json(self, path: str, *, authenticated: bool) -> dict | None:
        headers = (
            {"Authorization": f"Bearer {self.client_key}"} if authenticated else {}
        )
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=1) as response:
                return json.load(response)
        except (OSError, ValueError, urllib.error.URLError):
            return None

    def _probe_models(self) -> list[str] | None:
        payload = self._request_json("/openai/v1/models", authenticated=True)
        if payload is None:
            return None
        items = payload.get("data")
        # The upstream bridge reports ``data: null`` for a short interval
        # between HTTP readiness and authenticated catalog discovery.  Treat
        # that as the same transitional state as an empty catalog; otherwise
        # the watcher raises TypeError and needlessly restarts a healthy cold
        # process until the catalog happens to win the race.
        if not isinstance(items, list):
            return []
        return [
            str(item.get("id") or "").strip()
            for item in items
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ]

    def _runtime_environment(self, cookie: str) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOST": "127.0.0.1",
                "PORT": str(self.port),
                "DEBATEAI_API_KEY": self.client_key,
                "GEMINI_COOKIES": cookie,
                "GEMINI_TEMPORARY": "true",
                "GEMINI_REFRESH_INTERVAL": "1440",
                "GEMINI_MAX_RETRIES": "1",
                "RATE_LIMIT_ENABLED": "false",
                "LOG_LEVEL": "error",
                "APP_ENV": "production",
            }
        )
        return environment

    def _stop_process(self) -> None:
        set_env("DEBATEAI_GEMINI_WEB_SESSION_ACTIVE", "0")
        process = self.process
        self.process = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        except OSError:
            self.log.exception("Gemini web provider failed to stop cleanly")

    def _start_process(self, cookie: str) -> bool:
        if self.stop_event.is_set():
            return False
        self._stop_process()
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.process = subprocess.Popen(
                [str(self.executable)],
                cwd=str(self.root),
                env=self._runtime_environment(cookie),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                startupinfo=hidden_startupinfo(),
            )
        except OSError:
            self.log.exception("Gemini web provider failed to start")
            self.process = None
            return False

        # /health is intentionally available before the authenticated account
        # catalog.  A freshly accepted Google session normally publishes its
        # models quickly, but a cold Web session can take noticeably longer.
        # Keep this wait in the dedicated watcher thread so neither backend
        # startup nor the UI is blocked, and do not publish an empty catalog.
        for _attempt in range(150):
            if self.stop_event.is_set():
                self._stop_process()
                return False
            process = self.process
            if process is None or process.poll() is not None:
                break
            if self._request_json("/health", authenticated=False) is not None:
                models = self._probe_models()
                # The provider can answer /models with an empty transitional
                # catalog while its authenticated Gemini session is still
                # discovering the account's selectable models.  Publishing
                # that intermediate value would permanently hide Pro until
                # the process is restarted because this startup probe is the
                # only place that exports the catalog.
                if models:
                    if self.stop_event.is_set():
                        self._stop_process()
                        return False
                    set_env(
                        "DEBATEAI_GEMINI_WEB_MODELS",
                        json.dumps(models, separators=(",", ":")),
                    )
                    set_env("DEBATEAI_GEMINI_WEB_SESSION_ACTIVE", "1")
                    self.log.info(
                        "Gemini web provider started with %s account models",
                        len(models),
                    )
                    return True
            time.sleep(0.2)
        self.log.error("Gemini web provider did not become ready")
        self._stop_process()
        return False

    def _watch_cookie(self) -> None:
        last_signature: tuple[int, int] | None = None
        while not self.stop_event.wait(0.25):
            try:
                try:
                    stat = self.cookie_file.stat()
                    signature = (stat.st_mtime_ns, stat.st_size)
                except OSError:
                    signature = None
                process_unavailable = (
                    self.process is None or self.process.poll() is not None
                )
                if signature is None and process_unavailable and self._restart_cookie:
                    if self._start_process(self._restart_cookie):
                        continue
                    self.stop_event.wait(1.0)
                    continue
                set_env("DEBATEAI_GEMINI_WEB_SESSION_ACTIVE", "0")
                set_env("DEBATEAI_GEMINI_WEB_MODELS", "[]")
                # One unchanged rejected credential must not relaunch the
                # provider forever. A new login rewrites the handoff file and
                # therefore changes the signature, which triggers a new try.
                if signature == last_signature:
                    continue
                last_signature = signature
                if signature is None:
                    self._stop_process()
                    set_env("DEBATEAI_GEMINI_WEB_MODELS", "[]")
                    continue
                try:
                    cookie = self.cookie_file.read_text(encoding="utf-8").strip()
                except OSError:
                    continue
                if not cookie:
                    # An empty handoff is an explicit disconnect signal from
                    # the backend.  It is distinguishable from the absent file
                    # used after a successful one-time credential handoff.
                    self._restart_cookie = ""
                    self._stop_process()
                    set_env("DEBATEAI_GEMINI_WEB_MODELS", "[]")
                    self.cookie_file.unlink(missing_ok=True)
                    shutil.rmtree(self.cookie_cache, ignore_errors=True)
                    last_signature = None
                    continue
                if self._start_process(cookie):
                    # The encrypted database copy is durable. The plaintext
                    # handoff exists only long enough to seed the child.
                    self._restart_cookie = cookie
                    self.cookie_file.unlink(missing_ok=True)
                    last_signature = None
            except Exception:
                # A transient process/filesystem failure must never kill the
                # only watcher that can consume a later successful re-login.
                self.log.exception("Gemini web provider watcher recovered")
                last_signature = None
                self.stop_event.wait(1.0)

    def start(self) -> bool:
        if self.thread is not None:
            return True
        if not self.executable.is_file():
            self.log.warning("Gemini web provider binary is not bundled")
            return False
        self._ensure_key()
        # The durable copy is encrypted by the backend. Never trust a runtime
        # file left behind by a crash before that encrypted value is restored.
        self.cookie_file.unlink(missing_ok=True)
        # The upstream process stores rotated timestamp cookies here. Keep the
        # cache across ordinary app restarts: Gemini can rotate PSIDTS while
        # the original encrypted browser handoff remains unchanged. It is
        # cleared only by the explicit disconnect signal above.
        self._export_connection()
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._watch_cookie,
            name="gemini-web-provider-watch",
            daemon=True,
        )
        self.thread.start()
        self.log.info("Gemini web provider is ready for explicit activation")
        return True

    def stop(self) -> None:
        thread = self.thread
        self.thread = None
        self.stop_event.set()
        if thread is not None:
            thread.join(timeout=3)
        self._stop_process()
        self._restart_cookie = ""
        self.cookie_file.unlink(missing_ok=True)
        set_env("DEBATEAI_GEMINI_WEB_MODELS", "[]")
        set_env("DEBATEAI_GEMINI_WEB_SESSION_ACTIVE", "0")
        self.log.info("Gemini web provider stopped")
