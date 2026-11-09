"""OAuth and capability checks for the desktop-owned subscription bridge.

The bridge keeps provider tokens in its own private auth directory.  The
backend receives only its loopback management address and a local bearer key;
neither OAuth codes nor provider tokens are returned to the frontend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

GEMINI_PROVIDER = "gemini-cli"
OPENAI_PROVIDER = "codex"
GEMINI_31_PRO_MODEL = "gemini-3.1-pro-preview"
SUPPORTED_PROVIDERS = {GEMINI_PROVIDER, OPENAI_PROVIDER}


def preferred_gemini_model(model_values: list[str]) -> str:
    """Pick only a Gemini model the bridge really advertises."""
    available = [
        str(model).strip()
        for model in model_values
        if str(model).strip().casefold().startswith("gemini-")
    ]
    if GEMINI_31_PRO_MODEL in available:
        return GEMINI_31_PRO_MODEL
    for marker in ("-high", "-pro"):
        match = next((model for model in available if marker in model.casefold()), "")
        if match:
            return match
    return available[0] if available else ""


class SubscriptionOAuthError(RuntimeError):
    """The local bridge rejected or could not complete an OAuth operation."""


@dataclass(frozen=True)
class BridgeConnection:
    root_url: str
    key: str

    @property
    def management_url(self) -> str:
        return f"{self.root_url}/v8/management"

    @property
    def inference_url(self) -> str:
        return f"{self.root_url}/v1"


def connection() -> BridgeConnection | None:
    raw_url = os.environ.get("BACKCHANNEL_SUBSCRIPTION_BRIDGE_URL", "").strip()
    key = os.environ.get("BACKCHANNEL_SUBSCRIPTION_BRIDGE_KEY", "").strip()
    if not raw_url or not key:
        return None
    parsed = urlparse(raw_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return None
    root_url = f"{parsed.scheme}://{parsed.netloc}"
    return BridgeConnection(root_url=root_url, key=key)


def available() -> bool:
    return connection() is not None


def _headers(value: BridgeConnection) -> dict[str, str]:
    return {"Authorization": f"Bearer {value.key}"}


def _provider(provider: str) -> str:
    value = str(provider or "").strip().casefold()
    if value not in SUPPORTED_PROVIDERS:
        raise SubscriptionOAuthError("Dieser Anmeldeanbieter wird nicht unterstuetzt.")
    return value


def _state(state: str) -> str:
    value = str(state or "").strip()
    if not 8 <= len(value) <= 512 or any(character.isspace() for character in value):
        raise SubscriptionOAuthError("Die lokale Anmeldesitzung ist ungueltig.")
    return value


async def models(*, timeout: float = 5.0) -> list[str]:
    value = connection()
    if value is None:
        return []
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{value.inference_url}/models", headers=_headers(value)
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return []
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return sorted(
        {
            str(item.get("id") or "").strip()
            for item in items
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
    )


async def start_login(provider: str) -> dict[str, str]:
    value = connection()
    if value is None:
        raise SubscriptionOAuthError("Die lokale OAuth-Bridge ist nicht verfuegbar.")
    selected = _provider(provider)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{value.management_url}/oauth/auth-url",
                headers=_headers(value),
                params={"provider": selected, "is_webui": "true"},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise SubscriptionOAuthError(
            "Die lokale OAuth-Anmeldung konnte nicht gestartet werden."
        ) from exc
    auth_url = str(payload.get("url") or "").strip() if isinstance(payload, dict) else ""
    state = str(payload.get("state") or "").strip() if isinstance(payload, dict) else ""
    status = str(payload.get("status") or "").strip() if isinstance(payload, dict) else ""
    parsed = urlparse(auth_url)
    if status != "ok" or parsed.scheme != "https" or not parsed.netloc:
        raise SubscriptionOAuthError("Die lokale OAuth-Bridge lieferte keine sichere Anmeldeadresse.")
    _state(state)
    return {"provider": selected, "auth_url": auth_url, "state": state}


async def login_status(state: str) -> dict[str, str]:
    value = connection()
    if value is None:
        raise SubscriptionOAuthError("Die lokale OAuth-Bridge ist nicht verfuegbar.")
    selected_state = _state(state)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{value.management_url}/oauth/status",
                headers=_headers(value),
                params={"state": selected_state},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise SubscriptionOAuthError("Der Anmeldestatus konnte nicht gelesen werden.") from exc
    status = str(payload.get("status") or "error").strip().casefold()
    if status not in {"wait", "ok", "error"}:
        status = "error"
    error = str(payload.get("error") or "").strip()
    return {"status": status, "error": error}


async def verify_gemini_31_pro_high() -> dict[str, str]:
    """Run one explicit user-requested minimal inference at Gemini High.

    This is never called during status reads or OAuth completion because it is
    a real external model request.  The UI labels the action accordingly.
    """
    return await verify_preferred_gemini_high()


async def verify_preferred_gemini_high() -> dict[str, str]:
    """Verify the best Gemini model actually present in the live catalog."""
    value = connection()
    if value is None:
        raise SubscriptionOAuthError("Die lokale OAuth-Bridge ist nicht verfuegbar.")
    selected_model = preferred_gemini_model(await models())
    if not selected_model:
        raise SubscriptionOAuthError(
            "Dieses Google-Konto stellt derzeit kein Gemini-Modell ueber die lokale Bridge bereit."
        )
    payload = {
        "model": selected_model,
        "messages": [{"role": "user", "content": "Antworte nur mit: OK"}],
        "reasoning_effort": "high",
        "max_tokens": 16,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{value.inference_url}/chat/completions",
                headers={**_headers(value), "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise SubscriptionOAuthError(
            f"{selected_model} konnte mit Denkstufe High nicht bestaetigt werden."
        ) from exc
    choices = result.get("choices") if isinstance(result, dict) else None
    if not isinstance(choices, list) or not choices:
        raise SubscriptionOAuthError(f"{selected_model} lieferte keine pruefbare Antwort.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = str(message.get("content") or "").strip() if isinstance(message, dict) else ""
    if not content:
        raise SubscriptionOAuthError(f"{selected_model} lieferte keine pruefbare Antwort.")
    return {
        "model": str(result.get("model") or selected_model),
        "thinking": "high",
        "answer": content[:80],
    }
