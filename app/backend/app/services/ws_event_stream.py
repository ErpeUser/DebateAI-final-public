"""Bounded, replayable WebSocket events for one live session."""

from __future__ import annotations

import asyncio
import copy
import json
import time
import uuid
from collections import OrderedDict, deque
from typing import Any

COALESCIBLE_TYPES = {"interim_transcript", "audio_level"}
DEFAULT_JOURNAL_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_JOURNAL_IDLE_TTL_SECONDS = 60 * 60
DEFAULT_MAX_JOURNALS = 4096


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    nested = event.get("payload")
    return nested if isinstance(nested, dict) else event


def _coalescible_key(event: dict[str, Any]) -> tuple[str, str, str]:
    event = _payload(event)
    data = event.get("data") or {}
    event_type = str(event.get("type") or "")
    if event_type == "audio_level":
        return event_type, str(data.get("track", 0)), "latest"
    return (
        event_type,
        str(data.get("track_id") or "default"),
        str(data.get("segment_id") or "legacy"),
    )


def _coalesce(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    payload = _payload(current)
    data = payload.get("data") or {}
    if payload.get("type") != "interim_transcript" or data.get("mode") != "append":
        return current
    merged = copy.deepcopy(current)
    target = _payload(merged)["data"]
    prior = _payload(previous).get("data") or {}
    target["text"] = str(prior.get("text") or "") + str(data.get("text") or "")
    target["mode"] = prior.get("mode") or "replace"
    if prior.get("audio_start_sample") is not None:
        target["audio_start_sample"] = prior["audio_start_sample"]
    return merged


def _state_key(event: dict[str, Any]) -> tuple[str, str]:
    event_type = str(event.get("type") or "unknown")
    data = event.get("data") or {}
    if event_type == "interim_transcript":
        return event_type, "|".join(_coalescible_key(event)[1:])
    if event_type == "audio_level":
        return event_type, str(data.get("track", 0))
    if event_type in {"transcript", "transcript_updated"}:
        # Keep the durable creation event as well as its latest revision. A
        # reconnect snapshot must insert the row before applying the update.
        return event_type, str(
            data.get("id") or data.get("sequence") or event.get("session_sequence")
        )
    if event_type in {
        "question",
        "question_answered",
        "insight_updated",
        "insight_elevated",
    }:
        return event_type, str(data.get("id") or event.get("session_sequence"))
    return event_type, "latest"


class SessionEventJournal:
    """Assign a monotone sequence and retain a compact reconnect snapshot."""

    def __init__(
        self,
        session_id: uuid.UUID | str,
        *,
        max_events: int = 512,
        max_state_events: int = 512,
        max_bytes: int = DEFAULT_JOURNAL_MAX_BYTES,
    ) -> None:
        self.session_id = str(session_id)
        self.max_events = max(1, max_events)
        self.max_state_events = max(1, max_state_events)
        self.max_bytes = max(1024, max_bytes)
        self.server_epoch = uuid.uuid4().hex
        self._sequence = 0
        self._generation = 0
        self._active_connections = 0
        self._last_touch = time.monotonic()
        self._events: deque[dict[str, Any]] = deque(maxlen=self.max_events)
        self._state: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
        self._event_bytes = 0
        self._state_bytes = 0

    @property
    def sequence(self) -> int:
        return self._sequence

    def open_generation(self) -> int:
        self._generation += 1
        self._active_connections += 1
        self._last_touch = time.monotonic()
        return self._generation

    def close_generation(self, generation: int) -> None:
        if generation <= self._generation and self._active_connections:
            self._active_connections -= 1
        self._last_touch = time.monotonic()

    @property
    def active_connections(self) -> int:
        return self._active_connections

    @property
    def buffered_bytes(self) -> int:
        return self._event_bytes + self._state_bytes

    def _size(self, event: dict[str, Any]) -> int:
        return len(json.dumps(event, ensure_ascii=False, default=str).encode("utf-8"))

    def _enforce_byte_budget(self) -> None:
        self._event_bytes = sum(self._size(event) for event in self._events)
        self._state_bytes = sum(self._size(event) for event in self._state.values())
        while self._events and self._event_bytes > self.max_bytes:
            self._events.popleft()
            self._event_bytes = sum(self._size(event) for event in self._events)
        while self._state and self._state_bytes > self.max_bytes:
            self._state.popitem(last=False)
            self._state_bytes = sum(self._size(event) for event in self._state.values())

    def is_current_generation(self, generation: int) -> bool:
        return generation == self._generation

    def export_state(self) -> dict[str, Any]:
        """Return JSON-safe replay state for the shared worker store."""
        return {
            "server_epoch": self.server_epoch,
            "sequence": self._sequence,
            "events": copy.deepcopy(list(self._events)),
            "state": [
                {
                    "event_type": key[0],
                    "state_key": key[1],
                    "event": copy.deepcopy(event),
                }
                for key, event in self._state.items()
            ],
        }

    def restore_state(self, payload: dict[str, Any]) -> None:
        """Restore a bounded replay snapshot loaded from shared storage."""
        self.server_epoch = str(payload.get("server_epoch") or self.server_epoch)
        self._sequence = max(0, int(payload.get("sequence") or 0))
        self._events.clear()
        self._state.clear()
        for event in payload.get("events") or []:
            if isinstance(event, dict):
                self._events.append(copy.deepcopy(event))
        for item in payload.get("state") or []:
            if not isinstance(item, dict) or not isinstance(item.get("event"), dict):
                continue
            key = (str(item.get("event_type") or "unknown"), str(item.get("state_key") or "latest"))
            self._state[key] = copy.deepcopy(item["event"])
        while len(self._state) > self.max_state_events:
            self._state.popitem(last=False)
        self._enforce_byte_budget()

    def record(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._sequence += 1
        event = copy.deepcopy(payload)
        event["event_id"] = self._sequence
        event["session_sequence"] = self._sequence
        if event.get("type") == "transcript":
            # The client clears previews on a finalized transcript. A compact
            # snapshot must not join later deltas to the completed preview.
            for state_key in tuple(self._state):
                if state_key[0] == "interim_transcript":
                    del self._state[state_key]
        key = _state_key(event)
        previous = self._state.get(key)
        data = event.get("data") or {}
        state_event = copy.deepcopy(event)
        if (
            event.get("type") == "interim_transcript"
            and data.get("mode") == "append"
            and previous is not None
        ):
            previous_data = previous.get("data") or {}
            state_event["data"] = {
                **data,
                "text": str(previous_data.get("text") or "")
                + str(data.get("text") or ""),
                # Reconnect state is self-contained. The live event remains a
                # small append delta so a long call does not send quadratic data.
                "mode": "replace",
            }

        self._events.append(event)
        self._state.pop(key, None)
        self._state[key] = state_event
        while len(self._state) > self.max_state_events:
            self._state.popitem(last=False)
        self._last_touch = time.monotonic()
        self._enforce_byte_budget()
        return event

    def latest(self, event_type: str) -> dict[str, Any] | None:
        event = self._state.get((event_type, "latest"))
        return copy.deepcopy(event) if event else None

    def snapshot(
        self,
        after_sequence: int = 0,
        *,
        after_epoch: str | None = None,
    ) -> dict[str, Any]:
        self._last_touch = time.monotonic()
        earliest = (
            self._events[0]["session_sequence"] if self._events else self._sequence + 1
        )
        full = (
            (after_epoch is not None and after_epoch != self.server_epoch)
            or after_sequence <= 0
            or after_sequence < earliest - 1
            or after_sequence > self._sequence
        )
        source = self._state.values() if full else self._events
        events = [
            copy.deepcopy(event)
            for event in source
            if full or event["session_sequence"] > after_sequence
        ]
        if not full:
            # Status is state, not history. In particular, never replay an
            # old `completed` immediately before a newer reconnect state.
            latest_status = self._state.get(("status", "latest"))
            events = [event for event in events if event.get("type") != "status"]
            if latest_status and latest_status["session_sequence"] > after_sequence:
                events.append(copy.deepcopy(latest_status))
        events.sort(key=lambda event: event["session_sequence"])
        return {
            "type": "session_snapshot",
            "data": {
                "session_id": self.session_id,
                "server_epoch": self.server_epoch,
                "through_sequence": self._sequence,
                "full": full,
                "events": events,
            },
        }


class ClientSendBuffer:
    """Bound one client's pending sends while preserving final events.

    Final transcripts and state changes apply backpressure when the client is
    slow. Interim revisions may replace an older revision or be discarded.
    """

    def __init__(self, maxsize: int = 256) -> None:
        self.maxsize = max(1, maxsize)
        self._items: deque[dict[str, Any]] = deque()
        self._condition = asyncio.Condition()
        self._closed = False
        self._needs_resync = False

    def qsize(self) -> int:
        return len(self._items)

    @property
    def needs_resync(self) -> bool:
        return self._needs_resync

    async def put(self, event: dict[str, Any]) -> bool:
        kind = _payload(event).get("type")
        async with self._condition:
            if self._closed:
                return False
            if kind in COALESCIBLE_TYPES:
                key = _coalescible_key(event)
                for index, queued in enumerate(self._items):
                    if (
                        _payload(queued).get("type") in COALESCIBLE_TYPES
                        and _coalescible_key(queued) == key
                    ):
                        # A reconnect cursor must not land between an unsent
                        # interim prefix and the event that now carries it.
                        if kind == "audio_level" or index == len(self._items) - 1:
                            del self._items[index]
                            self._items.append(_coalesce(queued, event))
                            self._condition.notify()
                            return True
                if len(self._items) >= self.maxsize:
                    for index, queued in enumerate(self._items):
                        if _payload(queued).get("type") in COALESCIBLE_TYPES:
                            if _payload(queued).get("type") == "interim_transcript":
                                # A future append may depend on this prefix.
                                # The journal's snapshot holds the complete text.
                                self._needs_resync = True
                                return False
                            del self._items[index]
                            self._items.append(event)
                            self._condition.notify()
                            return True
                    if _payload(event).get("type") == "interim_transcript":
                        self._needs_resync = True
                    return False
                self._items.append(event)
                self._condition.notify()
                return True

            if len(self._items) >= self.maxsize:
                # Final state is already in the session journal. Waiting here
                # would couple a slow UI back into transcript persistence and
                # the audio producer. Signal the per-client sender to replace
                # its stale backlog with a current snapshot instead.
                self._needs_resync = True
                return False
            if self._closed:
                return False
            self._items.append(event)
            self._condition.notify()
            return True

    async def replace_with_snapshot(self, event: dict[str, Any]) -> None:
        """Atomically discard this client's stale backlog for one snapshot."""
        async with self._condition:
            if self._closed:
                return
            self._items.clear()
            self._items.append(event)
            self._needs_resync = False
            self._condition.notify_all()

    async def get(self) -> dict[str, Any]:
        async with self._condition:
            while not self._items and not self._closed:
                await self._condition.wait()
            if not self._items:
                raise asyncio.CancelledError
            event = self._items.popleft()
            self._condition.notify_all()
            return event

    async def close(self) -> None:
        async with self._condition:
            self._closed = True
            self._condition.notify_all()


_journals: dict[str, SessionEventJournal] = {}


def sweep_idle_journals(
    *,
    now: float | None = None,
    idle_ttl_seconds: float = DEFAULT_JOURNAL_IDLE_TTL_SECONDS,
    max_journals: int = DEFAULT_MAX_JOURNALS,
) -> int:
    """Release replay buffers that have no active websocket owner."""
    now = time.monotonic() if now is None else now
    expired = [
        key
        for key, journal in _journals.items()
        if journal.active_connections == 0
        and now - journal._last_touch >= idle_ttl_seconds
    ]
    if len(_journals) - len(expired) > max(1, max_journals):
        remaining = [
            (journal._last_touch, key)
            for key, journal in _journals.items()
            if key not in set(expired) and journal.active_connections == 0
        ]
        remaining.sort()
        needed = len(_journals) - len(expired) - max(1, max_journals)
        expired.extend(key for _, key in remaining[:needed])
    for key in expired:
        _journals.pop(key, None)
    return len(expired)


def _evict_one_idle_journal() -> bool:
    """Evict the least-recently touched idle journal without a full sweep."""
    candidate = min(
        (
            (journal._last_touch, key, journal)
            for key, journal in _journals.items()
            if journal.active_connections == 0
        ),
        default=None,
    )
    if candidate is None:
        return False
    _journals.pop(candidate[1], None)
    return True


def event_journal(session_id: uuid.UUID | str) -> SessionEventJournal:
    key = str(session_id)
    journal = _journals.get(key)
    if journal is not None:
        return journal
    if len(_journals) >= DEFAULT_MAX_JOURNALS:
        # Reserve one slot for the journal being requested.  Without this
        # reservation a registry of exactly max_journals grows by one on every
        # periodic sweep before the over-capacity branch can run.  The direct
        # LRU eviction keeps the 10,000-session path linear instead of doing
        # a full sort over the registry for every new session.
        _evict_one_idle_journal()
    elif len(_journals) % 32 == 0:
        sweep_idle_journals()
    journal = _journals.get(key)
    if journal is None:
        journal = SessionEventJournal(key)
        _journals[key] = journal
    return journal


def latest_session_event(
    session_id: uuid.UUID | str, event_type: str
) -> dict[str, Any] | None:
    journal = _journals.get(str(session_id))
    return journal.latest(event_type) if journal else None


def forget_session(session_id: uuid.UUID | str) -> None:
    """Release the in-process replay journal after a session is deleted.

    Active websocket owners are closed by their route before a session can be
    deleted. Removing the registry entry here prevents a deleted session's
    bounded-but-sensitive replay history from surviving indefinitely.
    """
    _journals.pop(str(session_id), None)
