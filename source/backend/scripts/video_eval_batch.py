#!/usr/bin/env python3
"""Process a JSON video list with Google transcription and AI-only source research.

Input items may provide local audio/video/media_path or a direct HTTPS media_url/video_url/audio_url/source_url. The latter is downloaded to a bounded temporary file before Google transcription.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import ipaddress
import socket
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

_MAX_MEDIA_BYTES = 1_000_000_000
_MEDIA_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
_CONTENT_SUFFIXES = {"audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}

from app.services.video_eval_pipeline import (
    build_video_artifact,
    evaluate_rhetoric_profile,
    research_source_candidates,
    save_artifact,
    update_style_profile,
    transcribe_with_google_cloud,
)


async def _public_https(url: str) -> bool:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if parsed.port not in (None, 443):
        return False
    try:
        literal = ipaddress.ip_address(host)
        return literal.is_global
    except ValueError:
        pass
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except OSError:
        return False
    return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses if item[4])


async def _download_media(url: str, directory: Path) -> Path:
    current = url
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0), follow_redirects=False) as client:
        for _ in range(4):
            if not await _public_https(current):
                raise ValueError("media URL must resolve to a public HTTPS host")
            async with client.stream("GET", current, headers={"User-Agent": "DebateAI-video-eval"}) as response:
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    if not location:
                        raise ValueError("media URL redirect has no location")
                    current = urljoin(str(response.url), location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
                declared = response.headers.get("content-length", "")
                if declared.isdigit() and int(declared) > _MAX_MEDIA_BYTES:
                    raise ValueError("media file exceeds the 1 GB safety limit")
                suffix = Path(urlsplit(current).path).suffix.casefold()
                if suffix not in _MEDIA_SUFFIXES:
                    suffix = _CONTENT_SUFFIXES.get(content_type, ".media")
                output = directory / ("download" + suffix)
                total = 0
                with output.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > _MAX_MEDIA_BYTES:
                            raise ValueError("media file exceeds the 1 GB safety limit")
                        handle.write(chunk)
                if content_type.startswith("text/html") and suffix == ".media":
                    raise ValueError("source_url points to a web page; provide a direct media_url")
                return output
        raise ValueError("media URL redirect limit exceeded")


async def _resolve_media_path(item: dict, directory: Path) -> Path:
    for key in ("audio", "video", "media_path"):
        value = str(item.get(key) or "").strip()
        if value:
            path = Path(value).expanduser()
            if path.is_file():
                return path
            raise FileNotFoundError(path)
    for key in ("media_url", "video_url", "audio_url", "source_url"):
        value = str(item.get(key) or "").strip()
        if value.startswith("https://"):
            return await _download_media(value, directory)
    raise ValueError("video-list item needs audio/video/media_path or a direct HTTPS media URL")


async def process(item: dict, output_dir: Path, language: str, diarization: bool, style_profile: str) -> Path:
    video_id = str(item.get("video_id") or item.get("id") or "").strip()
    if not video_id:
        raise ValueError("video-list item is missing video_id")
    with tempfile.TemporaryDirectory(prefix="debateai-video-") as temp_dir:
        media_path = await _resolve_media_path(item, Path(temp_dir))
        segments = transcribe_with_google_cloud(
            media_path,
            language_code=language,
            project_id=item.get("project_id"),
            speaker_diarization=diarization,
        )
    artifact = build_video_artifact(
        video_id=video_id,
        source_url=str(item.get("source_url") or item.get("media_url") or ""),
        segments=segments,
        language_code=language,
    )
    artifact = await research_source_candidates(artifact)
    artifact = await evaluate_rhetoric_profile(artifact)
    artifact_path = save_artifact(artifact, output_dir / f"{video_id}.json")
    if style_profile:
        update_style_profile(style_profile, artifact.rhetorical_profile)
    return artifact_path


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
