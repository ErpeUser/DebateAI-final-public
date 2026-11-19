from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[2]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from scripts.generated_paths import ensure_output_path, output_dir


class GeneratedPathTests(unittest.TestCase):
    def test_output_directories_are_below_generated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = output_dir("benchmarks", root)
            self.assertEqual(target, root / "DebateAI_Generated" / "reports" / "benchmarks")

    def test_external_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                ensure_output_path(root / "app" / "result.json", "benchmarks", root)

    def test_nested_generated_output_is_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = ensure_output_path(
                root / "DebateAI_Generated" / "reports" / "benchmarks" / "run.json",
                "benchmarks",
                root,
            )
            self.assertTrue(target.parent.is_dir())


if __name__ == "__main__":
    unittest.main()
