"""Stable public imports and edge cases for shared interval parsing."""

import unittest

from app.services.agents.orchestrator import _parse_model_intervals as scheduler_parser
from app.services.local_fit import parse_model_intervals as fit_parser
from app.services.model_intervals import parse_model_intervals


class ModelIntervalParserTests(unittest.TestCase):
    def test_both_historical_entrypoints_are_the_same_callable(self):
        self.assertIs(fit_parser, parse_model_intervals)
        self.assertIs(scheduler_parser, parse_model_intervals)

    def test_valid_numeric_values_keep_the_original_semantics(self):
        raw = '{"model-a": 35, "model-b": 49.5, "zero": 0, "negative": -3}'
        expected = {"model-a": 35, "model-b": 49, "zero": 0, "negative": -3}
        self.assertEqual(parse_model_intervals(raw), expected)

    def test_invalid_payloads_are_empty(self):
        for value in ("", "not json", "[]", "null", "4", '"string"'):
            with self.subTest(value=value):
                self.assertEqual(parse_model_intervals(value), {})

    def test_bool_strings_and_nested_values_are_not_intervals(self):
        raw = '{"enabled": true, "numeric_string": "60", "nested": {}, "valid": 40}'
        self.assertEqual(parse_model_intervals(raw), {"valid": 40})

    def test_nonfinite_values_cannot_crash_scheduling(self):
        self.assertEqual(
            parse_model_intervals('{"nan": NaN, "infinite": Infinity, "valid": 15}'),
            {"valid": 15},
        )

    def test_type_mismatch_is_not_fatal(self):
        self.assertEqual(parse_model_intervals(None), {})


if __name__ == "__main__":
    unittest.main()
