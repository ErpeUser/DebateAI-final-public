"""Real child-process contracts for the acceptance runner, without product data."""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class ExecutionTests(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module('acceptance.execution')
        except ModuleNotFoundError as exc:
            self.fail('Acceptance executor is not implemented: ' + str(exc))
        self.temp = tempfile.TemporaryDirectory(prefix='acceptance path ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def step(self, name, code, **kwargs):
        return self.m.Step(name, (sys.executable, '-c', code), **kwargs)

    def execute(self, steps, **kwargs):
        return self.m.run_steps(steps, self.root, self.root/'logs', env=dict(os.environ), **kwargs)

    def test_real_exit_code_and_independent_continuation(self):
        result = self.execute([self.step('fails', 'raise SystemExit(7)'), self.step('next', "print('ran')")])
        self.assertEqual(['FAILED', 'PASSED'], [r['status'] for r in result])
        self.assertEqual(7, result[0]['returncode'])
        self.assertIn('ran', (self.root/'logs/next.log').read_text())

    def test_missing_command_is_blocked_not_passed(self):
        result = self.execute([self.m.Step('missing', ('__debateai_absent_executable__',)), self.step('next', 'print(1)')])
        self.assertEqual(['BLOCKED', 'PASSED'], [r['status'] for r in result])

    def test_failed_dependency_does_not_prevent_independent_task(self):
        result = self.execute([self.step('build', 'raise SystemExit(1)'),
            self.step('dependent', "print('must not run')", depends_on=('build',)), self.step('other', 'print(1)')])
        self.assertEqual(['FAILED', 'BLOCKED', 'PASSED'], [r['status'] for r in result])
        self.assertFalse((self.root/'logs/dependent.log').exists())

    def test_task_completion_callback_is_emitted_for_each_task(self):
        seen = []
        self.execute([self.step('first', 'print(1)'), self.m.Step('hardware', (), blocked_reason='Real device required')], on_result=seen.append)
        self.assertEqual(['first', 'hardware'], [r['id'] for r in seen])

    def test_timeout_is_bounded_failure(self):
        start = time.monotonic()
        result = self.execute([self.step('hang', 'import time; time.sleep(30)', timeout=0.8)])
        self.assertEqual('TIMED_OUT', result[0]['status'])
        self.assertLess(time.monotonic()-start, 8)

    def test_overflow_omits_output_including_split_secret(self):
        secret = 'PRIVATE-CREDENTIAL-MUST-NOT-LEAK'
        result = self.execute([self.step('large', f"print('x'*1018+{secret!r}+'x'*100000)")], max_output=1024, secrets=(secret,))
        self.assertEqual('OUTPUT_LIMIT', result[0]['status'])
        log = (self.root/'logs/large.log').read_text()
        self.assertNotIn('PRIVAT', log)
        self.assertLess(len(log), 1024)

    def test_secret_is_redacted_across_chunks(self):
        secret = 'private-test-token-123456789'
        result = self.execute([self.step('redact', f"print('x'*4080+{secret!r})")], secrets=(secret,))
        self.assertEqual('PASSED', result[0]['status'])
        text = (self.root/'logs/redact.log').read_text()
        self.assertNotIn(secret, text)
        self.assertIn('[REDACTED]', text)

    def test_invalid_plan_rejected_before_first_command(self):
        marker = self.root/'ran'
        first = self.step('first', f"from pathlib import Path; Path({str(marker)!r}).touch()")
        for bad in (self.step('first', 'print(1)'), self.step('../escape', 'print(1)'),
                    self.step('bad', 'print(1)', cwd='..'), self.step('bad', 'print(1)', timeout=float('nan')),
                    self.step('bad', 'print(1)', depends_on=('unknown',))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.execute([first,bad])
        self.assertFalse(marker.exists())

    def test_logs_are_never_overwritten(self):
        self.execute([self.step('original', "print('keep')")])
        with self.assertRaises(FileExistsError):
            self.execute([self.step('original', "print('replace')")])
        self.assertIn('keep', (self.root/'logs/original.log').read_text())

    def test_arguments_are_not_shell_interpreted(self):
        step = self.m.Step('literal',(sys.executable,'-c','import sys; print(sys.argv[1])',';echo NOT_A_COMMAND'))
        result=self.execute([step])
        self.assertEqual('PASSED',result[0]['status'])
        self.assertIn(';echo NOT_A_COMMAND',(self.root/'logs/literal.log').read_text())

    def check_descendant(self, parent_waits):
        ready, escaped = self.root/'ready', self.root/'escaped'
        child = f"import time; from pathlib import Path; Path({str(ready)!r}).touch(); time.sleep(1.5); Path({str(escaped)!r}).touch()"
        parent = (f"import subprocess,sys,time; from pathlib import Path; subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);\n"
                  f"while not Path({str(ready)!r}).exists(): time.sleep(0.01)\n" + ('time.sleep(30)' if parent_waits else ''))
        result=self.execute([self.step('tree',parent,timeout=1 if parent_waits else 10)])
        self.assertEqual('TIMED_OUT' if parent_waits else 'PASSED',result[0]['status'])
        self.assertTrue(ready.exists(), 'The child must actually start for this test to prove cleanup')
        time.sleep(1.8)
        self.assertFalse(escaped.exists(), 'An owned child survived completion or cancellation')

    def test_timeout_terminates_real_descendant(self):
        self.check_descendant(True)

    def test_successful_parent_cannot_leave_background_child(self):
        self.check_descendant(False)

if __name__=='__main__':
    unittest.main()
