"""Synthetic files only; never starts PostgreSQL or touches a real profile."""

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from debateai_desktop.pg import EmbeddedPostgres


class PGDataPreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pg = EmbeddedPostgres(self.root / "runtime", self.root / "data")

    def test_nonempty_unversioned_directory_is_preserved_without_side_effects(self):
        sentinel = self.pg.pgdata / "base" / "synthetic-table"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_bytes(b"previously retained synthetic database bytes")
        before = sentinel.read_bytes()
        with (
            patch.object(self.pg, "_run") as launch,
            patch.object(self.pg, "password") as password,
            patch.object(self.pg, "_grant_windows_acl") as acl,
        ):
            error = None
            try:
                self.pg.ensure_initdb()
            except RuntimeError as exc:
                error = exc
            self.assertTrue(
                sentinel.exists(), "Existing unversioned database was deleted"
            )
            self.assertEqual(before, sentinel.read_bytes())
            self.assertIsNotNone(error)
            self.assertRegex(str(error).lower(), "refus|recover")
            launch.assert_not_called()
            password.assert_not_called()
            acl.assert_not_called()
        self.assertFalse(self.pg.pwfile.exists())

    def test_empty_directory_is_initialized_without_deleting_the_directory(self):
        self.pg.pgdata.mkdir(parents=True)
        identity = self.pg.pgdata.stat().st_ino
        with (
            patch.object(self.pg, "_run") as launch,
            patch.object(self.pg, "password"),
            patch.object(self.pg, "_grant_windows_acl"),
        ):
            self.pg.ensure_initdb()
        self.assertTrue(
            self.pg.pgdata.is_dir(), "An empty owned directory need not be deleted"
        )
        self.assertEqual(identity, self.pg.pgdata.stat().st_ino)
        launch.assert_called_once()
        self.assertIn("initdb", str(launch.call_args.args[0][0]))

    def test_failed_initialization_partial_data_survives_a_retry(self):
        sentinel = self.pg.pgdata / "partial-cluster"

        def fail(command):
            self.pg.pgdata.mkdir(parents=True, exist_ok=True)
            sentinel.write_bytes(b"partial first attempt")
            raise RuntimeError("Synthetic initdb failure")

        with (
            patch.object(self.pg, "_run", side_effect=fail),
            patch.object(self.pg, "password"),
            patch.object(self.pg, "_grant_windows_acl"),
            self.assertRaisesRegex(RuntimeError, "Synthetic"),
        ):
            self.pg.ensure_initdb()
        self.assertEqual(b"partial first attempt", sentinel.read_bytes())
        with (
            patch.object(self.pg, "_run") as retry,
            patch.object(self.pg, "password") as password,
            patch.object(self.pg, "_grant_windows_acl") as acl,
        ):
            error = None
            try:
                self.pg.ensure_initdb()
            except RuntimeError as exc:
                error = exc
            self.assertTrue(
                sentinel.exists(), "Retry deleted the failed initialization evidence"
            )
            self.assertEqual(b"partial first attempt", sentinel.read_bytes())
            self.assertIsNotNone(error)
            retry.assert_not_called()
            password.assert_not_called()
            acl.assert_not_called()

    def test_existing_versioned_cluster_is_not_mutated(self):
        self.pg.pgdata.mkdir(parents=True)
        version = self.pg.pgdata / "PG_VERSION"
        version.write_text("16")
        with (
            patch.object(self.pg, "_run") as launch,
            patch.object(self.pg, "password") as password,
            patch.object(self.pg, "_grant_windows_acl") as acl,
        ):
            self.pg.ensure_initdb()
        self.assertEqual("16", version.read_text())
        launch.assert_not_called()
        password.assert_not_called()
        acl.assert_not_called()

    def test_absent_directory_allows_initialization(self):

        def initialize(command):
            self.pg.pgdata.mkdir(parents=True)
            (self.pg.pgdata / "PG_VERSION").write_text("16")

        with (
            patch.object(self.pg, "_run", side_effect=initialize) as launch,
            patch.object(self.pg, "password"),
            patch.object(self.pg, "_grant_windows_acl"),
        ):
            self.pg.ensure_initdb()
        launch.assert_called_once()
        self.assertTrue(self.pg.initialized_here)
        self.assertTrue(self.pg.role_marker.is_file())

    def test_unversioned_link_or_junction_is_not_initialized(self):
        self.pg.pgdata.mkdir(parents=True)
        for flag in ("is_symlink", "is_junction"):
            with self.subTest(flag=flag):
                with patch.object(Path, flag, return_value=True, create=True):
                    with (
                        patch.object(self.pg, "_run") as launch,
                        patch.object(self.pg, "password") as password,
                        patch.object(self.pg, "_grant_windows_acl") as acl,
                    ):
                        with self.assertRaisesRegex(RuntimeError, "explicit recovery"):
                            self.pg.ensure_initdb()
                        launch.assert_not_called()
                        password.assert_not_called()
                        acl.assert_not_called()
        self.assertTrue(self.pg.pgdata.is_dir())

    def test_unreadable_directory_refuses_before_any_mutating_action(self):
        self.pg.pgdata.mkdir(parents=True)
        with (
            patch.object(
                Path,
                "iterdir",
                side_effect=PermissionError("Synthetic unreadable directory"),
            ),
            patch.object(self.pg, "_run") as launch,
            patch.object(self.pg, "password") as password,
            patch.object(self.pg, "_grant_windows_acl") as acl,
        ):
            with self.assertRaises(PermissionError):
                self.pg.ensure_initdb()
            launch.assert_not_called()
            password.assert_not_called()
            acl.assert_not_called()

    def test_regular_file_at_pgdata_is_preserved(self):
        self.pg.pgdata.parent.mkdir(parents=True)
        self.pg.pgdata.write_bytes(b"Synthetic retained file")
        with (
            patch.object(self.pg, "_run") as launch,
            patch.object(self.pg, "password") as password,
            patch.object(self.pg, "_grant_windows_acl") as acl,
        ):
            with self.assertRaises((RuntimeError, OSError)):
                self.pg.ensure_initdb()
            launch.assert_not_called()
            password.assert_not_called()
            acl.assert_not_called()
        self.assertEqual(b"Synthetic retained file", self.pg.pgdata.read_bytes())

    def _check_real_junction(self, *, dangling=False, hide_junction_api=False):
        if os.name != "nt":
            self.skipTest("Native Windows junction contract")
        target = self.root / "synthetic-junction-target"
        target.mkdir()
        link = self.pg.pgdata
        link.parent.mkdir(parents=True)
        command = str(Path(os.environ["SystemRoot"]) / "System32" / "cmd.exe")
        made = subprocess.run(
            [command, "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(
            0, made.returncode, "Synthetic junction fixture could not be created"
        )
        self.addCleanup(lambda: os.rmdir(link))
        self.assertTrue(
            link.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        if dangling:
            target.rmdir()  # Only the empty synthetic directory created above.
        if hide_junction_api:

            class WithoutJunctionAPI:
                def __truediv__(self, part):
                    return link / part

                def __getattr__(self, name):
                    if name == "is_junction":
                        raise AttributeError(name)
                    return getattr(link, name)

            self.pg.pgdata = WithoutJunctionAPI()
        with (
            patch.object(self.pg, "_run") as launch,
            patch.object(self.pg, "password") as password,
            patch.object(self.pg, "_grant_windows_acl") as acl,
        ):
            with self.assertRaisesRegex(RuntimeError, "explicit recovery"):
                self.pg.ensure_initdb()
            launch.assert_not_called()
            password.assert_not_called()
            acl.assert_not_called()
        self.assertTrue(
            link.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        if dangling:
            self.assertFalse(target.exists())
        else:
            self.assertEqual([], list(target.iterdir()))

    def test_real_windows_empty_junction_is_rejected(self):
        self._check_real_junction()

    def test_real_windows_dangling_junction_is_rejected(self):
        self._check_real_junction(dangling=True)

    def test_real_junction_without_pathlib_helper_is_rejected(self):
        self._check_real_junction(hide_junction_api=True)

    def test_real_dangling_junction_without_pathlib_helper_is_rejected(self):
        self._check_real_junction(dangling=True, hide_junction_api=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
