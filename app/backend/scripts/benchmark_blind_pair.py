"""Run two local production replays and export failure-preserving blind cases.

Uses benchmark_debate_copilot.py in separate, sequential child processes. Never
import its monkey-patched provider state into a running application. This is a
headless text-path experiment, not Windows audio or screen-paint acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.services.response_contract import normalize_response_event
from benchmark_debate_copilot import endpoint_scope

MODES = {"persuasive": "ueberzeugen", "forceful": "hart"}
MAX_BYTES = 512 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
BACKEND = Path(__file__).resolve().parents[1]


def fixture_digest(turns: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(
            turns, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def validate_turns(turns: object) -> list[dict]:
    if not isinstance(turns, list) or not 1 <= len(turns) <= 50:
        raise ValueError(
            "Use 1 to 50 ordered fixture turns (both modes yield at most 100 pairs)."
        )
    result = []
    for turn in turns:
        if not isinstance(turn, dict):
            raise ValueError("Each fixture turn must be an object.")
        for key in ("speaker", "text"):
            if not isinstance(turn.get(key), str) or not turn[key].strip():
                raise ValueError("Each turn needs non-empty speaker and text strings.")
        result.append({key: turn[key].strip() for key in ("speaker", "text")})
    if len("\n".join(f"{t['speaker']}: {t['text']}" for t in result)) > 12000:
        raise ValueError(
            "Causal fixture context exceeds 12000 characters; split into separate experiments."
        )
    return result


def _latency(value: object) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    ):
        return float(value)
    return None


def _records(report: dict, mode: str, digest: str, turns: list[dict]) -> dict:
    if report.get("measurement_path") != "transcript_ingest_to_debate_update":
        raise ValueError("Only production replay reports are accepted.")
    if report.get("fixture_sha256") != digest:
        raise ValueError("The report uses a different fixture.")
    if report.get("mode") != mode or report.get("generation_egress") != "loopback":
        raise ValueError("Mode or local endpoint contract mismatch.")
    if report.get("research_egress") != "disabled":
        raise ValueError("Research must be disabled for this local paired experiment.")
    result = {}
    for row in report.get("turns", []):
        index = row.get("turn_index")
        if type(index) is not int or index not in range(len(turns)):
            raise ValueError("Invalid turn index in report.")
        if index in result:
            raise ValueError("A duplicate turn index cannot be silently discarded.")
        if (
            row.get("text") != turns[index]["text"]
            or row.get("speaker") != turns[index]["speaker"]
        ):
            raise ValueError("Reported turn does not match the causal fixture.")
        result[index] = row
    return result


def build_suite(
    turns: list[dict], reports: dict, candidate_ids: list[str], provenance: dict
) -> dict:
    turns = validate_turns(turns)
    if (
        len(candidate_ids) != 2
        or len(set(candidate_ids)) != 2
        or any(
            not isinstance(x, str) or not x.strip() or len(x) > 200
            for x in candidate_ids
        )
    ):
        raise ValueError(
            "Provide exactly two distinct candidate identifiers, at most 200 characters."
        )
    if not reports or any(
        mode not in MODES or len(rows) != 2 for mode, rows in reports.items()
    ):
        raise ValueError("Provide two reports per supported mode.")
    digest = fixture_digest(turns)
    cases, failures = [], []
    failed_candidates = 0
    for mode, pair in reports.items():
        indexed = [_records(r, mode, digest, turns) for r in pair]
        context = []
        for i, turn in enumerate(turns):
            context.append(f"{turn['speaker']}: {turn['text']}")
            context_text = "\n".join(context)
            context_hash = hashlib.sha256(context_text.encode("utf-8")).hexdigest()
            case_id = f"de-{i + 1:03d}"
            candidates, errors = [], []
            for j, rows in enumerate(indexed):
                row = rows.get(i, {})
                rec = row.get("recommendation") or {}
                primary = (
                    "counter_question"
                    if rec.get("primary_move") == "question"
                    else "answer_now"
                )
                text = rec.get(primary)
                contract_status = (
                    row.get("status")
                    if row.get("status")
                    in {"ok", "timeout", "empty", "stale", "error", "abstent"}
                    else "error"
                )
                normalize_response_event(
                    {
                        "case_id": case_id,
                        "turn_id": str(i),
                        "status": contract_status,
                        "failure_class": "none"
                        if contract_status == "ok"
                        else contract_status,
                        "first_speakable_ms": _latency(row.get("first_update_ms")),
                        "first_update_ms": _latency(row.get("first_update_ms")),
                        "final_update_ms": _latency(row.get("current_update_ms")),
                        "deep_revision_ms": _latency(row.get("deep_revision_ms")),
                        "accepted_model_ms": _latency(row.get("accepted_model_ms")),
                    }
                )
                if (
                    row.get("status") != "ok"
                    or not isinstance(text, str)
                    or not text.strip()
                    or len(text) > 4000
                ):
                    failed_candidates += 1
                    # Never copy provider exceptions, paths, endpoint credentials or raw logs.
                    errors.append(
                        {
                            "candidate_id": candidate_ids[j],
                            "status": "failed",
                            "reason": "missing_or_failed_speakable_output",
                        }
                    )
                    continue
                prompt_hash = pair[j].get("prompt_template_sha256")
                if not isinstance(prompt_hash, str) or not re.fullmatch(
                    "[a-f0-9]{64}", prompt_hash
                ):
                    prompt_hash = None
                candidates.append(
                    {
                        "id": candidate_ids[j],
                        "text": text.strip(),
                        "context_sha256": context_hash,
                        "prompt_template_sha256": prompt_hash,
                        "first_update_ms": _latency(row.get("first_update_ms")),
                        "accepted_model_ms": _latency(row.get("current_update_ms")),
                    }
                )
            if errors:
                failures.append(
                    {"case_id": case_id, "mode": MODES[mode], "errors": errors}
                )
            else:
                cases.append(
                    {
                        "case_id": case_id,
                        "mode": MODES[mode],
                        "context": context_text,
                        "context_sha256": context_hash,
                        "candidates": candidates,
                    }
                )
    attempted = len(turns) * len(reports)
    return {
        "schema_version": 1,
        "kind": "production_replay_blind_suite",
        "created_at": datetime.now(UTC).isoformat(),
        "cases": cases,
        "failures": failures,
        "summary": {
            "attempted_pairs": attempted,
            "votable_pairs": len(cases),
            "failed_pairs": len(failures),
            "attempted_candidates": attempted * 2,
            "failed_candidates": failed_candidates,
        },
        "fixture_sha256": digest,
        "provenance": provenance,
        "settings_changed": False,
        "factual_status": "unverified",
        "limitations": [
            "Headless production replay; no real screen-paint or microphone acceptance.",
            "Prompt hash covers the resolved live template, not all dynamically formatted inputs.",
            "Context hash covers the available causal fixture prefix; the production path may select a shorter window.",
            "Prompt fingerprints must match before comparing model quality; no automatic winner is selected.",
            "First turn can be cold; subsequent turns can be warm. No controlled hardware ranking.",
            "A trusted loopback server must not forward prompts to a remote provider.",
            "Failed pairs are not votable, but remain in the experiment denominator.",
        ],
    }


def write_new_json(path: Path, value: dict) -> None:
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError(
            "Export exceeds the laboratory 512 KiB import limit; use a shorter fixture."
        )
    # Exclusive creation: never overwrite an existing user result. On a write
    # failure remove only the new file this call created.
    with path.open("xb") as stream:
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            path.unlink(missing_ok=True)
            raise


def _source_provenance() -> dict:
    root = BACKEND.parents[1]
    info = {
        "source_commit": None,
        "tracked_source_dirty": None,
        "platform": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "measurement_path": "headless production replay",
    }
    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
        if re.fullmatch("[a-f0-9]{40}", commit):
            info["source_commit"] = commit
        state = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        info["tracked_source_dirty"] = bool(state.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return info


def run_child(
    model: str,
    mode: str,
    endpoint: str,
    fixture: Path,
    output: Path,
    timeout: float,
    turn_count: int,
) -> dict:
    if endpoint_scope(endpoint) != "loopback":
        raise ValueError("Only a trusted loopback HTTP endpoint is permitted.")
    command = [
        sys.executable,
        str(Path(__file__).with_name("benchmark_debate_copilot.py")),
        "--endpoint",
        endpoint,
        "--model",
        model,
        "--mode",
        mode,
        "--fixture",
        str(fixture),
        "--output",
        str(output),
        "--timeout",
        str(timeout),
        "--skip-probes",
    ]
    return execute_report(command, output, (turn_count + 1) * timeout + 30)


def report_requires_stop(report: dict) -> bool:
    return any(
        row.get("error_type") == "TimeoutError" for row in report.get("turns", [])
    )


def execute_report(command: list[str], output: Path, deadline_seconds: float) -> dict:
    """Bound one owned Python worker; never signal an external model server."""
    if not math.isfinite(deadline_seconds) or deadline_seconds <= 0:
        raise ValueError("Invalid child deadline")
    # No shell, no growing PIPE/log buffer, no API key in argv. This child is
    # ours; we never kill the user's separately running Ollama server.
    with subprocess.Popen(
        command, cwd=BACKEND, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ) as child:
        try:
            code = child.wait(timeout=deadline_seconds)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)
            raise TimeoutError(
                "Owned benchmark process exceeded its deadline"
            ) from None
        except BaseException:
            # Includes an explicit Ctrl+C by the person running the experiment.
            # Reap only our child; never signal Ollama or unrelated processes.
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
            raise
    if (
        code not in (0, 1)
        or not output.is_file()
        or output.stat().st_size > MAX_REPORT_BYTES
    ):
        raise RuntimeError("Benchmark produced no bounded report")
    value = json.loads(output.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Benchmark report must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-a", required=True)
    parser.add_argument("--model-b", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/v1")
    parser.add_argument(
        "--fixture", type=Path, default=BACKEND / "fixtures/debate_calibration_de.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    try:
        if endpoint_scope(args.endpoint) != "loopback":
            raise ValueError("Use a trusted loopback HTTP model endpoint.")
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
            raise ValueError(
                "Timeout must be finite, greater than zero and at most 300 seconds."
            )
        if args.model_a == args.model_b or any(
            not m.strip() or len(m) > 200 or any(ord(c) < 32 for c in m)
            for m in (args.model_a, args.model_b)
        ):
            raise ValueError("Choose two distinct installed local models.")
        if args.output.exists():
            raise FileExistsError(
                "Output already exists; choose a new result filename."
            )
        if args.fixture.stat().st_size > MAX_BYTES:
            raise ValueError("Fixture file is too large.")
        turns = validate_turns(json.loads(args.fixture.read_text(encoding="utf-8")))
        reports = {}
        with tempfile.TemporaryDirectory(prefix="debateai-pair-") as temp:
            fixture = Path(temp) / "fixture.json"
            fixture.write_text(json.dumps(turns, ensure_ascii=False), encoding="utf-8")
            aborted = False
            for n, mode in enumerate(MODES):
                rows = [None, None]
                # Counterbalance model execution order across modes, not parallel
                # GPU contention. This does not by itself remove warmup bias.
                for j in [0, 1] if n == 0 else [1, 0]:
                    try:
                        if aborted:
                            raise TimeoutError(
                                "Prior process timeout; no further model work started"
                            )
                        rows[j] = run_child(
                            [args.model_a, args.model_b][j],
                            mode,
                            args.endpoint,
                            fixture,
                            Path(temp) / f"{mode}-{j}.json",
                            args.timeout,
                            len(turns),
                        )
                        if report_requires_stop(rows[j]):
                            aborted = True
                    except (
                        OSError,
                        ValueError,
                        RuntimeError,
                        subprocess.SubprocessError,
                    ) as error:
                        if isinstance(error, TimeoutError):
                            aborted = True
                        rows[j] = {
                            "mode": mode,
                            "measurement_path": "transcript_ingest_to_debate_update",
                            "fixture_sha256": fixture_digest(turns),
                            "generation_egress": "loopback",
                            "research_egress": "disabled",
                            "turns": [],
                            "run_status": "failed",
                        }
                reports[mode] = rows
            suite = build_suite(
                turns, reports, [args.model_a, args.model_b], _source_provenance()
            )
            write_new_json(args.output, suite)
        print(
            f"Pairs: {suite['summary']['votable_pairs']}/{suite['summary']['attempted_pairs']}; "
            f"failed: {suite['summary']['failed_pairs']}. No settings changed."
        )
        return 1 if suite["summary"]["failed_pairs"] else 0
    except (OSError, ValueError, RuntimeError) as error:
        print(
            f"Comparison not completed ({type(error).__name__}); check local inputs and dependencies.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
