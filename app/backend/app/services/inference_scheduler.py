"""Priority scheduling for requests sent to local model endpoints."""

import asyncio
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class InferencePriority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"


class InferencePreempted(RuntimeError):
    """A normal local request yielded its endpoint to urgent guidance."""


@dataclass
class _EndpointState:
    serial: asyncio.Lock = field(default_factory=asyncio.Lock)
    guard: asyncio.Lock = field(default_factory=asyncio.Lock)
    current_task: asyncio.Task | None = None
    current_priority: InferencePriority | None = None
    preempted_tasks: set[asyncio.Task] = field(default_factory=set)


_states_by_loop: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[str, _EndpointState]
] = weakref.WeakKeyDictionary()


def _state(endpoint_key: str) -> _EndpointState:
    loop = asyncio.get_running_loop()
    states = _states_by_loop.setdefault(loop, {})
    return states.setdefault(endpoint_key, _EndpointState())


async def run_local_inference(
    endpoint_key: str,
    priority: InferencePriority,
    operation: Callable[[], Awaitable[T]],
) -> T:
    """Run one local request, allowing urgent work to preempt normal work."""
    state = _state(endpoint_key)

    if priority is InferencePriority.HIGH:
        async with state.guard:
            running = state.current_task
            if (
                running is not None
                and not running.done()
                and state.current_priority is InferencePriority.NORMAL
            ):
                state.preempted_tasks.add(running)
                running.cancel()

    async with state.serial:
        inner = asyncio.create_task(operation())
        async with state.guard:
            state.current_task = inner
            state.current_priority = priority
        try:
            return await inner
        except asyncio.CancelledError as exc:
            async with state.guard:
                preempted = inner in state.preempted_tasks
                state.preempted_tasks.discard(inner)
            if preempted:
                raise InferencePreempted(
                    f"Local inference at {endpoint_key} was preempted by urgent work"
                ) from exc
            raise
        finally:
            if not inner.done():
                inner.cancel()
                try:
                    await inner
                except asyncio.CancelledError:
                    pass
            async with state.guard:
                state.preempted_tasks.discard(inner)
                if state.current_task is inner:
                    state.current_task = None
                    state.current_priority = None
