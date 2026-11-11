"""Post-import transcript analysis using the configured analyst model."""

import json
import inspect
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

MAX_ANALYZE_TRANSCRIPT_CHARS = 120_000
MAX_ANALYZE_DIRECTIVES_CHARS = 16_000
MAX_ANALYZE_RESPONSE_CHARS = 500_000
MAX_ANALYZE_ITEMS = 256
_ALLOWED_ITEM_TYPES = {"question", "observation", "opportunity", "action_item", "answered"}

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


def _clip_context(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    head = max(1, (limit - 64) // 2)
    tail = max(1, limit - 64 - head)
    return f"{value[:head]}\n[...context truncated...]\n{value[-tail:]}"


def _bounded_field(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _parse_items(raw: str) -> list:
    if len(raw) > MAX_ANALYZE_RESPONSE_CHARS:
        raise HTTPException(502, "Analyseergebnis ist zu gross.")
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
        meeting_context_text=_clip_context(build_meeting_context_text(session), MAX_ANALYZE_DIRECTIVES_CHARS),
        directives_text=_clip_context(
            "\n".join(f"- {item}" for item in directives) or "(Keine)",
            MAX_ANALYZE_DIRECTIVES_CHARS,
        ),
        transcript_text=_clip_context(
            "\n".join(entry.text for entry in entries),
            MAX_ANALYZE_TRANSCRIPT_CHARS,
        ),
    )
    model_id = await agent_model_id("consolidated_analyst")
    # The SELECTs above open a DB transaction. Release the connection before
    # waiting on a remote/local model; analysis can take minutes and must not
    # hold a pool slot or a database snapshot for the whole inference.
    rollback = getattr(db, "rollback", None)
    if rollback is not None:
        rollback_result = rollback()
        if inspect.isawaitable(rollback_result):
            await rollback_result
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
    for item in items[:MAX_ANALYZE_ITEMS]:
        if count >= MAX_ANALYZE_ITEMS:
            break
        if not isinstance(item, dict):
            continue
        item_type = _bounded_field(item.get("item_type", "question"), 40)
        if item_type not in _ALLOWED_ITEM_TYPES:
            item_type = "question"
        question_text = _bounded_field(item.get("question"), 4000)
        if not question_text:
            continue
        question = Question(
            session_id=session_id,
            item_type="question" if item_type == "answered" else item_type,
            question=question_text,
            rationale=_bounded_field(item.get("rationale"), 8000),
            source_context=_bounded_field(item.get("source_context"), 8000),
        )
        if item_type == "answered":
            question.answered = True
            question.answer_summary = _bounded_field(item.get("answer_summary"), 8000)
            question.needs_followup = bool(item.get("needs_followup", False))
            question.followup_question = _bounded_field(item.get("followup_question"), 4000)
        db.add(question)
        count += 1
        if (
            count < MAX_ANALYZE_ITEMS
            and item_type == "answered"
            and item.get("needs_followup")
            and item.get("followup_question")
        ):
            db.add(Question(
                session_id=session_id,
                question=_bounded_field(item.get("followup_question"), 4000),
                rationale=f"Rueckfrage zu: {question_text}",
                source_context=_bounded_field(item.get("answer_summary"), 8000),
                needs_followup=True,
            ))
            count += 1

    session.state = "completed"
    session.ended_at = datetime.now(timezone.utc)
    session.started_at = session.started_at or datetime.now(timezone.utc)
    await db.commit()
    return {"analyzed": count, "session_id": str(session_id)}
