"""Explicitly confirmed, compact examples for the live debate coach."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from app.services.app_settings import get_app_setting, set_app_setting
from pydantic import BaseModel, Field, field_validator

SETTING_KEY = "debate.confirmed_good_answers"
MAX_EXAMPLES = 24


class GoodDebateExample(BaseModel):
    id: str
    claim: str
    answer: str
    counterargument: str = ""
    mode: str = ""
    style_focus: str = ""
    created_at: str
    feedback_kind: str = "usefulness"
    usefulness_confirmed: bool = True
    factual_status: str = "unverified"
    evidence_sources: list[str] = Field(default_factory=list)
    context: str = ""
    valid_until: str | None = None
    corrections: list[str] = Field(default_factory=list)
    revoked_at: str | None = None
    export_allowed: bool = False

    @field_validator("claim", "answer", "counterargument", "context")
    @classmethod
    def compact_text(cls, value: str) -> str:
        return " ".join(value.split())[:700]


async def load_good_debate_examples(
    db, *, include_revoked: bool = False
) -> list[GoodDebateExample]:
    raw = await get_app_setting(db, SETTING_KEY, "[]")
    try:
        values = json.loads(raw)
    except (TypeError, ValueError):
        return []
    examples: list[GoodDebateExample] = []
    for value in values if isinstance(values, list) else []:
        try:
            example = GoodDebateExample.model_validate(value)
            if not include_revoked and example.revoked_at:
                continue
            if not include_revoked and example.valid_until:
                try:
                    if datetime.fromisoformat(example.valid_until) <= datetime.now(UTC):
                        continue
                except ValueError:
                    continue
            examples.append(example)
        except (TypeError, ValueError):
            continue
    return examples[-MAX_EXAMPLES:]


async def save_good_debate_example(
    db,
    *,
    claim: str,
    answer: str,
    counterargument: str = "",
    mode: str = "",
    style_focus: str = "",
    evidence_sources: list[str] | None = None,
    context: str = "",
    valid_until: str | None = None,
) -> GoodDebateExample:
    examples = await load_good_debate_examples(db)
    example = GoodDebateExample(
        id=str(uuid.uuid4()),
        claim=claim,
        answer=answer,
        counterargument=counterargument,
        mode=mode,
        style_focus=style_focus,
        created_at=datetime.now(UTC).isoformat(),
        feedback_kind="usefulness",
        usefulness_confirmed=True,
        factual_status="unverified",
        evidence_sources=[str(item)[:500] for item in (evidence_sources or [])[:8]],
        context=context,
        valid_until=valid_until,
        export_allowed=False,
    )
    deduplicated = [
        item
        for item in examples
        if item.claim.casefold() != example.claim.casefold()
        or item.answer.casefold() != example.answer.casefold()
    ]
    deduplicated.append(example)
    await set_app_setting(
        db,
        SETTING_KEY,
        json.dumps(
            [item.model_dump(mode="json") for item in deduplicated[-MAX_EXAMPLES:]],
            ensure_ascii=False,
        ),
    )
    return example


async def revoke_good_debate_example(
    db,
    example_id: str,
    *,
    correction: str = "",
) -> bool:
    examples = await load_good_debate_examples(db, include_revoked=True)
    changed = False
    now = datetime.now(UTC).isoformat()
    updated: list[GoodDebateExample] = []
    for example in examples:
        if example.id != example_id:
            updated.append(example)
            continue
        corrections = list(example.corrections)
        if correction.strip():
            corrections.append(" ".join(correction.split())[:700])
        updated.append(
            example.model_copy(
                update={
                    "revoked_at": now,
                    "factual_status": "corrected"
                    if corrections
                    else example.factual_status,
                    "corrections": corrections,
                }
            )
        )
        changed = True
    if changed:
        await set_app_setting(
            db,
            SETTING_KEY,
            json.dumps(
                [item.model_dump(mode="json") for item in updated[-MAX_EXAMPLES:]],
                ensure_ascii=False,
            ),
        )
    return changed
