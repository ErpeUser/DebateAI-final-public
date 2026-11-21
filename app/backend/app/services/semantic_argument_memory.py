"""Small local semantic index over the durable debate argument graph.

The graph remains the source of truth. At startup its claim texts are embedded
locally with a multilingual ONNX model; no transcript or vector leaves the
machine and no second database is needed for the bounded 40-claim history.
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_NEGATIONS = {"nicht", "kein", "keine", "nie", "niemals", "ohne"}
_TIME_WORDS = {
    "heute",
    "gestern",
    "morgen",
    "derzeit",
    "aktuell",
    "frueher",
    "früher",
    "kuenftig",
    "künftig",
    "jaehrlich",
    "jährlich",
}
_UNITS = {
    "%",
    "prozent",
    "euro",
    "eur",
    "dollar",
    "usd",
    "kg",
    "g",
    "km",
    "m",
    "mio",
    "million",
    "millionen",
    "mrd",
    "milliarde",
    "milliarden",
    "stunden",
    "tage",
    "wochen",
    "monate",
    "jahre",
}
_CONDITION_MARKERS = {"wenn", "falls", "sofern", "unter", "vorausgesetzt"}


def _lexical_features(text: str) -> tuple[set[str], set[str], set[str]]:
    tokens = set(re.findall(r"[\wäöüß]+", text.casefold()))
    numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", text))
    return {token for token in tokens if len(token) >= 3}, tokens & _NEGATIONS, numbers


@dataclass(frozen=True)
class SemanticArgumentMatch:
    row: dict[str, Any]
    score: float
    match_type: Literal["related", "possible_conflict"] = "related"
    conflict_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class SemanticSearchResult:
    related: list[SemanticArgumentMatch]
    possible_conflicts: list[SemanticArgumentMatch]


@dataclass(frozen=True)
class _ConflictFeatures:
    terms: set[str]
    negated: bool
    quantities: set[tuple[str, str]]
    time_scopes: set[str]
    conditions: set[str]


def _conflict_features(text: str) -> _ConflictFeatures:
    folded = text.casefold()
    tokens = re.findall(r"[\wäöüß%]+", folded)
    terms = {
        token
        for token in tokens
        if len(token) >= 3
        and token not in _NEGATIONS
        and token not in _TIME_WORDS
        and token not in _CONDITION_MARKERS
        and token not in _UNITS
        and not token.isdigit()
    }
    quantities: set[tuple[str, str]] = set()
    for match in re.finditer(
        r"\b(\d+(?:[.,]\d+)?)\s*(%|prozent|euro|eur|dollar|usd|kg|g|km|m|mio|million(?:en)?|mrd|milliarde(?:n)?|stunden?|tage?|wochen?|monate?|jahre?)\b",
        folded,
    ):
        quantities.add((match.group(1).replace(",", "."), match.group(2)))
    time_scopes = set(re.findall(r"\b(?:19|20)\d{2}\b", folded))
    time_scopes.update(token for token in tokens if token in _TIME_WORDS)
    conditions = {
        " ".join(match.group(0).split())[:160]
        for match in re.finditer(
            r"\b(?:wenn|falls|sofern|vorausgesetzt)\b[^,.;!?]{0,140}", folded
        )
    }
    return _ConflictFeatures(
        terms=terms,
        negated=bool(set(tokens) & _NEGATIONS),
        quantities=quantities,
        time_scopes=time_scopes,
        conditions=conditions,
    )


def _possible_conflict_reasons(
    query: _ConflictFeatures,
    candidate: _ConflictFeatures,
    *,
    cosine: float,
) -> tuple[str, ...]:
    # Different periods or explicit conditions describe different scopes and
    # must not be promoted to a contradiction candidate merely because their
    # embeddings are close.
    if (
        query.time_scopes
        and candidate.time_scopes
        and query.time_scopes.isdisjoint(candidate.time_scopes)
    ):
        return ()
    if (
        query.conditions
        and candidate.conditions
        and query.conditions.isdisjoint(candidate.conditions)
    ):
        return ()
    shared_terms = query.terms & candidate.terms
    if cosine < 0.55 or len(shared_terms) < 2:
        return ()
    reasons: list[str] = []
    if query.negated != candidate.negated:
        reasons.append("negation")
    if query.quantities and candidate.quantities:
        query_units = {unit for _number, unit in query.quantities}
        candidate_units = {unit for _number, unit in candidate.quantities}
        if query_units & candidate_units and query.quantities != candidate.quantities:
            reasons.append("number")
    return tuple(reasons)


class SemanticArgumentMemory:
    """Thread-safe in-process vectors rebuilt from persisted claim rows."""

    def __init__(self, *, model_name: str = MODEL_NAME, minimum_score: float = 0.34):
        self.model_name = model_name
        self.minimum_score = minimum_score
        self._model = None
        self._rows: dict[str, dict[str, Any]] = {}
        self._vectors: dict[str, np.ndarray] = {}
        self._lock = threading.RLock()
        self._embed_lock = threading.Lock()
        self.ready = False
        self.error = ""
        self.vector_dimension = 0
        self.model_signature = ""

    @staticmethod
    def _key(row: dict[str, Any]) -> str:
        return str(row.get("claim_id") or row.get("target_claim") or "").strip()

    @staticmethod
    def _text(row: dict[str, Any]) -> str:
        # Only the original claim is embedded. AI replies and interpretations
        # stay separate and cannot silently become remembered user statements.
        return " ".join(str(row.get("target_claim") or "").split()).strip()

    @staticmethod
    def _revision(row: dict[str, Any]) -> int:
        for field in (
            "revision",
            "claim_revision",
            "transcript_revision",
            "recommendation_revision",
        ):
            try:
                if row.get(field) is not None:
                    return max(0, int(row[field]))
            except (TypeError, ValueError):
                continue
        return 0

    @staticmethod
    def _normalized(vector) -> np.ndarray:
        value = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(value))
        return value / norm if norm else value

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

    def _embed(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        with self._embed_lock:
            return [self._normalized(item) for item in self._load_model().embed(texts)]

    def rebuild(self, rows: list[dict[str, Any]]) -> None:
        """Warm the model and replace the index from durable claim rows."""
        usable = [(self._key(row), self._text(row), dict(row)) for row in rows]
        usable = [item for item in usable if item[0] and item[1]]
        try:
            vectors = self._embed([item[1] for item in usable])
        except Exception as exc:
            self.error = str(exc)
            return
        with self._lock:
            dimension = int(vectors[0].shape[0]) if vectors else 0
            self._rows = {key: row for (key, _text, row) in usable}
            self._vectors = {
                key: vector for (key, _text, _row), vector in zip(usable, vectors)
            }
            self.vector_dimension = dimension
            self.model_signature = f"{self.model_name}:{dimension}"
            self.ready = True
            self.error = ""

    def upsert(self, row: dict[str, Any]) -> None:
        key = self._key(row)
        text = self._text(row)
        if not key or not text or not self.ready:
            return
        with self._lock:
            previous = self._rows.get(key)
            if previous and self._revision(row) < self._revision(previous):
                return
            if previous and self._text(previous) == text:
                self._rows[key] = dict(row)
                return
        try:
            vector = self._embed([text])[0]
        except Exception as exc:
            self.error = str(exc)
            return
        if self.vector_dimension and int(vector.shape[0]) != self.vector_dimension:
            self.error = "Embedding model dimension changed; rebuild required"
            self.ready = False
            return
        with self._lock:
            self._rows[key] = dict(row)
            self._vectors[key] = vector

    def remove(self, claim_id: str) -> None:
        """Forget a revoked learning example without rebuilding the index."""
        with self._lock:
            self._rows.pop(claim_id, None)
            self._vectors.pop(claim_id, None)

    def search(
        self,
        text: str,
        *,
        limit: int = 4,
        exclude_claim_id: str = "",
        speaker_id: str = "",
        topic_terms: set[str] | None = None,
    ) -> list[SemanticArgumentMatch]:
        return self.search_targets(
            text,
            related_limit=limit,
            conflict_limit=0,
            exclude_claim_id=exclude_claim_id,
            speaker_id=speaker_id,
            topic_terms=topic_terms,
        ).related

    def search_targets(
        self,
        text: str,
        *,
        related_limit: int = 4,
        conflict_limit: int = 4,
        exclude_claim_id: str = "",
        speaker_id: str = "",
        topic_terms: set[str] | None = None,
    ) -> SemanticSearchResult:
        """Return topical memories and separately labelled conflict candidates.

        Conflict signals are retrieval hints only.  Logical verification stays
        downstream because embeddings and surface differences cannot prove a
        contradiction.
        """
        query = " ".join(text.split()).strip()
        if not query or not self.ready:
            return SemanticSearchResult([], [])
        try:
            query_vector = self._embed([query])[0]
        except Exception as exc:
            self.error = str(exc)
            return SemanticSearchResult([], [])
        query_terms, _query_negations, _query_numbers = _lexical_features(query)
        query_conflict = _conflict_features(query)
        topic_terms = {term.casefold() for term in (topic_terms or set()) if term}
        with self._lock:
            related: list[SemanticArgumentMatch] = []
            conflicts: list[SemanticArgumentMatch] = []
            for key, vector in self._vectors.items():
                row = self._rows[key]
                if key == exclude_claim_id or self._text(row) == query:
                    continue
                row_text = self._text(row)
                row_terms, _row_negations, _row_numbers = _lexical_features(row_text)
                if topic_terms and not topic_terms.intersection(row_terms):
                    continue
                cosine = float(np.dot(query_vector, vector))
                union = query_terms | row_terms
                lexical = len(query_terms & row_terms) / len(union) if union else 0.0
                score = cosine * 0.78 + lexical * 0.22
                if (
                    speaker_id
                    and row.get("speaker_id")
                    and row.get("speaker_id") != speaker_id
                ):
                    score -= 0.04
                related.append(SemanticArgumentMatch(row=dict(row), score=score))
                reasons = _possible_conflict_reasons(
                    query_conflict,
                    _conflict_features(row_text),
                    cosine=cosine,
                )
                if reasons:
                    conflicts.append(
                        SemanticArgumentMatch(
                            row=dict(row),
                            score=score,
                            match_type="possible_conflict",
                            conflict_reasons=reasons,
                        )
                    )
        related_matches = [
            match
            for match in sorted(related, key=lambda item: item.score, reverse=True)
            if match.score >= self.minimum_score
        ][: max(0, related_limit)]
        conflict_matches = sorted(
            conflicts,
            key=lambda item: (len(item.conflict_reasons), item.score),
            reverse=True,
        )[: max(0, conflict_limit)]
        return SemanticSearchResult(related_matches, conflict_matches)
