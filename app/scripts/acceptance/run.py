"""Local acceptance entry: fixed verification profiles, no installs or publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generated_paths import ensure_output_path, output_dir

from acceptance.catalog import PROFILES, build_plan, isolated_environment
from acceptance.execution import redact, run_steps
from acceptance.inventory import read_inventory
from acceptance.reporting import summarize, write_reports


@contextmanager
def exclusive_lock(path):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    identity = os.fstat(fd)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "owner": uuid.uuid4().hex}, stream)
        yield
    finally:
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                path.unlink()
        except FileNotFoundError:
            pass


def safe_path(path):
    for component in (path, *path.parents):
        if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
            raise ValueError("Evidence path traverses a link or junction")


def git(root, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, timeout=10
        )
        return result.stdout if result.returncode == 0 else b""
    except (OSError, subprocess.TimeoutExpired):
        return b""


def provenance(root):
    head = git(root, "rev-parse", "HEAD").decode("ascii", errors="replace").strip()
    origin = (
        git(root, "remote", "get-url", "origin")
        .decode("utf-8", errors="replace")
        .strip()
    )
    canonical = bool(
        re.fullmatch(
            r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
            r"ErpeUser/DebateAI(?:-final-public)?(?:\.git)?/?",
            origin,
        )
    )
    return {
        "source_head": head if re.fullmatch(r"[0-9a-f]{40}", head) else None,
        "canonical_origin": canonical,
        "private_status_reverified_online": False,
        "dirty": bool(git(root, "status", "--porcelain")),
        "tracked_diff_sha256": hashlib.sha256(
            git(root, "diff", "HEAD", "--binary")
        ).hexdigest(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "native_build_verified": False,
        "signature_verified": False,
    }


def resume_profile(path, current):
    with path.open("rb") as stream:
        content = stream.read(16385)
    if len(content) > 16384:
        raise ValueError("Resume state exceeds size limit")
    state = json.loads(content)
    if (
        not isinstance(state, dict)
        or set(state) != {"schema_version", "profile", "source_head"}
        or type(state["schema_version"]) is not int
        or state["schema_version"] != 1
        or state["profile"] not in PROFILES
        or not state["source_head"]
        or state["source_head"] != current["source_head"]
        or current["dirty"]
    ):
        raise ValueError(
            "Resume state is stale or unsafe; start a fresh verification run"
        )
    return state["profile"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--profile", choices=PROFILES, default="Full")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Permit advisory database queries, not provider calls",
    )
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    if not (root / "app/scripts").is_dir():
        parser.error("Expected repository root containing app/scripts")
    current = provenance(root)
    try:
        profile = resume_profile(args.resume, current) if args.resume else args.profile
        parent = output_dir("acceptance", root)
        output = ensure_output_path(
            args.output
            if args.output
            else parent
            / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]),
            "acceptance",
            root,
        )
        safe_path(output)
        safe_path(parent)
        parent.mkdir(parents=True, exist_ok=True)
        lock = (
            exclusive_lock(parent / ".run.lock")
            if profile != "Report"
            else nullcontext()
        )
        with lock:
            output.mkdir(parents=True, exist_ok=False, mode=0o700)
            inventory, issues = read_inventory(root)
            if not current["canonical_origin"]:
                issues.append("Canonical Git origin was not confirmed")
            if not current["source_head"]:
                issues.append("Source Git HEAD unavailable")
            plan = build_plan(
                profile, root, python=sys.executable, allow_network=args.allow_network
            )
            secrets = tuple(
                value
                for key, value in os.environ.items()
                if re.search(r"(?i)(secret|token|password|api.?key)", key)
                and len(value) >= 4
            )
            rows = []
            with (output / "task-events.jsonl").open("x", encoding="utf-8") as journal:

                def completed(row):
                    rows.append(row)
                    journal.write(json.dumps(row, ensure_ascii=True) + "\n")
                    journal.flush()
                    os.fsync(journal.fileno())
                    print(f"TASK-END {row['id']} {row['status']}", flush=True)

                with tempfile.TemporaryDirectory(
                    prefix="debateai-acceptance-"
                ) as temporary:
                    env = isolated_environment(root, Path(temporary), os.environ)
                    try:
                        run_steps(
                            plan,
                            root,
                            output / "logs",
                            env=env,
                            secrets=secrets,
                            on_result=completed,
                        )
                    except KeyboardInterrupt:
                        completed(
                            {
                                "id": "interrupted",
                                "status": "FAILED",
                                "reason": "Caller interruption; remaining tasks not executed",
                            }
                        )
                    except (OSError, ValueError, RuntimeError) as exc:
                        completed(
                            {
                                "id": "runner-error",
                                "status": "FAILED",
                                "reason": type(exc).__name__,
                            }
                        )
            after = provenance(root)
            if (
                after["source_head"] != current["source_head"]
                or after["tracked_diff_sha256"] != current["tracked_diff_sha256"]
            ):
                issues.append(
                    "Tracked source changed during verification; results are not a stable release proof"
                )
            report = summarize(
                profile,
                rows,
                inventory,
                [redact(issue, secrets) for issue in issues],
                provenance=current,
            )
            if any(row["id"] == "interrupted" for row in rows):
                report["exit_code"] = 130
            write_reports(output, report)
            with (output / "resume.json").open("x", encoding="utf-8") as stream:
                json.dump(
                    {
                        "schema_version": 1,
                        "profile": profile,
                        "source_head": current["source_head"],
                    },
                    stream,
                    indent=2,
                )
            print(
                f"REPORT {output}\nPROJECT IN_ARBEIT\nEXIT {report['exit_code']}",
                flush=True,
            )
            return report["exit_code"]
    except (OSError, ValueError) as exc:
        print(
            "Acceptance preflight blocked: " + type(exc).__name__ + ": " + str(exc),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
