"""Explicitly confirmed post-debate coaching review."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.database import get_db
from app.models import DebateClaimRecord, Session, Speaker, TranscriptEntry
from app.services.agents.orchestrator import get_live_orchestrator
from app.services.argument_graph import (
    ArgumentGraph,
    correct_source_assignment,
    load_argument_graph,
)
from app.services.briefing_synthesis import agent_model_id
from app.services.debate_contracts import DebateSource
from app.services.debate_review import (
    DebateReview,
    apply_review_suggestion,
    build_review_traces,
    collect_review_sources,
    evaluate_debate,
    get_debate_review,
    parse_diagnostics,
    save_debate_review,
)
from app.services.debate_settings import get_debate_settings, set_debate_settings
from app.services.privacy import allows_local_only, get_local_only
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/api/sessions/{session_id}/debate-review",
    tags=["debate-review"],
)


class ConfirmedAction(BaseModel):
    confirmed: bool = False


class SourceCorrection(BaseModel):
    claim_id: str
    source_url: str
    relation: str
    affected_claim_ids: list[str] = Field(default_factory=list, max_length=12)


async def _completed_session(db: AsyncSession, session_id: uuid.UUID) -> Session:
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.state != "completed":
        raise HTTPException(409, "The debate must be completed first")
    return session


@router.get("", response_model=DebateReview | None)
async def read_review(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _completed_session(db, session_id)
    return await get_debate_review(db, session_id)


@router.get("/argument-graph", response_model=ArgumentGraph)
async def read_argument_graph(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _completed_session(db, session_id)
    return await load_argument_graph(db, session_id)


@router.post("/generate", response_model=DebateReview)
async def generate_review(
    session_id: uuid.UUID,
    action: ConfirmedAction,
    db: AsyncSession = Depends(get_db),
):
    if not action.confirmed:
        raise HTTPException(400, "Manual confirmation is required")
    session = await _completed_session(db, session_id)
    result = await db.execute(
        select(TranscriptEntry)
        .where(TranscriptEntry.session_id == session_id)
        .order_by(TranscriptEntry.sequence, TranscriptEntry.timestamp)
    )
    entries = list(result.scalars().all())
    if not entries:
        raise HTTPException(400, "No transcript is available for review")

    speaker_result = await db.execute(
        select(Speaker).where(Speaker.session_id == session_id)
    )
    speakers = list(speaker_result.scalars().all())
    speaker_types = {speaker.id: speaker.speaker_type for speaker in speakers}
    speaker_names = {
        speaker.id: (
            speaker.display_name
            if speaker.display_name_enabled and speaker.display_name
            else speaker.name
        )
        for speaker in speakers
    }
    transcript = "\n".join(
        f"[{speaker_types.get(entry.speaker_id, 'unknown')}]: {entry.text}"
        for entry in entries
    )
    model_id = await agent_model_id("objection_handler")
    if await get_local_only(db) and not await allows_local_only(model_id):
        raise HTTPException(
            403,
            "Privacy First blocks this review until the Debate Copilot uses a local model.",
        )
    metrics, samples = parse_diagnostics(session.drain_summary)
    review = await evaluate_debate(
        transcript=transcript,
        samples=samples,
        metrics=metrics,
        model_id=model_id,
        session_id=session_id,
    )
    claims_result = await db.execute(
        select(DebateClaimRecord).where(DebateClaimRecord.session_id == session_id)
    )
    graph = await load_argument_graph(db, session_id)
    traces, learning_notes = build_review_traces(
        entries=entries,
        speakers=speaker_names,
        claims=list(claims_result.scalars().all()),
        graph=graph,
        samples=samples,
    )
    review = review.model_copy(
        update={
            "sources": collect_review_sources(samples),
            "traces": traces,
            "learning_notes": learning_notes,
        }
    )
    await save_debate_review(db, session_id, review)
    await db.commit()
    return review


@router.post("/apply", response_model=DebateReview)
async def apply_review(
    session_id: uuid.UUID,
    action: ConfirmedAction,
    db: AsyncSession = Depends(get_db),
):
    if not action.confirmed:
        raise HTTPException(400, "Manual confirmation is required")
    await _completed_session(db, session_id)
    review = await get_debate_review(db, session_id)
    if review is None:
        raise HTTPException(404, "Generate the debate review first")
    current = await get_debate_settings(db)
    await set_debate_settings(db, apply_review_suggestion(current, review))
    applied = review.model_copy(update={"applied_at": datetime.now(UTC).isoformat()})
    await save_debate_review(db, session_id, applied)
    await db.commit()
    return applied


@router.put("/source", response_model=DebateSource)
async def correct_source(
    session_id: uuid.UUID,
    correction: SourceCorrection,
    db: AsyncSession = Depends(get_db),
):
    if correction.relation not in {"supports", "contradicts", "unclear"}:
        raise HTTPException(400, "Invalid source relation")
    if await db.get(Session, session_id) is None:
        raise HTTPException(404, "Session not found")
    try:
        source = await correct_source_assignment(
            db,
            session_id,
            claim_id=correction.claim_id,
            source_url=correction.source_url,
            relation=correction.relation,
            affected_claim_ids=correction.affected_claim_ids,
        )
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    review = await get_debate_review(db, session_id)
    if review is not None:
        review_sources = [
            DebateSource.model_validate(source).model_copy(
                update={
                    "claim_relation": correction.relation,
                    "verification_status": correction.relation,
                    "affected_claim_ids": correction.affected_claim_ids,
                }
            )
            if source.url.rstrip("/") == correction.source_url.rstrip("/")
            else source
            for source in review.sources
        ]
        await save_debate_review(
            db,
            session_id,
            review.model_copy(update={"sources": review_sources}),
        )
    await db.commit()
    orchestrator = get_live_orchestrator(session_id)
    if orchestrator is not None:
        await orchestrator.apply_source_correction(
            claim_id=correction.claim_id,
            source_url=correction.source_url,
            relation=correction.relation,
            affected_claim_ids=correction.affected_claim_ids,
        )
    return DebateSource.model_validate(source)
