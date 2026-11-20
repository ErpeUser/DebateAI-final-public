from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "video_eval_autotune.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("video_eval_autotune_controlled", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class ControlledAutotuneTests(unittest.TestCase):
    def _rows(self):
        return [
            {"case_id": "fixed-1", "split": "fixed", "metrics": {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100}},
            {"case_id": "holdout-1", "split": "holdout", "metrics": {"naturalness": .7, "factuality": .9, "argument_strength": .7, "source_honesty": .9, "latency_ms": 100}},
        ]

    def test_load_evaluation_rows_requires_same_case_contract(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "scores.json"
            path.write_text(json.dumps({"results": self._rows()}), encoding="utf-8")
            rows = module.load_evaluation_results(path)
        self.assertEqual(["fixed", "holdout"], [row.split for row in rows])
        self.assertEqual("fixed-1", rows[0].case_id)

    def test_controlled_decision_is_reportable_and_does_not_apply_by_default(self):
        baseline = module.load_evaluation_results_from_payload({"results": self._rows()})
        candidate = module.load_evaluation_results_from_payload({"results": [
            {**row, "metrics": {**row["metrics"], "naturalness": .8 if row["split"] == "fixed" else .7}}
            for row in self._rows()
        ]})
        report = module.build_optimization_report(baseline, candidate)
        self.assertTrue(report["decision"]["approved"])
        self.assertEqual("proposal_only", report["activation"]["status"])
        self.assertFalse(report["activation"]["applied"])

    def test_apply_requires_explicit_auto_flag(self):
        baseline = module.load_evaluation_results_from_payload({"results": self._rows()})
        candidate = module.load_evaluation_results_from_payload({"results": [
            {**row, "metrics": {**row["metrics"], "naturalness": .8}}
            for row in self._rows()
        ]})
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "prompt.txt").write_text("old", encoding="utf-8")
            result = module.apply_optimization(
                root,
                "prompt",
                "new",
                baseline,
                candidate,
                auto_apply=True,
                explicit_auto_apply=False,
            )
            self.assertEqual("rejected", result["status"])
            self.assertEqual("old", (root / "prompt.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
