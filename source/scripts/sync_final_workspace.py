#!/usr/bin/env python3
"""Synchronize the ACTUAL Windows workspace with the latest fixed origin/master.

Outdated tracked working-tree edits are removed from the active checkout,
after being secured in a named Git stash for Codex's semantic review.
Divergent committed work is kept on a rescue branch and, when possible,
rebased onto the latest remote. No user data, untracked files or ignored
runtime directories are deleted. Codex follows AGENTS.md to inspect,
discard obsolete work and selectively integrate genuinely unique improvements.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = "ErpeUser/backchannel-v6-private"
MINIMUM_FIXED_COMMIT = "b7d48730bed175d4e4e7e5b2a6a6acf309f6dfb4"
ALLOWED_ORIGIN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"ErpeUser/backchannel-v6-private(?:\.git)?/?$",
    re.IGNORECASE,
)


class SyncError(RuntimeError):
    pass


def git(repo: Path, *args: str, ok: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, encoding="utf-8", errors="replace", capture_output=True,
        check=False,
    )
    if result.returncode not in ok:
        # Do not echo captured output: remote URLs may contain credentials.
        raise SyncError(f"git {args[0]} failed (exit {result.returncode}).")
    return result


def present(repo: Path, *args: str) -> bool:
    result = git(repo, *args, ok=(0, 1))
    return result.returncode == 0


def branch_safe_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"codex/final-sync-backup-{stamp}-{secrets.token_hex(4)}"


def checkout_root(path: Path) -> Path:
    return Path(git(path, "rev-parse", "--show-toplevel").stdout.strip()).resolve()


def validate_origin(url: str, expected: str | None) -> None:
    if expected is None:
        if not ALLOWED_ORIGIN.fullmatch(url.strip()):
            raise SyncError("origin is not the expected private Debate AI repository.")
    elif url.strip() != expected.strip():
        raise SyncError("origin does not match the explicitly expected remote.")


def sync(repo: Path, expected_remote: str | None, minimum_commit: str | None = None) -> dict:
    repo = repo.expanduser().resolve()
    if not repo.is_dir():
        raise SyncError("The requested local project directory does not exist.")
    if checkout_root(repo) != repo:
        raise SyncError("Use the repository ROOT, not its source/ directory.")
    validate_origin(git(repo, "remote", "get-url", "origin").stdout, expected_remote)
    current_branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if current_branch != "master":
        raise SyncError(
            "The existing worktree is not on master. Codex must first inspect "
            "the active branch and transfer meaningful changes to master."
        )
    for path in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD"):
        marker = Path(git(repo, "rev-parse", "--git-path", path).stdout.strip())
        if not marker.is_absolute():
            marker = repo / marker
        if marker.exists():
            raise SyncError("A Git merge/rebase/cherry-pick is in progress. Codex must resolve it first.")

    start_head = git(repo, "rev-parse", "HEAD").stdout.strip()
    # Explicit remote-tracking refspec prevents FETCH_HEAD-only updates.
    git(repo, "fetch", "--no-tags", "origin", "+refs/heads/master:refs/remotes/origin/master")
    remote_head = git(repo, "rev-parse", "refs/remotes/origin/master").stdout.strip()
    if minimum_commit:
        check = git(
            repo, "merge-base", "--is-ancestor", minimum_commit,
            "refs/remotes/origin/master", ok=(0, 1, 128),
        )
        if check.returncode != 0:
            raise SyncError("Remote master does not contain the known final-fix commit; refusing a downgrade.")
    result = {
        "repository": REPOSITORY,
        "local_worktree": str(repo),
        "previous_local_head": start_head,
        "fetched_origin_master": remote_head,
        "local_changes_stash": None,
        "local_commits_backup": None,
        "action": None,
        "next_action": None,
    }

    # Only stash TRACKED changes: untracked/ignored user data and .env files
    # are neither staged, cleaned, deleted nor published.
    tracked = bool(git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip())
    if tracked:
        old_stash = git(repo, "rev-parse", "--verify", "-q", "refs/stash", ok=(0, 1)).stdout.strip()
        git(repo, "stash", "push", "-m", "codex-final-sync-tracked-worktree")
        new_stash = git(repo, "rev-parse", "--verify", "-q", "refs/stash", ok=(0, 1)).stdout.strip()
        if not new_stash or new_stash == old_stash:
            raise SyncError("Tracked changes were not secured in Git stash; refusing overwrite.")
        result["local_changes_stash"] = new_stash

    try:
        if start_head == remote_head:
            result["action"] = "already_at_remote_head"
        elif present(repo, "merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/master"):
            git(repo, "merge", "--ff-only", "refs/remotes/origin/master")
            result["action"] = "fast_forward_to_newest_master"
        else:
            backup = branch_safe_name()
            git(repo, "branch", backup, start_head)
            result["local_commits_backup"] = backup
            if present(repo, "merge-base", "--is-ancestor", "refs/remotes/origin/master", "HEAD"):
                result["action"] = "local_commits_ahead_review_needed"
            else:
                # No ours/theirs auto-conflict strategy: Codex must choose
                # by comparing functionality, not by timestamps alone.
                rebase = subprocess.run(
                    ["git", "-C", str(repo), "rebase", "refs/remotes/origin/master"],
                    text=True, capture_output=True, check=False,
                )
                if rebase.returncode:
                    result["action"] = "rebase_conflict_codex_must_resolve"
                    result["next_action"] = (
                        "Codex: resolve conflict using latest remote as baseline; "
                        "preserve truly unique improvements; git rebase --continue."
                    )
                    return result
                result["action"] = "rebased_local_commits_onto_newest_master"
    finally:
        result["current_local_head"] = git(repo, "rev-parse", "HEAD").stdout.strip()

    result["matches_origin_master"] = result["current_local_head"] == remote_head
    result["has_tracked_worktree_changes"] = bool(
        git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip()
    )
    if result["local_changes_stash"]:
        result["next_action"] = (
            "Codex: inspect named stash versus newest master; discard obsolete code; "
            "selectively restore genuinely new improvements, test and publish if appropriate."
        )
    elif not result["matches_origin_master"]:
        result["next_action"] = (
            "Codex: review unique local commits, discard obsolete ones, test valuable changes, "
            "push to origin/master (NEVER force-push), then verify HEAD equals origin/master."
        )
    else:
        result["next_action"] = (
            "Source now matches newest master. Build and install the current Windows bundle."
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[2],
        help="Existing local repository root, not a temporary clone or source/.",
    )
    parser.add_argument(
        "--minimum-commit", default=MINIMUM_FIXED_COMMIT,
        help="Required ancestor of origin/master; rejects older remote history.",
    )
    parser.add_argument(
        "--expected-remote", default=None,
        help="Override expected origin URL ONLY for isolated fixture tests.",
    )
    args = parser.parse_args()
    try:
        outcome = sync(args.repo, args.expected_remote, args.minimum_commit)
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 2 if outcome["action"] == "rebase_conflict_codex_must_resolve" else 0
    except SyncError as exc:
        print(f"FINAL SYNC BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
