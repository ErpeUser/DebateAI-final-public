"""Local-only calibration mechanics, with supervised cancellation semantics.

Factory injection is a normal dependency boundary: the router binds it to the
existing LocalTranscriber with German language and downloads disabled.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.services.calibration_metrics import percentile, score_transcript


class CalibrationBusy(RuntimeError):
    pass


class SingleFlight:
    """Keep a job reserved until it really finishes, even when its waiter leaves.

    A timeout/cancel is NOT permission to start overlapping native inference.
    The job receives a cooperative stop flag, checked between native calls.
    A wedged native runtime stays visibly busy until process restart.
    """
    def __init__(self):
        self._task: asyncio.Task | None = None

    @property
    def busy(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run(self, work: Callable[[asyncio.Event], Awaitable[Any]], *, timeout: float = 180):
        if self.busy:
            raise CalibrationBusy('A diagnostic job is still running or draining.')
        stop = asyncio.Event()
        task = asyncio.create_task(work(stop))
        self._task = task

        def consume(completed):
            if not completed.cancelled():
                completed.exception()  # consume abandoned failures, never log sensitive inputs
            if self._task is completed:
                self._task = None
        task.add_done_callback(consume)
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout)
        except (asyncio.CancelledError, TimeoutError):
            stop.set()
            raise


async def compare_asr(
    pcm: bytes, reference: str, model_ids: list[str], repeats: int,
    make_transcriber: Callable[[str], Any], *, stop: asyncio.Event | None = None,
) -> dict:
    if not 1 <= repeats <= 3 or not 1 <= len(model_ids) <= 3 or len(set(model_ids)) != len(model_ids):
        raise ValueError('Select one to three distinct models and one to three repetitions.')
    if not pcm or len(pcm) % 2 or len(pcm) > 30 * 32000:
        raise ValueError('Expected at most 30 seconds of aligned PCM16 audio.')
    score_transcript(reference, '')  # validate before model execution
    seconds = len(pcm) / 32000
    results = []
    failed = 0
    for model_id in model_ids:
        if stop and stop.is_set():
            raise asyncio.CancelledError
        trials = []
        start = time.perf_counter()
        try:
            transcriber = make_transcriber(model_id)
            await transcriber.transcribe_segment(pcm)
            warmup = time.perf_counter() - start
            init_error = None
        except Exception:
            transcriber, warmup, init_error = None, None, 'model_initialization_failed'
        for _ in range(repeats):
            if stop and stop.is_set():
                raise asyncio.CancelledError
            if init_error:
                trial = {'status': 'failed', 'reason': init_error, 'text': None, 'seconds': None}
            else:
                start = time.perf_counter()
                try:
                    text = await transcriber.transcribe_segment(pcm)
                    elapsed = time.perf_counter() - start
                    text = text if isinstance(text, str) else ''
                    metrics = await asyncio.to_thread(score_transcript, reference, text)
                    empty_speech = bool(reference.strip()) and not text.strip()
                    trial = {
                        'status': 'failed' if empty_speech else 'ok',
                        'reason': 'no_transcript' if empty_speech else '',
                        'text': text, 'seconds': elapsed, 'real_time_factor': elapsed / seconds,
                        'metrics': metrics,
                    }
                except Exception:
                    trial = {'status': 'failed', 'reason': 'transcription_failed', 'text': None, 'seconds': None}
            failed += trial['status'] != 'ok'
            trials.append(trial)
        latencies = [t['seconds'] for t in trials if t['status'] == 'ok']
        results.append({
            'model_id': model_id, 'warmup_seconds': warmup, 'trials': trials,
            'latency_p50_seconds': percentile(latencies, .5),
            'latency_p95_seconds': percentile(latencies, .95),
            'successful_trials': len(latencies),
        })
    return {
        'schema_version': 1, 'kind': 'offline_clip_asr', 'language': 'de',
        'reference': reference, 'reference_sha256': hashlib.sha256(reference.encode()).hexdigest(),
        'audio_sha256': hashlib.sha256(pcm).hexdigest(), 'audio_seconds': seconds,
        'models': results, 'attempted_trials': len(model_ids) * repeats, 'failed_trials': failed,
        'settings_changed': False, 'audio_persisted': False,
        'limitations': ['Not a streaming or dual-track latency test.',
                        'Percentiles are descriptive; one to three trials cannot establish a reliable tail latency.',
                        'Silence may be filtered by the existing energy gate before inference.'],
    }
