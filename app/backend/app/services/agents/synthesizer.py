"""Synthesizer agent — meta-agent for cross-agent reconciliation.

Replaces the current insight_refiner.py refinement loop with enhanced
cross-agent deduplication and reconciliation capabilities.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.services.llm import generate_json
from app.database import async_session
from app.models import Question, Session, Speaker, TranscriptEntry
from app.services.agents.prompts import PRINCIPAL_AGENT_PROMPT
from app.services.agents.prompt_resources import load_prompt_resource
from app.services.agents.signal_insights import SIGNAL_ITEM_TYPES
from app.services.agents.speaker_context import (
    speaker_to_dict as _speaker_dict,
    build_speaker_aliases,
    format_speakers_list,
    format_transcript_segment,
    normalize_speaker_type,
)
from app.services.insight_refiner import _apply_operations
from app.services.meeting_context import build_meeting_context_text, format_prompt_layers

logger = logging.getLogger(__name__)

# Mirrors ASK_ITEM_TYPE in app.routers.ask (ALP-178). Redeclared here rather
# than imported to avoid a services -> routers dependency for one string.
ASKED_ITEM_TYPE = "asked"


class SynthesizerOperation(BaseModel):
    op: str
    id: str | None = None
    keep_id: str | None = None
    remove_id: str | None = None
    answer_summary: str | None = None
    needs_followup: bool | None = None
    followup: str | None = None
    additional_context: str | None = None
    reason: str | None = None
    new_type: str | None = None
    new_text: str | None = None
    new_rationale: str | None = None
    new_source_context: str | None = None
    new_answer_summary: str | None = None
    new_followup_question: str | None = None
    new_followup: str | None = None
    new_offering_match: str | None = None
    offering_match: str | None = None
    followup_question: str | None = None
    item_type: str | None = None
    question: str | None = None
    rationale: str | None = None
    source_context: str | None = None
    merged_text: str | None = None


class SynthesizerOutput(BaseModel):
    items: list[SynthesizerOperation]


# An insight earns a full record while it is still live: starred, or unanswered
# and touched recently. Everything else is settled and appears as a compact stub
# so merge/answer operations can still target it by id without paying for its
# full backstory on every cycle. Sending the whole corpus in full made this
# agent 48 percent of a measured meeting's token bill, growing quadratically
# with call length (ALP-283).
_STUB_TEXT_CHARS = 110
_ENRICHMENT_NOTE_CHARS = 200
_INSIGHTS_JSON_BUDGET_CHARS = 18000
# Keep the whole insight array bounded; individual fields are truncated above,
# but long meetings can otherwise accumulate an unbounded number of settled rows.
SYNTHESIZER_INSIGHTS_JSON_BUDGET_CHARS = 18000

# Last (insights + transcript) fingerprint per session, so an unchanged corpus
# skips the call. Cleared by clear_session_state when the call ends.
_last_fingerprints: dict[uuid.UUID, str] = {}


def clear_synthesizer_state(session_id: uuid.UUID) -> None:
    """Drop the per-session skip fingerprint when a call finishes."""
    _last_fingerprints.pop(session_id, None)


def _touched_at(q: Question) -> datetime | None:
    stamp = q.updated_at or q.created_at
    if stamp is not None and stamp.tzinfo is None:
        return stamp.replace(tzinfo=timezone.utc)
    return stamp


def _in_working_set(q: Question, cutoff: datetime) -> bool:
    """Whether this insight still needs its full record in the prompt."""
    if q.starred:
        return True
    if q.answered:
        return False
    touched = _touched_at(q)
    return touched is None or touched >= cutoff


def _truncate(text: str | None, limit: int) -> str:
    value = (text or "").strip()
    return value if len(value) <= limit else value[:limit].rstrip() + "..."


def _truncate_tail(text: str | None, limit: int) -> str:
    """Keep the END of a value that grows by appending.

    _truncate keeps the head, which is right for an insight's text - the
    opening words identify it. It is wrong for enrichment notes, because
    _append_note in insight_refiner appends to the tail: past the limit the
    model was shown only its OLDEST notes and could never see what it wrote
    last cycle, so it had no signal that it had already enriched an insight
    (ALP-297).
    """
    value = (text or "").strip()
    return value if len(value) <= limit else "..." + value[-limit:].lstrip()


def _full_record(q: Question) -> dict:
    """A live insight: everything the operations can actually reason about.

    Deliberately omits source_context (raw quote material no operation can
    write), the standalone speaker_id, and the rendered speaker line, which
    repeated the same UUID a second time. The prompt only ever reasons about
    speaker_type.
    """
    item = {
        "id": str(q.id),
        "item_type": q.item_type,
        "text": q.question,
        "rationale": q.rationale or "",
        "agent_source": q.agent_source,
    }
    if q.speaker is not None:
        item["speaker_type"] = normalize_speaker_type(q.speaker.speaker_type)
    if q.answered:
        item["answered"] = True
        if q.answer_summary:
            item["answer_summary"] = q.answer_summary
    if q.starred:
        item["starred"] = True
    if q.enrichment_notes:
        item["enrichment_notes"] = _truncate_tail(q.enrichment_notes, _ENRICHMENT_NOTE_CHARS)
    return item


def _stub_record(q: Question) -> dict:
    """A settled insight: enough to recognize it and target it by id."""
    return {
        "id": str(q.id),
        "item_type": q.item_type,
        "text": _truncate(q.question, _STUB_TEXT_CHARS),
        "answered": bool(q.answered),
        "settled": True,
    }


def _build_insights_json(
    questions: list[Question],
    now: datetime | None = None,
    budget: int = SYNTHESIZER_INSIGHTS_JSON_BUDGET_CHARS,
) -> str:
    """Serialize a compact, bounded corpus for the synthesizer prompt.

    Records stay ordered by creation for deterministic fingerprints. When the
    corpus exceeds the budget, newest records are admitted first and rendered
    back in chronological order so the agent retains recent context without
    sending an unbounded JSON array to ChatGPT Web.
    """
    window = max(0, int(getattr(settings, "SYNTHESIZER_WORKING_SET_SECONDS", 600)))
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(seconds=window)
    items = [
        _full_record(q) if _in_working_set(q, cutoff) else _stub_record(q)
        for q in questions
    ]
    budget = max(128, int(budget))
    rendered = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    if len(rendered) <= budget:
        return rendered

    kept: list[dict] = []
    for item in reversed(items):
        candidate = [item, *kept]
        candidate_rendered = json.dumps(
            candidate,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if len(candidate_rendered) > budget:
            if not kept:
                # The normal field-level limits make this rare, but preserve
                # one addressable row when a caller passes a tiny test budget.
                clipped = {
                    key: (value[: max(0, budget // 4)] + "...")
                    if isinstance(value, str)
                    else value
                    for key, value in item.items()
                }
                candidate_rendered = json.dumps(
                    [clipped],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                if len(candidate_rendered) <= budget:
                    return candidate_rendered
            break
        kept = candidate
    return json.dumps(kept, ensure_ascii=False, separators=(",", ":"))


def _format_transcript_entries(
    entries: list[TranscriptEntry],
    aliases: dict[str, str] | None = None,
) -> str:
    lines = []
    for entry in entries:
        speaker = _speaker_dict(entry.speaker) if entry.speaker else None
        lines.append(format_transcript_segment(
            entry.text,
            speaker.get("name") if speaker else "Unknown",
            speaker_id=str(entry.speaker_id) if entry.speaker_id else None,
            speaker_type=speaker.get("speaker_type") if speaker else None,
            alias=(aliases or {}).get(str(entry.speaker_id or "")),
        ))
    return "\n".join(lines) if lines else "(No transcript yet)"


async def run_synthesizer_cycle(session_id: uuid.UUID, model_override: str | None = None, prompt_override: str | None = None) -> list[dict]:
    """Execute one synthesizer cycle. Returns list of applied operations."""
    async with async_session() as db:
        session = await db.get(Session, session_id)
        meeting_context_text = build_meeting_context_text(session)

        result = await db.execute(
            select(Question).where(
                Question.session_id == session_id,
                Question.dismissed.is_(False),
                # The operator's own live-chat Q&A is a private read, not
                # agent material: excluded so the Principal Agent cannot
                # dismiss, adjust, or elevate an answer it did not produce.
                Question.item_type != ASKED_ITEM_TYPE,
                # Strategic signals are owned by their own agent, which
                # rewrites them every cycle. Reconciling them here would have
                # two agents editing the same rows in opposite directions.
                Question.item_type.notin_(SIGNAL_ITEM_TYPES),
            )
            # Deterministic order: without it the payload is not byte-stable
            # between cycles, so no prompt cache can ever hit (ALP-285).
            .order_by(Question.created_at, Question.id)
            .options(selectinload(Question.speaker))
        )
        questions = list(result.scalars().all())

        if not questions:
            return []

        # Load recent transcript (~5 min window)
        result = await db.execute(
            select(TranscriptEntry)
            .where(TranscriptEntry.session_id == session_id)
            .options(selectinload(TranscriptEntry.speaker))
            .order_by(TranscriptEntry.sequence.desc())
            .limit(30)
        )
        entries = list(reversed(result.scalars().all()))

        # The roster in its canonical order, which is what the alias map is
        # derived from. Ordered by created_at like every other loader, so a
        # rebuilt orchestrator on a resumed call produces the same map.
        roster = (
            await db.execute(
                select(Speaker).where(Speaker.session_id == session_id).order_by(Speaker.created_at)
            )
        ).scalars().all()
        roster_dicts = [_speaker_dict(s) for s in roster]
        aliases = build_speaker_aliases(roster_dicts)
        speaker_legend = format_speakers_list(roster_dicts, aliases)

    transcript_text = _format_transcript_entries(entries, aliases)
    insights_json = _build_insights_json(questions)

    # Nothing new to reconcile since the last cycle: skip the call entirely.
    # The transcript is deliberately part of this fingerprint because the
    # synthesizer detects answers spoken after an insight was created.
    fingerprint = hashlib.sha256(
        f"{insights_json}\x00{transcript_text}".encode("utf-8")
    ).hexdigest()
    if _last_fingerprints.get(session_id) == fingerprint:
        logger.debug("[synthesizer] corpus and transcript unchanged, skipping cycle")
        return []

    prompt_template = load_prompt_resource(
        "agent.synthesizer", prompt_override or PRINCIPAL_AGENT_PROMPT
    )
    system, prompt = format_prompt_layers(
        prompt_template,
        meeting_context_text,
        insights_json=insights_json,
        transcript_text=transcript_text,
    )
    # The synthesizer template predates the shared transcript alias contract.
    # Bind aliases once in a compact legend so [S1] references in operations
    # remain attributable without repeating identities on every transcript line.
    prompt = f"{prompt}\n\nParticipants (alias legend):\n{speaker_legend}"

    model_id = settings.REFINEMENT_MODEL if model_override is None else model_override

    try:
        output = await generate_json(
            model_id,
            prompt,
            SynthesizerOutput,
            session_id=session_id,
            source="synthesizer",
            system=system,
        )
    except Exception as e:
        logger.error(f"[synthesizer] API call failed: {e}")
        return []

    # Structured output (generate_json + SynthesizerOutput) replaced the hand
    # rolled fence-strip and bracket-scan recovery this commit originally
    # carried; llm.parse_json_response now tolerates fences centrally.
    ops = [item.model_dump(exclude_unset=True) for item in output.items]

    # Do not mark this corpus as processed until the database operations commit.
    # A transient commit failure must leave the fingerprint retryable.
    applied = await _apply_operations(session_id, ops, questions, agent_source="synthesizer")
    _last_fingerprints[session_id] = fingerprint
    return applied
