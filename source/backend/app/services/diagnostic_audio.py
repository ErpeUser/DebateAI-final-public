"""Small bounded audio uploads; decoding never runs on the asyncio event loop."""
from __future__ import annotations

import asyncio
from pathlib import PurePath

MAX_UPLOAD_BYTES = 16 * 1024 * 1024
SUPPORTED_FORMATS = {'.wav', '.webm', '.ogg', '.mp3', '.m4a', '.flac'}
PCM_BYTES_PER_SECOND = 32000


class AudioInputError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


async def read_encoded_audio(upload) -> tuple[bytes, str]:
    ext = PurePath(upload.filename or '').suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise AudioInputError('Unsupported audio format.')
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise AudioInputError('Audio upload exceeds 16 MiB.', 413)
    if not content:
        raise AudioInputError('Audio upload is empty.')
    return content, ext[1:]


async def decode_audio_clip(content: bytes, source_format: str, decoder, *, min_seconds: float = .5, max_seconds: float = 30) -> bytes:
    try:
        # One extra second detects overlong clips without decoding the entire file.
        pcm = await asyncio.to_thread(decoder, content, source_format, max_seconds=max_seconds + 1)
    except Exception as exc:
        # Decoder errors can contain local paths or full ffmpeg command lines.
        raise AudioInputError('Audio could not be decoded. Use a valid short audio clip.') from exc
    if not isinstance(pcm, bytes) or len(pcm) % 2:
        raise AudioInputError('Decoder did not return aligned PCM16 audio.')
    if len(pcm) < min_seconds * PCM_BYTES_PER_SECOND:
        raise AudioInputError(f'Clip must contain at least {min_seconds:g} seconds of audio.')
    if len(pcm) > max_seconds * PCM_BYTES_PER_SECOND:
        raise AudioInputError(f'Clip exceeds {max_seconds:g} seconds; record a shorter reference.')
    return pcm


async def read_audio_clip(upload, decoder, *, min_seconds: float = .5, max_seconds: float = 30) -> bytes:
    content, source_format = await read_encoded_audio(upload)
    return await decode_audio_clip(content, source_format, decoder, min_seconds=min_seconds, max_seconds=max_seconds)
