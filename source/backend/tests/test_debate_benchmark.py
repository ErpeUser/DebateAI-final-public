import asyncio
import inspect
import unittest

from scripts.benchmark_debate_copilot import (
    ApplicationReplay,
    DEFAULT_TURNS,
    build_request_payload,
    benchmark_protect_and_guard,
    create_application_replay,
    elapsed_ms,
    endpoint_scope,
    evaluate_recommendation_contract,
    load_turns,
    measure_turn,
    run_supersession_probe,
    summarize,
)
from app.services.agents.objection_handler import DebateRecommendation


class FakeClock:
    def __init__(self):
        self.value = 10.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class StreamingFixtureClient:
    def __init__(self, clock):
        self.clock = clock

    async def stream(self, _turns):
        self.clock.advance(0.08)
        yield '{"answer_now":"Das greift zu kurz.",'
        self.clock.advance(0.12)
        yield '"counterargument":"Der Vergleich fehlt.","counter_question":"Welche Quelle?","analogy":"Wie ein Preis ohne Produkt."}'


class SlowFixtureClient:
    async def stream(self, _turns):
        await asyncio.sleep(0.03)
        yield '{"answer_now":"A","counterargument":"B","counter_question":"C","analogy":"D"}'


class FailingFixtureClient:
    async def stream(self, _turns):
        raise TimeoutError("fixture timeout")
        yield ""  # pragma: no cover - keeps this an async generator


class FinalProbeFailureClient:
    def __init__(self):
        self.calls = 0

    async def stream(self, _turns):
        self.calls += 1
        if self.calls == 3:
            raise RuntimeError("final probe failed")
        await asyncio.sleep(1)
        yield '{"answer_now":"A","counterargument":"B","counter_question":"C","analogy":"D"}'


class ApplicationFixtureAgent:
    def __init__(self, clock):
        self.clock = clock
        self.latest_recommendation = DebateRecommendation()
        self.last_outcome = None

    async def run_cycle(self, **_kwargs):
        self.clock.advance(0.25)
        self.latest_recommendation = DebateRecommendation(
            answer_now="Direkte Antwort",
            counterargument="Gegenargument",
            counter_question="Rueckfrage?",
            analogy="Wie ein Preis ohne Produkt.",
        )
        self.last_outcome = {"kind": "no_findings", "items": 0}
        return []


class TemplateOnlyFixtureAgent:
    def __init__(self):
        self.latest_recommendation = DebateRecommendation()
        self.last_outcome = None

    def instant_recommendation(self, _window):
        return DebateRecommendation(
            answer_now="Nur Schablone",
            counterargument="Noch keine Modellanalyse",
            counter_question="Welcher Beleg?",
            analogy="Wie ein Entwurf.",
            provisional=True,
        )

    async def run_cycle(self, **_kwargs):
        self.last_outcome = {"kind": "error", "error": {"message": "model failed"}}
        return []


class TemplateAndModelFixtureAgent(ApplicationFixtureAgent):
    def instant_recommendation(self, _window):
        return DebateRecommendation(
            answer_now="Sofortentwurf",
            counterargument="Vorlaeufiger Einwand",
            counter_question="Welcher Beleg?",
            analogy="Wie ein Entwurf.",
            provisional=True,
        )

    async def run_cycle(self, **_kwargs):
        self.clock.advance(0.25)
        self.latest_recommendation = DebateRecommendation(
            answer_now="Direkte Modellantwort",
            counterargument="Das Modell nennt den entscheidenden Grund.",
            counter_question="Welcher Beleg traegt den Schluss?",
            analogy="Wie ein Preis ohne Produkt.",
            target_claim="Der aktuelle Streitpunkt.",
            argument_points=["Der Schluss braucht einen Beleg."],
            confidence="high",
        )
        self.last_outcome = {"kind": "no_findings", "items": 0}
        return []


