"""Standalone product identity; legacy names are read-only migration aliases."""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

PRODUCT_NAME = 'DebateAI'
REPOSITORY = 'ErpeUser/DebateAI'
LEGACY_PRODUCT_NAME = 'Backchannel'


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
        if not selected.exists() and legacy.is_dir():
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
