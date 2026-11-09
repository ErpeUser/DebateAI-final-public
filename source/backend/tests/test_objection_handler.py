import unittest
import uuid
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app.services.agents.objection_handler import (
    DebateRecommendation,
    LiveDebateResponse,
    ObjectionHandlerAgent,
    ObjectionHandlerOutput,
    _compose_rationale,
)


SPEAKER_ID = str(uuid.uuid4())
SPEAKERS = [{"id": SPEAKER_ID, "name": "Speaker 1"}]


def _model_item(**overrides) -> dict:
    item = {
        "item_type": "objection",
        "question": "Pricing is higher than the budgeted amount",
        "response_now": "Totally fair — can I ask what number you had budgeted so we can look at phasing?",
        "bigger_picture": "Cost justification concern; build the ROI case before the next call.",
        "source_context": "That's way more than we planned to spend this year.",
        "severity": "high",
        "speaker_id": SPEAKER_ID,
    }
    item.update(overrides)
    return item


def _model_recommendation() -> DebateRecommendation:
    return DebateRecommendation(
        answer_now="Das greift zu kurz.",
        counterargument="Die Praemisse ist nicht belegt.",
        counter_question="Welche Quelle stuetzt das?",
        analogy="Das ist wie ein Urteil ohne Beweisaufnahme.",
    )


class ComposeRationaleTests(unittest.TestCase):
    def test_includes_micro_macro_and_severity(self):
        rationale = _compose_rationale(_model_item())
        self.assertIn("Respond now:", rationale)
        self.assertIn("Bigger picture:", rationale)
        self.assertIn("(Severity: high)", rationale)

    def test_skips_missing_fields_and_bad_severity(self):
        rationale = _compose_rationale({"response_now": "Say this.", "severity": "urgent"})
        self.assertEqual(rationale, "Respond now: Say this.")


