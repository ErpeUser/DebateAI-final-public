import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from app.routers.dossiers import _prepare_record_embedding, _source
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.debate_settings import DebateSettings
from app.services.session_manager import get_local_dossier_context


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return False


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


class _DossierDb:
    def __init__(self, source, records=(), claims=()):
        self.source = source
        self.records = list(records)
        self.claims = list(claims)
        self.record_queries = 0

    async def execute(self, statement):
        sql = str(statement)
        if "FROM knowledge_sources" in sql:
            return _ScalarResult([self.source] if self.source is not None else [])
        if "FROM knowledge_records" in sql:
            self.record_queries += 1
            return _ScalarResult(self.records)
        if "FROM debate_claim_records" in sql:
            return _ScalarResult(self.claims)
        raise AssertionError(sql)


class DossierEmbeddingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_dossier_record_prepares_reusable_embedding_metadata(self):
        record = SimpleNamespace(id=uuid.uuid4(), active=True, meta="{}")

        with mock.patch(
            "app.routers.dossiers.prepare_knowledge_record_embeddings",
            return_value=1,
        ) as prepare:
            await _prepare_record_embedding(record)

        prepare.assert_called_once_with([record])


class DossierAclIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_inactive_dossier_source_is_not_used_for_runtime_context(self):
        session_id = uuid.uuid4()
        source = SimpleNamespace(
            id=uuid.uuid4(),
            active=False,
            config=(
                '{"kind":"session_dossier","session_id":"'
                + str(session_id)
                + '","local_only":true}'
            ),
        )
        record = SimpleNamespace(id=uuid.uuid4(), active=True, meta="{}")
        db = _DossierDb(source, [record])

        with mock.patch(
            "app.services.session_manager.retrieve_knowledge_record_context",
            mock.AsyncMock(return_value="private dossier"),
        ) as retrieve:
            context = await get_local_dossier_context(
                session_id,
                db,
                query="Behauptung",
            )

        self.assertEqual("", context)
        self.assertEqual(0, db.record_queries)
        retrieve.assert_not_awaited()

    async def test_non_local_source_config_is_not_accepted_as_session_dossier(self):
        session_id = uuid.uuid4()
        source = SimpleNamespace(
            id=uuid.uuid4(),
            active=True,
            config=(
                '{"kind":"session_dossier","session_id":"'
                + str(session_id)
                + '","local_only":false}'
            ),
        )
        db = _DossierDb(source)

        resolved = await _source(db, session_id, create=False)

        self.assertIsNone(resolved)

    async def test_query_time_private_context_respects_total_budget(self):
        claim = SimpleNamespace(
            claim_id="claim-1",
            original_text="x" * 13_000,
            revision=1,
            sources=[],
        )
        db = _DossierDb(None, claims=[claim])

        context = await get_local_dossier_context(
            uuid.uuid4(),
            db,
            query="Behauptung",
        )

        self.assertLessEqual(len(context), 12_000)


class DossierRuntimeIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_support_uses_query_time_hybrid_dossier_retrieval(self):
        orchestrator = object.__new__(AgentOrchestrator)
        orchestrator.session_id = uuid.uuid4()
        orchestrator.local_dossier_context = "full dossier fallback"
        orchestrator._get_model = lambda _slug: "endpoint:local:debate"
        orchestrator.debate_settings = DebateSettings()
        orchestrator._board_stubs = []
        orchestrator.active_questions = []
        orchestrator._semantic_argument_memory = None
        db = mock.AsyncMock()

        with (
            mock.patch(
                "app.services.agents.orchestrator.async_session",
                return_value=_SessionContext(db),
            ),
            mock.patch(
                "app.services.agents.orchestrator.get_local_dossier_context",
                mock.AsyncMock(return_value="### Hybridtreffer\nBeleg"),
            ) as retrieve,
            mock.patch(
                "app.services.agents.orchestrator.allows_local_only",
                mock.AsyncMock(return_value=True),
                create=True,
            ),
        ):
            context = await orchestrator._debate_support_context_async(
                "aktuelle Behauptung",
                include_local_dossier=True,
            )

        retrieve.assert_awaited_once_with(
            orchestrator.session_id,
            db,
            query="aktuelle Behauptung",
        )
        db.commit.assert_not_awaited()
        self.assertIn("Hybridtreffer", context)
        self.assertNotIn("full dossier fallback", context)

    async def test_cloud_debate_route_never_receives_local_dossier(self):
        orchestrator = object.__new__(AgentOrchestrator)
        orchestrator.session_id = uuid.uuid4()
        orchestrator.local_dossier_context = "GEHEIMER PRIVATER DOSSIERINHALT"
        orchestrator._get_model = lambda _slug: "gemini-3.5-flash-lite"
        orchestrator.debate_settings = DebateSettings()
        orchestrator._board_stubs = []
        orchestrator.active_questions = []
        orchestrator._semantic_argument_memory = None

        with (
            mock.patch(
                "app.services.agents.orchestrator.allows_local_only",
                mock.AsyncMock(return_value=False),
                create=True,
            ),
            mock.patch(
                "app.services.agents.orchestrator.get_local_dossier_context",
                mock.AsyncMock(
                    side_effect=AssertionError("cloud route must not retrieve dossier")
                ),
            ) as retrieve,
        ):
            context = await orchestrator._debate_support_context_async(
                "aktuelle Behauptung",
                include_local_dossier=True,
            )

        retrieve.assert_not_awaited()
        self.assertNotIn("GEHEIMER PRIVATER DOSSIERINHALT", context)

    async def test_hybrid_failure_falls_back_to_preloaded_local_dossier(self):
        orchestrator = object.__new__(AgentOrchestrator)
        orchestrator.session_id = uuid.uuid4()
        orchestrator.local_dossier_context = "### Lokaler Beleg\nNur lokal geladen."
        orchestrator._get_model = lambda _slug: "endpoint:local:debate"
        orchestrator.debate_settings = DebateSettings()
        orchestrator._board_stubs = []
        orchestrator.active_questions = []
        orchestrator._semantic_argument_memory = None

        with (
            mock.patch(
                "app.services.agents.orchestrator.async_session",
                return_value=_SessionContext(object()),
            ),
            mock.patch(
                "app.services.agents.orchestrator.get_local_dossier_context",
                mock.AsyncMock(side_effect=RuntimeError("database unavailable")),
            ),
            mock.patch(
                "app.services.agents.orchestrator.allows_local_only",
                mock.AsyncMock(return_value=True),
            ),
        ):
            context = await orchestrator._debate_support_context_async(
                "aktuelle Behauptung",
                include_local_dossier=True,
            )

        self.assertIn("Lokaler Beleg", context)
        self.assertIn("nicht an Cloudmodelle senden", context)


if __name__ == "__main__":
    unittest.main()
