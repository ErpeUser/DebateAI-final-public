"""Contracts for the bounded static-analysis baseline generator."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP = Path(__file__).resolve().parents[2]
ROOT = APP.parent
SPEC = importlib.util.spec_from_file_location(
    "debateai_static_analysis_baseline", APP / "scripts/static_analysis_baseline.py"
)
assert SPEC and SPEC.loader
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


class StaticAnalysisBaselineTests(unittest.TestCase):
    def test_tool_configs_are_pinned_and_scope_is_bounded(self):
        tools = json.loads((APP / "scripts/static-analysis/package.json").read_text())
        self.assertEqual("6.46.1", tools["dependencies"]["knip"])
        self.assertEqual("18.8.0", tools["dependencies"]["dependency-cruiser"])
        self.assertIn(
            "deptry==0.25.1",
            (APP / "scripts/static-analysis/requirements-lock.txt").read_text(),
        )
        config = (
            APP / "scripts/static-analysis/dependency-cruiser.config.cjs"
        ).read_text()
        for package in ("frontend", "docs-site", "release-signing-worker"):
            self.assertIn(package, config)
        for generated in ("node_modules", "dist-site", "generated", "runtime"):
            self.assertIn(generated, config)

    def test_compact_reports_preserve_triage_findings_without_full_graph(self):
        knip = baseline._compact("knip", {"issues": [{"file": "src/a.ts"}]})
        self.assertEqual(1, knip["issue_count"])
        cruiser = baseline._compact(
            "dependency-cruiser",
            {
                "modules": [{"source": "src/a.ts"}],
                "summary": {
                    "violations": [{"rule": {"name": "no-circular"}}],
                    "error": 1,
                    "warn": 0,
                    "info": 0,
                    "ignore": 0,
                    "totalCruised": 1,
                    "totalDependenciesCruised": 2,
                    "issues": [],
                },
            },
        )
        self.assertEqual(1, cruiser["modules"])
        self.assertEqual(1, len(cruiser["violations"]))
        self.assertNotIn("modules", cruiser["violations"][0])

    def test_default_mode_is_non_gating_and_never_installs_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "baseline.json"
            fake = {
                "schema_version": 1,
                "generated_from": {},
                "scope": {},
                "gating": "baseline_only",
                "tools": [],
            }
            with mock.patch.object(baseline, "build_report", return_value=fake):
                self.assertEqual(
                    0, baseline.main(["--root", temp, "--output", str(output)])
                )
            self.assertEqual(fake, json.loads(output.read_text()))

    def test_strict_mode_detects_missing_optional_analyzers(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "baseline.json"
            fake = {
                "schema_version": 1,
                "generated_from": {},
                "scope": {},
                "gating": "baseline_only",
                "tools": [
                    {"tool": "knip", "status": "not_installed"},
                    {"tool": "dependency-cruiser", "status": "clean"},
                    {
                        "tool": "deptry",
                        "status": "not_installed",
                        "scopes": [{"status": "not_installed"}],
                    },
                ],
            }
            with mock.patch.object(baseline, "build_report", return_value=fake):
                self.assertEqual(
                    1,
                    baseline.main(
                        ["--root", temp, "--output", str(output), "--strict"]
                    ),
                )


if __name__ == "__main__":
    unittest.main()
