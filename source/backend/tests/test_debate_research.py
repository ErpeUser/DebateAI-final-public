import asyncio
import unittest

import httpx
from unittest import mock

from app.services import debate_research


class DebateResearchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        debate_research._search_cache.clear()
        debate_research._document_cache.clear()
        debate_research._passage_cache.clear()
        debate_research._research_inflight.clear()
        debate_research._research_provider_cooldown_until.clear()
        debate_research._research_provider_health.clear()

    async def test_identical_live_queries_share_one_inflight_research(self):
        calls = 0

        async def fake_research(client, claim, query):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return debate_research.ResearchResult(
                claim=claim, query=query, status="completed"
            )

        with mock.patch.object(debate_research, "_research_with_client", fake_research):
            first, second = await asyncio.gather(
                debate_research.research_claim("Claim A", "gleiche Suche"),
                debate_research.research_claim("Claim B", "gleiche Suche"),
            )

        self.assertEqual(1, calls)
        self.assertEqual("Claim A", first.claim)
        self.assertEqual("Claim B", second.claim)

    async def test_legacy_providers_are_disabled_even_in_old_configuration(self):
        with mock.patch.object(
            debate_research,
            "research_settings",
            return_value={
                "enabled": True,
                "providers": ["wikipedia", "duckduckgo"],
                "timeout_seconds": 3,
                "steps": 2,
                "original_sources_required": True,
            },
        ):
            with mock.patch.object(debate_research, "_ai_web_sources") as ai_lane:
                result = await debate_research.research_claim(
                    "Eine Behauptung", "diese Behauptung pruefen"
                )
        self.assertEqual("unavailable", result.status)
        self.assertFalse(hasattr(debate_research, "_wikipedia_sources"))
        self.assertFalse(hasattr(debate_research, "_duckduckgo_sources"))
        ai_lane.assert_not_awaited()

    async def test_ai_web_provider_is_the_only_research_path(self):
        source = debate_research.ResearchSource(
            title="Originalquelle",
            url="https://example.org/source",
            snippet="Beleg",
            provider="chatgpt_web",
            claim="Claim",
        )
        with mock.patch.object(
            debate_research,
            "_ai_web_sources",
            return_value=[source],
        ) as ai_lane:
            result = await debate_research.research_claim(
                "Claim", "Claim pruefen", client=mock.AsyncMock()
            )
        self.assertEqual("completed", result.status)
        self.assertEqual("chatgpt_web", result.sources[0].provider)
        ai_lane.assert_awaited_once()

    async def test_trusted_original_is_opened_and_relevant_passage_is_read(self):
        source = debate_research.ResearchSource(
            title="Originalquelle",
            url="https://www.destatis.de/original",
            snippet="Kurzer Fundstellenhinweis",
            provider="chatgpt_web",
            claim="Inflation",
        )
        document = (
            b"<html><body><h1>Inflation</h1>"
            b"<p>Die Verbraucherpreise stiegen im Jahresdurchschnitt um einen "
            b"messbaren Wert und die Entwicklung ist fuer die Einordnung relevant.</p>"
            b"<script>private noise</script></body></html>"
        )
        bounded = mock.AsyncMock(return_value=(document, "text/html"))
        with mock.patch.object(debate_research, "_bounded_get", bounded):
            result = await debate_research._read_trusted_original(
                mock.AsyncMock(), source, "Inflation Verbraucherpreise"
            )

        self.assertEqual("read", result.verification_status)
        self.assertEqual("read", result.retrieval_status)
        self.assertEqual("original", result.source_type)
        self.assertIn("Verbraucherpreise", result.passage)
        self.assertNotIn("private noise", result.passage)
        bounded.assert_awaited_once()
        self.assertEqual(
            debate_research._MAX_ORIGINAL_BYTES,
            bounded.await_args.kwargs["max_bytes"],
        )

    async def test_original_reader_keeps_unreadable_source_unverified(self):
        source = debate_research.ResearchSource(
            title="Quelle",
            url="https://www.destatis.de/original",
            snippet="Treffer",
            provider="chatgpt_web",
            claim="Inflation",
        )
        with mock.patch.object(
            debate_research,
            "_bounded_get",
            side_effect=ValueError("content type not allowed"),
        ) as bounded:
            result = await debate_research._read_trusted_original(
                mock.AsyncMock(), source, "Inflation"
            )

        self.assertEqual("found", result.verification_status)
        self.assertEqual("found", result.retrieval_status)
        self.assertEqual("", result.passage)
        bounded.assert_awaited_once()

    async def test_ai_web_failover_tries_all_enabled_routes(self):
        calls = []

        async def fake_generate_text(model, *_args, **_kwargs):
            calls.append(model)
            if len(calls) == 1:
                raise RuntimeError("Gemini Web unavailable")
            if len(calls) == 2:
                return "https://api.example/gemini https://shared.example/source"
            return "https://cli.example/source"

        with mock.patch.object(
            debate_research,
            "_research_provider_ready",
            return_value=True,
        ), mock.patch(
            "app.services.chatgpt_web.generate",
            new=mock.AsyncMock(side_effect=RuntimeError("ChatGPT Web unavailable")),
        ), mock.patch(
            "app.services.llm.generate_text",
            new=fake_generate_text,
        ):
            sources = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["chatgpt_web", "gemini_web", "gemini_api", "cliproxyapi"],
            )

        self.assertEqual(
            [
                "endpoint:gemini-web:gemini-3.1-pro",
                "gemini-3.1-pro-preview",
                "endpoint:subscription-ai:gpt-6-sol",
            ],
            calls,
        )
        self.assertEqual(
            {"gemini_api", "cliproxyapi"},
            {source.provider for source in sources},
        )
        self.assertEqual(
            {"https://api.example/gemini", "https://shared.example/source", "https://cli.example/source"},
            {source.url for source in sources},
        )

    async def test_ai_web_failover_returns_empty_when_all_enabled_routes_fail(self):
        async def fake_generate_text(*_args, **_kwargs):
            raise RuntimeError("provider unavailable")

        with mock.patch.object(
            debate_research,
            "_research_provider_ready",
            return_value=True,
        ), mock.patch(
            "app.services.chatgpt_web.generate",
            new=mock.AsyncMock(side_effect=RuntimeError("ChatGPT Web unavailable")),
        ), mock.patch(
            "app.services.llm.generate_text",
            new=fake_generate_text,
        ):
            sources = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["chatgpt_web", "gemini_web", "gemini_api", "cliproxyapi"],
            )

        self.assertEqual([], sources)

    def test_empty_and_pii_queries_are_refused(self):
        self.assertFalse(debate_research.is_safe_research_query("   "))
        for token in ("[PERSON_1]", "[EMAIL_2]", "[PHONE_3]", "[ADDRESS_4]"):
            self.assertFalse(
                debate_research.is_safe_research_query(f"Fakten zu {token}")
            )
        self.assertTrue(
            debate_research.is_safe_research_query(
                "Wie hoch war die deutsche Inflation 2025?"
            )
        )

    async def test_unsafe_query_makes_no_external_request(self):
        client = mock.AsyncMock()
        result = await debate_research.research_claim(
            "Die Aussage betrifft eine Person.",
            "Wer ist [PERSON_1]?",
            client=client,
        )
        self.assertEqual("refused", result.status)
        self.assertEqual([], result.sources)
        client.get.assert_not_awaited()

    async def test_cancelled_shared_research_is_cleaned_up(self):
        started = asyncio.Event()
        release = asyncio.Event()

        async def fake_research(client, claim, query):
            started.set()
            await release.wait()
            return debate_research.ResearchResult(
                claim=claim, query=query, status="completed"
            )

        with mock.patch.object(debate_research, "_research_with_client", fake_research):
            waiter = asyncio.create_task(
                debate_research.research_claim("Claim", "abgebrochene Suche")
            )
            await started.wait()
            waiter.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await waiter
            release.set()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        self.assertNotIn("abgebrochene suche", debate_research._research_inflight)

    async def test_live_and_deep_modes_keep_separate_inflight_cache_entries(self):
        modes = []

        async def fake_research(_client, claim, query, *, research_mode):
            modes.append(research_mode)
            return debate_research.ResearchResult(
                claim=claim,
                query=query,
                status="completed",
            )

        with mock.patch.object(debate_research, "_research_with_client", fake_research):
            await debate_research.research_claim(
                "Claim",
                "gleiche Suche",
                research_mode="live",
            )
            await debate_research.research_claim(
                "Claim",
                "gleiche Suche",
                research_mode="deep",
            )

        self.assertEqual(["live", "deep"], modes)

    async def test_live_fact_check_stops_after_first_successful_provider(self):
        calls = []

        async def fake_generate_text(model, *_args, **_kwargs):
            calls.append(model)
            return "https://api.example/live"

        with mock.patch.object(
            debate_research,
            "_research_provider_ready",
            return_value=True,
        ), mock.patch(
            "app.services.llm.generate_text",
            new=fake_generate_text,
        ):
            sources = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["gemini_api", "cliproxyapi"],
                research_mode="live",
            )

        self.assertEqual(["gemini-3.1-pro-preview"], calls)
        self.assertEqual(["https://api.example/live"], [source.url for source in sources])

    async def test_live_fact_check_skips_busy_chatgpt_web_and_uses_fallback(self):
        calls = []

        async def fake_generate_text(model, *_args, **_kwargs):
            calls.append(model)
            return "https://api.example/fallback"

        with mock.patch(
            "app.services.chatgpt_web.runtime_available",
            return_value=True,
        ), mock.patch(
            "app.services.chatgpt_web.configured",
            return_value=True,
        ), mock.patch(
            "app.services.chatgpt_web.model_confirmed",
            return_value=True,
        ), mock.patch(
            "app.services.chatgpt_web.browser_busy",
            return_value=True,
        ), mock.patch(
            "app.services.llm.generate_text",
            new=fake_generate_text,
        ):
            sources = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["chatgpt_web", "gemini_api"],
                research_mode="live",
            )

        self.assertEqual(["gemini-3.1-pro-preview"], calls)
        self.assertEqual(["https://api.example/fallback"], [source.url for source in sources])

    async def test_original_read_budget_is_balanced_across_provider_routes(self):
        providers = ["chatgpt_web", "gemini_web", "gemini_api", "cliproxyapi"]
        candidates = [
            debate_research.ResearchSource(
                title=provider,
                url=f"https://{provider}.example/source",
                snippet="Treffer",
                provider=provider,
                claim="Claim",
                source_type="ai_web",
            )
            for provider in providers
        ]

        async def read(_client, source, _query):
            return source.model_copy(update={
                "verification_status": "read",
                "retrieval_status": "read",
                "passage": "Originalpassage zum Claim.",
                "source_type": "original",
            })

        settings = {
            "enabled": True,
            "providers": providers,
            "fallback_providers": [],
            "timeout_seconds": 3,
            "steps": 2,
            "original_sources_required": True,
        }
        client = httpx.AsyncClient()
        try:
            with mock.patch.object(
                debate_research,
                "research_settings",
                return_value=settings,
            ), mock.patch.object(
                debate_research,
                "_ai_web_sources",
                new=mock.AsyncMock(return_value=candidates),
            ), mock.patch.object(
                debate_research,
                "_read_trusted_original",
                side_effect=read,
            ) as reader:
                result = await debate_research._research_with_client(
                    client,
                    "Claim",
                    "Claim pruefen",
                )
        finally:
            await client.aclose()

        self.assertEqual("completed", result.status)
        self.assertEqual(
            set(providers),
            {call.args[1].provider for call in reader.await_args_list},
        )
        self.assertTrue(all(source.retrieval_status == "read" for source in result.sources))

    async def test_all_unread_ai_sources_remain_unavailable(self):
        source = debate_research.ResearchSource(
            title="Treffer",
            url="https://example.org/source",
            snippet="Snippet",
            provider="gemini_api",
            claim="Claim",
            source_type="ai_web",
        )
        settings = {
            "enabled": True,
            "providers": ["gemini_api"],
            "fallback_providers": [],
            "timeout_seconds": 3,
            "steps": 1,
            "original_sources_required": True,
        }
        client = httpx.AsyncClient()
        try:
            with mock.patch.object(
                debate_research,
                "research_settings",
                return_value=settings,
            ), mock.patch.object(
                debate_research,
                "_ai_web_sources",
                new=mock.AsyncMock(return_value=[source]),
            ), mock.patch.object(
                debate_research,
                "_read_trusted_original",
                new=mock.AsyncMock(return_value=source),
            ):
                result = await debate_research._research_with_client(
                    client,
                    "Claim",
                    "Claim pruefen",
                )
        finally:
            await client.aclose()

        self.assertEqual("unavailable", result.status)
        self.assertEqual("found", result.sources[0].retrieval_status)
        self.assertEqual("", result.sources[0].passage)

    async def test_provider_readiness_skips_unlogged_browser_lanes(self):
        async def fake_generate_text(model, *_args, **_kwargs):
            self.assertEqual("gemini-3.1-pro-preview", model)
            return "https://api.example/research"

        with mock.patch(
            "app.services.chatgpt_web.runtime_available",
            return_value=False,
        ), mock.patch(
            "app.services.subscription_bridge.gemini_web_cookie_configured",
            return_value=False,
        ), mock.patch(
            "app.services.llm.generate_text",
            new=fake_generate_text,
        ):
            sources = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["chatgpt_web", "gemini_web", "gemini_api"],
            )

        self.assertEqual(["https://api.example/research"], [source.url for source in sources])
        health = debate_research.research_provider_health()
        self.assertEqual("blocked", health["chatgpt_web"]["state"])
        self.assertEqual("authentication", health["chatgpt_web"]["failure_kind"])
        self.assertEqual("blocked", health["gemini_web"]["state"])

    async def test_rate_limit_sets_provider_cooldown_and_skips_next_lane(self):
        request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
        error = httpx.HTTPStatusError(
            "rate limited",
            request=request,
            response=httpx.Response(
                429,
                headers={"Retry-After": "120"},
                request=request,
            ),
        )
        with mock.patch(
            "app.services.llm.generate_text",
            new=mock.AsyncMock(side_effect=error),
        ) as generate:
            first = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["gemini_api"],
            )
            second = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["gemini_api"],
            )

        self.assertEqual([], first)
        self.assertEqual([], second)
        generate.assert_awaited_once()
        health = debate_research.research_provider_health()["gemini_api"]
        self.assertEqual("cooldown", health["state"])
        self.assertEqual("rate_limit", health["failure_kind"])
        self.assertEqual(120, health["cooldown_seconds"])

    async def test_authentication_failure_is_classified_and_cooled_down(self):
        with mock.patch(
            "app.services.llm.generate_text",
            new=mock.AsyncMock(side_effect=RuntimeError("not logged in")),
        ) as generate:
            sources = await debate_research._ai_web_sources(
                "Die Aussage",
                "Quelle pruefen",
                ["gemini_api"],
            )

        self.assertEqual([], sources)
        generate.assert_awaited_once()
        health = debate_research.research_provider_health()["gemini_api"]
        self.assertEqual("cooldown", health["state"])
        self.assertEqual("authentication", health["failure_kind"])
        self.assertFalse(health["retryable"])

    async def test_configured_fallbacks_are_added_to_effective_research_order(self):
        settings = {
            "enabled": True,
            "providers": ["chatgpt_web"],
            "fallback_providers": ["cliproxyapi"],
            "timeout_seconds": 3,
            "steps": 2,
            "original_sources_required": False,
        }
        with mock.patch.object(
            debate_research,
            "research_settings",
            return_value=settings,
        ), mock.patch.object(
            debate_research,
            "_ai_web_sources",
            new=mock.AsyncMock(return_value=[]),
        ) as ai_lane:
            result = await debate_research._research_with_client(
                mock.AsyncMock(),
                "Claim",
                "Claim pruefen",
            )

        self.assertEqual("unavailable", result.status)
        self.assertEqual(
            ["chatgpt_web", "cliproxyapi"],
            ai_lane.await_args.args[2],
        )


if __name__ == "__main__":
    unittest.main()
