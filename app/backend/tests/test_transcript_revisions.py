import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.transcript_refiner import is_refinable
from app.services.transcript_revisions import apply_manual_transcript_revision

from app import models


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class TranscriptRevisionModelTests(unittest.TestCase):
    def test_history_has_stable_identity_source_and_unique_revision(self):
        model = models.TranscriptEntryRevision
        self.assertTrue(
            {
                "session_id",
                "transcript_id",
                "revision",
                "text",
                "speaker_id",
                "source",
                "reason",
                "created_at",
            }.issubset(model.__table__.columns.keys())
        )
        self.assertIn(
            "uq_transcript_entry_revision",
            {constraint.name for constraint in model.__table__.constraints},
        )
        self.assertIn("manual_corrected_at", models.TranscriptEntry.__table__.columns)
        self.assertIn("utterance_id", models.TranscriptEntry.__table__.columns)
        self.assertIn("producer_revision", models.TranscriptEntry.__table__.columns)

    def test_manual_correction_is_never_eligible_for_late_model_refinement(self):
        entry = SimpleNamespace(
            text="Manuell korrigiert.",
            refined_at=None,
            manual_corrected_at=datetime.now(UTC),
        )
        self.assertFalse(is_refinable(entry))


class TranscriptRevisionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_manual_edit_keeps_original_and_appends_corrected_revision(
        self,
    ):
        session_id = uuid.uuid4()
        transcript_id = uuid.uuid4()
        old_speaker = uuid.uuid4()
        new_speaker = uuid.uuid4()
        entry = SimpleNamespace(
            id=transcript_id,
            session_id=session_id,
            text="Fuenfzig Prozent.",
            speaker_id=old_speaker,
            raw_text=None,
            manual_corrected_at=None,
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=_ScalarResult(entry))
        db.scalar = AsyncMock(return_value=None)
        db.add = MagicMock()
        db.flush = AsyncMock()

        result = await apply_manual_transcript_revision(
            db,
            session_id,
            transcript_id,
            text="Fuenfzehn Prozent.",
            speaker_id=new_speaker,
            reason="Zahl und Sprecher korrigiert",
        )

        self.assertEqual("Fuenfzehn Prozent.", entry.text)
        self.assertEqual("Fuenfzig Prozent.", entry.raw_text)
        self.assertEqual(new_speaker, entry.speaker_id)
        self.assertIsNotNone(entry.manual_corrected_at)
        original, corrected = [call.args[0] for call in db.add.call_args_list]
        self.assertEqual(
            (1, "original", "Fuenfzig Prozent."),
            (original.revision, original.source, original.text),
        )
        self.assertEqual(
            (2, "manual", "Fuenfzehn Prozent."),
            (corrected.revision, corrected.source, corrected.text),
        )
        self.assertEqual("Zahl und Sprecher korrigiert", corrected.reason)
        self.assertIs(result.revision, corrected)

    async def test_manual_correction_after_refiner_preserves_asr_as_original(self):
        session_id = uuid.uuid4()
        transcript_id = uuid.uuid4()
        entry = SimpleNamespace(
            id=transcript_id,
            session_id=session_id,
            text="ASR text, refined.",
            raw_text="ASR text",
            speaker_id=None,
            manual_corrected_at=None,
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=_ScalarResult(entry))
        db.scalar = AsyncMock(return_value=None)
        db.add = MagicMock()
        db.flush = AsyncMock()

        result = await apply_manual_transcript_revision(
            db,
            session_id,
            transcript_id,
            text="Manually corrected text.",
            reason="manual wording correction",
        )

        original, refiner, manual = [call.args[0] for call in db.add.call_args_list]
        self.assertEqual("ASR text", original.text)
        self.assertEqual("original", original.source)
        self.assertEqual("ASR text, refined.", refiner.text)
        self.assertEqual("refiner", refiner.source)
        self.assertEqual("Manually corrected text.", manual.text)
        self.assertEqual("manual", manual.source)
        self.assertEqual("Manually corrected text.", entry.text)
        self.assertEqual("ASR text", entry.raw_text)
        self.assertEqual(3, result.revision.revision)


if __name__ == "__main__":
    unittest.main()
