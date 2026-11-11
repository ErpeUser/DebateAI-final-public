"""Deterministic response/event contract for DebateAI experiments.

This module is independent of the live orchestrator and database. It validates
lineage, timing and failure states at replay/laboratory boundaries without
pretending to prove semantic truth.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from math import isfinite
from typing import Any, Mapping

SCHEMA_VERSION = 1
STATUSES = frozenset({"ok", "timeout", "empty", "stale", "error", "abstent"})
FAILURE_CLASSES = frozenset({
    "none", "timeout", "empty", "stale", "error", "provider", "parse", "privacy",
    "cancelled", "resource", "unknown",
})
LATENCY_FIELDS = (
    "first_speakable_ms", "first_update_ms", "final_update_ms",
    "deep_revision_ms", "accepted_model_ms",
)


class ResponseContractError(ValueError):
    """Raised when a replay/result cannot be trusted as a contract record."""


@dataclass(frozen=True, slots=True)
class ResponseEvent:
    case_id: str
    turn_id: str
    status: str = "ok"
    failure_class: str = "none"
    schema_version: int = SCHEMA_VERSION
    claim_id: str | None = None
    revision_of: str | None = None
    transcript_revision: int | None = None
    prompt_hash: str | None = None
    model_id: str | None = None
    model_revision: str | None = None
    provider_kind: str | None = None
    source_passage_id: str | None = None
    source_hash: str | None = None
    retrieved_at: str | None = None
    valid_time: str | None = None
    population: str | None = None
    unit: str | None = None
    first_speakable_ms: float | None = None
    first_update_ms: float | None = None
    final_update_ms: float | None = None
    deep_revision_ms: float | None = None
    accepted_model_ms: float | None = None
    queue_depth: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self) if getattr(self, field.name) is not None}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ResponseEvent":
        normalized = normalize_response_event(value)
        names = {field.name for field in fields(cls)}
        return cls(**{name: normalized.get(name) for name in names})


def _text(value: Any, field: str, *, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ResponseContractError(f"{field} must be a non-empty string")
    if len(value) > 512:
        raise ResponseContractError(f"{field} exceeds the contract length limit")
    return value.strip()


def _latency(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResponseContractError(f"{field} must be a finite non-negative number")
    result = float(value)
    if not isfinite(result) or result < 0:
        raise ResponseContractError(f"{field} must be a finite non-negative number")
    return result


def normalize_response_event(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one replay/laboratory response event.

    Unknown keys are preserved for forward compatibility. Deterministic checks
    cover shape, lineage, timing and failure state; they do not classify truth.
    """
    if not isinstance(value, Mapping):
        raise ResponseContractError("response event must be a mapping")
    case_id = _text(value.get("case_id"), "case_id", required=True)
    turn_id = _text(value.get("turn_id"), "turn_id", required=True)
    status = value.get("status", "ok")
    failure_class = value.get("failure_class", "none")
    if not isinstance(status, str) or status not in STATUSES:
        raise ResponseContractError(f"unsupported status: {status!r}")
    if not isinstance(failure_class, str) or failure_class not in FAILURE_CLASSES:
        raise ResponseContractError(f"unsupported failure_class: {failure_class!r}")
    schema_version = value.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ResponseContractError(f"unsupported schema_version: {schema_version!r}")
    claim_id = _text(value.get("claim_id"), "claim_id")
    revision_of = _text(value.get("revision_of"), "revision_of")
    if revision_of is not None and claim_id is None:
        raise ResponseContractError("revision_of requires claim_id")
    if status == "ok" and failure_class != "none":
        raise ResponseContractError("ok events must use failure_class=none")
    if status != "ok" and failure_class == "none":
        failure_class = status
    transcript_revision = value.get("transcript_revision")
    if transcript_revision is not None and (
        isinstance(transcript_revision, bool) or not isinstance(transcript_revision, int) or transcript_revision < 0
    ):
        raise ResponseContractError("transcript_revision must be a non-negative integer")
    queue_depth = value.get("queue_depth")
    if queue_depth is not None and (
        isinstance(queue_depth, bool) or not isinstance(queue_depth, int) or queue_depth < 0
    ):
        raise ResponseContractError("queue_depth must be a non-negative integer")
    result = dict(value)
    result.update({
        "schema_version": SCHEMA_VERSION, "case_id": case_id, "turn_id": turn_id,
        "status": status, "failure_class": failure_class, "claim_id": claim_id,
        "revision_of": revision_of, "transcript_revision": transcript_revision,
        "queue_depth": queue_depth,
    })
    for field in LATENCY_FIELDS:
        result[field] = _latency(value.get(field), field)
    if (result["first_update_ms"] is not None and result["final_update_ms"] is not None
            and result["final_update_ms"] < result["first_update_ms"]):
        raise ResponseContractError("final_update_ms cannot precede first_update_ms")
    return result


def validate_response_event(value: Mapping[str, Any]) -> None:
    """Raise ResponseContractError unless *value* satisfies the contract."""
    normalize_response_event(value)
