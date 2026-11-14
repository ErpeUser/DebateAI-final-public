"""Transactional append-only corrections for durable transcript entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TranscriptEntry, TranscriptEntryRevision

UNCHANGED = object()


async def append_refiner_revision(
    db: AsyncSession,
    session_id: uuid.UUID,
    entry: TranscriptEntry,
    *,
    original_text: str,
    reason: str = "Transcript refiner correction",
) -> TranscriptEntryRevision:
    """Append an explicit refiner revision without advancing claim revisions.

    ``TranscriptEntry.raw_text`` is the ASR source of truth. When older data
    predates the append-only history, seed that source as revision 1 before
    adding the refiner row. The live orchestrator never consumes this counter
    as a claim/transcript revision; it is transcript history only.
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
    entry.manual_corrected_at = datetime.now(timezone.utc)
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
