"""Bound selected diagnostic bodies BEFORE Starlette spools multipart files.

This is an endpoint-scoped 16 MiB + multipart-overhead bound, not a general
network security/rate limiter. Place inside the existing Host/Origin guard.
"""

import asyncio
import json
import time

from app.services.diagnostic_audio import MAX_UPLOAD_BYTES

_PATHS = {
    "/api/calibration/asr",
    "/api/diagnostics/local-fit/asr",
    "/api/diagnostics/diarization/sortformer/benchmark",
    "/api/diagnostics/diarization/voice-profile",
}


class DiagnosticUploadLimitMiddleware:
    def __init__(self, app, max_bytes=MAX_UPLOAD_BYTES + 65536, timeout_seconds=30):
        self.app, self.max_bytes, self.timeout = app, max_bytes, timeout_seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") not in _PATHS:
            return await self.app(scope, receive, send)

        async def reject(status, detail):
            body = json.dumps({"detail": detail}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"cache-control", b"no-store"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        lengths = [
            v for k, v in scope.get("headers", []) if k.lower() == b"content-length"
        ]
        if lengths:
            try:
                length = int(lengths[0])
                if length < 0 or len(lengths) != 1:
                    raise ValueError
            except ValueError:
                return await reject(400, "Invalid Content-Length.")
            if length > self.max_bytes:
                return await reject(413, "Diagnostic request body is too large.")
        deadline = time.monotonic() + self.timeout
        chunks, size = [], 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return await reject(408, "Diagnostic upload timed out.")
            try:
                message = await asyncio.wait_for(receive(), remaining)
            except TimeoutError:
                return await reject(408, "Diagnostic upload timed out.")
            if deadline - time.monotonic() <= 0:
                return await reject(408, "Diagnostic upload timed out.")
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                return await reject(413, "Diagnostic request body is too large.")
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        chunks.clear()
        replayed = False

        async def bounded_receive():
            nonlocal replayed, body
            if not replayed:
                replayed = True
                saved, body = body, b""
                return {"type": "http.request", "body": saved, "more_body": False}
            return await receive()

        return await self.app(scope, bounded_receive, send)
