import os
import unittest
from unittest import mock


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    handler = None

    def __init__(self, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, url, **kwargs):
        return self.handler("GET", url, kwargs)

    async def post(self, url, **kwargs):
        return self.handler("POST", url, kwargs)


class SubscriptionOAuthTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from app.services import subscription_oauth

        self.oauth = subscription_oauth
        self.environment = mock.patch.dict(
            os.environ,
            {
                "DEBATEAI_SUBSCRIPTION_BRIDGE_URL": "http://127.0.0.1:8317/v1",
                "DEBATEAI_SUBSCRIPTION_BRIDGE_KEY": "local-only-key",
            },
            clear=True,
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    async def test_gemini_login_uses_plugin_oauth_without_api_key(self):
        calls = []

        def handler(method, url, kwargs):
            calls.append((method, url, kwargs))
            return _Response(
                {
                    "status": "ok",
                    "url": "https://accounts.google.com/o/oauth2/auth?state=test",
                    "state": "gemini-state-123",
                }
            )

        _Client.handler = staticmethod(handler)
        with mock.patch.object(self.oauth.httpx, "AsyncClient", _Client):
            flow = await self.oauth.start_login("gemini-cli")

        self.assertEqual("gemini-cli", flow["provider"])
        self.assertEqual("gemini-state-123", flow["state"])
        self.assertEqual("gemini-cli", calls[0][2]["params"]["provider"])
        self.assertNotIn("GEMINI_API_KEY", os.environ)

    async def test_explicit_verification_sends_exact_model_at_high(self):
        calls = []

        def handler(method, url, kwargs):
            calls.append((method, url, kwargs))
            return _Response(
                {
                    "model": "gemini-3.1-pro-preview",
                    "choices": [{"message": {"content": "OK"}}],
                }
            )

        _Client.handler = staticmethod(handler)
        with (
            mock.patch.object(self.oauth.httpx, "AsyncClient", _Client),
            mock.patch.object(
                self.oauth,
                "models",
                mock.AsyncMock(return_value=["gemini-3.1-pro-preview"]),
            ),
        ):
            result = await self.oauth.verify_gemini_31_pro_high()

        payload = calls[0][2]["json"]
        self.assertEqual("gemini-3.1-pro-preview", payload["model"])
        self.assertEqual("high", payload["reasoning_effort"])
        self.assertEqual("high", result["thinking"])

    def test_catalog_prefers_exact_pro_then_available_high_model(self):
        self.assertEqual(
            "gemini-3.1-pro-preview",
            self.oauth.preferred_gemini_model(
                ["gemini-3.8-flash-high", "gemini-3.1-pro-preview"]
            ),
        )
        self.assertEqual(
            "gemini-3.8-flash-high",
            self.oauth.preferred_gemini_model(
                ["gemini-3-flash", "gemini-3.8-flash-high"]
            ),
        )

    async def test_verification_uses_available_high_model_when_pro_is_absent(self):
        calls = []

        def handler(method, url, kwargs):
            calls.append((method, url, kwargs))
            return _Response(
                {
                    "model": "gemini-3.8-flash-high",
                    "choices": [{"message": {"content": "OK"}}],
                }
            )

        _Client.handler = staticmethod(handler)
        with (
            mock.patch.object(self.oauth.httpx, "AsyncClient", _Client),
            mock.patch.object(
                self.oauth,
                "models",
                mock.AsyncMock(
                    return_value=["gemini-3-flash", "gemini-3.8-flash-high"]
                ),
            ),
        ):
            result = await self.oauth.verify_preferred_gemini_high()

        self.assertEqual("gemini-3.8-flash-high", calls[0][2]["json"]["model"])
        self.assertEqual("high", calls[0][2]["json"]["reasoning_effort"])
        self.assertEqual("gemini-3.8-flash-high", result["model"])

    def test_public_bridge_address_is_rejected(self):
        with mock.patch.dict(
            os.environ,
            {"DEBATEAI_SUBSCRIPTION_BRIDGE_URL": "https://example.com/v1"},
        ):
            self.assertIsNone(self.oauth.connection())


if __name__ == "__main__":
    unittest.main()
