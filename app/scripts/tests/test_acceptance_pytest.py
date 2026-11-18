"""Full acceptance must include pytest functions, fixtures and setup failures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


class CheckedPytestTests(unittest.TestCase):
    def run_case(self, source):
        entry = SCRIPTS / 'acceptance/checked_pytest.py'
        self.assertTrue(entry.is_file(), 'Checked pytest entry not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if source:
                (root / 'test_example.py').write_text(source, encoding='utf-8')
            env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
            env.pop('PYTEST_ADDOPTS', None)
            result = subprocess.run([sys.executable, str(entry), '--', '-q', str(root)],
                cwd=root, env=env, capture_output=True, text=True, timeout=30)
            records = [line.split('=', 1)[1] for line in result.stdout.splitlines()
                       if line.startswith('DEBATEAI_TEST_RESULT=')]
            self.assertEqual(1, len(records), result.stdout + result.stderr)
            return result.returncode, json.loads(records[0])

    def test_free_functions_and_unittest_classes_are_both_executed(self):
        code, row = self.run_case('import unittest\ndef test_function(): assert 2+2 == 4\nclass T(unittest.TestCase):\n def test_method(self): self.assertEqual(3, 1+2)\n')
        self.assertEqual(0, code)
        self.assertEqual(2, row['tests_run'])
        self.assertEqual(2, row['passed'])

    def test_zero_tests_is_failure(self):
        code, row = self.run_case('')
        self.assertEqual(1, code)
        self.assertEqual(0, row['tests_run'])

    def test_skips_are_incomplete_not_passed(self):
        code, row = self.run_case('import pytest\n@pytest.mark.skip(reason="hardware missing")\ndef test_skip(): pass\n')
        self.assertEqual(2, code)
        self.assertEqual(1, row['skipped'])
        self.assertEqual(0, row['passed'])

    def test_setup_error_is_failure(self):
        code, row = self.run_case('import pytest\n@pytest.fixture\ndef broken(): raise RuntimeError("setup failed")\ndef test_it(broken): pass\n')
        self.assertEqual(1, code)
        self.assertEqual(1, row['errors'])
        self.assertEqual(0, row['passed'])

    def test_teardown_failure_does_not_count_as_passed(self):
        code, row = self.run_case('import pytest\n@pytest.fixture\ndef broken():\n yield\n raise RuntimeError("teardown failed")\ndef test_it(broken): assert True\n')
        self.assertEqual(1, code)
        self.assertEqual(1, row['errors'])
        self.assertEqual(0, row['passed'])

    def test_collection_error_is_failure_with_zero_execution(self):
        code, row = self.run_case('raise RuntimeError("import failed")\n')
        self.assertEqual(1, code)
        self.assertEqual(0, row['tests_run'])
        self.assertGreater(row['errors'], 0)

    def test_failed_assertion_and_unexpected_success_are_failures(self):
        for source, field in [('def test_it(): assert False\n', 'failures'),
            ('import pytest\n@pytest.mark.xfail\ndef test_it(): assert True\n', 'unexpected_successes')]:
            with self.subTest(field=field):
                code, row = self.run_case(source)
                self.assertEqual(1, code)
                self.assertEqual(1, row[field])

    def test_full_backend_profile_uses_function_aware_collector(self):
        from acceptance.catalog import build_plan
        with tempfile.TemporaryDirectory() as tmp, patch('acceptance.catalog.sys.version_info', (3, 12)):
            root = Path(tmp)
            (root / 'app/backend/tests').mkdir(parents=True)
            (root / 'app/backend/tests/test_function.py').write_text('def test_example(): assert True')
            step = next(item for item in build_plan('Full', root, python=sys.executable) if item.id == 'backend')
            self.assertTrue(any(Path(arg).name == 'checked_pytest.py' for arg in step.argv))
            self.assertEqual('', step.blocked_reason)


if __name__ == '__main__':
    unittest.main()
