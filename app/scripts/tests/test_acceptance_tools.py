"""Prepared audit/browser tools do not replace the production interpreter."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from acceptance.catalog import build_plan, isolated_environment


class ToolEnvironmentTests(unittest.TestCase):
    def test_existing_tools_environment_is_used_only_for_audit_and_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = root / ('app/.acceptance-venv/Scripts/python.exe' if os.name == 'nt'
                           else 'app/.acceptance-venv/bin/python')
            tool.parent.mkdir(parents=True)
            tool.write_text('fixture executable path only')
            (root / 'app/frontend/calibration-tests').mkdir(parents=True)
            (root / 'app/frontend/calibration-tests/test_one.py').write_text('')
            plan = {s.id:s for s in build_plan('Full', root, python=sys.executable)}
            for key in ('security-bandit', 'dependency-python-audit', 'calibration-browser'):
                self.assertEqual(str(tool), plan[key].argv[0], key)
            self.assertEqual(sys.executable, plan['backend'].argv[0])
            self.assertEqual(sys.executable, plan['runner-contracts'].argv[0])

    def test_missing_tools_environment_uses_selected_python_without_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = build_plan('Security', root, python=sys.executable)
            self.assertEqual(sys.executable, next(s for s in rows if s.id=='security-bandit').argv[0])
            self.assertFalse((root/'app/.acceptance-venv').exists())

    def test_explicit_existing_browser_binary_is_preserved_without_user_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root/'browser.exe'
            binary.write_bytes(b'fixture')
            parent = {'PATH':os.defpath, 'PLAYWRIGHT_CHROMIUM_EXECUTABLE':str(binary),
                      'PLAYWRIGHT_USER_DATA_DIR':'C:/private-browser', 'LOCALAPPDATA':'C:/real'}
            env = isolated_environment(root, root/'sandbox', parent)
            self.assertEqual(str(binary), env.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
            self.assertNotIn('PLAYWRIGHT_USER_DATA_DIR', env)
            self.assertNotEqual('C:/real', env['LOCALAPPDATA'])

    def test_invalid_browser_override_is_not_forwarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for value in ('relative.exe', str(root/'missing.exe'), str(root)):
                with self.subTest(value=value):
                    env=isolated_environment(root,root/'sandbox',{'PLAYWRIGHT_CHROMIUM_EXECUTABLE':value})
                    self.assertNotIn('PLAYWRIGHT_CHROMIUM_EXECUTABLE',env)


if __name__ == '__main__':
    unittest.main()
