import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar


class ShutdownReserved(RuntimeError):
    pass


_lock = threading.Lock()
_active: dict[str, int] = {}
_shutdown_deadline: float | None = None
_exclusive_token: object | None = None
_activity_owner: ContextVar[object | None] = ContextVar("diagnostic_owner", default=None)


def _expire_shutdown() -> None:
    global _shutdown_deadline
    if _shutdown_deadline is not None and time.monotonic() >= _shutdown_deadline:
        _shutdown_deadline = None


@contextmanager
def track(name: str):
    with _lock:
        _expire_shutdown()
        if _shutdown_deadline is not None:
            raise ShutdownReserved("Update installation is starting.")
        if _exclusive_token is not None and _activity_owner.get() is not _exclusive_token:
            raise ShutdownReserved("A diagnostic job is running; retry after it has drained.")
        _active[name] = _active.get(name, 0) + 1
    try:
        yield
    finally:
        with _lock:
            remaining = _active[name] - 1
            if remaining:
                _active[name] = remaining
            else:
                del _active[name]


def request_tracker(name: str):
    async def dependency():
        with track(name):
            yield

    return dependency


def busy_reason() -> str:
    with _lock:
        _expire_shutdown()
        if _active:
            return next(iter(_active))
        return "update installation" if _shutdown_deadline is not None else ""


def reserve_shutdown(timeout_seconds: int = 60) -> bool:
    global _shutdown_deadline
    with _lock:
        _expire_shutdown()
        if _active or _shutdown_deadline is not None:
            return False
        _shutdown_deadline = time.monotonic() + timeout_seconds
        return True


def release_shutdown() -> None:
    global _shutdown_deadline
    with _lock:
        _shutdown_deadline = None


@contextmanager
def exclusive(name: str):
    """Atomically exclude live calls, updates and other jobs during calibration.

    The owner's nested tracking is allowed, including asyncio.to_thread, which
    carries context variables. Other tasks/threads cannot enter. Callers must
    retain this context until native work has actually completed.
    """
    global _exclusive_token
    with _lock:
        _expire_shutdown()
        if _active or _shutdown_deadline is not None or _exclusive_token is not None:
            raise ShutdownReserved("Finish the active call, job or update before calibration.")
        owner = object()
        _exclusive_token = owner
        _active[name] = 1
    context_token = _activity_owner.set(owner)
    try:
        yield
    finally:
        _activity_owner.reset(context_token)
        with _lock:
            del _active[name]
            _exclusive_token = None
