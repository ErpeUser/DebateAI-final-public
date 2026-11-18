"""F11 acknowledgement at the real operation-applier/commit boundary.

Only storage and provider I/O are replaced. The cycle, serialization, operation
dispatch and adjustment run unchanged. The transaction double discards pending
edits on failure, so a retry sees the identical input rather than dirty objects.
"""

import asyncio
import copy
import unittest
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models import Question, Session
from app.services import insight_refiner
from app.services.agents import synthesizer


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _ReadSession:
    def __init__(self, store):
        self.store = store
        self.query_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, model, item_id):
        assert model is Session and item_id == self.store.session_id
        return SimpleNamespace(meeting_type="general", meeting_context="Synthetic")

    async def execute(self, query):
        self.query_count += 1
        if self.query_count == 1:
            self.store.question_queries.append(query)
            return _Result(copy.deepcopy(self.store.rows))
        assert self.query_count in (2, 3)
        return _Result([])  # No transcript or participants needed for this case.


class _Transaction:
    def __init__(self, store):
        self.store = store
        self.pending = copy.deepcopy(store.rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False  # Pending objects are never published by a failed commit.

    async def get(self, model, item_id):
        assert model is Question
        return next((row for row in self.pending if row.id == item_id), None)

    async def commit(self):
        self.store.commit_attempts += 1
        failure = self.store.commit_failure
        self.store.commit_failure = None
        if failure is not None:
            raise failure
        self.store.rows = copy.deepcopy(self.pending)
        self.store.commits += 1


class _Store:
    def __init__(self):
        self.session_id = uuid.uuid4()
        self.rows = [SimpleNamespace(
            id=uuid.uuid4(), question="Synthetic original", item_type="observation",
            rationale="", source_context="", speaker=None, speaker_id=None,
            directive_id=None, answered=False, answer_summary="", starred=True,
            dismissed=False, needs_followup=False, followup_question="",
            enrichment_notes="", agent_source="observer", revision_count=0,
            lens_label="", enhanced=False, offering_match="", vote=0,
            created_at=datetime(2026, 11, 16, tzinfo=timezone.utc), updated_at=None,
        )]
        self.commit_failure = None
        self.commit_attempts = 0
        self.commits = 0
        self.question_queries = []

    def read_session(self):
        return _ReadSession(self)

    def transaction(self):
        return _Transaction(self)


class SynthesizerCommitRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = _Store()
        self.session_id = self.store.session_id
        self.addCleanup(synthesizer.clear_synthesizer_state, self.session_id)
        self.output = synthesizer.SynthesizerOutput(items=[{
            "op": "adjust", "id": str(self.store.rows[0].id),
            "new_text": "Synthetic adjusted", "reason": "Synthetic correction",
        }])
        stack = self.enterContext(ExitStack())
        stack.enter_context(patch.object(synthesizer, "async_session", self.store.read_session))
        stack.enter_context(patch.object(insight_refiner, "async_session", self.store.transaction))
        # The real loader may seed user-editable files. Use only the bundled
        # fallback text in this synthetic test; never consult runtime AI files.
        stack.enter_context(patch.object(
            synthesizer, "load_prompt_resource", side_effect=lambda _name, fallback: fallback,
        ))
        self.generate = stack.enter_context(patch.object(
            synthesizer, "generate_json", new=AsyncMock(return_value=self.output),
        ))

    async def cycle(self):
        return await synthesizer.run_synthesizer_cycle(self.session_id, model_override="synthetic")

    async def test_failed_commit_retries_identical_snapshot(self):
        self.store.commit_failure = RuntimeError("synthetic commit failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic commit failure"):
            await self.cycle()
        self.assertEqual("Synthetic original", self.store.rows[0].question)
        self.assertEqual(0, self.store.commits)

        applied = await self.cycle()
        self.assertEqual(1, len(applied), "identical retry must not be fingerprint-skipped")
        self.assertEqual("Synthetic adjusted", applied[0]["ws_data"]["question"])
        self.assertEqual("Synthetic adjusted", self.store.rows[0].question)
        self.assertEqual(1, self.store.rows[0].revision_count)
        self.assertEqual(2, self.store.commit_attempts)
        self.assertEqual(1, self.store.commits)
        self.assertEqual(2, self.generate.await_count)

    async def test_failed_commit_preserves_previous_successful_fingerprint(self):
        self.generate.return_value = synthesizer.SynthesizerOutput(items=[])
        await self.cycle()
        previous = synthesizer._last_fingerprints[self.session_id]
        self.store.rows[0].question = "Synthetic external edit"
        self.generate.return_value = self.output
        self.store.commit_failure = RuntimeError("synthetic commit failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic commit failure"):
            await self.cycle()
        self.assertEqual(previous, synthesizer._last_fingerprints[self.session_id])
        self.assertEqual(1, len(await self.cycle()))
        self.assertEqual(2, self.store.commits)

    async def test_successful_empty_output_consumes_snapshot(self):
        self.generate.return_value = synthesizer.SynthesizerOutput(items=[])
        self.assertEqual([], await self.cycle())
        self.assertEqual([], await self.cycle())
        self.assertEqual(1, self.generate.await_count)
        self.assertEqual(1, self.store.commits)
        self.assertEqual("Synthetic original", self.store.rows[0].question)
        self.assertEqual(0, self.store.rows[0].revision_count)

    async def test_successful_no_write_operation_consumes_snapshot(self):
        self.generate.return_value = synthesizer.SynthesizerOutput(items=[{
            "op": "adjust", "id": str(self.store.rows[0].id),
            "new_text": "Synthetic original",
        }])
        self.assertEqual([], await self.cycle())
        self.assertEqual([], await self.cycle())
        self.assertEqual(1, self.generate.await_count)
        self.assertEqual(1, self.store.commits)
        self.assertEqual(0, self.store.rows[0].revision_count)

    async def test_failed_empty_commit_does_not_consume_snapshot(self):
        self.generate.return_value = synthesizer.SynthesizerOutput(items=[])
        self.store.commit_failure = RuntimeError("synthetic empty commit failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic empty commit failure"):
            await self.cycle()
        self.assertNotIn(self.session_id, synthesizer._last_fingerprints)
        self.assertEqual([], await self.cycle())
        self.assertEqual([], await self.cycle())
        self.assertEqual(2, self.generate.await_count)
        self.assertEqual(2, self.store.commit_attempts)
        self.assertEqual(1, self.store.commits)

    async def test_model_failure_leaves_identical_snapshot_retryable(self):
        self.generate.side_effect = [ValueError("synthetic model failure"), self.output]
        with self.assertLogs(synthesizer.logger, level="ERROR"):
            self.assertEqual([], await self.cycle())
        self.assertNotIn(self.session_id, synthesizer._last_fingerprints)
        self.assertEqual(0, self.store.commit_attempts)
        self.assertEqual(1, len(await self.cycle()))
        self.assertEqual(1, self.store.commits)

    async def test_cancellation_during_model_leaves_snapshot_retryable(self):
        self.generate.side_effect = [asyncio.CancelledError(), self.output]
        with self.assertRaises(asyncio.CancelledError):
            await self.cycle()
        self.assertNotIn(self.session_id, synthesizer._last_fingerprints)
        self.assertEqual(0, self.store.commit_attempts)
        self.assertEqual(1, len(await self.cycle()))
        self.assertEqual(1, self.store.commits)

    async def test_cancellation_during_commit_leaves_snapshot_retryable(self):
        self.store.commit_failure = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.cycle()
        self.assertNotIn(self.session_id, synthesizer._last_fingerprints)
        self.assertEqual("Synthetic original", self.store.rows[0].question)
        self.assertEqual(1, len(await self.cycle()))
        self.assertEqual(1, self.store.commits)

    async def test_no_eligible_rows_does_not_generate_or_consume_snapshot(self):
        self.store.rows = []
        self.assertEqual([], await self.cycle())
        self.assertNotIn(self.session_id, synthesizer._last_fingerprints)
        self.assertEqual(0, self.generate.await_count)
        self.assertEqual(0, self.store.commit_attempts)

    async def test_corpus_query_preserves_private_and_strategic_ownership(self):
        self.generate.return_value = synthesizer.SynthesizerOutput(items=[])
        await self.cycle()
        sql = str(self.store.question_queries[0].compile(
            compile_kwargs={"literal_binds": True},
        ))
        self.assertIn("questions.item_type != 'asked'", sql)
        self.assertIn("questions.item_type NOT IN ('signal', 'signal_history')", sql)
        self.assertIn("questions.dismissed IS false", sql)
        self.assertIn("ORDER BY questions.created_at, questions.id", sql)


if __name__ == "__main__":
    unittest.main()
