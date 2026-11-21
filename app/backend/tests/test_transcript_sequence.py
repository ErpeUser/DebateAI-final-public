import unittest
import uuid
from types import SimpleNamespace

from app.models import TranscriptEntry
from app.services.session_manager import get_next_sequence


class FakeSequenceDB:
    def __init__(self, session_id, last_sequence):
        self.values = [session_id, last_sequence]
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        value = self.values.pop(0)
        return SimpleNamespace(scalar_one_or_none=lambda: value)


class TranscriptSequenceContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_row_is_locked_before_sequence_is_read(self):
        session_id = uuid.uuid4()
        db = FakeSequenceDB(session_id, 7)

        sequence = await get_next_sequence(session_id, db)

        self.assertEqual(8, sequence)
        self.assertEqual(2, len(db.statements))
        self.assertIsNotNone(db.statements[0]._for_update_arg)
        self.assertIsNone(db.statements[1]._for_update_arg)

    async def test_empty_session_starts_at_one(self):
        session_id = uuid.uuid4()
        db = FakeSequenceDB(session_id, None)

        self.assertEqual(1, await get_next_sequence(session_id, db))

    def test_model_enforces_one_sequence_per_session(self):
        constraints = {
            constraint.name for constraint in TranscriptEntry.__table__.constraints
        }
        self.assertIn("uq_transcript_entries_session_sequence", constraints)


if __name__ == "__main__":
    unittest.main()
