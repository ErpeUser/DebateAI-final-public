"""Durable, deterministic argument memory for the live debate copilot.

The graph is derived from recommendation fields that already exist. It adds no
model call and no prompt tokens. One claim keeps only its newest response tree,
while distinct claims and their open questions remain available across resumes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database import async_session
from app.models import DebateClaimRecord
from app.services.app_settings import get_app_setting, set_app_setting


# Live consumers select a small recent window, but persistence keeps the full
# session graph so old questions, concessions, sources and transcript links
# remain inspectable after resume.
MAX_GRAPH_CLAIMS = 40


class ArgumentNode(BaseModel):
    id: str
    kind: Literal["claim", "response", "point", "question"]
    claim_id: str
    text: str
    status: str = ""
    revision: int = 0
    speaker_id: str = ""
    speaker_name: str = ""
    speaker_type: str = ""
    evidence_urls: list[str] = Field(default_factory=list, max_length=8)


class ArgumentEdge(BaseModel):
    source_id: str
    target_id: str
    relation: Literal[
        "rebuts",
        "supports",
        "questions",
        "continues",
        "related",
        "contradicts",
        "concedes",
        "counterevidence",
        "premise",
        "condition",
        "double_standard",
        "answers",
        "topic_shift",
    ]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verified: bool = True
    source_claim_revision: int = 0
    target_claim_revision: int = 0
    source_span: tuple[int, int] | None = None
    target_span: tuple[int, int] | None = None
    verification_method: Literal["derived", "model", "rule", "source", "user"] = "derived"
    rationale: str = ""
    obsolete: bool = False


class ArgumentGraph(BaseModel):
    session_id: str
    nodes: list[ArgumentNode] = Field(default_factory=list)
    edges: list[ArgumentEdge] = Field(default_factory=list)
    updated_at: str = ""


def argument_graph_key(session_id: uuid.UUID | str) -> str:
    return f"debate.argument_graph.{session_id}"


def _text(value: Any, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[:limit].strip()


def _revision(data: dict[str, Any]) -> int:
    # Claim/source edges belong to the durable transcript claim revision, not
    # to the independently increasing UI recommendation revision.
    value = data.get(
        "claim_revision",
        data.get("transcript_revision", data.get("recommendation_revision", data.get("revision", 0))),
    )
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _claim_id(data: dict[str, Any]) -> str:
    supplied = _text(data.get("claim_id"), 120)
    if supplied:
        return supplied
    seed = _text(data.get("target_claim")) or _text(data.get("answer_now"))
    return "derived-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _evidence_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for source in data.get("sources") or []:
        if not isinstance(source, dict):
            continue
        url = _text(source.get("url"), 500)
        if url.startswith(("https://", "http://")) and url not in urls:
            urls.append(url)
        if len(urls) == 8:
            break
    return urls


def _terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\wäöüß]+", value.casefold())
        if len(token) >= 5
    }


def _trim_claims(graph: ArgumentGraph) -> ArgumentGraph:
    claims = sorted(
        (node for node in graph.nodes if node.kind == "claim"),
        key=lambda node: node.revision,
        reverse=True,
    )
    keep_claim_ids = {node.claim_id for node in claims[:MAX_GRAPH_CLAIMS]}
    nodes = [node for node in graph.nodes if node.claim_id in keep_claim_ids]
    node_ids = {node.id for node in nodes}
    edges = [
        edge for edge in graph.edges
        if edge.source_id in node_ids and edge.target_id in node_ids
    ]
    return graph.model_copy(update={"nodes": nodes, "edges": edges})


def update_argument_graph(
    graph: ArgumentGraph,
    recommendation: dict[str, Any] | BaseModel,
) -> ArgumentGraph:
    data = (
        recommendation.model_dump(mode="json")
        if isinstance(recommendation, BaseModel)
        else dict(recommendation)
    )
    claim_id = _claim_id(data)
    revision = _revision(data)
    claim_node_id = f"claim:{claim_id}"
    # A later model or research revision replaces only this claim's children.
    nodes = [
        node for node in graph.nodes
        if node.claim_id != claim_id or node.kind == "claim"
    ]
    retained_ids = {node.id for node in nodes}
    edges = [
        edge for edge in graph.edges
        if edge.source_id in retained_ids and edge.target_id in retained_ids
    ]

    target_claim = _text(data.get("target_claim"))
    target_terms = _terms(target_claim)
    semantic_related_ids = {
        _text(value, 120)
        for value in data.get("semantic_related_claim_ids") or []
        if _text(value, 120) and _text(value, 120) != claim_id
    }
    related_claim = next(
        (
            node
            for node in reversed(nodes)
            if node.kind == "claim"
            and node.claim_id != claim_id
            and (
                node.claim_id in semantic_related_ids
                or target_terms.intersection(_terms(node.text))
            )
        ),
        None,
    )
    existing_claim = next((node for node in nodes if node.id == claim_node_id), None)
    # Persistence runs off the latency-critical socket path. A slower older
    # task may therefore acquire the per-session lock after a newer revision;
    # it must not replace that claim's already visible response tree.
    if existing_claim is not None and existing_claim.revision > revision:
        return graph
    if existing_claim is not None and revision > existing_claim.revision:
        edges = [
            edge.model_copy(update={"obsolete": True})
            if edge.source_id == claim_node_id or edge.target_id == claim_node_id
            else edge
            for edge in edges
        ]
    claim = ArgumentNode(
        id=claim_node_id,
        kind="claim",
        claim_id=claim_id,
        text=target_claim or (existing_claim.text if existing_claim else "Unbenannte Behauptung"),
        status=_text(data.get("question_status"), 40),
        revision=max(revision, existing_claim.revision if existing_claim else 0),
        speaker_id=_text(data.get("speaker_id"), 120),
        speaker_name=_text(data.get("speaker_name"), 120),
        speaker_type=_text(data.get("speaker_type"), 40),
    )
    nodes = [node for node in nodes if node.id != claim_node_id]
    nodes.append(claim)
    if related_claim is not None:
        edges.append(ArgumentEdge(
            source_id=claim_node_id,
            target_id=related_claim.id,
            relation="related",
            confidence=0.5,
            verified=False,
        ))

    claim_ids = {
        node.claim_id
        for node in nodes
        if node.kind == "claim" and node.claim_id != claim_id
    }
    allowed_logical_relations = {
        "contradicts",
        "concedes",
        "counterevidence",
        "premise",
        "condition",
        "double_standard",
        "answers",
        "topic_shift",
        "supports",
    }
    claim_nodes_by_id = {
        node.claim_id: node for node in nodes if node.kind == "claim"
    }
    for raw_relation in data.get("logical_relations") or []:
        if not isinstance(raw_relation, dict):
            continue
        target_claim_id = _text(raw_relation.get("target_claim_id"), 120)
        relation = _text(raw_relation.get("relation"), 40)
        try:
            confidence = float(raw_relation.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if target_claim_id not in claim_ids or relation not in allowed_logical_relations:
            continue
        method = _text(raw_relation.get("verification_method"), 20) or "model"
        if method not in {"model", "rule", "source", "user"}:
            method = "model"
        rationale = _text(raw_relation.get("rationale"), 700)
        verified = bool(
            raw_relation.get("verified")
            and method in {"rule", "source", "user"}
            and rationale
        )
        target_node = claim_nodes_by_id[target_claim_id]
        source_span = raw_relation.get("source_span")
        target_span = raw_relation.get("target_span")
        source_span = tuple(source_span) if isinstance(source_span, (list, tuple)) and len(source_span) == 2 else None
        target_span = tuple(target_span) if isinstance(target_span, (list, tuple)) and len(target_span) == 2 else None
        edges = [
            edge
            for edge in edges
            if not (
                edge.source_id == claim_node_id
                and edge.target_id == f"claim:{target_claim_id}"
                and edge.relation == relation
            )
        ]
        edges.append(ArgumentEdge(
            source_id=claim_node_id,
            target_id=f"claim:{target_claim_id}",
            relation=relation,
            confidence=confidence,
            verified=verified,
            source_claim_revision=revision,
            target_claim_revision=target_node.revision,
            source_span=source_span,
            target_span=target_span,
            verification_method=method,
            rationale=rationale,
        ))

    response_text = _text(data.get("answer_now")) or _text(data.get("counterargument"))
    response_id = f"response:{claim_id}"
    if response_text:
        nodes.append(ArgumentNode(
            id=response_id,
            kind="response",
            claim_id=claim_id,
            text=response_text,
            revision=revision,
            evidence_urls=_evidence_urls(data),
        ))
        edges.append(ArgumentEdge(
            source_id=response_id,
            target_id=claim_node_id,
            relation="rebuts",
        ))

    for index, raw_point in enumerate(data.get("argument_points") or []):
        point = _text(raw_point, 400)
        if not point:
            continue
        point_id = f"point:{claim_id}:{index}"
        nodes.append(ArgumentNode(
            id=point_id,
            kind="point",
            claim_id=claim_id,
            text=point,
            revision=revision,
        ))
        edges.append(ArgumentEdge(
            source_id=point_id,
            target_id=response_id if response_text else claim_node_id,
            relation="supports" if response_text else "rebuts",
        ))

    question_text = _text(data.get("open_question")) or _text(data.get("counter_question"))
    if question_text:
        question_id = f"question:{claim_id}"
        nodes.append(ArgumentNode(
            id=question_id,
            kind="question",
            claim_id=claim_id,
            text=question_text,
            status=_text(data.get("question_status"), 40),
            revision=revision,
        ))
        edges.append(ArgumentEdge(
            source_id=question_id,
            target_id=claim_node_id,
            relation="questions",
        ))

    updated = ArgumentGraph(
        session_id=graph.session_id,
        nodes=nodes,
        edges=edges,
        updated_at=datetime.now(UTC).isoformat(),
    )
    return updated


def parse_argument_graph(raw: str, session_id: uuid.UUID | str) -> ArgumentGraph:
    try:
        return ArgumentGraph.model_validate_json(raw)
    except (TypeError, ValueError):
        return ArgumentGraph(session_id=str(session_id))


async def load_argument_graph(db, session_id: uuid.UUID | str) -> ArgumentGraph:
    records_result = await db.execute(
        select(DebateClaimRecord)
        .where(DebateClaimRecord.session_id == session_id)
        .order_by(DebateClaimRecord.revision, DebateClaimRecord.created_at)
    )
    records = list(records_result.scalars().all())
    if records:
        return argument_graph_from_records(session_id, records)
    raw = await get_app_setting(db, argument_graph_key(session_id), "")
    return parse_argument_graph(raw, session_id)


def argument_graph_from_records(
    session_id: uuid.UUID | str,
    records: list[DebateClaimRecord],
) -> ArgumentGraph:
    """Derive the presentation graph from normalized claim records."""
    newest: dict[str, DebateClaimRecord] = {}
    for record in records:
        current = newest.get(record.claim_id)
        if current is None or record.revision >= current.revision:
            newest[record.claim_id] = record
    graph = ArgumentGraph(session_id=str(session_id))
    for record in sorted(newest.values(), key=lambda item: (item.revision, item.claim_id)):
        feedback = record.feedback if isinstance(record.feedback, dict) else {}
        presentation = feedback.get("presentation")
        data = dict(presentation) if isinstance(presentation, dict) else {}
        data.update({
            "claim_id": record.claim_id,
            "claim_revision": record.revision,
            "target_claim": record.original_text,
            "speaker_id": record.speaker_id,
            "atomic_claims": list(record.atomic_claims or []),
            "sources": list(record.sources or []),
            "logical_relations": list(record.relations or []),
        })
        graph = update_argument_graph(graph, data)
    return _trim_claims(graph)


async def save_argument_graph(db, session_id: uuid.UUID | str, graph: ArgumentGraph) -> None:
    await set_app_setting(db, argument_graph_key(session_id), graph.model_dump_json())


async def correct_source_assignment(
    db,
    session_id: uuid.UUID,
    *,
    claim_id: str,
    source_url: str,
    relation: Literal["supports", "contradicts", "unclear"],
    affected_claim_ids: list[str],
) -> dict[str, Any]:
    """Persist a user's evidence correction and update graph consumers atomically."""
    result = await db.execute(
        select(DebateClaimRecord)
        .where(
            DebateClaimRecord.session_id == session_id,
            DebateClaimRecord.claim_id == claim_id,
        )
        .order_by(DebateClaimRecord.revision.desc())
    )
    record = result.scalars().first()
    if record is None:
        raise ValueError("claim not found")
    allowed = {
        str(item.get("id"))
        for item in (record.atomic_claims or [])
        if isinstance(item, dict) and item.get("id")
    }
    selected = [value for value in dict.fromkeys(affected_claim_ids) if value in allowed]
    claim_text = {
        str(item.get("id")): str(item.get("text") or "")
        for item in (record.atomic_claims or [])
        if isinstance(item, dict) and item.get("id")
    }
    sources = [dict(value) for value in (record.sources or []) if isinstance(value, dict)]
    corrected = None
    for source in sources:
        if str(source.get("url") or "").rstrip("/") != source_url.rstrip("/"):
            continue
        source.update({
            "claim_id": claim_id,
            "claim_revision": record.revision,
            "affected_claim_ids": selected,
            "affected_claims": [claim_text[value] for value in selected if claim_text.get(value)],
            "claim_relation": relation,
            "verification_status": relation,
        })
        corrected = source
        break
    if corrected is None:
        raise ValueError("source not found")
    record.sources = sources
    feedback = dict(record.feedback or {})
    corrections = list(feedback.get("source_corrections") or [])
    corrections.append({
        "url": source_url,
        "relation": relation,
        "affected_claim_ids": selected,
        "corrected_at": datetime.now(UTC).isoformat(),
    })
    feedback["source_corrections"] = corrections[-20:]
    record.feedback = feedback
    record.updated_at = datetime.now(UTC)

    graph = await load_argument_graph(db, session_id)
    nodes = []
    for node in graph.nodes:
        if node.claim_id == claim_id and node.kind == "response":
            urls = [url for url in node.evidence_urls if url.rstrip("/") != source_url.rstrip("/")]
            if selected and relation != "unclear":
                urls.append(source_url)
            node = node.model_copy(update={"evidence_urls": urls})
        nodes.append(node)
    await save_argument_graph(
        db,
        session_id,
        graph.model_copy(update={"nodes": nodes, "updated_at": datetime.now(UTC).isoformat()}),
    )
    return corrected


