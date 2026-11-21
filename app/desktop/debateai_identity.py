"""Canonical DebateAI runtime identity and side-effect-free data paths."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

PRODUCT_NAME = "DebateAI"
REPOSITORY = "ErpeUser/DebateAI"
WINDOWS_LAUNCHER = "DebateAI.exe"
WINDOWS_UPDATER = "DebateAIUpdater.exe"
INSTANCE_HEADER = "X-DebateAI-Instance"
WS_TOKEN_PROTOCOL_PREFIX = "debateai.instance."


def env_value(name: str, default: str = "") -> str:
    """Read one canonical environment variable."""
    return os.environ.get(name) or default


def set_env(name: str, value: str) -> None:
    os.environ[name] = value


def canonical_launcher(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == "win32":
        return WINDOWS_LAUNCHER
    if platform == "darwin":
        return "Contents/MacOS/DebateAI"
    if platform.startswith("linux"):
        return "DebateAI"
    raise ValueError(f"unsupported platform: {platform}")


def canonical_updater(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == "win32":
        return WINDOWS_UPDATER
    if platform == "darwin":
        return "Contents/MacOS/DebateAIUpdater"
    if platform.startswith("linux"):
        return "DebateAIUpdater"
    raise ValueError(f"unsupported platform: {platform}")


def canonical_root(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == "darwin":
        return "DebateAI.app"
    if platform == "win32" or platform.startswith("linux"):
        return "DebateAI"
    raise ValueError(f"unsupported platform: {platform}")


def resolve_data_root(
    *, base: Path, environment: Mapping[str, str], lowercase: bool = False
) -> Path:
    """Select only the configured or canonical path; never copy user data."""
    override = environment.get("DEBATEAI_DATA_DIR")
    name = PRODUCT_NAME.lower() if lowercase else PRODUCT_NAME
    selected = Path(override).expanduser() if override else base / name
    if selected.exists() and not selected.is_dir():
        raise NotADirectoryError(
            "The configured DebateAI data location is not a directory."
        )
    return selected


def app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ["LOCALAPPDATA"])
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return resolve_data_root(
        base=base,
        environment=os.environ,
        lowercase=sys.platform not in {"win32", "darwin"},
    )
