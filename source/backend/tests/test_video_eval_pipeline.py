import asyncio

from app.services.video_eval_pipeline import (
    attach_media_metadata,
    SourceCandidate,
    TranscriptSegment,
    build_eval_cases,
    build_rhetorical_profile,
    extract_source_candidates,
)


def test_extract_source_candidates_keeps_urls_dois_and_study_years():
    text = "Siehe https://example.org/report, DOI 10.1234/ABC-1 und Studie zur Wirkung 2021."
    rows = extract_source_candidates(text)
    assert {row.kind for row in rows} == {"url", "doi", "study_reference"}
    assert any(row.value == "https://example.org/report" for row in rows)


def test_video_source_extraction_redacts_pii_before_external_call(monkeypatch):
    from app.services import chatgpt_web
    from app.services.video_eval_pipeline import extract_source_candidates_with_ai

    prompts = []

    async def fake_generate(prompt, **_kwargs):
        prompts.append(prompt)
        return "[]"

    monkeypatch.setattr(chatgpt_web, "configured", lambda: True)
    monkeypatch.setattr(chatgpt_web, "runtime_available", lambda: True)
    monkeypatch.setattr(chatgpt_web, "generate", fake_generate)

    asyncio.run(
        extract_source_candidates_with_ai(
            "Kontakt +49 30 12345678; Quelle https://example.org/report"
        )
    )

    assert prompts
    assert "+49 30 12345678" not in prompts[0]
    assert "[REDACTED_PHONE]" in prompts[0]


def test_rhetorical_profile_counts_debate_moves():
    segments = [
        TranscriptSegment(0, 2, "Ist das wirklich immer so?"),
        TranscriptSegment(2, 5, "Nein, aber ein Beispiel ist der Handytarif."),
        TranscriptSegment(5, 8, "Das stimmt nicht, weil der Maßstab sonst doppelt wäre."),
    ]
    profile = build_rhetorical_profile(segments, source_candidates=[])
    assert profile["question_rate"] > 0
    assert profile["rebuttal_rate"] > 0
    assert profile["analogy_rate"] > 0


def test_eval_cases_do_not_turn_transcript_into_ground_truth():
    segments = [TranscriptSegment(0, 2, "Alles wird teurer.", speaker="S1")]
    candidates = [SourceCandidate("10.1234/x", "doi", "context", 0)]
    cases = build_eval_cases(segments, source_candidates=candidates)
    assert cases[0]["expected_response"] == ""
    assert cases[0]["difficulty"] == "source_check"
    assert cases[0]["source_candidates"] == ["10.1234/x"]


def test_attach_media_metadata_records_hashes_and_quality_checks(tmp_path):
    media = tmp_path / "sample.wav"
    media.write_bytes(b"pcm-test")
    artifact = attach_media_metadata(
        build_video_artifact(
            video_id="v1",
            source_url="https://example.test/watch?v=1",
            segments=[TranscriptSegment(0, 2, "Eine Studie von Ada 2021.", speaker="S1")],
        ),
        media,
    )
    assert artifact.original_url == artifact.source_url
    assert artifact.source_platform == "example.test"
    assert artifact.audio_hash
    assert artifact.duration_seconds == 2
    assert artifact.ingestion_checks["has_timestamps"] is True
    assert artifact.ingestion_checks["has_speakers"] is True
    assert artifact.ingestion_checks["audio_hash_available"] is True


def test_attach_media_metadata_keeps_audio_identity_for_video_fallback(tmp_path):
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"not-a-real-container")
    artifact = attach_media_metadata(
        build_video_artifact(
            video_id="v-video",
            source_url="https://example.test/video/1",
            segments=[TranscriptSegment(0, 1, "Beispiel.", speaker="S1")],
        ),
        media,
    )
    assert artifact.video_hash
    assert artifact.audio_hash
    assert artifact.ingestion_checks["audio_hash_kind"] in {"decoded_audio", "container_fallback"}
