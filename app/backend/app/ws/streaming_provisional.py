"""Bounded local-ASR deltas feeding the existing provisional coach contract."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class StreamingProvisionalRelay:
    """Coalesce each track without putting model work on the capture callback.

    At most one task and one bounded text window per track are retained. Finals
    retire the corresponding generation; this is not an alternative LLM engine.
    """

    def __init__(
        self,
        deliver: Callable[..., Awaitable[object]],
        *,
        capture_id: str,
        interval: float = 0.25,
        max_chars: int = 2000,
    ):
        if interval <= 0 or max_chars < 2:
            raise ValueError("Provisional limits must be positive")
        self._deliver = deliver
        self._interval = interval
        self._max_chars = max_chars
        self._ids = {
            track: f"{capture_id[:96]}:track:{track}:{uuid.uuid4().hex}"
            for track in (0, 1)
        }
        self._text = {track: "" for track in (0, 1)}
        self._revision = {track: 0 for track in (0, 1)}
        self._tasks: dict[int, asyncio.Task] = {}
        self._closed = False

    def append(self, track: int, delta: str) -> tuple[str, int]:
        if self._closed:
            raise RuntimeError("Provisional relay is closed")
        if track not in self._ids or isinstance(track, bool):
            raise ValueError("Unknown audio track")
        if not isinstance(delta, str):
            raise ValueError("Transcript delta must be text")
        if delta:
            self._text[track] = (self._text[track] + delta)[-self._max_chars :]
            self._revision[track] += 1
            task = self._tasks.get(track)
            if task is None or task.done():
                self._tasks[track] = asyncio.create_task(
                    self._run(track, self._ids[track]),
                    name=f"local-provisional-{track}",
                )
        return self._ids[track], self._revision[track]

    async def _run(self, track: int, identity: str) -> None:
        delivered = -1
        while not self._closed and self._ids[track] == identity:
            await asyncio.sleep(self._interval)
            revision = self._revision[track]
            if revision == delivered:
                return
            text = self._text[track]
            try:
                await self._deliver(
                    text, utterance_id=identity, segment_revision=revision
                )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                # Do not log the transcript or provider exception text.
                logger.warning("Provisional delivery failed (%s)", type(error).__name__)
            delivered = revision
            if self._revision[track] == delivered:
                return

    async def finalize(self, track: int) -> str:
        if track not in self._ids or isinstance(track, bool):
            raise ValueError("Unknown audio track")
        identity = self._ids[track]
        self._ids[track] = uuid.uuid4().hex
        self._text[track] = ""
        self._revision[track] = 0
        task = self._tasks.pop(track, None)
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return identity

    async def close(self) -> None:
        self._closed = True
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
