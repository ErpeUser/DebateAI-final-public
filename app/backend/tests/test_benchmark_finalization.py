"""Regression tests for the real benchmark with an external event-producer double."""

import asyncio
import importlib.util
import sys
import time
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark_debate_copilot.py"
spec = importlib.util.spec_from_file_location("benchmark_finalization_subject", SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class EndpointTests(unittest.TestCase):
    def test_local_http_and_ipv6_are_admitted(self):
        for url in (
            "http://127.0.0.1:11434/v1",
            "https://localhost:9443/v1",
            "http://[::1]:11434/v1",
        ):
            with self.subTest(url=url):
                self.assertEqual(bench.endpoint_scope(url), "loopback")

    def test_invalid_or_credential_bearing_urls_are_not_local(self):
        for url in (
            "file://localhost/a",
            "ftp://127.0.0.1/a",
            "http://u:p@localhost:11434/v1",
            "http://localhost:bad/v1",
            "http://localhost/v1?secret=x",
            "http://localhost/v1#token",
            "http://localhost.evil.example/v1",
            "https://example.com/v1",
            "http://[broken",
            "http://localhost\n/v1",
        ):
            with self.subTest(url=url):
                self.assertEqual(bench.endpoint_scope(url), "network")


class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_run_rejects_cloud_before_model_construction(self):
        args = SimpleNamespace(endpoint="https://example.com/v1")
        with self.assertRaisesRegex(ValueError, "loopback"):
            await bench.run_benchmark(args)


class FakeOrchestrator:
    """Only the event producer is doubled; replay selection/timing is real."""

    def __init__(
        self,
        ws,
        *,
        answer="Das folgt daraus nicht.",
        question="",
        stall=False,
        old=False,
    ):
        self.ws, self.answer, self.question = ws, answer, question
        self.stall, self.old = stall, old
        self._debate_revision = 1
        self._active_claim_id = "claim-current"
        self._transcript_revision = 1
        self._objection_task = None
        self.objection_agent = SimpleNamespace(last_outcome=None)
        self.calls = 0

    async def feed_transcript(self, text, speaker):
        self.calls += 1

        async def produce():
            data = {
                "claim_id": self._active_claim_id,
                "transcript_revision": self._transcript_revision,
                "revision": 1,
                "recommendation_revision": 1,
                "primary_move": "answer",
                "answer_now": self.answer,
                "counter_question": self.question,
                "counterargument": "",
                "analogy": "",
                "target_claim": text,
                "confidence": "low",
                "needs_research": False,
            }
            if self.old:
                await self.ws.send_json(
                    {
                        "type": "debate_update",
                        "data": dict(
                            data,
                            claim_id="old",
                            transcript_revision=0,
                            revision=0,
                            origin="model",
                        ),
                    }
                )
            await self.ws.send_json(
                {"type": "debate_update", "data": dict(data, origin="model_stream")}
            )
            if self.stall:
                await asyncio.Event().wait()
            await self.ws.send_json(
                {"type": "debate_update", "data": dict(data, origin="model")}
            )

        self._objection_task = asyncio.create_task(produce())

    def acknowledge_debate_update(self, **kwargs):
        return kwargs.get("claim_id") == "claim-current"


class ReplayTests(unittest.IsolatedAsyncioTestCase):
    async def measure(
        self, *, answer="Das folgt daraus nicht.", question="", old=False
    ):
        ws = bench._CaptureWebSocket(time.perf_counter)
        producer = FakeOrchestrator(ws, answer=answer, question=question, old=old)
        replay = bench.ApplicationReplay(producer, ws, time.perf_counter)
        with patch.object(
            bench, "evaluate_recommendation_contract", return_value={"status": "pass"}
        ):
            return await replay.measure_turn(
                {"speaker": "Gegenseite", "text": "Jeder Versuch gelingt."},
                turn_index=0,
                timeout_seconds=0.1,
            )

    async def test_optional_counterquestion_does_not_fail_a_spoken_answer(self):
        record = await self.measure()
        self.assertEqual(record["status"], "ok", record)
        self.assertEqual(record["recommendation"]["counter_question"], "")

    async def test_null_spoken_fields_cannot_pass_as_literal_none(self):
        self.assertEqual(
            (await self.measure(answer=None, question=None))["status"], "failed"
        )

    async def test_stale_revision_cannot_supply_this_turn_first_update(self):
        self.assertTrue(
            (await self.measure(question="Welche Belege?", old=True))["ui_acknowledged"]
        )

    async def test_partial_answer_does_not_remove_final_timeout(self):
        ws = bench._CaptureWebSocket(time.perf_counter)
        producer = FakeOrchestrator(ws, stall=True)
        replay = bench.ApplicationReplay(producer, ws, time.perf_counter)
        try:
            try:
                record = await asyncio.wait_for(
                    replay.measure_turn(
                        {"speaker": "G", "text": "Test"},
                        turn_index=0,
                        timeout_seconds=0.02,
                    ),
                    0.2,
                )
            except TimeoutError:
                self.fail("Inner timeout did not cover unfinished worker")
            self.assertEqual(record["error_type"], "TimeoutError")
            await asyncio.sleep(0)
            self.assertTrue(producer._objection_task.cancelled())
            next_record = await replay.measure_turn(
                {"speaker": "G", "text": "next"}, turn_index=1, timeout_seconds=0.02
            )
            self.assertEqual(next_record["status"], "failed")
            self.assertEqual(
                producer.calls, 1, "No overlapping turn after abandoned worker"
            )
        finally:
            if producer._objection_task:
                producer._objection_task.cancel()
                await asyncio.gather(producer._objection_task, return_exceptions=True)


class ModeTests(unittest.TestCase):
    def test_cli_accepts_both_production_modes(self):
        for mode in ("persuasive", "forceful"):
            with (
                self.subTest(mode=mode),
                patch.object(sys, "argv", ["benchmark", "--mode", mode]),
            ):
                self.assertEqual(bench.parse_args().mode, mode)

    def test_replay_preserves_forceful_mode(self):
        from dataclasses import dataclass

        @dataclass
        class Settings:
            mode: str = "persuasive"

        orchestrator_mod = ModuleType("app.services.agents.orchestrator")
        orchestrator_mod.AgentOrchestrator = type("Orchestrator", (), {})
        orchestrator_mod.TranscriptBuffer = type("Buffer", (), {})
        settings_mod = ModuleType("app.services.debate_settings")
        settings_mod.DebateSettings = Settings
        with patch.dict(
            sys.modules,
            {
                orchestrator_mod.__name__: orchestrator_mod,
                settings_mod.__name__: settings_mod,
            },
        ):
            replay = bench.create_application_replay(
                SimpleNamespace(_debate_mode="forceful")
            )
            self.assertEqual(replay.orchestrator.debate_settings.mode, "forceful")


class LocalModelAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, payload, model="qwen3:4b", status=200):
        import httpx

        async def respond(request):
            self.assertEqual(request.url.path, "/api/tags")
            return httpx.Response(status, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await bench.verify_native_local_model(
                "http://127.0.0.1:11434/v1", model, client=client
            )

    async def test_installed_native_model_is_admitted_without_download(self):
        await self.check({"models": [{"name": "qwen3:4b", "digest": "abc"}]})

    async def test_cloud_alias_behind_localhost_is_rejected(self):
        for extra in (
            {"remote_host": "https://ollama.com"},
            {"remote_model": "cloud-model"},
        ):
            with (
                self.subTest(extra=extra),
                self.assertRaisesRegex(ValueError, "remote"),
            ):
                await self.check({"models": [dict(name="qwen3:4b", **extra)]})

    async def test_missing_model_or_unknown_catalog_is_rejected(self):
        for payload in ({"models": []}, {"wrong": True}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                await self.check(payload)

    async def test_catalog_response_is_bounded(self):
        with self.assertRaises(ValueError):
            await self.check({"models": [{"name": "qwen3:4b", "filler": "x" * 300000}]})


class FirstSpeakableTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_fragment_is_not_first_speakable_update(self):
        clock = SimpleNamespace(value=10.0)

        def now():
            return clock.value

        ws = bench._CaptureWebSocket(now)
        producer = FakeOrchestrator(ws)

        async def feed(text, speaker):
            async def emit():
                data = {
                    "revision": 1,
                    "claim_id": producer._active_claim_id,
                    "transcript_revision": producer._transcript_revision,
                    "recommendation_revision": 1,
                    "primary_move": "answer",
                    "counter_question": "",
                    "target_claim": text,
                }
                for at, origin, answer in [
                    (10.001, "model_stream", ""),
                    (10.021, "model_stream", "Der Beleg fehlt."),
                    (10.025, "model", "Der Beleg fehlt."),
                ]:
                    clock.value = at
                    await ws.send_json(
                        {
                            "type": "debate_update",
                            "data": dict(data, origin=origin, answer_now=answer),
                        }
                    )

            producer._objection_task = asyncio.create_task(emit())

        producer.feed_transcript = feed
        replay = bench.ApplicationReplay(producer, ws, now)
        with patch.object(
            bench, "evaluate_recommendation_contract", return_value={"status": "pass"}
        ):
            record = await replay.measure_turn(
                {"speaker": "X", "text": "A"}, turn_index=0, timeout_seconds=0.2
            )
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["first_update_ms"], 21.0)
        self.assertEqual(record["current_update_ms"], 25.0)

    async def test_failed_headless_ack_is_not_success(self):
        ws = bench._CaptureWebSocket(time.perf_counter)
        producer = FakeOrchestrator(ws)
        producer.acknowledge_debate_update = lambda **kwargs: False
        replay = bench.ApplicationReplay(producer, ws, time.perf_counter)
        with patch.object(
            bench, "evaluate_recommendation_contract", return_value={"status": "pass"}
        ):
            record = await replay.measure_turn(
                {"speaker": "X", "text": "A"}, turn_index=0, timeout_seconds=0.2
            )
        self.assertFalse(record["ui_acknowledged"])
        self.assertEqual(record["status"], "failed")


if __name__ == "__main__":
    unittest.main()
