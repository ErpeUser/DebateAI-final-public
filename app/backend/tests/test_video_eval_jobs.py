import asyncio

import pytest
from app.services import video_eval_jobs as jobs
from app.services.video_eval_jobs import (
    DefaultGeminiTranscriber,
    SubtitleTrack,
    VideoJobError,
    VideoJobStore,
    VideoSourceProbe,
    normalize_subtitle_text,
    retrieve_subtitles,
    validate_public_url,
)
from app.services.video_eval_pipeline import TranscriptSegment


def _probe(*tracks):
    return VideoSourceProbe(
        source_url="https://www.youtube.com/watch?v=abc",
        video_id="abc",
        title="Debatte",
        duration_seconds=10,
        platform="YouTube",
        subtitles=tuple(tracks),
        metadata={"title": "Debatte"},
    )


def test_normalize_vtt_is_timestamped_and_extracts_speaker():
    rows = normalize_subtitle_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\n<v Alice>Eine Behauptung.\n",
        video_id="abc",
    )
    assert rows == [TranscriptSegment(1.0, 2.5, "Eine Behauptung.", "Alice")]


def test_manual_subtitles_win_over_automatic_without_video_download(monkeypatch):
    calls = []

    async def fetch(url):
        calls.append(url)
        return b"1\n00:00:00,000 --> 00:00:01,000\nManuell.\n"

    async def allow(url):
        return url

    monkeypatch.setattr(jobs, "validate_public_url", allow)

    probe = _probe(
        SubtitleTrack(
            "https://cdn.example.test/auto.vtt", "de", "automatic", "vtt", "automatic"
        ),
        SubtitleTrack(
            "https://cdn.example.test/manual.srt", "de", "manual", "srt", "manual"
        ),
    )

    async def run():
        return await retrieve_subtitles(probe, fetcher=fetch)

    rows, meta = asyncio.run(run())
    assert rows[0].text == "Manuell."
    assert meta["source"] == "manual"
    assert calls == ["https://cdn.example.test/manual.srt"]


def test_missing_subtitles_enters_consent_then_key_error(tmp_path, monkeypatch):
    probe = _probe()

    async def fake_probe(*_args, **_kwargs):
        return probe

    async def fake_retrieve(*_args, **_kwargs):
        return [], {"available": False, "reason": "no_parseable_subtitle"}

    monkeypatch.setattr(jobs, "probe_video_source", fake_probe)
    monkeypatch.setattr(jobs, "retrieve_subtitles", fake_retrieve)
    store = VideoJobStore(tmp_path, gemini=DefaultGeminiTranscriber(api_key=""))

    async def run():
        payload, _ = store.create(probe.source_url)
        store.start(payload["id"])
        waiting = await store.wait(payload["id"])
        assert waiting["status"] == "awaiting_consent"
        await store.consent(payload["id"], provider="gemini_api", approved=True)
        failed = await store.wait(payload["id"])
        return failed

    failed = asyncio.run(run())
    assert failed["status"] == "failed"
    assert failed["error_code"] == "gemini_key_missing"


def test_consent_denial_preserves_checkpoint_and_artifact_access_is_scoped(
    tmp_path, monkeypatch
):
    probe = _probe(
        SubtitleTrack(
            "https://cdn.example.test/manual.vtt", "de", "manual", "vtt", "manual"
        )
    )

    async def fake_probe(*_args, **_kwargs):
        return probe

    async def fake_retrieve(*_args, **_kwargs):
        return [TranscriptSegment(0, 1, "Quelle: Studie 2024", "S1")], {
            "available": True,
            "source": "manual",
            "content_hash": "hash",
            "format": "vtt",
        }

    monkeypatch.setattr(jobs, "probe_video_source", fake_probe)
    monkeypatch.setattr(jobs, "retrieve_subtitles", fake_retrieve)
    store = VideoJobStore(tmp_path)

    async def run():
        payload, _ = store.create(probe.source_url)
        store.start(payload["id"])
        complete = await store.wait(payload["id"])
        assert complete["status"] == "completed"
        with pytest.raises(VideoJobError, match="Zugriff"):
            store.artifact(payload["id"], token="wrong")
        return store.artifact(payload["id"], token=payload["access_token"])

    artifact = asyncio.run(run())
    assert artifact["rhetorical_evidence"]["branch"] == "A1_rhetoric_evidence"
    assert artifact["argument_evidence"]["branch"] == "A2_argument_source_evidence"
    assert artifact["provenance"]["video_downloaded"] is False


def test_default_gemini_rejects_non_youtube_even_with_key():
    async def run():
        with pytest.raises(VideoJobError) as error:
            await DefaultGeminiTranscriber(api_key="test").transcribe(
                "https://video.example.test/watch/1", language="de-DE"
            )
        return error.value.code

    assert asyncio.run(run()) == "gemini_url_unsupported"


def test_public_url_validation_blocks_private_dns(monkeypatch):
    def private(*_args, **_kwargs):
        return [(None, None, None, None, ("10.0.0.4", 0))]

    monkeypatch.setattr(jobs.socket, "getaddrinfo", private)

    async def run():
        with pytest.raises(VideoJobError, match="private"):
            await validate_public_url("https://example.test/video")

    asyncio.run(run())
