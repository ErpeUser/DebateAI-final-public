"""Bounded-retention stress checks for the process-local replay registries."""

import unittest
import uuid

from app.services import transcription_jobs, ws_event_stream
from app.services.transcription_jobs import TranscriptionJob
from app.services.ws_event_stream import SessionEventJournal


class ProcessLocalRetentionStressTests(unittest.TestCase):
    def tearDown(self):
        ws_event_stream._journals.clear()
        transcription_jobs._jobs.clear()

    def test_ten_thousand_idle_journals_are_released_by_ttl(self):
        for index in range(10_000):
            journal = SessionEventJournal(
                f"stress-{index}", max_events=1, max_state_events=1, max_bytes=1024
            )
            journal._last_touch = 0
            ws_event_stream._journals[journal.session_id] = journal

        removed = ws_event_stream.sweep_idle_journals(
            now=10_000, idle_ttl_seconds=60
        )

        self.assertEqual(10_000, removed)
        self.assertEqual({}, ws_event_stream._journals)

    def test_ten_thousand_terminal_jobs_are_released_by_ttl(self):
        for _ in range(10_000):
            job = TranscriptionJob(
                session_id=uuid.uuid4(),
                kind="audio_import",
                model_id="test",
                total_segments=1,
                status="completed",
            )
            job._finished_at = 0
            transcription_jobs._jobs[job.session_id] = job

        removed = transcription_jobs.sweep_jobs(now=10_000, terminal_ttl_seconds=60)

        self.assertEqual(10_000, removed)
        self.assertEqual({}, transcription_jobs._jobs)


if __name__ == "__main__":
    unittest.main()
