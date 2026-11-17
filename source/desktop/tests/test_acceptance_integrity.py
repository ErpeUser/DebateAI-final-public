"""Evidence identity and fail-closed result admission; all child data synthetic."""
import importlib.util
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class AcceptanceIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / 'scripts' / 'run_acceptance.py'
        spec = importlib.util.spec_from_file_location('acceptance_integrity_target', path)
        cls.runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.runner
        spec.loader.exec_module(cls.runner)

    def make_repository(self, root):
        source = root / 'source'
        source.mkdir()
        (source / 'sample.py').write_text('value = 0\n', encoding='utf-8')
        (root / '.gitignore').write_text('source/runtime/\n', encoding='utf-8')
        for args in (('init', '-q'), ('add', '.'),
                     ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '-qm', 'synthetic baseline')):
            subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
        return source

    def test_tracked_edits_cannot_share_the_same_evidence_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_repository(Path(tmp))
            target = source / 'sample.py'
            target.write_text('value = 1\n', encoding='utf-8')
            before = self.runner.source_identity(source)
            target.write_text('value = 2\n', encoding='utf-8')
            self.assertNotEqual(before, self.runner.source_identity(source))

    def test_untracked_edits_cannot_share_the_same_evidence_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_repository(Path(tmp))
            target = source / 'new.py'
            target.write_text('value = 1\n', encoding='utf-8')
            before = self.runner.source_identity(source)
            target.write_text('value = 2\n', encoding='utf-8')
            self.assertNotEqual(before, self.runner.source_identity(source))

    def test_ignored_runtime_data_is_outside_the_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_repository(Path(tmp))
            before = self.runner.source_identity(source)
            (source / 'runtime').mkdir()
            (source / 'runtime' / 'sample.txt').write_text('synthetic runtime data')
            self.assertEqual(before, self.runner.source_identity(source))

    def test_boolean_exit_metadata_cannot_pass(self):
        counts = dict(total=1, failed=0, errors=0, skipped=0)
        for code in (False, True, None, '0'):
            with self.subTest(code=code):
                self.assertNotEqual('PASS', self.runner.test_status(code, counts))

    def test_node_summary_needs_complete_consistent_pass_counts(self):
        for text in (
            '# tests 1\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n',
            '# tests 2\n# pass 1\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n',
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.runner.log_counts(text))

    def test_last_unittest_run_controls_counts(self):
        text = 'Ran 2 tests in 0.1s\nOK\nRan 3 tests in 0.1s\nFAILED (failures=1)\n'
        self.assertEqual(dict(total=3, failed=1, errors=0, skipped=0), self.runner.log_counts(text))

    def test_unfinished_last_unittest_run_cannot_reuse_earlier_success(self):
        text = 'Ran 2 tests in 0.1s\nOK\nRan 3 tests in 0.1s\n'
        self.assertIsNone(self.runner.log_counts(text))

    def test_unrelated_xml_or_entity_declarations_are_not_junit_evidence(self):
        for body in ('<unrelated><testcase/></unrelated>',
                     '<!DOCTYPE testsuite [<!ENTITY x "synthetic">]><testsuite><testcase>&x;</testcase></testsuite>'):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'report.xml'
                path.write_text(body, encoding='utf-8')
                self.assertIsNone(self.runner.junit_counts(path))

    def test_stale_junit_cannot_be_reused_by_a_new_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            junit = root / 'stale.xml'
            junit.write_text('<testsuite><testcase/></testsuite>', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.runner.run_check('stale', [sys.executable, '-c', 'print("no tests")'],
                                      root, root, dict(os.environ), junit=junit)

    def test_invalid_timeouts_are_rejected_before_starting_a_child(self):
        for timeout in (0, -1, True, math.inf, math.nan):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with self.assertRaises(ValueError):
                    self.runner.run_check('invalid-timeout', [sys.executable, '-c', 'pass'],
                                          root, root, dict(os.environ), timeout=timeout)
                self.assertFalse((root / 'invalid-timeout.log').exists())


if __name__ == '__main__':
    unittest.main()
