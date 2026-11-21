"""Platform paths, port picking, and bundle resource resolution."""

import socket
import sys
from pathlib import Path

from debateai_identity import PRODUCT_NAME, app_data_dir

APP_NAME = PRODUCT_NAME
__all__ = ["APP_NAME", "app_data_dir", "free_port", "resource"]

# Repo-checkout locations for each bundled resource (dev mode). In a
# PyInstaller bundle every resource sits directly under sys._MEIPASS.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEV_RESOURCES = {
    "frontend": _REPO_ROOT / "frontend" / "dist",
    "models": _REPO_ROOT / "backend" / "models",
    "pgsql": _REPO_ROOT / "desktop" / "pgsql",
    "assets": _REPO_ROOT / "desktop" / "assets",
    "ffmpeg": _REPO_ROOT / "desktop" / "ffmpeg",
    "cliproxyapi": _REPO_ROOT / "desktop" / "cliproxyapi",
    "gemini_web_to_api": _REPO_ROOT / "desktop" / "gemini_web_to_api",
    "chatgpt_oracle": _REPO_ROOT / "desktop" / "chatgpt_oracle",
    "release_signing_keys.json": _REPO_ROOT / "desktop" / "release_signing_keys.json",
}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def resource(name: str) -> Path:
    if name not in _DEV_RESOURCES:
        raise KeyError(f"unknown resource: {name}")
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / name
    return _DEV_RESOURCES[name]
