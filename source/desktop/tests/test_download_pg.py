import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.download_pg import artifact_platform, has_complete_install, jar_url


class DownloadPgTests(unittest.TestCase):
    def test_platform_names_match_zonky_artifacts(self):
        with mock.patch("scripts.download_pg.sys.platform", "win32"):
            self.assertEqual(artifact_platform(), "windows-amd64")
        with mock.patch("scripts.download_pg.sys.platform", "darwin"):
            with mock.patch("scripts.download_pg.platform.machine", return_value="arm64"):
                self.assertEqual(artifact_platform(), "darwin-arm64v8")
            with mock.patch("scripts.download_pg.platform.machine", return_value="x86_64"):
                self.assertEqual(artifact_platform(), "darwin-amd64")

    def test_jar_url_points_at_maven_central(self):
        url = jar_url("windows-amd64")
        self.assertTrue(url.startswith("https://repo1.maven.org/maven2/io/zonky/test/postgres/"))
        self.assertTrue(url.endswith(".jar"))
        self.assertIn("embedded-postgres-binaries-windows-amd64", url)

    def test_incomplete_bin_directory_is_not_considered_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)
            with mock.patch("scripts.download_pg.DEST", new=destination):
                (destination / "bin").mkdir()
                self.assertFalse(has_complete_install())

    def test_zero_length_binary_is_not_considered_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)
            binary_dir = destination / "bin"
            binary_dir.mkdir()
            for name in ("postgres", "initdb", "pg_ctl"):
                (binary_dir / name).touch()
            with mock.patch("scripts.download_pg.DEST", new=destination):
                self.assertFalse(has_complete_install())


if __name__ == "__main__":
    unittest.main()
