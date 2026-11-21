"""Signed release and update services, with old module imports preserved."""

from app.services.debateai_update_channel import channel_configuration
from app.services.update_service import InvalidUpdate, UpdateService
from app.services.update_signing import (
    canonical_update_bytes,
    parse_release_signing_keys,
    public_update_descriptor,
    verify_update_descriptor,
)

__all__ = (
    "InvalidUpdate",
    "UpdateService",
    "canonical_update_bytes",
    "channel_configuration",
    "parse_release_signing_keys",
    "public_update_descriptor",
    "verify_update_descriptor",
)
