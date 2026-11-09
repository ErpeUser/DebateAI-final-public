import logging
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Speaker, TranscriptEntry, TranscriptEntryRevision
from app.schemas import TranscriptEntryOut, TranscriptEntryRevisionOut
from app.services.pii import shield
from app.services.session_manager import get_next_sequence
from app.services.provisional_transcripts import (
    list_visible_provisional_revisions,
    provisional_transcript_payload,
)
from app.services.transcript_revisions import (
    UNCHANGED,
    apply_manual_transcript_revision,
)
from app.services.agents.orchestrator import get_live_orchestrator

router = APIRouter(prefix="/api/sessions/{session_id}/transcripts", tags=["transcripts"])
logger = logging.getLogger(__name__)


class TranscriptCreate(BaseModel):
    text: str
    speaker_id: uuid.UUID | None = None


class TranscriptUpdate(BaseModel):
    speaker_id: uuid.UUID | None = None
    text: str | None = None
    correction_reason: str = ""


@router.post("", status_code=201)
async def create_transcript(session_id: uuid.UUID, body: TranscriptCreate, db: AsyncSession = Depends(get_db)):
    """Save a transcript entry from the browser's Speech Recognition API."""
    text = await shield.protect_text(db, session_id, body.text)
    seq = await get_next_sequence(session_id, db)
    entry = TranscriptEntry(session_id=session_id, text=text, sequence=seq, speaker_id=body.speaker_id)
    db.add(entry)
    await db.commit()
    return {"ok": True}


@router.get("", response_model=list[TranscriptEntryOut])
async def list_transcripts(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TranscriptEntry)
        .where(TranscriptEntry.session_id == session_id)
        .order_by(TranscriptEntry.sequence)
    )
    entries = list(result.scalars().all())
    provisional = await list_visible_provisional_revisions(db, session_id)
    next_sequence = max((entry.sequence for entry in entries), default=0)
    return [
        *entries,
        *[
            provisional_transcript_payload(row, sequence=next_sequence + index)
            for index, row in enumerate(provisional, start=1)
        ],
    ]


@router.patch("/{transcript_id}", response_model=TranscriptEntryOut)
async def update_transcript(
    session_id: uuid.UUID,
    transcript_id: uuid.UUID,
    body: TranscriptUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a transcript entry's speaker assignment."""
    text: str | object = UNCHANGED
    if "text" in body.model_fields_set:
        if body.text is None or not body.text.strip():
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="Transcript text cannot be empty")
        text = await shield.protect_text(db, session_id, body.text)
    speaker_id: uuid.UUID | None | object = (
        body.speaker_id if "speaker_id" in body.model_fields_set else UNCHANGED
    )
    applied = await apply_manual_transcript_revision(
        db,
        session_id,
        transcript_id,
        text=text,
        speaker_id=speaker_id,
        reason=body.correction_reason,
    )
    entry = applied.entry
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transcript entry not found")
    utterance_id = entry.utterance_id or str(entry.id)
    corrected_utterance_text = entry.text
    if entry.utterance_id:
        related = await db.execute(
            select(TranscriptEntry)
            .where(
                TranscriptEntry.session_id == session_id,
                TranscriptEntry.utterance_id == entry.utterance_id,
            )
            .order_by(TranscriptEntry.sequence)
        )
        corrected_utterance_text = " ".join(
            row.text for row in related.scalars().all() if row.text.strip()
        )
    speaker = await db.get(Speaker, entry.speaker_id) if entry.speaker_id else None
    await db.commit()
    await db.refresh(entry)
    orchestrator = get_live_orchestrator(session_id)
    if applied.revision is not None and orchestrator is not None:
        try:
            speaker_name = None
            if speaker is not None:
                speaker_name = (
                    speaker.display_name
                    if speaker.display_name and speaker.display_name_enabled
                    else speaker.name
                )
            await orchestrator.apply_manual_transcript_correction(
                text=corrected_utterance_text,
                speaker_name=speaker_name,
                speaker_id=str(entry.speaker_id) if entry.speaker_id else None,
                speaker_type=speaker.speaker_type if speaker is not None else None,
                utterance_id=utterance_id,
            )
        except Exception as exc:  # Durable correction must survive a closed live socket.
            logger.warning("Live recommendation invalidation failed: %s", exc)
    return entry


@router.get(
    "/{transcript_id}/revisions",
    response_model=list[TranscriptEntryRevisionOut],
)
async def list_transcript_revisions(
    session_id: uuid.UUID,
    transcript_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(TranscriptEntry, transcript_id)
    if entry is None or entry.session_id != session_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transcript entry not found")
    result = await db.execute(
        select(TranscriptEntryRevision)
        .where(
            TranscriptEntryRevision.session_id == session_id,
            TranscriptEntryRevision.transcript_id == transcript_id,
        )
        .order_by(TranscriptEntryRevision.revision)
    )
    return list(result.scalars().all())
