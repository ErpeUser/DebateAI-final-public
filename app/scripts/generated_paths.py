#!/usr/bin/env python3
"""Canonical destinations for local DebateAI-generated output.

The source tree is public and reproducible. Build products, test evidence,
acceptance runs and local reports belong below ``DebateAI_Generated``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "DebateAI_Generated"

OUTPUT_DIRS = {
    "acceptance": GENERATED / "reports" / "acceptance",
    "benchmarks": GENERATED / "reports" / "benchmarks",
    "provenance": GENERATED / "reports" / "provenance",
    "screenshots": GENERATED / "reports" / "screenshots",
    "tmp": GENERATED / "tmp",
}


def output_dir(kind: str, root: Path = ROOT) -> Path:
    """Return a canonical generated-output directory for ``kind``."""
    try:
        return root / OUTPUT_DIRS[kind].relative_to(ROOT)
    except KeyError as error:
        raise ValueError(f"Unknown generated output kind: {kind}") from error


def ensure_output_path(path: Path, kind: str, root: Path = ROOT) -> Path:
    """Validate and create a generated output path below the selected folder.

    Existing files are allowed because some reports are intentionally updated
    by a single run. Symlinks and Windows junctions are rejected so a caller
    cannot redirect generated output into source or private user data.
    """
    target = path.expanduser().resolve()
    parent = output_dir(kind, root).resolve()
    try:
        target.relative_to(parent)
    except ValueError as error:
        raise ValueError(
            f"Generated output must be below {parent}, received {target}"
        ) from error
    for item in (parent, *target.parents):
        if item == root.resolve():
            break
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise ValueError(f"Generated output traverses a link or junction: {item}")
    parent.mkdir(parents=True, exist_ok=True)
    return target
