"""Run existing unittest suites with explicit counts; zero tests is never success."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest


class CountedResult(unittest.TextTestResult):
    """Count successful test methods, not failed subtest events subtracted twice."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = 0

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed += 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', required=True)
    parser.add_argument('--pattern', default='test_*.py')
    args = parser.parse_args(argv)
    # Match python -m unittest: project-local modules resolve from the selected cwd.
    sys.path.insert(0, str(Path.cwd()))
    try:
        suite = unittest.TestLoader().discover(args.start, pattern=args.pattern)
        result = unittest.TextTestRunner(verbosity=2, resultclass=CountedResult).run(suite)
        counts = {
            'schema_version': 1,
            'tests_run': result.testsRun,
            'passed': result.passed,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'expected_failures': len(result.expectedFailures),
            'unexpected_successes': len(result.unexpectedSuccesses),
            'failed_test_ids': [test.id() for test, _ in result.failures + result.errors],
        }
        if not result.wasSuccessful() or result.testsRun == 0:
            code = 1
        elif result.skipped or result.expectedFailures:
            code = 2
        else:
            code = 0
    except Exception as exc:
        counts = {'schema_version': 1, 'tests_run': 0, 'passed': 0, 'failures': 0,
                  'errors': 1, 'skipped': 0, 'expected_failures': 0,
                  'unexpected_successes': 0, 'discovery_error': type(exc).__name__}
        code = 1
    print('DEBATEAI_TEST_RESULT=' + json.dumps(counts, ensure_ascii=True, sort_keys=True), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
