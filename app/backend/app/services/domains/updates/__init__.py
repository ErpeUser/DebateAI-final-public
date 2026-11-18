"""Signed release and update services, with old module imports preserved."""
from app.services.debateai_update_channel import channel_configuration
from app.services.update_signing import (
    parse_release_signing_keys,
    verify_update_descriptor,
    public_update_descriptor,
    canonical_update_bytes,
)
from app.services.update_service import UpdateService, InvalidUpdate

__all__ = (
    "channel_configuration", "parse_release_signing_keys",
    "verify_update_descriptor", "public_update_descriptor",
    "canonical_update_bytes", "UpdateService", "InvalidUpdate",
)
