import asyncio
import os

from app.database import get_db
from app.models import Session
from app.services import runtime_activity
from app.services.request_guard import instance_token_matches
from app.services.update_service import UpdateService, get_update_service
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

router = APIRouter(prefix="/api/updates", tags=["updates"])


class GrantIn(BaseModel):
    grant: str


def start_background_check():
    desktop = os.environ.get("DEBATEAI_DESKTOP", "")
    if desktop != "1":
        return None
    service = get_update_service()
    if not service.enabled:
        return None
    return asyncio.create_task(asyncio.to_thread(get_update_service().check))


def stop_background_check(task) -> None:
    if task:
        task.cancel()


async def shutdown_reserved_handler(
    request: Request, exc: runtime_activity.ShutdownReserved
):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


def configure_app(app: FastAPI) -> None:
    app.title = "DebateAI"
    app.add_exception_handler(
        runtime_activity.ShutdownReserved, shutdown_reserved_handler
    )
    desktop = os.environ.get("DEBATEAI_DESKTOP", "")
    if desktop == "1":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "localhost",
                "127.0.0.1",
                os.environ.get("DEBATEAI_BOUND_HOST") or "127.0.0.1",
            ],
        )


def require_instance_token(
    request: Request,
    token: str | None = Header(default=None, alias="X-DebateAI-Instance"),
) -> None:
    expected = os.environ.get("DEBATEAI_INSTANCE_TOKEN", "")
    supplied = request.headers.getlist("x-debateai-instance")
    if len(supplied) != 1 or not instance_token_matches(token, expected):
        raise HTTPException(403, "Desktop instance authorization failed")


@router.get("")
def update_status(service: UpdateService = Depends(get_update_service)):
    status = service.status()
    if status.get("state") == "ready":
        status["blocked_reason"] = runtime_activity.busy_reason()
    return status


@router.post("/check", dependencies=[Depends(require_instance_token)])
def check_update(service: UpdateService = Depends(get_update_service)):
    return service.check(force=True)


@router.post("/download", dependencies=[Depends(require_instance_token)])
def start_update_download(service: UpdateService = Depends(get_update_service)):
    """Start a verified independent-channel download."""
    try:
        return service.start_download()
    except (ValueError, RuntimeError) as error:
        raise HTTPException(409, str(error)) from error


# An already open older UI can use its established instance header and route.
@router.post("/grant", dependencies=[Depends(require_instance_token)])
def accept_update_grant(
    body: GrantIn,
    service: UpdateService = Depends(get_update_service),
):
    try:
        return service.start_download(body.grant)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(409, str(error)) from error


@router.delete("/download", dependencies=[Depends(require_instance_token)])
def cancel_update(service: UpdateService = Depends(get_update_service)):
    return service.cancel_download()


@router.post("/apply", dependencies=[Depends(require_instance_token)])
async def apply_update(
    db: AsyncSession = Depends(get_db),
    service: UpdateService = Depends(get_update_service),
):
    if not runtime_activity.reserve_shutdown():
        reason = runtime_activity.busy_reason() or "active work"
        raise HTTPException(409, f"Finish {reason} before installing.")
    accepted = False
    try:
        active = await db.scalar(
            select(func.count()).select_from(Session).where(Session.state == "active")
        )
        if active:
            raise HTTPException(409, "Finish the active call before installing.")
        try:
            result = service.request_apply()
        except RuntimeError as error:
            raise HTTPException(409, str(error)) from error
        accepted = True
        return result
    finally:
        if not accepted:
            runtime_activity.release_shutdown()
