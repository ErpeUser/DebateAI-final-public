"""Provider failures must preserve their cause and finalize the audit record."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from app.services import external_audit, llm
from app.services.llm_endpoint import OpenAIEndpoint
from pydantic import BaseModel


class _Reply(BaseModel):
    answer: str


class LLMRequestFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_errors_and_cancellation_preserve_audit_lifecycle(self):
        endpoint = OpenAIEndpoint(
            base_url="https://provider.invalid/v1", model="test-model", api_key=""
        )
        real_client = httpx.AsyncClient
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            for route in (
                "google_text",
                "google_json",
                "openai_text",
                "openai_json",
                "openai_stream",
                "ollama_json",
                "ollama_stream",
            ):
                for failure_type, status in (
                    (RuntimeError, "failed"),
                    (asyncio.CancelledError, "cancelled"),
                ):
                    with self.subTest(route=route, status=status):
                        audit_path.unlink(missing_ok=True)
                        failure = failure_type("simulated provider interruption")

                        async def fail_request(request):
                            raise failure

                        def client_factory(**kwargs):
                            return real_client(
                                transport=httpx.MockTransport(fail_request), **kwargs
                            )

                        google_client = SimpleNamespace(
                            aio=SimpleNamespace(
                                models=SimpleNamespace(
                                    generate_content=AsyncMock(side_effect=failure)
                                )
                            )
                        )
                        with (
                            patch.object(
                                external_audit, "_audit_path", return_value=audit_path
                            ),
                            patch.object(
                                llm, "_google_client", return_value=google_client
                            ),
                            patch.object(
                                llm, "_google_generation_limits", return_value={}
                            ),
                            patch.object(
                                llm.httpx, "AsyncClient", side_effect=client_factory
                            ),
                            self.assertRaises(failure_type) as raised,
                        ):
                            if route == "google_text":
                                await llm._call_google(
                                    "gemini-test", "prompt", None, None, ""
                                )
                            elif route == "google_json":
                                await llm._google_json(
                                    "gemini-test",
                                    "prompt",
                                    _Reply,
                                    "{}",
                                    "",
                                    None,
                                    "test",
                                )
                            elif route == "openai_text":
                                await llm._call_openai(
                                    "gpt-test", endpoint, "prompt", None, None, ""
                                )
                            elif route.startswith("openai"):
                                await llm._openai_json(
                                    "gpt-test",
                                    endpoint,
                                    "prompt",
                                    _Reply,
                                    "{}",
                                    "",
                                    None,
                                    "test",
                                    None,
                                    on_partial_json=AsyncMock()
                                    if route.endswith("stream")
                                    else None,
                                )
                            else:
                                await llm._ollama_native_debate_json(
                                    "endpoint:test:test-model",
                                    endpoint,
                                    "prompt",
                                    _Reply,
                                    None,
                                    "test",
                                    None,
                                    AsyncMock() if route.endswith("stream") else None,
                                    "balanced",
                                )
                        self.assertIs(raised.exception, failure)
                        records = [
                            json.loads(line)
                            for line in audit_path.read_text().splitlines()
                        ]
                        # Google JSON may retry a failed request. Every actual
                        # attempt still needs exactly one terminal event.
                        self.assertTrue(records)
                        self.assertEqual(len(records) % 2, 0)
                        request_ids = set()
                        for started, finished in zip(records[::2], records[1::2]):
                            self.assertEqual(
                                [started["status"], finished["status"]],
                                ["started", status],
                            )
                            self.assertEqual(
                                started["request_id"], finished["request_id"]
                            )
                            self.assertNotIn(started["request_id"], request_ids)
                            request_ids.add(started["request_id"])
                            if status == "failed":
                                self.assertEqual(
                                    finished["error_class"], "RuntimeError"
                                )
                        self.assertNotIn(
                            "simulated provider interruption", audit_path.read_text()
                        )


if __name__ == "__main__":
    unittest.main()
