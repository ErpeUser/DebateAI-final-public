"""Durable, append-only revisions for live ASR hypotheses."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProvisionalTranscriptRevision, Session
from app.services.pii import shield


@dataclass(frozen=True)
class PersistedProvisionalRevision:
    row: ProvisionalTranscriptRevision | None
    created: bool


def provisional_transcript_payload(
    row: ProvisionalTranscriptRevision,
    *,
    sequence: int,
) -> dict:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "text": row.text,
        "timestamp": row.created_at,
        "sequence": sequence,
        "speaker_id": None,
        "raw_text": None,
        "refined_at": None,
        "provisional": True,
        "utterance_id": row.segment_id,
        "revision": row.revision,
        "track_id": row.track_id,
        "audio_start_sample": row.audio_start_sample,
        "audio_end_sample": row.audio_end_sample,
        "sample_rate": row.sample_rate,
    }


def materialize_revision_text(
    previous_text: str,
    incoming_text: str,
    mode: str,
) -> str | None:
    if not incoming_text or not incoming_text.strip():
        return None
    if mode == "append":
        return f"{previous_text}{incoming_text}"
    return incoming_text.strip()


def should_finalize_provisional(provisional_text: str, final_text: str) -> bool:
    # Segment/audio identity, not text length, proves that this final belongs
    # to the draft. The append-only draft rows remain available for audit.
    del provisional_text
    return bool((final_text or "").strip())


async def persist_provisional_revision(
    db: AsyncSession,
    session_id: uuid.UUID,
    data: dict,
) -> PersistedProvisionalRevision:
    segment_id = str(data.get("segment_id") or "").strip()
    revision = int(data.get("segment_revision") or 0)
    incoming_text = str(data.get("text") or "")
    if not segment_id or revision <= 0 or not incoming_text.strip():
        return PersistedProvisionalRevision(None, False)

    protected_text = await shield.protect_text(db, session_id, incoming_text)
    # One short lock serializes append materialization and makes identical
    # technical replay idempotent under concurrent PostgreSQL writers.
    await db.execute(
        select(Session.id).where(Session.id == session_id).with_for_update()
    )
    existing = (
        await db.execute(
            select(ProvisionalTranscriptRevision).where(
                ProvisionalTranscriptRevision.session_id == session_id,
                ProvisionalTranscriptRevision.segment_id == segment_id,
                ProvisionalTranscriptRevision.revision == revision,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return PersistedProvisionalRevision(existing, False)

    latest = (
        await db.execute(
            select(ProvisionalTranscriptRevision)
            .where(
                ProvisionalTranscriptRevision.session_id == session_id,
                ProvisionalTranscriptRevision.segment_id == segment_id,
            )
            .order_by(ProvisionalTranscriptRevision.revision.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is not None and revision <= latest.revision:
        return PersistedProvisionalRevision(latest, False)

    text = materialize_revision_text(
        latest.text if latest is not None else "",
        protected_text,
        str(data.get("mode") or "replace"),
    )
    if text is None:
        return PersistedProvisionalRevision(latest, False)

    row = ProvisionalTranscriptRevision(
        session_id=session_id,
        segment_id=segment_id,
        revision=revision,
        text=text,
        mode="replace",
        track_id=str(data.get("track_id") or data.get("track") or "mixed"),
        audio_start_sample=(
            int(data["audio_start_sample"])
            if data.get("audio_start_sample") is not None
            else None
        ),
        audio_end_sample=(
            int(data["audio_end_sample"])
            if data.get("audio_end_sample") is not None
            else None
        ),
        sample_rate=int(data.get("sample_rate") or 16000),
    )
    db.add(row)
    await db.flush()
    return PersistedProvisionalRevision(row, True)


async def finalize_provisional_segment(
    db: AsyncSession,
    session_id: uuid.UUID,
    segment_id: str | None,
    final_text: str,
) -> int:
    if not segment_id:
        return 0
    latest = (
        await db.execute(
            select(ProvisionalTranscriptRevision)
            .where(
                ProvisionalTranscriptRevision.session_id == session_id,
                ProvisionalTranscriptRevision.segment_id == segment_id,
                ProvisionalTranscriptRevision.finalized_at.is_(None),
            )
            .order_by(ProvisionalTranscriptRevision.revision.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None or not should_finalize_provisional(latest.text, final_text):
        return 0
    result = await db.execute(
        update(ProvisionalTranscriptRevision)
        .where(
            ProvisionalTranscriptRevision.session_id == session_id,
            ProvisionalTranscriptRevision.segment_id == segment_id,
            ProvisionalTranscriptRevision.finalized_at.is_(None),
        )
        .values(finalized_at=datetime.now(timezone.utc))
    )
    return int(result.rowcount or 0)


async def list_visible_provisional_revisions(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> list[ProvisionalTranscriptRevision]:
    latest = (
        select(
            ProvisionalTranscriptRevision.segment_id.label("segment_id"),
            func.max(ProvisionalTranscriptRevision.revision).label("revision"),
        )
        .where(
            ProvisionalTranscriptRevision.session_id == session_id,
            ProvisionalTranscriptRevision.finalized_at.is_(None),
        )
        .group_by(ProvisionalTranscriptRevision.segment_id)
        .subquery()
    )
    rows = await db.execute(
        select(ProvisionalTranscriptRevision)
        .join(
            latest,
            (ProvisionalTranscriptRevision.segment_id == latest.c.segment_id)
            & (ProvisionalTranscriptRevision.revision == latest.c.revision),
        )
        .where(ProvisionalTranscriptRevision.session_id == session_id)
        .order_by(ProvisionalTranscriptRevision.created_at)
    )
    return list(rows.scalars().all())
