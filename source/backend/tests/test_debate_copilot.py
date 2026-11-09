import asyncio
import unittest
import uuid
from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.objection_handler import (
    DeepDebateAnalysis,
    DebateRecommendation,
    DebateSource,
    LiveDebateResponse,
    LogicalRelation,
    ObjectionHandlerAgent,
    ObjectionHandlerItem,
    ObjectionHandlerOutput,
    _has_speakable_guidance,
    _limit_spoken_words,
    build_deep_analysis_prompt,
)
from app.services.agents.base import TranscriptBuffer
from app.services.agents.orchestrator import (
    AgentOrchestrator,
    live_debate_snapshot,
    _manual_research_query,
    _materially_better_recommendation,
    _contains_unsupported_numeric_assertion,
    _unicode_words,
    _bind_research_result,
)
from app.services.debate_research import ResearchResult, ResearchSource
from app.services.debate_settings import DebateSettings


SPEAKER_ID = str(uuid.uuid4())
SPEAKERS = [{"id": SPEAKER_ID, "name": "Alex", "speaker_type": "external"}]


class DebateRecommendationTests(unittest.IsolatedAsyncioTestCase):
    def test_single_primary_question_is_valid_without_a_mandatory_bundle(self):
        response = LiveDebateResponse(
            primary_move="question",
            counter_question="Welche Quelle belegt diese Zahl?",
            target_claim="Die Quote liege bei acht Prozent.",
        )
        recommendation = DebateRecommendation(**response.model_dump())

        self.assertTrue(_has_speakable_guidance(recommendation))
        self.assertEqual("", recommendation.answer_now)
        self.assertEqual("", recommendation.counterargument)
        self.assertEqual("", recommendation.analogy)

    def test_selected_primary_move_must_contain_speakable_text(self):
        recommendation = DebateRecommendation(
            primary_move="question",
            answer_now="Das ist eine brauchbare Antwort.",
            target_claim="Die Behauptung.",
        )

        self.assertFalse(_has_speakable_guidance(recommendation))

    def test_cached_research_is_rebound_to_corrected_claim_and_revision(self):
        cached = ResearchResult(
            claim="Die Quote liegt bei acht Prozent.",
            query="Quote pruefen",
            status="completed",
            sources=[ResearchSource(
                title="Amtliche Reihe",
                url="https://example.test/rate",
                snippet="Die Rate liegt bei 2,2 Prozent.",
                provider="test",
                claim="Die Quote liegt bei acht Prozent.",
                claim_revision=1,
            )],
        )

        rebound = _bind_research_result(
            cached,
            "Die Quote liegt nicht bei acht Prozent.",
            claim_revision=3,
        )

        self.assertEqual("Die Quote liegt nicht bei acht Prozent.", rebound.claim)
        self.assertEqual("Die Quote liegt nicht bei acht Prozent.", rebound.sources[0].claim)
        self.assertEqual(3, rebound.sources[0].claim_revision)

    def test_deep_analysis_prompt_is_compact_and_claim_specific(self):
        prompt = build_deep_analysis_prompt(
            claim="Wenn Freiheit wichtig ist, darf es keinerlei Regeln geben.",
            own_position="Freiheit braucht faire Grenzen, die gleiche Freiheit schuetzen.",
            relevant_context="Frueherer Claim: Jede Regel sei automatisch Zwang.",
            sources=[],
        )

        self.assertIn("keinerlei Regeln", prompt)
        self.assertIn("faire Grenzen", prompt)
        self.assertIn("Frueherer Claim", prompt)
        self.assertLess(len(prompt), 2400)
        self.assertNotIn("Wikipedia", prompt)

    async def test_deep_analysis_uses_requested_external_model(self):
        analysis = DeepDebateAnalysis(
            best_reply="Freiheit ohne gleiche Grenzen wird zur Freiheit des Staerkeren.",
            counterarguments=["Die Folgerung setzt Freiheit mit Regellosigkeit gleich."],
            rebuttal="Regeln koennen Freiheit sichern, statt sie nur zu begrenzen.",
            interpretation="Die versteckte Praemisse lautet, jede Regel sei Zwang.",
            followups=["Welche Freiheit bleibt den Schwaecheren ohne Regeln?"],
        )
        generate = AsyncMock(return_value=analysis)
        agent = ObjectionHandlerAgent(session_id=uuid.uuid4())

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            result, prompt = await agent.analyze_deep(
                DebateRecommendation(
                    answer_now="Regeln und Freiheit sind kein Widerspruch.",
                    counter_question="Warum ist jede Regel automatisch Zwang?",
                    target_claim="Wenn Freiheit wichtig ist, darf es keinerlei Regeln geben.",
                ),
                model_id="gpt-5.5-mini",
                own_position="Freiheit braucht faire Grenzen.",
                relevant_context="",
                sources=[],
            )

        self.assertEqual(analysis, result)
        self.assertIn("keinerlei Regeln", prompt)
        self.assertEqual("gpt-5.5-mini", generate.await_args.args[0])
        self.assertEqual("debate_analyst", generate.await_args.kwargs["source"])

    def test_deep_analysis_keeps_only_typed_claim_relations(self):
        analysis = DeepDebateAnalysis(
            best_reply="Beide Aussagen koennen fuer denselben Zeitraum nicht zugleich gelten.",
            logical_relations=[
                LogicalRelation(
                    target_claim_id="claim-1",
                    relation="contradicts",
                    confidence=0.92,
                    verified=True,
                )
            ],
        )

        relation = analysis.logical_relations[0]
        self.assertEqual("claim-1", relation.target_claim_id)
        self.assertEqual("contradicts", relation.relation)
        self.assertTrue(relation.verified)

    def test_spoken_limit_never_removes_a_trailing_negation(self):
        sentence = (
            "Wenn die Quelle nur eine kleine Auswahl befragt und den Zeitraum nicht nennt, "
            "dann belegt dieses Ergebnis die behauptete Mehrheit trotz der vielen genannten Einzelwerte nicht."
        )

        shortened = _limit_spoken_words(sentence, 25)

        self.assertTrue(shortened.endswith("nicht."))
        self.assertIn("Wenn", shortened)

    def test_low_confidence_or_planned_research_does_not_validate_a_number(self):
        recommendation = DebateRecommendation(
            answer_now="Die Quote liegt bei exakt 73 Prozent.",
            counterargument="Das ist die klare Mehrheit.",
            counter_question="Warum ignorierst du diese Mehrheit?",
            analogy="Wie eine eindeutige Abstimmung.",
            target_claim="73 Prozent stimmen zu.",
            confidence="low",
            needs_research=True,
            research_query="Quote pruefen",
        )

        self.assertTrue(_contains_unsupported_numeric_assertion(recommendation))

    def test_german_unicode_number_words_are_checked_without_mojibake(self):
        recommendation = DebateRecommendation(
            answer_now="Die Quote liegt bei fünf Prozent.",
            counterargument="Das ist die klare Mehrheit.",
            target_claim="Die Quote liegt bei fünf Prozent.",
            confidence="high",
        )

        self.assertTrue(_contains_unsupported_numeric_assertion(recommendation))

    def test_unicode_word_tokenizer_keeps_german_umlauts(self):
        self.assertEqual({"fünf", "grösserer", "massstab"}, _unicode_words("Fünf größerer Maßstab"))

    def test_unrelated_found_source_does_not_validate_a_number(self):
        recommendation = DebateRecommendation(
            answer_now="Die Quote liegt bei exakt 73 Prozent.",
            counterargument="Das ist die klare Mehrheit.",
            counter_question="Warum ignorierst du diese Mehrheit?",
            analogy="Wie eine eindeutige Abstimmung.",
            target_claim="73 Prozent stimmen zu.",
            confidence="high",
            sources=[DebateSource(
                title="Irgendeine Seite",
                url="https://example.test",
                claim="Ein anderes Thema",
                verification_status="found",
            )],
        )

        self.assertTrue(_contains_unsupported_numeric_assertion(recommendation))

    def test_source_id_and_number_do_not_validate_mismatched_scope_metadata(self):
        recommendation = DebateRecommendation(
            answer_now="73 Prozent im Jahr 2023 unter allen Einwohnern stimmen zu.",
            counterargument="Das ist die Mehrheit.",
            target_claim="73 Prozent stimmen zu.",
            confidence="high",
            sources=[DebateSource(
                title="Studie",
                url="https://example.test/studie",
                claim="73 Prozent der befragten Erwachsenen stimmten zu.",
                passage="73 Prozent im Jahr 2024 unter befragten Erwachsenen.",
                claim_relation="supports",
                verification_status="supports",
                retrieval_status="read",
                numeric_unit="Prozent",
                numeric_period="2024",
                numeric_population="befragte Erwachsene",
            )],
        )

        self.assertTrue(_contains_unsupported_numeric_assertion(recommendation))

    def test_source_metadata_can_validate_a_matching_numeric_scope(self):
        recommendation = DebateRecommendation(
            answer_now="73 Prozent im Jahr 2024 unter befragten Erwachsenen stimmen zu.",
            counterargument="Das ist die Mehrheit.",
            target_claim="73 Prozent stimmen zu.",
            confidence="high",
            sources=[DebateSource(
                title="Studie",
                url="https://example.test/studie",
                claim="73 Prozent der befragten Erwachsenen stimmten zu.",
                passage="73 Prozent im Jahr 2024 unter befragten Erwachsenen.",
                claim_relation="supports",
                verification_status="supports",
                retrieval_status="read",
                numeric_unit="Prozent",
                numeric_period="2024",
                numeric_population="befragte Erwachsene",
            )],
        )

        self.assertFalse(_contains_unsupported_numeric_assertion(recommendation))

    def test_slow_revision_must_address_the_current_claim(self):
        current = DebateRecommendation(
            answer_now="Die Zahl ist ohne Quelle nicht belastbar.",
            counterargument="Quelle und Grundgesamtheit fehlen.",
            counter_question="Welche Erhebung belegt das konkret?",
            analogy="Eine Zahl ohne Basis ist ein Preisschild ohne Ware.",
            target_claim="Neunzig Prozent der Spieler sehen das genauso.",
        )
        stale = DebateRecommendation(
            answer_now="Der holprige Start sagt nichts über das heutige Spiel.",
            counterargument="Der Zustand hat sich geändert.",
            counter_question="Welche Fehler bestehen heute noch?",
            analogy="Ein Startfoto ist nicht das Zielbild.",
            target_claim="Cyberpunk hatte am Anfang Bugs.",
            confidence="high",
            argument_points=["Heute statt Release bewerten"],
        )

        self.assertFalse(_materially_better_recommendation(current, stale))

    def test_unverified_numeric_revision_cannot_overwrite_safe_first_move(self):
        current = DebateRecommendation(
            answer_now="Die Zahl ist ohne Quelle nicht belastbar.",
            counterargument="Quelle und Grundgesamtheit fehlen.",
            counter_question="Welche Erhebung belegt das konkret?",
            analogy="Eine Zahl ohne Basis ist ein Preisschild ohne Ware.",
            target_claim="Neunzig Prozent der Spieler sehen das genauso.",
        )
        unsafe = DebateRecommendation(
            answer_now="Heute bewerten 90 Prozent der Spieler das Spiel positiv.",
            counterargument="Die Mehrheit bestätigt die Qualität.",
            counter_question="Warum ignorierst du diese Mehrheit?",
            analogy="Die Abstimmung ist eindeutig.",
            target_claim="Neunzig Prozent der Spieler sehen das genauso.",
            confidence="high",
            argument_points=["90 Prozent Zustimmung"],
        )

        self.assertFalse(_materially_better_recommendation(current, unsafe))

    def test_relevant_structured_revision_can_improve_the_first_move(self):
        current = DebateRecommendation(
            answer_now="Das ist zunächst nur eine Behauptung.",
            counterargument="Der Beleg fehlt.",
            counter_question="Wo ist die Prämisse belegt?",
            analogy="Eine Behauptung ist noch kein Beweis.",
            target_claim="Speicher sind unbezahlbar.",
        )
        improved = DebateRecommendation(
            answer_now="'Unbezahlbar' ist absolut; nenne Kosten, Zeitraum und Vergleich.",
            counterargument="Ohne Bezugswert trägt der Preisvorwurf nicht.",
            counter_question="Unbezahlbar verglichen mit welcher Alternative?",
            analogy="Ein Preis ohne Vergleich ist eine Zahl ohne Maßstab.",
            target_claim="Speicher seien unbezahlbar.",
            confidence="medium",
            argument_points=["Kostenmaßstab fehlt"],
            needs_research=True,
            research_query="aktuelle Speicherkosten Deutschland pro kWh",
        )

        self.assertTrue(_materially_better_recommendation(current, improved))

    def test_multiple_arguments_are_bounded_for_the_compact_context(self):
        with self.assertRaises(Exception):
            DebateRecommendation(argument_points=[str(index) for index in range(13)])

    def test_output_has_an_empty_safe_recommendation(self):
        output = ObjectionHandlerOutput(items=[])

        self.assertEqual("", output.recommendation.answer_now)
        self.assertEqual("", output.recommendation.counterargument)
        self.assertEqual("", output.recommendation.counter_question)
        self.assertEqual("", output.recommendation.analogy)
        self.assertEqual("low", output.recommendation.confidence)
        self.assertFalse(output.recommendation.needs_research)

    async def test_cycle_exposes_speakable_german_guidance_and_keeps_objections(self):
        output = ObjectionHandlerOutput(
            recommendation=DebateRecommendation(
                answer_now="Das ist ein fairer Punkt. Entscheidend ist die Wirkung.",
                counterargument="Die Folgekosten des Nichtstuns sind hoeher.",
                counter_question="Welche Alternative loest das Problem schneller?",
                analogy="Das ist wie eine Versicherung: Der Preis allein sagt nichts ueber das vermiedene Risiko.",
                target_claim="Die Umstellung ist zu teuer.",
                confidence="high",
            ),
            items=[
                ObjectionHandlerItem(
                    question="Die Umstellung ist zu teuer.",
                    response_now="Lassen Sie uns Gesamtkosten vergleichen.",
                    bigger_picture="Die Sorge gilt dem Kostenrisiko.",
                    source_context="Das kostet uns zu viel.",
                    severity="high",
                    speaker_id=SPEAKER_ID,
                )
            ],
        )
        agent = ObjectionHandlerAgent()

        with patch(
            "app.services.agents.objection_handler.generate_json",
            new=AsyncMock(return_value=output),
        ):
            items = await agent.run_cycle(
                "[S1]: Das kostet uns zu viel.", [], SPEAKERS
            )

        self.assertEqual(1, len(items))
        self.assertEqual("objection", items[0]["item_type"])
        self.assertEqual(output.recommendation, agent.latest_recommendation)
        self.assertLessEqual(len(agent.latest_recommendation.answer_now.split(".")), 3)

    async def test_prompt_demands_german_brevity_and_disables_thinking(self):
        agent = ObjectionHandlerAgent()
        generate = AsyncMock(
            return_value=ObjectionHandlerOutput(
                recommendation=DebateRecommendation(
                    answer_now="Direkte Antwort.",
                    counterargument="Klares Gegenargument.",
                    counter_question="Welche Quelle?",
                    analogy="Das ist wie ein Urteil ohne Beweis.",
                ),
                items=[],
            )
        )

        with patch(
            "app.services.agents.objection_handler.generate_json", new=generate
        ):
            await agent.run_cycle("[S1]: Das stimmt so nicht.", [], SPEAKERS)

        system = generate.await_args.kwargs["system"]
        prompt = generate.await_args.args[1]
        self.assertIn("/no_think", system)
        self.assertTrue(prompt.rstrip().endswith("/no_think"))
        self.assertIn("Deutsch", system)
        self.assertIn("1-2", system)
        self.assertEqual("debate_copilot", generate.await_args.kwargs["source"])

    async def test_prompt_stays_loyal_to_user_position_and_handles_topic_changes(self):
        agent = ObjectionHandlerAgent(recommendation_only=True)
        generate = AsyncMock(
            return_value=LiveDebateResponse(
                answer_now="Das ist meine Position; entscheidend ist die tragfaehige Begruendung.",
                counterargument="Der Themenwechsel beantwortet den offenen Punkt nicht.",
                counter_question="Welche Praemisse bestreitest du konkret?",
                analogy="Ein neues Kapitel schliesst die offene Rechnung nicht.",
                primary_move="answer",
                target_claim="Dann reden wir jetzt ueber ein anderes Thema.",
                argument_points=["Der bisherige Punkt bleibt offen."],
                confidence="high",
                needs_research=False,
                research_query="",
            )
        )
        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            await agent.run_cycle("[S1]: Dann reden wir jetzt ueber ein anderes Thema.", [], SPEAKERS)

        system = generate.await_args.kwargs["system"]
        self.assertIn("Nutzerseite", system)
        self.assertIn("erfinde keine Fakten", system)
        # Keep the complete live schema and ASR-safety contract bounded while
        # still allowing the mode-specific instruction appended at runtime.
        self.assertLess(len(system), 2000)
        self.assertIs(generate.await_args.args[2], LiveDebateResponse)

    async def test_semantically_empty_guidance_is_not_retried(self):
        objection = ObjectionHandlerItem(
            question="Das ist zu teuer.",
            response_now="Lassen Sie uns die Gesamtkosten vergleichen.",
            bigger_picture="Die Sorge gilt dem Kostenrisiko.",
        )
        generate = AsyncMock(return_value=ObjectionHandlerOutput(items=[objection]))
        agent = ObjectionHandlerAgent()

        with patch(
            "app.services.agents.objection_handler.generate_json", new=generate
        ):
            items = await agent.run_cycle(
                "[S1]: Nennen Sie Ihr Gegenargument.", [], SPEAKERS
            )

        self.assertEqual(1, generate.await_count)
        self.assertEqual("", agent.latest_recommendation.answer_now)
        self.assertEqual("no_guidance", agent.last_outcome["kind"])
        self.assertEqual("Das ist zu teuer.", items[0]["question"])

    async def test_empty_guidance_does_not_fail_or_lose_objections(self):
        objection = ObjectionHandlerItem(
            question="Das ist zu teuer.",
            response_now="Lassen Sie uns die Gesamtkosten vergleichen.",
            bigger_picture="Die Sorge gilt dem Kostenrisiko.",
        )
        generate = AsyncMock(return_value=ObjectionHandlerOutput(items=[objection]))
        agent = ObjectionHandlerAgent()

        with patch(
            "app.services.agents.objection_handler.generate_json", new=generate
        ):
            items = await agent.run_cycle("[S1]: Das ist zu teuer.", [], SPEAKERS)

        self.assertEqual("Das ist zu teuer.", items[0]["question"])
        self.assertEqual(1, generate.await_count)
        self.assertEqual("no_guidance", agent.last_outcome["kind"])
        self.assertEqual("", agent.latest_recommendation.answer_now)

    async def test_empty_guidance_does_not_trigger_retry_exception(self):
        objection = ObjectionHandlerItem(
            question="Das ist zu teuer.",
            response_now="Lassen Sie uns die Gesamtkosten vergleichen.",
            bigger_picture="Die Sorge gilt dem Kostenrisiko.",
        )
        generate = AsyncMock(return_value=ObjectionHandlerOutput(items=[objection]))
        agent = ObjectionHandlerAgent()

        with patch(
            "app.services.agents.objection_handler.generate_json", new=generate
        ):
            items = await agent.run_cycle("[S1]: Das ist zu teuer.", [], SPEAKERS)

        self.assertEqual("Das ist zu teuer.", items[0]["question"])
        self.assertEqual(1, generate.await_count)
        self.assertEqual("no_guidance", agent.last_outcome["kind"])
        self.assertEqual("", agent.latest_recommendation.answer_now)

    async def test_uncertain_fact_requests_one_narrow_research_query(self):
        recommendation = DebateRecommendation(
            answer_now="Das sollte ich nicht als gesichert darstellen.",
            counterargument="Die genannte Zahl ist noch unbelegt.",
            counter_question="Auf welche Erhebung stuetzt sich diese Zahl?",
            analogy="Eine unbelegte Zahl ist wie ein Preisschild ohne Ware.",
            target_claim="Deutschland hatte 2025 genau 8 Prozent Inflation.",
            confidence="low",
            needs_research=True,
            research_query="Deutschland Inflationsrate 2025 Destatis",
        )
        agent = ObjectionHandlerAgent()

        with patch(
            "app.services.agents.objection_handler.generate_json",
            new=AsyncMock(
                return_value=ObjectionHandlerOutput(
                    recommendation=recommendation, items=[]
                )
            ),
        ):
            await agent.run_cycle("[S1]: 2025 waren es genau 8 Prozent.", [], SPEAKERS)

        self.assertTrue(agent.latest_recommendation.needs_research)
        self.assertEqual(
            "Deutschland Inflationsrate 2025 Destatis",
            agent.latest_recommendation.research_query,
        )
        self.assertNotIn("Alex", agent.latest_recommendation.research_query)

    async def test_research_refinement_uses_claim_linked_sources(self):
        agent = ObjectionHandlerAgent()
        original = DebateRecommendation(
            answer_now="Die Zahl ist noch unbestaetigt.",
            counterargument="Ohne Quelle ist sie kein belastbarer Beleg.",
            counter_question="Welche Erhebung ist gemeint?",
            primary_move="question",
            question_status="partial",
            open_question="Welche Erhebung belegt die genannte Zahl?",
            follow_ups=[
                {
                    "condition": "Wenn keine Erhebung genannt wird",
                    "question": "Warum sollte die Zahl dann belastbar sein?",
                }
            ],
            analogy="Eine unbelegte Zahl ist wie ein Preisschild ohne Ware.",
            target_claim="Die Inflation lag 2025 bei acht Prozent.",
            confidence="low",
            needs_research=True,
            research_query="Deutschland Inflationsrate 2025 Destatis",
        )
        source = DebateSource(
            title="Inflationsrate 2025",
            url="https://example.test/inflation",
            snippet="Die amtliche Rate betrug 2,2 Prozent.",
            passage="Die amtliche Rate betrug 2,2 Prozent.",
            provider="test",
            claim=original.target_claim,
            verification_status="read",
        )
        refined = DebateRecommendation(
            answer_now="Die amtliche Rate lag laut Quelle bei 2,2 Prozent.",
            counterargument="Acht Prozent widersprechen der amtlichen Erhebung.",
            counter_question="Welche andere belastbare Quelle stuetzt acht Prozent?",
            analogy="Acht Prozent zu behaupten ist hier wie acht Meter zu schaetzen, obwohl ein geeichtes Massband 2,2 zeigt.",
            target_claim=original.target_claim,
            confidence="high",
        )
        generate = AsyncMock(return_value=refined)

        with patch("app.services.agents.objection_handler.generate_json", new=generate):
            result = await agent.refine_with_sources(original, [source])

        self.assertIn("2,2 Prozent", result.answer_now)
        self.assertEqual("completed", result.research_status)
        self.assertEqual([source], result.sources)
        self.assertFalse(result.needs_research)
        self.assertEqual("question", result.primary_move)
        self.assertEqual("partial", result.question_status)
        self.assertEqual(original.open_question, result.open_question)
        self.assertEqual(original.follow_ups, result.follow_ups)
        self.assertIn(source.url, generate.await_args.args[1])
        self.assertIn("amtliche Statistiken", generate.await_args.args[1])
        self.assertIn("direkt in answer_now oder counterargument", generate.await_args.args[1])
        self.assertIn("Zeitraum", generate.await_args.args[1])
        self.assertIn("1-3", generate.await_args.args[1])
        self.assertIn("quellengetragene Gegenargumente", generate.await_args.args[1])
        self.assertEqual("debate_copilot", generate.await_args.kwargs["source"])


class DebateOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    def test_live_overlay_snapshot_reuses_running_recommendation(self):
        session_id = uuid.uuid4()
        orchestrator = object.__new__(AgentOrchestrator)
        orchestrator.session_id = session_id
        orchestrator._stopped = False
        orchestrator.objection_agent = MagicMock()
        orchestrator.objection_agent.latest_recommendation = DebateRecommendation(
            claim_id="claim-1",
            target_claim="Regeln zerstoeren immer die Freiheit.",
            answer_now="Gleiche Freiheit braucht Grenzen gegen die Macht Staerkerer.",
            counter_question="Wie schuetzt Regellosigkeit die Freiheit der Schwaecheren?",
        )
        with patch(
            "app.services.agents.orchestrator._live_orchestrators",
            {session_id: orchestrator},
        ):
            snapshot = live_debate_snapshot()

        self.assertTrue(snapshot["active"])
        self.assertEqual(str(session_id), snapshot["session_id"])
        self.assertEqual("claim-1", snapshot["recommendation"]["claim_id"])

    def _orchestrator(self, agent) -> AgentOrchestrator:
        orchestrator = object.__new__(AgentOrchestrator)
        orchestrator.session_id = uuid.uuid4()
        orchestrator.websocket = MagicMock(send_json=AsyncMock())
        orchestrator.directives = []
        orchestrator.speakers = SPEAKERS
        orchestrator.local_only = False
        orchestrator.transcript_buffer = TranscriptBuffer()
        orchestrator.objection_agent = agent
        orchestrator.activity = MagicMock(
            cycle_started=AsyncMock(),
            cycle_finished=AsyncMock(),
            cycle_error=AsyncMock(),
        )
        orchestrator._event_bus = MagicMock()
        orchestrator._save_and_send_insight = AsyncMock(return_value=True)
        orchestrator._get_model = lambda slug: "qwen3:4b"
        orchestrator._is_enabled = lambda slug, fallback=True: slug == "objection_handler"
        orchestrator._stopped = False
        orchestrator._objection_task = None
        orchestrator._debate_pending = False
        orchestrator._interim_debate_chunks = deque(maxlen=3)
        orchestrator._interim_debate_hypotheses = {}
        orchestrator._active_utterance_id = None
        orchestrator._active_claim_id = None
        orchestrator._transcript_revision = 0
        orchestrator._recommendation_revision = 0
        orchestrator._debate_revision = 0
        orchestrator._research_tasks = set()
        orchestrator._research_cache = {}
        orchestrator._last_research_at = 0.0
        orchestrator._debate_diagnostics = []
        orchestrator.debate_settings = DebateSettings(
            research_enabled=True, research_frequency="often"
        )
        return orchestrator

    async def test_learning_rechecks_current_retention_policy_before_commit(self):
        agent = MagicMock()
        agent.latest_recommendation = DebateRecommendation(
            claim_id="claim-1",
            recommendation_revision=7,
            target_claim="Die konkrete Behauptung.",
            answer_now="Die knappe Antwort.",
        )
        orchestrator = self._orchestrator(agent)
        orchestrator.meeting_context = "Privater Kontext"
        orchestrator._good_answer_examples = []
        orchestrator._semantic_memory_tasks = set()
        orchestrator._semantic_argument_memory = None

        db = SimpleNamespace(commit=AsyncMock())

        class SessionContext:
            async def __aenter__(self):
                return db

            async def __aexit__(self, *_args):
                return False

        current = DebateSettings(
            transcript_retention_enabled=False,
            learning_examples_enabled=False,
        )
        save = AsyncMock(return_value=SimpleNamespace(
            id="example-1", claim="claim", answer="answer",
            counterargument="", mode="", style_focus="",
        ))
        with (
            patch("app.services.agents.orchestrator.async_session", return_value=SessionContext()),
            patch("app.services.debate_settings.get_debate_settings", AsyncMock(return_value=current)) as policy,
            patch("app.services.agents.orchestrator.save_good_debate_example", save),
        ):
            result = await orchestrator.confirm_good_debate_answer(
                claim_id="claim-1",
                recommendation_revision=7,
            )

        self.assertFalse(result)
        policy.assert_awaited_once_with(db)
        save.assert_not_awaited()
        db.commit.assert_not_awaited()

    @staticmethod
    def _enable_external_analyst(orchestrator, model_id="gemini-3.1-pro"):
        orchestrator._get_model = lambda slug: (
            model_id if slug == "consolidated_analyst" else "qwen3:4b"
        )
        orchestrator._is_enabled = lambda slug, fallback=True: slug in {
            "objection_handler", "consolidated_analyst"
        }
        orchestrator._privacy_admits = lambda _model_id: True
        orchestrator.meeting_context = ""
        orchestrator._argument_memory = deque(maxlen=16)

    def test_external_analyst_priority_uses_only_enabled_routes_in_saved_order(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator._privacy_admits = lambda _model_id: True
        orchestrator._external_model_unavailable_until = {}
        orchestrator._is_enabled = lambda _slug, _fallback=False: False

        with (
            patch.dict(
                "app.services.agents.orchestrator.os.environ",
                {
                    "BACKCHANNEL_SUBSCRIPTION_BRIDGE_URL": "http://127.0.0.1:8317/v1",
                    "BACKCHANNEL_SUBSCRIPTION_BRIDGE_KEY": "local-key",
                    "BACKCHANNEL_SUBSCRIPTION_MODELS": (
                        '["gpt-6-sol","gpt-6.1-sol","gemini-3.1-pro-high",'
                        '"gemini-3.1-pro-preview","gemini-3.8-flash-high"]'
                    ),
                },
            ),
            patch(
                "app.services.subscription_bridge.gemini_web_cookie_configured",
                return_value=True,
            ),
            patch(
                "app.services.subscription_bridge.gemini_web_models",
                return_value=["gemini-3.1-pro"],
            ),
            patch(
                "app.services.chatgpt_web.runtime_available",
                return_value=True,
            ),
            patch(
                "app.services.chatgpt_web.configured",
                return_value=True,
            ),
        ):
            candidates = orchestrator._external_analysis_models()

        self.assertEqual(
            [
                "chatgpt-web:gpt-6",
                "endpoint:gemini-web:gemini-3.1-pro",
                "endpoint:subscription-ai:gpt-6-sol",
                "endpoint:subscription-ai:gemini-3.1-pro-preview",
            ],
            candidates,
        )

    async def test_background_analyst_runs_for_logic_without_web_search(self):
        agent = MagicMock(
            analyze_deep=AsyncMock(return_value=(
                DeepDebateAnalysis(
                    best_reply="Aus dem Wert Freiheit folgt nicht, dass jede Regel falsch ist.",
                    counterarguments=["Die Schlussfolgerung setzt Freiheit mit Regellosigkeit gleich."],
                    rebuttal="Gleiche Regeln koennen die Freiheit aller erst absichern.",
                    interpretation="Versteckte Praemisse: Jede Begrenzung vernichtet Freiheit.",
                    followups=["Welche Freiheit haben Schwaechere ohne gemeinsame Regeln?"],
                ),
                "kompakter Analyseauftrag",
            )),
            latest_recommendation=DebateRecommendation(),
            last_outcome={"kind": "no_findings", "items": 0},
        )
        orchestrator = self._orchestrator(agent)
        orchestrator._get_model = lambda slug: (
            "gemini-3.1-pro" if slug == "consolidated_analyst" else "qwen3:4b"
        )
        orchestrator._is_enabled = lambda slug, fallback=True: slug in {
            "objection_handler", "consolidated_analyst"
        }
        orchestrator._privacy_admits = lambda model_id: True
        orchestrator.meeting_context = "Freiheit braucht faire gemeinsame Regeln."
        orchestrator._argument_memory = deque(maxlen=16)
        recommendation = DebateRecommendation(
            answer_now="Freiheit ist nicht dasselbe wie Regellosigkeit.",
            counter_question="Warum soll jede Regel Freiheit zerstoeren?",
            target_claim="Wenn Freiheit wichtig ist, darf es keinerlei Regeln geben.",
            confidence="medium",
        )

        with patch(
            "app.services.agents.orchestrator.research_claim",
            new=AsyncMock(),
        ) as research:
            task = orchestrator._maybe_schedule_research(0, recommendation)
            self.assertIsNotNone(task)
            task.set_name("debate-test-deep-logic")
            await asyncio.wait_for(task, 0.5)

        research.assert_not_awaited()
        agent.analyze_deep.assert_awaited_once()
        self.assertEqual(
            "gemini-3.1-pro",
            agent.analyze_deep.await_args.kwargs["model_id"],
        )
        update = orchestrator.websocket.send_json.await_args.args[0]["data"]
        self.assertEqual("research", update["origin"])
        self.assertEqual("Google", update["analyst_provider"])
        self.assertIn("Schwaechere", update["counter_question"])

    async def test_final_negation_replaces_interim_for_same_utterance(self):
        class Agent:
            latest_recommendation = DebateRecommendation()
            last_outcome = {"kind": "no_findings", "items": 0}

            def __init__(self):
                self.windows = []

            async def run_cycle(self, **kwargs):
                self.windows.append(kwargs["transcript_window"])
                return []

        agent = Agent()
        orchestrator = self._orchestrator(agent)
        await orchestrator.feed_interim_transcript(
            "Das kann funktionieren.", utterance_id="utt-1"
        )
        first = orchestrator._objection_task
        first.set_name("debate-test-interim-replacement")
        await asyncio.wait_for(first, 0.5)

        await orchestrator.feed_transcript(
            "Das kann nicht funktionieren.", "Alex", utterance_id="utt-1"
        )
        second = orchestrator._objection_task
        second.set_name("debate-test-final-replacement")
        await asyncio.wait_for(second, 0.5)

        self.assertIn("kann nicht", agent.windows[-1])
        self.assertNotIn("Das kann funktionieren", agent.windows[-1])

    async def test_manual_correction_invalidates_matching_live_recommendation(self):
        agent = MagicMock()
        agent.latest_recommendation = DebateRecommendation(
            answer_now="Die alte Empfehlung.",
            counterargument="Der alte Einwand.",
            target_claim="Fuenfzig Prozent.",
            claim_id="utt-1",
            utterance_id="utt-1",
            transcript_revision=1,
            claim_revision=1,
        )
        orchestrator = self._orchestrator(agent)
        orchestrator._active_claim_id = "utt-1"
        orchestrator._active_utterance_id = "utt-1"
        orchestrator._transcript_revision = 1
        orchestrator._send_debate_update = AsyncMock()
        orchestrator._schedule_debate_revision = MagicMock()
        await orchestrator.transcript_buffer.add(
            "Fuenfzig Prozent.", "Alex", utterance_id="utt-1"
        )

        changed = await orchestrator.apply_manual_transcript_correction(
            text="Fuenfzehn Prozent.",
            speaker_name="Alex",
            speaker_id="speaker-1",
            speaker_type="external",
            utterance_id="utt-1",
        )

        self.assertTrue(changed)
        self.assertEqual(2, orchestrator._transcript_revision)
        self.assertEqual(
            "Fuenfzehn Prozent.",
            orchestrator.transcript_buffer._segments[-1]["text"],
        )
        invalidated = orchestrator._send_debate_update.await_args.args[1]
        self.assertEqual("Fuenfzehn Prozent.", invalidated.target_claim)
        self.assertEqual("", invalidated.counterargument)
        self.assertIn("neu geprueft", invalidated.answer_now)
        self.assertEqual(2, invalidated.transcript_revision)
        orchestrator._schedule_debate_revision.assert_called_once_with()

    async def test_gateway_preserves_provider_segment_identity_and_zero_audio_origin(self):
        orchestrator = self._orchestrator(MagicMock())

        class Gateway:
            async def receive_responses(self):
                yield {
                    "type": "transcript",
                    "data": "Lokaler Entwurf.",
                    "mode": "replace",
                    "segment_id": "local-segment-1",
                    "segment_revision": 2,
                    "track_id": "mixed",
                    "audio_start_sample": 0,
                    "audio_end_sample": 320,
                }

        orchestrator.audio_gateway = Gateway()
        orchestrator._gateway_segment_id = "gateway-segment-1"
        orchestrator._gateway_segment_revision = 0
        orchestrator._gateway_segment_start_sample = 999
        orchestrator._gateway_samples_sent = 640
        orchestrator._finalized_interim_segments = set()
        orchestrator.feed_interim_transcript = AsyncMock()

        await orchestrator._handle_gateway_responses()

        payload = orchestrator.websocket.send_json.await_args.args[0]["data"]
        self.assertEqual("local-segment-1", payload["segment_id"])
        self.assertEqual(0, payload["audio_start_sample"])
        self.assertEqual(320, payload["audio_end_sample"])
        self.assertEqual("local-segment-1", orchestrator._active_interim_segment_id)

    async def test_directive_during_pause_schedules_a_new_revision(self):
        class Agent:
            latest_recommendation = DebateRecommendation()
            last_outcome = {"kind": "no_findings", "items": 0}

            async def run_cycle(self, **kwargs):
                return []

        orchestrator = self._orchestrator(Agent())
        await orchestrator.transcript_buffer.add("Ein vorhandener Streitpunkt", "Alex")

        accepted = await orchestrator.send_directive("Debate AI, wiederhole meine Frage")

        self.assertTrue(accepted)
        self.assertIsNotNone(orchestrator._objection_task)
        orchestrator._objection_task.set_name("debate-test-directive")
        await asyncio.wait_for(orchestrator._objection_task, 0.5)

    async def test_spoken_team_research_directive_is_an_event_not_transcript(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator.update_debate_research = AsyncMock()

        accepted = await orchestrator.feed_transcript(
            "Debate AI, Recherche aus",
            "Ich",
            speaker_type="team",
            is_local_mic=True,
        )

        self.assertTrue(accepted)
        orchestrator.update_debate_research.assert_awaited_once_with(False)
        self.assertEqual(0, len(orchestrator.transcript_buffer._segments))

    async def test_spoken_team_playbook_is_an_event_not_transcript(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator._schedule_debate_revision = MagicMock()

        accepted = await orchestrator.feed_transcript(
            "Debate AI, Zeile für Zeile",
            "Ich",
            speaker_type="team",
            is_local_mic=True,
        )

        self.assertTrue(accepted)
        self.assertEqual(0, len(orchestrator.transcript_buffer._segments))
        self.assertTrue(orchestrator.directives[-1].startswith("[PLAYBOOK]"))
        self.assertIn("zeile für zeile", orchestrator.directives[-1].casefold())
        orchestrator._schedule_debate_revision.assert_called_once_with()

    async def test_spoken_local_command_respects_disabled_voice_commands(self):
        agent = MagicMock(
            run_cycle=AsyncMock(return_value=[]),
            latest_recommendation=DebateRecommendation(),
            last_outcome={"kind": "no_findings", "items": 0},
        )
        orchestrator = self._orchestrator(agent)
        orchestrator.debate_settings = DebateSettings(voice_commands_enabled=False)
        orchestrator.update_debate_research = AsyncMock()

        accepted = await orchestrator.feed_transcript(
            "Debate AI, Recherche aus",
            "Ich",
            speaker_type="team",
            is_local_mic=True,
        )

        self.assertFalse(accepted)
        orchestrator.update_debate_research.assert_not_awaited()
        self.assertEqual(1, len(orchestrator.transcript_buffer._segments))
        if orchestrator._objection_task is not None:
            orchestrator._objection_task.set_name("debate-test-disabled-voice-command")
            await asyncio.wait_for(orchestrator._objection_task, 0.5)

    async def test_text_command_can_force_extra_high_for_next_deep_analysis(self):
        orchestrator = self._orchestrator(MagicMock())

        accepted = await orchestrator.send_directive("Debate AI, Extra High analysieren")

        self.assertTrue(accepted)
        self.assertTrue(orchestrator._force_deep_analysis_once)

    async def test_text_command_changes_the_live_debate_mode(self):
        agent = MagicMock()
        orchestrator = self._orchestrator(agent)

        accepted = await orchestrator.send_directive("Debate AI, Modus hart")

        self.assertTrue(accepted)
        agent.update_debate_mode.assert_called_once_with("forceful")

    async def test_external_speaker_cannot_trigger_spoken_directive(self):
        agent = MagicMock(
            run_cycle=AsyncMock(return_value=[]),
            latest_recommendation=DebateRecommendation(),
            last_outcome={"kind": "no_findings", "items": 0},
        )
        orchestrator = self._orchestrator(agent)
        orchestrator.update_debate_research = AsyncMock()

        await orchestrator.feed_transcript(
            "Debate AI, Recherche aus",
            "Gegenseite",
            speaker_type="external",
        )

        orchestrator.update_debate_research.assert_not_awaited()
        self.assertEqual(1, len(orchestrator.transcript_buffer._segments))
        if orchestrator._objection_task is not None:
            orchestrator._objection_task.set_name("debate-test-external-directive")
            await asyncio.wait_for(orchestrator._objection_task, 0.5)

    async def test_spoken_team_command_from_system_audio_is_not_executed(self):
        agent = MagicMock(
            run_cycle=AsyncMock(return_value=[]),
            latest_recommendation=DebateRecommendation(),
            last_outcome={"kind": "no_findings", "items": 0},
        )
        orchestrator = self._orchestrator(agent)
        orchestrator.update_debate_research = AsyncMock()

        await orchestrator.feed_transcript(
            "Debate AI, Recherche aus",
            "Interner Teilnehmer",
            speaker_type="team",
            is_local_mic=False,
        )

        orchestrator.update_debate_research.assert_not_awaited()
        self.assertEqual(1, len(orchestrator.transcript_buffer._segments))
        if orchestrator._objection_task is not None:
            orchestrator._objection_task.set_name("debate-test-system-directive")
            await asyncio.wait_for(orchestrator._objection_task, 0.5)

    async def asyncTearDown(self):
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task() and task.get_name().startswith("debate-test-"):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def test_source_enriched_update_merges_into_measured_diagnostic_revision(self):
        orchestrator = self._orchestrator(MagicMock())
        draft = DebateRecommendation(
            answer_now="Die Zahl ist noch unbelegt.",
            counterargument="Ohne Quelle traegt sie den Schluss nicht.",
            counter_question="Welche Quelle belegt die Zahl?",
            analogy="Wie ein Preisschild ohne Ware.",
            target_claim="Die Quote liegt bei acht Prozent.",
            argument_points=["Die acht Prozent brauchen eine Grundgesamtheit."],
            confidence="low",
        )
        await orchestrator._send_debate_update(7, draft, latency_ms=42)

        researched = draft.model_copy(
            update={
                "answer_now": "Die amtliche Reihe liegt bei 2,2 statt acht Prozent.",
                "counterargument": "Die genannte Zahl widerspricht der Primaerquelle.",
                "argument_points": ["Amtlich: 2,2 Prozent", "Behauptet: acht Prozent"],
                "confidence": "high",
                "research_status": "completed",
                "research_alert": "Gegenbeleg gefunden.",
                "sources": [DebateSource(
                    title="Amtliche Reihe",
                    url="https://example.test/rate",
                    snippet="Die Rate lag bei 2,2 Prozent.",
                    provider="test",
                    claim="Die Quote liegt bei acht Prozent.",
                )],
            }
        )
        await orchestrator._send_debate_update(7, researched)

        self.assertEqual(1, len(orchestrator._debate_diagnostics))
        sample = orchestrator._debate_diagnostics[0]
        self.assertEqual(42, sample["latency_ms"])
        self.assertEqual(researched.answer_now, sample["answer_now"])
        self.assertEqual("completed", sample["research_status"])
        self.assertEqual("high", sample["confidence"])
        self.assertEqual(researched.argument_points, sample["argument_points"])
        self.assertEqual("https://example.test/rate", sample["sources"][0]["url"])

    async def test_older_topic_knowledge_cannot_replace_corrected_revision(self):
        orchestrator = self._orchestrator(MagicMock())
        recommendation = DebateRecommendation(target_claim="Korrigierter Claim")
        newer = SimpleNamespace(claim_id="claim-1", claim_revision=4)
        older = SimpleNamespace(claim_id="claim-1", claim_revision=3)

        orchestrator._remember_topic_knowledge(
            newer,
            recommendation,
            [DebateSource(title="Neu", claim="Korrigierter Claim")],
        )
        orchestrator._remember_topic_knowledge(
            older,
            recommendation.model_copy(update={"target_claim": "Alter Claim"}),
            [DebateSource(title="Alt", claim="Alter Claim")],
        )

        stored = orchestrator._topic_knowledge["claim-1"]
        self.assertEqual(4, stored["claim_revision"])
        self.assertEqual("Korrigierter Claim", stored["target_claim"])
        self.assertEqual("Neu", stored["sources"][0]["title"])

    async def test_server_rejects_explicitly_stale_live_update(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator._active_claim_id = "claim-1"
        orchestrator._transcript_revision = 4

        await orchestrator._send_debate_update(
            3,
            DebateRecommendation(
                claim_id="claim-1",
                transcript_revision=3,
                claim_revision=3,
                answer_now="Veraltete Antwort",
            ),
        )

        orchestrator.websocket.send_json.assert_not_awaited()
        self.assertEqual(0, orchestrator._recommendation_revision)

    async def test_model_update_gets_a_newer_visible_revision_than_instant_card(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator._active_claim_id = "claim-1"
        orchestrator._active_utterance_id = "utt-1"
        orchestrator._transcript_revision = 4
        instant = DebateRecommendation(
            answer_now="Vorlaeufige Antwort.",
            counterargument="Vorlaeufiger Einwand.",
            counter_question="Welcher Beleg fehlt?",
            analogy="Wie ein Entwurf.",
            provisional=True,
        )
        model = instant.model_copy(
            update={"answer_now": "Praezise Modellantwort.", "provisional": False}
        )

        await orchestrator._send_debate_update(4, instant, origin="instant")
        await orchestrator._send_debate_update(4, model, origin="model")

        first, second = [
            call.args[0]["data"]
            for call in orchestrator.websocket.send_json.await_args_list
        ]
        self.assertLess(first["recommendation_revision"], second["recommendation_revision"])
        self.assertEqual(first["claim_id"], second["claim_id"])
        self.assertTrue(first["provisional"])
        self.assertFalse(second["provisional"])
        self.assertEqual("model", second["origin"])
        self.assertEqual(
            second["recommendation_revision"],
            orchestrator.objection_agent.latest_recommendation.recommendation_revision,
        )

    async def test_ui_ack_marks_the_exact_visible_card(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator._active_claim_id = "claim-1"
        await orchestrator._send_debate_update(
            2,
            DebateRecommendation(
                answer_now="Antwort.",
                counterargument="Einwand.",
                counter_question="Warum?",
                analogy="Wie ein Test.",
            ),
            latency_ms=30,
            origin="model",
        )
        visible_revision = orchestrator._recommendation_revision

        accepted = orchestrator.acknowledge_debate_update(
            claim_id="claim-1",
            recommendation_revision=visible_revision,
        )

        self.assertTrue(accepted)
        self.assertTrue(orchestrator._debate_diagnostics[-1]["ui_acknowledged"])

    async def test_new_speech_cancels_stale_revision_and_runs_latest(self):
        class BlockingAgent:
            def __init__(self):
                self.started = asyncio.Event()
                self.release = asyncio.Event()
                self.calls = 0
                self.latest_recommendation = DebateRecommendation()
                self.last_outcome = None

            async def run_cycle(self, **kwargs):
                self.calls += 1
                self.started.set()
                await self.release.wait()
                return []

        agent = BlockingAgent()
        orchestrator = self._orchestrator(agent)

        await asyncio.wait_for(orchestrator.feed_transcript("Erster Punkt", "Alex"), 0.1)
        first = orchestrator._objection_task
        first.set_name("debate-test-first")
        await agent.started.wait()
        await asyncio.wait_for(orchestrator.feed_transcript("Neuer Punkt", "Alex"), 0.1)
        await asyncio.sleep(0)

        self.assertTrue(first.cancelled())
        second = orchestrator._objection_task
        self.assertIsNot(first, second)
        self.assertEqual(2, orchestrator._debate_revision)
        self.assertFalse(orchestrator._debate_pending)

        agent.release.set()
        await asyncio.wait_for(second, 0.5)

        self.assertEqual(2, orchestrator._debate_revision)
        self.assertEqual(2, agent.calls)

    async def test_final_negation_drops_slow_model_result_for_interim_claim(self):
        class SlowAgent:
            def __init__(self):
                self.started = asyncio.Event()
                self.release = asyncio.Event()
                self.calls = 0
                self.latest_recommendation = DebateRecommendation()
                self.last_outcome = {"kind": "no_findings", "items": 0}

            async def run_cycle(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    self.started.set()
                    await self.release.wait()
                    self.latest_recommendation = DebateRecommendation(
                        answer_now="Es kann funktionieren.",
                        counterargument="Die Aussage ist positiv.",
                        counter_question="Warum sollte es funktionieren?",
                        analogy="Wie ein Test mit offenem Ergebnis.",
                        target_claim="Es kann funktionieren.",
                    )
                else:
                    self.latest_recommendation = DebateRecommendation(
                        answer_now="Es kann gerade nicht funktionieren.",
                        counterargument="Die Verneinung aendert den Schluss.",
                        counter_question="Welche Voraussetzung fehlt?",
                        analogy="Wie ein Schalter, der jetzt auf Aus steht.",
                        target_claim="Es kann nicht funktionieren.",
                    )
                return []

        agent = SlowAgent()
        orchestrator = self._orchestrator(agent)
        await orchestrator.feed_interim_transcript(
            "Es kann funktionieren.", utterance_id="utt-negation"
        )
        worker = orchestrator._objection_task
        worker.set_name("debate-test-negation-stale-guard")
        await agent.started.wait()

        await orchestrator.feed_transcript(
            "Es kann nicht funktionieren.",
            "Alex",
            utterance_id="utt-negation",
        )
        latest_worker = orchestrator._objection_task
        self.assertIsNot(worker, latest_worker)
        agent.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(worker, 0.5)
        await asyncio.wait_for(latest_worker, 0.5)

        model_updates = [
            call.args[0]["data"]
            for call in orchestrator.websocket.send_json.await_args_list
            if call.args[0].get("type") == "debate_update"
            and call.args[0]["data"].get("origin") == "model"
        ]
        self.assertEqual(1, len(model_updates))
        self.assertIn("nicht funktionieren", model_updates[0]["answer_now"])
        self.assertEqual(orchestrator._transcript_revision, model_updates[0]["transcript_revision"])

    async def test_streamed_model_sentence_is_broadcast_before_full_model_finishes(self):
        class SlowAgent:
            def __init__(self):
                self.started = asyncio.Event()
                self.release = asyncio.Event()
                self.latest_recommendation = DebateRecommendation()
                self.last_outcome = None

            async def run_cycle(self, **kwargs):
                self.started.set()
                await kwargs["on_model_partial"](DebateRecommendation(
                    answer_now="Das widerlegt meine Position noch nicht.",
                    target_claim="Die Position sei widerlegt.",
                    provisional=True,
                ))
                await self.release.wait()
                return []

        agent = SlowAgent()
        orchestrator = self._orchestrator(agent)
        await orchestrator.transcript_buffer.add("Das ist komplett widerlegt.", "Alex")
        orchestrator._debate_revision = 1

        task = asyncio.create_task(orchestrator._run_debate_revision(1))
        await asyncio.wait_for(agent.started.wait(), 0.2)

        orchestrator.websocket.send_json.assert_awaited()
        first = orchestrator.websocket.send_json.await_args_list[0].args[0]["data"]
        self.assertIn("noch nicht", first["answer_now"])
        self.assertEqual("model_stream", first["origin"])
        self.assertLessEqual(first["latency_ms"], 3000)

        agent.release.set()
        await asyncio.wait_for(task, 0.5)

    async def test_template_guidance_is_never_published_as_a_model_answer(self):
        class SlowFailingAgent:
            def __init__(self):
                self.started = asyncio.Event()
                self.release = asyncio.Event()
                self.latest_recommendation = DebateRecommendation()
                self.last_outcome = {
                    "kind": "error",
                    "error": {"kind": "truncated", "detail": "output limit"},
                }

            def instant_recommendation(self, transcript_window):
                return DebateRecommendation(
                    answer_now="Eine genaue Zahl braucht zuerst eine belastbare Quelle.",
                    counterargument="Ohne Zeitraum und Grundgesamtheit ist sie nicht aussagekraeftig.",
                    counter_question="Welche Erhebung belegt diese Zahl?",
                    analogy="Eine Zahl ohne Bezug ist ein Preisschild ohne Ware.",
                    target_claim="Neunzig Prozent stimmen zu.",
                    provisional=True,
                )

            async def run_cycle(self, **kwargs):
                self.started.set()
                await self.release.wait()
                self.latest_recommendation = DebateRecommendation()
                return []

        agent = SlowFailingAgent()
        orchestrator = self._orchestrator(agent)
        await orchestrator.transcript_buffer.add(
            "Neunzig Prozent stimmen zu.", "Alex"
        )
        orchestrator._debate_revision = 1

        task = asyncio.create_task(orchestrator._run_debate_revision(1))
        await asyncio.wait_for(agent.started.wait(), 0.2)

        orchestrator.websocket.send_json.assert_not_awaited()

        agent.release.set()
        await asyncio.wait_for(task, 0.5)
        orchestrator.websocket.send_json.assert_not_awaited()

    async def test_new_speech_is_coalesced_while_streamed_model_answer_remains_visible(self):
        class SlowAgent:
            def __init__(self):
                self.started = asyncio.Event()
                self.release = asyncio.Event()
                self.latest_recommendation = DebateRecommendation()
                self.last_outcome = None

            async def run_cycle(self, **kwargs):
                self.started.set()
                await kwargs["on_model_partial"](DebateRecommendation(
                    answer_now="Das widerlegt meine Position noch nicht.",
                    target_claim=kwargs["transcript_window"],
                    provisional=True,
                ))
                await self.release.wait()
                return []

        agent = SlowAgent()
        orchestrator = self._orchestrator(agent)

        await orchestrator.feed_transcript("Erster Einwand", "Alex")
        await asyncio.wait_for(agent.started.wait(), 0.2)
        before = orchestrator.websocket.send_json.await_count

        await asyncio.wait_for(
            orchestrator.feed_interim_transcript(
                "Das ist jetzt ein komplett neuer und relevanter Einwand"
            ),
            0.2,
        )

        self.assertEqual(before, orchestrator.websocket.send_json.await_count)
        visible = orchestrator.websocket.send_json.await_args.args[0]["data"]
        self.assertEqual("model_stream", visible["origin"])

        agent.release.set()
        await asyncio.wait_for(orchestrator._objection_task, 0.5)

    async def test_live_partial_triggers_copilot_without_saving_duplicate_transcript(self):
        class Agent:
            latest_recommendation = DebateRecommendation()
            last_outcome = {"kind": "no_findings", "items": 0}

            def __init__(self):
                self.windows = []

            async def run_cycle(self, **kwargs):
                self.windows.append(kwargs["transcript_window"])
                return []

        agent = Agent()
        orchestrator = self._orchestrator(agent)

        accepted = await orchestrator.feed_interim_transcript(
            "Treibung ist Mord und deshalb immer abzulehnen."
        )
        task = orchestrator._objection_task
        task.set_name("debate-test-interim")
        await asyncio.wait_for(task, 0.5)

        self.assertTrue(accepted)
        self.assertEqual(0, len(orchestrator.transcript_buffer._segments))
        self.assertIn("LIVE-TEILTRANSKRIPT", agent.windows[0])
        self.assertIn("Treibung ist Mord", agent.windows[0])

    async def test_each_meaningful_word_is_considered_for_the_streamed_model_sentence(self):
        class Agent:
            latest_recommendation = DebateRecommendation()
            last_outcome = {"kind": "no_findings", "items": 0}

            async def run_cycle(self, **kwargs):
                await kwargs["on_model_partial"](DebateRecommendation(
                    answer_now="Dann fehlt dir noch der Beleg.",
                    target_claim=kwargs["transcript_window"],
                    provisional=True,
                ))
                return []

        orchestrator = self._orchestrator(Agent())

        accepted = await orchestrator.feed_interim_transcript("Unsinn.")
        self.assertTrue(accepted)
        task = orchestrator._objection_task
        task.set_name("debate-test-short-interim")
        await asyncio.wait_for(task, 0.5)

        payload = orchestrator.websocket.send_json.await_args_list[0].args[0]["data"]
        self.assertIn("Unsinn.", payload["target_claim"])
        self.assertLessEqual(payload["latency_ms"], 3000)

    async def test_background_analysis_is_compacted_into_the_next_deep_revision(self):
        class Agent:
            latest_recommendation = DebateRecommendation()
            last_outcome = {"kind": "no_findings", "items": 0}

            def __init__(self):
                self.support_context = ""

            async def run_cycle(self, **kwargs):
                self.support_context = kwargs["support_context"]
                return []

        agent = Agent()
        orchestrator = self._orchestrator(agent)
        orchestrator._board_stubs = deque(
            [{"item_type": "observation", "text": "Der Gegner wechselt den Massstab."}],
            maxlen=48,
        )
        orchestrator.active_questions = [
            {"id": "q1", "question": "Welcher Beleg traegt die Zahl?", "item_type": "question"}
        ]
        await orchestrator.transcript_buffer.add("Das ist doch eindeutig.", "Alex")
        orchestrator._debate_revision = 1

        await orchestrator._run_debate_revision(1)

        self.assertIn("Gegner wechselt den Massstab", agent.support_context)
        self.assertIn("Welcher Beleg traegt die Zahl", agent.support_context)

    def test_deep_analysis_relations_keep_prior_claim_ids_through_merge(self):
        orchestrator = self._orchestrator(MagicMock())
        original = DebateRecommendation(
            target_claim="Die Massnahme erhoeht die Kosten.",
            answer_now="Dann muessen wir denselben Zeitraum vergleichen.",
        )
        analysis = DeepDebateAnalysis(
            best_reply="Das widerspricht der frueheren Aussage fuer denselben Zeitraum.",
            logical_relations=[
                LogicalRelation(
                    target_claim_id="claim-old",
                    relation="contradicts",
                    confidence=0.88,
                    verified=True,
                )
            ],
        )

        merged = orchestrator._merge_deep_analysis(
            original,
            analysis,
            model_id="endpoint:subscription-ai:gpt-6-sol",
            prompt="kompakt",
            sources=[],
        )

        self.assertEqual("claim-old", merged.logical_relations[0].target_claim_id)
        self.assertEqual("contradicts", merged.logical_relations[0].relation)

    async def test_strategic_signal_becomes_support_context_for_the_debate_engine(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator._board_stubs = deque(maxlen=48)

        await orchestrator._send_signal_insights(
            {
                "created": [
                    {
                        "item_type": "signal",
                        "question": "Jetzt einsteigen: Der Massstab wurde gerade gewechselt.",
                    }
                ],
                "updated": [],
            }
        )

        self.assertEqual(1, len(orchestrator._board_stubs))
        self.assertIn("Jetzt einsteigen", orchestrator._board_stubs[0]["text"])

    async def test_live_research_toggle_changes_only_automatic_research(self):
        agent = MagicMock(latest_recommendation=DebateRecommendation())
        orchestrator = self._orchestrator(agent)

        self.assertTrue(orchestrator.debate_settings.research_enabled)
        await orchestrator.update_debate_research(False)

        self.assertFalse(orchestrator.debate_settings.research_enabled)
        orchestrator.websocket.send_json.assert_awaited()

    async def test_research_revision_keeps_spoken_text_when_not_materially_better(self):
        original = DebateRecommendation(
            answer_now="Die Zahl ist unbelegt.",
            counterargument="Ohne Quelle traegt sie den Schluss nicht.",
            counter_question="Welche Quelle belegt die Zahl?",
            analogy="Das ist wie ein Urteil ohne Akte.",
            target_claim="Die Quote liegt bei acht Prozent.",
            research_query="Quote acht Prozent Quelle",
            needs_research=True,
        )
        unchanged = original.model_copy(update={"research_status": "completed"})
        agent = MagicMock(
            latest_recommendation=original,
            analyze_deep=AsyncMock(return_value=(
                DeepDebateAnalysis(
                    best_reply=unchanged.answer_now,
                    counterarguments=[],
                    rebuttal=unchanged.counterargument,
                    followups=[unchanged.counter_question],
                ),
                "kompakter Analyseauftrag",
            )),
        )
        orchestrator = self._orchestrator(agent)
        self._enable_external_analyst(orchestrator)
        orchestrator._debate_revision = 1
        with patch(
            "app.services.agents.orchestrator.research_claim",
            new=AsyncMock(
                return_value=ResearchResult(
                    claim=original.target_claim,
                    status="completed",
                    query=original.research_query,
                    sources=[ResearchSource(
                        title="Quelle",
                        url="https://example.test",
                        snippet="Text",
                        passage="Text",
                        provider="test",
                        claim=original.target_claim,
                    )],
                )
            ),
        ):
            await orchestrator._run_debate_research(1, original, force_refresh=True)

        sent = orchestrator.websocket.send_json.await_args.args[0]["data"]
        self.assertEqual(original.answer_now, sent["answer_now"])
        self.assertEqual("completed", sent["research_status"])

    async def test_current_revision_broadcasts_guidance_before_saving_objections(self):
        recommendation = DebateRecommendation(
            answer_now="Darauf koennen wir direkt eingehen.",
            counterargument="Die Schlussfolgerung folgt nicht aus der Praemisse.",
            counter_question="Welche Annahme traegt diesen Schluss?",
            analogy="Das ist wie ein Haus ohne tragendes Fundament.",
            target_claim="Das Vorhaben sei wirkungslos.",
            confidence="medium",
        )

        class Agent:
            latest_recommendation = recommendation
            last_outcome = {"kind": "insights", "items": 1}

            async def run_cycle(self, **kwargs):
                return [{"item_type": "objection", "question": "Es wirkt nicht."}]

        orchestrator = self._orchestrator(Agent())
        orchestrator._debate_revision = 1
        await orchestrator.transcript_buffer.add("Das wirkt nicht.", "Alex")

        async def save_after_broadcast(*args, **kwargs):
            orchestrator.websocket.send_json.assert_awaited()
            return True

        orchestrator._save_and_send_insight.side_effect = save_after_broadcast
        await orchestrator._run_debate_revision(1)

        payload = orchestrator.websocket.send_json.await_args_list[0].args[0]
        self.assertEqual("debate_update", payload["type"])
        self.assertEqual(recommendation.answer_now, payload["data"]["answer_now"])
        self.assertGreaterEqual(payload["data"]["latency_ms"], 0)
        self.assertEqual(1, len(orchestrator._debate_diagnostics))
        orchestrator._event_bus.publish.assert_called_once()

    async def test_stale_revision_is_discarded_even_if_model_returns(self):
        class Agent:
            latest_recommendation = DebateRecommendation(answer_now="Zu spaet")
            last_outcome = {"kind": "no_findings", "items": 0}

            def __init__(self, orchestrator):
                self.orchestrator = orchestrator

            async def run_cycle(self, **kwargs):
                self.orchestrator._debate_revision = 2
                return []

        orchestrator = self._orchestrator(None)
        orchestrator.objection_agent = Agent(orchestrator)
        orchestrator._debate_revision = 1
        await orchestrator.transcript_buffer.add("Die alte Behauptung.", "Alex")

        await orchestrator._run_debate_revision(1)

        orchestrator.websocket.send_json.assert_not_awaited()
        orchestrator._save_and_send_insight.assert_not_awaited()

    async def test_failed_guidance_is_not_broadcast_but_objections_are_saved(self):
        class Agent:
            latest_recommendation = DebateRecommendation()
            last_outcome = {"kind": "error", "error": {"message": "empty guidance"}}

            async def run_cycle(self, **kwargs):
                return [{"item_type": "objection", "question": "Zu teuer."}]

        orchestrator = self._orchestrator(Agent())
        orchestrator._debate_revision = 1
        await orchestrator.transcript_buffer.add("Das ist zu teuer.", "Alex")

        await orchestrator._run_debate_revision(1)

        orchestrator.websocket.send_json.assert_not_awaited()
        orchestrator._save_and_send_insight.assert_awaited_once()
        orchestrator.activity.cycle_error.assert_awaited_once()

    async def test_privacy_first_never_schedules_external_research(self):
        orchestrator = self._orchestrator(MagicMock())
        orchestrator.local_only = True
        recommendation = DebateRecommendation(
            needs_research=True,
            research_query="Inflationsrate Deutschland 2025",
            target_claim="Die Rate betrug acht Prozent.",
        )

        task = orchestrator._maybe_schedule_research(1, recommendation)

        self.assertIsNone(task)
        self.assertEqual(set(), orchestrator._research_tasks)

    def test_research_frequency_controls_event_cooldown(self):
        orchestrator = self._orchestrator(MagicMock())
        self._enable_external_analyst(orchestrator)
        orchestrator._debate_revision = 1
        orchestrator._last_research_at = 100.0
        recommendation = DebateRecommendation(
            answer_now="Das pruefen wir.",
            counterargument="Die Zahl ist unbelegt.",
            counter_question="Welche Quelle?",
            analogy="Eine Zahl ohne Quelle ist wie ein Preis ohne Produkt.",
            needs_research=True,
            research_query="Inflationsrate Deutschland 2025",
            target_claim="Die Rate betrug acht Prozent.",
        )

        orchestrator.debate_settings = DebateSettings(
            research_enabled=True, research_frequency="normal"
        )
        with patch("app.services.agents.orchestrator.time.monotonic", return_value=125.0):
            self.assertIsNone(orchestrator._maybe_schedule_research(1, recommendation))

        fake_task = MagicMock()
        def capture_task(coro, **_kwargs):
            coro.close()
            return fake_task

        orchestrator.debate_settings = DebateSettings(
            research_enabled=True, research_frequency="often"
        )
        with (
            patch("app.services.agents.orchestrator.time.monotonic", return_value=125.0),
            patch("app.services.agents.orchestrator.asyncio.create_task", side_effect=capture_task),
        ):
            self.assertIs(fake_task, orchestrator._maybe_schedule_research(1, recommendation))

        self.assertEqual(125.0, orchestrator._last_research_at)

    async def test_stale_research_is_cached_without_broadcast(self):
        class Agent:
            refine_with_sources = AsyncMock()

        orchestrator = self._orchestrator(Agent())
        self._enable_external_analyst(orchestrator)
        orchestrator._debate_revision = 1
        recommendation = DebateRecommendation(
            needs_research=True,
            research_query="Inflationsrate Deutschland 2025",
            target_claim="Die Rate betrug acht Prozent.",
        )
        result = ResearchResult(
            claim=recommendation.target_claim,
            query=recommendation.research_query,
            status="completed",
            sources=[
                ResearchSource(
                    title="Amtliche Rate",
                    url="https://example.test/rate",
                    snippet="2,2 Prozent",
                    passage="Die amtliche Rate lag bei 2,2 Prozent.",
                    provider="test",
                    claim=recommendation.target_claim,
                    verification_status="read",
                )
            ],
        )

        async def research(*args, **kwargs):
            orchestrator._debate_revision = 2
            return result

        with patch("app.services.agents.orchestrator.research_claim", new=research):
            await orchestrator._run_debate_research(1, recommendation)

        self.assertEqual(result, orchestrator._research_cache[recommendation.research_query])
        remembered = orchestrator._topic_knowledge["claim-1"]
        self.assertEqual(0, remembered["claim_revision"])
        self.assertEqual("https://example.test/rate", remembered["sources"][0]["url"])
        orchestrator.objection_agent.refine_with_sources.assert_not_awaited()
        orchestrator.websocket.send_json.assert_not_awaited()

    async def test_plain_paraphrase_does_not_start_another_automatic_deep_analysis(self):
        orchestrator = self._orchestrator(MagicMock())
        self._enable_external_analyst(orchestrator)
        orchestrator._debate_revision = 1
        orchestrator._active_semantic_related_claim_ids = ["claim-earlier"]
        recommendation = DebateRecommendation(
            answer_now="Das ist dieselbe Aussage.",
            counterargument="Kein neuer Sachkern.",
            counter_question="Was ist daran neu?",
            target_claim="Die schon genannte Reform ist weiterhin nicht sinnvoll.",
            needs_research=False,
        )

        self.assertIsNone(orchestrator._maybe_schedule_research(1, recommendation))

    def test_manual_research_queries_send_only_the_target_claim_and_category(self):
        recommendation = DebateRecommendation(
            target_claim="Die zitierte Studie belegt einen Anstieg um acht Prozent.",
            argument_points=["Studie", "Acht Prozent"],
        )

        counter = _manual_research_query(recommendation, "counterevidence")
        translation = _manual_research_query(recommendation, "translation")
        interpretation = _manual_research_query(recommendation, "interpretation")
        everything = _manual_research_query(recommendation, "all")

        self.assertIn(recommendation.target_claim, counter)
        self.assertIn("Widerlegung", counter)
        self.assertIn("Statistik", counter)
        self.assertIn("Zahlen", counter)
        self.assertIn("Originalquelle", translation)
        self.assertIn("Kontext", interpretation)
        self.assertIn("Widerlegung", everything)
        self.assertIn("Originalquelle", everything)
        self.assertNotIn("Studie Acht Prozent", counter)
        self.assertTrue(all(len(query) <= 300 for query in (counter, translation, interpretation, everything)))

    async def test_manual_research_bypasses_cache_and_marks_the_card_searching(self):
        class Agent:
            latest_recommendation = DebateRecommendation(
                answer_now="Das folgt nicht aus der Quelle.",
                counterargument="Die Interpretation ist nicht belegt.",
                counter_question="Wo steht das im Original?",
                analogy="Das ist wie eine Bildunterschrift ohne Bild.",
                target_claim="Die Quelle belegt acht Prozent.",
            )

        orchestrator = self._orchestrator(Agent())
        self._enable_external_analyst(orchestrator)
        orchestrator._debate_revision = 4
        orchestrator._run_debate_research = AsyncMock()

        accepted = await orchestrator.request_debate_research("translation")
        await asyncio.sleep(0)

        self.assertTrue(accepted)
        payload = orchestrator.websocket.send_json.await_args_list[0].args[0]
        self.assertEqual("searching", payload["data"]["research_status"])
        self.assertIn("Originalquelle", payload["data"]["research_query"])
        orchestrator._run_debate_research.assert_awaited_once()
        self.assertTrue(orchestrator._run_debate_research.await_args.kwargs["force_refresh"])

    async def test_manual_deep_analysis_can_be_cancelled_without_stopping_shared_provider(self):
        started = asyncio.Event()
        request_closed = asyncio.Event()

        class Agent:
            latest_recommendation = DebateRecommendation(
                answer_now="Die Schlussfolgerung ist noch nicht belegt.",
                counterargument="Der Beleg fehlt.",
                counter_question="Welche Quelle traegt den Schluss?",
                analogy="Wie ein Urteil ohne Akte.",
                target_claim="Die Quelle beweise den Schluss.",
            )

            async def analyze_deep(self, *args, **kwargs):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    request_closed.set()

        orchestrator = self._orchestrator(Agent())
        self._enable_external_analyst(orchestrator)
        orchestrator._debate_revision = 4
        no_sources = ResearchResult(
            claim="Die Quelle beweise den Schluss.",
            status="completed",
            query="Quelle pruefen",
            sources=[],
        )

        with patch(
            "app.services.agents.orchestrator.research_claim",
            new=AsyncMock(return_value=no_sources),
        ):
            self.assertTrue(await orchestrator.request_debate_research("all"))
            await asyncio.wait_for(started.wait(), 0.5)

            self.assertTrue(await orchestrator.cancel_manual_debate_analysis())
            await asyncio.wait_for(request_closed.wait(), 0.5)

        final_payload = orchestrator.websocket.send_json.await_args_list[-1].args[0]
        self.assertEqual("debate_update", final_payload["type"])
        self.assertEqual("cancelled", final_payload["data"]["analysis_status"])
        self.assertFalse(final_payload["data"]["analysis_can_cancel"])


if __name__ == "__main__":
    unittest.main()
