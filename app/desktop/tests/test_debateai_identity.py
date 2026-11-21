import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class IdentityTests(unittest.TestCase):
    def load(self):
        path = ROOT / "debateai_identity.py"
        self.assertTrue(path.is_file())
        spec = importlib.util.spec_from_file_location("debateai_identity", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_brand_is_canonical(self):
        module = self.load()
        self.assertEqual(module.PRODUCT_NAME, "DebateAI")
        self.assertEqual(module.WINDOWS_LAUNCHER, "DebateAI.exe")
        self.assertEqual(module.WINDOWS_UPDATER, "DebateAIUpdater.exe")
        self.assertEqual(module.INSTANCE_HEADER, "X-DebateAI-Instance")

    def test_new_install_uses_independent_directory(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                module.resolve_data_root(base=Path(tmp), environment={}),
                Path(tmp) / "DebateAI",
            )
            self.assertFalse((Path(tmp) / "DebateAI").exists())

    def test_legacy_data_stays_untouched_until_explicit_import(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy = base / "Backchannel"
            legacy.mkdir()
            (legacy / "master.key").write_bytes(b"opaque-fixture")
            destination = module.resolve_data_root(base=base, environment={})
            self.assertEqual(destination, base / "DebateAI")
            self.assertFalse((destination / "master.key").exists())
            self.assertEqual((legacy / "master.key").read_bytes(), b"opaque-fixture")

    def test_non_empty_destination_is_never_overwritten(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy = base / "Backchannel"
            legacy.mkdir()
            (legacy / "old").write_text("old")
            destination = base / "DebateAI"
            destination.mkdir()
            (destination / "current").write_text("current")
            self.assertEqual(
                module.resolve_data_root(base=base, environment={}), destination
            )
            self.assertEqual((destination / "current").read_text(), "current")
            self.assertFalse((destination / "old").exists())

    def test_empty_destination_is_not_populated_implicitly(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy = base / "Backchannel"
            legacy.mkdir()
            (legacy / "master.key").write_bytes(b"opaque-fixture")
            destination = base / "DebateAI"
            destination.mkdir()
            self.assertEqual(
                module.resolve_data_root(base=base, environment={}), destination
            )
            self.assertFalse((destination / "master.key").exists())
            self.assertEqual((legacy / "master.key").read_bytes(), b"opaque-fixture")

    def test_explicit_new_override_has_priority(self):
        module = self.load()
        value = module.resolve_data_root(
            base=Path("/fixture"),
            environment={"DEBATEAI_DATA_DIR": "/new-fixture"},
        )
        self.assertEqual(value, Path("/new-fixture"))

    def test_lowercase_root_remains_canonical_without_migration(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy = base / "backchannel"
            legacy.mkdir()
            (legacy / "state").write_text("saved")
            self.assertEqual(
                module.resolve_data_root(base=base, environment={}, lowercase=True),
                base / "debateai",
            )
            self.assertFalse((base / "debateai" / "state").exists())
            self.assertEqual((legacy / "state").read_text(), "saved")

    def test_file_collision_is_not_used_as_data_directory(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "DebateAI").write_text("not a directory")
            with self.assertRaises(NotADirectoryError):
                module.resolve_data_root(base=Path(tmp), environment={})

    def test_resolution_never_copies_even_when_legacy_data_exists(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy = base / "Backchannel"
            legacy.mkdir()
            (legacy / "state").write_text("saved")
            with patch(
                "shutil.copytree", side_effect=AssertionError("implicit migration")
            ):
                self.assertEqual(
                    module.resolve_data_root(base=base, environment={}),
                    base / "DebateAI",
                )
            self.assertFalse((base / "DebateAI").exists())
            self.assertEqual((legacy / "state").read_text(), "saved")

    def test_unreadable_legacy_directory_does_not_change_selection(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "Backchannel").mkdir()
            with patch.object(
                Path, "iterdir", side_effect=PermissionError("synthetic read-only")
            ):
                self.assertEqual(
                    module.resolve_data_root(base=base, environment={}),
                    base / "DebateAI",
                )


if __name__ == "__main__":
    unittest.main()
