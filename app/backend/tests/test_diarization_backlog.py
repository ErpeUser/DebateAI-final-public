"""The diarization backlog stops before accepting audio it cannot retain."""

import asyncio
import unittest
from collections import deque

from app.ws.audio_runtime import (
    MAX_DIARIZATION_BACKLOG_BYTES,
    _PCM_BYTES_PER_SECOND,
    _QueuedAudioFrame,
    _shed_diarization_backlog,
)


def _frame(seconds: float = 1.0, track: int = 0, at: float = 0.0) -> _QueuedAudioFrame:
    return _QueuedAudioFrame(
        track=track,
        pcm_bytes=b"\x00" * int(seconds * _PCM_BYTES_PER_SECOND),
        split_track_established=False,
        enqueued_at=at,
    )


def _fill(queue, pending, frames):
    buffered = 0
    for frame in frames:
        queue.put_nowait(frame)
        pending.append(0.0)
        buffered += len(frame.pcm_bytes)
    return buffered


class DiarizationBacklogTests(unittest.TestCase):
    def setUp(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.pending: deque[float] = deque()

    def test_under_the_cap_is_not_an_overflow(self):
        buffered = _fill(self.queue, self.pending, [_frame(1.0) for _ in range(5)])
        result, overflowed = _shed_diarization_backlog(self.queue, self.pending, buffered)
        self.assertEqual(buffered, result)
        self.assertFalse(overflowed)
        self.assertEqual(5, self.queue.qsize())

    def test_overflow_is_reported_without_removing_accepted_audio(self):
        # A queued frame is already accepted by the audio pipeline. The
        # overload contract may reject a later frame and stop recording, but it
        # must never remove an earlier PCM frame that the final path needs.
        frames = [_frame(1.0, at=float(i)) for i in range(5)]
        buffered = _fill(self.queue, self.pending, frames)
        result, overflowed = _shed_diarization_backlog(
            self.queue, self.pending, buffered, limit_bytes=3 * _PCM_BYTES_PER_SECOND
        )
        self.assertEqual(buffered, result)
        self.assertTrue(overflowed)
        self.assertEqual(5, self.queue.qsize())
        self.assertEqual(5, len(self.pending))
        remaining = []
        while not self.queue.empty():
            remaining.append(self.queue.get_nowait())
        self.assertEqual([0.0, 1.0, 2.0, 3.0, 4.0], [f.enqueued_at for f in remaining])

    def test_pending_ages_stay_in_step_with_the_queue(self):
        _fill(self.queue, self.pending, [_frame(1.0) for _ in range(40)])
        _, overflowed = _shed_diarization_backlog(
            self.queue, self.pending, MAX_DIARIZATION_BACKLOG_BYTES * 3
        )
        self.assertEqual(self.queue.qsize(), len(self.pending))
        self.assertTrue(overflowed)

    def test_shutdown_sentinel_is_never_discarded(self):
        self.queue.put_nowait(None)
        result, overflowed = _shed_diarization_backlog(
            self.queue, self.pending, MAX_DIARIZATION_BACKLOG_BYTES * 2
        )
        self.assertEqual(MAX_DIARIZATION_BACKLOG_BYTES * 2, result)
        self.assertTrue(overflowed)
        self.assertEqual(1, self.queue.qsize())
        self.assertIsNone(self.queue.get_nowait())

    def test_empty_queue_still_reports_accounted_overflow(self):
        result, overflowed = _shed_diarization_backlog(
            self.queue, self.pending, MAX_DIARIZATION_BACKLOG_BYTES * 5
        )
        self.assertEqual(MAX_DIARIZATION_BACKLOG_BYTES * 5, result)
        self.assertTrue(overflowed)

    def test_cap_is_a_sane_fraction_of_process_memory(self):
        self.assertLessEqual(MAX_DIARIZATION_BACKLOG_BYTES, 4 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