class ObjectionHandlerCycleTests(unittest.IsolatedAsyncioTestCase):
    def test_debate_mode_uses_the_compact_recommendation_prompt(self):
        agent = ObjectionHandlerAgent(recommendation_only=True)
        self.assertIn("LIVE-DEBATTENVERTRAG", agent._prompt_template)
        self.assertNotIn("What Counts as an Objection", agent._prompt_template)

    def test_custom_prompt_is_preserved_in_debate_mode(self):
        agent = ObjectionHandlerAgent(
            recommendation_only=True,
            prompt_override="Custom {transcript_window}",
        )
        self.assertEqual(agent._prompt_template, "Custom {transcript_window}")

    def test_live_schema_requires_target_and_choice_but_not_a_fixed_bundle(self):
        required = set(LiveDebateResponse.model_json_schema().get("required", []))
        self.assertEqual({"primary_move", "target_claim"}, required)

    async def test_recommendation_accepts_ranked_two_move_state(self):
        recommendation = DebateRecommendation.model_validate(
            {
                "answer_now": "Diese Folgerung braucht noch einen Beleg.",
                "counter_question": "Welcher Beleg traegt genau diese Folgerung?",
                "primary_move": "question",
                "question_status": "partial",
                "open_question": "Warum gilt dieser Massstab nur hier?",
                "follow_ups": [
                    {
                        "condition": "Wenn nur ein Beispiel genannt wird",
                        "question": "Wie zeigt ein Einzelfall die allgemeine Regel?",
                    }
                ],
            }
        )

        payload = recommendation.model_dump()
        self.assertEqual("question", payload.get("primary_move"))
        self.assertEqual("partial", payload.get("question_status"))
        self.assertEqual("Warum gilt dieser Massstab nur hier?", payload.get("open_question"))
        self.assertEqual(1, len(payload.get("follow_ups", [])))

    async def test_follow_ups_are_limited_to_two(self):
        with self.assertRaises(ValidationError):
            DebateRecommendation.model_validate(
                {
                    "follow_ups": [
                        {"condition": "A", "question": "Frage eins?"},
                        {"condition": "B", "question": "Frage zwei?"},
                        {"condition": "C", "question": "Frage drei?"},
                    ]
                }
            )

    async def test_spoken_moves_are_normalized_to_word_limits(self):
        recommendation = DebateRecommendation(
            answer_now=" ".join(f"Antwort{i}" for i in range(30)),
            counter_question=" ".join(f"Frage{i}" for i in range(18)) + "?",
        )

        # An indivisible sentence is kept intact rather than silently changing
        # its meaning. Complete shorter sentences are still preferred.
        self.assertEqual(30, len(recommendation.answer_now.split()))
        self.assertEqual(18, len(recommendation.counter_question.split()))
        self.assertTrue(recommendation.counter_question.endswith("?"))

    async def test_missing_optional_counterargument_does_not_trigger_retry(self):
        incomplete = ObjectionHandlerOutput(
            recommendation=DebateRecommendation(
                answer_now="Das beantwortet den Einwand direkt.",
                counter_question="Welcher Beleg traegt Ihre Schlussfolgerung?",
                analogy="Das ist wie ein Urteil ohne Beweisaufnahme.",
            )
        )
        complete = ObjectionHandlerOutput(
            recommendation=_model_recommendation()
        )
        generate = AsyncMock(side_effect=[incomplete, complete])
        agent = ObjectionHandlerAgent()

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("Speaker 1: Das folgt zwingend daraus.", [], SPEAKERS)

        self.assertEqual(1, generate.await_count)
        self.assertEqual("", agent.latest_recommendation.counterargument)

    async def test_single_primary_answer_is_not_retried_by_default(self):
        response = LiveDebateResponse(
            answer_now="Die Schlussfolgerung folgt nicht aus der Praemisse.",
            primary_move="answer",
            target_claim="Das folge zwingend daraus.",
        )
        generate = AsyncMock(return_value=response)
        agent = ObjectionHandlerAgent(recommendation_only=True)

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("Speaker 1: Das folgt zwingend daraus.", [], SPEAKERS)

        self.assertEqual(1, generate.await_count)
        self.assertEqual(response.answer_now, agent.latest_recommendation.answer_now)

    async def test_explicit_blank_model_is_not_replaced(self):
        self.assertEqual("", ObjectionHandlerAgent(model_override="")._model)

    async def test_run_cycle_parses_and_tags_items(self):
        agent = ObjectionHandlerAgent()
        output = ObjectionHandlerOutput(
            recommendation=_model_recommendation(), items=[_model_item()]
        )

        with patch(
            "app.services.agents.objection_handler.generate_json",
            new=AsyncMock(return_value=output),
        ) as generate:
            items = await agent.run_cycle("Speaker 1: too expensive", [], SPEAKERS)

        self.assertIs(ObjectionHandlerOutput, generate.await_args.args[2])
        self.assertEqual("none", generate.await_args.kwargs["reasoning_effort"])
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["item_type"], "objection")
        self.assertEqual(item["agent_source"], "objection_handler")
        self.assertEqual(item["speaker_id"], SPEAKER_ID)
        self.assertIn("Respond now:", item["rationale"])
        self.assertIn("Bigger picture:", item["rationale"])
        self.assertEqual("insights", agent.last_outcome["kind"])

    async def test_run_cycle_forwards_the_explicit_resource_profile(self):
        output = ObjectionHandlerOutput(
            recommendation=_model_recommendation(), items=[]
        )
        generate = AsyncMock(return_value=output)

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await ObjectionHandlerAgent().run_cycle(
                "Speaker 1: Das folgt zwingend daraus.",
                [],
                SPEAKERS,
                resource_profile="economy",
            )

        self.assertEqual("economy", generate.await_args.kwargs["resource_profile"])

    async def test_live_prompt_handles_noisy_asr_without_inventing_personal_history(self):
        output = LiveDebateResponse(**_model_recommendation().model_dump())
        generate = AsyncMock(return_value=output)

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await ObjectionHandlerAgent(recommendation_only=True).run_cycle(
                "Teilnehmer: Ich bin gegen Abkaelbungen, das ist mein Fall.",
                [],
                SPEAKERS,
            )

        request_text = " ".join(
            (generate.await_args.args[1] + generate.await_args.kwargs["system"]).split()
        )
        self.assertIn("ASR-Transkript kann Fehler enthalten", request_text)
        self.assertIn("keine erfundenen persoenlichen Erlebnisse", request_text)
        self.assertIn("offensichtlich beschaedigte Formulierung", request_text)
        self.assertIn("nur bei hoher Sicherheit", request_text)
        self.assertIn("Zugestaendnis, Kontrast oder Konsequenz", request_text)

    async def test_forceful_mode_adds_claim_focused_playbook(self):
        agent = ObjectionHandlerAgent(debate_mode="forceful")
        generate = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("Speaker 1: Das ist falsch.", [], SPEAKERS)

        system = generate.await_args.kwargs["system"]
        self.assertIn("BRUTAL-SACHLICH", system)
        self.assertIn("Behauptung", system)
        self.assertIn("nie die Person", system)
        self.assertIn("Position, Beweislast und Konsistenz", system)
        self.assertIn("Ausnahme fuer sich selbst", system)

    async def test_persuasive_mode_adds_steelman_and_common_ground_playbook(self):
        agent = ObjectionHandlerAgent(debate_mode="persuasive")
        generate = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("Speaker 1: Ich sehe das anders.", [], SPEAKERS)

        system = generate.await_args.kwargs["system"]
        self.assertIn("UEBERZEUGEND", system)
        self.assertIn("Steelman", system)
        self.assertIn("gemeinsame Basis", system)
        self.assertIn("eigenen Lager", system)
        self.assertIn("unentschlossene Mitleser", system)

    async def test_natural_style_focus_adds_only_a_bounded_style_instruction(self):
        agent = ObjectionHandlerAgent(style_focus="natural")
        generate = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("Speaker 1: Das klingt kuenstlich.", [], SPEAKERS)

        system = generate.await_args.kwargs["system"]
        self.assertIn("NATUERLICH", system)
        self.assertIn("gesprochenem Deutsch", system)

    async def test_prompt_requests_word_limits_ranking_and_conservative_question_state(self):
        agent = ObjectionHandlerAgent()
        generate = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("External: Das beantwortet die Frage nur teilweise.", [], SPEAKERS)

        request_text = generate.await_args.args[1] + generate.await_args.kwargs["system"]
        self.assertIn("25 Woerter", request_text)
        self.assertIn("6-14 Woerter", request_text)
        self.assertIn("primary_move", request_text)
        self.assertIn("team", request_text.lower())
        self.assertIn("external", request_text.lower())
        self.assertIn("Ausweichen nie erfinden", request_text)
        self.assertIn("staerksten relevanten Punkt", request_text)
        self.assertIn("vergleichende Wirkung", request_text)
        self.assertIn("Ironie", request_text)
        self.assertIn("erkennbare Hyperbel", request_text)

    async def test_analogy_setting_is_explicit_in_the_model_instruction(self):
        required = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )
        optional = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )

        with patch("app.services.agents.objection_handler.generate_json", new=required):
            await ObjectionHandlerAgent(always_analogy=True).run_cycle(
                "External: Das ist falsch.", [], SPEAKERS
            )
        with patch("app.services.agents.objection_handler.generate_json", new=optional):
            await ObjectionHandlerAgent(always_analogy=False).run_cycle(
                "External: Das ist falsch.", [], SPEAKERS
            )

        self.assertIn("Analogie MUSS", required.await_args.kwargs["system"])
        self.assertIn("Analogie nur", optional.await_args.kwargs["system"])

    async def test_previous_question_state_is_included_in_next_cycle(self):
        first = DebateRecommendation.model_validate(
            {
                **_model_recommendation().model_dump(),
                "primary_move": "question",
                "question_status": "partial",
                "open_question": "Welche konkrete Quelle belegt das?",
                "follow_ups": [
                    {
                        "condition": "Wenn wieder nur eine Behauptung folgt",
                        "question": "Welche nachpruefbare Quelle stuetzt das konkret?",
                    }
                ],
            }
        )
        generate = AsyncMock(
            side_effect=[
                ObjectionHandlerOutput(recommendation=first, items=[]),
                ObjectionHandlerOutput(recommendation=_model_recommendation(), items=[]),
            ]
        )
        agent = ObjectionHandlerAgent()

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("External: Irgendwo stand das.", [], SPEAKERS)
            await agent.run_cycle("Team: Welche konkrete Quelle belegt das?", [], SPEAKERS)

        second_prompt = generate.await_args_list[1].args[1]
        self.assertIn("partial", second_prompt)
        self.assertIn("Welche konkrete Quelle belegt das?", second_prompt)
        self.assertIn("Wenn wieder nur eine Behauptung folgt", second_prompt)

    async def test_missing_analogy_triggers_one_correction(self):
        incomplete = _model_recommendation().model_copy(update={"analogy": ""})
        recovered = _model_recommendation()
        generate = AsyncMock(
            side_effect=[
                ObjectionHandlerOutput(recommendation=incomplete, items=[]),
                ObjectionHandlerOutput(recommendation=recovered, items=[]),
            ]
        )
        agent = ObjectionHandlerAgent(always_analogy=True)

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("Speaker 1: Das ist unlogisch.", [], SPEAKERS)

        self.assertEqual(2, generate.await_count)
        self.assertEqual(recovered, agent.latest_recommendation)
        self.assertIn("analogy", generate.await_args.args[1])

    async def test_unchanged_window_skips_llm_call(self):
        agent = ObjectionHandlerAgent()
        mock_generate = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=_model_recommendation(), items=[]
            )
        )

        with patch("app.services.agents.objection_handler.generate_json", new=mock_generate):
            await agent.run_cycle("Speaker 1: same text", [], SPEAKERS)
            self.assertEqual("no_findings", agent.last_outcome["kind"])
            await agent.run_cycle("Speaker 1: same text", [], SPEAKERS)

        self.assertEqual(mock_generate.await_count, 1)
        self.assertEqual("skipped_unchanged", agent.last_outcome["kind"])

    async def test_surfaced_objections_fed_back_into_prompt(self):
        agent = ObjectionHandlerAgent()
        mock_generate = AsyncMock(
            side_effect=[
                ObjectionHandlerOutput(
                    recommendation=_model_recommendation(), items=[_model_item()]
                ),
                ObjectionHandlerOutput(
                    recommendation=_model_recommendation(), items=[]
                ),
            ]
        )

        with patch("app.services.agents.objection_handler.generate_json", new=mock_generate):
            await agent.run_cycle("Speaker 1: window one", [], SPEAKERS)
            await agent.run_cycle("Speaker 1: window two", [], SPEAKERS)

        second_prompt = mock_generate.await_args_list[1].args[1]
        self.assertIn("Pricing is higher than the budgeted amount", second_prompt)

    async def test_unknown_speaker_id_normalized_to_none(self):
        agent = ObjectionHandlerAgent()
        output = ObjectionHandlerOutput(
            recommendation=_model_recommendation(),
            items=[_model_item(speaker_id=str(uuid.uuid4()))]
        )

        with patch(
            "app.services.agents.objection_handler.generate_json",
            new=AsyncMock(return_value=output),
        ):
            items = await agent.run_cycle("Speaker 1: too expensive", [], SPEAKERS)

        self.assertIsNone(items[0]["speaker_id"])

    async def test_malformed_items_report_each_drop_reason(self):
        agent = ObjectionHandlerAgent()
        with self.assertLogs(
            "app.services.agents.objection_handler", level="WARNING"
        ) as logs:
            items = agent._parse_response(
                [_model_item(), {"item_type": "objection"}, "junk"],
                {SPEAKER_ID},
            )

        self.assertEqual(len(items), 1)
        self.assertIn("question=None", "\n".join(logs.output))
        self.assertIn("entry_type=str", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
