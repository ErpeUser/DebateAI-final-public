"""Small opaque cursors shared by ordered list endpoints.

The public API keeps returning arrays for compatibility. A cursor is a
URL-safe JSON envelope carrying the endpoint kind and the last ordered row;
callers must treat it as opaque and send it back unchanged.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any


class InvalidCursor(ValueError):
    """Raised when a cursor is malformed or belongs to another endpoint."""


def encode_cursor(kind: str, **values: Any) -> str:
    payload = {"v": 1, "kind": kind, **values}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str, expected_kind: str) -> dict[str, Any]:
    if not value or len(value) > 512:
        raise InvalidCursor("Cursor is empty or too long")
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise InvalidCursor("Cursor is malformed") from None
    if (
        not isinstance(payload, dict)
        or payload.get("v") != 1
        or payload.get("kind") != expected_kind
    ):
        raise InvalidCursor("Cursor does not belong to this endpoint")
    return payload
