import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.debate_review import (
    DebateReviewDraft,
    DebateReviewMetrics,
    apply_review_suggestion,
    build_review_traces,
    collect_review_sources,
    evaluate_debate,
)
from app.services.argument_graph import ArgumentEdge, ArgumentGraph, ArgumentNode
from app.services.debate_settings import DebateSettings


class DebateReviewTests(unittest.IsolatedAsyncioTestCase):
    def test_useful_acknowledged_research_is_not_labeled_late_by_duration(self):
        traces, _notes = build_review_traces(
            entries=[], speakers={}, claims=[], graph=ArgumentGraph(session_id="s"),
            samples=[{
                "claim_id": "c", "target_claim": "Eine Zahl",
                "answer_now": "Die Quelle praezisiert die Zahl.",
                "latency_ms": 9000, "origin": "research",
                "sources": [{"url": "https://example.org", "passage": "Beleg"}],
                "ui_acknowledged": True,
            }],
        )
        self.assertFalse(any(trace.category == "late_recommendation" for trace in traces))

    def test_review_traces_link_open_claims_and_late_advice_to_original_transcript(self):
        speaker_id = uuid.uuid4()
        entry = SimpleNamespace(
            text="Die Quote liegt sicher bei acht Prozent.",
            raw_text=None,
            speaker_id=speaker_id,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        claim = SimpleNamespace(
            claim_id="claim-1", revision=1,
            original_text=entry.text, sources=[], feedback={},
        )
        graph = ArgumentGraph(
            session_id="session",
            nodes=[
                ArgumentNode(id="claim:claim-1", kind="claim", claim_id="claim-1", text=entry.text),
                ArgumentNode(id="question:claim-1", kind="question", claim_id="claim-1", text="Welche Quelle belegt das?", status="open"),
            ],
            edges=[ArgumentEdge(source_id="question:claim-1", target_id="claim:claim-1", relation="questions")],
        )

        traces, notes = build_review_traces(
            entries=[entry], speakers={speaker_id: "Alex"}, claims=[claim], graph=graph,
            samples=[{"claim_id": "claim-1", "target_claim": entry.text, "answer_now": "Bitte Quelle nennen.", "latency_ms": 4200}],
        )

        self.assertEqual(
            {"open_question", "unsupported_claim", "late_recommendation"},
            {trace.category for trace in traces},
        )
        self.assertTrue(all(trace.transcript_quote == entry.text for trace in traces))
        self.assertTrue(any("späte" in note for note in notes))

    def test_review_uses_claim_identity_instead_of_similar_opposite_sentence(self):
        wrong = SimpleNamespace(
            id=uuid.uuid4(),
            utterance_id="other-claim",
            producer_revision=1,
            sequence=1,
            text="Die Quote liegt nicht bei acht Prozent.",
            raw_text=None,
            speaker_id="other",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        right = SimpleNamespace(
            id=uuid.uuid4(),
            utterance_id="claim-1",
            producer_revision=1,
            sequence=2,
            text="Die Quote liegt bei acht Prozent.",
            raw_text=None,
            speaker_id="owner",
            timestamp=datetime(2026, 1, 2, tzinfo=UTC),
        )
        claim = SimpleNamespace(
            claim_id="claim-1", revision=1,
            original_text=right.text, sources=[], feedback={},
        )

        traces, _notes = build_review_traces(
            entries=[wrong, right], speakers={"other": "Bea", "owner": "Alex"},
            claims=[claim], graph=ArgumentGraph(session_id="session"), samples=[],
        )

        self.assertEqual(1, len(traces))
        self.assertEqual(right.text, traces[0].transcript_quote)
        self.assertEqual("Alex", traces[0].speaker)

    def test_sources_are_deduplicated_and_remain_linked_to_checked_claims(self):
        samples = [
            {"sources": [{
                "title": "Amtliche Reihe",
                "url": "https://example.test/rate",
                "snippet": "2,2 Prozent",
                "provider": "test",
                "claim": "Die Quote liegt bei acht Prozent.",
            }]},
            {"sources": [{
                "title": "Amtliche Reihe (erneut)",
                "url": "https://example.test/rate",
                "snippet": "2,2 Prozent",
                "provider": "test",
                "claim": "Die Quote liegt bei acht Prozent.",
            }]},
        ]

        sources = collect_review_sources(samples)

        self.assertEqual(1, len(sources))
        self.assertEqual("Amtliche Reihe", sources[0].title)
        self.assertEqual("Die Quote liegt bei acht Prozent.", sources[0].claim)

    async def test_review_uses_one_structured_call_and_keeps_safe_suggestions(self):
        draft = DebateReviewDraft(
            summary="Die Argumente waren klar, aber einzelne Antworten zu lang.",
            strengths=["Beweislast sauber eingefordert"],
            improvements=[
                {
                    "issue": "Antwort zu lang",
                    "example": "Der Mittelteil wiederholt denselben Punkt.",
                    "better": "Nur Behauptung, Beleg und Folge nennen.",
                }
            ],
            source_quality="Zwei Tatsachen blieben ungeprueft.",
            suggested_style_focus="concise",
            suggested_mode="forceful",
            suggested_research_frequency="often",
            suggested_always_analogy=False,
        )
        generate = AsyncMock(return_value=draft)
        metrics = DebateReviewMetrics(
            recommendations=4,
            average_latency_ms=820,
            maximum_latency_ms=1400,
            average_answer_words=18,
            average_question_words=9,
        )

        with patch("app.services.debate_review.generate_json", new=generate):
            review = await evaluate_debate(
                transcript="[team]: Unser Punkt ist klar.\n[external]: Welcher Beleg?",
                samples=[{"answer_now": "Der Beleg folgt.", "counter_question": "Welcher Teil fehlt?"}],
                metrics=metrics,
                model_id="qwen3:4b",
                session_id=uuid.uuid4(),
            )

        self.assertEqual(1, generate.await_count)
        self.assertEqual("concise", review.suggested_style_focus)
        self.assertEqual(metrics, review.metrics)
        self.assertEqual("debate_review", generate.await_args.kwargs["source"])
        prompt = generate.await_args.args[1]
        self.assertIn("[team]", prompt)
        self.assertIn("820", prompt)

    def test_apply_requires_only_hard_coded_setting_values(self):
        current = DebateSettings(
            mode="persuasive",
            research_enabled=True,
            research_frequency="normal",
            always_analogy=True,
            style_focus="balanced",
        )
        draft = DebateReviewDraft(
            summary="Kuerzer formulieren.",
            suggested_style_focus="natural",
            suggested_mode="forceful",
            suggested_research_frequency="low",
            suggested_always_analogy=False,
        )

        updated = apply_review_suggestion(current, draft)

        self.assertEqual("forceful", updated.mode)
        self.assertEqual("natural", updated.style_focus)
        self.assertEqual("low", updated.research_frequency)
        self.assertFalse(updated.always_analogy)
        self.assertTrue(updated.research_enabled)


if __name__ == "__main__":
    unittest.main()
