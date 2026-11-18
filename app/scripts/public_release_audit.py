#!/usr/bin/env python3
"""Audit a DebateAI tree before public publication.

The report contains rule identifiers and paths only. It never prints matched
secret values or file contents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Iterable


PRIVATE_DATA_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm"}
FORBIDDEN_BINARY_SUFFIXES = {".dll", ".exe", ".msi", ".p12", ".pfx", ".pem", ".zip"}
ENV_ALLOWLIST = {".env.example", ".env.sample", ".env.template"}
SKIP_DIRS = {".git", ".codex", ".superpowers", "node_modules", "__pycache__"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
)


def _finding(rule: str, path: Path, root: Path) -> dict[str, str]:
    return {"rule": rule, "path": path.relative_to(root).as_posix()}


def _iter_files(root: Path) -> Iterable[Path]:
    for current, directories, files in __import__("os").walk(root):
        current_path = Path(current)
        kept: list[str] = []
        for directory in directories:
            if directory in SKIP_DIRS:
                continue
            kept.append(directory)
        directories[:] = kept
        for filename in files:
            yield current_path / filename


def _is_env_file(path: Path) -> bool:
    name = path.name.lower()
    return name.startswith(".env") and name not in ENV_ALLOWLIST


def _scan_text(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if len(data) > 4 * 1024 * 1024 or b"\x00" in data:
        return False
    text = data.decode("utf-8", errors="ignore")
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def audit(repo_root: Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    findings: list[dict[str, str]] = []
    if not (root / "LICENSE").is_file():
        findings.append(_finding("missing_root_license", root / "LICENSE", root))
    app_license = root / "app" / "LICENSE"
    if app_license.is_file() and (root / "LICENSE").is_file():
        if (root / "LICENSE").read_bytes() != app_license.read_bytes():
            findings.append(_finding("license_mismatch", root / "LICENSE", root))

    for top_level in (root / "runtime", root / "DebateAI_Generated"):
        if top_level.exists():
            rule = "runtime_path" if top_level.name == "runtime" else "generated_path"
            findings.append(_finding(rule, top_level, root))

    for path in _iter_files(root):
        relative = path.relative_to(root)
        if any(part in {"runtime", "DebateAI_Generated"} for part in relative.parts):
            continue
        suffix = path.suffix.lower()
        if suffix in PRIVATE_DATA_SUFFIXES:
            findings.append(_finding("private_data_path", path, root))
        if suffix in FORBIDDEN_BINARY_SUFFIXES:
            findings.append(_finding("binary_artifact", path, root))
        if _is_env_file(path):
            findings.append(_finding("local_config_path", path, root))
        if _scan_text(path):
            findings.append(_finding("secret_marker", path, root))

    unique = {(item["rule"], item["path"]): item for item in findings}
    ordered = [unique[key] for key in sorted(unique)]
    return {
        "root": str(root),
        "finding_count": len(ordered),
        "findings": ordered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = audit(args.repo_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report["findings"]))


if __name__ == "__main__":
    raise SystemExit(main())
