import asyncio
import json
import logging
import uuid
from collections import deque
from collections.abc import Callable
from time import monotonic
from typing import Any, Awaitable

from fastapi import WebSocket

from app.services.pii import shield
from app.database import async_session
from app.models import Directive
from app.services.agents.activity import ActivityRegistry
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.audio_store import SegmentAudioWriter
from app.ws.audio_persistence import _append_audio_frames
from app.ws.audio_runtime import (
    MAX_DIARIZATION_BACKLOG_BYTES,
    _PCM_BYTES_PER_SECOND,
    _QueuedAudioFrame,
    _decode_audio_frame,
    _record_audio_flow,
    _send_gateway_audio,
    _shed_diarization_backlog,
    _send_status,
    _split_track_established_after_frame,
    _split_track_established_after_message,
)

logger = logging.getLogger("app.ws.audio_handler")

MAX_CONTROL_MESSAGE_CHARS = 16_384
MAX_DIRECTIVE_CHARS = 2_000
_CONTROL_TYPES = {
    "stop",
    "track_state",
    "directive",
    "debate_research",
    "debate_research_control",
    "debate_analysis_cancel",
    "debate_update_ack",
    "debate_answer_good",
    "debate_learning_revoke",
}


async def _handle_audio_frame(
    raw_frame: bytes,
    websocket: WebSocket,
    orchestrator: AgentOrchestrator,
    mixer: Any,
    audio_writers: dict[str, SegmentAudioWriter | None] | None,
    queue: asyncio.Queue[_QueuedAudioFrame | None],
    pending_enqueued_at: deque[float],
    state: Any,
    frame_metadata: dict[str, Any] | None = None,
    gateway_queue: asyncio.Queue[bytes | None] | None = None,
) -> bool:
    try:
        track, pcm_data = _decode_audio_frame(raw_frame)
    except (TypeError, ValueError) as exc:
        await _send_status(
            websocket,
            "audio_error",
            "One audio frame was rejected as malformed.",
            details={"error": str(exc)[:200]},
        )
        return False
    try:
        metadata = frame_metadata or {}
        origin = str(metadata.get("origin") or "browser")[:20]
        sample_rate = int(metadata.get("sample_rate") or 16000)
        if sample_rate != 16000:
            raise ValueError("Live audio must be PCM16 mono at 16 kHz")
        prospective_backlog = state.diarization_backlog_bytes + len(pcm_data)
        state.diarization_backlog_bytes, overflowed = _shed_diarization_backlog(
            queue,
            pending_enqueued_at,
            prospective_backlog,
        )
        if overflowed:
            state.stopped = True
            state.stop_drain_mode = "full"
            state.diarization_overload_notified = True
            await _send_status(
                websocket,
                "diarization_overflow",
                (
                    "Speaker processing reached its bounded audio buffer. "
                    "Recording was stopped; the rejected frame was not reported "
                    "as captured audio and all accepted PCM will be drained."
                ),
                details={
                    "buffered_bytes": state.diarization_backlog_bytes,
                    "max_backlog_bytes": MAX_DIARIZATION_BACKLOG_BYTES,
                    "rejected_bytes": len(pcm_data),
                    "frames_dropped": 0,
                },
            )
            return False
        if queue.full():
            state.stopped = True
            state.stop_drain_mode = "full"
            state.diarization_overload_notified = True
            await _send_status(
                websocket,
                "diarization_overflow",
                (
                    "Speaker processing reached its bounded frame buffer. "
                    "Recording was stopped; the rejected frame was not reported "
                    "as captured audio and all accepted PCM will be drained."
                ),
                details={
                    "buffered_bytes": state.diarization_backlog_bytes,
                    "max_backlog_bytes": MAX_DIARIZATION_BACKLOG_BYTES,
                    "rejected_bytes": len(pcm_data),
                    "frames_dropped": 0,
                    "queue_limit_reached": True,
                },
            )
            return False
        sample_counter = state.audio_sample_counters[track]
        state.audio_sample_counters[track] += len(pcm_data) // 2
        captured_at_ms = int(metadata.get("captured_at_ms") or round(monotonic() * 1000))
        device_id = str(metadata.get("device_id") or f"{origin}-track-{track}")[:160]
        state.audio_chunks_received += 1
        state.audio_bytes_received += len(pcm_data)
        now = monotonic()
        raw_level = metadata.get("level")
        if origin == "native" and isinstance(raw_level, (int, float)):
            levels = getattr(state, "audio_levels", [0.0, 0.0])
            last_levels = getattr(state, "last_audio_level_at", [0.0, 0.0])
            levels[track] = max(0.0, min(1.0, float(raw_level)))
            state.audio_levels = levels
            if now - last_levels[track] >= 0.1:
                last_levels[track] = now
                state.last_audio_level_at = last_levels
                await websocket.send_json({
                    "type": "audio_level",
                    "data": {
                        "track": track,
                        "level": levels[track],
                    },
                })
        audio_status_due = now - state.last_audio_status_at >= 5
        if audio_status_due:
            state.last_audio_status_at = now

        mixed_frames = mixer.add(track, pcm_data)
        if mixed_frames:
            mixed, mic, system = mixed_frames
            if audio_writers:
                _append_audio_frames(
                    audio_writers,
                    (mixed, mic, system),
                    state.split_track_established,
                )

        state.split_track_established = _split_track_established_after_frame(
            track,
            state.split_track_established,
        )
        enqueued_at = monotonic()
        pending_enqueued_at.append(enqueued_at)
        queue.put_nowait(
            _QueuedAudioFrame(
                track=track,
                pcm_bytes=pcm_data,
                split_track_established=state.split_track_established,
                enqueued_at=enqueued_at,
                origin=origin,
                sample_rate=sample_rate,
                sample_counter=sample_counter,
                captured_at_ms=captured_at_ms,
                device_id=device_id,
            )
        )
        if isinstance(getattr(orchestrator, "activity", None), ActivityRegistry):
            await orchestrator.activity.update_call(
                diarization={
                    "queued": max(0, len(pending_enqueued_at)),
                    "shed": state.diarization_frames_dropped,
                }
            )
        if mixed_frames and state.gateway_available:
            if gateway_queue is None:
                state.gateway_available = await _send_gateway_audio(
                    orchestrator,
                    mixed,
                )
            else:
                try:
                    gateway_queue.put_nowait(mixed)
                except asyncio.QueueFull:
                    state.gateway_frames_dropped += 1
                    if not state.gateway_overload_notified:
                        state.gateway_overload_notified = True
                        await _send_status(
                            websocket,
                            "audio_gateway_overflow",
                            (
                                "Die Live-Zwischentranskription ist ueberlastet. "
                                "Die Batch-Transkription laeuft weiter; einzelne "
                                "Zwischenframes wurden verworfen."
                            ),
                            details={
                                "frames_dropped": state.gateway_frames_dropped,
                                "queue_limit": gateway_queue.maxsize,
                            },
                        )
        audio_flow = _record_audio_flow(
            state.audio_bytes_by_track,
            track,
            len(pcm_data),
        )
        if audio_flow:
            mic_seconds, system_seconds = audio_flow
            logger.info(
                (
                    "Audio ingress: mic=%.1fs system=%.1fs "
                    "aggregate_track_seconds=%.1fs backlog=%s"
                ),
                mic_seconds,
                system_seconds,
                mic_seconds + system_seconds,
                len(pending_enqueued_at),
            )
        if audio_status_due:
            await _send_status(
                websocket,
                "audio_received",
                (
                    f"Backend received "
                    f"{state.audio_bytes_received // _PCM_BYTES_PER_SECOND}s "
                    f"audio ({state.audio_chunks_received} chunks)"
                ),
                details={
                    "chunks": state.audio_chunks_received,
                    "bytes": state.audio_bytes_received,
                    "seconds": (
                        state.audio_bytes_received / _PCM_BYTES_PER_SECOND
                    ),
                    "track": track,
                    "origin": origin,
                    "sample_rate": sample_rate,
                    "sample_counter": sample_counter,
                    "device_id": device_id,
                },
            )
        return True
    except Exception as exc:
        logger.exception("Audio frame handling failed")
        await _send_status(
            websocket,
            "audio_error",
            f"One audio frame could not be processed: {exc}",
            details={"track": track},
        )
        return False


