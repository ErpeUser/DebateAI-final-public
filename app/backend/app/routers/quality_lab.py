"""Controlled model/prompt comparison for the Quality Lab UI.

The lab is deliberately a thin orchestration boundary: it validates the same
model registry and privacy rules as the live paths, runs exactly two selected
text candidates, and keeps ratings in a bounded process-local result cache.
Prompt activation is not implied by a model comparison.  The apply/rollback
routes therefore return an explicit conflict until a run contains a real,
validated prompt candidate that can be handed to the prompt optimization store.
"""

from __future__ import annotations

import asyncio
import secrets
import time
import uuid
from collections import OrderedDict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal

from app.database import get_db
from app.models import QualityLabRun
from app.services.custom_endpoints import endpoint_model_entry
from app.services.llm import generate_text, provider_for, registry_entry
from app.services.privacy import LocalOnlyModeError, allows_local_only, is_local_only
from app.services.provider_errors import PROVIDER_ERROR_TYPES, provider_error_to_http
from app.services.quality_lab_holdout import (
    HOLDOUT_DATASET_ID,
    HOLDOUT_VERSION,
    get_case,
    list_cases,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/quality-lab", tags=["quality-lab"])

MAX_RUNS = 128
MAX_CLAIM_CHARS = 4000
MAX_CONTEXT_CHARS = 8000
MAX_SOURCE_CHARS = 2000
MAX_SOURCES = 20
LAB_SOURCE = "quality_lab"
RATING_DIMENSIONS = frozenset(
    {"naturalness", "strength", "precision", "source_honesty", "usability"}
)


class QualityLabRunRequest(BaseModel):
    claim: str = Field(min_length=1, max_length=MAX_CLAIM_CHARS)
    context: str = Field(default="", max_length=MAX_CONTEXT_CHARS)
    allowed_sources: list[str] = Field(default_factory=list, max_length=MAX_SOURCES)
    dataset_id: str = Field(default="interactive", min_length=1, max_length=120)
    holdout: bool = False
    holdout_case_id: str | None = Field(default=None, max_length=120)
    model_ids: list[str] = Field(min_length=2, max_length=2)
    prompt_variants: list[str] = Field(default_factory=list, max_length=2)

    @field_validator("model_ids")
    @classmethod
    def distinct_models(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("Es müssen zwei verschiedene Modell-IDs gewählt werden.")
        return cleaned

    @field_validator("allowed_sources")
    @classmethod
    def bounded_sources(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if any(len(item) > MAX_SOURCE_CHARS for item in cleaned):
            raise ValueError("Quellen dürfen höchstens 2000 Zeichen lang sein.")
        return cleaned

    @field_validator("prompt_variants")
    @classmethod
    def bounded_variants(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if any(len(item) > 2000 for item in cleaned):
            raise ValueError("Promptvarianten dürfen höchstens 2000 Zeichen lang sein.")
        return cleaned


class QualityLabRating(BaseModel):
    ratings: dict[str, dict[str, int | bool | None]]
    preferred: Literal["A", "B", "tie"]
    holdout: bool = False
    dataset_id: str = Field(min_length=1, max_length=120)


class QualityLabApply(BaseModel):
    variant_id: str = Field(min_length=1, max_length=160)


@router.get("/holdouts")
async def list_quality_lab_holdouts():
    return {
        "dataset_id": HOLDOUT_DATASET_ID,
        "version": HOLDOUT_VERSION,
        "cases": list_cases(),
    }


def _prompt_for(request: QualityLabRunRequest, index: int) -> str:
    source_lines = "\n".join(f"- {source}" for source in request.allowed_sources)
    return (
        "Erzeuge eine kurze, sachlich redliche Antwort für das DebateAI-Qualitätslabor. "
        "Gib nur die Antwort aus, keine Meta-Erklärung.\n\n"
        f"Debattenfrage/Claim:\n{request.claim.strip()}\n\n"
        f"Kontext:\n{request.context.strip() or '(kein zusätzlicher Kontext)'}\n\n"
        f"Erlaubte Quellen:\n{source_lines or '(keine Quellen vorgegeben)'}\n"
        + (
            f"\nZusätzliche Promptvariante:\n{request.prompt_variants[index]}\n"
            if index < len(request.prompt_variants)
            else ""
        )
    )


def _candidate(
    *,
    run_id: str,
    index: int,
    model_id: str,
    entry: dict[str, Any],
    answer: str,
    elapsed_ms: float,
    prompt: str,
    source_status: str,
) -> dict[str, Any]:
    variant_id = f"{run_id}:{index}"
    return {
        "variant_id": variant_id,
        "model_id": model_id,
        "prompt_version": "quality-lab-v1",
        "prompt_hash": sha256(prompt.encode("utf-8")).hexdigest(),
        "answer": answer.strip(),
        "latency_ms": round(elapsed_ms, 1),
        # generate_text intentionally exposes no provider billing estimate;
        # returning null is more honest than inventing a price.
        "cost_usd": None,
        "source_status": source_status,
        "available": bool(answer.strip()),
        "model_name": entry.get("name") or model_id,
    }


_RUNS: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _remember(run_id: str, record: dict[str, Any]) -> None:
    _RUNS[run_id] = record
    _RUNS.move_to_end(run_id)
    while len(_RUNS) > MAX_RUNS:
        _RUNS.popitem(last=False)


def _record_from_model(run: QualityLabRun) -> dict[str, Any]:
    return {
        "run_id": run.id.hex,
        "dataset_id": run.dataset_id,
        "holdout": run.holdout,
        "holdout_verified": run.holdout_verified,
        "can_apply": run.can_apply,
        "can_rollback": run.can_rollback,
        "created_at": run.created_at.isoformat(),
        "input": run.input_payload,
        "candidates": run.candidates,
        "blind_order": run.blind_order,
        "ratings": run.ratings,
    }


async def _persist_run(
    db: AsyncSession | object, record: dict[str, Any]
) -> None:
    if not isinstance(db, AsyncSession):
        return
    run = QualityLabRun(
        id=uuid.UUID(record["run_id"]),
        dataset_id=record["dataset_id"],
        holdout=record["holdout"],
        holdout_verified=record["holdout_verified"],
        can_apply=record["can_apply"],
        can_rollback=record["can_rollback"],
        input_payload=record["input"],
        candidates=record["candidates"],
        blind_order=record["blind_order"],
        ratings=record["ratings"],
        created_at=datetime.fromisoformat(record["created_at"]),
    )
    db.add(run)
    await db.commit()


async def _get_run(run_id: str, db: AsyncSession | object) -> dict[str, Any]:
    if isinstance(db, AsyncSession):
        try:
            parsed_id = uuid.UUID(run_id)
        except ValueError as exc:
            raise HTTPException(404, "Laborrunde nicht gefunden oder bereits abgelaufen.") from exc
        run = await db.get(QualityLabRun, parsed_id)
        if run is None:
            raise HTTPException(404, "Laborrunde nicht gefunden oder bereits abgelaufen.")
        return _record_from_model(run)
    record = _RUNS.get(run_id)
    if record is None:
        raise HTTPException(404, "Laborrunde nicht gefunden oder bereits abgelaufen.")
    _RUNS.move_to_end(run_id)
    return record


async def _save_rating(
    run_id: str,
    payload: QualityLabRating,
    record: dict[str, Any],
    db: AsyncSession | object,
) -> None:
    if isinstance(db, AsyncSession):
        try:
            parsed_id = uuid.UUID(run_id)
        except ValueError as exc:
            raise HTTPException(404, "Laborrunde nicht gefunden oder bereits abgelaufen.") from exc
        run = await db.get(QualityLabRun, parsed_id)
        if run is None:
            raise HTTPException(404, "Laborrunde nicht gefunden oder bereits abgelaufen.")
        run.ratings = payload.model_dump()
        await db.commit()
        return
    record["ratings"] = payload.model_dump()


async def _resolve_models(model_ids: list[str], db: AsyncSession) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for model_id in model_ids:
        entry = registry_entry(model_id)
        if entry is None:
            entry = await endpoint_model_entry(db, model_id)
        if not entry or not entry.get("supports_text"):
            raise HTTPException(
                400, f"Modell {model_id} unterstützt keine Textgenerierung."
            )
        if await is_local_only() and not await allows_local_only(model_id):
            raise LocalOnlyModeError("das Qualitätslabor", model_id)
        entries.append(entry)
    return entries


async def _generate_candidate(
    request: QualityLabRunRequest,
    index: int,
    entry: dict[str, Any],
    prompt: str,
    run_id: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        answer = await generate_text(
            request.model_ids[index],
            prompt,
            system="Du bist ein nüchterner Evaluator für DebateAI. Antworte auf Deutsch.",
            source=LAB_SOURCE,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except PROVIDER_ERROR_TYPES as exc:
        raise provider_error_to_http(
            provider_for(request.model_ids[index]),
            exc,
            context="Quality-Lab-Lauf fehlgeschlagen",
        ) from exc
    return _candidate(
        run_id=run_id,
        index=index,
        model_id=request.model_ids[index],
        entry=entry,
        answer=answer,
        elapsed_ms=(time.perf_counter() - started) * 1000,
        prompt=prompt,
        source_status="sources_provided" if request.allowed_sources else "no_sources",
    )


async def _generate_candidates(
    request: QualityLabRunRequest,
    entries: list[dict[str, Any]],
    prompts: list[str],
    run_id: str,
) -> list[dict[str, Any]]:
    tasks = [
        asyncio.create_task(
            _generate_candidate(request, index, entries[index], prompts[index], run_id)
        )
        for index in range(2)
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    failure = next(
        (
            task.exception()
            for task in done
            if not task.cancelled() and task.exception() is not None
        ),
        None,
    )
    if failure is not None:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        raise failure
    await asyncio.gather(*pending)
    return [task.result() for task in tasks]


def _validate_rating_side(side: str, rating: dict[str, int | bool | None]) -> None:
    allowed_keys = RATING_DIMENSIONS | {"both_unsuitable"}
    if set(rating) - allowed_keys:
        raise HTTPException(422, f"Unbekannte Bewertungsdimension für Antwort {side}.")
    both_unsuitable = rating.get("both_unsuitable", False)
    if not isinstance(both_unsuitable, bool):
        raise HTTPException(422, f"both_unsuitable für Antwort {side} muss boolesch sein.")
    if not both_unsuitable and set(rating) != allowed_keys:
        raise HTTPException(422, f"Bewertung für Antwort {side} ist unvollständig.")
    for name, value in rating.items():
        if name == "both_unsuitable":
            continue
        if both_unsuitable and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise HTTPException(422, f"{name} muss zwischen 1 und 5 liegen.")


@router.post("/runs")
async def run_quality_lab(
    request: QualityLabRunRequest,
    db: AsyncSession = Depends(get_db),
):
    holdout_case = get_case(request.holdout_case_id) if request.holdout_case_id else None
    effective_request = request
    if holdout_case is not None:
        effective_request = request.model_copy(
            update={
                "dataset_id": HOLDOUT_DATASET_ID,
                "claim": holdout_case["claim"],
                "context": holdout_case["context"],
                "allowed_sources": holdout_case["allowed_sources"],
            }
        )
    entries = await _resolve_models(effective_request.model_ids, db)
    run_id = uuid.uuid4().hex
    prompts = [_prompt_for(effective_request, index) for index in range(2)]
    candidates = await _generate_candidates(effective_request, entries, prompts, run_id)
    if any(not candidate["available"] for candidate in candidates):
        raise HTTPException(502, "Mindestens ein ausgewähltes Modell lieferte keine Antwort.")
    created_at = datetime.now(UTC).isoformat()
    record = {
        "run_id": run_id,
        "dataset_id": effective_request.dataset_id.strip() or "interactive",
        "holdout": effective_request.holdout,
        # The current source tree has no registered immutable dataset/holdout
        # catalog. Keep the requested flag for the UI, but never label it as a
        # scientific holdout until such a dataset is actually loaded.
        "holdout_verified": bool(holdout_case),
        "can_apply": False,
        "can_rollback": False,
        "created_at": created_at,
        "input": {
            "claim": effective_request.claim.strip(),
            "context": effective_request.context.strip(),
            "allowed_sources": effective_request.allowed_sources,
            "holdout_case_id": holdout_case["case_id"] if holdout_case else None,
        },
        "candidates": candidates,
        "blind_order": ["B", "A"] if secrets.randbelow(2) else ["A", "B"],
        "ratings": None,
    }
    _remember(run_id, record)
    await _persist_run(db, record)
    return {key: value for key, value in record.items() if key != "ratings"}


@router.post("/runs/{run_id}/ratings")
async def submit_quality_lab_rating(
    run_id: str,
    payload: QualityLabRating,
    db: AsyncSession = Depends(get_db),
):
    record = await _get_run(run_id, db)
    if set(payload.ratings) != {"A", "B"}:
        raise HTTPException(422, "Bewertungen für genau die Antworten A und B sind erforderlich.")
    for side in ("A", "B"):
        rating = payload.ratings.get(side)
        if not isinstance(rating, dict):
            raise HTTPException(422, f"Bewertung für Antwort {side} fehlt.")
        _validate_rating_side(side, rating)
    if payload.dataset_id != record["dataset_id"] or payload.holdout != record["holdout"]:
        raise HTTPException(409, "Bewertung gehört zu einer anderen Laborrunde.")
    await _save_rating(run_id, payload, record, db)
    return {"saved": True, "agreement": None}


@router.post("/runs/{run_id}/apply")
async def apply_quality_lab_variant(
    run_id: str,
    payload: QualityLabApply,
    db: AsyncSession = Depends(get_db),
):
    record = await _get_run(run_id, db)
    if not any(item["variant_id"] == payload.variant_id for item in record["candidates"]):
        raise HTTPException(404, "Variante gehört nicht zu dieser Laborrunde.")
    raise HTTPException(
        409,
        "Ein Modellvergleich ist noch keine freigegebene Promptvariante. "
        "Übernehmen ist erst nach einer kontrollierten Prompt-Evaluation möglich.",
    )


@router.post("/runs/{run_id}/rollback")
async def rollback_quality_lab(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_run(run_id, db)
    raise HTTPException(
        409,
        "Für diese Modellvergleichsrunde existiert keine aktivierte Promptvariante.",
    )
