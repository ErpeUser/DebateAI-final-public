import json
import unittest
from types import SimpleNamespace

from app.services.agents.opportunity_specialist import (
    _build_opportunities_json,
    _parse_mappings,
)


class ParseMappingsTests(unittest.TestCase):
    def test_opportunity_json_is_compact_and_bounded(self):
        questions = [
            SimpleNamespace(
                id=f"id-{index}",
                question="Opportunity " + ("x" * 180),
                rationale="Rationale " + ("y" * 180),
                source_context="Context " + ("z" * 180),
            )
            for index in range(20)
        ]
        rendered = _build_opportunities_json(questions, budget=900)
        self.assertLessEqual(len(rendered), 900)
        self.assertIsInstance(json.loads(rendered), list)
        self.assertNotIn(": ", rendered)

    def test_bare_json_array(self):
        raw = '[{"id": "abc", "offering_match": "match"}]'
        self.assertEqual(
            _parse_mappings(raw), [{"id": "abc", "offering_match": "match"}]
        )

    def test_fenced_json_array(self):
        raw = '```json\n[{"id": "abc", "offering_match": "match"}]\n```'
        self.assertEqual(
            _parse_mappings(raw), [{"id": "abc", "offering_match": "match"}]
        )

    def test_garbage_with_embedded_array(self):
        raw = 'Here are the mappings: [{"id": "abc", "offering_match": "m"}] hope that helps!'
        self.assertEqual(_parse_mappings(raw), [{"id": "abc", "offering_match": "m"}])

    def test_empty_and_empty_array(self):
        self.assertEqual(_parse_mappings(""), [])
        self.assertEqual(_parse_mappings("[]"), [])
        self.assertEqual(_parse_mappings("```json\n[]\n```"), [])

    def test_unparseable_returns_none(self):
        self.assertIsNone(_parse_mappings("no json here"))
        self.assertIsNone(_parse_mappings("[ this is { not json ]"))

    def test_non_list_json_returns_empty(self):
        self.assertEqual(_parse_mappings('{"id": "abc"}'), [])


if __name__ == "__main__":
    unittest.main()
