"""Small, loopback-only client for the desktop-managed CLIProxyAPI process.

The desktop owns the process and OAuth files.  This module owns the backend
wire contract: strict loopback validation, lossless model metadata, explicit
reasoning/streaming parameters, and bounded rate-limit handling.  It never
retries a provider request; CLIProxyAPI may fail over between its configured
credentials, while DebateAI records only the affected provider/model pair.
"""

from __future__ import annotations

import ipaddress
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import AsyncIterator, Callable
from urllib.parse import urlparse

import httpx


class CLIProxyError(RuntimeError):
    """The local CLIProxyAPI endpoint returned an invalid or failed response."""


class CLIProxyRateLimited(CLIProxyError):
    """One provider/model route is cooling down after a 429 response."""

    def __init__(self, provider: str, model: str, retry_after: float):
        self.provider = provider
        self.model = model
        self.retry_after = max(0.0, retry_after)
        super().__init__(
            f"{provider}/{model} is rate limited; retry after "
            f"{self.retry_after:.0f} second(s)"
        )


@dataclass(frozen=True)
class CLIProxyConnection:
    root_url: str
    key: str

    @property
    def inference_url(self) -> str:
        return f"{self.root_url}/v1"

    @property
    def management_url(self) -> str:
        return f"{self.root_url}/v8/management"


def loopback_connection(raw_url: str, key: str) -> CLIProxyConnection | None:
    """Return a normalized connection only for an unambiguous loopback URL."""
    raw_url = str(raw_url or "").strip()
    key = str(key or "").strip()
    if not raw_url or not key:
        return None
    try:
        parsed = urlparse(raw_url)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "http"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") not in {"", "/v1"}
    ):
        return None
    host = (parsed.hostname or "").casefold()
    if host == "localhost":
        normalized_host = "localhost"
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return None
        if not address.is_loopback:
            return None
        normalized_host = f"[{address.compressed}]" if address.version == 6 else address.compressed
    authority = normalized_host + (f":{port}" if port is not None else "")
    return CLIProxyConnection(root_url=f"http://{authority}", key=key)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(dict.fromkeys(str(item).strip().casefold() for item in value if str(item).strip()))


def _positive_int(*values: object) -> int | None:
    for value in values:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return None


@dataclass(frozen=True)
class CLIProxyModel:
    id: str
    label: str
    provider: str
    model_type: str
    context_length: int | None
    max_output_tokens: int | None
    reasoning_levels: tuple[str, ...]
    parameters: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: object) -> "CLIProxyModel | None":
        if not isinstance(payload, dict):
            return None
        model_id = str(payload.get("id") or "").strip()
        if not model_id:
            return None
        capabilities = payload.get("capabilities")
        capabilities = capabilities if isinstance(capabilities, dict) else {}
        reasoning = capabilities.get("reasoning")
        reasoning = reasoning if isinstance(reasoning, dict) else {}
        thinking = payload.get("thinking")
        thinking = thinking if isinstance(thinking, dict) else {}
        providers = _strings(payload.get("providers"))
        provider = (
            providers[0]
            if providers
            else str(payload.get("owned_by") or payload.get("type") or "unknown").strip().casefold()
            or "unknown"
        )
        return cls(
            id=model_id,
            label=str(payload.get("display_name") or payload.get("name") or model_id).strip(),
            provider=provider,
            model_type=str(payload.get("type") or "").strip(),
            context_length=_positive_int(
                payload.get("context_length"),
                payload.get("max_context_length"),
                payload.get("inputTokenLimit"),
            ),
            max_output_tokens=_positive_int(
                payload.get("max_output_tokens"),
                payload.get("max_completion_tokens"),
                payload.get("outputTokenLimit"),
            ),
            reasoning_levels=_strings(reasoning.get("levels") or thinking.get("levels")),
            parameters=_strings(
                capabilities.get("parameters") or payload.get("supported_parameters")
            ),
        )

    def endpoint_entry(self) -> dict:
        result: dict = {"id": self.id, "label": self.label}
        if self.provider != "unknown":
            result["provider"] = self.provider
        if self.model_type:
            result["model_type"] = self.model_type
        if self.context_length is not None:
            result["context_length"] = self.context_length
        if self.max_output_tokens is not None:
            result["max_output_tokens"] = self.max_output_tokens
        if self.reasoning_levels:
            result["reasoning_levels"] = list(self.reasoning_levels)
        if self.parameters:
            result["parameters"] = list(self.parameters)
        return result


