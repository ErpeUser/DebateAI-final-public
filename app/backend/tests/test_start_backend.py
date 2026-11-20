import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


_fake_installer = types.ModuleType("install_sortformer")
_fake_installer.ensure_sortformer_installed = mock.Mock()
_spec = importlib.util.spec_from_file_location(
    "start_backend_under_test",
    Path(__file__).resolve().parents[1] / "scripts" / "start_backend.py",
)
_start_backend = importlib.util.module_from_spec(_spec)
with mock.patch.dict(sys.modules, {"install_sortformer": _fake_installer}):
    _spec.loader.exec_module(_start_backend)


EXPECTED_COMMAND = [
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--workers",
    "1",
    "--ws-ping-timeout",
    "90",
    "--ws-max-queue",
    "2048",
    "--ws-max-size",
    "65536",
]


class BackendStartupTests(unittest.TestCase):
    def test_native_start_defaults_to_loopback_without_reload(self):
        with (
            mock.patch.object(_start_backend, "ensure_sortformer_installed"),
            mock.patch.object(_start_backend.os, "execvp") as execvp,
            mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0)),
            mock.patch.dict(_start_backend.os.environ, {}, clear=True),
        ):
            _start_backend.main()

        execvp.assert_called_once_with("uvicorn", EXPECTED_COMMAND)

    def test_multiworker_start_is_rejected_until_shared_state_exists(self):
        with (
            mock.patch.object(_start_backend, "ensure_sortformer_installed"),
            mock.patch.dict(_start_backend.os.environ, {"BACKEND_WORKERS": "2"}, clear=True),
        ):
            with self.assertRaisesRegex(RuntimeError, "BACKEND_WORKERS"):
                _start_backend.main()

    def test_non_loopback_start_requires_instance_token(self):
        with (
            mock.patch.object(_start_backend, "ensure_sortformer_installed"),
            mock.patch.dict(
                _start_backend.os.environ,
                {"BACKEND_HOST": "0.0.0.0"},
                clear=True,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "DEBATEAI_INSTANCE_TOKEN"):
                _start_backend.main()

    def test_execs_uvicorn_without_reload(self):
        with (
            mock.patch.object(_start_backend, "ensure_sortformer_installed"),
            mock.patch.object(_start_backend.os, "execvp") as execvp,
            mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0)),
            mock.patch.dict(_start_backend.os.environ, {"BACKEND_RELOAD": "false"}),
        ):
            _start_backend.main()

        execvp.assert_called_once_with(
            "uvicorn",
            EXPECTED_COMMAND,
        )

    def test_execs_uvicorn_with_reload_last(self):
        with (
            mock.patch.object(_start_backend, "ensure_sortformer_installed"),
            mock.patch.object(_start_backend.os, "execvp") as execvp,
            mock.patch.object(subprocess, "run", return_value=mock.Mock(returncode=0)),
            mock.patch.dict(_start_backend.os.environ, {"BACKEND_RELOAD": "true"}),
        ):
            _start_backend.main()

        execvp.assert_called_once_with(
            "uvicorn",
            EXPECTED_COMMAND + ["--reload"],
        )

    def test_native_gpu_start_uses_same_websocket_limits(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "setup_windows_gpu.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("--ws-ping-timeout 90", script)
        self.assertIn("--ws-max-queue 2048", script)
        self.assertIn("--ws-max-size 65536", script)

    def test_compose_sets_non_loopback_listener_only_with_instance_token(self):
        compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("BACKEND_HOST: ${BACKEND_HOST:-0.0.0.0}", compose)
        self.assertIn("DEBATEAI_INSTANCE_TOKEN: ${DEBATEAI_INSTANCE_TOKEN:?", compose)


if __name__ == "__main__":
    unittest.main()
