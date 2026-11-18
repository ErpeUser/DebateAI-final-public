import asyncio
import unittest

from app.services.external_analysis_scheduler import (
    AnalysisJobContext,
    ExternalAnalysisCancelled,
    ExternalAnalysisDeadline,
    ExternalAnalysisPriority,
    ExternalAnalysisScheduler,
    ExternalAnalysisSuperseded,
)


def context(session_id: str, generation_id: str) -> AnalysisJobContext:
    return AnalysisJobContext(
        session_id=session_id,
        claim_id=f"claim-{generation_id}",
        claim_revision=1,
        directive_revision=0,
        config_generation=1,
        generation_id=generation_id,
    )


class ExternalAnalysisSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_automatic_job_replaces_only_the_waiting_job_for_its_session(self):
        scheduler = ExternalAnalysisScheduler(max_parallel=1)
        blocker_started = asyncio.Event()
        release_blocker = asyncio.Event()

        async def blocker():
            blocker_started.set()
            await release_blocker.wait()
            return "blocker"

        running = asyncio.create_task(
            scheduler.run(
                context("busy", "running"),
                ExternalAnalysisPriority.AUTOMATIC,
                blocker,
                deadline_seconds=1,
            )
        )
        await blocker_started.wait()

        old_ran = False

        async def old_operation():
            nonlocal old_ran
            old_ran = True
            return "old"

        old = asyncio.create_task(
            scheduler.run(
                context("session-a", "old"),
                ExternalAnalysisPriority.AUTOMATIC,
                old_operation,
                deadline_seconds=1,
            )
        )
        await asyncio.sleep(0)
        newest = asyncio.create_task(
            scheduler.run(
                context("session-a", "newest"),
                ExternalAnalysisPriority.AUTOMATIC,
                lambda: asyncio.sleep(0, result="newest"),
                deadline_seconds=1,
            )
        )

        with self.assertRaises(ExternalAnalysisSuperseded):
            await old
        self.assertFalse(old_ran)

        release_blocker.set()
        self.assertEqual("blocker", await running)
        self.assertEqual("newest", await newest)

    async def test_manual_job_runs_before_already_waiting_automatic_job(self):
        scheduler = ExternalAnalysisScheduler(max_parallel=1)
        blocker_started = asyncio.Event()
        release_blocker = asyncio.Event()
        order: list[str] = []

        async def blocker():
            blocker_started.set()
            await release_blocker.wait()

        async def record(label: str):
            order.append(label)
            return label

        running = asyncio.create_task(
            scheduler.run(
                context("busy", "running"),
                ExternalAnalysisPriority.AUTOMATIC,
                blocker,
                deadline_seconds=1,
            )
        )
        await blocker_started.wait()
        automatic = asyncio.create_task(
            scheduler.run(
                context("auto", "auto"),
                ExternalAnalysisPriority.AUTOMATIC,
                lambda: record("automatic"),
                deadline_seconds=1,
            )
        )
        manual = asyncio.create_task(
            scheduler.run(
                context("manual", "manual"),
                ExternalAnalysisPriority.MANUAL,
                lambda: record("manual"),
                deadline_seconds=1,
            )
        )
        await asyncio.sleep(0)

        release_blocker.set()
        await running
        self.assertEqual("manual", await manual)
        self.assertEqual("automatic", await automatic)
        self.assertEqual(["manual", "automatic"], order)

    async def test_deadline_includes_time_spent_waiting_for_capacity(self):
        scheduler = ExternalAnalysisScheduler(max_parallel=1)
        blocker_started = asyncio.Event()
        release_blocker = asyncio.Event()
        expired_ran = False

        async def blocker():
            blocker_started.set()
            await release_blocker.wait()

        async def expired_operation():
            nonlocal expired_ran
            expired_ran = True

        running = asyncio.create_task(
            scheduler.run(
                context("busy", "running"),
                ExternalAnalysisPriority.AUTOMATIC,
                blocker,
                deadline_seconds=1,
            )
        )
        await blocker_started.wait()
        expired = asyncio.create_task(
            scheduler.run(
                context("waiting", "expired"),
                ExternalAnalysisPriority.AUTOMATIC,
                expired_operation,
                deadline_seconds=0.01,
            )
        )
        await asyncio.sleep(0.03)
        release_blocker.set()
        await running

        with self.assertRaises(ExternalAnalysisDeadline):
            await expired
        self.assertFalse(expired_ran)

    async def test_cancel_generation_stops_only_that_request_operation(self):
        scheduler = ExternalAnalysisScheduler(max_parallel=2)
        cancelled_started = asyncio.Event()
        cancelled_closed = asyncio.Event()
        sibling_release = asyncio.Event()

        async def cancellable():
            cancelled_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled_closed.set()

        cancelled = asyncio.create_task(
            scheduler.run(
                context("same-session", "cancel-me"),
                ExternalAnalysisPriority.MANUAL,
                cancellable,
                deadline_seconds=1,
            )
        )
        sibling = asyncio.create_task(
            scheduler.run(
                context("same-session", "keep-me"),
                ExternalAnalysisPriority.MANUAL,
                lambda: sibling_release.wait(),
                deadline_seconds=1,
            )
        )
        await cancelled_started.wait()

        self.assertTrue(scheduler.cancel_generation("cancel-me"))
        with self.assertRaises(ExternalAnalysisCancelled):
            await cancelled
        await cancelled_closed.wait()

        self.assertFalse(sibling.done())
        sibling_release.set()
        await sibling


if __name__ == "__main__":
    unittest.main()
