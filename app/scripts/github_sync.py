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
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORY = "ErpeUser/DebateAI-final-public"

EXTENSION_PATH_RE = re.compile(
    r"(^|/)(browser-extension|web-extension|extension|webext)(/|$)",
    re.IGNORECASE,
)
DESKTOP_PREFIXES = (
    "app/backend/",
    "app/frontend/",
    "app/desktop/",
    "app/ai/",
    "app/.env.example",
    "app/docker-compose",
    "app/scripts/build_debate_assistant.ps1",
    "app/scripts/recover_release.py",
    "app/scripts/setup_debate_assistant.ps1",
    "Start-DebateAI.cmd",
    "Start-DebateAI.ps1",
)
SHORTCUT_PREFIXES = ("Start-DebateAI.", "app/desktop/launcher.py")


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


def changed_impact(paths: list[str]) -> dict[str, object]:
    """Classify generated-client work required by a pulled source change."""
    extension_paths = [path for path in paths if EXTENSION_PATH_RE.search(path)]
    desktop_paths = [path for path in paths if path.startswith(DESKTOP_PREFIXES)]
    shortcut_paths = [path for path in paths if path.startswith(SHORTCUT_PREFIXES)]
    return {
        "changed_paths": paths,
        "extension_paths": extension_paths,
        "desktop_paths": desktop_paths,
        "shortcut_paths": shortcut_paths,
        "extension_action": "rebuild-required" if extension_paths else "none",
        "desktop_action": "rebuild-required" if desktop_paths else "none",
        "shortcut_action": "verify-after-build" if shortcut_paths else "none",
    }


def run_affected_build(impact: dict[str, object]) -> dict[str, object]:
    """Rebuild and smoke-test generated desktop/extension outputs."""
    desktop_paths = impact["desktop_paths"]
    extension_paths = impact["extension_paths"]
    commands: list[str] = []
    statuses: list[str] = []
    if desktop_paths:
        if os.name != "nt":
            statuses.append("desktop-skipped-non-windows")
        else:
            script = ROOT / "Start-DebateAI.ps1"
            commands.append(
                "powershell.exe -NoProfile -ExecutionPolicy Bypass "
                f"-File {script} -Rebuild -NoLaunch"
            )
            command(
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-Rebuild",
                "-NoLaunch",
            )
            statuses.append("desktop-rebuilt-and-smoke-tested")
            if impact["shortcut_paths"]:
                command(
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                    "-Check",
                )
                statuses.append("launcher-verified")
    if extension_paths:
        candidates = (
            ROOT / "browser-extension",
            ROOT / "web-extension",
            ROOT / "extension",
            ROOT / "app" / "browser-extension",
            ROOT / "app" / "web-extension",
            ROOT / "app" / "extension",
        )
        extension_root = next(
            (path for path in candidates if (path / "package.json").is_file()),
            None,
        )
        if extension_root is None:
            raise RuntimeError(
                "Extension changes were pulled, but no package.json build entry "
                "exists in a recognized extension directory."
            )
        npm = "npm.cmd" if os.name == "nt" else "npm"
        command(npm, "run", "build", "--prefix", str(extension_root))
        commands.append(f"{npm} run build --prefix {extension_root}")
        statuses.append("extension-rebuilt")
    if not statuses:
        return {"status": "not-needed", "command": ""}
    return {"status": "+".join(statuses), "command": " && ".join(commands)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--repository", default="")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Fetch, inspect, then ff-only pull the default branch",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when non-default branches or open PRs exist",
    )
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
        for branch in branches
        if branch.get("name") != default_branch
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
    before_pull = command("git", "rev-parse", "HEAD")
    if args.pull:
        if dirty:
            raise RuntimeError("Refusing to pull with uncommitted local changes")
        if args.strict and (non_default or open_prs):
            result["blocked_pull"] = True
        else:
            command("git", "pull", "--ff-only", args.remote, default_branch)
            result["pulled"] = True

    after_pull = command("git", "rev-parse", "HEAD")
    changed = []
    if before_pull != after_pull:
        changed = command(
            "git", "diff", "--name-only", f"{before_pull}..{after_pull}"
        ).splitlines()
    impact = changed_impact(changed)
    result["impact"] = impact
    result["affected_build"] = (
        run_affected_build(impact)
        if result["pulled"]
        else {"status": "not-run", "command": ""}
    )

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Repository: {repository}")
        print(f"Default branch: {default_branch}")
        print(f"Pulled: {'yes' if result['pulled'] else 'no'}")
        if result["blocked_pull"]:
            print("Pull blocked until candidates are reviewed")
        print(f"Desktop impact: {impact['desktop_action']}")
        print(f"Extension impact: {impact['extension_action']}")
        print(f"Shortcut impact: {impact['shortcut_action']}")
        print(f"Affected build: {result['affected_build']['status']}")
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
