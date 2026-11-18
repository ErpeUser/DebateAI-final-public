import unittest

from app.services.agents.base import TranscriptBuffer
from app.services.turn_assembler import TurnAssembler


class TurnAssemblerTests(unittest.IsolatedAsyncioTestCase):
    async def test_short_vad_pause_revises_same_utterance_and_buffer_row(self):
        turns = TurnAssembler()
        first = turns.add("speaker-a", "Die Kosten liegen bei", now=10.0)
        second = turns.add("speaker-a", "zehn Euro pro Monat", now=11.0)

        self.assertEqual(first.utterance_id, second.utterance_id)
        self.assertEqual("Die Kosten liegen bei zehn Euro pro Monat", second.text)
        self.assertTrue(second.continued)

        buffer = TranscriptBuffer()
        await buffer.add(first.text, "A", utterance_id=first.utterance_id)
        await buffer.add(second.text, "A", utterance_id=second.utterance_id)
        self.assertEqual(1, len(buffer._segments))
        self.assertEqual(second.text, buffer._segments[0]["text"])

    async def test_sentence_end_or_speaker_change_starts_new_turn(self):
        turns = TurnAssembler()
        first = turns.add("a", "Das ist abgeschlossen.", now=1.0)
        after_stop = turns.add("a", "Ein neuer Punkt", now=1.5)
        other = turns.add("b", "Ein Einwand", now=1.8)

        self.assertNotEqual(first.utterance_id, after_stop.utterance_id)
        self.assertNotEqual(after_stop.utterance_id, other.utterance_id)

    async def test_lexical_continuation_can_override_asr_sentence_punctuation(self):
        turns = TurnAssembler()
        first = turns.add("a", "Ich glaube.", now=1.0)
        continued = turns.add("a", "dass der Preis bei zehn Euro bleibt", now=1.6)

        self.assertEqual(first.utterance_id, continued.utterance_id)
        self.assertTrue(continued.continued)

    async def test_longer_gap_and_new_statement_do_not_merge_without_punctuation(self):
        turns = TurnAssembler()
        first = turns.add("a", "Der erste Punkt", now=1.0)
        next_turn = turns.add("a", "Jetzt kommt ein anderes Thema", now=3.0)

        self.assertNotEqual(first.utterance_id, next_turn.utterance_id)


if __name__ == "__main__":
    unittest.main()
