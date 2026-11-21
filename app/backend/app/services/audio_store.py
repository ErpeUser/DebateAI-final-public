"""Per-call-segment WAV persistence for raw PCM16 16kHz mono call audio.

Enables playback and re-transcription after the call. The WAV header is
written up front with placeholder sizes and patched on close, so a crashed
call leaves a file readable by tools that tolerate oversized declared sizes.
"""

import json
import logging
import os
import stat
import struct
import tempfile
import uuid
from pathlib import Path

from app.services.audio_utils import make_wav_header
from app.services.secrets import data_dir

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
WAV_HEADER_BYTES = 44


def audio_file_path(
    session_id: uuid.UUID | str, segment_number: int, track: str = "mixed"
) -> Path:
    suffix = "" if track == "mixed" else f"_{track}"
    return (
        data_dir() / "audio" / str(session_id) / f"segment_{segment_number}{suffix}.wav"
    )


def repair_wav_file(path: Path) -> bool:
    """Repair the size fields of a crash-surviving PCM WAV, if valid.

    Writers fsync each PCM append, but a process crash can happen before
    ``close`` patches RIFF/data sizes. Recovery trusts only the bytes physically
    present after a complete 44-byte PCM header; malformed or truncated files
    remain unlinked and are reported to the startup log.
    """
    try:
        original = path.lstat()
        if not stat.S_ISREG(original.st_mode) or original.st_size < WAV_HEADER_BYTES:
            return False
        with path.open("r+b") as source:
            current = os.fstat(source.fileno())
            if (original.st_dev, original.st_ino) != (current.st_dev, current.st_ino):
                return False
            header = source.read(WAV_HEADER_BYTES)
            expected = make_wav_header(b"", SAMPLE_RATE)
            # Only this writer's fixed PCM16/mono/16-kHz layout is repairable.
            # General WAVs may contain extra chunks at these byte offsets.
            if (
                len(header) != WAV_HEADER_BYTES
                or header[:4] != expected[:4]
                or header[8:40] != expected[8:40]
            ):
                return False
            pcm_bytes = current.st_size - WAV_HEADER_BYTES
            if pcm_bytes < 0 or pcm_bytes % 2:
                return False
            # Validate both sizes before touching either field (RIFF is uint32).
            riff_size = struct.pack("<I", 36 + pcm_bytes)
            data_size = struct.pack("<I", pcm_bytes)
            source.seek(4)
            source.write(riff_size)
            source.seek(40)
            source.write(data_size)
            source.flush()
            os.fsync(source.fileno())
        return True
    except (OSError, struct.error):
        return False


def _quarantine_orphan_track_audio(path: Path, root: Path) -> None:
    """Preserve unindexed bytes; absence from the database is not deletion consent."""
    current = path
    while current != root:
        if current == current.parent or current.is_symlink() or current.is_junction():
            raise OSError(
                "Audio recovery path traverses a link or leaves the data root"
            )
        current = current.parent
    original = path.lstat()
    if not stat.S_ISREG(original.st_mode):
        raise OSError("Only regular auxiliary archives can be preserved")
    recovery = root / "audio-recovery"
    if (
        recovery.is_symlink()
        or recovery.is_junction()
        or not recovery.resolve().is_relative_to(root.resolve())
    ):
        raise OSError("Recovery directory escapes the data directory")
    recovery.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="orphan-", dir=recovery))
    observed = path.lstat()
    if (observed.st_dev, observed.st_ino) != (original.st_dev, original.st_ino):
        raise OSError("Audio archive identity changed before preservation")
    destination = folder / "archive.wav"
    path.rename(destination)
    # Metadata failure still leaves the original bytes in the recovery folder.
    with destination.with_suffix(".json").open("x", encoding="utf-8") as metadata:
        json.dump(
            {
                "status": "orphan_unverified",
                "original_path": path.relative_to(root).as_posix(),
                "confirmed_pcm_bytes": None,
            },
            metadata,
        )
        metadata.flush()
        os.fsync(metadata.fileno())


