"""Reveal protected values on the WebSocket path to the interface.

Every live message - transcript lines, insights, signals, briefing updates -
is built by hand somewhere in the orchestrator or the audio handler. Rather
than teach each of them about the vault, the socket handed to them reveals at
the send boundary. Anything not sent through ``send_json`` (binary frames,
close) is delegated untouched.

Reveals are audited in batches: a talking call sends a message every few
seconds, and one audit row per line would say nothing a per-minute row does
not.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid

from app.services.pii import shield, vault
from app.services.provisional_transcripts import persist_provisional_revision
from app.services.ws_event_stream import ClientSendBuffer, event_journal

AUDIT_FLUSH_SECONDS = 60.0


class RevealingWebSocket:
    def __init__(self, inner, session_id: uuid.UUID):
        self._inner = inner
        self._session_id = session_id
        self._pending = 0
        self._last_flush = time.monotonic()
        self._journal = event_journal(session_id)
        self._generation = self._journal.open_generation()
        self._generation_closed = False
        self._send_buffer = ClientSendBuffer(maxsize=256)
        self._drained = asyncio.Event()
        self._drained.set()
        self._sender_error: Exception | None = None
        self._sender_task = asyncio.create_task(self._sender_loop())
        self._transcript_retention_enabled = False

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def set_transcript_retention(self, enabled: bool) -> None:
        self._transcript_retention_enabled = bool(enabled)

    async def send_json(self, data, mode: str = "text") -> None:
        if (
            isinstance(data, dict)
            and data.get("type") == "status"
            and (data.get("data") or {}).get("state") == "completed"
            and not self._journal.is_current_generation(self._generation)
        ):
            # A reconnect owns the session now. A late finalizer from the old
            # socket must not terminate or journal over the new generation.
            return
        if (
            self._transcript_retention_enabled
            and isinstance(data, dict)
            and data.get("type") == "interim_transcript"
        ):
            from app.database import async_session

            async with async_session() as db:
                persisted = await persist_provisional_revision(
                    db,
                    self._session_id,
                    data.get("data") or {},
                )
                if not persisted.created:
                    # Rejected/replayed provisional segments still produce an
                    # append-only discard audit row; commit that audit before
                    # dropping the websocket payload.
                    await db.commit()
                    return
                await db.commit()
        if isinstance(data, (dict, list)) and vault.has_tokens(json.dumps(data, ensure_ascii=False)):
            from app.database import async_session

            async with async_session() as db:
                mapping = await vault.reveal_map(db, self._session_id)
            if mapping:
                data, count = shield._walk(data, mapping)
                self._pending += count
                await self._maybe_flush()
        if isinstance(data, dict):
            data = self._journal.record(data)
        if self._sender_error is not None:
            raise self._sender_error
        self._drained.clear()
        accepted = await self._send_buffer.put({"payload": data, "mode": mode, "type": data.get("type") if isinstance(data, dict) else "raw"})
        if not accepted and self._send_buffer.needs_resync:
            await self._send_buffer.replace_with_snapshot({
                "payload": self._journal.snapshot(0),
                "mode": "text",
                "type": "session_snapshot",
            })
        elif not accepted and not self._send_buffer.qsize():
            self._drained.set()

    async def send_snapshot(
        self,
        after_sequence: int = 0,
        *,
        after_epoch: str | None = None,
    ) -> None:
        """Queue reconnect state without assigning it a new session event id."""
        self._drained.clear()
        await self._send_buffer.replace_with_snapshot({
            "payload": self._journal.snapshot(
                after_sequence,
                after_epoch=after_epoch,
            ),
            "mode": "text",
            "type": "session_snapshot",
        })

    async def close(self, *args, **kwargs):
        await self._flush()
        if self._sender_error is None:
            try:
                await asyncio.wait_for(self._drained.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
        await self._send_buffer.close()
        if not self._sender_task.done():
            self._sender_task.cancel()
        await asyncio.gather(self._sender_task, return_exceptions=True)
        if not self._generation_closed:
            self._generation_closed = True
            self._journal.close_generation(self._generation)
        return await self._inner.close(*args, **kwargs)

    async def _sender_loop(self) -> None:
        try:
            while True:
                queued = await self._send_buffer.get()
                await self._inner.send_json(queued["payload"], queued["mode"])
                if not self._send_buffer.qsize():
                    self._drained.set()
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self._sender_error = exc
            self._drained.set()
            await self._send_buffer.close()

    async def _maybe_flush(self) -> None:
        if self._pending and time.monotonic() - self._last_flush >= AUDIT_FLUSH_SECONDS:
            await self._flush()

    async def _flush(self) -> None:
        if not self._pending:
            return
        count, self._pending = self._pending, 0
        self._last_flush = time.monotonic()
        await shield.record_reveal(self._session_id, "ws", count)
