"""A failed browser setup must not poison the next class's event loop."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class FixtureCleanupTests(unittest.TestCase):
    def test_failed_class_setup_releases_playwright_for_next_suite(self):
        source = r"""
import io, os, unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_import_evidence import ImportEvidenceBrowserTests
suite = unittest.TestSuite([ImportEvidenceBrowserTests('test_wrong_denominator_rejected')])
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
assert len(result.errors) == 1, 'Expected deliberate browser startup failure'
assert 'intentional-missing-browser' in str(result.errors), 'Explicit browser override was ignored'
with sync_playwright() as runtime:
    assert runtime.chromium.name == 'chromium'
"""
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ, PLAYWRIGHT_CHROMIUM_EXECUTABLE=str(Path(tmp)/'intentional-missing-browser.exe'),
                     PLAYWRIGHT_BROWSERS_PATH=str(Path(tmp)/'empty-browser-cache'))
            result=subprocess.run([sys.executable,'-c',source],cwd=Path(__file__).parent,
                                  env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(0,result.returncode,result.stderr)

if __name__=='__main__': unittest.main()
