import asyncio
import unittest
from unittest import mock

import httpx

from app.services import debate_research


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _Client:
    def __init__(self, *, wikipedia=None, duckduckgo=None, failures=None):
        self.wikipedia = wikipedia or {}
        self.duckduckgo = duckduckgo or {}
        self.failures = failures or set()
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        provider = "wikipedia" if "wikipedia.org" in url else "duckduckgo"
        if provider in self.failures:
            raise RuntimeError(f"{provider} unavailable")
        payload = self.wikipedia if provider == "wikipedia" else self.duckduckgo
        return _Response(payload)


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

    async def test_cancelled_only_subscriber_does_not_leave_completed_inflight_entry(self):
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

    async def test_cancelling_one_subscriber_keeps_shared_research_for_the_other(self):
        started = asyncio.Event()
        release = asyncio.Event()

        async def fake_research(client, claim, query):
            started.set()
            await release.wait()
            return debate_research.ResearchResult(
                claim=claim, query=query, status="completed"
            )

        with mock.patch.object(debate_research, "_research_with_client", fake_research):
            cancelled = asyncio.create_task(
                debate_research.research_claim("Claim A", "shared cancellation")
            )
            survivor = asyncio.create_task(
                debate_research.research_claim("Claim B", "shared cancellation")
            )
            await started.wait()
            cancelled.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await cancelled
            release.set()
            result = await survivor

        self.assertEqual("completed", result.status)
        self.assertEqual("Claim B", result.claim)
        self.assertNotIn("shared cancellation", debate_research._research_inflight)

    async def test_transient_failure_is_not_served_from_search_cache(self):
        calls = 0

        async def fake_research(client, claim, query):
            nonlocal calls
            calls += 1
            return debate_research.ResearchResult(
                claim=claim,
                query=query,
                status="unavailable" if calls == 1 else "completed",
                error="temporary" if calls == 1 else "",
            )

        with mock.patch.object(debate_research, "_research_with_client", fake_research):
            first = await debate_research.research_claim("Claim", "retry search")
            second = await debate_research.research_claim("Claim", "retry search")

        self.assertEqual("unavailable", first.status)
        self.assertEqual("completed", second.status)
        self.assertEqual(2, calls)

    def test_cache_set_evicts_the_oldest_entry_at_its_bound(self):
        cache = {}
        with mock.patch.object(debate_research, "_SEARCH_CACHE_MAX_ENTRIES", 2):
            debate_research._cache_set(cache, "first", "a", max_entries=2)
            debate_research._cache_set(cache, "second", "b", max_entries=2)
            debate_research._cache_set(cache, "third", "c", max_entries=2)

        self.assertEqual({"second", "third"}, set(cache))

    async def test_each_redirect_hop_is_validated_before_following(self):
        requests = []

        async def handler(request):
            requests.append(str(request.url))
            if len(requests) == 1:
                return httpx.Response(
                    302,
                    headers={"location": "https://example.net/final"},
                )
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                content=b"verified",
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with mock.patch.object(
                debate_research,
                "_public_url",
                mock.AsyncMock(return_value=True),
            ) as public_url:
                content, _ = await debate_research._bounded_get(
                    client, "https://example.org/start"
                )

        self.assertEqual(b"verified", content)
        self.assertGreaterEqual(public_url.await_count, 2)
        self.assertEqual(2, len(requests))
    def test_html_search_extracts_real_results_and_decodes_redirects(self):
        html = """
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Ffact-check">
          Faktencheck zur Behauptung
        </a>
        <a class="result__snippet">Die Primaerquelle widerspricht der Zahl.</a>
        """

        rows = debate_research._parse_duckduckgo_html(html)

        self.assertEqual(1, len(rows))
        self.assertEqual("Faktencheck zur Behauptung", rows[0]["title"])
        self.assertEqual("https://example.org/fact-check", rows[0]["url"])
        self.assertIn("widerspricht", rows[0]["snippet"])

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
        client = _Client()

        result = await debate_research.research_claim(
            "Die Aussage betrifft eine Person.",
            "Wer ist [PERSON_1]?",
            client=client,
        )

        self.assertEqual("refused", result.status)
        self.assertEqual([], result.sources)
        self.assertEqual([], client.calls)

    async def test_wikimedia_request_identifies_the_project(self):
        class _PolicyClient(_Client):
            async def get(self, url, **kwargs):
                if "wikipedia.org" in url:
                    user_agent = kwargs.get("headers", {}).get("User-Agent", "")
                    if "github.com/talberthoule/backchannel" not in user_agent:
                        return _Response({}, status_code=403)
                return await super().get(url, **kwargs)

        client = _PolicyClient(
            wikipedia={
                "query": {
                    "pages": {
                        "10": {
                            "title": "Bundestag",
                            "fullurl": "https://de.wikipedia.org/wiki/Deutscher_Bundestag",
                            "extract": "Das gesetzgebende Organ des Bundes.",
                        }
                    }
                }
            }
        )

        result = await debate_research.research_claim(
            "Der Bundestag beschliesst Bundesgesetze.",
            "Aufgabe Deutscher Bundestag",
            client=client,
        )

        self.assertEqual("completed", result.status)
        self.assertEqual("wikipedia", result.sources[0].provider)
        self.assertEqual("read", result.sources[0].verification_status)
        self.assertIn("gesetzgebende", result.sources[0].passage)

    async def test_sources_are_normalized_deduplicated_and_capped(self):
        client = _Client(
            wikipedia={
                "query": {
                    "pages": {
                        "10": {
                            "title": "Inflation in Deutschland",
                            "fullurl": "http://de.wikipedia.org/wiki/Inflation#Messung",
                            "extract": "<b>Inflation</b> beschreibt den Preisanstieg.",
                        },
                        "11": {
                            "title": "Verbraucherpreisindex",
                            "fullurl": "https://de.wikipedia.org/wiki/Verbraucherpreisindex",
                            "extract": "Der Index misst Preise &amp; Gewichte.",
                        },
                    }
                }
            },
            duckduckgo={
                "Heading": "Inflation",
                "AbstractText": "Doppelte Quelle",
                "AbstractURL": "https://de.wikipedia.org/wiki/Inflation#Andere",
                "AbstractSource": "Wikipedia",
                "RelatedTopics": [
                    {
                        "Text": "Statistisches Bundesamt zur Inflation",
                        "FirstURL": "https://www.destatis.de/inflation",
                    }
                ],
            },
        )

        with mock.patch.object(
            debate_research.settings, "DEBATE_RESEARCH_MAX_SOURCES", 2
        ):
            result = await debate_research.research_claim(
                "Die Inflation ist deutlich gestiegen.",
                "Inflation Deutschland 2025",
                client=client,
            )

        self.assertEqual("completed", result.status)
        self.assertEqual(2, len(result.sources))
        self.assertEqual(
            "https://de.wikipedia.org/wiki/Inflation",
            result.sources[0].url,
        )
        self.assertNotIn("<b>", result.sources[0].snippet)
        self.assertEqual(
            "Die Inflation ist deutlich gestiegen.", result.sources[0].claim
        )
        self.assertEqual(2, len({source.url for source in result.sources}))
        self.assertTrue(all(source.url.startswith("https://") for source in result.sources))
        self.assertTrue(all(source.verification_status in {"found", "read"} for source in result.sources))

    async def test_one_provider_can_succeed_when_the_other_fails(self):
        client = _Client(
            wikipedia={
                "query": {
                    "pages": {
                        "10": {
                            "title": "Bundestag",
                            "fullurl": "https://de.wikipedia.org/wiki/Deutscher_Bundestag",
                            "extract": "Das deutsche Parlament.",
                        }
                    }
                }
            },
            failures={"duckduckgo"},
        )

        result = await debate_research.research_claim(
            "Der Bundestag beschliesst Bundesgesetze.",
            "Aufgabe Deutscher Bundestag",
            client=client,
        )

        self.assertEqual("completed", result.status)
        self.assertEqual(1, len(result.sources))
        self.assertEqual("wikipedia", result.sources[0].provider)

    async def test_wikipedia_keeps_search_rank_and_bounds_snippets(self):
        client = _Client(
            wikipedia={
                "query": {
                    "pages": {
                        "20": {
                            "title": "Less relevant",
                            "index": 2,
                            "fullurl": "https://de.wikipedia.org/wiki/Less_relevant",
                            "extract": "later",
                        },
                        "10": {
                            "title": "Best match",
                            "index": 1,
                            "fullurl": "https://de.wikipedia.org/wiki/Best_match",
                            "extract": "x" * 2000,
                        },
                    }
                }
            }
        )

        result = await debate_research.research_claim(
            "Die beste passende Behauptung.",
            "beste passende Behauptung",
            client=client,
        )

        self.assertEqual("Best match", result.sources[0].title)
        self.assertLessEqual(len(result.sources[0].snippet), 600)

    async def test_total_timeout_returns_bounded_failure(self):
        class _SlowClient:
            async def get(self, url, **kwargs):
                await asyncio.Event().wait()

        with mock.patch.object(
            debate_research.settings, "DEBATE_RESEARCH_TIMEOUT_SECONDS", 0.01
        ):
            result = await debate_research.research_claim(
                "Eine zeitkritische Behauptung.",
                "zeitkritische Behauptung pruefen",
                client=_SlowClient(),
            )

        self.assertEqual("unavailable", result.status)
        self.assertEqual([], result.sources)
        self.assertIn("timed out", result.error.lower())

    async def test_missing_urls_never_create_fallback_sources(self):
        client = _Client(
            wikipedia={"query": {"pages": {}}},
            duckduckgo={
                "Heading": "Behauptung",
                "AbstractText": "Text ohne belegbare URL",
                "AbstractURL": "",
                "RelatedTopics": [{"Text": "Auch ohne URL"}],
            },
        )

        result = await debate_research.research_claim(
            "Unbelegte Behauptung.",
            "unbelegte Behauptung",
            client=client,
        )

        self.assertEqual("unavailable", result.status)
        self.assertEqual([], result.sources)
        self.assertTrue(result.error)


if __name__ == "__main__":
    unittest.main()
