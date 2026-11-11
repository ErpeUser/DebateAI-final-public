import math
import unittest

from app.services.response_contract import (
    ResponseContractError,
    ResponseEvent,
    normalize_response_event,
    validate_response_event,
)


class ResponseContractTests(unittest.TestCase):
    def test_valid_event_has_lineage_and_preserves_unknown_fields(self):
        event = normalize_response_event(
            {
                "case_id": "de-001",
                "turn_id": "turn-1",
                "claim_id": "claim-7",
                "revision_of": "claim-6",
                "first_update_ms": 120,
                "final_update_ms": 240,
                "future_field": "kept",
            }
        )
        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["status"], "ok")
        self.assertEqual(event["failure_class"], "none")
        self.assertEqual(event["future_field"], "kept")
        validate_response_event(event)

    def test_slotted_event_round_trips(self):
        event = ResponseEvent.from_mapping(
            {
                "case_id": "de-002",
                "turn_id": "turn-2",
                "claim_id": "claim-8",
                "first_speakable_ms": 40,
            }
        )
        self.assertEqual(event.to_dict()["case_id"], "de-002")
        self.assertEqual(event.to_dict()["first_speakable_ms"], 40.0)

    def test_revision_requires_claim(self):
        with self.assertRaises(ResponseContractError):
            validate_response_event(
                {"case_id": "de-003", "turn_id": "turn-3", "revision_of": "claim-1"}
            )

    def test_final_update_cannot_precede_first_update(self):
        with self.assertRaises(ResponseContractError):
            validate_response_event(
                {
                    "case_id": "de-004",
                    "turn_id": "turn-4",
                    "first_update_ms": 200,
                    "final_update_ms": 100,
                }
            )

    def test_latencies_are_finite_and_nonnegative(self):
        for value in (-1, math.inf, math.nan, True, "10"):
            with self.subTest(value=value):
                with self.assertRaises(ResponseContractError):
                    validate_response_event(
                        {
                            "case_id": "de-005",
                            "turn_id": "turn-5",
                            "first_speakable_ms": value,
                        }
                    )

    def test_failure_states_stay_in_the_contract(self):
        for status in ("timeout", "empty", "stale", "error", "abstent"):
            with self.subTest(status=status):
                event = normalize_response_event(
                    {"case_id": "de-006", "turn_id": status, "status": status}
                )
                self.assertEqual(event["status"], status)
                self.assertEqual(event["failure_class"], status)

    def test_ok_cannot_have_failure_class(self):
        with self.assertRaises(ResponseContractError):
            validate_response_event(
                {
                    "case_id": "de-007",
                    "turn_id": "turn-7",
                    "status": "ok",
                    "failure_class": "timeout",
                }
            )


if __name__ == "__main__":
    unittest.main()
