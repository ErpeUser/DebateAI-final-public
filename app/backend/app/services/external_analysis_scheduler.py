"""Bounded, revision-aware scheduling for optional external analysis work."""

from __future__ import annotations

import asyncio
import weakref
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class AnalysisJobContext:
    """Immutable identity of the application state one analysis may update."""

    session_id: str
    claim_id: str
    claim_revision: int
    directive_revision: int
    config_generation: int
    generation_id: str


class ExternalAnalysisPriority(IntEnum):
    MANUAL = 0
    AUTOMATIC = 1


class ExternalAnalysisSuperseded(RuntimeError):
    """A newer automatic request replaced this request before it started."""


class ExternalAnalysisCancelled(RuntimeError):
    """The user or owning session cancelled this one analysis request."""


class ExternalAnalysisDeadline(TimeoutError):
    """The end-to-end deadline elapsed in the queue or operation."""


class ExternalAnalysisQueueFull(RuntimeError):
    """A session already owns its bounded number of manual requests."""


@dataclass(slots=True)
class _AnalysisJob(Generic[T]):
    context: AnalysisJobContext
    priority: ExternalAnalysisPriority
    operation: Callable[[], Awaitable[T]]
    is_current: Callable[[], bool]
    expires_at: float
    result: asyncio.Future[T]
    inner_task: asyncio.Task[T] | None = None
    cancel_requested: bool = False


