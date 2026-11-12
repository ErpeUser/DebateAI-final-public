"""Canonical DebateAI identity and safe one-way data migration."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

PRODUCT_NAME = "DebateAI"
REPOSITORY = "ErpeUser/DebateAI"
WINDOWS_LAUNCHER = "DebateAI.exe"
WINDOWS_UPDATER = "DebateAIUpdater.exe"
INSTANCE_HEADER = "X-DebateAI-Instance"
WS_TOKEN_PROTOCOL_PREFIX = "debateai.instance."


class DataMigration:
    """Result of a non-destructive legacy data migration check."""

    __slots__ = ("destination", "source", "copied", "reason")

    def __init__(self, destination: Path, source: Path | None, copied: bool, reason: str):
        self.destination = destination
        self.source = source
        self.copied = copied
        self.reason = reason


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


def _legacy_data_root(base: Path, *, lowercase: bool) -> Path:
    # This is the only legacy identifier retained, and it is used solely for
    # an explicit, non-destructive migration check.
    return base / ("backchannel" if lowercase else "Backchannel")


def migrate_legacy_data_root(
    *,
    base: Path,
    destination: Path,
    source: Path | None = None,
) -> DataMigration:
    """Copy an old data root into an empty DebateAI root without deleting it.

    The source is never removed. A non-empty destination is never overwritten;
    callers can continue using it and the migration result is explicit.
    """
    destination = destination.expanduser()
    source = source or _legacy_data_root(base, lowercase=False)
    if not source.is_dir() or not any(source.iterdir()):
        return DataMigration(destination, None, False, "no-legacy-data")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        return DataMigration(destination, source, False, "destination-not-empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{destination.name}.migration-",
        dir=str(destination.parent),
    ))
    try:
        shutil.copytree(source, staging, dirs_exist_ok=True)
        if destination.exists():
            if not destination.is_dir() or any(destination.iterdir()):
                return DataMigration(destination, source, False, "destination-not-empty")
            destination.rmdir()
        os.replace(staging, destination)
        staging = None
        return DataMigration(destination, source, True, "copied")
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def resolve_data_root(*, base: Path, environment: Mapping[str, str], lowercase: bool = False) -> Path:
    """Resolve the canonical data root and perform a safe legacy copy check."""
    override = environment.get("DEBATEAI_DATA_DIR")
    if override:
        selected = Path(override).expanduser()
    else:
        name = PRODUCT_NAME.lower() if lowercase else PRODUCT_NAME
        selected = base / name
        legacy = _legacy_data_root(base, lowercase=lowercase)
        try:
            migration = migrate_legacy_data_root(
                base=base,
                destination=selected,
                source=legacy,
            )
        except OSError:
            # If the canonical destination cannot be populated, keep using the
            # intact legacy source instead of abandoning user data.
            if legacy.is_dir() and any(legacy.iterdir()):
                selected = legacy
                migration = None
            else:
                raise
        if migration is not None and (
            migration.copied or migration.reason == "already-copied"
        ):
            selected = migration.destination
        elif migration is not None and migration.reason == "destination-not-empty":
            selected = migration.destination
        elif not selected.exists() and legacy.is_dir() and any(legacy.iterdir()):
            # A read-only filesystem can still use the legacy root; no data is
            # silently abandoned.
            selected = legacy
    if selected.exists() and not selected.is_dir():
        raise NotADirectoryError("The configured DebateAI data location is not a directory.")
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
