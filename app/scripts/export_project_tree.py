#!/usr/bin/env python3
"""Read-only, reproducible folder tree of the DebateAI checkout.

Default view condenses the 16k-file native runtime and noisy generated
dependency trees. Use --full to see every file, including the runtime.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from generated_paths import ensure_output_path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".git",
    ".venv",
    ".release-venv",
}
HEAVY = {"runtime/DebateAI/_internal"}


def scan_stats(path: Path) -> tuple[int, int]:
    count, total_bytes = 0, 0
    for base, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [
            d
            for d in dirs
            if not (Path(base) / d).is_symlink()
            and not (
                hasattr(Path(base) / d, "is_junction")
                and (Path(base) / d).is_junction()
            )
        ]
        for filename in files:
            try:
                item = Path(base) / filename
                if not item.is_symlink():
                    count += 1
                    total_bytes += item.stat().st_size
            except OSError:
                continue
    return count, total_bytes


def direct_entries(path: Path, full: bool) -> tuple[list[Path], int]:
    try:
        entries = list(path.iterdir())
    except OSError:
        return [], 0
    if not full:
        entries = [x for x in entries if x.name not in SKIP or x == ROOT / ".git"]
    entries.sort(key=lambda p: (not p.is_dir(), p.name.casefold()))
    return entries, len(entries)


def render(*, max_depth: int, max_entries: int, full: bool) -> str:
    count_app, bytes_app = scan_stats(ROOT / "app")
    count_runtime, bytes_runtime = scan_stats(ROOT / "runtime")
    lines = [
        "# DebateAI - aktueller Ordnerbaum (automatisch erzeugt)",
        "",
        f"Stand: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "Quelle: Repository-Root (relativ zu app/scripts/export_project_tree.py)",
        f"app/: {count_app} Dateien, {bytes_app / 1024**2:.1f} MiB",
        f"runtime/: {count_runtime} Dateien, {bytes_runtime / 1024**2:.1f} MiB",
        f"DebateAI_Generated vorhanden: {(ROOT / 'DebateAI_Generated').exists()}",
        "",
        "Dieser Baum zeigt echte Verzeichnisse; '...' bezeichnet nur gekuerzte Inhalte.",
        "Private Benutzerdaten ausserhalb des Repositorys werden nicht eingelesen.",
        "",
        "```text",
        "DebateAI/",
    ]

    def add(path: Path, prefix: str, level: int) -> None:
        if level > max_depth:
            return
        items, _ = direct_entries(path, full)
        if not full and len(items) > max_entries:
            shown = items[:max_entries]
            suppressed = len(items) - len(shown)
        else:
            shown, suppressed = items, 0
        for idx, entry in enumerate(shown):
            last = idx == len(shown) - 1 and suppressed == 0
            connector = "└── " if last else "├── "
            is_link = entry.is_symlink() or (
                hasattr(entry, "is_junction") and entry.is_junction()
            )
            directory = entry.is_dir() and not is_link
            text = entry.name + ("/" if directory else "")
            rel = entry.relative_to(ROOT).as_posix()
            if is_link:
                text += " [Verweis; nicht gefolgt]"
            if directory and not full and rel in HEAVY:
                n, size = scan_stats(entry)
                text += f" [{n} Dateien, {size / 1024**2:.1f} MiB; gekuerzt]"
            lines.append(prefix + connector + text)
            if directory and level < max_depth and (full or rel not in HEAVY):
                add(entry, prefix + ("    " if last else "│   "), level + 1)
        if suppressed:
            lines.append(prefix + f"└── ... (+{suppressed} weitere Eintraege)")

    add(ROOT, "", 1)
    if not (ROOT / "DebateAI_Generated").exists():
        lines.append("[DebateAI_Generated/ fehlt: optional, kein Start-Hindernis]")
    gitfile = ROOT / ".git"
    if gitfile.is_file():
        try:
            lines.append(
                f"[.git-Verweis: {gitfile.read_text(encoding='utf-8-sig').strip()}]"
            )
        except OSError:
            pass
    lines.extend(["```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include hidden caches and all runtime files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional report path below DebateAI_Generated/reports/provenance",
    )
    args = parser.parse_args()
    if args.depth < 1 or args.limit < 1:
        parser.error("--depth and --limit must be positive")
    output = render(max_depth=args.depth, max_entries=args.limit, full=args.full)
    if args.output:
        target = ensure_output_path(args.output, "provenance")
        target.write_text(output, encoding="utf-8")
        print(f"Gespeichert: {target}")
    else:
        try:
            print(output)
        except UnicodeEncodeError:
            # Windows PowerShell may use CP1252 instead of UTF-8.
            ascii_tree = (
                output.replace("├", "+")
                .replace("└", "\\\\")
                .replace("│", "|")
                .replace("─", "-")
            )
            print(ascii_tree.encode("ascii", "backslashreplace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