class ExternalAnalysisScheduler:
    """Run external work fairly without allowing unbounded per-session queues."""

    def __init__(
        self,
        *,
        max_parallel: int,
        max_manual_per_session: int = 2,
    ) -> None:
        self.max_parallel = max(1, int(max_parallel))
        self.max_manual_per_session = max(1, int(max_manual_per_session))
        self._automatic_pending: dict[str, _AnalysisJob] = {}
        self._manual_pending: dict[str, deque[_AnalysisJob]] = {}
        self._automatic_sessions: deque[str] = deque()
        self._manual_sessions: deque[str] = deque()
        self._automatic_session_set: set[str] = set()
        self._manual_session_set: set[str] = set()
        self._running: dict[str, _AnalysisJob] = {}
        self._wake = asyncio.Event()
        self._workers: list[asyncio.Task] = []

    async def run(
        self,
        context: AnalysisJobContext,
        priority: ExternalAnalysisPriority,
        operation: Callable[[], Awaitable[T]],
        *,
        deadline_seconds: float,
        is_current: Callable[[], bool] | None = None,
    ) -> T:
        """Queue one operation; its deadline starts before any capacity wait."""
        loop = asyncio.get_running_loop()
        result: asyncio.Future[T] = loop.create_future()
        job = _AnalysisJob(
            context=context,
            priority=priority,
            operation=operation,
            is_current=is_current or (lambda: True),
            expires_at=loop.time() + max(0.001, float(deadline_seconds)),
            result=result,
        )
        self._ensure_workers()
        self._enqueue(job)
        # Capacity can stay occupied longer than this job's budget. Expire the
        # waiter independently, but leave a running operation owned by its worker
        # until cancellation cleanup has actually finished.
        expiry = loop.call_at(job.expires_at, self._expire_job, job)
        try:
            return await result
        except asyncio.CancelledError:
            self.cancel_generation(context.generation_id)
            raise
        finally:
            expiry.cancel()
            # A deadline/manual error can settle the future in the same turn
            # that the caller is cancelled. Own that error even if cancellation
            # wins delivery to the caller.
            if result.done() and not result.cancelled():
                result.exception()

    def _expire_job(self, job: _AnalysisJob) -> None:
        if job.result.done():
            return
        self._remove_pending(job.context.generation_id)
        message = (
            "Analysis expired while waiting for capacity"
            if job.inner_task is None
            else "Analysis exceeded its end-to-end deadline"
        )
        job.result.set_exception(ExternalAnalysisDeadline(message))
        if job.inner_task is not None and not job.inner_task.done():
            job.inner_task.cancel()
        self._wake.set()

    def cancel_generation(self, generation_id: str) -> bool:
        """Cancel one queued/running request without touching shared bridges."""
        job = self._running.get(generation_id)
        if job is None:
            job = self._remove_pending(generation_id)
        if job is None or job.cancel_requested:
            return False
        # Cancelling run() also cancels the future it directly awaits. That
        # does not mean the worker's provider operation has stopped.
        if job.result.done() and not job.result.cancelled():
            return False
        job.cancel_requested = True
        if not job.result.done():
            job.result.set_exception(
                ExternalAnalysisCancelled(f"Analysis {generation_id} was cancelled")
            )
        if job.inner_task is not None and not job.inner_task.done():
            job.inner_task.cancel()
        self._wake.set()
        return True

    def cancel_session(self, session_id: str) -> int:
        """Cancel requests owned by a closing session, not provider processes."""
        generation_ids = [
            job.context.generation_id
            for job in self._all_jobs()
            if job.context.session_id == session_id
        ]
        return sum(self.cancel_generation(generation_id) for generation_id in generation_ids)

    def _ensure_workers(self) -> None:
        if self._workers:
            return
        self._workers = [
            asyncio.create_task(
                self._worker(),
                name=f"external-analysis-worker-{index + 1}",
            )
            for index in range(self.max_parallel)
        ]

    def _enqueue(self, job: _AnalysisJob) -> None:
        session_id = job.context.session_id
        if job.priority is ExternalAnalysisPriority.AUTOMATIC:
            previous = self._automatic_pending.get(session_id)
            if previous is not None and not previous.result.done():
                previous.result.set_exception(
                    ExternalAnalysisSuperseded(
                        "A newer automatic analysis replaced the waiting request"
                    )
                )
            self._automatic_pending[session_id] = job
            if session_id not in self._automatic_session_set:
                self._automatic_session_set.add(session_id)
                self._automatic_sessions.append(session_id)
        else:
            manual_count = sum(
                1
                for existing in self._all_jobs()
                if existing.context.session_id == session_id
                and existing.priority is ExternalAnalysisPriority.MANUAL
                and not existing.result.done()
            )
            if manual_count >= self.max_manual_per_session:
                raise ExternalAnalysisQueueFull(
                    "Too many manual analyses are already queued for this session"
                )
            queue = self._manual_pending.setdefault(session_id, deque())
            queue.append(job)
            if session_id not in self._manual_session_set:
                self._manual_session_set.add(session_id)
                self._manual_sessions.append(session_id)
        self._wake.set()

    def _take_next(self) -> _AnalysisJob | None:
        job = self._take_manual()
        if job is not None:
            return job
        return self._take_automatic()

    def _take_manual(self) -> _AnalysisJob | None:
        while self._manual_sessions:
            session_id = self._manual_sessions.popleft()
            self._manual_session_set.discard(session_id)
            queue = self._manual_pending.get(session_id)
            if queue is None:
                continue
            while queue and queue[0].result.done():
                queue.popleft()
            if not queue:
                self._manual_pending.pop(session_id, None)
                continue
            job = queue.popleft()
            if queue:
                self._manual_sessions.append(session_id)
                self._manual_session_set.add(session_id)
            else:
                self._manual_pending.pop(session_id, None)
            return job
        return None

    def _take_automatic(self) -> _AnalysisJob | None:
        while self._automatic_sessions:
            session_id = self._automatic_sessions.popleft()
            self._automatic_session_set.discard(session_id)
            job = self._automatic_pending.pop(session_id, None)
            if job is not None and not job.result.done():
                return job
        return None

    async def _worker(self) -> None:
        while True:
            job = self._take_next()
            if job is None:
                self._wake.clear()
                if self._manual_sessions or self._automatic_sessions:
                    self._wake.set()
                    continue
                await self._wake.wait()
                continue
            await self._execute(job)

    async def _execute(self, job: _AnalysisJob) -> None:
        if job.result.done():
            return
        loop = asyncio.get_running_loop()
        remaining = job.expires_at - loop.time()
        if remaining <= 0:
            job.result.set_exception(
                ExternalAnalysisDeadline("Analysis expired while waiting for capacity")
            )
            return
        if not job.is_current():
            job.result.set_exception(
                ExternalAnalysisSuperseded("Analysis context is no longer current")
            )
            return

        generation_id = job.context.generation_id
        inner = asyncio.create_task(
            job.operation(),
            name=f"external-analysis-{generation_id}",
        )
        job.inner_task = inner
        self._running[generation_id] = job
        try:
            # run() owns the deadline and cancels this operation. A second
            # timeout here could cancel its cleanup a second time.
            value = await inner
            if job.result.done():
                return
            if not job.is_current():
                job.result.set_exception(
                    ExternalAnalysisSuperseded("Analysis context changed before delivery")
                )
            else:
                job.result.set_result(value)
        except TimeoutError:
            if not job.result.done():
                job.result.set_exception(
                    ExternalAnalysisDeadline("Analysis exceeded its end-to-end deadline")
                )
        except asyncio.CancelledError:
            if not job.result.done():
                error = (
                    ExternalAnalysisCancelled("Analysis was cancelled")
                    if job.cancel_requested
                    else ExternalAnalysisSuperseded("Analysis worker was cancelled")
                )
                job.result.set_exception(error)
            # Cancelling an inner job is recoverable; cancelling the worker
            # itself is shutdown and must terminate its loop after cleanup.
            worker = asyncio.current_task()
            if worker is not None and worker.cancelling():
                raise
        except Exception as exc:
            if not job.result.done():
                job.result.set_exception(exc)
        finally:
            if not inner.done():
                inner.cancel()
                try:
                    await inner
                except (asyncio.CancelledError, Exception):
                    pass
            self._running.pop(generation_id, None)

    def _remove_pending(self, generation_id: str) -> _AnalysisJob | None:
        for session_id, job in tuple(self._automatic_pending.items()):
            if job.context.generation_id == generation_id:
                self._automatic_pending.pop(session_id, None)
                return job
        for session_id, queue in tuple(self._manual_pending.items()):
            for job in tuple(queue):
                if job.context.generation_id == generation_id:
                    queue.remove(job)
                    if not queue:
                        self._manual_pending.pop(session_id, None)
                    return job
        return None

    def _all_jobs(self):
        yield from self._automatic_pending.values()
        for queue in self._manual_pending.values():
            yield from queue
        yield from self._running.values()


_schedulers_by_loop: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[int, ExternalAnalysisScheduler]
] = weakref.WeakKeyDictionary()


def external_analysis_scheduler(max_parallel: int) -> ExternalAnalysisScheduler:
    """Return the process-wide scheduler for this event loop and capacity."""
    loop = asyncio.get_running_loop()
    capacity = max(1, int(max_parallel))
    schedulers = _schedulers_by_loop.setdefault(loop, {})
    return schedulers.setdefault(
        capacity,
        ExternalAnalysisScheduler(max_parallel=capacity),
    )
