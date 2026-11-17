"""Failed pytest runs must retain their observed denominator, never gain PASS."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest


class FailedSubtestEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / 'scripts' / 'run_acceptance.py'
        spec = importlib.util.spec_from_file_location('failed_subtest_runner', path)
        cls.runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.runner
        spec.loader.exec_module(cls.runner)

    def read_counts(self, outcome, summary):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fresh.xml'
            failures, errors = (1, 0) if outcome == 'failure' else (0, 1)
            path.write_text(
                f'<testsuites><testsuite name="pytest" tests="4" failures="{failures}" '
                f'errors="{errors}" skipped="0"><testcase><{outcome}/></testcase>'
                '<testcase/></testsuite></testsuites>', encoding='utf-8')
            return self.runner.junit_counts(path, terminal_output=summary)

    def test_failed_test_and_passing_subtests_keep_the_full_denominator(self):
        counts = self.read_counts('failure', '1 failed, 1 passed, 2 subtests passed in 0.01s')
        self.assertEqual(dict(total=2, failed=1, errors=0, skipped=0,
                              subtests_passed=2, reported_total=4), counts)
        self.assertEqual('FAIL', self.runner.test_status(1, counts))
        self.assertEqual('FAIL', self.runner.test_status(0, counts))

    def test_error_and_passing_subtests_keep_the_error_count(self):
        counts = self.read_counts('error', '1 passed, 1 error, 2 subtests passed in 0.01s')
        self.assertEqual(dict(total=2, failed=0, errors=1, skipped=0,
                              subtests_passed=2, reported_total=4), counts)
        self.assertEqual('FAIL', self.runner.test_status(1, counts))
        self.assertEqual('FAIL', self.runner.test_status(0, counts))

    def test_failure_summary_must_match_the_xml_exactly(self):
        for summary in ('2 passed, 2 subtests passed in 0.01s',
                        '1 failed, 1 passed, 3 subtests passed in 0.01s',
                        '1 failed, 1 skipped, 2 subtests passed in 0.01s',
                        '1 failed, 1 passed, 2 subtests passed', ''):
            with self.subTest(summary=summary):
                self.assertIsNone(self.read_counts('failure', summary))

    def test_failed_owned_child_keeps_counts_in_its_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            junit = root / 'owned.xml'
            xml = ('<testsuites><testsuite name="pytest" tests="3" failures="1" '
                   'errors="0" skipped="0"><testcase><failure/></testcase>'
                   '</testsuite></testsuites>')
            code = (f'from pathlib import Path; Path({str(junit)!r}).write_text({xml!r}); '
                    'print("1 failed, 2 subtests passed in 0.01s"); raise SystemExit(1)')
            result = self.runner.run_check('failed-child', [sys.executable, '-c', code],
                                           root, root, dict(os.environ), junit=junit)
            self.assertEqual('FAIL', result['status'])
            self.assertEqual(1, result['exit_code'])
            self.assertEqual(dict(total=1, failed=1, errors=0, skipped=0,
                                  subtests_passed=2, reported_total=3), result['counts'])
            self.assertTrue(result['owned_cleanup_confirmed'])


if __name__ == '__main__':
    unittest.main()
