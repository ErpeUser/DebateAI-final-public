"""Backend startup wrapper."""

from __future__ import annotations

import os
import sys

from install_sortformer import ensure_sortformer_installed

DEFAULT_BACKEND_HOST = "127.0.0.1"


def _backend_host() -> str:
    """Resolve and validate the listener address for native and Compose starts."""
    host = os.getenv("BACKEND_HOST", DEFAULT_BACKEND_HOST).strip() or DEFAULT_BACKEND_HOST
    loopback_hosts = {"localhost", "127.0.0.1", "::1", "[::1]"}
    if host.lower() not in loopback_hosts and not os.getenv("DEBATEAI_INSTANCE_TOKEN", "").strip():
        raise RuntimeError(
            "BACKEND_HOST must stay on loopback unless DEBATEAI_INSTANCE_TOKEN is set"
        )
    return host


def main() -> int:
    ensure_sortformer_installed(required=False)
    host = _backend_host()

    command = [
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        "8000",
        "--ws-ping-timeout",
        "90",
        "--ws-max-queue",
        "2048",
        "--ws-max-size",
        "65536",
    ]
    if os.getenv("BACKEND_RELOAD", "false").strip().lower() not in {"0", "false", "no", "off"}:
        command.append("--reload")

    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
