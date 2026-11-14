import asyncio
import unittest
from unittest import mock

from app.services import debate_research


class DebateResearchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        debate_research._search_cache.clear()
        debate_research._document_cache.clear()
        debate_research._passage_cache.clear()
        debate_research._research_inflight.clear()

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


if __name__ == "__main__":
    unittest.main()