async def _handle_text_message(
    raw_message: str,
    session_id: uuid.UUID,
    orchestrator: AgentOrchestrator,
    state: Any,
    requested_drain_mode: Callable[[dict], str],
    on_system_track_stopped: Callable[[], Awaitable[None]] | None = None,
) -> None:
    if len(raw_message) > MAX_CONTROL_MESSAGE_CHARS:
        raise ValueError("WebSocket control message is too large")
    data = json.loads(raw_message)
    if not isinstance(data, dict) or data.get("type") not in _CONTROL_TYPES:
        raise ValueError("Unsupported WebSocket control message")
    state.split_track_established = _split_track_established_after_message(
        data,
        state.split_track_established,
    )
    if (
        data.get("type") == "track_state"
        and data.get("track") == 1
        and data.get("active") is False
        and on_system_track_stopped is not None
    ):
        # The share ended here, so this is where that track's buffered audio
        # gets its answer. split_track_established deliberately stays set: it is
        # a topology fact for the rest of the call (ALP-103), not a live-capture
        # flag.
        await on_system_track_stopped()
    if data.get("type") == "stop":
        state.stopped = True
        state.stop_drain_mode = requested_drain_mode(data)
    elif data.get("type") == "directive":
        directive_text = str(data.get("text", ""))[:MAX_DIRECTIVE_CHARS].strip()
        if directive_text:
            async with async_session() as db:
                directive_text = await shield.protect_text(db, session_id, directive_text)
                directive = Directive(session_id=session_id, text=directive_text)
                db.add(directive)
                await db.commit()
            await orchestrator.send_directive(directive_text)
    elif data.get("type") == "debate_research":
        await orchestrator.request_debate_research(str(data.get("category", "")))
    elif data.get("type") == "debate_research_control":
        await orchestrator.update_debate_research(bool(data.get("enabled")))
    elif data.get("type") == "debate_analysis_cancel":
        await orchestrator.cancel_manual_debate_analysis()
    elif data.get("type") == "debate_update_ack":
        orchestrator.acknowledge_debate_update(
            claim_id=str(data.get("claim_id") or ""),
            recommendation_revision=int(data.get("recommendation_revision") or 0),
        )
    elif data.get("type") == "debate_answer_good":
        await orchestrator.confirm_good_debate_answer(
            claim_id=str(data.get("claim_id") or ""),
            recommendation_revision=int(data.get("recommendation_revision") or 0),
        )
    elif data.get("type") == "debate_learning_revoke":
        await orchestrator.revoke_good_debate_answer(
            example_id=str(data.get("example_id") or "")[:80],
            correction=str(data.get("correction") or "")[:700],
        )
