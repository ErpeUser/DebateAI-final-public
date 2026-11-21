import unittest

from app.services.agents.objection_handler import (
    DebateRecommendation,
    normalize_standard_strategies,
)


class StandardStrategyContractTests(unittest.TestCase):
    """The default live contract is one primary move plus two alternatives."""

    def test_normalizer_returns_three_distinct_versioned_moves(self):
        recommendation = DebateRecommendation(
            answer_now="Die Zahl belegt den Trend noch nicht.",
            counterargument="Eine Einzelzahl reicht für diese Schlussfolgerung nicht.",
            counter_question="Welche Vergleichsbasis verwenden Sie?",
            analogy="Das ist wie ein einzelnes Foto statt eines ganzen Films.",
            primary_move="answer",
            target_claim="Die Zahl beweist den Trend.",
            claim_id="claim-1",
            claim_revision=3,
            transcript_revision=7,
            generation_id="generation-1",
        )

        options = normalize_standard_strategies(recommendation)

        self.assertEqual(["answer", "counter_question", "example"], [o["kind"] for o in options])
        self.assertEqual(3, len(options))
        self.assertEqual(3, len({o["text"].casefold() for o in options}))
        self.assertEqual([1, 2, 3], [o["rank"] for o in options])
        self.assertTrue(all(o["claim_id"] == "claim-1" for o in options))
        self.assertTrue(all(o["transcript_revision"] == 7 for o in options))

    def test_incomplete_model_output_is_bounded_without_duplicate_text(self):
        recommendation = DebateRecommendation(
            answer_now="",
            counterargument="",
            counter_question="",
            analogy="",
            primary_move="question",
            confidence="low",
        )

        options = normalize_standard_strategies(recommendation)

        self.assertLessEqual(len(options), 3)
        self.assertEqual(len(options), len({o["text"].casefold() for o in options}))
        self.assertTrue(all(o["text"].strip() for o in options))
        self.assertTrue(all(o["speakable"] for o in options))


if __name__ == "__main__":
    unittest.main()
