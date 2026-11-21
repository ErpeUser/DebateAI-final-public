import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from debateai_desktop.subscription_bridge import SubscriptionBridge


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class SubscriptionBridgeTests(unittest.TestCase):
    def test_probe_uses_configured_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = SubscriptionBridge(Path(tmp), Mock())
            bridge.port = 9234
            response = _Response()
            with (
                patch(
                    "debateai_desktop.subscription_bridge.urllib.request.urlopen",
                    return_value=response,
                ) as urlopen,
                patch(
                    "debateai_desktop.subscription_bridge.json.load",
                    return_value={"data": [{"id": "gpt-test"}]},
                ),
            ):
                self.assertEqual(bridge._probe(), ["gpt-test"])
            request = urlopen.call_args.args[0]
            self.assertEqual(
                request.full_url,
                "http://127.0.0.1:9234/v1/models",
            )

    def test_prepare_exports_connection_without_starting_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            (root / "cli-proxy-api.exe").write_bytes(b"test executable")
            with (
                patch("debateai_desktop.subscription_bridge.subprocess.Popen") as popen,
                patch.dict(
                    "debateai_desktop.subscription_bridge.os.environ", {}, clear=True
                ) as environment,
            ):
                bridge = SubscriptionBridge(Path(tmp), Mock())
                self.assertTrue(bridge.prepare())
                popen.assert_not_called()
                self.assertEqual(
                    environment["DEBATEAI_SUBSCRIPTION_BRIDGE_URL"],
                    "http://127.0.0.1:8317/v1",
                )
                self.assertEqual(
                    environment["SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK"], "true"
                )
                self.assertEqual(environment["DEBATEAI_SUBSCRIPTION_MODELS"], "[]")

    def test_missing_bridge_is_a_quiet_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = SubscriptionBridge(Path(tmp), Mock())
            bridge.bundled_root = Path(tmp) / "missing-bundle"
            bridge.bundled_executable = bridge.bundled_root / "cli-proxy-api.exe"
            with (
                patch("debateai_desktop.subscription_bridge.subprocess.Popen") as popen,
                patch.object(bridge, "_probe", return_value=None),
            ):
                self.assertFalse(bridge.start())
            popen.assert_not_called()

    def test_start_creates_loopback_config_and_hidden_child_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            executable = root / "cli-proxy-api.exe"
            executable.write_bytes(b"test executable")
            process = Mock()
            process.poll.return_value = None

            with (
                patch(
                    "debateai_desktop.subscription_bridge.subprocess.Popen",
                    return_value=process,
                ) as popen,
                patch.object(
                    SubscriptionBridge, "_probe", side_effect=[None, ["gpt-test"]]
                ),
            ):
                bridge = SubscriptionBridge(Path(tmp), Mock())
                self.assertTrue(bridge.start())

            config = (root / "config.yaml").read_text(encoding="utf-8")
            self.assertIn('host: "127.0.0.1"', config)
            self.assertIn("port: 8317", config)
            self.assertIn(str(root / "auth").replace("\\", "\\\\"), config)
            self.assertNotIn("allow-remote: true", config)
            self.assertIn("max-retry-credentials: 0", config)
            self.assertNotIn('name: "gemini-pro-agent"', config)
            self.assertNotIn('alias: "gemini-3.1-pro-preview"', config)
            self.assertIn("gemini-cli:", config)
            args = popen.call_args.args[0]
            self.assertEqual(
                args,
                [
                    str(executable),
                    "-config",
                    str(root / "config.yaml"),
                    "-local-model",
                ],
            )
            self.assertEqual(
                popen.call_args.kwargs.get("creationflags", 0),
                subprocess.CREATE_NO_WINDOW,
            )
            self.assertEqual(0, popen.call_args.kwargs["startupinfo"].wShowWindow)

    def test_start_waits_past_the_initial_empty_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            (root / "cli-proxy-api.exe").write_bytes(b"test executable")
            process = Mock()
            process.poll.return_value = None
            with (
                patch(
                    "debateai_desktop.subscription_bridge.subprocess.Popen",
                    return_value=process,
                ),
                patch.object(
                    SubscriptionBridge,
                    "_probe",
                    side_effect=[None, [], [], ["gemini-3.8-flash-high", "gpt-6-sol"]],
                ),
                patch("debateai_desktop.subscription_bridge.time.sleep"),
            ):
                bridge = SubscriptionBridge(Path(tmp), Mock())
                self.assertTrue(bridge.start())

            self.assertEqual(
                ["gemini-3.8-flash-high", "gpt-6-sol"], bridge.served_models
            )

    def test_stop_terminates_and_waits_for_the_exact_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            (root / "cli-proxy-api.exe").write_bytes(b"test executable")
            process = Mock()
            process.poll.return_value = None
            with (
                patch(
                    "debateai_desktop.subscription_bridge.subprocess.Popen",
                    return_value=process,
                ),
                patch.object(
                    SubscriptionBridge,
                    "_probe",
                    side_effect=[None] + ([[]] * 15),
                ),
                patch("debateai_desktop.subscription_bridge.time.sleep"),
            ):
                bridge = SubscriptionBridge(Path(tmp), Mock())
                bridge.start()
                bridge.stop()

            process.terminate.assert_called_once_with()
            process.wait.assert_called_once_with(timeout=5)

    def test_start_exports_only_local_connection_details_not_oauth_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            (root / "cli-proxy-api.exe").write_bytes(b"test executable")
            with (
                patch(
                    "debateai_desktop.subscription_bridge.subprocess.Popen",
                    return_value=Mock(),
                ),
                patch.object(
                    SubscriptionBridge, "_probe", side_effect=[None, ["gpt-6-sol"]]
                ),
                patch.dict(
                    "debateai_desktop.subscription_bridge.os.environ", {}, clear=True
                ) as environment,
            ):
                bridge = SubscriptionBridge(Path(tmp), Mock())
                bridge.start()
                self.assertEqual(
                    environment["DEBATEAI_SUBSCRIPTION_BRIDGE_URL"],
                    "http://127.0.0.1:8317/v1",
                )
                self.assertEqual(
                    environment["DEBATEAI_SUBSCRIPTION_BRIDGE_KEY"], bridge.client_key
                )
                self.assertEqual(
                    environment.get("SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK"), "true"
                )
                self.assertEqual(
                    environment["DEBATEAI_SUBSCRIPTION_MODELS"], '["gpt-6-sol"]'
                )
                self.assertNotIn("DEBATEAI_SUBSCRIPTION_BRIDGE_OAUTH", environment)

    def test_start_adopts_an_existing_healthy_bridge_without_spawning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            (root / "client-key").write_text("local-key", encoding="utf-8")
            bridge = SubscriptionBridge(Path(tmp), Mock())
            with (
                patch.object(bridge, "_probe", return_value=["gpt-6-sol"]),
                patch("debateai_desktop.subscription_bridge.subprocess.Popen") as popen,
            ):
                self.assertTrue(bridge.start())
            popen.assert_not_called()
            self.assertTrue(bridge.adopted)

    def test_stop_event_cancels_start_before_spawning_a_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "subscription-bridge"
            root.mkdir()
            (root / "cli-proxy-api.exe").write_bytes(b"test executable")
            bridge = SubscriptionBridge(Path(tmp), Mock())

            def cancel_probe():
                bridge.stop_event.set()

            with (
                patch.object(bridge, "_probe", side_effect=cancel_probe),
                patch("debateai_desktop.subscription_bridge.subprocess.Popen") as popen,
            ):
                self.assertFalse(bridge.start())
            popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
