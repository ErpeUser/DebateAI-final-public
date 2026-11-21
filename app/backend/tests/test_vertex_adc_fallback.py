import unittest
from types import SimpleNamespace
from unittest import mock

from app.services import llm
from app.services.llm_endpoint import OpenAIEndpoint
from pydantic import BaseModel


class _Reply(BaseModel):
    answer: str = ""


class VertexAdcTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        local_only = mock.patch.object(
            llm, "is_local_only", mock.AsyncMock(return_value=False)
        )
        local_only.start()
        self.addCleanup(local_only.stop)
        pii = mock.patch.object(
            llm.pii_egress,
            "protect_and_guard",
            mock.AsyncMock(
                side_effect=lambda prompt, **kwargs: (prompt, kwargs.get("system"))
            ),
        )
        pii.start()
        self.addCleanup(pii.stop)

    async def test_vertex_adc_google_call_needs_no_api_key(self):
        with (
            mock.patch.dict(llm.settings.__dict__, {"GOOGLE_GENAI_USE_VERTEXAI": True}),
            mock.patch.object(llm, "_resolve_key", mock.AsyncMock(return_value="")),
            mock.patch.object(
                llm, "_call_google", mock.AsyncMock(return_value=("adc reply", None))
            ),
            mock.patch.object(llm, "record_token_usage", mock.AsyncMock()),
        ):
            reply = await llm.generate_text("gemini-3.5-flash", "hello")

        self.assertEqual("adc reply", reply)

    async def test_google_client_uses_vertex_project_and_location(self):
        response = SimpleNamespace(text="ok", usage_metadata=None)
        client = SimpleNamespace(
            aio=SimpleNamespace(
                models=SimpleNamespace(
                    generate_content=mock.AsyncMock(return_value=response)
                )
            )
        )
        with (
            mock.patch.dict(
                llm.settings.__dict__,
                {
                    "GOOGLE_GENAI_USE_VERTEXAI": True,
                    "GOOGLE_CLOUD_PROJECT": "project-0c960003-cd51-4e36-a49",
                    "GOOGLE_CLOUD_LOCATION": "global",
                },
            ),
            mock.patch.object(llm.genai, "Client", return_value=client) as factory,
        ):
            text, _usage = await llm._call_google(
                "gemini-3.5-flash", "hello", None, None, ""
            )

        self.assertEqual("ok", text)
        factory.assert_called_once_with(
            vertexai=True,
            project="project-0c960003-cd51-4e36-a49",
            location="global",
        )


class SpendCapFallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        local_only = mock.patch.object(
            llm, "is_local_only", mock.AsyncMock(return_value=False)
        )
        local_only.start()
        self.addCleanup(local_only.stop)
        pii = mock.patch.object(
            llm.pii_egress,
            "protect_and_guard",
            mock.AsyncMock(
                side_effect=lambda prompt, **kwargs: (prompt, kwargs.get("system"))
            ),
        )
        pii.start()
        self.addCleanup(pii.stop)
        self.endpoint = OpenAIEndpoint(
            base_url="http://127.0.0.1:8317/v1",
            model="gemini-3.5-flash",
            api_key="bridge-key",
        )

    def _settings(self):
        return mock.patch.dict(
            llm.settings.__dict__,
            {
                "GOOGLE_GENAI_USE_VERTEXAI": True,
                "SUBSCRIPTION_BRIDGE_BUDGET_FALLBACK": True,
                "SUBSCRIPTION_BRIDGE_FALLBACK_MODEL": "",
            },
        )

    async def test_text_falls_back_only_when_vertex_reports_spend_cap(self):
        cap_error = RuntimeError("429 RESOURCE_EXHAUSTED: monthly spend cap exceeded")
        fallback = mock.AsyncMock(return_value=("bridge reply", {"total_tokens": 4}))
        with (
            self._settings(),
            mock.patch.object(llm, "_resolve_key", mock.AsyncMock(return_value="")),
            mock.patch.object(
                llm, "_call_google", mock.AsyncMock(side_effect=cap_error)
            ),
            mock.patch.object(
                llm, "resolve_endpoint", mock.AsyncMock(return_value=self.endpoint)
            ) as resolve,
            mock.patch.object(llm, "_call_openai", fallback),
            mock.patch.object(llm, "record_token_usage", mock.AsyncMock()),
        ):
            reply = await llm.generate_text("gemini-3.5-flash", "hello")

        self.assertEqual("bridge reply", reply)
        self.assertEqual(
            "endpoint:subscription-ai:gemini-3.5-flash",
            resolve.await_args.args[1],
        )
        fallback.assert_awaited_once()

    async def test_generic_rate_limit_does_not_use_subscription_bridge(self):
        rate_error = RuntimeError("429 RESOURCE_EXHAUSTED: per-minute rate limit")
        fallback = mock.AsyncMock()
        with (
            self._settings(),
            mock.patch.object(llm, "_resolve_key", mock.AsyncMock(return_value="")),
            mock.patch.object(
                llm, "_call_google", mock.AsyncMock(side_effect=rate_error)
            ),
            mock.patch.object(llm, "_call_openai", fallback),
            mock.patch.object(llm, "record_token_usage", mock.AsyncMock()),
        ):
            with self.assertRaisesRegex(RuntimeError, "rate limit"):
                await llm.generate_text("gemini-3.5-flash", "hello")

        fallback.assert_not_awaited()

    async def test_structured_call_uses_same_spend_cap_fallback(self):
        cap_error = RuntimeError("429: billing monthly spend cap has been reached")
        with (
            self._settings(),
            mock.patch.object(llm, "_resolve_key", mock.AsyncMock(return_value="")),
            mock.patch.object(
                llm, "_google_json", mock.AsyncMock(side_effect=cap_error)
            ),
            mock.patch.object(
                llm, "resolve_endpoint", mock.AsyncMock(return_value=self.endpoint)
            ),
            mock.patch.object(
                llm,
                "_openai_json",
                mock.AsyncMock(return_value=_Reply(answer="bridge json")),
            ) as fallback,
        ):
            reply = await llm.generate_json(
                "gemini-3.5-flash", "prompt", _Reply, source="debate_copilot"
            )

        self.assertEqual("bridge json", reply.answer)
        fallback.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
