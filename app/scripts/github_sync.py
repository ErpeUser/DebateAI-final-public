#!/usr/bin/env python3
"""Inspect GitHub branches and pull requests before updating the default branch.

This command is deliberately read-only on GitHub. It fetches remote refs,
reports every non-default branch and open pull request, and optionally performs
an ff-only pull of the default branch. Integrating a candidate remains a
reviewed local commit because GitHub cannot decide whether two changes should
be cherry-picked, merged, or combined.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORY = "ErpeUser/DebateAI-final-public"


def command(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def repository_from_remote(remote: str) -> str:
    value = command("git", "remote", "get-url", remote)
    if value.startswith("git@github.com:"):
        value = value.split(":", 1)[1]
    else:
        parsed = urlparse(value)
        value = parsed.path.lstrip("/")
    value = value.removesuffix(".git").strip("/")
    if not re.fullmatch(r"[^/]+/[^/]+", value):
        raise RuntimeError(f"Remote is not a GitHub repository: {value}")
    return value


def gh_json(repository: str, endpoint: str, *, paginate: bool = False):
    path = f"repos/{repository}"
    if endpoint:
        path += f"/{endpoint}"
    arguments = ["gh", "api"]
    if paginate:
        arguments.extend(["--paginate", "--slurp"])
    arguments.append(path)
    payload = json.loads(command(*arguments))
    if paginate and payload and isinstance(payload[0], list):
        return [item for page in payload for item in page]
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repository", default="")
    parser.add_argument("--pull", action="store_true",
                        help="Fetch, inspect, then ff-only pull the default branch")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero when non-default branches or open PRs exist")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    repository = args.repository or repository_from_remote(args.remote)
    metadata = gh_json(repository, "")
    default_branch = metadata.get("default_branch")
    if not default_branch:
        raise RuntimeError("GitHub did not return a default branch")
    current_branch = command("git", "branch", "--show-current")
    if current_branch != default_branch:
        raise RuntimeError(
            f"Checkout must be on GitHub default branch {default_branch!r}, "
            f"currently on {current_branch or 'detached HEAD'!r}"
        )
    dirty = bool(command("git", "status", "--porcelain"))
    command("git", "fetch", "--prune", args.remote)
    branches = gh_json(repository, "branches?per_page=100", paginate=True)
    pull_requests = gh_json(repository, "pulls?state=open&per_page=100", paginate=True)
    non_default = [
        {"name": branch["name"], "sha": branch["commit"]["sha"]}
        for branch in branches if branch.get("name") != default_branch
    ]
    open_prs = [
        {
            "number": pr["number"],
            "title": pr["title"],
            "head": pr["head"]["ref"],
            "head_sha": pr["head"]["sha"],
            "base": pr["base"]["ref"],
            "updated_at": pr["updated_at"],
            "draft": pr["draft"],
        }
        for pr in pull_requests
    ]
    result = {
        "repository": repository,
        "remote": args.remote,
        "default_branch": default_branch,
        "current_branch": current_branch,
        "dirty": dirty,
        "non_default_branches": non_default,
        "open_pull_requests": open_prs,
        "pulled": False,
        "blocked_pull": False,
    }
    if args.pull:
        if dirty:
            raise RuntimeError("Refusing to pull with uncommitted local changes")
        if args.strict and (non_default or open_prs):
            result["blocked_pull"] = True
        else:
            command("git", "pull", "--ff-only", args.remote, default_branch)
            result["pulled"] = True

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Repository: {repository}")
        print(f"Default branch: {default_branch}")
        print(f"Pulled: {'yes' if result['pulled'] else 'no'}")
        if result["blocked_pull"]:
            print("Pull blocked until candidates are reviewed")
        print(f"Non-default branches: {len(non_default)}")
        for branch in non_default:
            print(f"  - {branch['name']} {branch['sha'][:12]}")
        print(f"Open pull requests: {len(open_prs)}")
        for pr in open_prs:
            marker = "draft" if pr["draft"] else "open"
            print(f"  - #{pr['number']} [{marker}] {pr['title']} ({pr['head']})")

    if args.strict and (non_default or open_prs):
        print(
            "Review each candidate on the default branch before declaring the "
            "GitHub update complete.",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"GitHub sync check failed: {error}", file=sys.stderr)
        raise SystemExit(2)
