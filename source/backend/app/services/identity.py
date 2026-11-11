"""DebateAI product identity helpers with controlled legacy aliases."""

from __future__ import annotations

import os


def env_value(canonical: str, legacy: str | None = None, default: str = "") -> str:
    """Return a canonical setting first, then its Backchannel alias."""
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
