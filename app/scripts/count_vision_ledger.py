#!/usr/bin/env python3
"""Count atomic rows in app/docs/VISION_LEDGER.md by status and evidence mode."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_COLUMNS = 15

def rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| V") and not line.startswith("| P"):
            continue
        fields = [field.strip() for field in line.strip().split("|")[1:-1]]
        if len(fields) != EXPECTED_COLUMNS:
            continue
        yield fields

def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} LEDGER.md", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    entries = list(rows(path))
    status_counts: dict[str, int] = {}
    evidence_counts: dict[str, int] = {}
    unmapped = 0
    for fields in entries:
        status = fields[5]
        evidence = fields[9].split(";", 1)[0].strip()
        status_counts[status] = status_counts.get(status, 0) + 1
        evidence_counts[evidence] = evidence_counts.get(evidence, 0) + 1
        if "UNMAPPED" in fields[8] or "UNMAPPED" in fields[12]:
            unmapped += 1
    print(json.dumps({
        "entries": len(entries),
        "status": dict(sorted(status_counts.items())),
        "evidence_mode": dict(sorted(evidence_counts.items())),
        "unmapped": unmapped,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
