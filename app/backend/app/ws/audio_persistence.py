import asyncio
import logging
from typing import Any

from app.services.audio_store import SegmentAudioWriter
from app.services.diarizer_selection import flush_diarizer_segments
from app.services.ordered_transcription import OrderedTranscriptionQueue
from app.services.secrets import data_dir

logger = logging.getLogger("app.ws.audio_handler")


async def _flush_remaining_audio(
    diarizer: Any,
    transcription_queue: OrderedTranscriptionQueue,
    speaker_prefix: str = "",
) -> None:
    for segment in await asyncio.to_thread(flush_diarizer_segments, diarizer):
        try:
            transcription_queue.add(
                f"{speaker_prefix}{segment.speaker_id}",
                segment.pcm_bytes,
            )
        except Exception:
            pass


def _preserve_failed_archive(writer: SegmentAudioWriter, track: str) -> None:
    try:
        path = writer.quarantine_failed_archive()
        if isinstance(path, str):
            logger.warning(
                "Preserved incomplete %s archive for recovery: %s", track, path
            )
    except Exception:
        # Never unlink previously confirmed audio just because preservation
        # itself failed. Keep the original and report the recovery failure.
        logger.exception(
            "Could not quarantine failed %s archive; original was not deleted", track
        )


def _close_audio_writers(
    audio_writers: dict[str, SegmentAudioWriter | None],
    split_track_established: bool,
) -> dict[str, str | None]:
    paths: dict[str, str | None] = {}
    for track, writer in audio_writers.items():
        try:
            paths[track] = writer.close() if writer else None
        except Exception as exc:
            logger.warning("Failed to finalize %s segment audio: %s", track, exc)
            if writer is not None:
                _preserve_failed_archive(writer, track)
            paths[track] = None
    # Auxiliary copies are redundant only when a finalized mixed archive exists.
    # A mixed-write failure must not delete the last valid microphone/system data.
    if not split_track_established and paths["mixed"]:
        for path in (paths["mic"], paths["system"]):
            if path:
                (data_dir() / path).unlink(missing_ok=True)
        paths["mic"] = paths["system"] = None
    return {
        "audio_path": paths["mixed"],
        "mic_audio_path": paths["mic"],
        "system_audio_path": paths["system"],
    }


def _append_audio_frames(
    audio_writers: dict[str, SegmentAudioWriter | None],
    frames: tuple[bytes, bytes, bytes],
    split_track_established: bool = True,
) -> None:
    for track, pcm in zip(("mixed", "mic", "system"), frames):
        writer = audio_writers[track]
        if not writer:
            continue
        try:
            writer.append(pcm)
        except Exception as exc:
            logger.warning("Disabling %s segment audio persistence: %s", track, exc)
            try:
                writer.close()
            except Exception:
                pass
            _preserve_failed_archive(writer, track)
            audio_writers[track] = None
