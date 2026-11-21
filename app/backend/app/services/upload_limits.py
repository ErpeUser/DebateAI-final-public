"""Bounded endpoint-side reads for user-supplied file uploads."""

from __future__ import annotations


class UploadTooLarge(ValueError):
    """Raised when an upload exceeds the endpoint configured byte limit."""

    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        super().__init__(f"Upload exceeds the {max_bytes}-byte limit.")


async def read_bounded_upload(upload, *, max_bytes: int) -> bytes:
    """Read at most max_bytes and one sentinel byte from an UploadFile."""
    if not isinstance(max_bytes, int) or max_bytes < 0:
        raise ValueError("max_bytes must be a non-negative integer")
    content = await upload.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise UploadTooLarge(max_bytes)
    return content