_PERSIST_LOCKS: dict[str, asyncio.Lock] = {}


async def persist_argument_recommendation(
    session_id: uuid.UUID | str,
    recommendation: dict[str, Any] | BaseModel,
) -> None:
    """Serialize live updates per session so research cannot overwrite a newer turn."""
    key = str(session_id)
    lock = _PERSIST_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        async with async_session() as db:
            graph = await load_argument_graph(db, session_id)
            updated_graph = update_argument_graph(graph, recommendation)
            await save_argument_graph(
                db,
                session_id,
                updated_graph,
            )
            raw = (
                recommendation.model_dump(mode="json")
                if isinstance(recommendation, BaseModel)
                else dict(recommendation)
            )
            claim_id = str(raw.get("claim_id") or raw.get("utterance_id") or "")
            revision = int(raw.get("claim_revision") or raw.get("transcript_revision") or 0)
            if claim_id:
                result = await db.execute(
                    select(DebateClaimRecord).where(
                        DebateClaimRecord.session_id == session_id,
                        DebateClaimRecord.claim_id == claim_id,
                        DebateClaimRecord.revision == revision,
                    )
                )
                record = result.scalar_one_or_none()
                values = {
                    "speaker_id": str(raw.get("speaker_id") or ""),
                    "original_text": str(raw.get("target_claim") or ""),
                    "atomic_claims": list(raw.get("atomic_claims") or []),
                    "sources": list(raw.get("sources") or []),
                    "relations": list(raw.get("logical_relations") or []),
                    "feedback": {
                        "presentation": {
                            key: raw.get(key)
                            for key in (
                                "answer_now",
                                "counterargument",
                                "argument_points",
                                "open_question",
                                "counter_question",
                                "question_status",
                                "speaker_name",
                                "speaker_type",
                                "semantic_related_claim_ids",
                            )
                            if raw.get(key) not in (None, "", [])
                        }
                    },
                    "updated_at": datetime.now(UTC),
                }
                if record is None:
                    db.add(DebateClaimRecord(
                        session_id=session_id,
                        claim_id=claim_id,
                        revision=revision,
                        **values,
                    ))
                else:
                    existing_feedback = dict(record.feedback or {})
                    existing_feedback.update(values["feedback"])
                    values["feedback"] = existing_feedback
                    for field, value in values.items():
                        setattr(record, field, value)
            await db.commit()
