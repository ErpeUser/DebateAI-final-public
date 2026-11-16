import unittest
from unittest import mock

from scripts.download_ffmpeg import (
    LINUX_URL,
    SHA256_BY_URL,
    WINDOWS_URL,
    binary_name,
    build_url,
    download_payload,
)


class DownloadFfmpegTests(unittest.TestCase):
    def test_platform_urls_are_lgpl_static_builds(self):
        with mock.patch("scripts.download_ffmpeg.sys.platform", "win32"):
            url = build_url()
            self.assertIn("win64-lgpl", url)
            self.assertTrue(url.endswith(".zip"))
        with mock.patch("scripts.download_ffmpeg.sys.platform", "linux"):
            url = build_url()
            self.assertIn("linux64-lgpl", url)
            self.assertTrue(url.endswith(".tar.xz"))

    def test_assets_are_versioned_and_hashed(self):
        self.assertIn("autobuild-2026-11-15-12-40", WINDOWS_URL)
        self.assertIn("autobuild-2026-11-15-12-40", LINUX_URL)
        self.assertNotIn("/latest/", WINDOWS_URL)
        self.assertEqual(64, len(SHA256_BY_URL[WINDOWS_URL]))
        self.assertEqual(64, len(SHA256_BY_URL[LINUX_URL]))

    def test_checksum_verification_rejects_modified_payload(self):
        with mock.patch("scripts.download_ffmpeg.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b"tampered"
            with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                download_payload(WINDOWS_URL)

    def test_macos_bundles_no_ffmpeg(self):
        with mock.patch("scripts.download_ffmpeg.sys.platform", "darwin"):
            self.assertIsNone(build_url())

    def test_binary_name_matches_platform(self):
        with mock.patch("scripts.download_ffmpeg.sys.platform", "win32"):
            self.assertEqual(binary_name(), "ffmpeg.exe")
        with mock.patch("scripts.download_ffmpeg.sys.platform", "linux"):
            self.assertEqual(binary_name(), "ffmpeg")


if __name__ == "__main__":
    unittest.main()
