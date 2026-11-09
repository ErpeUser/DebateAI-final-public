"""Persistence and consent boundaries for explicitly confirmed debate examples."""

import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.debate_learning import (
    load_good_debate_examples,
    revoke_good_debate_example,
    save_good_debate_example,
)


class _SettingsStore:
    def __init__(self, values=None):
        self.values = values if values is not None else {}

    async def get(self, _model, key):
        return self.values.get(key)

    def add(self, setting):
        self.values[setting.key] = setting

    async def flush(self):
        return None


class DebateLearningTests(unittest.IsolatedAsyncioTestCase):
    async def test_expiry_is_enforced_and_survives_a_new_db_session(self):
        values = {}
        writer = _SettingsStore(values)
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        example = await save_good_debate_example(
            writer,
            claim="Claim A",
            answer="Answer A",
            valid_until=future,
        )

        reader = _SettingsStore(values)
        loaded = await load_good_debate_examples(reader)

        self.assertEqual([example.id], [item.id for item in loaded])
        self.assertEqual("unverified", loaded[0].factual_status)
        self.assertTrue(loaded[0].usefulness_confirmed)
        self.assertFalse(loaded[0].export_allowed)

        expired = await save_good_debate_example(
            writer,
            claim="Expired",
            answer="Old answer",
            valid_until=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        )
        self.assertNotIn(expired.id, [item.id for item in await load_good_debate_examples(reader)])

    async def test_revoke_is_persistent_and_records_correction_without_truth_label(self):
        values = {}
        db = _SettingsStore(values)
        example = await save_good_debate_example(
            db,
            claim="Claim B",
            answer="Answer B",
            evidence_sources=["source-7"],
        )

        self.assertTrue(
            await revoke_good_debate_example(
                _SettingsStore(values),
                example.id,
                correction="Do not use this answer for the stated population.",
            )
        )
        self.assertEqual([], await load_good_debate_examples(_SettingsStore(values)))

        restored = await load_good_debate_examples(
            _SettingsStore(values), include_revoked=True
        )
        self.assertEqual(1, len(restored))
        self.assertIsNotNone(restored[0].revoked_at)
        self.assertEqual("corrected", restored[0].factual_status)
        self.assertEqual(
            ["Do not use this answer for the stated population."],
            restored[0].corrections,
        )
        self.assertEqual("usefulness", restored[0].feedback_kind)
        self.assertEqual(["source-7"], restored[0].evidence_sources)

    async def test_duplicate_claim_and_answer_replaces_old_example(self):
        db = _SettingsStore()
        first = await save_good_debate_example(
            db, claim="Same claim", answer="Same answer", context="old"
        )
        second = await save_good_debate_example(
            db, claim=" same CLAIM ", answer="same answer", context="new"
        )

        loaded = await load_good_debate_examples(db)
        self.assertEqual([second.id], [item.id for item in loaded])
        self.assertEqual("new", loaded[0].context)
        self.assertNotEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
