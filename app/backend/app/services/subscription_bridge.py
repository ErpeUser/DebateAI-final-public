"""Register the optional desktop OAuth bridge as a normal local endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomEndpoint
from app.services.custom_endpoints import (
    create_endpoint,
    get_endpoint,
    probe,
    update_endpoint,
)
from app.services.secrets import get_secret, set_secret
from app.services.identity import env_value, set_env

BRIDGE_ENDPOINT_ID = "subscription-ai"
BRIDGE_NAME = "Subscription AI"
GEMINI_WEB_ENDPOINT_ID = "gemini-web"
GEMINI_WEB_NAME = "Gemini Web"
GEMINI_WEB_WIRE_MODEL = "gemini-3.1-pro"
GEMINI_WEB_COOKIE_SECRET = "credentials.gemini_web.cookie"


def _gemini_web_cookie_path() -> Path | None:
    value = env_value("DEBATEAI_GEMINI_WEB_COOKIE_FILE").strip()
    return Path(value) if value else None


def materialize_gemini_web_cookie(value: str) -> None:
    """Expose the encrypted credential only as a short-lived runtime file."""
    path = _gemini_web_cookie_path()
    if path is None:
        return
    if not value:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(value, encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    os.replace(temporary, path)


def cleanup_gemini_web_cookie() -> None:
    path = _gemini_web_cookie_path()
    if path is not None:
        try:
            # The desktop consumes and removes the non-empty credential handoff,
            # so a later unlink is indistinguishable from the normal running
            # state.  An empty file is the explicit disconnect/shutdown signal
            # that makes the watcher stop the helper and forget its in-memory
            # restart credential.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
        except OSError:
            pass


async def restore_gemini_web_cookie(db: AsyncSession) -> bool:
    value = await get_secret(db, GEMINI_WEB_COOKIE_SECRET)
    materialize_gemini_web_cookie(value)
    return bool(value)


async def save_gemini_web_cookie(db: AsyncSession, value: str) -> None:
    await set_secret(db, GEMINI_WEB_COOKIE_SECRET, value)


async def stored_gemini_web_cookie_configured(db: AsyncSession) -> bool:
    return bool(await get_secret(db, GEMINI_WEB_COOKIE_SECRET))


def gemini_web_cookie_configured() -> bool:
    if env_value("DEBATEAI_GEMINI_WEB_SESSION_ACTIVE") == "1":
        return True
    path = env_value("DEBATEAI_GEMINI_WEB_COOKIE_FILE").strip()
    try:
        return bool(path and Path(path).is_file() and Path(path).stat().st_size > 32)
    except OSError:
        return False


def gemini_web_models() -> list[str]:
    try:
        values = json.loads(env_value("DEBATEAI_GEMINI_WEB_MODELS", "[]"))
    except (TypeError, ValueError):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


async def sync_gemini_web_bridge(db: AsyncSession):
    url = env_value("DEBATEAI_GEMINI_WEB_URL").strip()
    key = env_value("DEBATEAI_GEMINI_WEB_KEY").strip()
    if not url or not key:
        return None
    configured = gemini_web_cookie_configured()
    served: list[str] = []
    if configured:
        # The launcher restarts the bridge after a re-login in a separate
        # watcher thread.  Give that process enough time to replace an expired
        # session and finish live account discovery before persisting a false
        # disabled state for an otherwise valid login.
        for _attempt in range(100):
            ok, _message, served = await probe(url, key, timeout=1.0)
            # /models is reachable before the authenticated Gemini session has
            # finished discovering its live account catalog.  An empty 200 is
            # transitional and must not disable the endpoint permanently.
            if ok and served:
                break
            await asyncio.sleep(0.25)
        if not ok:
            served = []
    set_env(
        "DEBATEAI_GEMINI_WEB_MODELS",
        json.dumps(served, separators=(",", ":")),
    )
    models = [{"id": model, "label": model} for model in served]
    endpoint = await get_endpoint(db, GEMINI_WEB_ENDPOINT_ID)
    if endpoint is None:
        # A user may have removed this auto-managed endpoint in an older run.
        # Revive the exact stable slug instead of creating gemini-web-2, which
        # would no longer match the configured deep-analysis model id.
        endpoint = await db.get(CustomEndpoint, GEMINI_WEB_ENDPOINT_ID)
        if endpoint is not None:
            endpoint.deleted_at = None
    if endpoint is None:
        return await create_endpoint(
            db,
            name=GEMINI_WEB_NAME,
            base_url=url,
            api_key=key,
            models=models,
            enabled=configured and bool(served),
        )
    return await update_endpoint(
        db,
        endpoint,
        base_url=url,
        api_key=key,
        models=models,
        enabled=configured and bool(served),
    )


async def sync_subscription_bridge(db: AsyncSession):
    if _gemini_web_cookie_path() is not None:
        await restore_gemini_web_cookie(db)
    url = env_value("DEBATEAI_SUBSCRIPTION_BRIDGE_URL").strip()
    key = env_value("DEBATEAI_SUBSCRIPTION_BRIDGE_KEY").strip()
    if not url or not key:
        return await sync_gemini_web_bridge(db)

    endpoint = await get_endpoint(db, BRIDGE_ENDPOINT_ID)
    ok = False
    served: list[str] = []
    ok, _message, served = await probe(url, key, timeout=3.0)
    if ok:
        set_env(
            "DEBATEAI_SUBSCRIPTION_MODELS",
            json.dumps(served, separators=(",", ":")),
        )
    models = [{"id": model} for model in served] if ok else None
    if endpoint is None:
        result = await create_endpoint(
            db,
            name=BRIDGE_NAME,
            base_url=url,
            api_key=key,
            models=models or [],
            enabled=True,
        )
    else:
        result = await update_endpoint(
            db,
            endpoint,
            base_url=url,
            api_key=key,
            models=models,
            enabled=True,
        )
    await sync_gemini_web_bridge(db)
    return result
