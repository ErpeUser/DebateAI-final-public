import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "app/services/debateai_update_channel.py"


class UpdateChannelTests(unittest.TestCase):
    def load(self):
        self.assertTrue(MODULE.exists(), "independent update policy is required")
        spec = importlib.util.spec_from_file_location("debateai_update_channel", MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_unreadable_trust_file_disables_updates_not_application(self):
        m = self.load()
        calls = []
        fake = types.ModuleType("app.services.update_service")

        class Service:
            def __init__(self, *, enabled, **kwargs):
                calls.append(enabled)
                if enabled:
                    raise OSError("unreadable fixture")
                self.enabled = enabled

        fake.UpdateService = Service
        env = {**self.config(), "DEBATEAI_DESKTOP": "1"}
        with (
            patch.dict(sys.modules, {"app.services.update_service": fake}),
            patch.dict(os.environ, env, clear=True),
        ):
            self.assertFalse(m.get_update_service().enabled)
            self.assertIs(m.get_update_service(), m.get_update_service())
        self.assertEqual(calls, [True, False])

    def test_default_has_no_channel(self):
        self.assertIsNone(self.load().channel_configuration({}))

    def test_partial_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            self.load().channel_configuration(
                {
                    "DEBATEAI_UPDATE_DESCRIPTOR_URL": "https://updates.example/latest/{platform_id}"
                }
            )

    def config(self):
        return {
            "DEBATEAI_UPDATE_DESCRIPTOR_URL": "https://updates.example/latest/{platform_id}",
            "DEBATEAI_UPDATE_ASSET_URL": "https://updates.example/assets/{version}/{platform_id}",
            "DEBATEAI_UPDATE_KEYS": "/fixture/public-keys.json",
        }

    def test_independent_channel_has_explicit_trust(self):
        c = self.load().channel_configuration(self.config())
        self.assertEqual(c["keys_path"], "/fixture/public-keys.json")
        self.assertEqual(
            c["descriptor_url"], self.config()["DEBATEAI_UPDATE_DESCRIPTOR_URL"]
        )

    def test_legacy_download_service_is_rejected(self):
        c = self.config()
        c["DEBATEAI_UPDATE_DESCRIPTOR_URL"] = (
            "https://updates.invalid/latest/{platform_id}"
        )
        c["DEBATEAI_UPDATE_ASSET_URL"] = (
            "https://updates.invalid/assets/{version}/{platform_id}"
        )
        with self.assertRaises(ValueError):
            self.load().channel_configuration(c)

    def test_origin_mismatch_rejected(self):
        c = self.config()
        c["DEBATEAI_UPDATE_ASSET_URL"] = "https://other.example/{version}/{platform_id}"
        with self.assertRaises(ValueError):
            self.load().channel_configuration(c)

    def test_http_userinfo_query_fragment_and_unknown_placeholder_rejected(self):
        for url in (
            "http://updates.example/{platform_id}",
            "https://name:secret@updates.example/{platform_id}",
            "https://updates.example/{platform_id}?key=secret",
            "https://updates.example/{platform_id}#fragment",
            "https://updates.example/{missing}",
            "https://updates.example/{platform_id.__class__}",
        ):
            c = self.config()
            c["DEBATEAI_UPDATE_DESCRIPTOR_URL"] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.load().channel_configuration(c)

    def test_placeholders_required(self):
        c = self.config()
        c["DEBATEAI_UPDATE_ASSET_URL"] = "https://updates.example/file.zip"
        with self.assertRaises(ValueError):
            self.load().channel_configuration(c)

    def test_old_env_does_not_enable_channel(self):
        self.assertIsNone(
            self.load().channel_configuration(
                {
                    "BACKCHANNEL_DESKTOP": "1",
                    "BACKCHANNEL_UPDATE_KEYS": "/old/trust.json",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
