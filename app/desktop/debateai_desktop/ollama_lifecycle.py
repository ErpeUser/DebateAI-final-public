"""Start a local Ollama server for the desktop app and stop only our copy."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from debateai_desktop.windows_console import hidden_startupinfo

_AUTO = object()


def find_ollama() -> Path | None:
    located = shutil.which("ollama")
    if located:
        return Path(located)
    if sys.platform != "win32":
        return None
    local = os.environ.get("LOCALAPPDATA")
    candidates = [
        Path(local) / "Programs" / "Ollama" / "ollama.exe" if local else None,
        Path(os.environ.get("PROGRAMFILES", "")) / "Ollama" / "ollama.exe",
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def ollama_is_ready() -> bool:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/tags", timeout=0.5
        ) as response:
            return response.status == 200
    except Exception:
        return False


def ollama_loaded_models() -> set[str]:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:11434/api/ps", timeout=1
        ) as response:
            payload = json.loads(response.read(1_000_000).decode("utf-8"))
        return {
            str(item.get("name") or item.get("model") or "").strip()
            for item in payload.get("models", [])
            if isinstance(item, dict) and (item.get("name") or item.get("model"))
        }
    except Exception:
        return set()


def ollama_unload_model(model: str) -> None:
    body = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3):
            pass
    except Exception:
        pass


def ollama_warm_model(model: str, timeout: float = 45.0) -> bool:
    """Load one already-installed model without pulling or producing output."""
    body = json.dumps(
        {
            "model": model,
            "prompt": " ",
            "stream": False,
            "keep_alive": "20m",
            "options": {"num_predict": 1},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


class ManagedOllama:
    """Own exactly the Ollama process started by this launcher instance."""

    def __init__(
        self,
        *,
        executable: Path | None | object = _AUTO,
        probe: Callable[[], bool] = ollama_is_ready,
        process_factory: Callable[..., object] = subprocess.Popen,
        sleep: Callable[[float], None] = time.sleep,
        loaded_models: Callable[[], set[str]] = ollama_loaded_models,
        unload_model: Callable[[str], None] = ollama_unload_model,
        warm_model: Callable[[str, float], bool] = ollama_warm_model,
    ) -> None:
        self.executable = find_ollama() if executable is _AUTO else executable
        self._probe = probe
        self._process_factory = process_factory
        self._sleep = sleep
        self._loaded_models = loaded_models
        self._unload_model = unload_model
        self._warm_model = warm_model
        self._models_before: set[str] = set()
        self._process = None

    @property
    def owns_process(self) -> bool:
        return self._process is not None

    def start(self, timeout: float = 12.0) -> str:
        self._models_before = self._safe_loaded_models()
        if self._probe():
            return "already_running"
        if self.executable is None:
            return "unavailable"

        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["startupinfo"] = hidden_startupinfo()
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        try:
            process = self._process_factory([str(self.executable), "serve"], **kwargs)
        except OSError:
            return "failed"

        deadline = time.monotonic() + max(0.0, timeout)
        while time.monotonic() <= deadline:
            if self._probe():
                self._process = process
                return "started"
            if process.poll() is not None:
                return "failed"
            self._sleep(0.2)
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            # A stubborn child must not be left behind as an unowned Ollama
            # server after startup timed out. Escalate exactly as shutdown
            # does, while keeping the launcher failure path non-blocking.
            try:
                process.kill()
                process.wait(timeout=3)
            except Exception:
                pass
        return "failed"

    def stop(self) -> None:
        process, self._process = self._process, None
        for model in sorted(self._safe_loaded_models() - self._models_before):
            self._unload_model(model)
        self._models_before = set()
        if process is None:
            return
        try:
            process.terminate()
            process.wait(timeout=8)
        except Exception:
            try:
                process.kill()
                process.wait(timeout=3)
            except Exception:
                pass

    def warm_model(self, model: str, timeout: float = 45.0) -> bool:
        if not self._probe():
            return False
        return bool(self._warm_model(model, timeout))

    def _safe_loaded_models(self) -> set[str]:
        try:
            return set(self._loaded_models())
        except Exception:
            return set()
