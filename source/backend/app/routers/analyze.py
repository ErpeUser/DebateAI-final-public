"""Post-import transcript analysis using the configured analyst model."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Directive, Question, Session, TranscriptEntry
from app.services.agents.prompt_resources import load_prompt_resource
from app.services.briefing_synthesis import agent_model_id, load_agent_configs
from app.services.llm import generate_text
from app.services.meeting_context import build_meeting_context_text
from app.services.transcript_refiner import REFINER_SLUG, refine_session

router = APIRouter(prefix="/api/sessions/{session_id}/analyze", tags=["analyze"])

ANALYZE_TRANSCRIPT_PROMPT = """Analysiere das Transkript auf Deutsch und leite nur kontextgestuetzte Erkenntnisse ab. Unterstelle kein Verkaufs- oder Kundengespraech, wenn Kontext und Transkript das nicht tragen.

## Gespraechskontext
{meeting_context_text}

## Aktive Nutzeranweisungen
{directives_text}

## Transkript
{transcript_text}

Gib ausschliesslich ein gueltiges JSON-Array aus. Erlaubte Eintraege:
- Frage: {{"item_type":"question","question":"...","rationale":"...","source_context":"..."}}
- Beobachtung: {{"item_type":"observation","question":"...","rationale":"...","source_context":"..."}}
- Chance: {{"item_type":"opportunity","question":"...","rationale":"...","source_context":"..."}}
- Aufgabe: {{"item_type":"action_item","question":"...","rationale":"...","source_context":"..."}}
- Beantwortete Frage: {{"item_type":"answered","question":"...","answer_summary":"...","needs_followup":true,"followup_question":"..."}}

Priorisiere wertvolle, belegte Erkenntnisse und aktive Nutzeranweisungen. Kennzeichne vage oder nur teilweise Antworten mit einem Folgepunkt. Erfinde keine Tatsachen und gib keinen Text ausserhalb des JSON-Arrays aus."""


def _parse_items(raw: str) -> list:
    value = raw.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else value[3:]
    if value.endswith("```"):
        value = value[:-3]
    value = value.strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("["), value.rfind("]")
        if start < 0 or end < start:
            raise HTTPException(500, "Analyseergebnis konnte nicht gelesen werden.")
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError as exc:
            raise HTTPException(500, "Analyseergebnis konnte nicht gelesen werden.") from exc
    if not isinstance(parsed, list):
        raise HTTPException(500, "Analyseergebnis ist keine Liste.")
    return parsed


@router.post("")
async def analyze_transcript(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    result = await db.execute(
        select(TranscriptEntry)
        .where(TranscriptEntry.session_id == session_id)
        .order_by(TranscriptEntry.sequence)
    )
    entries = result.scalars().all()
    if not entries:
        raise HTTPException(400, "No transcript entries to analyze")

    refiner_cfg = (await load_agent_configs()).get(REFINER_SLUG)
    if refiner_cfg and refiner_cfg.enabled and refiner_cfg.model_id:
        await refine_session(db, session_id, refiner_cfg.model_id)
        await db.commit()
        result = await db.execute(
            select(TranscriptEntry)
            .where(TranscriptEntry.session_id == session_id)
            .order_by(TranscriptEntry.sequence)
        )
        entries = result.scalars().all()

    directives_result = await db.execute(
        select(Directive.text).where(
            Directive.session_id == session_id,
            Directive.active.is_(True),
        )
    )
    directives = list(directives_result.scalars().all())
    prompt = load_prompt_resource(
        "analyze_transcript", ANALYZE_TRANSCRIPT_PROMPT
    ).format(
        meeting_context_text=build_meeting_context_text(session),
        directives_text="\n".join(f"- {item}" for item in directives) or "(Keine)",
        transcript_text="\n".join(entry.text for entry in entries),
    )
    model_id = await agent_model_id("consolidated_analyst")
    # The SELECTs above open a DB transaction. Release the connection before
    # waiting on a remote/local model; analysis can take minutes and must not
    # hold a pool slot or a database snapshot for the whole inference.
    await db.rollback()
    items = _parse_items(
        await generate_text(model_id, prompt, session_id=session_id, source="analyze")
    )

    # The session may have been deleted or changed while the model was running.
    # Re-read the row before persisting the result instead of mutating an
    # object expired by the rollback or relying on a stale ORM snapshot.
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("item_type", "question")
        question_text = str(item.get("question") or "").strip()
        if not question_text:
            continue
        question = Question(
            session_id=session_id,
            item_type=item_type if item_type != "answered" else "question",
            question=question_text,
            rationale=item.get("rationale", ""),
            source_context=item.get("source_context", ""),
        )
        if item_type == "answered":
            question.answered = True
            question.answer_summary = item.get("answer_summary", "")
            question.needs_followup = item.get("needs_followup", False)
            question.followup_question = item.get("followup_question", "")
        db.add(question)
        count += 1
        if item_type == "answered" and item.get("needs_followup") and item.get("followup_question"):
            db.add(Question(
                session_id=session_id,
                question=item["followup_question"],
                rationale=f"Rueckfrage zu: {question_text}",
                source_context=item.get("answer_summary", ""),
                needs_followup=True,
            ))
            count += 1

    session.state = "completed"
    session.ended_at = datetime.now(timezone.utc)
    session.started_at = session.started_at or datetime.now(timezone.utc)
    await db.commit()
    return {"analyzed": count, "session_id": str(session_id)}
