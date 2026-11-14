#!/usr/bin/env python3
"""Run the safe, review-gated video-to-prompt evaluation workflow.

This runner accepts only a video list, creates Google-STT/source/rhetoric
artifacts, builds leakage-safe blind splits, asks the configured AI web lane
for prompt/agent recommendations, and optionally runs tests. It never writes
production prompts, master, provider profiles, or fine-tuning jobs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.video_eval_evaluator import build_split_manifest, load_video_artifacts, save_manifest
from app.services.ai_config import research_settings
from app.services.video_eval_batch import process


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


async def _request_tuning_review(summary: dict[str, Any]) -> dict[str, Any]:
    prompt = (
        "Review this leakage-safe DebateAI video evaluation summary. Return only JSON "
        "with keys prompt_variants (array of id, hypothesis, prompt, risks), "
        "agent_comparison (array), routing_recommendation, and fine_tuning_readiness. "
        "Recommend prompt/routing/Few-shot changes before real fine-tuning. Do not "
        "claim a blind win without scored pairs and do not mention providers in any "
        "candidate user-facing prompt.\\n\\nSUMMARY:\\n" + _json(summary)

    )
    answer = ""
    provider = "unavailable"
    try:
        from app.services.chatgpt_web import configured, generate, runtime_available
        if configured() and runtime_available():
            answer = await generate(
                prompt,
                system="You are the review-gated prompt optimization lane. Return strict JSON only.",
                reasoning_effort="high",
                research="none",
            )
            provider = "chatgpt_web"
    except Exception:
        answer = ""
    if not answer:
        try:
            from app.services.llm import generate_text
            providers = set(research_settings().get("providers") or [])
            model = next((
                item for item in (
                    "endpoint:gemini-web:gemini-3.1-pro",
                    "gemini-3.1-pro-preview",
                    "endpoint:subscription-ai:gpt-6-sol",
                ) if (
                    (item.startswith("endpoint:gemini-web:") and "gemini_web" in providers)
                    or (item.startswith("gemini-") and "gemini_api" in providers)
                    or (item.startswith("endpoint:subscription-ai:") and "cliproxyapi" in providers)
                )
            ), "")
            if model:
                answer = await generate_text(model, prompt, system="Return strict JSON only.", source="video_autotune_review")
                provider = "ai_web_fallback"
        except Exception:
            answer = ""
    if not answer:
        return {"provider": provider, "status": "unavailable", "prompt_variants": [], "agent_comparison": [], "routing_recommendation": "", "fine_tuning_readiness": "insufficient evidence"}
    raw = str(answer).strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit(fence, 1)[0].strip()
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return {"provider": provider, "status": "invalid_json", "raw": raw[:12000], "prompt_variants": [], "agent_comparison": []}
    if not isinstance(payload, dict):
        return {"provider": provider, "status": "invalid_shape", "prompt_variants": [], "agent_comparison": []}
    return {"provider": provider, "status": "completed", **payload}


def _run_checks(repo_root: str, command: str) -> dict[str, Any]:
    if not repo_root or not command:
        return {"status": "not_requested", "command": "", "returncode": None, "output": ""}
    try:
        completed = subprocess.run(
            shlex.split(command), cwd=repo_root, capture_output=True, text=True, timeout=1800
        )
        output = (completed.stdout + "\n" + completed.stderr)[-12000:]
        return {"status": "passed" if completed.returncode == 0 else "failed", "command": command, "returncode": completed.returncode, "output": output}
    except Exception as exc:
        return {"status": "error", "command": command, "returncode": None, "output": str(exc)}


async def run(video_list: Path, out_dir: Path, *, language: str, diarization: bool, style_profile: str, repo_root: str, test_command: str) -> Path:
    items = json.loads(video_list.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError("video-list must be a JSON array of objects")
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths: list[Path] = []
    for item in items:
        artifact_paths.append(await process(item, out_dir, language, diarization, style_profile))
    records = load_video_artifacts(artifact_paths)
    manifest = build_split_manifest(records)
    manifest_path = save_manifest(manifest, out_dir / "evaluation-manifest.json")
    summary = {
        "artifact_count": len(artifact_paths),
        "case_count": len(records),
        "manifest": str(manifest_path),
        "leakage_checks": manifest.leakage_checks,
        "blind_pairs": len(manifest.blind_pairs),
        "scoring": manifest.scoring,
    }
    review = await _request_tuning_review(summary)
    checks = _run_checks(repo_root, test_command)
    report = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "video_list": str(video_list),
        "artifacts": [str(path) for path in artifact_paths],
        "evaluation": summary,
        "review": review,
        "checks": checks,
        "approval": {
            "required": True,
            "approved": False,
            "master_mutation": False,
            "production_prompt_changed": False,
            "fine_tuning_started": False,
            "next_step": "Review blind scores and candidate prompts, then apply an explicitly approved isolated change.",
        },
    }
    report_path = out_dir / "autotune-report.json"
    report_path.write_text(_json(report) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-list", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--language", default="de-DE")
    parser.add_argument("--speaker-diarization", action="store_true")
    parser.add_argument("--style-profile", default="")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--test-command", default="python -m pytest source/backend/tests/test_video_eval_pipeline.py")
    args = parser.parse_args()
    path = asyncio.run(run(
        Path(args.video_list), Path(args.out_dir),
        language=args.language, diarization=args.speaker_diarization,
        style_profile=args.style_profile, repo_root=args.repo_root,
        test_command=args.test_command if args.repo_root else "",
    ))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())