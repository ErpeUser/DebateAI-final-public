"""Backend/frontend contract for link-first video evaluation jobs.

The router is intentionally separate from ``main.py``.  The final integrator
can register it with ``app.include_router(video_eval.router)`` after reviewing
the contract; tests and mock frontends can include it directly today.
"""

from __future__ import annotations

from typing import Any

from app.services.video_eval_jobs import VideoJobError, VideoJobStore
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

router = APIRouter(prefix="/api/video-eval", tags=["video-eval"])
_store = VideoJobStore()


class CreateVideoJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: HttpUrl
    language: str = Field(default="de-DE", min_length=2, max_length=20)


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1, max_length=80)
    approved: bool


def _raise(exc: VideoJobError) -> None:
    status = {
        "not_found": 404,
        "forbidden": 403,
        "not_ready": 409,
        "invalid_state": 409,
        "provider_not_allowed": 400,
    }.get(exc.code, 400)
    raise HTTPException(
        status_code=status, detail={"code": exc.code, "message": exc.message}
    ) from exc


def _token_matches(job_id: str, token: str) -> bool:
    payload = _store.get(job_id, include_token=True)
    return bool(payload and token and token == payload.get("access_token"))


@router.post("/jobs", status_code=202)
async def create_video_eval_job(request: CreateVideoJobRequest) -> dict[str, Any]:
    payload, deduplicated = _store.create(str(request.url), language=request.language)
    _store.start(str(payload["id"]))
    payload["deduplicated"] = deduplicated
    return payload


@router.get("/jobs/{job_id}")
async def get_video_eval_job(
    job_id: str,
    x_debateai_job_token: str = Header(default=""),
) -> dict[str, Any]:
    payload = _store.get(job_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Videojob nicht gefunden."},
        )
    if not _token_matches(job_id, x_debateai_job_token):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden",
                "message": "Der Zugriff auf diesen Job ist nicht erlaubt.",
            },
        )
    return payload


@router.post("/jobs/{job_id}/consent")
async def consent_video_eval_job(
    job_id: str,
    request: ConsentRequest,
    x_debateai_job_token: str = Header(default=""),
) -> dict[str, Any]:
    if not _token_matches(job_id, x_debateai_job_token):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden",
                "message": "Der Zugriff auf diesen Job ist nicht erlaubt.",
            },
        )
    try:
        return await _store.consent(
            job_id, provider=request.provider, approved=request.approved
        )
    except VideoJobError as exc:
        _raise(exc)
    raise AssertionError("unreachable")


@router.post("/jobs/{job_id}/cancel")
async def cancel_video_eval_job(
    job_id: str,
    x_debateai_job_token: str = Header(default=""),
) -> dict[str, Any]:
    if not _token_matches(job_id, x_debateai_job_token):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden",
                "message": "Der Zugriff auf diesen Job ist nicht erlaubt.",
            },
        )
    try:
        return await _store.cancel(job_id)
    except VideoJobError as exc:
        _raise(exc)
    raise AssertionError("unreachable")


@router.get("/jobs/{job_id}/artifact")
async def get_video_eval_artifact(
    job_id: str,
    x_debateai_job_token: str = Header(default=""),
) -> dict[str, Any]:
    try:
        return _store.artifact(job_id, token=x_debateai_job_token)
    except VideoJobError as exc:
        _raise(exc)
    raise AssertionError("unreachable")


__all__ = ["router"]
