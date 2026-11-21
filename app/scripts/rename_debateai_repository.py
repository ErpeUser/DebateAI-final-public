#!/usr/bin/env python3
"""Verify and optionally rename this private repository using authenticated gh.

Dry-run by default. No credential extraction, branch changes, history rewrites,
visibility changes, user-data operations, or implicit creation of another repo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPOSITORY_ID = 1450951492
OLD_NAME = "ErpeUser/backchannel-v6-private"
NEW_NAME = "ErpeUser/DebateAI"
_ORIGIN = re.compile(
    r"^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"ErpeUser/(?:backchannel-v6-private|DebateAI)(?:\.git)?/?$",
    re.IGNORECASE,
)


class RenameError(RuntimeError):
    pass


def command(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenameError(
            f"{args[0]} unavailable or timed out; check the local installation and login."
        ) from exc
    if result.returncode:
        # Do not echo subprocess output: it may include credentials or private URLs.
        raise RenameError(
            f"{args[0]} failed (exit {result.returncode}); no credentials were printed."
        )
    return result.stdout.strip()


def remote_identity(repo: Path, run) -> dict:
    try:
        identity = json.loads(
            run(
                repo,
                "gh",
                "api",
                f"repositories/{REPOSITORY_ID}",
                "--hostname",
                "github.com",
            )
        )
    except (ValueError, TypeError) as exc:
        raise RenameError("GitHub did not return valid repository metadata.") from exc
    if (
        not isinstance(identity, dict)
        or identity.get("id") != REPOSITORY_ID
        or identity.get("private") is not True
        or identity.get("full_name") not in {OLD_NAME, NEW_NAME}
    ):
        raise RenameError(
            "Repository ID, owner/name or private visibility did not match. Nothing renamed."
        )
    return identity


def rename_repository(repo: Path, *, apply: bool = False, run=command) -> dict:
    repo = repo.expanduser().resolve()
    if Path(run(repo, "git", "rev-parse", "--show-toplevel")).resolve() != repo:
        raise RenameError("Run this against the actual repository root.")
    urls = run(repo, "git", "remote", "get-url", "--all", "origin").splitlines()
    match = _ORIGIN.fullmatch(urls[0]) if len(urls) == 1 else None
    if match is None:
        raise RenameError(
            "Expected one credential-free GitHub origin for this project."
        )
    config = run(repo, "git", "config", "--get-regexp", r"^remote\.origin\.")
    if any(
        line.split(None, 1)[0].lower() == "remote.origin.pushurl"
        for line in config.splitlines()
        if line.strip()
    ):
        raise RenameError(
            "Explicit origin push URLs require semantic review before renaming."
        )
    target_url = match.group(1) + NEW_NAME + ".git"
    before = remote_identity(repo, run)
    result = {
        "repository_id": REPOSITORY_ID,
        "private": True,
        "dry_run": not apply,
        "remote_name": before["full_name"],
        "target_name": NEW_NAME,
        "origin_updated": False,
    }
    if not apply:
        return result
    if before["full_name"] != NEW_NAME:
        run(
            repo,
            "gh",
            "repo",
            "rename",
            "DebateAI",
            "--repo",
            "github.com/" + OLD_NAME,
            "--yes",
        )
    try:
        after = remote_identity(repo, run)
        if after["full_name"] != NEW_NAME:
            raise RenameError("The canonical remote name is not yet verified.")
    except RenameError as exc:
        raise RenameError(
            "Remote rename may have succeeded, but verification failed; origin was not changed. Re-run safely to reconcile."
        ) from exc
    result["remote_name"] = after["full_name"]
    # Recheck origin just before writing; do not silently overwrite a concurrent edit.
    if run(repo, "git", "remote", "get-url", "--all", "origin").splitlines() != urls:
        raise RenameError(
            "Remote rename is verified, but local origin changed concurrently; review it before continuing."
        )
    try:
        if urls[0] != target_url:
            run(repo, "git", "remote", "set-url", "origin", target_url)
        if run(repo, "git", "remote", "get-url", "--all", "origin") != target_url:
            raise RenameError("Local origin verification failed.")
    except RenameError as exc:
        raise RenameError(
            "GitHub is renamed; local origin update is incomplete. Re-run to reconcile without renaming again."
        ) from exc
    result["origin_updated"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the user-authorized rename after verification.",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(rename_repository(args.repo, apply=args.apply), indent=2))
        return 0
    except RenameError as exc:
        parser.exit(2, f"DEBATEAI RENAME BLOCKED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
