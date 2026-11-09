"""CRUD and reachability checks for self-hosted OpenAI-compatible endpoints.

Every model listed on a saved endpoint becomes a selectable entry in
GET /api/models, so this router is what turns "I run a model on my own box"
into a named choice in the agent, chat, and analysis pickers.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.custom_endpoints import (
    EndpointError,
    create_endpoint,
    delete_endpoint,
    get_endpoint,
    is_on_prem,
    list_endpoints,
    normalize_models,
    probe,
    record_probe,
    to_dict,
    update_endpoint,
)
from app.services.seed_agents import DESKTOP_DEBATE_ENDPOINT_ID, DESKTOP_DEBATE_WIRE_MODEL
from app.services.redaction import redact_text
from app.services.secrets import MasterKeyUnavailable, decrypt_value, master_key_recovery_message


def _merge_desktop_qwen_models(current: list | None, served: list[str]) -> list[dict]:
    """Keep the 4B fallback and expose only Qwen 3.5 variants seen at runtime."""
    models = normalize_models(current)
    seen = {model["id"] for model in models}
    if DESKTOP_DEBATE_WIRE_MODEL not in seen:
        models.insert(0, {"id": DESKTOP_DEBATE_WIRE_MODEL, "label": "Qwen3 4B"})
        seen.add(DESKTOP_DEBATE_WIRE_MODEL)
    for wire in served:
        if wire in seen or not wire.casefold().startswith("qwen3.5:"):
            continue
        models.append({"id": wire, "label": wire})
        seen.add(wire)
    return models

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


class EndpointModelIn(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    label: str = Field(default="", max_length=200)


class EndpointIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=2048)
    api_key: str = Field(default="", max_length=4096)
    models: list[EndpointModelIn] = Field(default_factory=list, max_length=64)
    enabled: bool = True


class EndpointPatch(BaseModel):
    # Omitted fields keep their stored value; an empty api_key clears the key.
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    api_key: str | None = Field(default=None, max_length=4096)
    models: list[EndpointModelIn] | None = Field(default=None, max_length=64)
    enabled: bool | None = None
    confirm_off_prem: bool = False


class ProbeIn(BaseModel):
    """Reachability check for an endpoint that has not been saved yet."""

    base_url: str = Field(min_length=1, max_length=2048)
    api_key: str = Field(default="", max_length=4096)


def _models_payload(models: list[EndpointModelIn] | None) -> list[dict] | None:
    if models is None:
        return None
    return [m.model_dump() for m in models]


async def _require(db: AsyncSession, endpoint_id: str):
    endpoint = await get_endpoint(db, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail=f"Unknown endpoint: {endpoint_id}")
    return endpoint


@router.get("")
async def list_all(db: AsyncSession = Depends(get_db)):
    return [to_dict(endpoint) for endpoint in await list_endpoints(db)]


@router.post("", status_code=201)
async def add(body: EndpointIn, db: AsyncSession = Depends(get_db)):
    try:
        endpoint = await create_endpoint(
            db,
            name=body.name,
            base_url=body.base_url,
            api_key=body.api_key,
            models=_models_payload(body.models),
            enabled=body.enabled,
        )
    except EndpointError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MasterKeyUnavailable as exc:
        raise HTTPException(status_code=503, detail=master_key_recovery_message(exc)) from exc
    await db.commit()
    await db.refresh(endpoint)
    return to_dict(endpoint)


@router.put("/{endpoint_id}")
async def edit(endpoint_id: str, body: EndpointPatch, db: AsyncSession = Depends(get_db)):
    endpoint = await _require(db, endpoint_id)
    if body.base_url and body.base_url != endpoint.base_url and body.api_key is None:
        raise HTTPException(status_code=409, detail="Changing the endpoint requires re-entering the API key")
    try:
        await update_endpoint(
            db,
            endpoint,
            name=body.name,
            base_url=body.base_url,
            api_key=body.api_key,
            models=_models_payload(body.models),
            enabled=body.enabled,
            confirm_off_prem=body.confirm_off_prem,
        )
    except EndpointError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MasterKeyUnavailable as exc:
        raise HTTPException(status_code=503, detail=master_key_recovery_message(exc)) from exc
    await db.commit()
    await db.refresh(endpoint)
    return to_dict(endpoint)


@router.delete("/{endpoint_id}", status_code=204)
async def remove(endpoint_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an endpoint. Agents still pointing at one of its models keep the
    stored id and report the endpoint as missing until they are repointed."""
    endpoint = await _require(db, endpoint_id)
    await delete_endpoint(db, endpoint)
    await db.commit()


@router.post("/{endpoint_id}/test")
async def test(endpoint_id: str, db: AsyncSession = Depends(get_db)):
    """Probe a saved endpoint and record the outcome for its status badge."""
    endpoint = await _require(db, endpoint_id)
    ok, message, served = await probe(endpoint.base_url, decrypt_value(endpoint.api_key))
    # probe() already scrubs its messages; scrubbing again here means a
    # future message source cannot reintroduce the key into this response.
    message = redact_text(message)
    if ok and endpoint.id == DESKTOP_DEBATE_ENDPOINT_ID:
        endpoint.models = _merge_desktop_qwen_models(endpoint.models, served)
    await record_probe(db, endpoint, ok, message)
    await db.commit()
    await db.refresh(endpoint)
    return {"ok": ok, "message": message, "served_models": served, "endpoint": to_dict(endpoint)}


@router.post("/probe")
async def probe_unsaved(body: ProbeIn):
    """Check a base URL before it is saved, and list what it serves.

    This is what lets the add form fill in the model list from the server
    instead of asking the user to type wire names by hand.
    """
    ok, message, served = await probe(body.base_url, body.api_key.strip())
    return {
        "ok": ok,
        "message": redact_text(message),
        "served_models": served,
        "on_prem": is_on_prem(body.base_url),
    }
