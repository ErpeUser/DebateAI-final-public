import unittest

from app.routers.gemini_web import _normalize_cookie


class GeminiWebCookieTests(unittest.TestCase):
    def test_accepts_only_the_two_session_cookies_required_by_upstream(self):
        value = _normalize_cookie(
            "__Secure-1PSID=first-secret; __Secure-1PSIDTS=second-secret; NID=route"
        )
        self.assertIn("__Secure-1PSID=", value)
        self.assertIn("__Secure-1PSIDTS=", value)

    def test_rejects_old_or_incomplete_cookie_exports(self):
        with self.assertRaisesRegex(ValueError, "__Secure-1PSIDTS"):
            _normalize_cookie("SAPISID=old; __Secure-1PSID=only-one")


if __name__ == "__main__":
    unittest.main()
