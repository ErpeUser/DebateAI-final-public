import unittest
from types import SimpleNamespace

import numpy as np
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.semantic_argument_memory import (
    SemanticArgumentMatch,
    SemanticArgumentMemory,
    SemanticSearchResult,
)


class _Memory(SemanticArgumentMemory):
    def __init__(self, vectors):
        super().__init__(minimum_score=0.2)
        self._query_vectors = vectors
        self.ready = True

    def _embed(self, texts):
        return [
            np.asarray(self._query_vectors[text], dtype=np.float32) for text in texts
        ]


class SemanticArgumentMemoryTests(unittest.TestCase):
    def _memory(self):
        query = "Die Reform senkt die Kosten 2026 um 20 Prozent."
        rows = {
            "negation": {
                "claim_id": "claim-negation",
                "target_claim": "Die Reform senkt die Kosten 2026 nicht um 20 Prozent.",
                "original_span": [4, 61],
            },
            "number": {
                "claim_id": "claim-number",
                "target_claim": "Die Reform senkt die Kosten 2026 um 10 Prozent.",
                "original_span": [0, 55],
            },
            "other_time": {
                "claim_id": "claim-other-time",
                "target_claim": "Die Reform senkte die Kosten 2024 um 10 Prozent.",
                "original_span": [0, 56],
            },
        }
        vectors = {
            query: [1.0, 0.0],
            rows["negation"]["target_claim"]: [0.99, 0.01],
            rows["number"]["target_claim"]: [0.98, 0.02],
            rows["other_time"]["target_claim"]: [0.97, 0.03],
        }
        memory = _Memory(vectors)
        memory._rows = {row["claim_id"]: row for row in rows.values()}
        memory._vectors = {
            row["claim_id"]: np.asarray(vectors[row["target_claim"]], dtype=np.float32)
            for row in rows.values()
        }
        return memory, query

    def test_search_targets_keeps_negation_and_number_disagreement_topically_relevant(
        self,
    ):
        memory, query = self._memory()

        result = memory.search_targets(query, related_limit=4, conflict_limit=4)

        self.assertEqual(
            {"claim-negation", "claim-number", "claim-other-time"},
            {match.row["claim_id"] for match in result.related},
        )

    def test_search_targets_marks_only_same_scope_disagreements_as_possible_conflicts(
        self,
    ):
        memory, query = self._memory()

        result = memory.search_targets(query, related_limit=4, conflict_limit=4)
        conflicts = {
            match.row["claim_id"]: match for match in result.possible_conflicts
        }

        self.assertIn("negation", conflicts["claim-negation"].conflict_reasons)
        self.assertIn("number", conflicts["claim-number"].conflict_reasons)
        self.assertNotIn("claim-other-time", conflicts)
        self.assertEqual([4, 61], conflicts["claim-negation"].row["original_span"])

    def test_similarity_never_labels_a_possible_conflict_as_confirmed(self):
        memory, query = self._memory()

        result = memory.search_targets(query, related_limit=4, conflict_limit=4)

        self.assertTrue(result.possible_conflicts)
        self.assertTrue(
            all(
                match.match_type == "possible_conflict"
                for match in result.possible_conflicts
            )
        )

    def test_stale_claim_revision_cannot_replace_newer_claim_text(self):
        current_text = "Die Reform senkt die Kosten 2026 um 20 Prozent."
        stale_text = "Die Reform senkt die Kosten 2026 um 10 Prozent."
        memory = _Memory(
            {
                stale_text: [0.0, 1.0],
            }
        )
        memory._rows = {
            "claim-1": {
                "claim_id": "claim-1",
                "target_claim": current_text,
                "revision": 2,
            }
        }
        memory._vectors = {"claim-1": np.asarray([1.0, 0.0], dtype=np.float32)}
        memory.vector_dimension = 2

        memory.upsert(
            {
                "claim_id": "claim-1",
                "target_claim": stale_text,
                "revision": 1,
            }
        )

        self.assertEqual(current_text, memory._rows["claim-1"]["target_claim"])
        np.testing.assert_array_equal(
            np.asarray([1.0, 0.0], dtype=np.float32),
            memory._vectors["claim-1"],
        )

    def test_coach_context_labels_conflict_candidates_with_claim_and_original_span(
        self,
    ):
        candidate = SemanticArgumentMatch(
            row={
                "claim_id": "claim-older",
                "target_claim": "Die Reform senkt die Kosten nicht.",
                "original_span": [18, 54],
                "speaker_name": "Mara",
            },
            score=0.91,
            match_type="possible_conflict",
            conflict_reasons=("negation",),
        )
        memory = SimpleNamespace(
            search_targets=lambda *_args, **_kwargs: SemanticSearchResult(
                [], [candidate]
            )
        )
        orchestrator = object.__new__(AgentOrchestrator)
        orchestrator.debate_settings = SimpleNamespace(performance_profile="balanced")
        orchestrator._board_stubs = []
        orchestrator.active_questions = []
        orchestrator._semantic_argument_memory = memory
        orchestrator._argument_memory = []
        orchestrator._active_claim_id = "claim-current"
        orchestrator._active_speaker_id = "speaker-current"

        context = orchestrator._debate_support_context("Die Reform senkt die Kosten.")

        self.assertIn("moeglicher Konflikt", context)
        self.assertIn("claim:claim-older", context)
        self.assertIn("Originalspanne:18-54", context)
        self.assertNotIn("bestaetigter Widerspruch", context)


if __name__ == "__main__":
    unittest.main()
