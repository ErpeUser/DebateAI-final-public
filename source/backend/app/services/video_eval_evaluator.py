"""Leakage-safe evaluation artifacts for DebateAI video runs.

This module never changes prompts, models, branches, or production settings. It
only turns saved video artifacts into deterministic train/development/test
manifests and blind pairwise evaluation records.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

_WORD_RE = re.compile(r"[\wäöüß]+", re.IGNORECASE)
_STOPWORDS = {
    "der", "die", "das", "ein", "eine", "einer", "einem", "einen",
    "und", "oder", "ist", "sind", "war", "wird", "zu", "von", "für",
    "mit", "auf", "im", "in", "an", "als", "auch", "nicht",
}


@dataclass(frozen=True)
class EvalCaseRecord:
    case_id: str
    video_id: str
    claim: str
    claim_family: str
    source_candidates: tuple[str, ...] = ()


@dataclass
class EvaluationManifest:
    schema_version: int = 1
    seed: str = "debateai-eval-v1"
    splits: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    blind_pairs: list[dict[str, Any]] = field(default_factory=list)
    leakage_checks: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] = field(default_factory=dict)


def _normalized_claim(value: str) -> str:
    return " ".join(_WORD_RE.findall(str(value or "").casefold()))


def _claim_family(value: str) -> str:
    tokens = [token for token in _WORD_RE.findall(str(value or "").casefold()) if token not in _STOPWORDS]
    # Keep order because the same words in a negated sentence are not the same
    # claim. The digest makes the family identifier stable and compact.
    normalized = " ".join(tokens)[:800]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20] or "empty"


def _near_duplicate(left: str, right: str) -> bool:
    a = _normalized_claim(left)
    b = _normalized_claim(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.88


def load_video_artifacts(paths: Iterable[str | Path]) -> list[EvalCaseRecord]:
    """Load saved artifacts without treating their response as ground truth."""
    records: list[EvalCaseRecord] = []
    for path_value in paths:
        path = Path(path_value)
        payload = json.loads(path.read_text(encoding="utf-8"))
        video_id = str(payload.get("video_id") or path.stem)
        for row in payload.get("eval_cases") or []:
            case_id = str(row.get("case_id") or "")
            claim = str(row.get("claim") or row.get("original_statement") or "").strip()
            if not case_id or not claim:
                continue
            candidates = tuple(
                str(value) for value in (row.get("source_candidates") or []) if str(value)
            )
            records.append(EvalCaseRecord(
                case_id=case_id,
                video_id=video_id,
                claim=claim,
                claim_family=_claim_family(claim),
                source_candidates=candidates,
            ))
    return records


def _connected_groups(records: list[EvalCaseRecord]) -> list[list[EvalCaseRecord]]:
    """Keep a video and a near-duplicate claim family in one split."""
    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    by_video: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for index, record in enumerate(records):
        if record.video_id in by_video:
            union(index, by_video[record.video_id])
        else:
            by_video[record.video_id] = index
        if record.claim_family in by_family:
            union(index, by_family[record.claim_family])
        else:
            by_family[record.claim_family] = index
    # Catch near-duplicate wording that received different family hashes.
    for left, record in enumerate(records):
        for right in range(left):
            if _near_duplicate(record.claim, records[right].claim):
                union(left, right)

    groups: dict[int, list[EvalCaseRecord]] = {}
    for index, record in enumerate(records):
        groups.setdefault(find(index), []).append(record)
    return list(groups.values())


def build_split_manifest(
    records: Iterable[EvalCaseRecord],
    *,
    seed: str = "debateai-eval-v1",
    ratios: tuple[float, float, float] = (0.6, 0.2, 0.2),
) -> EvaluationManifest:
    """Assign connected video/claim groups to train, development, and test."""
    rows = list(records)
    if not rows:
        return EvaluationManifest(seed=seed, splits={"train": [], "development": [], "test": []})
    if len(ratios) != 3 or any(value <= 0 for value in ratios):
        raise ValueError("ratios must contain three positive values")
    groups = _connected_groups(rows)
    ordered = sorted(
        groups,
        key=lambda group: hashlib.sha256(
            f"{seed}:{group[0].video_id}:{group[0].claim_family}".encode("utf-8")
        ).hexdigest(),
    )
    total = sum(len(group) for group in ordered)
    targets = [total * value / sum(ratios) for value in ratios]
    names = ("train", "development", "test")
    splits: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    counts = [0, 0, 0]
    for group in ordered:
        index = min(
            range(3),
            key=lambda candidate: (
                counts[candidate] - targets[candidate],
                counts[candidate],
                candidate,
            ),
        )
        for record in group:
            splits[names[index]].append({
                "case_id": record.case_id,
                "video_id": record.video_id,
                "claim": record.claim,
                "claim_family": record.claim_family,
                "source_candidates": list(record.source_candidates),
            })
        counts[index] += len(group)

    manifest = EvaluationManifest(seed=seed, splits=splits)
    manifest.leakage_checks = validate_no_leakage(manifest)
    manifest.blind_pairs = build_blind_pairs(manifest)
    return manifest


def validate_no_leakage(manifest: EvaluationManifest) -> dict[str, Any]:
    """Check that video IDs and claim families never cross split boundaries."""
    video_splits: dict[str, set[str]] = {}
    family_splits: dict[str, set[str]] = {}
    for split, rows in manifest.splits.items():
        for row in rows:
            video_splits.setdefault(str(row.get("video_id") or ""), set()).add(split)
            family_splits.setdefault(str(row.get("claim_family") or ""), set()).add(split)
    video_leaks = {key: sorted(value) for key, value in video_splits.items() if len(value) > 1}
    family_leaks = {key: sorted(value) for key, value in family_splits.items() if len(value) > 1}
    return {
        "passed": not video_leaks and not family_leaks,
        "video_leaks": video_leaks,
        "claim_family_leaks": family_leaks,
    }


def build_blind_pairs(
    manifest: EvaluationManifest,
    *,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
) -> list[dict[str, Any]]:
    """Create blind comparison rows; labels are hidden until a reviewer scores."""
    pairs: list[dict[str, Any]] = []
    for row in manifest.splits.get("test", []):
        case_id = str(row.get("case_id") or "")
        video_id = str(row.get("video_id") or "")
        pair_id = hashlib.sha256(
            f"{manifest.seed}:{video_id}:{case_id}:{baseline_label}:{candidate_label}".encode("utf-8")
        ).hexdigest()[:24]
        pairs.append({
            "pair_id": pair_id,
            "case_id": case_id,
            "video_id": video_id,
            "claim_family": row.get("claim_family", ""),
            "left_label": "A",
            "right_label": "B",
            "baseline_label": baseline_label,
            "candidate_label": candidate_label,
            "blind": True,
            "revealed": False,
            "decision": "",
            "criteria": {
                "directness": None,
                "example_or_analogy": None,
                "counter_question": None,
                "rebuttal_quality": None,
                "claim_accuracy": None,
                "source_binding": None,
                "speakability": None,
                "latency_ms": None,
            },
        })
    return pairs


def score_blind_pairs(
    pairs: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate reviewer decisions without revealing provider names."""
    rows = list(pairs)
    decisions = [str(row.get("decision") or "").casefold() for row in rows]
    valid = [value for value in decisions if value in {"a", "b", "tie"}]
    return {
        "pairs": len(rows),
        "scored": len(valid),
        "a_wins": valid.count("a"),
        "b_wins": valid.count("b"),
        "ties": valid.count("tie"),
        "completion": round(len(valid) / len(rows), 3) if rows else 0.0,
    }


def save_manifest(manifest: EvaluationManifest, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.scoring = score_blind_pairs(manifest.blind_pairs)
    path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
