"""Safe UI surface for Google and OpenAI OAuth on the local desktop bridge."""

from __future__ import annotations

import asyncio

from app.database import get_db
from app.services import subscription_oauth
from app.services.ai_config import ensure_gemini_cli_route
from app.services.subscription_bridge import sync_subscription_bridge
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/subscription-accounts", tags=["subscription-accounts"])


def _provider_message(provider: str, model_values: list[str]) -> str:
    if provider == subscription_oauth.GEMINI_PROVIDER:
        selected = subscription_oauth.preferred_gemini_model(model_values)
        if selected:
            return (
                f"Google-OAuth ist aktiv; {selected} steht mit Denkstufe High bereit."
            )
        return "Google-OAuth ist aktiv, aber die Bridge meldet noch kein Gemini-Modell."
    if any(model.casefold().startswith("gpt-") for model in model_values):
        return "OpenAI-OAuth ist aktiv; die Modelle des neuen Kontos stehen bereit."
    return (
        "OpenAI-OAuth wurde abgeschlossen, aber die Bridge meldet noch kein GPT-Modell."
    )


async def _status(*, message: str = "", login_state: str = "idle") -> dict[str, object]:
    model_values = await subscription_oauth.models()
    selected_gemini = subscription_oauth.preferred_gemini_model(model_values)
    gemini_ready = bool(selected_gemini)
    openai_ready = any(model.casefold().startswith("gpt-") for model in model_values)
    return {
        "available": subscription_oauth.available(),
        "models": model_values,
        "gemini": {
            "provider": subscription_oauth.GEMINI_PROVIDER,
            "model": selected_gemini or subscription_oauth.GEMINI_31_PRO_MODEL,
            "thinking": "high",
            "ready": gemini_ready,
        },
        "openai": {
            "provider": subscription_oauth.OPENAI_PROVIDER,
            "ready": openai_ready,
        },
        "login_state": login_state,
        "message": message
        or (
            "Gemini CLI und OpenAI koennen hier ohne API-Key per OAuth angemeldet werden."
        ),
    }


@router.get("/status")
async def read_status():
    return await _status()


@router.post("/login/{provider}")
async def start_login(provider: str):
    try:
        flow = await subscription_oauth.start_login(provider)
    except subscription_oauth.SubscriptionOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        **await _status(
            login_state="pending",
            message="Oeffne die sichere Anmeldeseite und waehle das gewuenschte Konto.",
        ),
        **flow,
    }


@router.get("/login/{provider}")
async def poll_login(
    provider: str,
    state: str = Query(min_length=8, max_length=512),
    db: AsyncSession = Depends(get_db),
):
    if provider not in subscription_oauth.SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unbekannter Anmeldeanbieter.")
    try:
        result = await subscription_oauth.login_status(state)
    except subscription_oauth.SubscriptionOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result["status"] == "wait":
        return await _status(
            login_state="pending", message="Die Anmeldung wartet auf Bestaetigung."
        )
    if result["status"] == "error":
        return await _status(
            login_state="error",
            message=result["error"] or "Die OAuth-Anmeldung ist fehlgeschlagen.",
        )

    # The bridge watches its auth directory, but provider registration and the
    # endpoint catalog can trail the OAuth completion briefly.
    model_values: list[str] = []
    for _attempt in range(20):
        model_values = await subscription_oauth.models(timeout=2.0)
        expected = (
            bool(subscription_oauth.preferred_gemini_model(model_values))
            if provider == subscription_oauth.GEMINI_PROVIDER
            else any(model.casefold().startswith("gpt-") for model in model_values)
        )
        if expected:
            break
        await asyncio.sleep(0.25)
    await sync_subscription_bridge(db)
    await db.commit()
    if provider == subscription_oauth.GEMINI_PROVIDER:
        selected_gemini = subscription_oauth.preferred_gemini_model(model_values)
        if selected_gemini:
            ensure_gemini_cli_route(selected_gemini)
    return await _status(
        login_state="complete",
        message=_provider_message(provider, model_values),
    )


@router.post("/verify/gemini-cli")
async def verify_gemini_cli():
    try:
        result = await subscription_oauth.verify_preferred_gemini_high()
    except subscription_oauth.SubscriptionOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    ensure_gemini_cli_route(result["model"])
    return {
        **await _status(
            login_state="complete",
            message=f"{result['model']} wurde mit einer echten High-Anfrage bestaetigt.",
        ),
        "verification": result,
    }
