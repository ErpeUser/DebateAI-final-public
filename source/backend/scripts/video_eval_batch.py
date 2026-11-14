#!/usr/bin/env python3
"""Process a JSON video list with Google transcription and AI-only source research.

Input format:
[
  {"video_id": "debate-001", "audio": "./001.wav", "source_url": "https://..."},
  {"video_id": "debate-002", "audio": "./002.wav"}
]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.services.video_eval_pipeline import (
    build_video_artifact,
    research_source_candidates,
    save_artifact,
    update_style_profile,
    transcribe_with_google_cloud,
)


async def process(item: dict, output_dir: Path, language: str, diarization: bool, style_profile: str) -> Path:
    video_id = str(item["video_id"])
    segments = transcribe_with_google_cloud(
        item["audio"],
        language_code=language,
        project_id=item.get("project_id"),
        speaker_diarization=diarization,
    )
    artifact = build_video_artifact(
        video_id=video_id,
        source_url=str(item.get("source_url") or ""),
        segments=segments,
        language_code=language,
    )
    artifact = await research_source_candidates(artifact)
    return save_artifact(artifact, output_dir / f"{video_id}.json")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-list", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--language", default="de-DE")
    parser.add_argument("--speaker-diarization", action="store_true")
    parser.add_argument("--style-profile", default="")
    args = parser.parse_args()
    items = json.loads(Path(args.video_list).read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise SystemExit("video-list must be a JSON array")
    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        path = await process(item, output_dir, args.language, args.speaker_diarization, args.style_profile)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
