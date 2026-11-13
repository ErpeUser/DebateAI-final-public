import unittest
from types import SimpleNamespace
from unittest import mock

from app.routers import gemini_web

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

    def test_status_uses_persisted_endpoint_models_when_runtime_catalog_is_empty(self):
        endpoint = SimpleNamespace(
            enabled=True,
            models=[
                {"id": "gemini-quick-answers"},
                {"id": "gemini-most-complex-work"},
            ],
        )

        async def run():
            with (
                mock.patch.object(
                    gemini_web,
                    "stored_gemini_web_cookie_configured",
                    mock.AsyncMock(return_value=True),
                ),
                mock.patch.object(gemini_web, "gemini_web_models", return_value=[]),
                mock.patch.object(
                    gemini_web,
                    "get_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ),
            ):
                return await gemini_web._status(object())

        import asyncio

        status = asyncio.run(run())
        self.assertTrue(status["ready"])
        self.assertEqual(
            ["gemini-quick-answers", "gemini-most-complex-work"],
            status["models"],
        )


if __name__ == "__main__":
    unittest.main()
