import os
import unittest
import uuid
from pathlib import Path
from unittest import mock


class ChatGPTWebAccountTests(unittest.TestCase):
    def test_switch_archives_only_the_dedicated_profile_and_marker(self):
        from app.routers import chatgpt_web

        root = Path(__file__).parents[1] / ".test-account-switch" / str(uuid.uuid4())
        profile = root / "browser-profile"
        marker = root / "verified.json"
        home = root / "oracle-home"
        profile.mkdir(parents=True)
        home.mkdir()
        (profile / "Cookies").write_text("dedicated", encoding="utf-8")
        marker.write_text("{}", encoding="utf-8")
        untouched = root / "other-user-data.txt"
        untouched.write_text("keep", encoding="utf-8")

        with mock.patch.dict(
            os.environ,
            {
                "BACKCHANNEL_CHATGPT_WEB_PROFILE": str(profile),
                "BACKCHANNEL_CHATGPT_WEB_MARKER": str(marker),
                "BACKCHANNEL_CHATGPT_WEB_HOME": str(home),
            },
            clear=False,
        ):
            archive = chatgpt_web._archive_dedicated_account(include_profile=True)

        self.assertFalse(profile.exists())
        self.assertFalse(marker.exists())
        self.assertEqual((archive / "browser-profile" / "Cookies").read_text(), "dedicated")
        self.assertTrue((archive / "verified.json").is_file())
        self.assertEqual(untouched.read_text(), "keep")

    def test_disconnect_archives_verification_but_keeps_the_session_profile(self):
        from app.routers import chatgpt_web

        root = Path(__file__).parents[1] / ".test-account-disconnect" / str(uuid.uuid4())
        profile = root / "browser-profile"
        marker = root / "verified.json"
        home = root / "oracle-home"
        profile.mkdir(parents=True)
        home.mkdir()
        (profile / "Cookies").write_text("keep-session", encoding="utf-8")
        marker.write_text("{}", encoding="utf-8")

        with mock.patch.dict(
            os.environ,
            {
                "BACKCHANNEL_CHATGPT_WEB_PROFILE": str(profile),
                "BACKCHANNEL_CHATGPT_WEB_MARKER": str(marker),
                "BACKCHANNEL_CHATGPT_WEB_HOME": str(home),
            },
            clear=False,
        ):
            archive = chatgpt_web._archive_dedicated_account(include_profile=False)

        self.assertTrue((profile / "Cookies").is_file())
        self.assertFalse(marker.exists())
        self.assertTrue((archive / "verified.json").is_file())


if __name__ == "__main__":
    unittest.main()
