import hashlib
import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from scripts import download_pg
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

    def test_tampered_jar_is_rejected_before_opening_or_extracting(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "pgsql"
            with (
                mock.patch.object(download_pg, "DEST", destination),
                mock.patch.object(download_pg.urllib.request, "urlopen", return_value=io.BytesIO(b"untrusted")),
                mock.patch.object(download_pg.zipfile, "ZipFile") as open_jar,
            ):
                with self.assertRaisesRegex(RuntimeError, "PostgreSQL checksum mismatch"):
                    download_pg.main()
                open_jar.assert_not_called()
                self.assertFalse(destination.exists())

    def test_pinned_jar_is_extracted(self):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:xz") as postgres:
            member = tarfile.TarInfo("bin/postgres")
            binary = b"postgres test fixture"
            member.size = len(binary)
            postgres.addfile(member, io.BytesIO(binary))
        jar = io.BytesIO()
        with zipfile.ZipFile(jar, "w") as outer:
            outer.writestr("postgres-linux-x86_64.txz", archive.getvalue())
        data = jar.getvalue()
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "pgsql"
            with (
                mock.patch.object(download_pg, "DEST", destination),
                mock.patch.object(download_pg, "artifact_platform", return_value="linux-amd64"),
                mock.patch.object(download_pg, "PG_JAR_SHA256", {"linux-amd64": hashlib.sha256(data).hexdigest()}),
                mock.patch.object(download_pg.urllib.request, "urlopen", return_value=io.BytesIO(data)),
            ):
                download_pg.main()
            self.assertEqual((destination / "bin" / "postgres").read_bytes(), binary)

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
