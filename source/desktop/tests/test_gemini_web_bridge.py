import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from bcdesktop.gemini_web_bridge import GeminiWebBridge


class GeminiWebBridgeTests(unittest.TestCase):
    def _bridge(self, tmp: str) -> GeminiWebBridge:
        bundled = Path(tmp) / "bundle"
        bundled.mkdir()
        (bundled / "gemini-web-to-api.exe").write_bytes(b"binary")
        resource_patch = patch(
            "bcdesktop.gemini_web_bridge.resource", return_value=bundled
        )
        port_patch = patch("bcdesktop.gemini_web_bridge.free_port", return_value=49819)
        self.addCleanup(resource_patch.stop)
        self.addCleanup(port_patch.stop)
        resource_patch.start()
        port_patch.start()
        return GeminiWebBridge(Path(tmp) / "data", logging.getLogger("test"))

    def test_runtime_is_loopback_only_and_receives_cookie_only_in_child_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge._ensure_key()
            environment = bridge._runtime_environment("private-cookie")
            client_key = bridge.client_key

        self.assertEqual(environment["HOST"], "127.0.0.1")
        self.assertEqual(environment["PORT"], "49819")
        self.assertEqual(environment["GEMINI_COOKIES"], "private-cookie")
        self.assertEqual(environment["BACKCHANNEL_API_KEY"], client_key)

    def test_provider_reports_live_models_after_start(self):
        process = Mock()
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge._ensure_key()
            with (
                patch("bcdesktop.gemini_web_bridge.subprocess.Popen", return_value=process) as popen,
                patch.object(bridge, "_request_json", return_value={"status": "ok"}),
                patch.object(
                    bridge,
                    "_probe_models",
                    return_value=["gemini-auto", "gemini-3.1-pro"],
                ),
            ):
                self.assertTrue(bridge._start_process("private-cookie"))

        child_environment = popen.call_args.kwargs["env"]
        self.assertEqual(child_environment["GEMINI_COOKIES"], "private-cookie")
        self.assertEqual(
            os.environ["BACKCHANNEL_GEMINI_WEB_MODELS"],
            '["gemini-auto","gemini-3.1-pro"]',
        )

    def test_provider_waits_for_nonempty_live_model_catalog(self):
        process = Mock()
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge._ensure_key()
            with (
                patch("bcdesktop.gemini_web_bridge.subprocess.Popen", return_value=process),
                patch.object(bridge, "_request_json", return_value={"status": "ok"}),
                patch.object(
                    bridge,
                    "_probe_models",
                    side_effect=[[], [], ["gemini-3.1-pro"]],
                ) as probe,
                patch("bcdesktop.gemini_web_bridge.time.sleep"),
            ):
                self.assertTrue(bridge._start_process("private-cookie"))

        self.assertEqual(probe.call_count, 3)
        self.assertEqual(
            os.environ["BACKCHANNEL_GEMINI_WEB_MODELS"],
            '["gemini-3.1-pro"]',
        )

    def test_cookie_watcher_does_not_loop_on_unchanged_invalid_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge.cookie_file.parent.mkdir(parents=True)
            bridge.cookie_file.write_text("private-cookie", encoding="utf-8")
            bridge.stop_event = Mock()
            bridge.stop_event.wait.side_effect = [False, False, True]
            with patch.object(bridge, "_start_process", return_value=False) as start:
                bridge._watch_cookie()

        self.assertEqual(start.call_count, 1)

    def test_cookie_watcher_consumes_runtime_cookie_after_provider_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge.cookie_file.parent.mkdir(parents=True)
            bridge.cookie_file.write_text("private-cookie", encoding="utf-8")
            bridge.stop_event = Mock()
            bridge.stop_event.wait.side_effect = [False, True]
            with patch.object(bridge, "_start_process", return_value=True):
                bridge._watch_cookie()

            self.assertFalse(bridge.cookie_file.exists())

    def test_cookie_watcher_restarts_crashed_provider_from_consumed_cookie(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge.cookie_file.parent.mkdir(parents=True)
            bridge.cookie_file.write_text("private-cookie", encoding="utf-8")
            bridge.stop_event = Mock()
            bridge.stop_event.wait.side_effect = [False, False, True]
            with patch.object(
                bridge, "_start_process", side_effect=[True, True]
            ) as start:
                bridge._watch_cookie()

        self.assertEqual(
            ["private-cookie", "private-cookie"],
            [call.args[0] for call in start.call_args_list],
        )

    def test_empty_cookie_signal_disconnects_and_clears_rotation_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge.cookie_file.parent.mkdir(parents=True)
            bridge.cookie_file.write_text("", encoding="utf-8")
            bridge.cookie_cache.mkdir()
            (bridge.cookie_cache / "rotated.txt").write_text(
                "private-rotation", encoding="utf-8"
            )
            bridge.stop_event = Mock()
            bridge.stop_event.wait.side_effect = [False, True]
            with patch.object(bridge, "_stop_process") as stop_process:
                bridge._watch_cookie()

            stop_process.assert_called_once_with()
            self.assertFalse(bridge.cookie_cache.exists())
            self.assertFalse(bridge.cookie_file.exists())

    def test_stop_removes_runtime_cookie_but_preserves_rotation_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = self._bridge(tmp)
            bridge.cookie_file.parent.mkdir(parents=True)
            bridge.cookie_file.write_text("private-cookie", encoding="utf-8")
            bridge.cookie_cache.mkdir()
            (bridge.cookie_cache / "rotated.txt").write_text(
                "private-rotation", encoding="utf-8"
            )

            bridge.stop()

            self.assertFalse(bridge.cookie_file.exists())
            self.assertTrue(bridge.cookie_cache.exists())


if __name__ == "__main__":
    unittest.main()
