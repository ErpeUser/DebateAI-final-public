"""Video-to-evaluation pipeline for DebateAI.

The pipeline deliberately keeps cloud work out of the live answer path. It
transcribes a supplied audio/video export with Google Cloud Speech-to-Text,
extracts source candidates from the transcript, creates reproducible rhetoric
and response-evaluation cases, and stores one JSON artifact for later review.
No automatic prompt/model change is applied from an artifact.
"""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_DOI_RE = re.compile(r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b', re.IGNORECASE)
_STUDY_RE = re.compile(
    r"\b(?:studie|paper|bericht|metaanalyse|meta-analyse|untersuchung)"
    r"[^.]{0,160}\b(?:19|20)\d{2}\b",
    re.IGNORECASE,
)

_CITATION_RE = re.compile(
    r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\'-]{2,}(?:\s+et\s+al\.)?"
    r"(?:,?\s+)(?:19|20)\d{2}\b"
)


@dataclass(frozen=True)
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str
    speaker: str = ""
    confidence: float | None = None


@dataclass(frozen=True)
class SourceCandidate:
    value: str
    kind: str
    context: str
    segment_index: int


@dataclass
class VideoEvalArtifact:
    schema_version: int = 1
    video_id: str = ""
    source_url: str = ""
    # Provenance and reproducibility metadata from the video-list ingestion.
    original_url: str = ""
    source_platform: str = ""
    retrieval_timestamp: str = ""
    video_hash: str = ""
    subtitle_hash: str = ""
    audio_hash: str = ""
    duration_seconds: float = 0.0
    availability: str = "available"
    ingestion_checks: dict[str, Any] = field(default_factory=dict)
    language_code: str = "de-DE"
    transcript_segments: list[dict[str, Any]] = field(default_factory=list)
    speaker_turns: list[dict[str, Any]] = field(default_factory=list)
    source_candidates: list[dict[str, Any]] = field(default_factory=list)
    verified_sources: list[dict[str, Any]] = field(default_factory=list)
    rhetorical_profile: dict[str, Any] = field(default_factory=dict)
    eval_cases: list[dict[str, Any]] = field(default_factory=list)
    improvement_notes: list[str] = field(default_factory=list)
    privacy: dict[str, Any] = field(default_factory=lambda: {
        "audio_uploaded_to_google_cloud": True,
        "raw_audio_retained": False,
        "raw_transcript_retained": True,
        "review_required_before_learning": True,
    })


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def extract_source_candidates(
    text: str,
    *,
    segment_index: int = 0,
    context_chars: int = 180,
) -> list[SourceCandidate]:
    """Find references worth sending to the AI source-research lane."""
    value = str(text or "")
    found: list[SourceCandidate] = []
    seen: set[tuple[str, str]] = set()
    matches: list[tuple[int, int, str, str]] = []
    for match in _URL_RE.finditer(value):
        matches.append((match.start(), match.end(), match.group(0).rstrip(".,;:)]}"), "url"))
    for match in _DOI_RE.finditer(value):
        matches.append((match.start(), match.end(), match.group(0), "doi"))
    for match in _STUDY_RE.finditer(value):
        matches.append((match.start(), match.end(), _clean(match.group(0)), "study_reference"))
    for match in _CITATION_RE.finditer(value):
        matches.append((match.start(), match.end(), _clean(match.group(0)), "citation"))
    for start, end, candidate, kind in sorted(matches):
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        context = _clean(value[max(0, start - context_chars): min(len(value), end + context_chars)])
        found.append(SourceCandidate(candidate, kind, context, segment_index))
    return found


def build_rhetorical_profile(
    segments: Iterable[TranscriptSegment],
    *,
    source_candidates: Iterable[SourceCandidate] = (),
) -> dict[str, Any]:
    rows = [item for item in segments if _clean(item.text)]
    texts = [_clean(item.text) for item in rows]
    words = [len(text.split()) for text in texts]
    joined = " ".join(texts)
    questions = sum(text.endswith("?") or "?" in text for text in texts)
    rebuttals = sum(bool(re.search(r"\b(aber|jedoch|stimmt nicht|falsch|trotzdem|widerleg)\b", text, re.I)) for text in texts)
    analogies = sum(bool(re.search(r"\b(wie|als ob|beispiel|vergleich|analogie)\b", text, re.I)) for text in texts)
    interruptions = sum(text.count("…") + text.count("--") for text in texts)
    return {
        "segment_count": len(rows),
        "speaker_count": len({item.speaker for item in rows if item.speaker}),
        "word_count": sum(words),
        "average_words_per_segment": round(sum(words) / len(words), 2) if words else 0,
        "question_rate": round(questions / len(rows), 3) if rows else 0,
        "rebuttal_rate": round(rebuttals / len(rows), 3) if rows else 0,
        "analogy_rate": round(analogies / len(rows), 3) if rows else 0,
        "interruption_signal_rate": round(interruptions / len(rows), 3) if rows else 0,
        "source_reference_count": len(list(source_candidates)),
        "style_traits": [
            trait for trait, enabled in (
                ("fragt häufig nach", questions >= max(1, len(rows) // 8)),
                ("widerlegt direkt", rebuttals >= max(1, len(rows) // 8)),
                ("arbeitet mit Beispielen", analogies >= max(1, len(rows) // 8)),
                ("spricht in kurzen Zügen", bool(words) and sum(words) / len(words) <= 18),
            ) if enabled
        ],
        "sample": joined[:1200],
    }


def build_eval_cases(
    segments: Iterable[TranscriptSegment],
    *,
    source_candidates: Iterable[SourceCandidate] = (),
    context_segments: int = 3,
) -> list[dict[str, Any]]:
    """Create deterministic cases for prompt/model comparisons.

    The expected response is intentionally empty: a reviewer or a later
    approved evaluator fills it, so the transcript cannot silently become its
    own ground truth.
    """
    rows = [item for item in segments if _clean(item.text)]
    candidates = list(source_candidates)
    cases: list[dict[str, Any]] = []
    for index, segment in enumerate(rows):
        text = _clean(segment.text)
        context = " ".join(_clean(item.text) for item in rows[max(0, index-context_segments):index])
        refs = [
            item.value for item in candidates
            if item.segment_index == index
        ]
        cases.append({
            "case_id": f"segment-{index + 1:04d}",
            "start_seconds": segment.start_seconds,
            "end_seconds": segment.end_seconds,
            "speaker": segment.speaker,
            "context_before": context[-1800:],
            "original_statement": text,
            "claim": text,
            "source_candidates": refs,
            "expected_response": "",
            "difficulty": "source_check" if refs else "rhetorical",
            "scoring": {
                "directness": None,
                "example_or_analogy": None,
                "counter_question": None,
                "rebuttal_quality": None,
                "source_accuracy": None,
                "latency_ms": None,
            },
        })
    return cases


def _audio_bytes(path: Path) -> bytes:
    """Extract mono 16 kHz WAV bytes when the input is a video container."""
    if path.suffix.casefold() not in {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}:
        return path.read_bytes()
    try:
        completed = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
                "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=900,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("ffmpeg is required to extract audio from video files") from exc
    return completed.stdout


def _recognize_google_chunk(
    client: Any,
    speech: Any,
    content: bytes,
    *,
    language_code: str,
    speaker_diarization: bool,
    offset_seconds: float = 0.0,
) -> list[TranscriptSegment]:
    diarization_config = None
    if speaker_diarization:
        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=1,
            max_speaker_count=8,
        )
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        language_code=language_code,
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True,
        diarization_config=diarization_config,
        model="latest_long",
    )
    response = client.recognize(
        config=config,
        audio=speech.RecognitionAudio(content=content),
    )
    segments: list[TranscriptSegment] = []
    for result in response.results:
        alternatives = result.alternatives
        if not alternatives:
            continue
        alternative = alternatives[0]
        words = list(getattr(alternative, "words", []) or [])
        start = (
            float(words[0].start_time.total_seconds()) + offset_seconds
            if words else offset_seconds
        )
        end = (
            float(words[-1].end_time.total_seconds()) + offset_seconds
            if words else start
        )
        speaker = str(getattr(words[0], "speaker_tag", "") or "") if words else ""
        segments.append(TranscriptSegment(
            start_seconds=start,
            end_seconds=end,
            text=_clean(alternative.transcript),
            speaker=speaker,
            confidence=float(alternative.confidence or 0) or None,
        ))
    return segments


def _chunk_media(path: Path, directory: Path, *, seconds: int = 45) -> list[Path]:
    """Create short PCM chunks so long local videos use Speech-to-Text safely."""
    prefix = directory / "chunk-%05d.wav"
    try:
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
                "-f", "segment", "-segment_time", str(seconds),
                "-reset_timestamps", "1", "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", str(prefix),
            ],
            check=True,
            capture_output=True,
            timeout=1800,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("ffmpeg is required to split long media files") from exc
    chunks = sorted(directory.glob("chunk-*.wav"))
    if not chunks:
        raise RuntimeError("ffmpeg produced no audio chunks")
    return chunks


def transcribe_with_google_cloud(
    audio_path: str | Path,
    *,
    language_code: str = "de-DE",
    project_id: str | None = None,
    location: str = "global",
    speaker_diarization: bool = False,
    timeout_seconds: int = 1800,
) -> list[TranscriptSegment]:
    """Transcribe local audio/video through Google Speech-to-Text.

    Short audio is sent directly. Long audio and every video container are
    split into 45-second mono PCM chunks first; each response is offset back
    onto the original timeline. This keeps the live path independent from
    batch transcription while allowing a supplied video list to run without
    waiting for one oversized synchronous request.
    """
    del project_id, location, timeout_seconds
    try:
        from google.cloud import speech
    except ImportError as exc:
        raise RuntimeError("google-cloud-speech is required for video transcription") from exc
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    client = speech.SpeechClient()
    media_suffixes = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
    needs_chunks = path.suffix.casefold() in media_suffixes or path.stat().st_size > 8_000_000
    if not needs_chunks:
        return _recognize_google_chunk(
            client,
            speech,
            _audio_bytes(path),
            language_code=language_code,
            speaker_diarization=speaker_diarization,
        )
    with tempfile.TemporaryDirectory(prefix="debateai-stt-") as temp_dir:
        chunks = _chunk_media(path, Path(temp_dir))
        segments: list[TranscriptSegment] = []
        for index, chunk in enumerate(chunks):
            segments.extend(_recognize_google_chunk(
                client,
                speech,
                chunk.read_bytes(),
                language_code=language_code,
                speaker_diarization=speaker_diarization,
                offset_seconds=index * 45.0,
            ))
        return segments


async def extract_source_candidates_with_ai(
    transcript: str,
    segments: Iterable[TranscriptSegment] = (),
    *,
    max_candidates: int = 64,
) -> list[SourceCandidate]:
    """Find transcript references missed by deterministic patterns.

    The model returns candidate names/URLs only; each candidate still goes
    through the bounded AI research path before it can become evidence.
    """
    text = _clean(transcript)[:36_000]
    if not text:
        return []
    prompt = (
        "Extract every source mentioned in this transcript (study, author, "
        "institution, law, dataset, report, URL or DOI). Return only JSON "
        "array objects with value, kind and context. Do not invent sources "
        "and do not use Wikipedia or DuckDuckGo.\n\nTRANSCRIPT:\n" + text
    )
    answer = ""
    try:
        from app.services.chatgpt_web import configured, generate, runtime_available
        if configured() and runtime_available():
            answer = await generate(
                prompt,
                system="You are the video source extraction lane. Return strict JSON only.",
                reasoning_effort="high",
                research="search",
            )
    except Exception:
        answer = ""
    if not answer:
        try:
            from app.services.ai_config import research_settings
            from app.services.llm import generate_text
            providers = set(research_settings().get("providers") or [])
            fallback = next((
                model for provider, model in (
                    ("gemini_web", "endpoint:gemini-web:gemini-3.1-pro"),
                    ("gemini_api", "gemini-3.1-pro-preview"),
                    ("cliproxyapi", "endpoint:subscription-ai:gpt-6-sol"),
                ) if provider in providers
            ), "")
            if fallback:
                answer = await generate_text(
                    fallback, prompt,
                    system="Return only JSON source candidates; exclude Wikipedia and DuckDuckGo.",
                    source="video_source_extraction",
                )
        except Exception:
            answer = ""
    if not answer:
        return []
    raw = str(answer).strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit(fence, 1)[0].strip()
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        match = re.search(r"\\[[\\s\\S]*\\]", raw)
        if not match:
            return []
        try:
            payload = json.loads(match.group(0))
        except ValueError:
            return []
    if not isinstance(payload, list):
        return []
    rows = list(segments)
    found: list[SourceCandidate] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        value = _clean(item.get("value") or item.get("source") or item.get("name"))
        if not value or value.casefold() in seen:
            continue
        seen.add(value.casefold())
        segment_index = next((
            index for index, segment in enumerate(rows)
            if value.casefold() in _clean(segment.text).casefold()
        ), 0)
        found.append(SourceCandidate(
            value=value[:500],
            kind=_clean(item.get("kind") or "ai_reference")[:80] or "ai_reference",
            context=_clean(item.get("context") or value)[:420],
            segment_index=segment_index,
        ))
        if len(found) >= max(1, max_candidates):
            break
    return found

def build_video_artifact(
    *,
    video_id: str,
    source_url: str,
    segments: Iterable[TranscriptSegment],
    language_code: str = "de-DE",
) -> VideoEvalArtifact:
    rows = list(segments)
    candidates: list[SourceCandidate] = []
    for index, segment in enumerate(rows):
        candidates.extend(extract_source_candidates(segment.text, segment_index=index))
    profile = build_rhetorical_profile(rows, source_candidates=candidates)
    return VideoEvalArtifact(
        video_id=video_id,
        source_url=source_url,
        language_code=language_code,
        transcript_segments=[asdict(item) for item in rows],
        speaker_turns=[asdict(item) for item in rows if item.speaker],
        source_candidates=[asdict(item) for item in candidates],
        rhetorical_profile=profile,
        eval_cases=build_eval_cases(rows, source_candidates=candidates),
    )


def attach_media_metadata(
    artifact: VideoEvalArtifact,
    media_path: str | Path,
    *,
    subtitle_path: str | Path | None = None,
) -> VideoEvalArtifact:
    """Add reproducible hashes and timestamp/speaker checks to an artifact."""
    path = Path(media_path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    suffix = path.suffix.casefold()
    if suffix in {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}:
        artifact.video_hash = digest.hexdigest()
    else:
        artifact.audio_hash = digest.hexdigest()
    if subtitle_path:
        subtitle = Path(subtitle_path)
        if subtitle.is_file():
            subtitle_digest = hashlib.sha256()
            with subtitle.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    subtitle_digest.update(chunk)
            artifact.subtitle_hash = subtitle_digest.hexdigest()
    artifact.original_url = artifact.source_url
    artifact.source_platform = urlsplit(artifact.source_url).netloc or "local_file"
    artifact.retrieval_timestamp = datetime.now(UTC).isoformat()
    artifact.duration_seconds = max((
        float(item.get("end_seconds") or 0.0) for item in artifact.transcript_segments
    ), default=0.0)
    artifact.ingestion_checks = {
        "has_timestamps": all(
            float(item.get("end_seconds") or 0.0) >= float(item.get("start_seconds") or 0.0)
            for item in artifact.transcript_segments
        ),
        "has_speakers": any(str(item.get("speaker") or "").strip() for item in artifact.transcript_segments),
        "has_chapters": False,
        "transcript_segments": len(artifact.transcript_segments),
        "source_candidates": len(artifact.source_candidates),
    }
    return artifact

async def research_source_candidates(
    artifact: VideoEvalArtifact,
    *,
    max_candidates: int | None = None,
) -> VideoEvalArtifact:
    """Verify transcript references through the AI-only research service."""
    from app.services.debate_research import research_claim

    transcript = " ".join(
        str(item.get("text") or "") for item in artifact.transcript_segments
    )
    existing_values = {
        str(item.get("value") or "").casefold()
        for item in artifact.source_candidates
        if str(item.get("value") or "").strip()
    }
    ai_candidates = await extract_source_candidates_with_ai(
        transcript,
        (
            TranscriptSegment(**item)
            for item in artifact.transcript_segments
            if isinstance(item, dict)
        ),
    )
    for candidate in ai_candidates:
        if candidate.value.casefold() in existing_values:
            continue
        artifact.source_candidates.append(asdict(candidate))
        existing_values.add(candidate.value.casefold())
    candidates = artifact.source_candidates if max_candidates is None else artifact.source_candidates[:max_candidates]
    verified: list[dict[str, Any]] = []
    for candidate in candidates:
        value = str(candidate.get("value") or "")
        context = str(candidate.get("context") or value)
        if not value:
            continue
        try:
            result = await research_claim(context, value)
        except Exception as exc:
            verified.append({
                "candidate": value,
                "status": "unavailable",
                "error": str(exc),
                "sources": [],
            })
            continue
        verified.append({
            "candidate": value,
            "status": result.status,
            "error": result.error,
            "sources": [source.model_dump(mode="json") for source in result.sources],
        })
    artifact.verified_sources = verified
    artifact.improvement_notes.append(
        "Quellenkandidaten wurden pro Claim an die KI-Recherche übergeben; "
        "Wikipedia und DuckDuckGo bleiben ausgeschlossen."
    )
    return artifact


async def evaluate_rhetoric_profile(
    artifact: VideoEvalArtifact,
    *,
    sample_chars: int = 12000,
) -> VideoEvalArtifact:
    """Ask the configured ChatGPT Web lane to review the deterministic profile.

    The review is stored as evidence alongside the local metrics. It never
    edits prompts, model routing, or production settings automatically.
    """
    profile_json = json.dumps(artifact.rhetorical_profile, ensure_ascii=False, indent=2)
    transcript = " ".join(
        str(item.get("text") or "") for item in artifact.transcript_segments
    )[:max(1000, sample_chars)]
    prompt = (
        "Bewerte das Debatten-Sprachprofil anhand der folgenden Messwerte und des "
        "Transkriptauszugs. Nenne konkrete beobachtete Muster, starke rhetorische "
        "Techniken, verbesserbare Punkte und zwei messbare Evaluationskriterien. "
        "Erfinde keine Fakten und schreibe keine neue Antwort für die Debatte.\\n\\n"
        "MESSWERTE:\\n" + profile_json + "\\n\\nTRANSKRIPTAUSZUG:\\n" + transcript
    )
    try:
        from app.services.chatgpt_web import generate

        review = await generate(
            prompt,
            system=(
                "Du bist der Rhetorik-Evaluator der Experimentell-DebateAI-Pipeline. "
                "Arbeite konkret, fair und prüfbar. Gib nur die Profilbewertung zurück."
            ),
            reasoning_effort="high",
            research="none",
        )
        artifact.rhetorical_profile["ai_review"] = {
            "provider": "chatgpt_web",
            "status": "completed",
            "text": str(review or "").strip()[:12000],
        }
        artifact.improvement_notes.append(
            "ChatGPT Web hat das lokale Sprachprofil bewertet; die Bewertung bleibt "
            "ein Review-Artefakt und ändert keine Prompts automatisch."
        )
    except Exception as exc:
        artifact.rhetorical_profile["ai_review"] = {
            "provider": "chatgpt_web",
            "status": "unavailable",
            "text": "",
            "error": str(exc),
        }
        artifact.improvement_notes.append(
            "Die ChatGPT-Web-Rhetorikbewertung war nicht verfügbar; lokale Metriken "
            "und Evaluationsfälle wurden trotzdem gespeichert."
        )
    return artifact


def update_style_profile(
    profile_path: str | Path,
    profile: dict[str, Any],
) -> Path:
    """Merge a reviewed rhetoric profile into a persistent local JSON file."""
    path = Path(profile_path)
    current: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except (OSError, ValueError):
            current = {}
    history = list(current.get("history") or [])
    history.append(profile)
    history = history[-50:]
    merged = dict(profile)
    merged["history"] = history
    merged["profile_revision"] = len(history)
    merged["review_required_before_prompt_change"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def save_artifact(artifact: VideoEvalArtifact, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(artifact), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
