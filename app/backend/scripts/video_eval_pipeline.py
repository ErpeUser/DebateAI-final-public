#!/usr/bin/env python3
"""Build a persistent DebateAI evaluation artifact from a media export.

Example:
  python app/backend/scripts/video_eval_pipeline.py \
    --audio ./video.wav --video-id debate-001 --out ./artifacts/debate-001.json \
    --speaker-diarization
"""

from __future__ import annotations

import argparse
import asyncio

from app.services.video_eval_pipeline import (
    build_video_artifact,
    evaluate_rhetoric_profile,
    research_source_candidates,
    save_artifact,
    transcribe_with_google_cloud,
    update_style_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Local audio/video export")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--source-url", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--language", default="de-DE")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--speaker-diarization", action="store_true")
    parser.add_argument(
        "--style-profile", default="", help="Persistent local rhetoric profile JSON"
    )
    args = parser.parse_args()
    segments = transcribe_with_google_cloud(
        args.audio,
        language_code=args.language,
        project_id=args.project_id,
        speaker_diarization=args.speaker_diarization,
    )
    artifact = build_video_artifact(
        video_id=args.video_id,
        source_url=args.source_url,
        segments=segments,
        language_code=args.language,
    )
    artifact = asyncio.run(research_source_candidates(artifact))
    artifact = asyncio.run(evaluate_rhetoric_profile(artifact))
    save_artifact(artifact, args.out)
    if args.style_profile:
        update_style_profile(args.style_profile, artifact.rhetorical_profile)
    print(f"saved {args.out} ({len(segments)} transcript segments)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
