"""Standalone product identity; legacy names are read-only migration aliases."""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

PRODUCT_NAME = 'DebateAI'
REPOSITORY = 'ErpeUser/DebateAI'
LEGACY_PRODUCT_NAME = 'Backchannel'
WINDOWS_LAUNCHER = 'DebateAI.exe'
WINDOWS_UPDATER = 'DebateAIUpdater.exe'
INSTANCE_HEADER = 'X-DebateAI-Instance'
LEGACY_INSTANCE_HEADER = 'X-Backchannel-Instance'


def env_value(canonical: str, legacy: str | None = None, default: str = '') -> str:
    value = os.environ.get(canonical)
    if value:
        return value
    if legacy:
        value = os.environ.get(legacy)
        if value:
            return value
    return default


def set_compat_env(canonical: str, legacy: str, value: str) -> None:
    os.environ[canonical] = value
    os.environ[legacy] = value


def canonical_launcher(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == 'win32':
        return WINDOWS_LAUNCHER
    if platform == 'darwin':
        return 'Contents/MacOS/DebateAI'
    if platform.startswith('linux'):
        return 'DebateAI'
    raise ValueError(f'unsupported platform: {platform}')


def canonical_updater(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == 'win32':
        return WINDOWS_UPDATER
    if platform == 'darwin':
        return 'Contents/MacOS/DebateAIUpdater'
    if platform.startswith('linux'):
        return 'DebateAIUpdater'
    raise ValueError(f'unsupported platform: {platform}')


def canonical_root(platform: str | None = None) -> str:
    platform = platform or sys.platform
    if platform == 'darwin':
        return 'DebateAI.app'
    if platform == 'win32' or platform.startswith('linux'):
        return 'DebateAI'
    raise ValueError(f'unsupported platform: {platform}')


def legacy_launchers(platform: str | None = None) -> tuple[str, ...]:
    platform = platform or sys.platform
    if platform == 'win32':
        return ('Backchannel.exe',)
    if platform == 'darwin':
        return ('Contents/MacOS/Backchannel',)
    if platform.startswith('linux'):
        return ('Backchannel',)
    raise ValueError(f'unsupported platform: {platform}')


def legacy_updaters(platform: str | None = None) -> tuple[str, ...]:
    platform = platform or sys.platform
    if platform == 'win32':
        return ('BackchannelUpdater.exe',)
    if platform == 'darwin':
        return ('Contents/MacOS/BackchannelUpdater',)
    if platform.startswith('linux'):
        return ('BackchannelUpdater',)
    raise ValueError(f'unsupported platform: {platform}')


def legacy_roots(platform: str | None = None) -> tuple[str, ...]:
    platform = platform or sys.platform
    if platform == 'darwin':
        return ('Backchannel.app',)
    if platform == 'win32' or platform.startswith('linux'):
        return ('Backchannel',)
    raise ValueError(f'unsupported platform: {platform}')


def resolve_data_root(*, base: Path, environment: Mapping[str, str], lowercase: bool = False) -> Path:
    """Select a directory without moving, reading or deleting any user files.

    Fresh installations are independent. An existing legacy workspace remains
    usable until an offline, verified migration is performed. Never silently
    create an empty database while the user's original data is still present.
    """
    override = environment.get('DEBATEAI_DATA_DIR') or environment.get('BACKCHANNEL_DATA_DIR')
    if override:
        selected = Path(override).expanduser()
    else:
        name = PRODUCT_NAME.lower() if lowercase else PRODUCT_NAME
        legacy_name = LEGACY_PRODUCT_NAME.lower() if lowercase else LEGACY_PRODUCT_NAME
        selected = base / name
        legacy = base / legacy_name
        empty_new = not selected.exists() or (selected.is_dir() and not any(selected.iterdir()))
        if empty_new and legacy.is_dir() and any(legacy.iterdir()):
            selected = legacy
    if selected.exists() and not selected.is_dir():
        raise NotADirectoryError('The configured DebateAI data location is not a directory.')
    return selected


def app_data_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ['LOCALAPPDATA'])
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
    return resolve_data_root(base=base, environment=os.environ,
                             lowercase=sys.platform not in {'win32', 'darwin'})
