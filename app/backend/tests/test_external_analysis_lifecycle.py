"""Scheduler deadlines and cancellation own provider cleanup and queued work."""
import asyncio
import gc
import unittest

from app.services.external_analysis_scheduler import (
    AnalysisJobContext, ExternalAnalysisPriority, ExternalAnalysisScheduler,
    ExternalAnalysisDeadline, ExternalAnalysisCancelled, ExternalAnalysisSuperseded,
)

def context(generation):
    return AnalysisJobContext(generation,generation,1,1,1,generation)

class SchedulerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.scheduler=ExternalAnalysisScheduler(max_parallel=1)
        self.releases=[]
        self.callers=[]
        self.loop_errors=[]
        self.loop=asyncio.get_running_loop()
        self.previous_handler=self.loop.get_exception_handler()
        self.loop.set_exception_handler(lambda loop, details:self.loop_errors.append(details))

    def event(self):
        event=asyncio.Event()
        self.releases.append(event)
        return event

    def start(self, generation, operation, deadline=10):
        task=asyncio.create_task(self.scheduler.run(
            context(generation),ExternalAnalysisPriority.MANUAL,operation,
            deadline_seconds=deadline))
        self.callers.append(task)
        return task

    async def settle(self):
        for event in self.releases:
            event.set()
        # Ensure even the buggy baseline cannot leave native work hanging in tests.
        for caller in self.callers:
            if not caller.done():
                caller.cancel()
        await asyncio.gather(*self.callers,return_exceptions=True)
        inner=[job.inner_task for job in self.scheduler._running.values() if job.inner_task is not None]
        for task in inner:
            if not task.done():
                task.cancel()
        await asyncio.gather(*inner,return_exceptions=True)
        for _ in range(4):
            await asyncio.sleep(0)
        for worker in self.scheduler._workers:
            worker.cancel()
        await asyncio.wait_for(asyncio.gather(*self.scheduler._workers,return_exceptions=True), 2)

    async def asyncTearDown(self):
        try:
            await self.settle()
            gc.collect()
            await asyncio.sleep(0)
            unobserved=[e for e in self.loop_errors if 'never retrieved' in str(e.get('message',''))]
            self.assertEqual([],unobserved)
        finally:
            self.loop.set_exception_handler(self.previous_handler)

    async def test_cancelling_caller_stops_running_operation(self):
        started=asyncio.Event()
        stopped=asyncio.Event()
        release=self.event()
        async def operation():
            started.set()
            try:
                await release.wait()
            finally:
                stopped.set()
        caller=self.start('caller-cancel',operation)
        await asyncio.wait_for(started.wait(), 1)
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        await asyncio.wait_for(stopped.wait(), 1)

    async def test_queued_deadline_fires_before_capacity_is_released(self):
        started=asyncio.Event()
        release=self.event()
        unwanted_start=asyncio.Event()
        async def blocker():
            started.set()
            await release.wait()
            return 'first'
        async def queued():
            unwanted_start.set()
            return 'second'
        first=self.start('blocker',blocker)
        await asyncio.wait_for(started.wait(), 1)
        second=self.start('short-queue',queued,deadline=.01)
        with self.assertRaises(ExternalAnalysisDeadline):
            await asyncio.wait_for(asyncio.shield(second), 1)
        self.assertFalse(release.is_set())
        self.assertFalse(unwanted_start.is_set())
        release.set()
        self.assertEqual('first',await first)
        self.assertFalse(unwanted_start.is_set())

    async def test_deadline_retains_capacity_until_operation_cleanup_finishes(self):
        started=asyncio.Event()
        cleanup_started=asyncio.Event()
        cleanup_completed=asyncio.Event()
        finish_cleanup=self.event()
        never=self.event()
        next_started=asyncio.Event()
        async def slow():
            started.set()
            try:
                await never.wait()
            finally:
                cleanup_started.set()
                await finish_cleanup.wait()
                cleanup_completed.set()
        async def next_job():
            next_started.set()
            return 'next'
        # Leave room to actually enter the operation on Windows before testing
        # the distinct running-deadline path (the queued path has its own test).
        first=self.start('deadline-cleanup',slow,deadline=.5)
        await asyncio.wait_for(started.wait(), 2)
        await asyncio.wait_for(cleanup_started.wait(), 2)
        with self.assertRaises(ExternalAnalysisDeadline):
            await asyncio.wait_for(asyncio.shield(first), 1)
        second=self.start('next-after-cleanup',next_job)
        # The new caller gets to enqueue, while the original worker still drains.
        await asyncio.sleep(0)
        self.assertFalse(next_started.is_set())
        self.assertFalse(cleanup_completed.is_set())
        finish_cleanup.set()
        self.assertEqual('next',await asyncio.wait_for(second, 1))
        self.assertTrue(cleanup_completed.is_set())

    async def test_explicit_cancel_is_idempotent_and_worker_remains_usable(self):
        started=asyncio.Event()
        stopped=asyncio.Event()
        release=self.event()
        async def operation():
            started.set()
            try:
                await release.wait()
            finally:
                stopped.set()
        caller=self.start('manual-cancel',operation)
        await asyncio.wait_for(started.wait(), 1)
        self.assertTrue(self.scheduler.cancel_generation('manual-cancel'))
        self.assertFalse(self.scheduler.cancel_generation('manual-cancel'))
        with self.assertRaises(ExternalAnalysisCancelled):
            await caller
        await asyncio.wait_for(stopped.wait(), 1)
        async def followup():
            return 7
        self.assertEqual(7,await asyncio.wait_for(self.start('followup',followup), 1))

    async def test_worker_shutdown_propagates_cancellation_after_inner_cleanup(self):
        started=asyncio.Event()
        stopped=asyncio.Event()
        release=self.event()
        async def operation():
            started.set()
            try:
                await release.wait()
            finally:
                stopped.set()
        caller=self.start('shutdown',operation)
        await asyncio.wait_for(started.wait(), 1)
        worker=self.scheduler._workers[0]
        worker.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(asyncio.shield(worker), 1)
        self.assertTrue(stopped.is_set())
        with self.assertRaises(ExternalAnalysisSuperseded):
            await caller

    async def test_error_settlement_racing_caller_cancel_is_observed(self):
        started=asyncio.Event()
        release=self.event()
        async def operation():
            started.set()
            await release.wait()
        caller=self.start('error-cancel-race',operation)
        await asyncio.wait_for(started.wait(), 1)
        # Force both decisions in one event-loop turn, before task wakeup.
        # This is the race a deadline callback/manual error can create.
        job=self.scheduler._running['error-cancel-race']
        job.result.set_exception(ExternalAnalysisDeadline('synthetic deadline race'))
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        release.set()
        del job
        await self.settle()
        self.callers.clear()
        del caller
        gc.collect()
        await asyncio.sleep(0)
        self.assertFalse(any('never retrieved' in str(e.get('message','')) for e in self.loop_errors))

if __name__=='__main__':
    unittest.main(verbosity=2)
