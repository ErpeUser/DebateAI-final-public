import unittest
from types import SimpleNamespace

from app.services.argument_graph import (
    ArgumentGraph,
    argument_graph_from_records,
    update_argument_graph,
)


def recommendation(**overrides):
    data = {
        "claim_id": "claim-1",
        "recommendation_revision": 1,
        "target_claim": "Die Maßnahme ist zu teuer.",
        "answer_now": "Teuer ist nicht dasselbe wie unwirtschaftlich.",
        "counterargument": "Entscheidend sind die vermiedenen Folgekosten.",
        "counter_question": "Welche Gesamtkosten vergleichen Sie?",
        "open_question": "Welche Folgekosten wurden eingerechnet?",
        "question_status": "open",
        "argument_points": ["Anschaffung und Folgekosten getrennt vergleichen"],
        "sources": [{"url": "https://example.test/source"}],
    }
    data.update(overrides)
    return data


class ArgumentGraphTests(unittest.TestCase):
    def test_graph_is_derived_from_latest_normalized_claim_record(self):
        older = SimpleNamespace(
            claim_id="claim-1",
            revision=1,
            original_text="Alter Text",
            speaker_id="speaker-1",
            atomic_claims=[],
            sources=[],
            relations=[],
            feedback={"presentation": {"answer_now": "Alte Antwort"}},
        )
        newer = SimpleNamespace(
            claim_id="claim-1",
            revision=2,
            original_text="Neuer Text",
            speaker_id="speaker-1",
            atomic_claims=[],
            sources=[{"url": "https://example.org/source"}],
            relations=[],
            feedback={"presentation": {"answer_now": "Neue Antwort"}},
        )

        graph = argument_graph_from_records("session-1", [older, newer])

        self.assertEqual(
            "Neuer Text", next(n for n in graph.nodes if n.kind == "claim").text
        )
        response = next(n for n in graph.nodes if n.kind == "response")
        self.assertEqual("Neue Antwort", response.text)
        self.assertEqual(["https://example.org/source"], response.evidence_urls)

    def test_rebuilt_graph_keeps_the_durable_claim_revision(self):
        record = SimpleNamespace(
            claim_id="claim-1",
            revision=7,
            original_text="Korrigierter Text",
            speaker_id="speaker-1",
            atomic_claims=[],
            sources=[],
            relations=[],
            feedback={"presentation": {"answer_now": "Aktuelle Antwort"}},
        )

        graph = argument_graph_from_records("session-1", [record])

        self.assertEqual(
            7, next(node for node in graph.nodes if node.kind == "claim").revision
        )
        self.assertEqual(
            7, next(node for node in graph.nodes if node.kind == "response").revision
        )

    def test_recommendation_becomes_a_claim_with_linked_response_points_and_question(
        self,
    ):
        graph = update_argument_graph(
            ArgumentGraph(session_id="session-1"), recommendation()
        )

        self.assertEqual(
            {"claim", "response", "point", "question"},
            {node.kind for node in graph.nodes},
        )
        self.assertIn("rebuts", {edge.relation for edge in graph.edges})
        self.assertIn("supports", {edge.relation for edge in graph.edges})
        self.assertIn("questions", {edge.relation for edge in graph.edges})
        response = next(node for node in graph.nodes if node.kind == "response")
        self.assertEqual(["https://example.test/source"], response.evidence_urls)

    def test_a_better_revision_replaces_children_without_losing_the_claim(self):
        graph = update_argument_graph(
            ArgumentGraph(session_id="session-1"), recommendation()
        )
        graph = update_argument_graph(
            graph,
            recommendation(
                recommendation_revision=2,
                answer_now="Die Gesamtkosten sind über fünf Jahre niedriger.",
                argument_points=["Fünfjahreskosten statt Kaufpreis vergleichen"],
                open_question="",
                counter_question="Welche Fünfjahresrechnung widerspricht dem?",
            ),
        )

        self.assertEqual(1, sum(node.kind == "claim" for node in graph.nodes))
        self.assertEqual(1, sum(node.kind == "response" for node in graph.nodes))
        response = next(node for node in graph.nodes if node.kind == "response")
        self.assertIn("fünf Jahre", response.text)
        self.assertEqual(2, response.revision)
        self.assertNotIn(
            "Welche Folgekosten wurden eingerechnet?",
            [node.text for node in graph.nodes],
        )

    def test_distinct_claims_and_open_questions_survive_later_turns(self):
        graph = update_argument_graph(
            ArgumentGraph(session_id="session-1"), recommendation()
        )
        graph = update_argument_graph(
            graph,
            recommendation(
                claim_id="claim-2",
                recommendation_revision=2,
                target_claim="Die Umsetzung dauert zu lange.",
                open_question="Wer hat die Frist geschätzt?",
            ),
        )

        self.assertEqual(2, sum(node.kind == "claim" for node in graph.nodes))
        self.assertEqual(2, sum(node.kind == "question" for node in graph.nodes))

    def test_semantic_memory_marks_paraphrases_as_related_not_logically_continuing(
        self,
    ):
        graph = update_argument_graph(
            ArgumentGraph(session_id="session-1"),
            recommendation(
                claim_id="claim-1", target_claim="Der Staat soll Preise deckeln."
            ),
        )
        graph = update_argument_graph(
            graph,
            recommendation(
                claim_id="claim-2",
                target_claim="Mieten duerfen gesetzlich nicht weiter steigen.",
                semantic_related_claim_ids=["claim-1"],
            ),
        )

        self.assertTrue(
            any(
                edge.source_id == "claim:claim-2"
                and edge.target_id == "claim:claim-1"
                and edge.relation == "related"
                for edge in graph.edges
            )
        )

    def test_model_relations_remain_visible_but_are_not_mislabeled_as_verified(self):
        graph = update_argument_graph(
            ArgumentGraph(session_id="session-1"),
            recommendation(
                claim_id="claim-1", target_claim="Die Massnahme senkt die Kosten."
            ),
        )
        graph = update_argument_graph(
            graph,
            recommendation(
                claim_id="claim-2",
                target_claim="Die Massnahme erhoeht dieselben Kosten.",
                logical_relations=[
                    {
                        "target_claim_id": "claim-1",
                        "relation": "contradicts",
                        "confidence": 0.91,
                        "verified": True,
                    },
                    {
                        "target_claim_id": "claim-1",
                        "relation": "double_standard",
                        "confidence": 0.95,
                        "verified": False,
                    },
                ],
            ),
        )

        relations = {
            edge.relation
            for edge in graph.edges
            if edge.source_id == "claim:claim-2" and edge.target_id == "claim:claim-1"
        }
        self.assertIn("contradicts", relations)
        self.assertIn("double_standard", relations)
        double_standard = next(
            edge
            for edge in graph.edges
            if edge.source_id == "claim:claim-2"
            and edge.target_id == "claim:claim-1"
            and edge.relation == "double_standard"
        )
        self.assertFalse(double_standard.verified)
        self.assertEqual("model", double_standard.verification_method)


if __name__ == "__main__":
    unittest.main()
