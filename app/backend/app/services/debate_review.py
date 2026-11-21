"""Manual, locally persisted coaching review for a completed debate.

The model may recommend only enumerated settings. It never writes prompts or
changes configuration directly; the separate apply action is the confirmation
boundary.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal

from app.services.agents.prompt_resources import load_prompt_resource
from app.services.app_settings import get_app_setting, set_app_setting
from app.services.debate_contracts import DebateSource
from app.services.debate_settings import DebateSettings
from app.services.llm import generate_json
from pydantic import BaseModel, Field, field_validator


class DebateImprovement(BaseModel):
    issue: str = ""
    example: str = ""
    better: str = ""

    @field_validator("issue", "example", "better")
    @classmethod
    def keep_feedback_compact(cls, value: str) -> str:
        return " ".join(value.split()[:35])


class DebateReviewDraft(BaseModel):
    summary: str = ""
    strengths: list[str] = Field(default_factory=list, max_length=3)
    improvements: list[DebateImprovement] = Field(default_factory=list, max_length=5)
    source_quality: str = ""
    suggested_style_focus: Literal["balanced", "natural", "concise", "evidence"] = (
        "balanced"
    )
    suggested_mode: Literal["persuasive", "forceful"] = "persuasive"
    suggested_research_frequency: Literal["low", "normal", "often"] = "normal"
    suggested_always_analogy: bool = True


class DebateReviewMetrics(BaseModel):
    recommendations: int = 0
    average_latency_ms: int = 0
    maximum_latency_ms: int = 0
    average_answer_words: float = 0
    average_question_words: float = 0


class DebateReviewSource(DebateSource):
    pass


class DebateReviewTrace(BaseModel):
    category: Literal[
        "open_question",
        "unsupported_claim",
        "corrected_statement",
        "concession",
        "late_recommendation",
    ]
    title: str = ""
    explanation: str = ""
    transcript_quote: str = ""
    speaker: str = ""
    timestamp: str = ""
    claim_id: str = ""
    recommendation: str = ""
    latency_ms: int = 0


class DebateReview(DebateReviewDraft):
    metrics: DebateReviewMetrics = Field(default_factory=DebateReviewMetrics)
    sources: list[DebateReviewSource] = Field(default_factory=list, max_length=20)
    traces: list[DebateReviewTrace] = Field(default_factory=list, max_length=40)
    learning_notes: list[str] = Field(default_factory=list, max_length=12)
    generated_at: str = ""
    applied_at: str = ""


def _transcript_reference(
    entries: list,
    text: str,
    speakers: dict,
    *,
    claim_id: str,
) -> tuple[str, str, str]:
    """Resolve a review trace only through durable transcript identity."""
    matching = [
        entry
        for entry in entries
        if claim_id
        and claim_id
        in {
            str(getattr(entry, "utterance_id", "") or ""),
            str(getattr(entry, "id", "") or ""),
        }
    ]
    if not matching:
        return text[:500], "", ""
    best = max(
        matching,
        key=lambda entry: (
            int(getattr(entry, "producer_revision", 0) or 0),
            int(getattr(entry, "sequence", 0) or 0),
        ),
    )
    quote = str(getattr(best, "raw_text", None) or best.text)[:500]
    speaker = speakers.get(getattr(best, "speaker_id", None), "Unbekannt")
    timestamp = getattr(best, "timestamp", None)
    return quote, str(speaker), timestamp.isoformat() if timestamp else ""


def _late_recommendation_reason(sample: dict, latency: int) -> str | None:
    """Judge whether advice missed its moment, not a fixed stopwatch."""
    if latency < 3000 or sample.get("ui_acknowledged"):
        return None
    if sample.get("superseded_before_delivery") or sample.get(
        "topic_changed_before_delivery"
    ):
        return "The relevant conversation turn had already changed before delivery."
    origin = str(sample.get("origin") or "model")
    materially_enriched = bool(sample.get("sources")) or (
        sample.get("analysis_status") == "completed"
        and bool(sample.get("analyst_model") or sample.get("argument_points"))
    )
    if origin == "research" and materially_enriched:
        return None
    return f"The recommendation was still neither visible nor acknowledged after {latency} ms."


def build_review_traces(
    *,
    entries: list,
    speakers: dict,
    claims: list,
    graph,
    samples: list[dict],
) -> tuple[list[DebateReviewTrace], list[str]]:
    """Derive auditable learning traces without inventing a win/loss score."""
    traces: list[DebateReviewTrace] = []
    claim_nodes = {node.claim_id: node for node in graph.nodes if node.kind == "claim"}

    for node in graph.nodes:
        if node.kind != "question" or node.status not in {
            "",
            "open",
            "partial",
            "unclear",
            "evaded",
        }:
            continue
        claim = claim_nodes.get(node.claim_id)
        quote, speaker, timestamp = _transcript_reference(
            entries,
            claim.text if claim else node.text,
            speakers,
            claim_id=node.claim_id,
        )
        traces.append(
            DebateReviewTrace(
                category="open_question",
                title=node.text,
                explanation=f"Status: {node.status or 'offen'}; im Gespräch nicht belastbar geklärt.",
                transcript_quote=quote,
                speaker=speaker,
                timestamp=timestamp,
                claim_id=node.claim_id,
            )
        )

    newest_claims = {}
    for claim in claims:
        previous = newest_claims.get(claim.claim_id)
        if previous is None or claim.revision > previous.revision:
            newest_claims[claim.claim_id] = claim
    for claim in newest_claims.values():
        sources = [
            source for source in (claim.sources or []) if isinstance(source, dict)
        ]
        supported = any(
            source.get("claim_relation") == "supports"
            or source.get("verification_status") in {"verified", "supports"}
            for source in sources
        )
        if not supported:
            quote, speaker, timestamp = _transcript_reference(
                entries, claim.original_text, speakers, claim_id=claim.claim_id
            )
            traces.append(
                DebateReviewTrace(
                    category="unsupported_claim",
                    title=claim.original_text[:500],
                    explanation="Für diese Behauptung ist kein bestätigender Beleg im gespeicherten Quellenstand verknüpft.",
                    transcript_quote=quote,
                    speaker=speaker,
                    timestamp=timestamp,
                    claim_id=claim.claim_id,
                )
            )
        corrections = (claim.feedback or {}).get("source_corrections", [])
        for correction in corrections[-3:]:
            if not isinstance(correction, dict):
                continue
            quote, speaker, timestamp = _transcript_reference(
                entries, claim.original_text, speakers, claim_id=claim.claim_id
            )
            traces.append(
                DebateReviewTrace(
                    category="corrected_statement",
                    title=claim.original_text[:500],
                    explanation=(
                        f"Quellenzuordnung nachträglich auf „{correction.get('relation', 'unklar')}“ korrigiert: "
                        f"{correction.get('url', '')}"
                    ),
                    transcript_quote=quote,
                    speaker=speaker,
                    timestamp=timestamp,
                    claim_id=claim.claim_id,
                )
            )

    for entry in entries:
        raw = str(getattr(entry, "raw_text", None) or "").strip()
        if raw and raw != str(entry.text).strip():
            speaker = speakers.get(getattr(entry, "speaker_id", None), "Unbekannt")
            timestamp = getattr(entry, "timestamp", None)
            traces.append(
                DebateReviewTrace(
                    category="corrected_statement",
                    title=str(entry.text)[:500],
                    explanation="Das Transkript wurde sprachlich korrigiert; die ursprüngliche Fassung bleibt hier nachvollziehbar.",
                    transcript_quote=raw[:500],
                    speaker=str(speaker),
                    timestamp=timestamp.isoformat() if timestamp else "",
                )
            )

    nodes = {node.id: node for node in graph.nodes}
    for edge in graph.edges:
        if edge.relation != "concedes" or edge.obsolete:
            continue
        source = nodes.get(edge.source_id)
        target = nodes.get(edge.target_id)
        if source is None or target is None:
            continue
        quote, speaker, timestamp = _transcript_reference(
            entries, source.text, speakers, claim_id=source.claim_id
        )
        traces.append(
            DebateReviewTrace(
                category="concession",
                title=f"Zugeständnis zu: {target.text}"[:500],
                explanation=edge.rationale
                or "Die gespeicherte Argumentbeziehung markiert ein Zugeständnis.",
                transcript_quote=quote,
                speaker=speaker,
                timestamp=timestamp,
                claim_id=source.claim_id,
            )
        )

    for sample in samples:
        try:
            latency = int(sample.get("latency_ms") or 0)
        except (TypeError, ValueError):
            latency = 0
        late_reason = _late_recommendation_reason(sample, latency)
        if late_reason is None:
            continue
        target = str(sample.get("target_claim") or "").strip()
        answer = str(
            sample.get("answer_now") or sample.get("counterargument") or ""
        ).strip()
        quote, speaker, timestamp = _transcript_reference(
            entries, target, speakers, claim_id=str(sample.get("claim_id") or "")
        )
        traces.append(
            DebateReviewTrace(
                category="late_recommendation",
                title=target[:500] or "Späte Empfehlung",
                explanation=late_reason,
                transcript_quote=quote,
                speaker=speaker,
                timestamp=timestamp,
                claim_id=str(sample.get("claim_id") or ""),
                recommendation=answer[:700],
                latency_ms=latency,
            )
        )

    traces = traces[:40]
    counts = {
        category: sum(trace.category == category for trace in traces)
        for category in (
            "open_question",
            "unsupported_claim",
            "corrected_statement",
            "concession",
            "late_recommendation",
        )
    }
    notes = []
    if counts["open_question"]:
        notes.append(
            f"{counts['open_question']} offene Frage(n) gezielt erneut stellen und eine überprüfbare Antwort einfordern."
        )
    if counts["unsupported_claim"]:
        notes.append(
            f"{counts['unsupported_claim']} unbelegte Behauptung(en) vor der nächsten Debatte mit einer Primärquelle absichern."
        )
    if counts["corrected_statement"]:
        notes.append(
            f"{counts['corrected_statement']} Korrektur(en) anhand der Originalpassage prüfen und künftig früher kenntlich machen."
        )
    if counts["concession"]:
        notes.append(
            f"{counts['concession']} Zugeständnis(se) ausdrücklich festhalten und an die nächste Schlussfolgerung anbinden."
        )
    if counts["late_recommendation"]:
        notes.append(
            f"{counts['late_recommendation']} späte Empfehlung(en) kürzen oder den lokalen Schnellpfad priorisieren."
        )
    return traces, notes


def collect_review_sources(samples: list[dict]) -> list[DebateReviewSource]:
    """Return the actual claim-linked sources shown during the debate."""
    collected: list[DebateReviewSource] = []
    seen_urls: set[str] = set()
    for sample in samples:
        raw_sources = sample.get("sources", []) if isinstance(sample, dict) else []
        if not isinstance(raw_sources, list):
            continue
        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                continue
            try:
                source = DebateReviewSource.model_validate(raw_source)
            except (TypeError, ValueError):
                continue
            url = source.url.strip()
            if not url.startswith(("https://", "http://")):
                continue
            identity = url.rstrip("/")
            if identity in seen_urls:
                continue
            seen_urls.add(identity)
            collected.append(source)
            if len(collected) == 20:
                return collected
    return collected


def review_setting_key(session_id: uuid.UUID) -> str:
    return f"debate.review.{session_id}"


def parse_diagnostics(raw: str) -> tuple[DebateReviewMetrics, list[dict]]:
    try:
        data = json.loads(raw or "{}")
    except (TypeError, ValueError):
        data = {}
    debate = data.get("debate_copilot") if isinstance(data, dict) else {}
    if not isinstance(debate, dict):
        debate = {}
    metrics = DebateReviewMetrics.model_validate(
        {key: debate.get(key, 0) for key in DebateReviewMetrics.model_fields}
    )
    samples = debate.get("samples", [])
    return metrics, samples[:20] if isinstance(samples, list) else []


async def evaluate_debate(
    *,
    transcript: str,
    samples: list[dict],
    metrics: DebateReviewMetrics,
    model_id: str,
    session_id: uuid.UUID,
) -> DebateReview:
    system_default = (
        "/no_think\nDu bist ein praeziser deutschsprachiger Debattencoach. "
        "Bewerte fair, konkret und ohne erfundene Motive. Zitiere hoechstens "
        "zwoelf Woerter am Stueck. Empfehle nur die vorgegebenen Enum-Werte; "
        "schreibe niemals selbst einen Systemprompt."
    )
    task_default = (
        "Analysiere diese beendete Debatte erst jetzt auf ausdrueckliche "
        "Bestaetigung des Nutzers. Pruefe: natuerliche gesprochene Sprache, "
        "Kuerze, punktbezogene Widerlegung, faire Darstellung, Beweislast, "
        "offene Fragen, Quellenqualitaet und ob Analogien wirklich helfen. "
        "Pruefe ausserdem, ob die Vorschlaege konsequent die Nutzerposition "
        "staerkten, Themenwechsel korrekt erkannten, nach akzeptiertem Wechsel "
        "alten Kontext losliessen, passende Eingriffszeitpunkte fanden und eine "
        "Sofortantwort nur bei materiell besseren Rechercheergebnissen ersetzten. "
        "Nenne konkrete bessere Formulierungen."
    )
    system = load_prompt_resource("debate_review_system", system_default)
    task = load_prompt_resource("debate_review_task", task_default)
    prompt = (
        f"{task}\n\n"
        f"MESSWERTE:\n{metrics.model_dump_json()}\n\n"
        f"ANGEZEIGTE VORSCHLAEGE (lokale Stichprobe):\n"
        f"{json.dumps(samples[:20], ensure_ascii=False)}\n\n"
        f"TRANSKRIPT:\n{transcript[-18000:]}"
    )
    draft = await generate_json(
        model_id,
        prompt,
        DebateReviewDraft,
        session_id=session_id,
        source="debate_review",
        reasoning_effort="none",
        system=system,
    )
    return DebateReview(
        **draft.model_dump(),
        metrics=metrics,
        generated_at=datetime.now(UTC).isoformat(),
    )


def apply_review_suggestion(
    current: DebateSettings, review: DebateReviewDraft
) -> DebateSettings:
    """Apply only schema-constrained values after the route's confirmation gate."""
    return replace(
        current,
        mode=review.suggested_mode,
        research_frequency=review.suggested_research_frequency,
        always_analogy=review.suggested_always_analogy,
        style_focus=review.suggested_style_focus,
    )


async def get_debate_review(db, session_id: uuid.UUID) -> DebateReview | None:
    raw = await get_app_setting(db, review_setting_key(session_id), "")
    if not raw:
        return None
    try:
        return DebateReview.model_validate_json(raw)
    except (TypeError, ValueError):
        return None


async def save_debate_review(db, session_id: uuid.UUID, review: DebateReview) -> None:
    await set_app_setting(
        db,
        review_setting_key(session_id),
        review.model_dump_json(),
    )
