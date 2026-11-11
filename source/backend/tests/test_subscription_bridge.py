import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


class SubscriptionBridgeRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cookie_cleanup_sends_explicit_disconnect_signal(self):
        from app.services import subscription_bridge

        path = mock.Mock()
        with mock.patch.object(
            subscription_bridge, "_gemini_web_cookie_path", return_value=path
        ):
            subscription_bridge.cleanup_gemini_web_cookie()

        path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        path.write_text.assert_called_once_with("", encoding="utf-8")
        path.unlink.assert_not_called()

    async def test_active_web_session_does_not_require_plaintext_cookie_file(self):
        from app.services import subscription_bridge

        with mock.patch.dict(
            os.environ,
            {"DEBATEAI_GEMINI_WEB_SESSION_ACTIVE": "1"},
            clear=True,
        ):
            self.assertTrue(subscription_bridge.gemini_web_cookie_configured())

    async def test_desktop_bridge_registers_current_models_as_local_endpoint(self):
        from app.services import subscription_bridge

        db = object()
        endpoint = SimpleNamespace(id="subscription-login-bridge")
        with (
            mock.patch.dict(
                os.environ,
                {
                    "DEBATEAI_SUBSCRIPTION_BRIDGE_URL": "http://127.0.0.1:8317/v1",
                    "DEBATEAI_SUBSCRIPTION_BRIDGE_KEY": "local-secret",
                },
            ),
            mock.patch.object(
                subscription_bridge,
                "probe",
                mock.AsyncMock(return_value=(True, "Connected", ["gpt-test", "gemini-test"])),
            ),
            mock.patch.object(
                subscription_bridge,
                "get_endpoint",
                mock.AsyncMock(return_value=endpoint),
            ),
            mock.patch.object(
                subscription_bridge,
                "update_endpoint",
                mock.AsyncMock(return_value=endpoint),
            ) as update,
        ):
            result = await subscription_bridge.sync_subscription_bridge(db)

        self.assertIs(result, endpoint)
        self.assertEqual(
            update.await_args.kwargs["models"],
            [{"id": "gpt-test"}, {"id": "gemini-test"}],
        )
        self.assertEqual(update.await_args.kwargs["api_key"], "local-secret")
        self.assertTrue(update.await_args.kwargs["enabled"])

    async def test_no_desktop_environment_is_a_noop(self):
        from app.services import subscription_bridge

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(await subscription_bridge.sync_subscription_bridge(object()))

    async def test_startup_uses_the_desktop_verified_bridge_models(self):
        from app.services import subscription_bridge

        endpoint = SimpleNamespace(id="subscription-ai")
        with (
            mock.patch.dict(
                os.environ,
                {
                    "DEBATEAI_SUBSCRIPTION_BRIDGE_URL": "http://127.0.0.1:8317/v1",
                    "DEBATEAI_SUBSCRIPTION_BRIDGE_KEY": "local-secret",
                },
            ),
            mock.patch.object(
                subscription_bridge,
                "probe",
                mock.AsyncMock(return_value=(True, "Connected", ["gpt-test"])),
            ) as probe,
            mock.patch.object(
                subscription_bridge,
                "get_endpoint",
                mock.AsyncMock(return_value=endpoint),
            ),
            mock.patch.object(
                subscription_bridge,
                "update_endpoint",
                mock.AsyncMock(return_value=endpoint),
            ) as update,
        ):
            await subscription_bridge.sync_subscription_bridge(object())

        self.assertEqual(probe.await_count, 1)
        self.assertEqual(update.await_args.kwargs["models"], [{"id": "gpt-test"}])

    async def test_web_bridge_registers_only_models_reported_by_the_account(self):
        from app.services import subscription_bridge

        endpoint = SimpleNamespace(id="gemini-web")
        with tempfile.TemporaryDirectory() as tmp:
            cookie = Path(tmp) / "cookie.txt"
            cookie.write_text("x" * 80, encoding="utf-8")
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "DEBATEAI_GEMINI_WEB_URL": "http://127.0.0.1:4981/openai/v1",
                        "DEBATEAI_GEMINI_WEB_KEY": "local-secret",
                        "DEBATEAI_GEMINI_WEB_COOKIE_FILE": str(cookie),
                    },
                ),
                mock.patch.object(
                    subscription_bridge,
                    "probe",
                    mock.AsyncMock(
                        return_value=(
                            True,
                            "Connected",
                            ["gemini-auto", "gemini-3.1-pro"],
                        )
                    ),
                ),
                mock.patch.object(
                    subscription_bridge,
                    "get_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ),
                mock.patch.object(
                    subscription_bridge,
                    "update_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ) as update,
            ):
                result = await subscription_bridge.sync_gemini_web_bridge(object())

        self.assertIs(result, endpoint)
        self.assertEqual(
            update.await_args.kwargs["models"],
            [
                {"id": "gemini-auto", "label": "gemini-auto"},
                {"id": "gemini-3.1-pro", "label": "gemini-3.1-pro"},
            ],
        )
        self.assertTrue(update.await_args.kwargs["enabled"])

    async def test_web_bridge_waits_past_empty_transitional_catalog(self):
        from app.services import subscription_bridge

        endpoint = SimpleNamespace(id="gemini-web")
        with tempfile.TemporaryDirectory() as tmp:
            cookie = Path(tmp) / "cookie.txt"
            cookie.write_text("x" * 80, encoding="utf-8")
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "DEBATEAI_GEMINI_WEB_URL": "http://127.0.0.1:4981/openai/v1",
                        "DEBATEAI_GEMINI_WEB_KEY": "local-secret",
                        "DEBATEAI_GEMINI_WEB_COOKIE_FILE": str(cookie),
                    },
                ),
                mock.patch.object(
                    subscription_bridge,
                    "probe",
                    mock.AsyncMock(
                        side_effect=[
                            (True, "Connected", []),
                            (True, "Connected", ["gemini-3.1-pro"]),
                        ]
                    ),
                ) as probe,
                mock.patch.object(
                    subscription_bridge,
                    "get_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ),
                mock.patch.object(
                    subscription_bridge,
                    "update_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ) as update,
                mock.patch.object(subscription_bridge.asyncio, "sleep", mock.AsyncMock()),
            ):
                await subscription_bridge.sync_gemini_web_bridge(object())

        self.assertEqual(probe.await_count, 2)
        self.assertEqual(
            update.await_args.kwargs["models"],
            [{"id": "gemini-3.1-pro", "label": "gemini-3.1-pro"}],
        )
        self.assertTrue(update.await_args.kwargs["enabled"])

    async def test_web_bridge_does_not_invent_pro_when_account_only_has_auto(self):
        from app.services import subscription_bridge

        endpoint = SimpleNamespace(id="gemini-web")
        with tempfile.TemporaryDirectory() as tmp:
            cookie = Path(tmp) / "cookie.txt"
            cookie.write_text("x" * 80, encoding="utf-8")
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "DEBATEAI_GEMINI_WEB_URL": "http://127.0.0.1:4981/openai/v1",
                        "DEBATEAI_GEMINI_WEB_KEY": "local-secret",
                        "DEBATEAI_GEMINI_WEB_COOKIE_FILE": str(cookie),
                    },
                ),
                mock.patch.object(
                    subscription_bridge,
                    "probe",
                    mock.AsyncMock(return_value=(True, "Connected", ["gemini-auto"])),
                ),
                mock.patch.object(
                    subscription_bridge,
                    "get_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ),
                mock.patch.object(
                    subscription_bridge,
                    "update_endpoint",
                    mock.AsyncMock(return_value=endpoint),
                ) as update,
            ):
                await subscription_bridge.sync_gemini_web_bridge(object())
                served_after_sync = subscription_bridge.gemini_web_models()

        self.assertEqual(
            update.await_args.kwargs["models"],
            [{"id": "gemini-auto", "label": "gemini-auto"}],
        )
        self.assertNotIn("gemini-3.1-pro", served_after_sync)


if __name__ == "__main__":
    unittest.main()
