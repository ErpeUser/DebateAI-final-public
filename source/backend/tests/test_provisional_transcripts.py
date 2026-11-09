import unittest

from app import models


class ProvisionalTranscriptModelContractTests(unittest.TestCase):
    def test_append_only_revision_model_has_identity_audio_and_visibility_fields(self):
        model = getattr(models, "ProvisionalTranscriptRevision", None)

        self.assertIsNotNone(model)
        columns = set(model.__table__.columns.keys())
        self.assertTrue({
            "session_id",
            "segment_id",
            "revision",
            "text",
            "mode",
            "track_id",
            "audio_start_sample",
            "audio_end_sample",
            "sample_rate",
            "finalized_at",
            "created_at",
        }.issubset(columns))
        constraints = {
            constraint.name
            for constraint in model.__table__.constraints
            if constraint.name
        }
        self.assertIn("uq_provisional_transcript_segment_revision", constraints)


class ProvisionalTranscriptRevisionContractTests(unittest.TestCase):
    def test_append_revision_materializes_without_losing_previous_words(self):
        from app.services.provisional_transcripts import materialize_revision_text

        self.assertEqual(
            "Ich stimme nicht zu.",
            materialize_revision_text("Ich stimme ", "nicht zu.", "append"),
        )

    def test_empty_revision_is_never_persisted_as_visible_text(self):
        from app.services.provisional_transcripts import materialize_revision_text

        self.assertIsNone(materialize_revision_text("Bleibt sichtbar", "   ", "replace"))

    def test_replace_revision_keeps_the_provider_correction(self):
        from app.services.provisional_transcripts import materialize_revision_text

        self.assertEqual(
            "Korrigierter Satz.",
            materialize_revision_text("Falscher Satz.", " Korrigierter Satz. ", "replace"),
        )

    def test_exactly_associated_nonempty_final_supersedes_regardless_of_length(self):
        from app.services.provisional_transcripts import should_finalize_provisional

        self.assertTrue(should_finalize_provisional("Das ist der ganze Satz.", "Das ist"))
        self.assertFalse(should_finalize_provisional("Das bleibt sichtbar.", ""))
        self.assertTrue(should_finalize_provisional("Gleicher Satz.", "Gleicher Satz."))

    def test_rest_projection_is_explicitly_provisional_and_revision_addressable(self):
        import uuid
        from datetime import datetime, timezone
        from types import SimpleNamespace

        from app.services.provisional_transcripts import provisional_transcript_payload

        row = SimpleNamespace(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            segment_id="segment-1",
            revision=3,
            text="Bleibt nach Reconnect sichtbar.",
            track_id="mic",
            audio_start_sample=160,
            audio_end_sample=320,
            sample_rate=16000,
            created_at=datetime.now(timezone.utc),
        )

        payload = provisional_transcript_payload(row, sequence=8)

        self.assertTrue(payload["provisional"])
        self.assertEqual("segment-1", payload["utterance_id"])
        self.assertEqual(3, payload["revision"])
        self.assertEqual(8, payload["sequence"])


if __name__ == "__main__":
    unittest.main()
