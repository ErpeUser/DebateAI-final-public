"""Core startup and shutdown must not depend on optional account discovery."""

import asyncio
import os
import unittest
from contextlib import ExitStack, asynccontextmanager
from types import SimpleNamespace
from unittest import mock

from app import main


class OptionalBridgeStartupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.sessions = []

        @asynccontextmanager
        async def session():
            db = SimpleNamespace(commits=0, closed=False)

            async def commit():
                db.commits += 1

            db.commit = commit
            self.sessions.append(db)
            try:
                yield db
            finally:
                db.closed = True

        @asynccontextmanager
        async def connection():
            yield SimpleNamespace(run_sync=mock.AsyncMock())

        engine = SimpleNamespace(begin=connection, dispose=mock.AsyncMock())
        self.stack.enter_context(mock.patch.object(main, "engine", engine))
        self.stack.enter_context(mock.patch("app.database.async_session", session))
        self.stack.enter_context(
            mock.patch.dict(os.environ, {"DEBATEAI_INSTANCE_TOKEN": ""})
        )
        for target in (
            "app.main._run_schema_migrations",
            "app.main._recover_interrupted_audio",
            "app.main._cleanup_orphan_audio",
            "app.services.seed_agents.seed_agent_configs",
            "app.services.seed_agents.configure_desktop_debate_runtime",
            "app.services.seed_knowledge.seed_knowledge_sources",
            "app.services.llm_endpoint.migrate_legacy_endpoint",
            "app.services.provider_health.verify_untested_provider_keys",
            "app.services.pii.shield.warm_up_ner",
            "app.services.windows_audio_capture.native_windows_audio.stop",
            "app.services.debate_research.close_research_client",
        ):
            self.stack.enter_context(mock.patch(target, mock.AsyncMock()))
        self.stack.enter_context(
            mock.patch(
                "app.services.pii.vault.migrate_legacy_entries",
                mock.AsyncMock(return_value=0),
            )
        )
        for target in (
            "app.main.ai_config._ensure_static_prompts",
            "app.main.updates.start_background_check",
            "app.main.updates.stop_background_check",
            "app.services.subscription_bridge.cleanup_gemini_web_cookie",
        ):
            self.stack.enter_context(mock.patch(target, mock.Mock(return_value=None)))

    async def enter_without_waiting_for_bridge(self):
        context = main.lifespan(main.app)
        try:
            await asyncio.wait_for(context.__aenter__(), timeout=1)
        except TimeoutError:
            self.fail("Core startup waited for optional bridge discovery")
        return context

    async def test_pending_bridge_does_not_block_core_and_is_drained_on_shutdown(self):
        started, cancelled = asyncio.Event(), asyncio.Event()
        bridge_sessions = []

        async def pending(db):
            bridge_sessions.append(db)
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.stack.enter_context(
            mock.patch(
                "app.services.subscription_bridge.sync_subscription_bridge", pending
            )
        )
        context = await self.enter_without_waiting_for_bridge()
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            self.assertTrue(self.sessions[0].closed)
            self.assertIsNot(self.sessions[0], bridge_sessions[0])
            self.assertFalse(bridge_sessions[0].closed)
            self.assertFalse(cancelled.is_set())
            self.assertEqual({"status": "ok"}, await main.health())
        finally:
            await context.__aexit__(None, None, None)
        self.assertTrue(cancelled.is_set())
        self.assertTrue(bridge_sessions[0].closed)

    async def test_failed_bridge_does_not_abort_startup(self):
        attempted = asyncio.Event()

        async def unavailable(_db):
            attempted.set()
            raise RuntimeError("optional provider unavailable")

        self.stack.enter_context(
            mock.patch(
                "app.services.subscription_bridge.sync_subscription_bridge", unavailable
            )
        )
        context = await self.enter_without_waiting_for_bridge()
        try:
            await asyncio.wait_for(attempted.wait(), timeout=1)
            self.assertEqual({"status": "ok"}, await main.health())
        finally:
            await context.__aexit__(None, None, None)

    async def test_successful_discovery_commits_its_own_session(self):
        completed = asyncio.Event()
        bridge_sessions = []

        async def discovered(db):
            bridge_sessions.append(db)
            completed.set()

        self.stack.enter_context(
            mock.patch(
                "app.services.subscription_bridge.sync_subscription_bridge", discovered
            )
        )
        context = await self.enter_without_waiting_for_bridge()
        try:
            await asyncio.wait_for(completed.wait(), timeout=1)
            self.assertEqual(1, self.sessions[0].commits)
            self.assertIsNot(self.sessions[0], bridge_sessions[0])
            self.assertEqual(1, bridge_sessions[0].commits)
            self.assertTrue(bridge_sessions[0].closed)
        finally:
            await context.__aexit__(None, None, None)

    async def test_exception_in_lifespan_body_still_drains_discovery(self):
        started, cancelled = asyncio.Event(), asyncio.Event()

        async def pending(_db):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.stack.enter_context(
            mock.patch(
                "app.services.subscription_bridge.sync_subscription_bridge", pending
            )
        )
        context = await self.enter_without_waiting_for_bridge()
        await asyncio.wait_for(started.wait(), timeout=1)
        suppressed = await context.__aexit__(
            RuntimeError, RuntimeError("lifespan consumer failed"), None
        )
        self.assertFalse(suppressed)
        self.assertTrue(cancelled.is_set())


if __name__ == "__main__":
    unittest.main()
