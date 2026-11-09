"""Per-call-segment WAV persistence for raw PCM16 16kHz mono call audio.

Enables playback and re-transcription after the call. The WAV header is
written up front with placeholder sizes and patched on close, so a crashed
call leaves a file readable by tools that tolerate oversized declared sizes.
"""

import logging
import os
import struct
import uuid
from pathlib import Path

from app.services.audio_utils import make_wav_header
from app.services.secrets import data_dir

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
WAV_HEADER_BYTES = 44


def audio_file_path(session_id: uuid.UUID | str, segment_number: int, track: str = "mixed") -> Path:
    suffix = "" if track == "mixed" else f"_{track}"
    return data_dir() / "audio" / str(session_id) / f"segment_{segment_number}{suffix}.wav"


def repair_wav_file(path: Path) -> bool:
    """Repair the size fields of a crash-surviving PCM WAV, if valid.

    Writers fsync each PCM append, but a process crash can happen before
    ``close`` patches RIFF/data sizes. Recovery trusts only the bytes physically
    present after a complete 44-byte PCM header; malformed or truncated files
    remain unlinked and are reported to the startup log.
    """
    try:
        if path.stat().st_size < WAV_HEADER_BYTES:
            return False
        with path.open("r+b") as source:
            header = source.read(WAV_HEADER_BYTES)
            if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                return False
            pcm_bytes = path.stat().st_size - WAV_HEADER_BYTES
            source.seek(4)
            source.write(struct.pack("<I", 36 + pcm_bytes))
            source.seek(40)
            source.write(struct.pack("<I", pcm_bytes))
            source.flush()
            os.fsync(source.fileno())
        return True
    except (OSError, struct.error):
        return False


def cleanup_orphan_track_audio(referenced_paths: set[str]) -> int:
    """Remove auxiliary track WAVs left unreferenced by an interrupted call."""
    root = data_dir()
    audio_root = root / "audio"
    referenced = {Path(path).as_posix() for path in referenced_paths}
    removed = 0
    for pattern in ("*_mic.wav", "*_sys.wav"):
        for path in audio_root.rglob(pattern) if audio_root.exists() else ():
            if path.relative_to(root).as_posix() in referenced:
                continue
            path.unlink(missing_ok=True)
            removed += 1
    return removed


class SegmentAudioWriter:
    def __init__(self, session_id: uuid.UUID | str, segment_number: int, track: str = "mixed"):
        self._path = audio_file_path(session_id, segment_number, track)
        self._file = None
        self._bytes_written = 0

    def append(self, pcm_bytes: bytes):
        if self._file is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self._path, "wb")
            self._file.write(make_wav_header(b"", SAMPLE_RATE))
        self._file.write(pcm_bytes)
        # The ingress status is sent only after this append returns. Flush the
        # user-enabled archive to the OS and force it to stable storage so an
        # ACK cannot claim durable audio while it is still only in a process
        # buffer. The database index is committed separately at segment close.
        self._file.flush()
        os.fsync(self._file.fileno())
        self._bytes_written += len(pcm_bytes)

    def pcm_chunks(self, chunk_size: int = 1024 * 1024):
        """Yield the PCM written so far without closing the active WAV."""
        if self._file is None:
            return
        self._file.flush()
        with self._path.open("rb") as source:
            source.seek(WAV_HEADER_BYTES)
            while chunk := source.read(chunk_size):
                yield chunk

    def close(self) -> str | None:
        """Finalize sizes in the header. Returns the path relative to DATA_DIR, or None if no audio."""
        if self._file is None:
            return None
        # RIFF chunk size at offset 4, data chunk size at offset 40
        self._file.seek(4)
        self._file.write(struct.pack("<I", 36 + self._bytes_written))
        self._file.seek(40)
        self._file.write(struct.pack("<I", self._bytes_written))
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()
        self._file = None
        rel = self._path.relative_to(data_dir())
        logger.info(f"Saved segment audio: {rel} ({self._bytes_written} bytes)")
        return str(rel)
