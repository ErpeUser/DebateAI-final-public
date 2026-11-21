"""Contracts for the isolated Experimentell-DebateAI response stream.

The standard debate contract remains unchanged.  This module only describes the
additional structured event that exposes the four experimental moves.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ExperimentalMoveKind = Literal[
    "contradiction",
    "example",
    "counter_question",
    "refutation",
]


class ExperimentalOption(BaseModel):
    id: str
    kind: ExperimentalMoveKind
    title: str
    text: str
    example: str = ""
    rationale: str = ""
    source_ids: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    selected: bool = False
    rank: int = 0
    claim_id: str = ""
    claim_revision: int = 0
    transcript_revision: int = 0
    generation_id: str = ""
    provisional: bool = True


class ExperimentalDebateUpdate(BaseModel):
    session_id: str
    claim_id: str
    claim_revision: int
    transcript_revision: int
    generation_id: str
    options_revision: int
    options: list[ExperimentalOption] = Field(min_length=4, max_length=4)
    selected_option_id: str
    selection_reason: str = ""
    external_insight_count: int = 0
    research_status: str = "idle"
    analysis_status: str = "idle"
    created_at: str = ""
    # The existing debate_update remains the source of truth for old clients.
    recommendation: dict[str, Any] = Field(default_factory=dict)


def build_experimental_update(
    recommendation: Any,
    *,
    external_insight_count: int = 0,
    created_at: str | None = None,
) -> ExperimentalDebateUpdate:
    options = [
        ExperimentalOption.model_validate(option)
        for option in (getattr(recommendation, "strategy_options", None) or [])
    ]
    selected_id = str(getattr(recommendation, "selected_strategy_id", "") or "")
    for option in options:
        option.selected = option.id == selected_id
    return ExperimentalDebateUpdate(
        session_id=str(getattr(recommendation, "session_id", "") or ""),
        claim_id=str(getattr(recommendation, "claim_id", "") or ""),
        claim_revision=int(getattr(recommendation, "claim_revision", 0) or 0),
        transcript_revision=int(getattr(recommendation, "transcript_revision", 0) or 0),
        generation_id=str(getattr(recommendation, "generation_id", "") or ""),
        options_revision=int(
            getattr(recommendation, "recommendation_revision", 0) or 0
        ),
        options=options,
        selected_option_id=selected_id,
        selection_reason=str(getattr(recommendation, "selection_reason", "") or ""),
        external_insight_count=int(external_insight_count),
        research_status=str(
            getattr(recommendation, "research_status", "idle") or "idle"
        ),
        analysis_status=str(
            getattr(recommendation, "analysis_status", "idle") or "idle"
        ),
        created_at=created_at or datetime.now(UTC).isoformat(),
        recommendation=recommendation.model_dump(mode="json"),
    )
