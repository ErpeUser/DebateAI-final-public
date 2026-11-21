#!/usr/bin/env python3
"""Fail CI when versioned files violate DebateAI's canonical source layout.

This checks Git's indexed files AND non-ignored new local files. It never
creates Generated, reads credentials, or touches installed/user data.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ROOT_FILES = frozenset(
    {
        ".gitignore",
        ".gitattributes",
        "pyproject.toml",
        "ruff.toml",
        "AGENTS.md",
        "LICENSE",
        "README.md",
        "Start-DebateAI.cmd",
        "Start-DebateAI.ps1",
    }
)
ROOT_DIRECTORIES = frozenset({".github", "app"})
APP_ROOT_FILES = frozenset(
    {
        ".dockerignore",
        ".env.example",
        "AGENTS.md",
        "LICENSE",
        "README.md",
        "dev.ps1",
        "release.ps1",
        "test-changed.ps1",
        "docker-compose.yml",
        "docker-compose.gpu.yml",
        "docker-compose.debate.yml",
    }
)
APP_DIRECTORIES = frozenset(
    {
        ".ai",
        ".github",
        ".sentrux",
        "ai",
        "backend",
        "desktop",
        "docs",
        "docs-site",
        "frontend",
        "release-signing-worker",
        "scripts",
        "site",
        "tools",
    }
)
PRIVATE_GENERATED_PATHS = frozenset({"app/docs/acceptance", "app/.ai"})
REQUIRED_FILES = frozenset(
    {
        ".gitignore",
        ".gitattributes",
        "AGENTS.md",
        "LICENSE",
        "README.md",
        "Start-DebateAI.cmd",
        "Start-DebateAI.ps1",
        ".github/CODEOWNERS",
        ".github/workflows/tests.yml",
        ".github/workflows/structure.yml",
        ".github/workflows/security.yml",
        ".github/workflows/deploy-site.yml",
        ".github/workflows/desktop-release.yml",
        "app/AGENTS.md",
        "app/README.md",
        "app/backend/app/main.py",
        "app/frontend/src/App.tsx",
        "app/frontend/package-lock.json",
        "app/desktop/debateai.spec",
        "app/desktop/release_signing_keys.json",
        "app/site/index.html",
        "app/docs-site/worker.js",
        "app/docs-site/package-lock.json",
        "app/scripts/workspace_refs.py",
        "app/scripts/generated_paths.py",
        "app/scripts/github_sync.py",
        "app/scripts/tests/test_github_sync.py",
        "app/scripts/verify_repository_layout.py",
    }
)
IGNORED_COMPONENTS = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        ".release-venv",
        ".tox",
        ".nox",
        ".cache",
        "dist",
        "build",
        "release-assets",
        "graphify-out",
        ".worktrees",
        ".superpowers",
    }
)
FORBIDDEN_SUFFIXES = (
    ".exe",
    ".msi",
    ".dll",
    ".dylib",
    ".so",
    ".onnx",
    ".zip",
    ".tar.gz",
    ".7z",
    ".dmg",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".db-wal",
    ".db-shm",
    ".p12",
    ".pfx",
    ".key",
    ".pem",
    ".log",
)
ALLOWED_ENV_TEMPLATES = frozenset({".env.example", ".env.sample", ".env.template"})


def tracked_and_new_files(root: Path = ROOT) -> list[str]:
    """Return indexed and non-ignored untracked files, including staged changes."""
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        capture_output=True,
        check=True,
    )
    return sorted(
        {
            name.decode("utf-8", "surrogateescape")
            for name in result.stdout.split(b"\0")
            if name
        }
    )


def validate_paths(paths: Iterable[str]) -> list[str]:
    """Return deterministic violations. Empty list means the layout is valid."""
    present = set(paths)
    errors: set[str] = set()
    missing = REQUIRED_FILES - present
    for filename in sorted(missing):
        errors.add(f"Missing required tracked source: {filename}")

    cased: dict[str, str] = {}
    for path in sorted(present):
        if not isinstance(path, str) or not path:
            errors.add(f"Invalid file path: {path!r}")
            continue
        if (
            path.startswith("/")
            or "\\" in path
            or "\x00" in path
            or re.search(r"[\x00-\x1f\x7f]", path)
        ):
            errors.add(f"Non-canonical or unsafe file path: {path}")
            continue
        parts = path.split("/")
        if any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in PRIVATE_GENERATED_PATHS
        ):
            errors.add(f"Private/generated evidence must stay outside source: {path}")
        if any(part in {"", ".", ".."} or part.endswith((" ", ".")) for part in parts):
            errors.add(f"Non-canonical file path: {path}")
            continue
        fold = path.casefold()
        if fold in cased and cased[fold] != path:
            errors.add(f"Case-insensitive path collision: {cased[fold]} / {path}")
        cased[fold] = path

        if parts[0] not in ROOT_DIRECTORIES:
            if path not in ROOT_FILES:
                errors.add(f"Unexpected root location: {path}")
            continue

        if parts[0] == "app":
            if len(parts) < 2 or (
                parts[1] not in APP_DIRECTORIES
                and path not in {"app/" + item for item in APP_ROOT_FILES}
            ):
                errors.add(f"Unexpected application root location: {path}")
                continue
            if len(parts) > 2 and parts[1] == ".github" and parts[2] == "workflows":
                errors.add(f"GitHub only runs root .github/workflows: {path}")

        if any(part.casefold() in IGNORED_COMPONENTS for part in parts[:-1]):
            errors.add(f"Generated or dependency file tracked: {path}")
        basename = parts[-1].casefold()
        if basename.startswith(".env") and basename not in ALLOWED_ENV_TEMPLATES:
            errors.add(f"Potential secret configuration tracked: {path}")
        if basename.endswith(".env"):
            errors.add(f"Potential secret environment file tracked: {path}")
        if basename.endswith(FORBIDDEN_SUFFIXES):
            errors.add(f"Generated binary, database or credential tracked: {path}")
    return sorted(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        paths = tracked_and_new_files(args.repo_root)
        problems = validate_paths(paths)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Repository layout check could not run: {error}", file=sys.stderr)
        return 2
    if problems:
        for issue in problems:
            print("LAYOUT ERROR: " + issue, file=sys.stderr)
        return 1
    print(f"Repository layout OK: {len(paths)} versioned or non-ignored files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
