"""Ordered transcription queue for diarized audio segments."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TranscribeFn = Callable[[bytes], Awaitable[str | None]]
EmitFn = Callable[[str, bytes, str], Awaitable[None]]
# Called with the cumulative failure count and the failure kind:
# "transcribe" (provider/model/timeout) or "emit" (persisting the transcript).
FailureFn = Callable[[int, str], Awaitable[None]]


@dataclass(frozen=True)
class TranscriptionResult:
    speaker_auto_id: str
    pcm_bytes: bytes
    text: str | None


class OrderedTranscriptionQueue:
    """Run transcriptions with bounded concurrency and emit results in input order."""

    def __init__(
        self,
        transcribe: TranscribeFn,
        emit: EmitFn,
        max_concurrency: int = 3,
        transcribe_timeout_seconds: float | None = 90.0,
        emit_timeout_seconds: float | None = 60.0,
        on_failure: FailureFn | None = None,
        min_batch_bytes: int = 0,
        max_batch_wait_seconds: float = 0.0,
    ):
        self._transcribe = transcribe
        self._emit = emit
        self._transcribe_timeout_seconds = transcribe_timeout_seconds
        self._emit_timeout_seconds = emit_timeout_seconds
        self._on_failure = on_failure
        self._min_batch_bytes = max(0, int(min_batch_bytes))
        self._max_batch_wait_seconds = max(0.0, float(max_batch_wait_seconds))
        self._pending_speaker: str | None = None
        self._pending_audio = bytearray()
        self._pending_flush_handle: asyncio.TimerHandle | None = None
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()
        self._emit_task: asyncio.Task | None = None
        self._results: dict[int, TranscriptionResult] = {}
        self._next_job_index = 0
        self._next_emit_index = 0
        self._closed = False
        self._emitted_count = 0
        self._failed_count = 0

    @property
    def stats(self) -> dict[str, int]:
        """Job accounting: a failure is an error/timeout, not a filtered segment."""
        return {
            "jobs": self._next_job_index,
            "emitted": self._emitted_count,
            "failed": self._failed_count,
        }

    def add(self, speaker_auto_id: str, pcm_bytes: bytes) -> int:
        if self._closed:
            raise RuntimeError("Cannot add transcription job after queue drain")
        if self._min_batch_bytes:
            if self._pending_speaker is not None and self._pending_speaker != speaker_auto_id:
                self._flush_pending()
            if self._pending_speaker is None:
                self._pending_speaker = speaker_auto_id
            self._pending_audio.extend(pcm_bytes)
            if len(self._pending_audio) < self._min_batch_bytes:
                if self._max_batch_wait_seconds and self._pending_flush_handle is None:
                    self._pending_flush_handle = asyncio.get_running_loop().call_later(
                        self._max_batch_wait_seconds,
                        self._flush_pending,
                    )
                return -1
            return self._flush_pending()
        return self._schedule(speaker_auto_id, pcm_bytes)

    def _schedule(self, speaker_auto_id: str, pcm_bytes: bytes) -> int:
        index = self._next_job_index
        self._next_job_index += 1
        task = asyncio.create_task(self._run(index, speaker_auto_id, pcm_bytes))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return index

    def _flush_pending(self) -> int:
        if self._pending_flush_handle is not None:
            self._pending_flush_handle.cancel()
            self._pending_flush_handle = None
        if self._pending_speaker is None or not self._pending_audio:
            return -1
        speaker = self._pending_speaker
        audio = bytes(self._pending_audio)
        self._pending_speaker = None
        self._pending_audio = bytearray()
        return self._schedule(speaker, audio)

    async def add_result(
        self,
        speaker_auto_id: str,
        pcm_bytes: bytes,
        text: str | None,
        *,
        failed: bool = False,
    ) -> int:
        """Queue a transcript produced by a persistent streaming backend."""
        if self._closed:
            raise RuntimeError("Cannot add transcription result after queue drain")
        index = self._next_job_index
        self._next_job_index += 1
        if failed:
            await self._record_failure("transcribe")
        async with self._lock:
            self._results[index] = TranscriptionResult(speaker_auto_id, pcm_bytes, text)
        await self._emit_ready()
        return index

    async def _record_failure(self, kind: str):
        self._failed_count += 1
        if self._on_failure is None:
            return
        try:
            await self._on_failure(self._failed_count, kind)
        except Exception:
            logger.warning("Transcription failure callback raised", exc_info=True)

    async def drain(self):
        self._flush_pending()
        self._closed = True
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
        await self._emit_ready()
        if self._emit_task is not None:
            await self._emit_task

    async def _run(self, index: int, speaker_auto_id: str, pcm_bytes: bytes):
        text = None
        failed = False
        try:
            async with self._semaphore:
                if self._transcribe_timeout_seconds is None:
                    text = await self._transcribe(pcm_bytes)
                else:
                    text = await asyncio.wait_for(
                        self._transcribe(pcm_bytes),
                        timeout=self._transcribe_timeout_seconds,
                    )
        except asyncio.TimeoutError:
            logger.error("Transcription job %s timed out", index)
            failed = True
        except Exception as exc:
            logger.error("Transcription job %s failed: %s", index, exc)
            failed = True

        if failed:
            await self._record_failure("transcribe")
        async with self._lock:
            self._results[index] = TranscriptionResult(speaker_auto_id, pcm_bytes, text)
        await self._emit_ready()

    async def _emit_ready(self):
        async with self._lock:
            if self._emit_task is None or self._emit_task.done():
                self._emit_task = asyncio.create_task(self._emit_ready_loop())

    async def _emit_ready_loop(self):
        """Emit contiguous results without holding the result-ingress lock."""
        while True:
            ready: list[TranscriptionResult] = []
            async with self._lock:
                while self._next_emit_index in self._results:
                    result = self._results.pop(self._next_emit_index)
                    self._next_emit_index += 1
                    if result.text:
                        ready.append(result)
            if not ready:
                return

            emit_failures = 0
            for result in ready:
                try:
                    if self._emit_timeout_seconds is None:
                        await self._emit(result.speaker_auto_id, result.pcm_bytes, result.text)
                    else:
                        await asyncio.wait_for(
                            self._emit(result.speaker_auto_id, result.pcm_bytes, result.text),
                            timeout=self._emit_timeout_seconds,
                        )
                    self._emitted_count += 1
                except asyncio.TimeoutError:
                    logger.error("Ordered transcript emit timed out")
                    emit_failures += 1
                except Exception as exc:
                    logger.error("Ordered transcript emit failed: %s", exc)
                    emit_failures += 1
            for _ in range(emit_failures):
                await self._record_failure("emit")
