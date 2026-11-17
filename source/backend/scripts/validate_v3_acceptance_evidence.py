"""Validate metadata for the remaining manual V3 acceptance packages.

This tool is intentionally a completeness and consistency gate.  It never
returns ``passed``: a complete package is only ``ready_for_manual_review`` and
still requires the operator's real hardware run and human sign-off.
"""

from __future__ import annotations

import argparse
import json
import math
import numbers
import re
from pathlib import Path
from typing import Any


REQUIREMENTS = {"A06", "A18", "A21", "A22"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
A06_EVENT_FIELDS = {
    "speaker_switch": ("at_seconds", "speaker_before", "speaker_after"),
    "device_switch": ("at_seconds", "track", "before_endpoint_id", "after_endpoint_id"),
    "asr_failure": ("at_seconds", "track", "injected", "visible_status"),
    "reconnect": ("at_seconds", "capture_id_before", "capture_id_after", "sequence_continuous"),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _sha(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(_text(value)))


def _missing(value: Any, path: str, missing: list[str]) -> None:
    if value is None or (isinstance(value, str) and not value.strip()):
        missing.append(path)


def _required_metrics(
    run: dict[str, Any],
    names: tuple[str, ...],
    errors: list[str],
) -> None:
    metrics = run.get("metrics")
    if not isinstance(metrics, dict):
        errors.append(f"run {run.get('name', '<unnamed>')} has no metrics object")
        return
    for name in names:
        if metrics.get(name) is None:
            errors.append(f"run {run.get('name', '<unnamed>')} misses metric {name}")
            continue
        value = metrics.get(name)
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(float(value)):
            errors.append(f"run {run.get('name', '<unnamed>')} metric {name} must be finite numeric")
        elif value < 0:
            errors.append(f"run {run.get('name', '<unnamed>')} metric {name} must be non-negative")


def _validate_metric_range(
    run: dict[str, Any],
    name: str,
    errors: list[str],
    *,
    maximum: float | None = None,
) -> None:
    metrics = run.get("metrics")
    if not isinstance(metrics, dict) or metrics.get(name) is None:
        return
    value = metrics.get(name)
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(float(value)):
        return
    if maximum is not None and value > maximum:
        errors.append(f"run {run.get('name', '<unnamed>')} metric {name} must be <= {maximum:g}")


def _validate_common(
    payload: dict[str, Any],
    missing: list[str],
    errors: list[str],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    requirement = _text(payload.get("requirement_id")).upper()
    if requirement not in REQUIREMENTS:
        errors.append("requirement_id must be one of A06, A18, A21, A22")

    reference = payload.get("reference")
    if not isinstance(reference, dict):
        missing.append("reference")
        reference = {}
    environment = payload.get("environment")
    if not isinstance(environment, dict):
        missing.append("environment")
        environment = {}

    _missing(reference.get("sha256"), "reference.sha256", missing)
    if reference.get("sha256") is not None and not _sha(reference.get("sha256")):
        errors.append("reference.sha256 must be a 64-character SHA-256 hash")
    _missing(reference.get("language"), "reference.language", missing)
    _missing(reference.get("duration_seconds"), "reference.duration_seconds", missing)
    duration = reference.get("duration_seconds")
    if duration is not None and (
        isinstance(duration, bool)
        or not isinstance(duration, numbers.Real)
        or not math.isfinite(float(duration))
        or duration <= 0
    ):
        errors.append("reference.duration_seconds must be a finite positive number")
    _missing(environment.get("hardware_id"), "environment.hardware_id", missing)
    _missing(environment.get("software_commit"), "environment.software_commit", missing)
    _missing(environment.get("load_profile"), "environment.load_profile", missing)

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        missing.append("artifacts")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"artifacts[{index}] must be an object")
                continue
            _missing(artifact.get("kind"), f"artifacts[{index}].kind", missing)
            _missing(artifact.get("sha256"), f"artifacts[{index}].sha256", missing)
            if artifact.get("sha256") is not None and not _sha(artifact.get("sha256")):
                errors.append(f"artifacts[{index}].sha256 must be a 64-character SHA-256 hash")
    return requirement, reference, environment


def _validate_a06_events(payload: dict[str, Any], missing: list[str], errors: list[str]) -> None:
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        missing.append("events")
        return
    seen: set[str] = set()
    for index, event in enumerate(events):
        prefix = f"events[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{prefix} must be an object")
            continue
        event_type = _text(event.get("type"))
        if event_type not in A06_EVENT_FIELDS:
            errors.append(f"{prefix}.type must be one of {', '.join(sorted(A06_EVENT_FIELDS))}")
            continue
        seen.add(event_type)
        for field in A06_EVENT_FIELDS[event_type]:
            _missing(event.get(field), f"{prefix}.{field}", missing)
        at_seconds = event.get("at_seconds")
        if (
            isinstance(at_seconds, bool)
            or not isinstance(at_seconds, numbers.Real)
            or not math.isfinite(float(at_seconds))
            or at_seconds < 0
        ):
            errors.append(f"{prefix}.at_seconds must be a finite non-negative number")
        if event_type == "speaker_switch" and _text(event.get("speaker_before")) == _text(event.get("speaker_after")):
            errors.append(f"{prefix} must change speaker identity")
        if event_type == "device_switch" and _text(event.get("before_endpoint_id")) == _text(event.get("after_endpoint_id")):
            errors.append(f"{prefix} must record different endpoint identities")
        if event_type == "asr_failure" and event.get("injected") is not True:
            errors.append(f"{prefix}.injected must be true for a deliberate recovery test")
        if event_type == "reconnect" and event.get("sequence_continuous") is not True:
            errors.append(f"{prefix}.sequence_continuous must be true after reconnect")
    for event_type in A06_EVENT_FIELDS:
        if event_type not in seen:
            missing.append(f"events.{event_type}")


def _validate_a06(
    payload: dict[str, Any],
    reference: dict[str, Any],
    missing: list[str],
    errors: list[str],
) -> None:
    if _text(reference.get("language")).casefold() != "de":
        errors.append("A06 reference.language must be de")
    duration = reference.get("duration_seconds")
    if isinstance(duration, (int, float)) and duration < 120:
        errors.append("A06 reference must be at least 120 seconds")
    flags = payload.get("scenario_flags")
    if not isinstance(flags, dict):
        missing.append("scenario_flags")
    else:
        for name in ("microphone", "system_audio", "overlap", "device_switch", "backlog"):
            if flags.get(name) is not True:
                errors.append(f"A06 scenario flag {name} must be true")
    _validate_a06_events(payload, missing, errors)
    _missing(payload.get("transcript_complete"), "transcript_complete", missing)
    if payload.get("transcript_complete") is not True:
        errors.append("A06 transcript_complete must be true after manual comparison")
    _missing(payload.get("terminal_state"), "terminal_state", missing)
    if _text(payload.get("terminal_state")).casefold() != "clean":
        errors.append("A06 terminal_state must be clean")


def _validate_human_review(
    payload: dict[str, Any],
    missing: list[str],
    errors: list[str],
    *,
    required: bool = True,
    require_blinded: bool = False,
    minimum_ratings: int | None = None,
) -> None:
    review = payload.get("human_review")
    if not isinstance(review, dict):
        missing.append("human_review")
        return
    raters = review.get("rater_ids")
    ratings = review.get("ratings")
    if require_blinded and review.get("blinded") is not True:
        errors.append("human_review must be blinded")
    if required and (not isinstance(raters, list) or not raters):
        missing.append("human_review.rater_ids")
    if required and (not isinstance(ratings, list) or not ratings):
        missing.append("human_review.ratings")
    if isinstance(raters, list):
        invalid = [item for item in raters if not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", item)]
        if invalid:
            errors.append("human_review.rater_ids must be anonymized identifiers")
    if isinstance(ratings, list):
        if minimum_ratings is not None and len(ratings) < minimum_ratings:
            errors.append("human_review ratings must cover every case")
        cases = []
        for rating in ratings:
            if not isinstance(rating, dict) or _text(rating.get("case")) == "":
                errors.append("human_review ratings must identify a case")
                continue
            cases.append(_text(rating.get("case")))
        if len(cases) != len(set(cases)):
            errors.append("human_review ratings must contain each case once")


def _validate_a18(payload: dict[str, Any], missing: list[str], errors: list[str]) -> None:
    modes = payload.get("modes")
    if not isinstance(modes, list) or len(set(map(_text, modes))) < 2:
        errors.append("A18 requires two modes")
    case_count = payload.get("case_count")
    if not isinstance(case_count, int) or case_count < 10:
        errors.append("A18 requires at least 10 German multi-turn cases")
    minimum_ratings = case_count if isinstance(case_count, int) and not isinstance(case_count, bool) and case_count > 0 else None
    _validate_human_review(
        payload,
        missing,
        errors,
        require_blinded=True,
        minimum_ratings=minimum_ratings,
    )


def _validate_a21(
    payload: dict[str, Any],
    reference: dict[str, Any],
    environment: dict[str, Any],
    missing: list[str],
    errors: list[str],
) -> None:
    runs = payload.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        missing.append("runs[asr_a,asr_b]")
        return
    names = {_text(run.get("name")) for run in runs if isinstance(run, dict)}
    if names != {"asr_a", "asr_b"}:
        errors.append("A21 runs must contain asr_a and asr_b")
    expected_reference = _text(reference.get("sha256")).casefold()
    expected_hardware = _text(environment.get("hardware_id"))
    expected_load = _text(environment.get("load_profile"))
    for run in runs:
        if not isinstance(run, dict):
            errors.append("A21 each run must be an object")
            continue
        if _text(run.get("reference_sha256")).casefold() != expected_reference:
            errors.append("A21 ASR runs must use the same reference audio")
        if _text(run.get("hardware_id")) != expected_hardware:
            errors.append("A21 ASR runs must use the same hardware")
        if _text(run.get("load_profile")) != expected_load:
            errors.append("A21 ASR runs must use the same load")
        if run.get("manual_correction") is not False:
            errors.append("A21 runs must not contain manual transcript correction")
        _required_metrics(
            run,
            ("wer", "number_errors", "negation_errors", "latency_ms", "dropouts", "cpu_peak_mb"),
            errors,
        )


def _validate_a22(
    payload: dict[str, Any],
    environment: dict[str, Any],
    missing: list[str],
    errors: list[str],
) -> None:
    _missing(payload.get("dataset_sha256"), "dataset_sha256", missing)
    if payload.get("dataset_sha256") is not None and not _sha(payload.get("dataset_sha256")):
        errors.append("dataset_sha256 must be a 64-character SHA-256 hash")
    if payload.get("future_data_excluded") is not True:
        errors.append("A22 future_data_excluded must be true")
    denominator = payload.get("denominator")
    if (
        not isinstance(denominator, int)
        or isinstance(denominator, bool)
        or denominator <= 0
    ):
        errors.append("A22 denominator must be a positive integer fixed before the run")
    runs = payload.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        missing.append("runs[production,reference]")
    else:
        expected_load = _text(environment.get("load_profile"))
        names = {_text(run.get("name")) for run in runs if isinstance(run, dict)}
        if names != {"production", "reference"}:
            errors.append("A22 runs must contain production and reference")
        for run in runs:
            if not isinstance(run, dict):
                errors.append("A22 each run must be an object")
                continue
            if _text(run.get("load_profile")) != expected_load:
                errors.append("A22 production and reference must use the same load")
            _required_metrics(run, ("latency_ms", "error_rate"), errors)
            _validate_metric_range(run, "error_rate", errors, maximum=1.0)
    minimum_ratings = (
        denominator
        if isinstance(denominator, int) and not isinstance(denominator, bool) and denominator > 0
        else None
    )
    _validate_human_review(
        payload,
        missing,
        errors,
        require_blinded=True,
        minimum_ratings=minimum_ratings,
    )


def validate_evidence_package(payload: Any) -> dict[str, Any]:
    """Return a conservative completeness report for one manual V3 package."""
    missing: list[str] = []
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {
            "status": "incomplete",
            "missing": ["object"],
            "errors": ["evidence package must be a JSON object"],
            "human_review_required": True,
        }
    requirement, reference, environment = _validate_common(payload, missing, errors)
    if requirement == "A06":
        _validate_a06(payload, reference, missing, errors)
    elif requirement == "A18":
        _validate_a18(payload, missing, errors)
    elif requirement == "A21":
        _validate_a21(payload, reference, environment, missing, errors)
    elif requirement == "A22":
        _validate_a22(payload, environment, missing, errors)
    status = "ready_for_manual_review" if not missing and not errors else "incomplete"
    return {
        "status": status,
        "requirement_id": requirement,
        "missing": sorted(set(missing)),
        "errors": sorted(set(errors)),
        "human_review_required": True,
        "note": "completeness gate only; this tool never grants V3 acceptance",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, help="JSON evidence package")
    args = parser.parse_args()
    try:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "incomplete", "errors": [str(exc)]}, indent=2))
        return 2
    result = validate_evidence_package(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ready_for_manual_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
