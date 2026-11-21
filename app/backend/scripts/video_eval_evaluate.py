#!/usr/bin/env python3
"""Create leakage-safe splits and blind comparison rows from video artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.video_eval_evaluator import (
    build_split_manifest,
    load_video_artifacts,
    save_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", default="debateai-eval-v1")
    args = parser.parse_args()
    artifact_paths = sorted(Path(args.artifacts_dir).glob("*.json"))
    if not artifact_paths:
        raise SystemExit("No video artifacts found")
    records = load_video_artifacts(artifact_paths)
    manifest = build_split_manifest(records, seed=args.seed)
    path = save_manifest(manifest, args.out)
    print(
        f"saved {path} ({len(records)} cases, {len(manifest.blind_pairs)} blind pairs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
