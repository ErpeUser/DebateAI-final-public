"""Local hybrid retrieval for private dossier context.

PostgreSQL full-text search supplies one ranking and FastEmbed supplies an
independent dense ranking.  Only records already admitted by the caller are
eligible, so retrieval cannot widen source or session permissions.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import json
import os
import re
import threading
from collections import OrderedDict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from app.models import KnowledgeRecord
from sqlalchemy import func, select

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_META_KEY = "retrieval_embedding"
_DEFAULT_TOP_K = 12
_DEFAULT_CACHE_ENTRIES = 512


@dataclass(frozen=True)
class KnowledgeSection:
    key: str
    text: str


@dataclass(frozen=True)
class _EmbeddingCacheEntry:
    model_version: str
    dimension: int
    content_hash: str
    vector: np.ndarray

    def metadata(self, *, include_vector: bool = False) -> dict[str, Any]:
        value: dict[str, Any] = {
            "model_version": self.model_version,
            "dimension": self.dimension,
            "content_hash": self.content_hash,
        }
        if include_vector:
            value["vector"] = self.vector.astype(float).tolist()
        return value


def _content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized(vector: Any) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(value))
    if not value.size or not norm or not np.isfinite(norm):
        raise ValueError("FastEmbed returned an invalid vector")
    return value / norm


def _installed_fastembed_version() -> str:
    try:
        return importlib.metadata.version("fastembed")
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


class FastEmbedContextIndex:
    """Bounded local dense index with content-addressed cache validation."""

    def __init__(
        self,
        *,
        model: Any | None = None,
        model_name: str = MODEL_NAME,
        model_version: str = "",
        max_cache_entries: int = _DEFAULT_CACHE_ENTRIES,
    ) -> None:
        self.model_name = model_name
        self.model_version = model_version or (
            f"{model_name}@fastembed-{_installed_fastembed_version()}"
        )
        self.max_cache_entries = max(1, int(max_cache_entries))
        self._model = model
        self._cache: OrderedDict[str, _EmbeddingCacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._embed_lock = threading.Lock()

    def _load_model(self):
        if self._model is not None:
            return self._model
        from fastembed import TextEmbedding

        data_dir = os.environ.get("DATA_DIR", "").strip()
        cache_dir = str(Path(data_dir) / "semantic-models") if data_dir else None
        self._model = TextEmbedding(
            model_name=self.model_name,
            cache_dir=cache_dir,
            threads=max(1, min(4, os.cpu_count() or 1)),
            lazy_load=True,
        )
        return self._model

    def _embed(self, texts: Sequence[str]) -> list[np.ndarray]:
        if not texts:
            return []
        with self._embed_lock:
            return [_normalized(item) for item in self._load_model().embed(list(texts))]

    def _valid_entry(
        self,
        section: KnowledgeSection,
        entry: _EmbeddingCacheEntry | None,
    ) -> bool:
        return bool(
            entry is not None
            and entry.model_version == self.model_version
            and entry.content_hash == _content_hash(section.text)
            and entry.dimension > 0
            and entry.vector.shape == (entry.dimension,)
        )

    def _remember(self, key: str, entry: _EmbeddingCacheEntry) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._cache[key] = entry
            while len(self._cache) > self.max_cache_entries:
                self._cache.popitem(last=False)

    def prime(self, section: KnowledgeSection, metadata: object) -> bool:
        """Load a persisted vector only when all cache identity fields match."""
        if not isinstance(metadata, dict):
            return False
        try:
            vector = _normalized(metadata.get("vector"))
            entry = _EmbeddingCacheEntry(
                model_version=str(metadata.get("model_version") or ""),
                dimension=int(metadata.get("dimension") or 0),
                content_hash=str(metadata.get("content_hash") or ""),
                vector=vector,
            )
        except (TypeError, ValueError):
            return False
        if not self._valid_entry(section, entry):
            return False
        self._remember(section.key, entry)
        return True

    def cache_metadata(
        self, key: str, *, include_vector: bool = False
    ) -> dict[str, Any]:
        with self._lock:
            entry = self._cache.get(key)
            return entry.metadata(include_vector=include_vector) if entry else {}

    def _prepare_entries(
        self, sections: Sequence[KnowledgeSection]
    ) -> tuple[int, dict[str, _EmbeddingCacheEntry]]:
        """Prepare sections and retain an operation-local view of every entry."""
        missing: list[KnowledgeSection] = []
        entries: dict[str, _EmbeddingCacheEntry] = {}
        with self._lock:
            for section in sections:
                entry = self._cache.get(section.key)
                if self._valid_entry(section, entry):
                    self._cache.move_to_end(section.key)
                    entries[section.key] = entry
                else:
                    self._cache.pop(section.key, None)
                    missing.append(section)
        if not missing:
            return 0, entries
        vectors = self._embed([section.text for section in missing])
        if len(vectors) != len(missing):
            raise ValueError("FastEmbed returned the wrong number of vectors")
        for section, vector in zip(missing, vectors):
            entry = _EmbeddingCacheEntry(
                model_version=self.model_version,
                dimension=int(vector.shape[0]),
                content_hash=_content_hash(section.text),
                vector=vector,
            )
            entries[section.key] = entry
            self._remember(section.key, entry)
        return len(missing), entries

    def prepare_sections(self, sections: Sequence[KnowledgeSection]) -> int:
        """Embed only sections whose model/dimension/hash metadata is stale."""
        prepared, _entries = self._prepare_entries(sections)
        return prepared

    def semantic_ranking(
        self,
        sections: Sequence[KnowledgeSection],
        query: str,
        *,
        limit: int = _DEFAULT_TOP_K,
    ) -> list[str]:
        clean_query = " ".join(query.split()).strip()
        if not clean_query or not sections or limit <= 0:
            return []

        _prepared, entries = self._prepare_entries(sections)

        query_vector = self._embed([clean_query])[0]
        ranked: list[tuple[str, float, int]] = []
        for position, section in enumerate(sections):
            entry = entries[section.key]
            if entry.dimension != int(query_vector.shape[0]):
                continue
            ranked.append(
                (section.key, float(np.dot(query_vector, entry.vector)), position)
            )
        ranked.sort(key=lambda item: (-item[1], item[2]))
        return [key for key, _score, _position in ranked[:limit]]


_DEFAULT_INDEX = FastEmbedContextIndex()


def reciprocal_rank_fusion(
    rankings: Iterable[Sequence[str]],
    *,
    rank_constant: int = 60,
) -> list[str]:
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    order = 0
    for ranking in rankings:
        seen_in_ranking: set[str] = set()
        for rank, key in enumerate(ranking, 1):
            if not key or key in seen_in_ranking:
                continue
            seen_in_ranking.add(key)
            first_seen.setdefault(key, order)
            order += 1
            scores[key] = scores.get(key, 0.0) + 1.0 / (rank_constant + rank)
    return sorted(scores, key=lambda key: (-scores[key], first_seen[key]))


def build_postgres_fts_statement(
    authorized_record_ids: Sequence[Any],
    query: str,
    *,
    limit: int = _DEFAULT_TOP_K,
):
    """Build the PostgreSQL 16 lexical ranking over an admitted ID set.

    ``to_regconfig`` makes the German configuration explicit while retaining a
    deployable ``simple`` fallback.  The ID filter is the permission boundary;
    callers must never pass records from another session/source grant.
    """
    config = func.coalesce(
        func.to_regconfig("german"),
        func.to_regconfig("simple"),
    )
    document = func.to_tsvector(
        config,
        func.concat_ws(
            " ",
            func.coalesce(KnowledgeRecord.title, ""),
            func.coalesce(KnowledgeRecord.body, ""),
        ),
    )
    tsquery = func.websearch_to_tsquery(config, query)
    rank = func.ts_rank_cd(document, tsquery, 32).label("fts_rank")
    return (
        select(KnowledgeRecord.id, rank)
        .where(
            KnowledgeRecord.id.in_(list(authorized_record_ids)),
            KnowledgeRecord.active.is_(True),
            document.op("@@")(tsquery),
        )
        .order_by(rank.desc(), KnowledgeRecord.id)
        .limit(max(1, int(limit)))
    )


async def postgres_fts_ranking(
    db,
    authorized_record_ids: Sequence[Any],
    query: str,
    *,
    limit: int = _DEFAULT_TOP_K,
) -> list[str]:
    if not query.strip() or not authorized_record_ids:
        return []
    result = await db.execute(
        build_postgres_fts_statement(authorized_record_ids, query, limit=limit)
    )
    return [str(row[0]) for row in result.all()]


def _parse_sections(value: str) -> list[KnowledgeSection]:
    raw_sections = [
        section.strip()
        for section in re.split(r"(?=^### )", value, flags=re.MULTILINE)
        if section.strip()
    ]
    return [
        KnowledgeSection(f"section:{index}", text)
        for index, text in enumerate(raw_sections)
    ]


def _lexical_fallback(sections: Sequence[KnowledgeSection], query: str) -> list[str]:
    terms = {
        token for token in re.findall(r"[\w]+", query.casefold()) if len(token) > 2
    }
    return [
        section.key
        for _score, _position, section in sorted(
            (
                sum(section.text.casefold().count(term) for term in terms),
                position,
                section,
            )
            for position, section in enumerate(sections)
        )[::-1]
    ]


def _within_budget(
    sections: Sequence[KnowledgeSection], ranking: Sequence[str], budget: int
) -> str:
    by_key = {section.key: section.text for section in sections}
    parts: list[str] = []
    used = 0
    for key in ranking:
        text = by_key.get(key, "")
        separator = 2 if parts else 0
        available = budget - used - separator
        if available <= 0:
            break
        chunk = text[:available]
        if not chunk:
            continue
        parts.append(chunk)
        used += separator + len(chunk)
        if len(chunk) < len(text):
            break
    return "\n\n".join(parts)


def _hybrid_selection(
    sections: Sequence[KnowledgeSection],
    query: str,
    *,
    lexical_ranking: Sequence[str],
    budget: int,
    index: FastEmbedContextIndex,
) -> str:
    try:
        semantic_ranking = index.semantic_ranking(sections, query, limit=_DEFAULT_TOP_K)
    except Exception:
        # The dossier remains usable when the optional local model is absent;
        # never replace its ranking with a second lexical approximation.
        semantic_ranking = []
    fused = reciprocal_rank_fusion((lexical_ranking[:_DEFAULT_TOP_K], semantic_ranking))
    return _within_budget(sections, fused, max(0, int(budget)))


def select_context_sections(
    value: str,
    query: str,
    *,
    budget: int = 12_000,
    lexical_ranking: Sequence[str] | None = None,
    index: FastEmbedContextIndex | None = None,
) -> str:
    """Compatibility renderer; callers with DB access should supply FTS IDs."""
    sections = _parse_sections(value)
    if (
        not query.strip()
        or len(sections) <= 1
        or (len(sections) <= 8 and index is None)
    ):
        return _within_budget(sections, [section.key for section in sections], budget)
    lexical = (
        list(lexical_ranking)
        if lexical_ranking is not None
        else _lexical_fallback(sections, query)
    )
    return _hybrid_selection(
        sections,
        query,
        lexical_ranking=lexical,
        budget=budget,
        index=index or _DEFAULT_INDEX,
    )


def _record_meta(record: Any) -> dict[str, Any]:
    try:
        value = json.loads(str(getattr(record, "meta", "") or "{}"))
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _record_section(record: Any, meta: dict[str, Any]) -> KnowledgeSection:
    label = (
        "local document"
        if meta.get("independent_evidence")
        else "user position; not independent evidence"
    )
    title = " ".join(str(getattr(record, "title", "") or "").split()).strip()
    body = str(getattr(record, "body", "") or "").strip()
    origin = " ".join(str(meta.get("origin") or title).split()).strip()
    page_reference = " ".join(str(meta.get("page_reference") or "").split()).strip()
    source_reference = f"origin: {origin}"
    if page_reference:
        source_reference += f"; page: {page_reference}"
    return KnowledgeSection(
        str(record.id),
        f"### {title} [{label}; private/local; {source_reference}]\n{body}",
    )


def prepare_knowledge_record_embeddings(
    authorized_records: Sequence[Any],
    *,
    index: FastEmbedContextIndex | None = None,
) -> int:
    """Prepare import/update embeddings and persist reusable cache metadata.

    The caller owns transaction boundaries. Run this CPU-bound helper through
    ``asyncio.to_thread`` from an async route, then commit the changed ``meta``
    fields in the same transaction as the imported records.
    """
    dense_index = index or _DEFAULT_INDEX
    records: list[Any] = []
    sections: list[KnowledgeSection] = []
    metadata: list[dict[str, Any]] = []
    for record in authorized_records:
        if not bool(getattr(record, "active", False)):
            continue
        meta = _record_meta(record)
        section = _record_section(record, meta)
        dense_index.prime(section, meta.get(EMBEDDING_META_KEY))
        records.append(record)
        sections.append(section)
        metadata.append(meta)
    prepared = dense_index.prepare_sections(sections)
    for record, section, meta in zip(records, sections, metadata):
        payload = dense_index.cache_metadata(section.key, include_vector=True)
        if not payload or meta.get(EMBEDDING_META_KEY) == payload:
            continue
        meta[EMBEDDING_META_KEY] = payload
        record.meta = json.dumps(meta, ensure_ascii=False)
    return prepared


def select_knowledge_record_context(
    authorized_records: Sequence[Any],
    query: str,
    *,
    lexical_ranking: Sequence[str],
    budget: int = 12_000,
    index: FastEmbedContextIndex | None = None,
) -> str:
    """Fuse rankings for active records already admitted by source/session ACLs.

    Embeddings are persisted inside the existing ``meta`` JSON so imports and
    content updates can reuse them without a new vector database or schema.
    Assignment back to ``record.meta`` lets the caller flush/commit atomically.
    """
    active = [
        record
        for record in authorized_records
        if bool(getattr(record, "active", False))
    ]
    if not active:
        return ""
    dense_index = index or _DEFAULT_INDEX
    prepare_knowledge_record_embeddings(active, index=dense_index)
    sections: list[KnowledgeSection] = []
    for record in active:
        meta = _record_meta(record)
        section = _record_section(record, meta)
        sections.append(section)

    return _hybrid_selection(
        sections,
        query,
        lexical_ranking=lexical_ranking,
        budget=budget,
        index=dense_index,
    )


async def retrieve_knowledge_record_context(
    db,
    authorized_records: Sequence[Any],
    query: str,
    *,
    budget: int = 12_000,
    top_k: int = _DEFAULT_TOP_K,
    index: FastEmbedContextIndex | None = None,
) -> str:
    """Compose authorized PostgreSQL FTS and local FastEmbed retrieval."""
    active = [
        record
        for record in authorized_records
        if bool(getattr(record, "active", False))
    ]
    lexical_ranking = await postgres_fts_ranking(
        db,
        [record.id for record in active],
        query,
        limit=top_k,
    )
    return await asyncio.to_thread(
        select_knowledge_record_context,
        active,
        query,
        lexical_ranking=lexical_ranking,
        budget=budget,
        index=index,
    )
