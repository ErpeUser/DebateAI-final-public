"""Canonical DebateAI environment helpers."""
from __future__ import annotations
import os

def env_value(name: str, default: str = "") -> str:
    return os.environ.get(name) or default

def set_env(name: str, value: str) -> None:
    os.environ[name] = value
