"""Shared REST/WebSocket/domain contracts for the debate pipeline."""

from typing import Literal

from pydantic import BaseModel, Field


class DebateSource(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    provider: str = ""
    claim: str = ""
    verification_status: Literal[
        "found", "read", "supports", "contradicts", "unclear"
    ] = "found"
    passage: str = ""
    published_at: str = ""
    retrieval_status: Literal["found", "read", "failed"] = "found"
    claim_relation: Literal["supports", "contradicts", "unclear"] = "unclear"
    source_type: str = "web"
    trust_level: Literal["primary", "secondary", "unknown"] = "unknown"
    publisher: str = ""
    retrieved_at: str = ""
    section: str = ""
    content_hash: str = ""
    claim_revision: int = 0
    transcript_revision: int = 0
    claim_id: str = ""
    conflict_group_id: str = ""
    scope_match: Literal["match", "mismatch", "unknown"] = "unknown"
    entailment_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    affected_claim_ids: list[str] = Field(default_factory=list, max_length=12)
    affected_claims: list[str] = Field(default_factory=list, max_length=12)
    numeric_unit: str = ""
    numeric_period: str = ""
    numeric_population: str = ""


class LogicalRelation(BaseModel):
    target_claim_id: str
    relation: Literal[
        "contradicts", "concedes", "counterevidence", "premise", "condition",
        "double_standard", "answers", "topic_shift", "supports",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    verified: bool = False
    source_claim_revision: int = 0
    target_claim_revision: int = 0
    source_span: tuple[int, int] | None = None
    target_span: tuple[int, int] | None = None
    verification_method: Literal["model", "rule", "source", "user"] = "model"
    rationale: str = ""


class AtomicClaim(BaseModel):
    id: str
    parent_claim_id: str
    text: str
    start: int = -1
    end: int = -1
    speaker_id: str = ""
    negated: bool = False
    quantifier: str = ""
    temporal_scope: str = ""
    condition: str = ""
    grouped: bool = False