class CLIProxyClient:
    """One local proxy connection with a provider/model-scoped cooldown map."""

    def __init__(
        self,
        connection: CLIProxyConnection,
        *,
        timeout: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
        max_cooldown: float = 300.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.connection = connection
        self.timeout = timeout
        self._clock = clock
        self._max_cooldown = max(1.0, max_cooldown)
        self._transport = transport
        self._catalog: dict[str, CLIProxyModel] = {}
        self._cooldowns: dict[tuple[str, str], float] = {}

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.connection.key}"}

    async def models(self, *, timeout: float | None = None) -> list[CLIProxyModel]:
        try:
            async with httpx.AsyncClient(
                timeout=timeout or self.timeout, transport=self._transport
            ) as client:
                response = await client.get(
                    f"{self.connection.inference_url}/models", headers=self.headers
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise CLIProxyError("CLIProxyAPI model catalog is unavailable") from exc
        items = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise CLIProxyError("CLIProxyAPI returned an invalid model catalog")
        parsed = [model for item in items if (model := CLIProxyModel.from_payload(item))]
        self._catalog = {model.id: model for model in parsed}
        return sorted(parsed, key=lambda model: model.id.casefold())

    def _route(self, model: str) -> tuple[str, str]:
        metadata = self._catalog.get(model)
        return ((metadata.provider if metadata else "unknown"), model)

    def _check_cooldown(self, model: str) -> None:
        provider, wire_model = self._route(model)
        until = self._cooldowns.get((provider, wire_model), 0.0)
        remaining = until - self._clock()
        if remaining > 0:
            raise CLIProxyRateLimited(provider, wire_model, remaining)
        self._cooldowns.pop((provider, wire_model), None)

    def _retry_after(self, response: httpx.Response) -> float:
        raw = response.headers.get("Retry-After", "").strip()
        try:
            seconds = float(raw)
        except ValueError:
            try:
                target = parsedate_to_datetime(raw)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                seconds = (target - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                seconds = 30.0
        return min(self._max_cooldown, max(1.0, seconds))

    def _record_rate_limit(self, model: str, response: httpx.Response) -> CLIProxyRateLimited:
        provider, wire_model = self._route(model)
        delay = self._retry_after(response)
        self._cooldowns[(provider, wire_model)] = self._clock() + delay
        return CLIProxyRateLimited(provider, wire_model, delay)

    def chat_payload(
        self,
        model: str,
        messages: list[dict],
        *,
        reasoning_effort: str | None = None,
        stream: bool = False,
        **parameters: object,
    ) -> dict:
        metadata = self._catalog.get(model)
        effort = str(reasoning_effort or "").strip().casefold()
        if effort and metadata and metadata.reasoning_levels and effort not in metadata.reasoning_levels:
            raise CLIProxyError(
                f"{model} does not advertise reasoning effort '{effort}'"
            )
        payload = {"model": model, "messages": messages, "stream": bool(stream)}
        if effort:
            payload["reasoning_effort"] = effort
        payload.update(parameters)
        return payload

    async def complete(
        self,
        model: str,
        messages: list[dict],
        *,
        reasoning_effort: str | None = None,
        **parameters: object,
    ) -> dict:
        self._check_cooldown(model)
        payload = self.chat_payload(
            model, messages, reasoning_effort=reasoning_effort, stream=False, **parameters
        )
        async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
            response = await client.post(
                f"{self.connection.inference_url}/chat/completions",
                headers=self.headers,
                json=payload,
            )
        if response.status_code == 429:
            raise self._record_rate_limit(model, response)
        try:
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise CLIProxyError(
                f"CLIProxyAPI completion failed with HTTP {response.status_code}"
            ) from exc
        if not isinstance(result, dict):
            raise CLIProxyError("CLIProxyAPI returned an invalid completion")
        return result

    async def stream(
        self,
        model: str,
        messages: list[dict],
        *,
        reasoning_effort: str | None = None,
        **parameters: object,
    ) -> AsyncIterator[dict]:
        self._check_cooldown(model)
        payload = self.chat_payload(
            model, messages, reasoning_effort=reasoning_effort, stream=True, **parameters
        )
        async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
            async with client.stream(
                "POST",
                f"{self.connection.inference_url}/chat/completions",
                headers=self.headers,
                json=payload,
            ) as response:
                if response.status_code == 429:
                    await response.aread()
                    raise self._record_rate_limit(model, response)
                try:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        chunk = json.loads(raw)
                        if isinstance(chunk, dict):
                            yield chunk
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    raise CLIProxyError("CLIProxyAPI stream failed") from exc
