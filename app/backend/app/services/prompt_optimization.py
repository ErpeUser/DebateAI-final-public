"""Controlled prompt evaluation, activation and rollback.

This module deliberately keeps optimization separate from model training.  A
candidate is only activated after it has been compared with the same fixed
cases and (when configured) an untouched holdout.  The store writes a small
audit ledger next to the editable prompts so every activation can be rolled
back without relying on an external provider or an LLM judge.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

_PROMPT_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,119}$")
_QUALITY_METRICS = (
    "naturalness",
    "factuality",
    "argument_strength",
    "source_honesty",
    "usability",
)


def candidate_digest(content: str) -> str:
    """Return the full content hash used to identify a prompt candidate."""
    return sha256(str(content).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """One deterministic score row for one case and one prompt variant."""

    case_id: str
    split: str
    metrics: Mapping[str, float]

    def __post_init__(self) -> None:
        if not str(self.case_id).strip():
            raise ValueError("Evaluation case_id darf nicht leer sein.")
        if self.split not in {"fixed", "holdout"}:
            raise ValueError("Evaluation split muss 'fixed' oder 'holdout' sein.")
        normalized: dict[str, float] = {}
        for name, value in dict(self.metrics).items():
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Ungueltiger Bewertungswert fuer {name}.") from exc
            if not math.isfinite(numeric):
                raise ValueError(f"Bewertungswert fuer {name} muss endlich sein.")
            normalized[str(name)] = numeric
        object.__setattr__(self, "metrics", normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "split": self.split,
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class OptimizationPolicy:
    """Safety limits for candidate comparison and optional auto-apply."""

    auto_apply_enabled: bool = False
    min_holdout_cases: int = 1
    max_quality_regression: float = 0.0
    max_latency_regression_ms: float = 100.0
    max_cost_increase_usd: float = 0.01
    max_prompt_change_chars: int = 400

    def __post_init__(self) -> None:
        if self.min_holdout_cases < 0:
            raise ValueError("min_holdout_cases darf nicht negativ sein.")
        if self.max_quality_regression < 0 or self.max_latency_regression_ms < 0:
            raise ValueError("Regressionsgrenzen duerfen nicht negativ sein.")
        if self.max_cost_increase_usd < 0 or self.max_prompt_change_chars < 0:
            raise ValueError("Aenderungsgrenzen duerfen nicht negativ sein.")


@dataclass(frozen=True, slots=True)
class EvaluationDecision:
    approved: bool
    reasons: tuple[str, ...]
    baseline: Mapping[str, Mapping[str, float]]
    candidate: Mapping[str, Mapping[str, float]]
    fixed_cases: int
    holdout_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "reasons": list(self.reasons),
            "baseline": {key: dict(value) for key, value in self.baseline.items()},
            "candidate": {key: dict(value) for key, value in self.candidate.items()},
            "fixed_cases": self.fixed_cases,
            "holdout_cases": self.holdout_cases,
        }


def _index(
    results: Iterable[EvaluationResult],
) -> dict[tuple[str, str], EvaluationResult]:
    indexed: dict[tuple[str, str], EvaluationResult] = {}
    for result in results:
        key = (result.split, result.case_id)
        if key in indexed:
            raise ValueError(
                f"Doppelte Evaluation fuer {result.split}/{result.case_id}."
            )
        indexed[key] = result
    return indexed


def _means(results: Sequence[EvaluationResult]) -> dict[str, float]:
    if not results:
        return {}
    names = set(_QUALITY_METRICS) | {"latency_ms", "cost_usd"}
    return {
        name: sum(float(item.metrics.get(name, 0.0)) for item in results) / len(results)
        for name in sorted(names)
    }


def compare_evaluations(
    baseline_results: Sequence[EvaluationResult],
    candidate_results: Sequence[EvaluationResult],
    policy: OptimizationPolicy | None = None,
) -> EvaluationDecision:
    """Compare two variants over identical fixed/holdout cases.

    The comparison is intentionally model-independent: a provider or the
    model that proposed a change cannot approve it by itself.  Quality is
    checked per split and the holdout is required to avoid optimizing only to
    the visible examples.
    """
    policy = policy or OptimizationPolicy()
    baseline = _index(baseline_results)
    candidate = _index(candidate_results)
    reasons: list[str] = []
    if set(baseline) != set(candidate):
        missing = sorted(set(baseline) - set(candidate))
        extra = sorted(set(candidate) - set(baseline))
        if missing:
            reasons.append(
                "candidate fehlt Evaluationsfaelle: "
                + ", ".join(f"{split}/{case}" for split, case in missing)
            )
        if extra:
            reasons.append(
                "candidate enthaelt unbekannte Evaluationsfaelle: "
                + ", ".join(f"{split}/{case}" for split, case in extra)
            )
    split_values: dict[str, dict[str, list[EvaluationResult]]] = {
        "fixed": {"baseline": [], "candidate": []},
        "holdout": {"baseline": [], "candidate": []},
    }
    for key in sorted(set(baseline) & set(candidate)):
        split, _case_id = key
        split_values[split]["baseline"].append(baseline[key])
        split_values[split]["candidate"].append(candidate[key])
    baseline_summary: dict[str, Mapping[str, float]] = {}
    candidate_summary: dict[str, Mapping[str, float]] = {}
    for split, values in split_values.items():
        baseline_summary[split] = _means(values["baseline"])
        candidate_summary[split] = _means(values["candidate"])
    holdout_count = len(split_values["holdout"]["baseline"])
    fixed_count = len(split_values["fixed"]["baseline"])
    if holdout_count < policy.min_holdout_cases:
        reasons.append(
            f"Holdout enthaelt nur {holdout_count} statt mindestens {policy.min_holdout_cases} Faelle."
        )
    for split in ("fixed", "holdout"):
        before = baseline_summary[split]
        after = candidate_summary[split]
        if not before or not after:
            continue
        for metric in _QUALITY_METRICS:
            if any(
                metric in row.metrics for row in split_values[split]["baseline"]
            ) != any(metric in row.metrics for row in split_values[split]["candidate"]):
                reasons.append(f"{split} {metric} fehlt auf einer Bewertungsseite.")
                continue
            if any(
                metric in row.metrics for row in split_values[split]["baseline"]
            ) and any(
                metric not in row.metrics
                for row in split_values[split]["baseline"]
                + split_values[split]["candidate"]
            ):
                reasons.append(
                    f"{split} {metric} ist nicht in allen Bewertungsf?llen vorhanden."
                )
                continue
            delta = after.get(metric, 0.0) - before.get(metric, 0.0)
            if delta < -policy.max_quality_regression:
                reasons.append(f"{split} {metric} regressiert um {delta:.3f}.")
        latency_delta = after.get("latency_ms", 0.0) - before.get("latency_ms", 0.0)
        if latency_delta > policy.max_latency_regression_ms:
            reasons.append(f"{split} Latenz steigt um {latency_delta:.1f} ms.")
        cost_delta = after.get("cost_usd", 0.0) - before.get("cost_usd", 0.0)
        if cost_delta > policy.max_cost_increase_usd:
            reasons.append(f"{split} Kosten steigen um {cost_delta:.4f} USD.")
    # A candidate may tie on quality, but it may not win solely by hiding an
    # unsupported metric: factuality and source honesty must be present.
    for split, results in split_values.items():
        for side in ("baseline", "candidate"):
            for row in results[side]:
                if any(
                    metric not in row.metrics
                    for metric in ("factuality", "source_honesty")
                ):
                    reasons.append(
                        f"{split} {side} benoetigt factuality und source_honesty."
                    )
                    break
    return EvaluationDecision(
        approved=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        baseline=baseline_summary,
        candidate=candidate_summary,
        fixed_cases=fixed_count,
        holdout_cases=holdout_count,
    )


def _change_size(before: str, after: str) -> int:
    # Count the larger side of each contiguous edit; replacements therefore
    # consume budget for both deletion and insertion instead of slipping through
    # when the strings happen to have equal length.
    import difflib

    return sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, before, after
        ).get_opcodes()
        if tag != "equal"
    )


class PromptOptimizationStore:
    """Persistent, atomic activation ledger for one editable AI directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.state_path = self.root / "optimization-state.json"
        self.history_root = self.root / "history" / "prompt-optimization"

    def _prompt_path(self, prompt_name: str) -> Path:
        if not _PROMPT_NAME.fullmatch(prompt_name):
            raise ValueError("Ungueltiger Promptname.")
        return self.root / f"{prompt_name}.txt"

    def _read_state(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"schema_version": 1, "active": None, "records": []}
        if not isinstance(value, dict):
            return {"schema_version": 1, "active": None, "records": []}
        value.setdefault("schema_version", 1)
        value.setdefault("active", None)
        value.setdefault("records", [])
        return value

    def _atomic_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(raw_path, path)
        finally:
            try:
                os.unlink(raw_path)
            except FileNotFoundError:
                pass

    def _atomic_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content.rstrip() + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(raw_path, path)
        finally:
            try:
                os.unlink(raw_path)
            except FileNotFoundError:
                pass

    def apply(
        self,
        prompt_name: str,
        candidate_content: str,
        rationale: str,
        baseline_results: Sequence[EvaluationResult],
        candidate_results: Sequence[EvaluationResult],
        policy: OptimizationPolicy | None = None,
        *,
        approved_by_user: bool = False,
        auto_apply: bool = False,
        explicit_auto_apply: bool = False,
        user_managed: bool = False,
        sources: Sequence[str] = (),
        risks: Sequence[str] = (),
    ) -> dict[str, Any]:
        policy = policy or OptimizationPolicy()
        if auto_apply:
            if not explicit_auto_apply:
                raise ValueError(
                    "Auto-Apply braucht eine ausdrueckliche Aktivierung (explicit enable)."
                )
            if not policy.auto_apply_enabled:
                raise ValueError("Auto-Apply ist deaktiviert.")
        elif not approved_by_user:
            raise ValueError(
                "Die Promptuebernahme braucht eine ausdrueckliche Nutzerfreigabe (approval required)."
            )
        if user_managed:
            raise ValueError(
                "user-managed / benutzerangepasste Prompts duerfen nicht automatisch ueberschrieben werden."
            )
        path = self._prompt_path(prompt_name)
        new_content = str(candidate_content).strip()
        if not new_content:
            raise ValueError("Ein Kandidatenprompt darf nicht leer sein.")
        # Reuse the production boundary so a proposal cannot bypass the
        # placeholder allowlist just because it arrived through the lab.
        try:
            from app.services.ai_config import _validate_prompt_content

            new_content = _validate_prompt_content(prompt_name, new_content)
        except ImportError:
            pass
        previous_content = (
            path.read_text(encoding="utf-8").strip() if path.is_file() else ""
        )
        change_size = _change_size(previous_content, new_content)
        if change_size > policy.max_prompt_change_chars:
            raise ValueError(
                f"Promptaenderung umfasst {change_size} Zeichen und ueberschreitet das Budget."
            )
        decision = compare_evaluations(baseline_results, candidate_results, policy)
        timestamp = datetime.now(UTC).isoformat()
        base_hash = candidate_digest(previous_content)
        new_hash = candidate_digest(new_content)
        record: dict[str, Any] = {
            "prompt_name": prompt_name,
            "timestamp": timestamp,
            "status": "rejected" if not decision.approved else "applied",
            "mode": "auto" if auto_apply else "manual",
            "base_hash": base_hash,
            "candidate_hash": new_hash,
            "rationale": str(rationale).strip(),
            "risks": [str(item) for item in risks],
            "sources": [str(item) for item in sources],
            "evaluation": decision.to_dict(),
        }
        if not decision.approved:
            state = self._read_state()
            state["records"].append(record)
            self._atomic_json(self.state_path, state)
            return {
                "status": "rejected",
                "candidate_hash": new_hash,
                "reasons": list(decision.reasons),
                "evaluation": decision.to_dict(),
            }
        history_path = (
            self.history_root
            / prompt_name
            / f"{timestamp.replace(':', '').replace('+', '_')}-{base_hash[:12]}.txt"
        )
        state = self._read_state()
        old_state = dict(state)
        try:
            if previous_content:
                self._atomic_text(history_path, previous_content)
            self._atomic_text(path, new_content)
            state["active"] = {
                "prompt_name": prompt_name,
                "previous_content": previous_content,
                "previous_hash": base_hash,
                "candidate_hash": new_hash,
                "activated_at": timestamp,
                "mode": "auto" if auto_apply else "manual",
            }
            state["records"].append(record)
            self._atomic_json(self.state_path, state)
        except Exception:
            # If the audit write fails, restore the previous active prompt so an
            # activation can never be visible without its audit record.
            if previous_content:
                self._atomic_text(path, previous_content)
            else:
                path.unlink(missing_ok=True)
            self._atomic_json(self.state_path, old_state)
            raise
        return {
            "status": "applied",
            "candidate_hash": new_hash,
            "evaluation": decision.to_dict(),
            "record": record,
        }

    def rollback_if_regressed(
        self,
        prompt_name: str,
        baseline_results: Sequence[EvaluationResult],
        current_results: Sequence[EvaluationResult],
        policy: OptimizationPolicy | None = None,
    ) -> dict[str, Any]:
        """Rollback the active candidate when a later holdout regresses.

        The hash check prevents a safety monitor from overwriting a prompt that
        a user edited after activation.  Such a race is surfaced as an error so
        the operator can decide which version to keep.
        """
        state = self._read_state()
        active = state.get("active")
        if not isinstance(active, dict) or active.get("prompt_name") != prompt_name:
            raise ValueError(
                "Fuer diesen Prompt ist keine aktive Optimierung vorhanden."
            )
        path = self._prompt_path(prompt_name)
        current = path.read_text(encoding="utf-8").strip() if path.is_file() else ""
        if candidate_digest(current) != str(active.get("candidate_hash") or ""):
            raise ValueError("Der aktive Prompt wurde seit der Aktivierung veraendert.")
        decision = compare_evaluations(baseline_results, current_results, policy)
        if decision.approved:
            return {
                "status": "kept",
                "prompt_name": prompt_name,
                "evaluation": decision.to_dict(),
            }
        result = self.rollback(prompt_name)
        result["reason"] = "holdout regression"
        result["evaluation"] = decision.to_dict()
        return result

    def rollback(self, prompt_name: str) -> dict[str, Any]:
        state = self._read_state()
        active = state.get("active")
        if not isinstance(active, dict) or active.get("prompt_name") != prompt_name:
            raise ValueError(
                "Fuer diesen Prompt ist keine wiederherstellbare Aktivierung vorhanden."
            )
        path = self._prompt_path(prompt_name)
        current = path.read_text(encoding="utf-8").strip() if path.is_file() else ""
        previous = str(active.get("previous_content") or "").strip()
        timestamp = datetime.now(UTC).isoformat()
        self._atomic_text(path, previous) if previous else path.unlink(missing_ok=True)
        state["records"].append(
            {
                "prompt_name": prompt_name,
                "timestamp": timestamp,
                "status": "rolled_back",
                "mode": "rollback",
                "base_hash": candidate_digest(current),
                "candidate_hash": candidate_digest(previous),
                "reason": "manual rollback",
            }
        )
        state["active"] = None
        self._atomic_json(self.state_path, state)
        return {
            "status": "rolled_back",
            "prompt_name": prompt_name,
            "restored_hash": candidate_digest(previous),
        }
