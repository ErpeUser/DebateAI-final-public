"""In-process bridge from native Windows capture into the live WebSocket pipeline."""

from __future__ import annotations

import asyncio
import json
import uuid

_PCM_BYTES_PER_SECOND_PER_TRACK = 16_000 * 2
_BUFFER_SECONDS = 2
_TRACKS = 2
_MAX_BUFFERED_PCM_BYTES = _PCM_BYTES_PER_SECOND_PER_TRACK * _BUFFER_SECONDS * _TRACKS


def _pcm_bytes(message: dict) -> int:
    raw = message.get("bytes")
    return max(0, len(raw) - 1) if isinstance(raw, (bytes, bytearray)) else 0


class NativeAudioQueue(asyncio.Queue[dict]):
    """Queue with a PCM byte budget derived from format, duration and tracks."""

    def __init__(self, *, max_audio_bytes: int = _MAX_BUFFERED_PCM_BYTES):
        super().__init__()
        self.max_audio_bytes = max_audio_bytes
        self.queued_audio_bytes = 0
        self.overflow_signaled = False

    def put_nowait(self, item: dict) -> None:
        super().put_nowait(item)
        self.queued_audio_bytes += _pcm_bytes(item)

    def get_nowait(self) -> dict:
        item = super().get_nowait()
        self.queued_audio_bytes = max(0, self.queued_audio_bytes - _pcm_bytes(item))
        return item


_QUEUES: dict[str, NativeAudioQueue] = {}


def register_native_audio_session(session_id: uuid.UUID | str) -> NativeAudioQueue:
    queue = NativeAudioQueue()
    _QUEUES[str(session_id)] = queue
    return queue


def unregister_native_audio_session(
    session_id: uuid.UUID | str,
    queue: asyncio.Queue[dict],
) -> None:
    key = str(session_id)
    if _QUEUES.get(key) is queue:
        _QUEUES.pop(key, None)


def native_audio_queue(session_id: uuid.UUID | str) -> asyncio.Queue[dict] | None:
    return _QUEUES.get(str(session_id))


def enqueue_native_message(queue: asyncio.Queue[dict], message: dict) -> bool:
    """Queue one callback message without silently discarding accepted PCM."""
    pcm_bytes = _pcm_bytes(message)
    if isinstance(queue, NativeAudioQueue) and pcm_bytes:
        if queue.overflow_signaled:
            return False
        if queue.queued_audio_bytes + pcm_bytes > queue.max_audio_bytes:
            queue.overflow_signaled = True
            queue.put_nowait(
                {
                    "native_overflow": {
                        "state": "native_audio_overflow",
                        "max_audio_bytes": queue.max_audio_bytes,
                        "queued_audio_bytes": queue.queued_audio_bytes,
                        "rejected_audio_bytes": pcm_bytes,
                    },
                    "text": json.dumps(
                        {
                            "type": "stop",
                            "drain_mode": "full",
                            "reason": "native_audio_overflow",
                        }
                    ),
                }
            )
            return False
    elif queue.full():
        return False
    queue.put_nowait(message)
    return True
