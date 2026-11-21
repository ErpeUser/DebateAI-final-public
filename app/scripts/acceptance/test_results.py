"""Classify observed test denominators without turning empty or skipped runs green."""

from __future__ import annotations

import json
import re

FIELDS = (
    "tests_run",
    "passed",
    "failures",
    "errors",
    "skipped",
    "expected_failures",
    "unexpected_successes",
)


def classify(row, text, kind):
    if kind not in {"unittest", "node-tests"}:
        return
    try:
        if kind == "unittest":
            records = [
                line.split("=", 1)[1]
                for line in text.splitlines()
                if line.startswith("DEBATEAI_TEST_RESULT=")
            ]
            if len(records) != 1:
                raise ValueError("Expected one authoritative test summary")
            counts = json.loads(records[0])
            if not isinstance(counts, dict) or counts.get("schema_version") != 1:
                raise ValueError("Invalid summary schema")
            counts = {key: counts[key] for key in FIELDS}
        else:
            pairs = dict(
                re.findall(
                    r"^# (tests|pass|fail|skipped|todo|cancelled) (\d+)\s*$",
                    text,
                    re.MULTILINE,
                )
            )
            counts = {
                "tests_run": int(pairs["tests"]),
                "passed": int(pairs["pass"]),
                "failures": int(pairs["fail"]),
                "errors": int(pairs.get("cancelled", 0)),
                "skipped": int(pairs.get("skipped", 0)),
                "expected_failures": int(pairs.get("todo", 0)),
                "unexpected_successes": 0,
            }
            if counts["tests_run"] != sum(counts[key] for key in FIELDS[1:]):
                raise ValueError("Inconsistent TAP denominator")
        if any(type(value) is not int or value < 0 for value in counts.values()):
            raise ValueError("Test counts must be nonnegative integers")
        if counts["tests_run"] == 0 or counts["passed"] > counts["tests_run"]:
            raise ValueError("No positive, consistent test denominator")
        row["tests"] = counts
        failures = (
            counts["failures"] + counts["errors"] + counts["unexpected_successes"]
        )
        skipped = counts["skipped"] + counts["expected_failures"]
        if row["status"] in {"PASSED", "FAILED"}:
            if failures:
                row.update(status="FAILED", reason="Test failures")
            elif skipped and row["returncode"] in (0, 2):
                row.update(
                    status="INCOMPLETE",
                    reason="Skipped or expected-failure cases require separate review",
                )
            elif row["returncode"] == 0 and counts["passed"] != counts["tests_run"]:
                row.update(
                    status="FAILED", reason="Incomplete successful test accounting"
                )
    except (ValueError, KeyError, TypeError):
        if row["status"] == "PASSED":
            row.update(status="FAILED", reason="Missing or invalid test-count evidence")
