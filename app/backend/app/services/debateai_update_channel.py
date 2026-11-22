"""Independent, explicitly configured update channel; no inherited vendor egress."""

from __future__ import annotations

import importlib
import logging
import os
import string
import threading
from collections.abc import Mapping
from urllib.parse import urlsplit

_lock = threading.Lock()
_service = None


def _validate_template(value: str, required: set[str]) -> tuple[str, str, int]:
    fields = {
        field for _, field, _, _ in string.Formatter().parse(value) if field is not None
    }
    if fields != required:
        raise ValueError("Update URL has invalid or missing placeholders.")
    for _, field, spec, conversion in string.Formatter().parse(value):
        if field is not None and (spec or conversion):
            raise ValueError("Update URL formatting modifiers are not allowed.")
    parsed = urlsplit(value.format(platform_id="windows-x64", version="v1.0.0"))
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "An independent HTTPS update URL without credentials is required."
        )
    if host.endswith(".invalid") or host == "invalid":
        raise ValueError("A placeholder hostname is not an update channel.")
    return parsed.scheme, host, parsed.port or 443


def channel_configuration(environment: Mapping[str, str]) -> dict[str, str] | None:
    names = (
        "DEBATEAI_UPDATE_DESCRIPTOR_URL",
        "DEBATEAI_UPDATE_ASSET_URL",
        "DEBATEAI_UPDATE_KEYS",
    )
    values = [environment.get(name, "").strip() for name in names]
    if not any(values):
        return None
    if not all(values):
        raise ValueError(
            "Descriptor URL, asset URL and independent public trust keys must all be configured."
        )
    descriptor, asset, keys = values
    if _validate_template(descriptor, {"platform_id"}) != _validate_template(
        asset, {"version", "platform_id"}
    ):
        raise ValueError("Descriptor and asset URLs must share one HTTPS origin.")
    return {"descriptor_url": descriptor, "asset_url": asset, "keys_path": keys}


def get_update_service():
    """One service per process, disabled unless a valid independent channel exists.

    The existing signature verification, archive validation and rollback remain
    mandatory. This layer never downloads keys or invents a replacement domain.
    A changed channel configuration takes effect after an application restart.
    """
    global _service
    # Resolve the implementation at call time.  The update service keeps a
    # backwards-compatible facade to this channel, so a top-level import in
    # either module would create an avoidable structural cycle.
    UpdateService = importlib.import_module(
        "app.services.update_service"
    ).UpdateService

    with _lock:
        if _service is None:
            try:
                config = channel_configuration(os.environ)
            except ValueError:
                logging.getLogger(__name__).warning(
                    "DebateAI updates disabled: invalid independent channel configuration."
                )
                config = None
            desktop = os.environ.get("DEBATEAI_DESKTOP") == "1"
            try:
                _service = UpdateService(
                    enabled=bool(desktop and config), **(config or {})
                )
            except (OSError, ValueError, TypeError):
                logging.getLogger(__name__).warning(
                    "DebateAI updates disabled: independent trust or installation configuration is unavailable."
                )
                _service = UpdateService(enabled=False)
        return _service