class DebateBenchmarkTests(unittest.IsolatedAsyncioTestCase):
    def test_contract_preflight_reports_speakability_and_keeps_human_review_open(self):
        result = evaluate_recommendation_contract({
            "primary_move": "answer",
            "answer_now": "Das ist ohne Beleg nicht belastbar.",
            "counter_question": "Welche Quelle belegt das?",
            "target_claim": "Die Quote liegt bei acht Prozent.",
            "confidence": "low",
        })

        self.assertEqual("pass", result["status"])
        self.assertEqual(1.0, result["score"])
        self.assertTrue(result["human_review_required"])
        self.assertIn("speakable_primary", result["checks"])

    def test_contract_preflight_rejects_unbounded_numeric_claim_without_evidence(self):
        result = evaluate_recommendation_contract({
            "primary_move": "answer",
            "answer_now": "Exakt 73 Prozent stimmen zu.",
            "counter_question": "Welche Quelle belegt das?",
            "target_claim": "73 Prozent stimmen zu.",
            "confidence": "high",
        })

        self.assertEqual("fail", result["status"])
        self.assertFalse(result["checks"]["evidence_guard"])
        self.assertTrue(result["human_review_required"])

    def test_contract_preflight_marks_missing_question_as_failure(self):
        result = evaluate_recommendation_contract({
            "primary_move": "question",
            "answer_now": "Eine Antwort ohne Frage.",
            "target_claim": "Die Behauptung.",
        })

        self.assertEqual("fail", result["status"])
        self.assertFalse(result["checks"]["speakable_primary"])

    async def test_loopback_benchmark_guard_does_not_touch_database(self):
        prompt, system = await benchmark_protect_and_guard(
            "fixture prompt", system="fixture system", model_id="local"
        )
        self.assertEqual(prompt, "fixture prompt")
        self.assertEqual(system, "fixture system")

    def test_endpoint_scope_distinguishes_loopback_from_network_egress(self):
        self.assertEqual("loopback", endpoint_scope("http://127.0.0.1:11434/v1"))
        self.assertEqual("loopback", endpoint_scope("http://localhost:11434/v1"))
        self.assertEqual("network", endpoint_scope("https://models.example/v1"))

    def test_local_qwen_request_disables_reasoning_and_requires_json(self):
        payload = build_request_payload(list(DEFAULT_TURNS[:1]), "qwen3:4b")
        self.assertEqual(payload["reasoning_effort"], "none")
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_production_benchmark_uses_compact_debate_schema(self):
        source = inspect.getsource(__import__(
            "scripts.benchmark_debate_copilot", fromlist=["run_benchmark"]
        ).run_benchmark)
        self.assertIn("recommendation_only=True", source)
        self.assertIn('style_focus="natural"', source)

    def test_elapsed_time_is_monotonic(self):
        self.assertEqual(elapsed_ms(1.0, 1.125), 125.0)
        with self.assertRaises(ValueError):
            elapsed_ms(2.0, 1.0)

    def test_default_fixture_is_deterministic_and_returned_as_a_copy(self):
        first = load_turns(None)
        second = load_turns(None)
        self.assertEqual(first, list(DEFAULT_TURNS))
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertTrue(all(turn["text"].strip() for turn in first))

    async def test_measurement_records_first_and_current_update_latency(self):
        clock = FakeClock()
        record = await measure_turn(
            StreamingFixtureClient(clock),
            [{"speaker": "Gegenseite", "text": "Das ist zu teuer."}],
            turn_index=0,
            clock=clock,
        )
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["first_update_ms"], 80.0)
        self.assertEqual(record["current_update_ms"], 200.0)
        self.assertLessEqual(record["first_update_ms"], record["current_update_ms"])
        self.assertIsNone(record["source_refinement_ms"])

    async def test_supersession_probe_counts_cancelled_requests(self):
        result = await run_supersession_probe(
            SlowFixtureClient(),
            list(DEFAULT_TURNS[:3]),
            delay_seconds=0.0,
        )
        self.assertEqual(result["cancellation_count"], 2)
        self.assertEqual(result["completed_count"], 1)
        self.assertEqual(result["failure_count"], 0)

    async def test_supersession_probe_retains_a_failed_final_request(self):
        result = await run_supersession_probe(
            FinalProbeFailureClient(),
            list(DEFAULT_TURNS[:3]),
            delay_seconds=0.0,
        )
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["records"][-1]["status"], "failed")
        self.assertIn("final probe failed", result["records"][-1]["error"])
        summary = summarize([], cancellation_count=2, probe_failure_count=1)
        self.assertEqual(summary["failure_count"], 1)
        self.assertEqual(summary["probe_failure_count"], 1)

    async def test_application_replay_measures_the_real_debate_update_path(self):
        clock = FakeClock()
        replay = create_application_replay(
            ApplicationFixtureAgent(clock),
            clock=clock,
        )
        self.assertIsInstance(replay, ApplicationReplay)
        self.assertEqual("balanced", replay.orchestrator.debate_settings.performance_profile)

        record = await replay.measure_turn(
            {"speaker": "Gegenseite", "text": "Das ist zu teuer."},
            turn_index=0,
            timeout_seconds=1,
        )

        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["revision"], 1)
        self.assertEqual(record["first_update_ms"], 250.0)
        self.assertEqual(record["current_update_ms"], 250.0)
        self.assertEqual(record["deep_revision_ms"], 250.0)
        self.assertEqual(record["accepted_model_ms"], 250.0)
        self.assertTrue(record["ui_acknowledged"])
        self.assertIn("quality_preflight", record)
        self.assertTrue(record["quality_preflight"]["human_review_required"])
        self.assertEqual(record["deep_recommendation"]["answer_now"], "Direkte Antwort")
        self.assertEqual(record["recommendation"]["answer_now"], "Direkte Antwort")
        self.assertEqual(replay.websocket.messages[0]["type"], "debate_update")

        summary = summarize([record], cancellation_count=0)
        self.assertEqual(250.0, summary["median_accepted_model_ms"])
        self.assertEqual(0, summary["technical_quality_pass_count"])
        self.assertEqual(1, summary["technical_quality_failure_count"])
        self.assertEqual(1, summary["human_review_required_count"])

    async def test_sequential_turn_ignores_unread_event_from_prior_turn(self):
        clock = FakeClock()
        replay = create_application_replay(
            TemplateAndModelFixtureAgent(clock),
            clock=clock,
        )

        first = await replay.measure_turn(
            {"speaker": "Gegenseite", "text": "Erster Punkt."},
            turn_index=0,
            timeout_seconds=1,
        )
        second = await replay.measure_turn(
            {"speaker": "Gegenseite", "text": "Zweiter Punkt."},
            turn_index=1,
            timeout_seconds=1,
        )

        self.assertEqual("ok", first["status"])
        self.assertEqual("ok", second["status"])
        self.assertEqual(250.0, second["first_update_ms"])
        self.assertEqual(250.0, second["accepted_model_ms"])

    async def test_application_probe_waits_until_worker_claims_revision(self):
        replay = create_application_replay(ApplicationFixtureAgent(FakeClock()))
        result = await replay.supersession_probe(
            [dict(DEFAULT_TURNS[0])],
            delay_seconds=0,
            timeout_seconds=1,
        )
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["statuses"], ["ok"])

    async def test_spoken_playbook_probe_uses_the_local_mic_control_contract(self):
        replay = create_application_replay(ApplicationFixtureAgent(FakeClock()))

        result = await replay.spoken_playbook_probe(
            context="Ein vorhandener Streitpunkt.",
            timeout_seconds=1,
        )

        self.assertEqual("ok", result["status"])
        self.assertTrue(result["command_consumed"])
        self.assertTrue(result["transcript_unchanged"])

    async def test_deterministic_supersession_replay_has_zero_stale_publishes(self):
        replay = create_application_replay(ApplicationFixtureAgent(FakeClock()))

        result = await replay.supersession_probe(
            list(DEFAULT_TURNS),
            delay_seconds=0,
            timeout_seconds=1,
        )

        self.assertEqual(0, result["failure_count"])
        self.assertEqual(0, result["stale_publishes"])
        self.assertEqual(0, replay.websocket.stale_publishes)

    async def test_application_replay_does_not_count_template_without_model_answer(self):
        replay = create_application_replay(TemplateOnlyFixtureAgent())

        record = await replay.measure_turn(
            {"speaker": "Gegenseite", "text": "Das ist zu teuer."},
            turn_index=0,
            timeout_seconds=1,
        )

        self.assertEqual("failed", record["status"])
        self.assertIsNone(record["first_update_ms"])
        self.assertIsNone(record["accepted_model_ms"])
        self.assertIn("model", record["error"].lower())

    async def test_failure_output_is_honest_and_has_no_fake_latency(self):
        record = await measure_turn(
            FailingFixtureClient(),
            [{"speaker": "Gegenseite", "text": "Belege das."}],
            turn_index=0,
        )
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error_type"], "TimeoutError")
        self.assertIn("fixture timeout", record["error"])
        self.assertIsNone(record["first_update_ms"])
        self.assertIsNone(record["current_update_ms"])
        summary = summarize([record], cancellation_count=0)
        self.assertEqual(summary["failure_count"], 1)
        self.assertIsNone(summary["median_current_update_ms"])
        self.assertIsNone(summary["median_deep_revision_ms"])


if __name__ == "__main__":
    unittest.main()