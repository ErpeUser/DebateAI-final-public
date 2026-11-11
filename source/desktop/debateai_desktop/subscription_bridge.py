"""Manage the single loopback CLIProxyAPI process used by the desktop app.

CLIProxyAPI owns OAuth login and refresh state. DebateAI owns only the
versioned executable, loopback configuration, client key, and child lifetime.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from debateai_desktop.paths import resource
from debateai_desktop.windows_console import hidden_startupinfo
from debateai_identity import env_value, set_env


DEFAULT_PORT = 8317
_LOGIN_FLAGS = {
    "codex": "--codex-login",
    "antigravity": "--antigravity-login",
    "gemini-cli": "--geminicli-login",
}


def _private_directory(path: Path) -> None:
    """Create an app-private directory without following a directory symlink."""
    if path.is_symlink():
        raise OSError(f"refusing private symlink directory: {path}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.chmod(0o700)
    except OSError:
        # Windows uses the containing LocalAppData ACL. chmod is still useful
        # on the supported Unix development platforms.
        pass


def _write_private_text(path: Path, value: str, *, encoding: str = "utf-8") -> None:
    """Atomically replace a secret-bearing file with owner-only Unix mode."""
    if path.is_symlink():
        raise OSError(f"refusing private symlink file: {path}")
    temporary = path.with_name(path.name + ".new")
    if temporary.is_symlink():
        raise OSError(f"refusing private temporary symlink: {temporary}")
    temporary.unlink(missing_ok=True)
    with temporary.open("x", encoding=encoding) as stream:
        stream.write(value)
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _yaml_string(value: str) -> str:
    # JSON string syntax is a strict, well-supported subset of YAML and safely
    # handles Windows backslashes, quotes, and non-ASCII profile names.
    return json.dumps(value, ensure_ascii=False)


class SubscriptionBridge:
    def __init__(self, data_dir: Path, logger):
        self.root = Path(data_dir) / "subscription-bridge"
        self.managed_executable = self.root / (
            "cli-proxy-api.exe" if sys.platform == "win32" else "cli-proxy-api"
        )
        configured_executable = env_value("DEBATEAI_CLIPROXYAPI_EXECUTABLE").strip()
        self.external_executable = (
            Path(configured_executable).expanduser()
            if configured_executable
            else None
        )
        if self.external_executable is not None and not self.external_executable.is_absolute():
            self.log = logger
            self.log.warning(
                "ignoring relative DEBATEAI_CLIPROXYAPI_EXECUTABLE"
            )
            self.external_executable = None
        self.executable = self.external_executable or self.managed_executable
        self.bundled_root = resource("cliproxyapi")
        self.bundled_executable = self.bundled_root / self.managed_executable.name
        self.plugins_dir = self.root / "plugins"
        self.bundled_plugins_dir = self.bundled_root / "plugins"
        self.config = self.root / "config.yaml"
        self.key_file = self.root / "client-key"
        self.log = logger
        configured_auth_dir = env_value("DEBATEAI_CLIPROXYAPI_AUTH_DIR").strip()
        candidate_auth_dir = (
            Path(configured_auth_dir).expanduser()
            if configured_auth_dir
            else self.root / "auth"
        )
        if configured_auth_dir and (
            not candidate_auth_dir.is_absolute()
            or any(
                part.casefold() in {"ai", "log", "logs"}
                for part in candidate_auth_dir.parts
            )
        ):
            self.log.warning(
                "ignoring unsafe DEBATEAI_CLIPROXYAPI_AUTH_DIR"
            )
            candidate_auth_dir = self.root / "auth"
        self.auth_dir = candidate_auth_dir
        try:
            configured_port = int(
                env_value("DEBATEAI_CLIPROXYAPI_PORT", str(DEFAULT_PORT))
            )
        except ValueError:
            configured_port = DEFAULT_PORT
        if not 1 <= configured_port <= 65535:
            configured_port = DEFAULT_PORT
        self.port = configured_port
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen | None = None
        self.served_models: list[str] = []
        self.adopted = False

    @property
    def installed(self) -> bool:
        return (
            self.executable.is_file()
            and not self.executable.is_symlink()
        ) or (
            self.bundled_executable.is_file()
            and not self.bundled_executable.is_symlink()
        )

    @property
    def client_key(self) -> str:
        if not self.key_file.is_file() or self.key_file.is_symlink():
            return ""
        return self.key_file.read_text(encoding="utf-8").strip()

    def _bundled_version(self) -> str:
        version_file = self.bundled_root / "VERSION"
        try:
            return version_file.read_text(encoding="ascii").strip()
        except OSError:
            return ""

    def _installed_version(self) -> str:
        version_file = self.root / "VERSION"
        try:
            return version_file.read_text(encoding="ascii").strip()
        except OSError:
            return ""

    def _provision_executable(self) -> None:
        if self.external_executable is not None:
            self._provision_plugins()
            return
        if not self.bundled_executable.is_file():
            return
        bundled_version = self._bundled_version()
        if self.executable.is_file() and bundled_version:
            if self._installed_version() == bundled_version:
                self._provision_plugins()
                return
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.executable.with_suffix(self.executable.suffix + ".new")
        shutil.copy2(self.bundled_executable, temporary)
        temporary.replace(self.executable)
        if bundled_version:
            (self.root / "VERSION").write_text(
                bundled_version + "\n", encoding="ascii"
            )
        self._provision_plugins()

    def _provision_plugins(self) -> None:
        bundled = self.bundled_plugins_dir / "windows" / "amd64"
        if not bundled.is_dir():
            return
        target_dir = self.plugins_dir / "windows" / "amd64"
        target_dir.mkdir(parents=True, exist_ok=True)
        bundled_files = list(bundled.glob("gemini-cli-v*.dll"))
        if not bundled_files:
            return
        source = bundled_files[0]
        target = target_dir / source.name
        for obsolete in target_dir.glob("gemini-cli-v*.dll"):
            if obsolete.name != target.name:
                obsolete.unlink(missing_ok=True)
        if not target.is_file() or target.stat().st_size != source.stat().st_size:
            temporary = target.with_suffix(target.suffix + ".new")
            shutil.copy2(source, temporary)
            temporary.replace(target)

    def _ensure_config(self) -> None:
        _private_directory(self.root)
        _private_directory(self.auth_dir)
        if not self.client_key:
            _write_private_text(self.key_file, secrets.token_urlsafe(32))
        key = _yaml_string(self.client_key)
        auth_path = _yaml_string(str(self.auth_dir))
        _write_private_text(
            self.config,
            "config-version: 8\n"
            "server:\n"
            '  host: "127.0.0.1"\n'
            f"  port: {self.port}\n"
            "  discovery:\n"
            "    enabled: false\n"
            "management:\n"
            "  allow-remote: false\n"
            f"  secret-key: {key}\n"
            "  disable-control-panel: true\n"
            "access:\n"
            "  api-keys:\n"
            f"    - {key}\n"
            "routing:\n"
            "  retry:\n"
            "    request-retry: 1\n"
            "    max-retry-credentials: 0\n"
            "    max-retry-interval: 15\n"
            "  cooldown:\n"
            "    disable-cooling: false\n"
            "    save-cooldown-status: false\n"
            "    transient-error-cooldown-seconds: 30\n"
            "oauth:\n"
            f"  auth-dir: {auth_path}\n"
            "observability:\n"
            "  logs:\n"
            "    debug: false\n"
            "    logging-to-file: false\n"
            "    request-log: false\n"
            "  usage:\n"
            "    usage-statistics-enabled: false\n"
            "plugins:\n"
            "  enabled: true\n"
            '  dir: "plugins"\n'
            "  configs:\n"
            "    gemini-cli:\n"
            "      enabled: true\n",
            encoding="utf-8",
        )

    def _export_connection(self) -> None:
        url = f"http://127.0.0.1:{self.port}/v1"
        set_env("DEBATEAI_SUBSCRIPTION_BRIDGE_URL", url)
        set_env("DEBATEAI_SUBSCRIPTION_BRIDGE_KEY", self.client_key)
        set_env(
            "DEBATEAI_SUBSCRIPTION_MODELS", "DEBATEAI_SUBSCRIPTION_MODELS",
            json.dumps(self.served_models, separators=(",", ":")),
        )
        os.environ.setdefault("SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK", "true")

    def _probe(self, timeout: float = 0.75) -> list[str] | None:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/models",
            # The listener is always loopback, even when the port is explicitly
            # changed for a locally managed development installation.
            headers={"Authorization": f"Bearer {self.client_key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
        except (OSError, ValueError, urllib.error.URLError):
            return None
        values = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(values, list):
            return None
        return sorted(
            {
                str(item.get("id") or "").strip()
                for item in values
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            }
        )

    def prepare(self) -> bool:
        """Provision the pinned binary and export its private endpoint."""
        if not self.installed:
            return False
        self._provision_executable()
        self._ensure_config()
        self._export_connection()
        return self.executable.is_file()

    def start(self) -> bool:
        if self.process is not None and self.process.poll() is None:
            return True

        self._ensure_config()
        existing_models = self._probe()
        if existing_models is not None:
            self.served_models = existing_models
            self.adopted = True
            self._export_connection()
            self.log.info(
                "using existing subscription bridge with %s models",
                len(existing_models),
            )
            return True

        try:
            self._provision_executable()
        except OSError:
            self.log.exception("subscription bridge could not be provisioned")
            return False
        if not self.executable.is_file():
            return False
        self._export_connection()
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.process = subprocess.Popen(
                [
                    str(self.executable),
                    "-config",
                    str(self.config),
                    "-local-model",
                ],
                cwd=str(self.root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                startupinfo=hidden_startupinfo(),
            )
        except OSError:
            self.log.exception("subscription bridge failed to start")
            self.process = None
            return False

        empty_catalog_probes = 0
        for _attempt in range(40):
            models = self._probe()
            if models is not None:
                # CLIProxyAPI starts accepting HTTP requests before its OAuth
                # providers have finished registering their models.  An empty
                # first response is therefore not yet a stable catalog.
                if not models:
                    empty_catalog_probes += 1
                    if empty_catalog_probes < 15:
                        time.sleep(0.2)
                        continue
                self.served_models = models
                self._export_connection()
                self.log.info(
                    "subscription bridge started with %s models", len(models)
                )
                return True
            if self.process.poll() is not None:
                break
            time.sleep(0.2)
        self.log.error("subscription bridge did not become ready")
        self.stop()
        return False

    def stop(self) -> None:
        process = self.process
        self.process = None
        self.adopted = False
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        except OSError:
            self.log.exception("subscription bridge failed to stop cleanly")
        else:
            self.log.info("subscription bridge stopped")
