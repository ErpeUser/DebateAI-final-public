"""Durable, append-only revisions for live ASR hypotheses."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProvisionalTranscriptRevision, Session
from app.services.pii import shield


# A streaming ASR backend can send many append hypotheses for one logical
# segment. Keep both the human-visible character count and the encoded byte
# count bounded: the former protects prompt/UI consumers while the latter
# protects PostgreSQL/JSON and memory even when a client uses multi-byte text.
MAX_PROVISIONAL_SEGMENT_CHARS = 32_000
MAX_PROVISIONAL_SEGMENT_BYTES = 128_000
MAX_PROVISIONAL_SEGMENT_ID_CHARS = 128
MAX_PROVISIONAL_TRACK_ID_CHARS = 32
_PROVISIONAL_MODES = frozenset({"replace", "append"})


@dataclass(frozen=True)
class PersistedProvisionalRevision:
    row: ProvisionalTranscriptRevision | None
    created: bool


def _within_provisional_limits(text: str) -> bool:
    return (
        len(text) <= MAX_PROVISIONAL_SEGMENT_CHARS
        and len(text.encode("utf-8")) <= MAX_PROVISIONAL_SEGMENT_BYTES
    )


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
    """Build one bounded revision, or return None when it is invalid.

    Append is deliberately rejected once the materialized segment would exceed
    either hard limit. Truncating an ASR hypothesis would make later revisions
    impossible to reason about and could silently change user text.
    """
    if not incoming_text or not incoming_text.strip():
        return None
    if mode not in _PROVISIONAL_MODES:
        return None
    text = (
        f"{previous_text}{incoming_text}"
        if mode == "append"
        else incoming_text.strip()
    )
    return text if _within_provisional_limits(text) else None


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
    if not segment_id or len(segment_id) > MAX_PROVISIONAL_SEGMENT_ID_CHARS:
        return PersistedProvisionalRevision(None, False)

    raw_revision = data.get("segment_revision")
    if isinstance(raw_revision, bool):
        return PersistedProvisionalRevision(None, False)
    try:
        revision = int(raw_revision or 0)
    except (TypeError, ValueError, OverflowError):
        return PersistedProvisionalRevision(None, False)
    if revision <= 0:
        return PersistedProvisionalRevision(None, False)

    incoming_text = str(data.get("text") or "")
    if (
        not incoming_text.strip()
        or not _within_provisional_limits(incoming_text)
    ):
        return PersistedProvisionalRevision(None, False)

    mode = str(data.get("mode") or "replace").strip().lower()
    if mode not in _PROVISIONAL_MODES:
        return PersistedProvisionalRevision(None, False)

    track_id = str(data.get("track_id") or data.get("track") or "mixed").strip()
    if not track_id or len(track_id) > MAX_PROVISIONAL_TRACK_ID_CHARS:
        return PersistedProvisionalRevision(None, False)

    # One short lock serializes revision validation and append materialization.
    # Validate before PII protection so stale/invalid replays do not mint vault
    # entries or spend NER work.
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
    # Revision numbers are strictly increasing per segment. Gaps are allowed
    # because reconnects can legitimately lose an intermediate UI update.
    if latest is not None and revision <= latest.revision:
        return PersistedProvisionalRevision(latest, False)

    protected_text = await shield.protect_text(db, session_id, incoming_text)
    text = materialize_revision_text(
        latest.text if latest is not None else "",
        protected_text,
        mode,
    )
    if text is None:
        return PersistedProvisionalRevision(latest, False)

    row = ProvisionalTranscriptRevision(
        session_id=session_id,
        segment_id=segment_id,
        revision=revision,
        text=text,
        mode=mode,
        track_id=track_id,
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
