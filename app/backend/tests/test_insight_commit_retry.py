"""Synthetic transaction-boundary coverage; no database or provider is used."""

import unittest
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from app.services.agents.base import TranscriptBuffer
from app.services.agents.orchestrator import AgentOrchestrator

MODULE = "app.services.agents.orchestrator"
TEXT = "Validate the rollout plan with the project team"
SPEAKER_A = "11111111-1111-1111-1111-111111111111"
SPEAKER_B = "22222222-2222-2222-2222-222222222222"


class SyntheticStore:
    """Only commit makes pending Question objects durable in this fake sink."""

    def __init__(self, fail_at=None):
        self.rows = []
        self.fail_at = fail_at
        self.clock = 1000.0
        self.commit_delay = 0.0

    def fail_once(self, stage):
        if self.fail_at == stage:
            self.fail_at = None
            raise RuntimeError("synthetic " + stage + " failure")

    def session(self):
        return SyntheticSession(self)


class SyntheticSession:
    def __init__(self, store):
        self.store = store
        self.pending = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, _tb):
        self.pending.clear()
        return False

    def add(self, row):
        self.store.fail_once("add")
        self.pending.append(row)

    async def commit(self):
        self.store.fail_once("commit")
        self.store.clock += self.store.commit_delay
        for row in self.pending:
            row.id = uuid4()
            row.created_at = datetime(2026, 11, 16, tzinfo=UTC)
        self.store.rows.extend(self.pending)
        self.pending.clear()

    async def refresh(self, row):
        self.store.fail_once("refresh")


class SyntheticSocket:
    def __init__(self, fail=False):
        self.messages = []
        self.fail = fail

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("synthetic closed socket")
        self.messages.append(message)


def make_orchestrator(socket):
    # Exercise the real save, scrub, validation and context-memory methods,
    # without constructing gateways, agents or reading runtime configuration.
    orchestrator = object.__new__(AgentOrchestrator)
    orchestrator.session_id = uuid4()
    orchestrator.websocket = socket
    orchestrator.speakers = [
        {"id": SPEAKER_A, "name": "Alex"},
        {"id": SPEAKER_B, "name": "Morgan"},
    ]
    orchestrator._recent_insights = {}
    orchestrator.active_questions = []
    orchestrator._board_stubs = []
    return orchestrator


class InsightCommitRetryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = SyntheticStore()
        self.socket = SyntheticSocket()
        self.orchestrator = make_orchestrator(self.socket)
        self.session_patch = patch(MODULE + ".async_session", self.store.session)
        self.clock_patch = patch(MODULE + ".time.time", lambda: self.store.clock)
        self.session_patch.start()
        self.clock_patch.start()
        self.addCleanup(self.session_patch.stop)
        self.addCleanup(self.clock_patch.stop)

    async def emit(self, **payload):
        return await self.orchestrator._save_and_send_insight(
            {"question": TEXT, **payload}, agent_source="consolidated_analyst"
        )

    async def assert_failed_write_retries(self, stage):
        self.store.fail_at = stage
        with self.assertRaisesRegex(RuntimeError, "synthetic " + stage):
            await self.emit()
        self.assertEqual(self.store.rows, [])
        self.assertEqual(self.socket.messages, [])
        self.assertEqual(self.orchestrator._recent_insights, {})
        self.assertEqual(self.orchestrator.active_questions, [])
        self.assertEqual(self.orchestrator._board_stubs, [])

        self.assertTrue(await self.emit())
        self.assertFalse(await self.emit())
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(len(self.socket.messages), 1)
        self.assertEqual(len(self.orchestrator.active_questions), 1)

    async def test_failed_add_does_not_poison_identical_retry(self):
        await self.assert_failed_write_retries("add")

    async def test_failed_commit_does_not_poison_identical_retry(self):
        await self.assert_failed_write_retries("commit")

    async def test_committed_row_is_not_reinserted_after_refresh_failure(self):
        self.store.fail_at = "refresh"
        with self.assertRaisesRegex(RuntimeError, "synthetic refresh"):
            await self.emit()
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(self.socket.messages, [])

        self.assertFalse(await self.emit())
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(self.socket.messages, [])

    async def test_failed_broadcast_keeps_committed_replay_suppression(self):
        self.socket.fail = True
        self.assertTrue(await self.emit())
        self.socket.fail = False
        self.assertFalse(await self.emit())
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(self.socket.messages, [])

    async def test_dedup_window_starts_at_successful_commit(self):
        self.store.commit_delay = 301.0
        self.assertTrue(await self.emit())
        self.assertFalse(await self.emit())
        self.assertEqual(len(self.store.rows), 1)

    async def test_distinct_validated_speakers_keep_identical_insights(self):
        self.assertTrue(await self.emit(speaker_id=SPEAKER_A))
        self.assertTrue(await self.emit(speaker_id=SPEAKER_B))
        self.assertFalse(await self.emit(speaker_id=SPEAKER_A))
        self.assertFalse(await self.emit(speaker_id=SPEAKER_B))
        self.assertEqual(
            [row.speaker_id for row in self.store.rows],
            [UUID(SPEAKER_A), UUID(SPEAKER_B)],
        )
        self.assertEqual(len(self.socket.messages), 2)

    async def test_invalid_speaker_labels_do_not_create_new_identity(self):
        self.assertTrue(await self.emit(speaker_id="invented"))
        self.assertFalse(await self.emit(speaker_id=str(uuid4())))
        self.assertFalse(await self.emit())
        self.assertEqual(len(self.store.rows), 1)
        self.assertIsNone(self.store.rows[0].speaker_id)

    async def test_missing_speaker_does_not_hide_known_speaker(self):
        self.assertTrue(await self.emit())
        self.assertTrue(await self.emit(speaker_id=SPEAKER_A))
        self.assertEqual(len(self.store.rows), 2)

    async def test_legacy_type_and_owner_suppression_is_preserved(self):
        self.assertTrue(
            await self.emit(item_type="observation", agent_source="analyst")
        )
        self.assertFalse(
            await self.emit(item_type="question", agent_source="objection_handler")
        )
        self.assertEqual(len(self.store.rows), 1)
        self.assertEqual(self.store.rows[0].item_type, "observation")
        self.assertEqual(self.store.rows[0].agent_source, "analyst")
        self.assertEqual(self.orchestrator.active_questions, [])
        self.assertEqual(
            self.orchestrator._board_stubs, [{"item_type": "observation", "text": TEXT}]
        )

    async def test_model_claim_ids_do_not_bypass_replay_suppression(self):
        self.assertTrue(await self.emit(claim_id="model-claim-one"))
        self.assertFalse(await self.emit(claim_id="model-claim-two"))
        self.assertEqual(len(self.store.rows), 1)

    async def test_scrubbed_text_is_the_committed_dedup_text(self):
        self.assertTrue(await self.emit(question="S1 should validate the rollout plan"))
        self.assertFalse(
            await self.emit(question="Alex should validate the rollout plan")
        )
        self.assertEqual(
            self.store.rows[0].question, "Alex should validate the rollout plan"
        )
        self.assertEqual(len(self.store.rows), 1)

    async def test_insight_replay_does_not_remove_accepted_human_repetitions(self):
        self.orchestrator.transcript_buffer = TranscriptBuffer()
        for utterance in ("accepted-turn-one", "accepted-turn-two"):
            await self.orchestrator.transcript_buffer.add(
                TEXT, "Alex", speaker_id=SPEAKER_A, utterance_id=utterance
            )
        self.assertTrue(await self.emit(speaker_id=SPEAKER_A))
        self.assertFalse(await self.emit(speaker_id=SPEAKER_A))

        transcript = await self.orchestrator.transcript_buffer.get_full()
        self.assertEqual(transcript.count(TEXT), 2)
        self.assertEqual(len(self.store.rows), 1)


if __name__ == "__main__":
    unittest.main()
