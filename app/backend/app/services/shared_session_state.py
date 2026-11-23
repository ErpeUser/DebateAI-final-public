"""Database-backed session replay state for multi-worker deployments."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.database import async_session
from app.models import SharedSessionState
from sqlalchemy import delete, select


@dataclass(frozen=True, slots=True)
class SharedJournalSnapshot:
    server_epoch: str
    sequence: int
    generation: int
    active_connections: int
    events: list[dict]
    state: list[dict]


def _snapshot(row: SharedSessionState) -> SharedJournalSnapshot:
    return SharedJournalSnapshot(
        server_epoch=row.server_epoch,
        sequence=row.sequence,
        generation=row.generation,
        active_connections=row.active_connections,
        events=list(row.events or []),
        state=list(row.state or []),
    )


async def open_generation(
    session_id: uuid.UUID,
    *,
    server_epoch: str,
    events: list[dict],
    state: list[dict],
    sequence: int,
) -> SharedJournalSnapshot:
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(
                select(SharedSessionState)
                .where(SharedSessionState.session_id == session_id)
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = SharedSessionState(
                    session_id=session_id,
                    server_epoch=server_epoch,
                    sequence=sequence,
                    generation=1,
                    active_connections=1,
                    events=events,
                    state=state,
                    updated_at=datetime.now(UTC),
                )
                db.add(row)
            else:
                row.generation += 1
                row.active_connections += 1
                row.updated_at = datetime.now(UTC)
            await db.flush()
            return _snapshot(row)


async def save_snapshot(
    session_id: uuid.UUID,
    generation: int,
    *,
    server_epoch: str,
    events: list[dict],
    state: list[dict],
    sequence: int,
) -> bool:
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(
                select(SharedSessionState)
                .where(SharedSessionState.session_id == session_id)
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None or row.generation != generation:
                return False
            row.server_epoch = server_epoch
            row.sequence = sequence
            row.events = events
            row.state = state
            row.updated_at = datetime.now(UTC)
            return True


async def close_generation(session_id: uuid.UUID, generation: int) -> None:
    async with async_session() as db:
        async with db.begin():
            result = await db.execute(
                select(SharedSessionState)
                .where(SharedSessionState.session_id == session_id)
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None or row.generation != generation:
                return
            row.active_connections = max(0, row.active_connections - 1)
            row.updated_at = datetime.now(UTC)


async def forget_session(session_id: uuid.UUID) -> None:
    async with async_session() as db:
        async with db.begin():
            await db.execute(
                delete(SharedSessionState).where(
                    SharedSessionState.session_id == session_id
                )
            )
