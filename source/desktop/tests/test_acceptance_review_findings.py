"""Behavioral reproductions of independent acceptance-review findings."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class AcceptanceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / 'scripts' / 'run_acceptance.py'
        spec = importlib.util.spec_from_file_location('acceptance_review_target', path)
        cls.runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.runner
        spec.loader.exec_module(cls.runner)

    def test_contradictory_declared_junit_counts_cannot_pass(self):
        for attributes in ('tests="2" failures="1"', 'tests="999"', 'tests="1" errors="1"',
                           'tests="1" skipped="1"', 'tests="-1"', 'tests="true"'):
            with self.subTest(attributes=attributes), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'report.xml'
                path.write_text(f'<testsuite {attributes}><testcase/></testsuite>', encoding='utf-8')
                self.assertIsNone(self.runner.junit_counts(path))

    def test_consistent_nested_junit_counts_are_not_double_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.xml'
            path.write_text('<testsuites tests="3" failures="1" skipped="1"><testsuite tests="3" failures="1" skipped="1"><testcase/><testcase><failure/></testcase><testcase><skipped/></testcase></testsuite></testsuites>', encoding='utf-8')
            self.assertEqual(dict(total=3, failed=1, errors=0, skipped=1), self.runner.junit_counts(path))

    def test_parent_dotenv_blocks_child_without_reading_the_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cwd, output = root / 'nested', root / 'output'
            cwd.mkdir()
            output.mkdir()
            (root / '.env').write_text('SYNTHETIC_SECRET=unchanged', encoding='utf-8')
            marker = root / 'ran'
            code = f'from pathlib import Path; Path({str(marker)!r}).write_text("ran")'
            result = self.runner.run_check('parent-env', [sys.executable, '-c', code], cwd, output,
                                           dict(os.environ), kind='command')
            self.assertEqual('BLOCKED_EXTERNAL', result['status'])
            self.assertFalse(marker.exists())
            self.assertEqual('SYNTHETIC_SECRET=unchanged', (root / '.env').read_text())

    def test_import_root_dotenv_blocks_child_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module, cwd, output = root / 'module', root / 'commands', root / 'output'
            for directory in (module, cwd, output):
                directory.mkdir()
            (module / '.env').write_text('SYNTHETIC_SECRET=unchanged', encoding='utf-8')
            env = dict(os.environ, PYTHONPATH=str(module))
            result = self.runner.run_check('module-env', [sys.executable, '-c', 'print("ran")'],
                                           cwd, output, env, kind='command')
            self.assertEqual('BLOCKED_EXTERNAL', result['status'])

    def test_cleanup_timeout_is_recorded_as_failure_after_owned_tree_reaping(self):
        execution = sys.modules[self.runner.run_check.__module__]
        real = execution.OwnedProcess
        class CleanupTimeout(real):
            def close(self):
                super().close()
                raise subprocess.TimeoutExpired('synthetic cleanup acknowledgement', 5)
        with tempfile.TemporaryDirectory() as tmp, patch.object(execution, 'OwnedProcess', CleanupTimeout):
            root = Path(tmp)
            try:
                result = self.runner.run_check('cleanup-timeout', [sys.executable, '-c', 'pass'],
                                               root, root, dict(os.environ), kind='command')
            except subprocess.TimeoutExpired:
                self.fail('cleanup timeout escaped without a structured failed result')
            self.assertEqual('FAIL', result['status'])
            self.assertFalse(result['owned_cleanup_confirmed'])

    def test_file_link_admission_is_rejected_without_reading_its_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            target = source / 'module.py'
            target.write_text('value = 1\n')
            for args in (('init', '-q'), ('add', '.'), ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')):
                subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
            original = Path.is_symlink
            # Policy test independent of the user's Windows symlink privilege.
            with patch.object(Path, 'is_symlink', lambda path: path == target or original(path)):
                with self.assertRaises(ValueError):
                    self.runner.source_identity(source)

    def test_pytest_subtests_are_admitted_only_with_matching_captured_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            junit = root / 'fresh.xml'
            xml = '<testsuites><testsuite name="pytest" tests="3" errors="0" failures="0" skipped="0"><testcase/></testsuite></testsuites>'
            code = (f'from pathlib import Path; Path({str(junit)!r}).write_text({xml!r}); '
                    'print("1 passed, 2 subtests passed in 0.01s")')
            result = self.runner.run_check('subtests', [sys.executable, '-c', code],
                                           root, root, dict(os.environ), junit=junit)
            self.assertEqual('PASS', result['status'])
            self.assertEqual(1, result['counts']['total'])
            self.assertEqual(2, result['counts'].get('subtests_passed'))
            self.assertEqual(3, result['counts'].get('reported_total'))

    def test_mismatched_or_missing_pytest_subtest_summary_cannot_pass(self):
        for summary in ('1 passed, 3 subtests passed in 0.01s', 'no summary',
                        '1 passed, 2 subtests passed', '2 passed, 1 subtests passed in 0.01s'):
            with self.subTest(summary=summary), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                junit = root / 'fresh.xml'
                xml = '<testsuites><testsuite name="pytest" tests="3" failures="0"><testcase/></testsuite></testsuites>'
                code = f'from pathlib import Path; Path({str(junit)!r}).write_text({xml!r}); print({summary!r})'
                result = self.runner.run_check('bad-summary', [sys.executable, '-c', code],
                                               root, root, dict(os.environ), junit=junit)
                self.assertNotEqual('PASS', result['status'])


if __name__ == '__main__':
    unittest.main()
