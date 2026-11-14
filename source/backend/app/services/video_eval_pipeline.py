"""Video-to-evaluation pipeline for DebateAI.

The pipeline deliberately keeps cloud work out of the live answer path. It
transcribes a supplied audio/video export with Google Cloud Speech-to-Text,
extracts source candidates from the transcript, creates reproducible rhetoric
and response-evaluation cases, and stores one JSON artifact for later review.
No automatic prompt/model change is applied from an artifact.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

_URL_RE = re.compile(r"https?://[^\\s<>\\\"]+")
_DOI_RE = re.compile(r"\\b10\\.\\d{4,9}/[-._;()/:A-Z0-9]+\\b", re.IGNORECASE)
_STUDY_RE = re.compile(
    r"\\b(?:studie|paper|bericht|metaanalyse|meta-analyse|untersuchung)"
    r"[^.]{0,160}\\b(?:19|20)\\d{2}\\b",
    re.IGNORECASE,
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
    for start, end, candidate, kind in sorted(matches):
        key = (kind, candidate.casefold())
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
    rebuttals = sum(bool(re.search(r"\\b(aber|jedoch|stimmt nicht|falsch|trotzdem|widerleg)\\b", text, re.I)) for text in texts)
    analogies = sum(bool(re.search(r"\\b(wie|als ob|beispiel|vergleich|analogie)\\b", text, re.I)) for text in texts)
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


def transcribe_with_google_cloud(
    audio_path: str | Path,
    *,
    language_code: str = "de-DE",
    project_id: str | None = None,
    location: str = "global",
    speaker_diarization: bool = False,
    timeout_seconds: int = 1800,
) -> list[TranscriptSegment]:
    """Transcribe a local audio/video export through Google Speech-to-Text v2.

    The Google dependency is imported lazily so the application can start
    without cloud credentials. Set GOOGLE_CLOUD_PROJECT or pass project_id.
    """
    try:
        from google.cloud import speech_v2
        from google.cloud.speech_v2.types import cloud_speech
    except ImportError as exc:
        raise RuntimeError("google-cloud-speech is required for video transcription") from exc
    import os

    project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Google transcription")
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    client = speech_v2.SpeechClient()
    recognizer = f"projects/{project}/locations/{location}/recognizers/_"
    config_kwargs: dict[str, Any] = {
        "auto_decoding_config": cloud_speech.AutoDetectDecodingConfig(),
        "language_codes": [language_code],
        "model": "long",
    }
    if speaker_diarization:
        config_kwargs["diarization_config"] = cloud_speech.SpeakerDiarizationConfig(
            min_speaker_count=1,
            max_speaker_count=8,
        )
    config = cloud_speech.RecognitionConfig(**config_kwargs)
    request = cloud_speech.BatchRecognizeRequest(
        recognizer=recognizer,
        config=config,
        files=[cloud_speech.BatchRecognizeFile(
            uri=path.as_uri(),
            config=cloud_speech.RecognitionConfig(**config_kwargs),
        )],
    )
    operation = client.batch_recognize(request=request)
    response = operation.result(timeout=timeout_seconds)
    segments: list[TranscriptSegment] = []
    for result_set in getattr(response, "results", {}).values():
        for result in getattr(result_set, "transcript", []) or []:
            alternatives = getattr(result, "alternatives", []) or []
            if not alternatives:
                continue
            alternative = alternatives[0]
            words = getattr(alternative, "words", []) or []
            start = float(getattr(words[0].start_offset, "total_seconds", lambda: 0)()) if words else 0.0
            end = float(getattr(words[-1].end_offset, "total_seconds", lambda: start)()) if words else start
            speaker = str(getattr(words[0], "speaker_label", "") or "") if words else ""
            segments.append(TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                text=_clean(getattr(alternative, "transcript", "")),
                speaker=speaker,
                confidence=float(getattr(alternative, "confidence", 0) or 0) or None,
            ))
    return segments


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


def save_artifact(artifact: VideoEvalArtifact, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(artifact), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
