"""Generate a bounded, read-only dependency and module-boundary baseline.

The analyzers are deliberately optional.  This command never installs packages,
never edits source files, and exits zero when an optional analyzer is unavailable
unless ``--strict`` is requested.  The checked-in JSON is a triage snapshot,
not a release gate: findings must be reviewed before any rule is promoted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_OUTPUT_BYTES = 2_000_000


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(
    command: list[str], *, cwd: Path, timeout: int = 300
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env={**os.environ, "CI": "1"},
    )


def _relative_command(command: Iterable[str], root: Path) -> list[str]:
    result: list[str] = []
    for value in command:
        if Path(value).name in {"python", "python3"} or "deptry-venv" in value:
            result.append("<python>")
            continue
        if "debateai-deptry-" in value or value.startswith("/tmp/"):
            result.append("<temporary-output>")
            continue
        try:
            result.append(Path(value).resolve().relative_to(root).as_posix())
        except (ValueError, OSError):
            result.append(value)
    return result


def _tool_version(binary: Path, *, cwd: Path, root: Path) -> str | None:
    try:
        result = _run([str(binary), "--version"], cwd=cwd, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    value = (result.stdout or result.stderr).strip().splitlines()
    return value[0].strip() if value else None


def _parse_json(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # A few optional tools print a notice before their JSON reporter.  Keep
        # the parser deterministic by accepting only the first JSON object/list.
        for marker in ("{", "["):
            start = text.find(marker)
            if start < 0:
                continue
            try:
                return json.loads(text[start:])
            except json.JSONDecodeError:
                continue
    return None


def _compact(tool: str, payload: Any) -> dict[str, Any]:
    if tool == "knip":
        issues = payload.get("issues", []) if isinstance(payload, dict) else []
        return {"issues": issues, "issue_count": len(issues)}
    if tool == "dependency-cruiser":
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        return {
            "violations": summary.get("violations", []),
            "rule_counts": {
                "error": summary.get("error", 0),
                "warn": summary.get("warn", 0),
                "info": summary.get("info", 0),
                "ignore": summary.get("ignore", 0),
            },
            "modules": summary.get("totalCruised", 0),
            "dependencies": summary.get("totalDependenciesCruised", 0),
            "tool_issues": summary.get("issues", []),
        }
    if tool == "deptry":
        issues = payload if isinstance(payload, list) else []
        return {"issues": issues, "issue_count": len(issues)}
    if tool == "ruff":
        issues = payload if isinstance(payload, list) else []
        return {"issues": issues, "issue_count": len(issues)}
    if tool == "vulture":
        if isinstance(payload, dict):
            issues = payload.get("issues", [])
        elif isinstance(payload, list):
            issues = payload
        else:
            issues = []
        return {"issues": issues, "issue_count": len(issues)}
    return {"payload": payload}


def _has_findings(tool: str, result: dict[str, Any]) -> bool:
    compact = result.get("result")
    if not isinstance(compact, dict):
        return False
    if tool == "knip" or tool == "deptry":
        return bool(compact.get("issues"))
    if tool == "dependency-cruiser":
        return bool(compact.get("violations") or compact.get("tool_issues"))
    if tool in {"ruff", "vulture"}:
        return bool(compact.get("issues"))
    return False


def _record(
    *,
    tool: str,
    binary: Path | None,
    command: list[str],
    cwd: Path,
    root: Path,
    output: str | None = None,
    parsed: Any | None = None,
    returncode: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "tool": tool,
        "command": _relative_command(command, root),
        "cwd": cwd.relative_to(root).as_posix(),
    }
    if binary is None:
        record.update({"status": "not_installed", "version": None, "result": None})
        return record
    version = _tool_version(binary, cwd=cwd, root=root)
    record["version"] = version
    record["exit_code"] = returncode
    if error:
        record.update({"status": "error", "error": error, "result": None})
    elif parsed is None:
        record.update({"status": "failed", "result": None})
        if output:
            record["output_tail"] = output[-4000:]
    else:
        compact = _compact(tool, parsed)
        record.update(
            {
                "status": "findings"
                if _has_findings(tool, {"result": compact})
                else "clean",
                "result": compact,
            }
        )
    return record


def _node_binary(root: Path, name: str) -> Path | None:
    candidate = root / "app/scripts/static-analysis/node_modules/.bin" / name
    return candidate if candidate.is_file() else None


def _quality_binary(root: Path, name: str) -> Path | None:
    """Resolve a pinned quality tool without installing or mutating the repo."""
    candidates = (
        root / "app/scripts/static-analysis/.venv/bin" / name,
        root / "DebateAI_Generated/static-analysis/bin" / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    located = shutil.which(name)
    return Path(located) if located else None


def _run_quality(root: Path, tool: str) -> dict[str, Any]:
    binary = _quality_binary(root, tool)
    if tool == "ruff":
        command = [
            str(binary or (root / "app/scripts/static-analysis/.venv/bin/ruff")),
            "check",
            "app/backend/app",
            "app/backend/tests",
            "--config",
            "ruff.toml",
            "--output-format",
            "json",
        ]
    else:
        command = [
            str(binary or (root / "app/scripts/static-analysis/.venv/bin/vulture")),
            "app/backend/app",
            "app/backend/tests",
            "--min-confidence",
            "80",
        ]
    if binary is None:
        return _record(tool=tool, binary=None, command=command, cwd=root, root=root)
    try:
        completed = _run(command, cwd=root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _record(
            tool=tool,
            binary=binary,
            command=command,
            cwd=root,
            root=root,
            error=str(exc),
        )
    output = completed.stdout or completed.stderr
    parsed = (
        _parse_json(completed.stdout or completed.stderr)
        if tool == "ruff"
        else [line.strip() for line in output.splitlines() if line.strip()]
    )
    return _record(
        tool=tool,
        binary=binary,
        command=command,
        cwd=root,
        root=root,
        output=output,
        parsed=parsed,
        returncode=completed.returncode,
    )


def _run_knip(root: Path, directory: str, config: str) -> dict[str, Any]:
    binary = _node_binary(root, "knip")
    cwd = root / directory
    command = [
        str(binary or (root / "app/scripts/static-analysis/node_modules/.bin/knip")),
        "--directory",
        ".",
        "--config",
        config,
        "--reporter",
        "json",
        "--no-config-hints",
    ]
    if binary is None:
        return _record(tool="knip", binary=None, command=command, cwd=cwd, root=root)
    try:
        completed = _run(command, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _record(
            tool="knip",
            binary=binary,
            command=command,
            cwd=cwd,
            root=root,
            error=str(exc),
        )
    return _record(
        tool="knip",
        binary=binary,
        command=command,
        cwd=cwd,
        root=root,
        output=completed.stdout,
        parsed=_parse_json(completed.stdout),
        returncode=completed.returncode,
    )


def _run_cruiser(root: Path) -> dict[str, Any]:
    binary = _node_binary(root, "depcruise")
    command = [
        str(
            binary or (root / "app/scripts/static-analysis/node_modules/.bin/depcruise")
        ),
        "--config",
        "app/scripts/static-analysis/dependency-cruiser.config.cjs",
        "--exclude",
        "(^|/)(node_modules|dist|dist-site|\\.astro|build|generated|runtime|DebateAI_Generated)/",
        "--output-type",
        "json",
        "app/frontend/src",
        "app/docs-site/src",
        "app/docs-site/*.mjs",
        "app/docs-site/*.js",
        "app/release-signing-worker/src",
        "app/release-signing-worker/*.mjs",
        "app/release-signing-worker/*.js",
    ]
    if binary is None:
        return _record(
            tool="dependency-cruiser", binary=None, command=command, cwd=root, root=root
        )
    try:
        completed = _run(command, cwd=root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _record(
            tool="dependency-cruiser",
            binary=binary,
            command=command,
            cwd=root,
            root=root,
            error=str(exc),
        )
    return _record(
        tool="dependency-cruiser",
        binary=binary,
        command=command,
        cwd=root,
        root=root,
        output=completed.stdout,
        parsed=_parse_json(completed.stdout),
        returncode=completed.returncode,
    )


def _run_deptry(root: Path, python: str) -> list[dict[str, Any]]:
    command_base = [python, "-m", "deptry"]
    checks = [
        (
            "backend",
            [
                "app/backend",
                "--requirements-files",
                "app/backend/requirements.txt,app/backend/requirements-sortformer.txt",
                "--requirements-files-dev",
                "app/backend/requirements-test.txt",
                "--extend-exclude",
                "app/backend/tests",
                # These are intentional runtime edges that deptry cannot infer.
                # The local script imports run with the script directory on
                # sys.path, while torch is installed by the optional
                # Sortformer/ASR stack.
                "--per-rule-ignores",
                (
                    "DEP001=benchmark_debate_copilot|install_sortformer|video_eval_batch,"
                    "DEP002=nemo_toolkit|uvicorn|asyncpg|python-multipart,"
                    "DEP003=torch"
                ),
            ],
        ),
        (
            "desktop",
            [
                "app/desktop",
                "--requirements-files",
                "app/desktop/requirements.txt",
                "--extend-exclude",
                "app/desktop/tests",
                # Desktop scripts import the backend package and sibling
                # release helpers through their runtime sys.path setup.
                "--per-rule-ignores",
                ("DEP001=build_release_manifest|desktop,DEP002=pyinstaller,DEP003=app"),
            ],
        ),
    ]
    records: list[dict[str, Any]] = []
    try:
        version_run = _run(command_base + ["--version"], cwd=root, timeout=30)
        version = (
            (version_run.stdout or version_run.stderr).strip().splitlines()[0]
            if version_run.returncode == 0
            and (version_run.stdout or version_run.stderr).strip()
            else None
        )
    except (OSError, subprocess.TimeoutExpired):
        version = None
    for name, args in checks:
        with tempfile.TemporaryDirectory(prefix="debateai-deptry-") as temporary:
            output_path = Path(temporary) / f"{name}.json"
            command = (
                command_base + args + ["--json-output", str(output_path), "--no-ansi"]
            )
            try:
                completed = _run(command, cwd=root)
            except (OSError, subprocess.TimeoutExpired) as exc:
                records.append(
                    {
                        "scope": name,
                        "status": "error",
                        "version": version,
                        "command": _relative_command(command, root),
                        "error": str(exc),
                        "result": None,
                    }
                )
                continue
            payload = (
                _parse_json(output_path.read_text(encoding="utf-8"))
                if output_path.exists()
                else None
            )
            compact = _compact("deptry", payload) if payload is not None else None
            records.append(
                {
                    "scope": name,
                    "status": "findings"
                    if compact and compact.get("issues")
                    else ("clean" if compact is not None else "failed"),
                    "version": version,
                    "command": _relative_command(command, root),
                    "exit_code": completed.returncode,
                    "result": compact,
                    **(
                        {"output_tail": (completed.stdout or completed.stderr)[-4000:]}
                        if payload is None and (completed.stdout or completed.stderr)
                        else {}
                    ),
                }
            )
    return records


def build_report(root: Path, *, deptry_python: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_from": {
            "commit": _git_commit(root),
            "repository": "ErpeUser/DebateAI-final-public",
            "branch": "main",
        },
        "scope": {
            "javascript": [
                "app/frontend",
                "app/docs-site",
                "app/release-signing-worker",
            ],
            "python": ["app/backend", "app/desktop"],
            "excluded": [
                "app/desktop/chatgpt_oracle",
                "node_modules",
                "dist",
                "build",
                "generated",
                "runtime",
                "DebateAI_Generated",
            ],
        },
        "gating": "baseline_only",
        "tools": [
            _run_quality(root, "ruff"),
            _run_quality(root, "vulture"),
            _run_knip(
                root, "app/frontend", "../scripts/static-analysis/knip.frontend.json"
            ),
            _run_knip(
                root, "app/docs-site", "../scripts/static-analysis/knip.docs-site.json"
            ),
            _run_knip(
                root,
                "app/release-signing-worker",
                "../scripts/static-analysis/knip.release-worker.json",
            ),
            _run_cruiser(root),
        ],
    }
    deptry = _run_deptry(root, deptry_python or sys.executable)
    report["tools"].append(
        {
            "tool": "deptry",
            "version": next(
                (item.get("version") for item in deptry if item.get("version")), None
            ),
            "scopes": deptry,
            "status": "findings"
            if any(item.get("status") == "findings" for item in deptry)
            else (
                "clean"
                if all(item.get("status") == "clean" for item in deptry)
                else "not_installed"
            ),
        }
    )
    return report


def _git_commit(root: Path) -> str | None:
    try:
        result = _run(["git", "rev-parse", "HEAD"], cwd=root, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--deptry-python",
        default=None,
        help="Python executable containing deptry; no installation is attempted",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when an analyzer is unavailable or cannot emit JSON",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output = (args.output or root / "app/docs/static-analysis-baseline.json").resolve()
    report = build_report(root, deptry_python=args.deptry_python)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    statuses = [
        item.get("status") for item in report["tools"] if item.get("tool") != "deptry"
    ]
    if report["tools"]:
        statuses.extend(
            scope.get("status") for scope in report["tools"][-1].get("scopes", [])
        )
    return (
        1
        if args.strict
        and any(status in {"not_installed", "failed", "error"} for status in statuses)
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
