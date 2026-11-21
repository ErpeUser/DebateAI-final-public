"""Transactional append-only corrections for durable transcript entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import TranscriptEntry, TranscriptEntryRevision
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

UNCHANGED = object()


@dataclass(frozen=True)
class AppliedTranscriptRevision:
    entry: TranscriptEntry | None
    revision: TranscriptEntryRevision | None


async def append_refiner_revision(
    db: AsyncSession,
    session_id: uuid.UUID,
    entry: TranscriptEntry,
    *,
    original_text: str,
    reason: str = "Transcript refiner correction",
) -> TranscriptEntryRevision:
    """Append a transcript-only refiner revision.

    ``raw_text`` is the ASR source of truth. If older data has no history
    rows yet, seed that source as revision 1 before adding the refiner row.
    This counter is transcript history only; the live orchestrator's claim
    and transcript revisions are intentionally untouched.
    """
    current_revision = int(
        await db.scalar(
            select(func.max(TranscriptEntryRevision.revision)).where(
                TranscriptEntryRevision.transcript_id == entry.id
            )
        )
        or 0
    )
    if current_revision == 0:
        db.add(
            TranscriptEntryRevision(
                session_id=session_id,
                transcript_id=entry.id,
                revision=1,
                text=str(original_text),
                speaker_id=entry.speaker_id,
                source="original",
                reason="",
            )
        )
        current_revision = 1
    revision = TranscriptEntryRevision(
        session_id=session_id,
        transcript_id=entry.id,
        revision=current_revision + 1,
        text=entry.text,
        speaker_id=entry.speaker_id,
        source="refiner",
        reason=" ".join(reason.split())[:500],
    )
    db.add(revision)
    await db.flush()
    return revision


async def apply_manual_transcript_revision(
    db: AsyncSession,
    session_id: uuid.UUID,
    transcript_id: uuid.UUID,
    *,
    text: str | object = UNCHANGED,
    speaker_id: uuid.UUID | None | object = UNCHANGED,
    reason: str = "",
) -> AppliedTranscriptRevision:
    entry = (
        await db.execute(
            select(TranscriptEntry)
            .where(
                TranscriptEntry.id == transcript_id,
                TranscriptEntry.session_id == session_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if entry is None:
        return AppliedTranscriptRevision(None, None)

    next_text = entry.text if text is UNCHANGED else str(text).strip()
    next_speaker = entry.speaker_id if speaker_id is UNCHANGED else speaker_id
    if not next_text:
        raise ValueError("Transcript text cannot be empty")
    if next_text == entry.text and next_speaker == entry.speaker_id:
        return AppliedTranscriptRevision(entry, None)

    current_revision = int(
        await db.scalar(
            select(func.max(TranscriptEntryRevision.revision)).where(
                TranscriptEntryRevision.transcript_id == transcript_id
            )
        )
        or 0
    )
    if current_revision == 0:
        original_text = str(entry.raw_text or entry.text)
        db.add(
            TranscriptEntryRevision(
                session_id=session_id,
                transcript_id=transcript_id,
                revision=1,
                text=original_text,
                speaker_id=entry.speaker_id,
                source="original",
                reason="",
            )
        )
        current_revision = 1
        if entry.raw_text and str(entry.raw_text).strip() != str(entry.text).strip():
            db.add(
                TranscriptEntryRevision(
                    session_id=session_id,
                    transcript_id=transcript_id,
                    revision=2,
                    text=entry.text,
                    speaker_id=entry.speaker_id,
                    source="refiner",
                    reason="Transcript refiner correction",
                )
            )
            current_revision = 2

    if next_text != entry.text:
        if entry.raw_text is None:
            entry.raw_text = entry.text
        entry.text = next_text
    entry.speaker_id = next_speaker
    entry.manual_corrected_at = datetime.now(UTC)
    revision = TranscriptEntryRevision(
        session_id=session_id,
        transcript_id=transcript_id,
        revision=current_revision + 1,
        text=entry.text,
        speaker_id=entry.speaker_id,
        source="manual",
        reason=" ".join(reason.split())[:500],
    )
    db.add(revision)
    await db.flush()
    return AppliedTranscriptRevision(entry, revision)
