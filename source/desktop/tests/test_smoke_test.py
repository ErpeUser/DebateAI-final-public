import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

try:
    from desktop.scripts import smoke_test, smoke_update_archive
except ModuleNotFoundError:
    from scripts import smoke_test, smoke_update_archive


class _Response:
    status = 200
    headers = {"X-DebateAI-Instance": "ours"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return b'{"status":"ok"}'


class SmokeTestTests(unittest.TestCase):
    def test_isolated_environment_removes_provider_credentials(self):
        with patch.dict(
            smoke_test.os.environ,
            {"GEMINI_API_KEY": "secret", "OPENAI_API_KEY": "secret", "SAFE": "kept"},
            clear=True,
        ):
            environment = smoke_test.isolated_environment("isolated-data")

        self.assertNotIn("GEMINI_API_KEY", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertEqual(environment["SAFE"], "kept")
        self.assertEqual(environment["DEBATEAI_DATA_DIR"], "isolated-data")
        self.assertEqual(environment["DEBATEAI_HEADLESS"], "1")

    def test_archive_smoke_uses_a_space_and_non_ascii_path(self):
        with smoke_update_archive.temporary_directory() as root:
            self.assertIn(" ", str(root))
            self.assertTrue(any(ord(character) > 127 for character in str(root)))

    def test_bundle_exe_accepts_an_explicit_staged_bundle(self):
        bundle = Path("release stage") / "DebateAI"
        expected = (bundle / "DebateAI.exe").resolve()
        with patch.object(Path, "exists", return_value=True):
            self.assertEqual(smoke_test.bundle_exe(bundle), expected)

    def test_bundle_exe_resolves_before_launcher_changes_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / "dist" / "DebateAI" / "DebateAI"
            executable.parent.mkdir(parents=True)
            executable.write_text("fixture")
            previous = Path.cwd()
            os.chdir(root)
            try:
                resolved = smoke_test.bundle_exe(Path("dist") / "DebateAI")
            finally:
                os.chdir(previous)
        self.assertTrue(resolved.is_absolute())
        self.assertTrue(resolved.exists())

    def test_wait_for_health_retries_and_checks_instance_token(self):
        proc = Mock()
        proc.poll.return_value = None
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "launcher.json"
            lock.write_text(json.dumps({"port": 8474, "token": "ours"}))
            with (
                patch.object(
                    smoke_test.urllib.request,
                    "urlopen",
                    side_effect=[URLError("starting"), _Response()],
                ) as urlopen,
                patch.object(smoke_test.time, "sleep"),
            ):
                self.assertEqual(
                    smoke_test.wait_for_health(proc, lock, deadline=float("inf")),
                    8474,
                )

        self.assertEqual(urlopen.call_count, 2)

    def test_stop_process_repeats_signal_until_launcher_observes_it(self):
        proc = Mock()
        proc.poll.side_effect = [None, None, 0]
        proc.wait.side_effect = [subprocess.TimeoutExpired("DebateAI", 1), 0]
        with tempfile.TemporaryDirectory() as tmp:
            stop = Path(tmp) / "stop"
            with patch.object(smoke_test.time, "monotonic", side_effect=[0, 0, 1]):
                self.assertTrue(smoke_test.stop_process(proc, stop, timeout=5))

        self.assertEqual(proc.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