def cleanup_orphan_track_audio(referenced_paths: set[str]) -> int:
    """Move unreferenced auxiliary archives to recovery; never silently erase them."""
    root = data_dir()
    audio_root = root / "audio"
    referenced = {Path(path).as_posix() for path in referenced_paths}
    preserved = 0
    for pattern in ("*_mic.wav", "*_sys.wav"):
        for path in audio_root.rglob(pattern) if audio_root.exists() else ():
            if path.relative_to(root).as_posix() in referenced:
                continue
            try:
                _quarantine_orphan_track_audio(path, root)
            except OSError:
                logger.exception(
                    "Auxiliary archive retained after recovery error: %s", path
                )
            else:
                preserved += 1
    return preserved


class SegmentAudioWriter:
    def __init__(
        self, session_id: uuid.UUID | str, segment_number: int, track: str = "mixed"
    ):
        self._path = audio_file_path(session_id, segment_number, track)
        self._file = None
        self._bytes_written = 0
        self._closed = False
        self._archive_identity = None
        self._quarantine_path = None

    def append(self, pcm_bytes: bytes):
        if self._closed:
            raise RuntimeError("Cannot append to a finalized audio archive")
        if self._file is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self._path, "xb")
            owned = os.fstat(self._file.fileno())
            self._archive_identity = (owned.st_dev, owned.st_ino)
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
        self._closed = True
        if self._file is None:
            return None
        source, self._file = self._file, None
        try:
            # RIFF chunk size at offset 4, data chunk size at offset 40.
            riff_size = struct.pack("<I", 36 + self._bytes_written)
            data_size = struct.pack("<I", self._bytes_written)
            source.seek(4)
            source.write(riff_size)
            source.seek(40)
            source.write(data_size)
            source.flush()
            os.fsync(source.fileno())
        finally:
            # Even a finalization failure must release the descriptor. Keep the
            # file for recovery; never reopen it with truncating write mode.
            source.close()
        rel = self._path.relative_to(data_dir())
        logger.info(f"Saved segment audio: {rel} ({self._bytes_written} bytes)")
        return str(rel)

    def quarantine_failed_archive(self) -> str | None:
        """Preserve owned bytes without advertising an incomplete archive as valid.

        Recovery candidates live outside audio/, where auxiliary orphan cleanup
        runs. No original is deleted and a writer that lost exclusive creation
        can never move another writer's archive. Metadata records only the
        confirmed byte count, not a fabricated complete recording.
        """
        if self._quarantine_path is not None:
            return self._quarantine_path
        try:
            self.close()
        except Exception:
            logger.warning(
                "Failed archive could not be finalized; preserving raw bytes",
                exc_info=True,
            )
        if self._archive_identity is None or not self._path.exists():
            return None
        original = self._path.lstat()
        if (
            not stat.S_ISREG(original.st_mode)
            or (original.st_dev, original.st_ino) != self._archive_identity
        ):
            raise OSError("Archive ownership changed; refusing to move it")
        root = data_dir()
        recovery_root = root / "audio-recovery"
        if recovery_root.is_symlink() or not recovery_root.resolve().is_relative_to(
            root.resolve()
        ):
            raise OSError("Recovery directory escapes the data directory")
        recovery_root.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix="segment-", dir=recovery_root))
        destination = folder / "archive.wav"
        original_path = self._path.relative_to(root).as_posix()
        self._path.rename(destination)
        self._quarantine_path = destination.relative_to(root).as_posix()
        with destination.with_suffix(".json").open("x", encoding="utf-8") as metadata:
            json.dump(
                {
                    "status": "incomplete_not_accepted",
                    "original_path": original_path,
                    "confirmed_pcm_bytes": self._bytes_written,
                },
                metadata,
            )
        return self._quarantine_path
