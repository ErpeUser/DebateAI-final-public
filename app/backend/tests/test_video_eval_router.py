import httpx
import pytest
from app.routers import video_eval
from app.services import video_eval_jobs
from app.services.video_eval_jobs import SubtitleTrack, VideoJobStore, VideoSourceProbe
from app.services.video_eval_pipeline import TranscriptSegment
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_video_eval_api_contract_and_artifact_scope(tmp_path, monkeypatch):
    probe = VideoSourceProbe(
        source_url="https://www.youtube.com/watch?v=contract",
        video_id="contract",
        title="Contract",
        duration_seconds=2,
        platform="YouTube",
        subtitles=(
            SubtitleTrack(
                "https://cdn.example.test/manual.vtt", "de", "manual", "vtt", "manual"
            ),
        ),
        metadata={"title": "Contract"},
    )

    async def fake_probe(*_args, **_kwargs):
        return probe

    async def fake_retrieve(*_args, **_kwargs):
        return [TranscriptSegment(0, 1, "Eine Quelle.", "S1")], {
            "available": True,
            "source": "manual",
            "content_hash": "h",
            "format": "vtt",
        }

    monkeypatch.setattr(video_eval_jobs, "probe_video_source", fake_probe)
    monkeypatch.setattr(video_eval_jobs, "retrieve_subtitles", fake_retrieve)
    store = VideoJobStore(tmp_path)
    monkeypatch.setattr(video_eval, "_store", store)
    app = FastAPI()
    app.include_router(video_eval.router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/video-eval/jobs", json={"url": probe.source_url, "language": "de"}
        )
        assert created.status_code == 202
        body = created.json()
        token = body["access_token"]
        await store.wait(body["id"])
        forbidden = await client.get(f"/api/video-eval/jobs/{body['id']}")
        assert forbidden.status_code == 403
        status = await client.get(
            f"/api/video-eval/jobs/{body['id']}",
            headers={"X-DebateAI-Job-Token": token},
        )
        assert status.status_code == 200
        assert status.json()["status"] == "completed"
        artifact = await client.get(
            f"/api/video-eval/jobs/{body['id']}/artifact",
            headers={"X-DebateAI-Job-Token": token},
        )
        assert artifact.status_code == 200
        assert artifact.json()["provenance"]["video_downloaded"] is False
