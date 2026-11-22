import asyncio
import pathlib
import sys
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import get_db
from app.routers import quality_lab


async def _fake_db():
    yield object()


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(quality_lab.router)
    app.dependency_overrides[get_db] = _fake_db
    return app


def _payload(**overrides):
    value = {
        "claim": "Soll eine Stadt den ÖPNV ausbauen?",
        "context": "Kurze deutschsprachige Debatte.",
        "allowed_sources": ["https://example.test/verkehr"],
        "dataset_id": "contract",
        "holdout": True,
        "model_ids": ["gemini-3.5-flash", "gpt-5.6-luna"],
    }
    value.update(overrides)
    return value


def test_quality_lab_runs_two_real_generation_calls_and_returns_metadata():
    calls = []

    async def generate(model_id, prompt, **kwargs):
        calls.append((model_id, prompt, kwargs))
        return f"Antwort von {model_id}"

    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        response = client.post("/api/quality-lab/runs", json=_payload())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dataset_id"] == "contract"
    assert body["holdout"] is True
    assert body["holdout_verified"] is False
    assert body["can_apply"] is False
    assert body["can_rollback"] is False
    assert sorted(body["blind_order"]) == ["A", "B"]
    assert [item["model_id"] for item in body["candidates"]] == [
        "gemini-3.5-flash",
        "gpt-5.6-luna",
    ]
    assert all(item["available"] for item in body["candidates"])
    assert all(item["prompt_hash"] for item in body["candidates"])
    assert {item[0] for item in calls} == {
        "gemini-3.5-flash",
        "gpt-5.6-luna",
    }


def test_quality_lab_rejects_duplicate_models_before_provider_calls():
    with patch.object(quality_lab, "generate_text", new=AsyncMock()) as generate:
        client = TestClient(_app())
        response = client.post(
            "/api/quality-lab/runs",
            json=_payload(model_ids=["gemini-3.5-flash", "gemini-3.5-flash"]),
        )
    assert response.status_code == 422
    generate.assert_not_awaited()


def test_quality_lab_ratings_are_bound_to_run_and_apply_is_explicitly_blocked():
    async def generate(model_id, prompt, **kwargs):
        return "Antwort"

    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        run = client.post("/api/quality-lab/runs", json=_payload()).json()
        run_id = run["run_id"]
        rating = {
            "ratings": {
                "A": {
                    "naturalness": 4,
                    "strength": 4,
                    "precision": 5,
                    "source_honesty": 4,
                    "usability": 4,
                    "both_unsuitable": False,
                },
                "B": {
                    "naturalness": 3,
                    "strength": 3,
                    "precision": 3,
                    "source_honesty": 3,
                    "usability": 3,
                    "both_unsuitable": False,
                },
            },
            "preferred": "A",
            "holdout": True,
            "dataset_id": "contract",
        }
        assert client.post(f"/api/quality-lab/runs/{run_id}/ratings", json=rating).json() == {
            "saved": True,
            "agreement": None,
        }
        apply_response = client.post(
            f"/api/quality-lab/runs/{run_id}/apply",
            json={"variant_id": run["candidates"][0]["variant_id"]},
        )
        rollback_response = client.post(f"/api/quality-lab/runs/{run_id}/rollback")

    assert apply_response.status_code == 409
    assert "keine freigegebene Promptvariante" in apply_response.json()["detail"]
    assert rollback_response.status_code == 409
    assert "keine aktivierte Promptvariante" in rollback_response.json()["detail"]


def test_quality_lab_rejects_rating_from_another_dataset():
    async def generate(model_id, prompt, **kwargs):
        return "Antwort"

    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        run = client.post("/api/quality-lab/runs", json=_payload()).json()
        response = client.post(
            f"/api/quality-lab/runs/{run['run_id']}/ratings",
            json={
                "ratings": {
                    "A": {
                        "naturalness": 4,
                        "strength": 4,
                        "precision": 4,
                        "source_honesty": 4,
                        "usability": 4,
                        "both_unsuitable": False,
                    },
                    "B": {
                        "naturalness": 3,
                        "strength": 3,
                        "precision": 3,
                        "source_honesty": 3,
                        "usability": 3,
                        "both_unsuitable": False,
                    },
                },
                "preferred": "tie",
                "holdout": False,
                "dataset_id": "other",
            },
        )
    assert response.status_code == 409


def test_quality_lab_rejects_incomplete_rating():
    async def generate(model_id, prompt, **kwargs):
        return "Antwort"

    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        run = client.post("/api/quality-lab/runs", json=_payload()).json()
        response = client.post(
            f"/api/quality-lab/runs/{run['run_id']}/ratings",
            json={
                "ratings": {"A": {}, "B": {}},
                "preferred": "tie",
                "holdout": True,
                "dataset_id": "contract",
            },
        )
    assert response.status_code == 422


def test_quality_lab_rejects_invalid_dimension_even_when_both_unsuitable():
    async def generate(model_id, prompt, **kwargs):
        return "Antwort"

    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        run = client.post("/api/quality-lab/runs", json=_payload()).json()
        response = client.post(
            f"/api/quality-lab/runs/{run['run_id']}/ratings",
            json={
                "ratings": {
                    "A": {"naturalness": 99, "both_unsuitable": True},
                    "B": {"both_unsuitable": True},
                },
                "preferred": "tie",
                "holdout": True,
                "dataset_id": "contract",
            },
        )
    assert response.status_code == 422


def test_quality_lab_accepts_null_dimensions_when_both_unsuitable():
    async def generate(model_id, prompt, **kwargs):
        return "Antwort"

    dimensions = {
        "naturalness": None,
        "strength": None,
        "precision": None,
        "source_honesty": None,
        "usability": None,
        "both_unsuitable": True,
    }
    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        run = client.post("/api/quality-lab/runs", json=_payload()).json()
        response = client.post(
            f"/api/quality-lab/runs/{run['run_id']}/ratings",
            json={
                "ratings": {"A": dimensions, "B": dimensions},
                "preferred": "tie",
                "holdout": True,
                "dataset_id": "contract",
            },
        )
    assert response.status_code == 200, response.text
    assert response.json() == {"saved": True, "agreement": None}


def test_quality_lab_cancels_the_other_provider_call_after_failure():
    cancelled = asyncio.Event()

    async def generate(model_id, prompt, **kwargs):
        if model_id == "gemini-3.5-flash":
            raise ValueError("provider unavailable")
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.set()
        return "unreachable"

    with (
        patch.object(quality_lab, "generate_text", side_effect=generate),
        patch.object(quality_lab, "is_local_only", new=AsyncMock(return_value=False)),
    ):
        client = TestClient(_app())
        response = client.post("/api/quality-lab/runs", json=_payload())

    assert response.status_code == 400
    assert cancelled.is_set()
