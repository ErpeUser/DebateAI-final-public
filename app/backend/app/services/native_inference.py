"""Cancellation-safe bridge for native work executed in Python threads."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
_supervised_workers: set[asyncio.Task] = set()


def _supervise(worker: asyncio.Task) -> None:
    """Keep an abandoned native worker referenced until it physically ends."""
    _supervised_workers.add(worker)
    worker.add_done_callback(_supervised_workers.discard)


class NativeInferenceLane:
    """Serialize one native context and quarantine it after abandonment.

    Python cannot stop an already-running native thread. Cancellation therefore
    releases the async caller immediately but marks this lane unavailable. The
    physical worker remains supervised and no second job can enter the same
    model/context behind its back.
    """

    def __init__(self, name: str):
        self.name = name
        self._lock = asyncio.Lock()
        self._worker: asyncio.Task | None = None
        self._unavailable = False

    @property
    def unavailable(self) -> bool:
        return self._unavailable

    async def run(
        self,
        operation: Callable[..., T],
        /,
        *args: Any,
        timeout_seconds: float | None = None,
        **kwargs: Any,
    ) -> T:
        async with self._lock:
            if self._unavailable:
                raise RuntimeError(f"Native inference lane {self.name} is unavailable")
            worker = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
            self._worker = worker
            try:
                awaited = asyncio.shield(worker)
                if timeout_seconds is not None:
                    return await asyncio.wait_for(awaited, timeout_seconds)
                return await awaited
            except (asyncio.CancelledError, TimeoutError):
                # Cancellation/timeout says nothing about the native function:
                # it may still hold ORT/CUDA state. Quarantine this context.
                self._unavailable = True
                _supervise(worker)
                raise
            finally:
                if worker.done():
                    self._worker = None

    async def close(self, timeout_seconds: float = 0.25) -> bool:
        worker = self._worker
        if worker is None or worker.done():
            return True
        _supervise(worker)
        try:
            await asyncio.wait_for(asyncio.shield(worker), timeout_seconds)
            return True
        except (TimeoutError, asyncio.CancelledError):
            self._unavailable = True
            return False


async def run_native_until_complete(
    operation: Callable[..., T],
    /,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Run unowned native work while supervising it after cancellation.

    Callers that reuse a model/context should use :class:`NativeInferenceLane`
    so abandonment also prevents a new job from entering that context.
    """
    worker = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        _supervise(worker)
        raise
