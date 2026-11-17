"""Real synthetic subprocess probes; never signal unrelated PIDs or servers."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


class AcceptanceOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / 'scripts' / 'run_acceptance.py'
        spec = importlib.util.spec_from_file_location('acceptance_ownership_target', path)
        cls.runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.runner
        spec.loader.exec_module(cls.runner)

    def test_descendant_is_reaped_when_its_parent_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started, survived = root / 'started', root / 'survived'
            child = ('from pathlib import Path; import time; '
                     f'Path({str(started)!r}).write_text("started"); '
                     f'time.sleep(0.8); Path({str(survived)!r}).write_text("survived")')
            parent = ('from pathlib import Path\nimport subprocess,sys,time\n'
                      f'subprocess.Popen([sys.executable,"-c",{child!r}])\n'
                      'deadline=time.monotonic()+3\n'
                      f'while not Path({str(started)!r}).exists() and time.monotonic()<deadline: time.sleep(0.01)\n')
            result = self.runner.run_check('owned-tree', [sys.executable, '-c', parent],
                                           root, root, dict(os.environ), timeout=5, kind='command')
            self.assertEqual(0, result['exit_code'])
            self.assertTrue(started.exists(), 'probe child never started')
            # Legacy implementation lets this owned child finish on its own;
            # the wait also ensures that the RED probe leaves no stray child.
            time.sleep(1.1)
            self.assertFalse(survived.exists(), 'successful parent leaked its child process')

    def test_output_overflow_is_bounded_and_not_a_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.runner.run_check('bounded-output',
                [sys.executable, '-c', 'import sys; sys.stdout.write("x"*(6*1024*1024))'],
                root, root, dict(os.environ), timeout=5, kind='command')
            self.assertEqual('FAIL', result['status'])
            self.assertLessEqual((root / 'bounded-output.log').stat().st_size, 4*1024*1024)

    def test_credentials_and_original_user_profile_are_not_inherited(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root / 'source', root / 'output'
            with patch.dict(os.environ, {'GITHUB_TOKEN': 'synthetic-token',
                                        'AWS_SECRET_ACCESS_KEY': 'synthetic-secret',
                                        'HOME': str(root / 'real-home')}, clear=True):
                env = self.runner._environment(source, output)
            self.assertNotIn('GITHUB_TOKEN', env)
            self.assertNotIn('AWS_SECRET_ACCESS_KEY', env)
            for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP', 'HF_HOME'):
                self.assertIn(key, env)
                self.assertTrue(Path(env[key]).is_relative_to(output), key)

    def test_user_dotenv_blocks_execution_without_reading_or_deleting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dotenv = root / '.env'
            dotenv.write_text('SYNTHETIC_SECRET=leave_unchanged', encoding='utf-8')
            marker = root / 'ran'
            code = f'from pathlib import Path; Path({str(marker)!r}).write_text("ran")'
            result = self.runner.run_check('dotenv', [sys.executable, '-c', code],
                                           root, root, dict(os.environ), kind='command')
            self.assertEqual('BLOCKED_EXTERNAL', result['status'])
            self.assertFalse(marker.exists())
            self.assertEqual('SYNTHETIC_SECRET=leave_unchanged', dotenv.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
