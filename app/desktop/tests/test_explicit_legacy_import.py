"""Explicit importer uses synthetic file-only roots, never real AppData."""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def importer():
    path = ROOT / "tools" / "legacy_data_import.py"
    spec = importlib.util.spec_from_file_location(
        "legacy_data_import_test_module", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(
    sys.platform == "win32", "atomic importer publication is Windows-only"
)
class ExplicitImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "legacy-fixture"
        self.source.mkdir()
        (self.source / "master.key").write_bytes(b"opaque-fixture-not-a-real-secret")
        (self.source / "ai").mkdir()
        (self.source / "ai" / "prompt.md").write_text(
            "synthetic prompt", encoding="utf-8"
        )
        self.destination = self.base / "DebateAI"
        self.backup = self.base / "backup"
        self.module = importer()

    def run_import(self, **extra):
        options = {
            "source": self.source,
            "destination": self.destination,
            "backup": self.backup,
            "confirmed_offline": True,
        }
        options.update(extra)
        return self.module.import_file_data(**options)

    def test_requires_explicit_confirmation_before_creating_anything(self):
        with self.assertRaisesRegex(self.module.ImportSafetyError, "confirm"):
            self.run_import(confirmed_offline=False)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.destination.exists())

    def test_source_backup_and_destination_bytes_match(self):
        result = self.run_import()
        self.assertEqual("copied", result["status"])
        for relative in ("master.key", "ai/prompt.md"):
            original = (self.source / relative).read_bytes()
            self.assertEqual(original, (self.backup / "data" / relative).read_bytes())
            self.assertEqual(original, (self.destination / relative).read_bytes())
        self.assertTrue((self.destination / self.module.RECEIPT).is_file())
        self.assertTrue((self.backup / "manifest.json").is_file())

    def test_exact_repeat_is_idempotent(self):
        self.run_import()
        before = (self.destination / self.module.RECEIPT).read_bytes()
        self.assertEqual("already-imported", self.run_import()["status"])
        self.assertEqual(before, (self.destination / self.module.RECEIPT).read_bytes())

    def test_modified_destination_never_gets_overwritten(self):
        self.run_import()
        path = self.destination / "master.key"
        path.write_bytes(b"newer-user-owned-data")
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import()
        self.assertEqual(b"newer-user-owned-data", path.read_bytes())

    def test_unrelated_or_empty_existing_destination_is_not_replaced(self):
        self.destination.mkdir()
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import()
        self.assertTrue(self.destination.is_dir())
        self.assertFalse(self.backup.exists())

    def test_existing_backup_is_never_replaced(self):
        self.backup.mkdir()
        (self.backup / "keep").write_text("kept")
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import()
        self.assertEqual("kept", (self.backup / "keep").read_text())
        self.assertFalse(self.destination.exists())

    def test_active_or_database_roots_are_refused_not_partially_imported(self):
        for name in (
            "postmaster.pid",
            "launcher.json",
            "PG_VERSION",
            "accounts.sqlite",
            "LOCK",
        ):
            with self.subTest(marker=name):
                marker = self.source / name
                marker.write_text("synthetic")
                try:
                    with self.assertRaises(self.module.ImportSafetyError):
                        self.run_import()
                    self.assertFalse(self.backup.exists())
                    self.assertFalse(self.destination.exists())
                finally:
                    marker.unlink()

    def test_renamed_sqlite_database_is_refused(self):
        (self.source / "Login Data").write_bytes(b"SQLite format 3\x00" + b"synthetic")
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import()
        self.assertFalse(self.backup.exists())

    def test_source_and_destination_overlap_is_refused(self):
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import(destination=self.source / "nested")
        self.assertFalse((self.source / "nested").exists())

    def test_hardlinked_file_is_refused(self):
        os.link(self.source / "master.key", self.source / "alias")
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import()
        self.assertFalse(self.backup.exists())

    def test_wrong_owner_is_refused(self):
        with (
            patch.object(
                self.module,
                "_require_current_owner",
                side_effect=self.module.ImportSafetyError("owner"),
            ),
            self.assertRaisesRegex(self.module.ImportSafetyError, "owner"),
        ):
            self.run_import()
        self.assertFalse(self.backup.exists())

    def test_failed_copy_preserves_source_and_never_publishes_partial_destination(self):
        with (
            patch.object(
                self.module,
                "_copy_inventory",
                side_effect=OSError("synthetic disk full"),
            ),
            self.assertRaises(OSError),
        ):
            self.run_import()
        self.assertEqual(
            b"opaque-fixture-not-a-real-secret",
            (self.source / "master.key").read_bytes(),
        )
        self.assertFalse(self.destination.exists())

    def test_source_change_during_backup_is_detected(self):
        original = self.module._copy_inventory

        def changed(source, destination, inventory):
            original(source, destination, inventory)
            if source == self.source:
                (self.source / "ai" / "prompt.md").write_text(
                    "changed during copy", encoding="utf-8"
                )

        with (
            patch.object(self.module, "_copy_inventory", side_effect=changed),
            self.assertRaises(self.module.ImportSafetyError),
        ):
            self.run_import()
        self.assertFalse(self.destination.exists())
        self.assertEqual(
            "changed during copy", (self.source / "ai" / "prompt.md").read_text()
        )

    def test_tampered_backup_blocks_repeat(self):
        self.run_import()
        (self.backup / "data" / "master.key").write_bytes(b"changed-backup")
        with self.assertRaises(self.module.ImportSafetyError):
            self.run_import()
        self.assertTrue(self.source.is_dir())


class CanonicalResolverBoundaryTests(unittest.TestCase):
    def test_existing_legacy_data_is_never_read_copied_or_selected_implicitly(self):
        import debateai_identity

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            legacy = base / "Backchannel"
            legacy.mkdir()
            (legacy / "master.key").write_bytes(b"synthetic")
            selected = debateai_identity.resolve_data_root(base=base, environment={})
            self.assertEqual(base / "DebateAI", selected)
            self.assertFalse(selected.exists(), "ordinary startup must not migrate")
            self.assertEqual(b"synthetic", (legacy / "master.key").read_bytes())

    def test_runtime_module_does_not_bundle_importer_or_legacy_names(self):
        source = (ROOT / "desktop" / "debateai_identity.py").read_text(encoding="utf-8")
        self.assertNotIn("backchannel", source.casefold())
        self.assertNotIn("copytree", source)
        self.assertNotIn("legacy_data_import", source)


if __name__ == "__main__":
    unittest.main()
