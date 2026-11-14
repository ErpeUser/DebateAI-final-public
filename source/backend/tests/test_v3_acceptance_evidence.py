import math
import unittest

from scripts.validate_v3_acceptance_evidence import validate_evidence_package


def _common(requirement: str) -> dict:
    return {
        "requirement_id": requirement,
        "reference": {
            "sha256": "a" * 64,
            "language": "de",
            "duration_seconds": 120,
        },
        "environment": {
            "hardware_id": "machine-1",
            "software_commit": "commit-1",
            "load_profile": "mic+system+agents",
        },
        "artifacts": [
            {"kind": "raw_recording", "sha256": "b" * 64},
            {"kind": "transcript_export", "sha256": "c" * 64},
        ],
    }


class V3AcceptanceEvidenceTests(unittest.TestCase):
    def test_missing_evidence_is_incomplete_and_never_passed(self):
        result = validate_evidence_package({"requirement_id": "A21"})

        self.assertEqual("incomplete", result["status"])
        self.assertIn("reference.sha256", result["missing"])
        self.assertTrue(result["human_review_required"])
        self.assertNotIn("passed", result["status"])

    def test_a21_rejects_runs_with_different_reference_or_load(self):
        payload = _common("A21")
        payload["runs"] = [
            {
                "name": "asr_a",
                "reference_sha256": "a" * 64,
                "hardware_id": "machine-1",
                "load_profile": "mic+system+agents",
                "manual_correction": False,
                "metrics": {"wer": 0.1, "latency_ms": 10},
            },
            {
                "name": "asr_b",
                "reference_sha256": "d" * 64,
                "hardware_id": "machine-1",
                "load_profile": "mic-only",
                "manual_correction": False,
                "metrics": {"wer": 0.2, "latency_ms": 20},
            },
        ]

        result = validate_evidence_package(payload)

        self.assertEqual("incomplete", result["status"])
        self.assertTrue(any("same reference" in item for item in result["errors"]))
        self.assertTrue(any("same load" in item for item in result["errors"]))

    def test_a22_can_be_ready_for_manual_review_but_not_passed(self):
        payload = _common("A22")
        payload["reference"]["duration_seconds"] = 600
        payload["dataset_sha256"] = "d" * 64
        payload["future_data_excluded"] = True
        payload["denominator"] = 20
        payload["runs"] = [
            {
                "name": "production",
                "load_profile": "mic+system+agents",
                "metrics": {"latency_ms": 100, "error_rate": 0.1},
            },
            {
                "name": "reference",
                "load_profile": "mic+system+agents",
                "metrics": {"latency_ms": 120, "error_rate": 0.2},
            },
        ]
        payload["human_review"] = {
            "rater_ids": ["rater-anon-1"],
            "blinded": True,
            "ratings": [{"case": 1, "score": 3}],
        }

        result = validate_evidence_package(payload)

        self.assertEqual("ready_for_manual_review", result["status"])
        self.assertTrue(result["human_review_required"])
        self.assertEqual([], result["errors"])

    def test_rejects_non_numeric_reference_duration(self):
        payload = _common("A06")
        payload["reference"]["duration_seconds"] = "120"
        payload["scenario_flags"] = {
            "microphone": True,
            "system_audio": True,
            "overlap": True,
            "device_switch": True,
            "backlog": True,
        }
        payload["transcript_complete"] = True
        payload["terminal_state"] = "clean"

        result = validate_evidence_package(payload)

        self.assertEqual("incomplete", result["status"])
        self.assertTrue(any("duration_seconds" in item for item in result["errors"]))

    def test_a18_requires_blinded_anonymized_and_complete_case_ratings(self):
        payload = _common("A18")
        payload["modes"] = ["persuasive", "forceful"]
        payload["case_count"] = 10
        payload["human_review"] = {
            "rater_ids": ["Alice Example"],
            "blinded": False,
            "ratings": [{"case": 1, "score": 3}],
        }

        result = validate_evidence_package(payload)

        self.assertEqual("incomplete", result["status"])
        self.assertTrue(any("anonym" in item for item in result["errors"]))
        self.assertTrue(any("blind" in item for item in result["errors"]))
        self.assertTrue(any("case" in item and "rating" in item for item in result["errors"]))

    def test_a21_rejects_non_finite_or_negative_metrics(self):
        payload = _common("A21")
        payload["runs"] = [
            {
                "name": "asr_a",
                "reference_sha256": "a" * 64,
                "hardware_id": "machine-1",
                "load_profile": "mic+system+agents",
                "manual_correction": False,
                "metrics": {
                    "wer": -0.1,
                    "number_errors": 0,
                    "negation_errors": 0,
                    "latency_ms": math.inf,
                    "dropouts": 0,
                    "cpu_peak_mb": 100,
                },
            },
            {
                "name": "asr_b",
                "reference_sha256": "a" * 64,
                "hardware_id": "machine-1",
                "load_profile": "mic+system+agents",
                "manual_correction": False,
                "metrics": {
                    "wer": 0.2,
                    "number_errors": 0,
                    "negation_errors": 0,
                    "latency_ms": 20,
                    "dropouts": 0,
                    "cpu_peak_mb": 100,
                },
            },
        ]

        result = validate_evidence_package(payload)

        self.assertEqual("incomplete", result["status"])
        self.assertTrue(any("wer" in item or "latency_ms" in item for item in result["errors"]))

    def test_a06_requires_reproducible_recovery_events(self):
        payload = _common("A06")
        payload["scenario_flags"] = {
            "microphone": True,
            "system_audio": True,
            "overlap": True,
            "device_switch": True,
            "backlog": True,
        }
        payload["transcript_complete"] = True
        payload["terminal_state"] = "clean"
        payload["events"] = [
            {"type": "speaker_switch", "at_seconds": 12.5, "speaker_before": "spk-a", "speaker_after": "spk-b"},
            {"type": "device_switch", "at_seconds": 30, "track": "microphone", "before_endpoint_id": "old", "after_endpoint_id": "new"},
            {"type": "asr_failure", "at_seconds": 45, "track": "microphone", "injected": True, "visible_status": "reconnecting"},
        ]

        result = validate_evidence_package(payload)

        self.assertEqual("incomplete", result["status"])
        self.assertTrue(any("reconnect" in item for item in result["missing"] + result["errors"]))

    def test_a18_requires_both_modes_and_ten_cases(self):
        payload = _common("A18")
        payload["modes"] = ["persuasive"]
        payload["case_count"] = 9
        payload["human_review"] = {"rater_ids": ["rater-anon-1"], "ratings": []}

        result = validate_evidence_package(payload)

        self.assertEqual("incomplete", result["status"])
        self.assertTrue(any("two modes" in item for item in result["errors"]))
        self.assertTrue(any("10" in item for item in result["errors"]))


if __name__ == "__main__":
    unittest.main()
