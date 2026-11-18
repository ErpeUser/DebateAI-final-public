import json
import unittest

from app.services.briefing_document import _text
from app.services.debate_settings import _from_json


class C1RegressionTests(unittest.TestCase):
    def test_zero_tally_text_is_preserved(self):
        self.assertEqual(_text(0), "0")

    def test_malformed_profile_id_falls_back(self):
        settings = _from_json(json.dumps({"profile_id": []}))
        self.assertEqual(settings.profile_id, "")

    def test_casefold_expansion_keeps_original_atomic_span(self):
        from app.services.agents.objection_handler import build_atomic_claims

        recommendation = type("Recommendation", (), {
            "target_claim": "Straße bleibt offen",
            "argument_points": ["STRASSE bleibt offen"],
        })()
        claims = build_atomic_claims(recommendation, parent_claim_id="claim-1")
        exact = next(claim for claim in claims if claim.start >= 0)
        self.assertEqual("Straße bleibt offen"[exact.start:exact.end], exact.text)


if __name__ == "__main__":
    unittest.main()
