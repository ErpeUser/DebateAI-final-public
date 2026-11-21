#!/usr/bin/env python3
"""Inspect the DebateAI worktree without requiring or creating Generated."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
GENERATED = ROOT / "DebateAI_Generated"
BUNDLE = ROOT / "runtime" / "DebateAI"

# All names point at the ONE original. Bundled binaries are never moved out
# of _internal or duplicated to generated dependency trees.
RESOURCES = {
    "source_backend": APP / "backend/app/main.py",
    "source_frontend": APP / "frontend/src/App.tsx",
    "source_desktop": APP / "desktop/launcher.py",
    "source_models_downloader": APP / "backend/scripts/download_models.py",
    "source_readme": ROOT / "README.md",
    "source_github_tests": ROOT / ".github/workflows/tests.yml",
    "build_frontend_config": APP / "frontend/vite.config.ts",
    "build_desktop_spec": APP / "desktop/debateai.spec",
    "build_docs_wrangler": APP / "docs-site/wrangler.jsonc",
    "build_backend_test": APP / "backend/tests/test_update_service.py",
    "source_canonical_docs": APP / "docs/HANDBUCH.md",
    "runtime_executable": BUNDLE / "DebateAI.exe",
    "runtime_updater": BUNDLE / "DebateAIUpdater.exe",
    "runtime_internal": BUNDLE / "_internal",
    "runtime_postgres": BUNDLE / "_internal/pgsql/bin/postgres.exe",
    "runtime_ffmpeg": BUNDLE / "_internal/ffmpeg/ffmpeg.exe",
    "runtime_models": BUNDLE / "_internal/models",
    "runtime_oracle_node": BUNDLE / "_internal/chatgpt_oracle/node/node.exe",
    "runtime_frontend": BUNDLE / "_internal/frontend",
    "dev_frontend_modules": APP / "frontend/node_modules",
    "dev_docs_modules": APP / "docs-site/node_modules",
    "dev_release_modules": APP / "release-signing-worker/node_modules",
    "build_venv": GENERATED / "dependencies/python/release-venv",
    "build_release_bundle": GENERATED / "build/releases/DebateAI",
    "build_release_archive": GENERATED / "build/releases/DebateAI-windows-x64.zip",
    "build_native_smoke": GENERATED / "build/native-smoke",
    "build_native_smoke_data": GENERATED / "build/native-smoke-data",
    "build_recovery": GENERATED / "build/recovery",
    "npm_cache": GENERATED / "cache/npm",
    "pip_cache": GENERATED / "cache/pip",
    "ruff_cache": GENERATED / "cache/ruff",
}

# Only recreate scratch/output directories. Do not resurrect obsolete
# generated copies of source, configs, git history or user databases.
GENERATED_DIRS = (
    "dependencies/python",
    "build",
    "build/native-smoke",
    "build/native-smoke-data",
    "cache",
    "cache/ruff",
    "downloads",
    "logs",
    "reports/provenance",
    "reports/screenshots",
    "tmp",
)


def git_metadata_dir() -> Path:
    """Resolve normal internal Git metadata and legacy pointer checkouts."""
    pointer = ROOT / ".git"
    if pointer.is_dir():
        return pointer
    if not pointer.is_file():
        return pointer
    line = pointer.read_text(encoding="utf-8-sig").strip()
    if not line.lower().startswith("gitdir: "):
        return pointer
    directory = Path(line.split(":", 1)[1].strip())
    return directory if directory.is_absolute() else ROOT / directory


def external_git_dir() -> Path:
    """Backward-compatible name for legacy callers."""
    return git_metadata_dir()


def collect(*, source_only: bool = False) -> dict:
    git = git_metadata_dir()
    references = dict(RESOURCES)
    references["git_metadata"] = git / "HEAD"
    required = [
        ROOT / ".git",
        git / "HEAD",
        RESOURCES["source_backend"],
        RESOURCES["source_frontend"],
        RESOURCES["source_desktop"],
    ]
    if not source_only:
        required.extend(
            (
                RESOURCES["runtime_executable"],
                RESOURCES["runtime_updater"],
                RESOURCES["runtime_internal"],
            )
        )
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "root": str(ROOT),
        "generated_exists": GENERATED.exists(),
        "source_only": source_only,
        "runtime_independent_of_generated": not BUNDLE.is_relative_to(GENERATED),
        "git_independent_of_generated": not git.resolve().is_relative_to(
            GENERATED.resolve()
        ),
        "references": {
            name: {"path": str(path), "exists": path.exists()}
            for name, path in references.items()
        },
        "essential_missing": [str(p) for p in required if not p.exists()],
        "note": "Reference map, not copies. Optional resources absent in source mode can be rebuilt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--initialize",
        action="store_true",
        help="Recreate only expendable build/cache directories",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Fail if essential paths are missing"
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="CI/source checkout: do not require an installed binary",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write an ephemeral JSON inventory into Generated",
    )
    args = parser.parse_args()
    if args.initialize:
        for item in GENERATED_DIRS:
            (GENERATED / item).mkdir(parents=True, exist_ok=True)
    report = collect(source_only=args.source_only)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.write_report:
        path = GENERATED / "reports/provenance/workspace-references.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    print(output)
    return int(
        args.strict
        and (
            bool(report["essential_missing"])
            or not report["git_independent_of_generated"]
            or not report["runtime_independent_of_generated"]
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
