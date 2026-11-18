import tempfile
import unittest
from unittest.mock import patch
from http.cookies import SimpleCookie
from pathlib import Path

from debateai_desktop.gemini_web_login import (
    REQUIRED_GEMINI_COOKIES,
    cookie_header_from_webview,
    wait_for_authenticated_cookie_header,
    write_login_result,
    _webview_gui,
)


class GeminiWebLoginTests(unittest.TestCase):
    def test_webview_backend_matches_desktop_platform(self):
        with patch("debateai_desktop.gemini_web_login.sys.platform", "linux"):
            self.assertEqual("gtk", _webview_gui())
        with patch("debateai_desktop.gemini_web_login.sys.platform", "darwin"):
            self.assertEqual("cocoa", _webview_gui())
        with patch("debateai_desktop.gemini_web_login.sys.platform", "win32"):
            self.assertEqual("edgechromium", _webview_gui())

    def test_cookie_header_keeps_webview_cookies_without_logging_them(self):
        first = SimpleCookie()
        first["__Secure-1PSID"] = "psid-secret"
        second = SimpleCookie()
        second["__Secure-1PSIDTS"] = "psidts-secret"
        second["NID"] = "routing-value"

        header = cookie_header_from_webview([first, second])

        self.assertIn("__Secure-1PSID=psid-secret", header)
        self.assertIn("__Secure-1PSIDTS=psidts-secret", header)
        self.assertIn("NID=routing-value", header)
        self.assertTrue(all(f"{name}=" in header for name in REQUIRED_GEMINI_COOKIES))

    def test_cookie_header_rejects_an_incomplete_login(self):
        cookie = SimpleCookie()
        cookie["__Secure-1PSID"] = "only-one-cookie"

        self.assertEqual("", cookie_header_from_webview([cookie]))

    def test_login_result_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "login.json"
            write_login_result(
                target,
                {"cookie": "__Secure-1PSID=x; __Secure-1PSIDTS=y"},
            )
            self.assertTrue(target.is_file())
            self.assertFalse(target.with_suffix(".json.new").exists())

    def test_login_keeps_polling_after_the_initial_page_load(self):
        incomplete = SimpleCookie()
        incomplete["__Secure-1PSID"] = "first"
        complete_a = SimpleCookie()
        complete_a["__Secure-1PSID"] = "first"
        complete_b = SimpleCookie()
        complete_b["__Secure-1PSIDTS"] = "second"
        responses = iter([[incomplete], [incomplete], [complete_a, complete_b]])

        header = wait_for_authenticated_cookie_header(
            lambda: next(responses),
            attempts=3,
            poll_seconds=0,
        )

        self.assertIn("__Secure-1PSID=first", header)
        self.assertIn("__Secure-1PSIDTS=second", header)


if __name__ == "__main__":
    unittest.main()
