"""Run pytest with a measured denominator, including free functions and fixtures."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys


class MeasuredResults:
    """One outcome per test item; failed subtests cannot become a passed parent."""

    PRIORITY = {'passed': 0, 'skipped': 1, 'expected_failures': 2,
                'unexpected_successes': 3, 'failures': 4, 'errors': 5}

    def __init__(self):
        self.outcomes = {}
        self.collection_errors = set()

    def record(self, nodeid, outcome):
        old = self.outcomes.get(nodeid)
        if old is None or self.PRIORITY[outcome] > self.PRIORITY[old]:
            self.outcomes[nodeid] = outcome

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors.add(report.nodeid)

    def pytest_runtest_logreport(self, report):
        if report.failed:
            self.record(report.nodeid, 'failures' if report.when == 'call' else 'errors')
        elif report.skipped:
            self.record(report.nodeid, 'expected_failures' if hasattr(report, 'wasxfail') else 'skipped')
        elif report.when == 'call':
            self.record(report.nodeid, 'unexpected_successes' if hasattr(report, 'wasxfail') else 'passed')

    def counts(self):
        grouped = Counter(self.outcomes.values())
        counts = {'schema_version': 1, 'tests_run': len(self.outcomes)}
        counts.update({key: grouped[key] for key in self.PRIORITY})
        counts['errors'] += len(self.collection_errors)
        counts['failed_test_ids'] = sorted(node for node, result in self.outcomes.items()
                                          if result in {'failures', 'errors', 'unexpected_successes'})
        counts['collection_error_ids'] = sorted(self.collection_errors)
        return counts


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == '--':
        arguments.pop(0)
    sys.path.insert(0, str(Path.cwd()))
    plugin = MeasuredResults()
    try:
        import pytest
        raw_code = int(pytest.main(arguments or ['-q', 'tests'], plugins=[plugin]))
        counts = plugin.counts()
        if raw_code == 2 and not counts['errors']:
            code = 130
        elif raw_code or counts['tests_run'] == 0 or any(counts[k] for k in
                 ('failures', 'errors', 'unexpected_successes')):
            code = 1
        elif counts['skipped'] or counts['expected_failures']:
            code = 2
        else:
            code = 0
    except Exception as exc:
        counts = plugin.counts()
        counts['errors'] += 1
        counts['discovery_error'] = type(exc).__name__
        code = 1
    print('DEBATEAI_TEST_RESULT=' + json.dumps(counts, ensure_ascii=True, sort_keys=True), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
