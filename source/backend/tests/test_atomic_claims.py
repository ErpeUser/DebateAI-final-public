import unittest

from app.services.agents.objection_handler import DebateRecommendation, build_atomic_claims


class AtomicClaimCoverageTests(unittest.TestCase):
    def test_ids_do_not_depend_on_argument_point_order(self):
        text = "Wenn der Preis 10 Euro ist, kaufen wir heute oder morgen."
        first = DebateRecommendation(
            target_claim=text,
            argument_points=["Wenn der Preis 10 Euro ist", "kaufen wir heute oder morgen"],
        )
        second = first.model_copy(update={"argument_points": list(reversed(first.argument_points))})

        first_ids = {claim.text: claim.id for claim in build_atomic_claims(first, parent_claim_id="c1")}
        second_ids = {claim.text: claim.id for claim in build_atomic_claims(second, parent_claim_id="c1")}

        self.assertEqual(first_ids, second_ids)

    def test_unextracted_original_span_is_preserved_verbatim(self):
        text = "Der Plan kostet 10 Euro pro Monat, aber nur wenn 100 Nutzer teilnehmen."
        recommendation = DebateRecommendation(
            target_claim=text,
            argument_points=["Der Plan kostet 10 Euro pro Monat"],
        )

        claims = build_atomic_claims(recommendation, parent_claim_id="c2")
        rendered = " ".join(claim.text for claim in sorted(claims, key=lambda item: item.start))

        self.assertIn("10 Euro pro Monat", rendered)
        self.assertIn("nur wenn 100 Nutzer teilnehmen", rendered)
        self.assertTrue(all(claim.start >= 0 for claim in claims))

    def test_quantifiers_use_whole_words_not_substrings(self):
        claims = build_atomic_claims(
            DebateRecommendation(target_claim="Die Preise fallen heute."),
            parent_claim_id="c3",
        )

        self.assertEqual("", claims[0].quantifier)
        self.assertEqual("heute", claims[0].temporal_scope)

    def test_vorausgesetzt_condition_is_preserved(self):
        text = "Vorausgesetzt die Quelle nennt den Zeitraum, gilt der Vergleich."
        claims = build_atomic_claims(
            DebateRecommendation(target_claim=text),
            parent_claim_id="c4",
        )

        self.assertEqual(text, claims[0].condition)


if __name__ == "__main__":
    unittest.main()
