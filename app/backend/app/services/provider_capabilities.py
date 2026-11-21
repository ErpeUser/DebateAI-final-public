"""Shared, conservative capability and failure contracts for optional providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal

import httpx
from app.services.adapter_contracts import AdapterContract, validate_adapter_contract

CostStatus = Literal["local", "subscription", "usage_billed", "unknown"]
FailureKind = Literal[
    "authentication",
    "subscription",
    "model",
    "rate_limit",
    "timeout",
    "transport",
    "request",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    adapter_id: str
    configured_model: str
    wire_model: str
    requested_reasoning_effort: str | None
    confirmed_reasoning_efforts: tuple[str, ...]
    streaming: bool
    structured_output: bool
    cancellation: bool
    context_limit_tokens: int | None
    cost_status: CostStatus
    lazy_start: bool
    contract: AdapterContract

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["confirmed_reasoning_efforts"] = list(self.confirmed_reasoning_efforts)
        value["contract"] = self.contract.payload()
        return value


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    kind: FailureKind
    retryable: bool
    retry_after_seconds: int | None = None


def _wire_model(model_id: str) -> str:
    return model_id.rsplit(":", 1)[-1]


def capabilities_for_route(route: dict[str, Any]) -> ProviderCapabilities:
    """Describe only behavior implemented by the selected adapter.

    Unknown context limits deliberately remain ``None`` instead of guessing a
    provider alias or advertising a limit that the adapter has not confirmed.
    """
    adapter = str(route.get("id") or route.get("provider") or "unknown")
    provider = str(route.get("provider") or "").casefold()
    model = str(route.get("model_id") or "").strip()
    requested = str(route.get("reasoning_effort") or "").casefold() or None
    lazy = bool(route.get("lazy_start", False))

    if adapter == "gemini_cli" or provider == "google-login":
        efforts, streaming, structured, cost = ("high",), True, True, "subscription"
    elif adapter == "cliproxyapi":
        efforts, streaming, structured, cost = (
            ("high", "xhigh"),
            True,
            True,
            "subscription",
        )
    elif provider == "google-web":
        efforts, streaming, structured, cost = ("high",), False, True, "subscription"
    elif provider == "openai-web":
        efforts, streaming, structured, cost = (), False, False, "subscription"
    elif provider in {"google", "openai"}:
        efforts, streaming, structured, cost = ("high",), True, True, "usage_billed"
    elif provider in {"local", "openai-compatible"}:
        efforts, streaming, structured, cost = (), True, True, "local"
    else:
        efforts, streaming, structured, cost = (), False, False, "unknown"

    permissions = ["network"]
    if cost == "subscription":
        permissions.append("account_session")
    if adapter == "gemini_cli":
        permissions.append("subprocess")
    try:
        timeout_seconds = max(1.0, float(route.get("timeout_seconds") or 120.0))
    except (TypeError, ValueError):
        timeout_seconds = 120.0
    contract = validate_adapter_contract(
        AdapterContract(
            adapter_id=f"provider.{adapter}",
            kind="provider",
            contract_version="1.0",
            capabilities=tuple(
                capability
                for capability, enabled in (
                    ("generate", True),
                    ("stream", streaming),
                    ("structured_output", structured),
                    ("cancel", True),
                )
                if enabled
            ),
            permissions=tuple(permissions),  # type: ignore[arg-type]
            timeout_seconds=timeout_seconds,
            lifecycle="process" if lazy else "request",
        ),
        expected_kind="provider",
    )

    return ProviderCapabilities(
        adapter_id=adapter,
        configured_model=model,
        wire_model=_wire_model(model),
        requested_reasoning_effort=requested,
        confirmed_reasoning_efforts=efforts,
        streaming=streaming,
        structured_output=structured,
        cancellation=True,
        context_limit_tokens=None,
        cost_status=cost,  # type: ignore[arg-type]
        lazy_start=lazy,
        contract=contract,
    )


def provider_capability_payload(configuration: dict[str, Any]) -> list[dict[str, Any]]:
    routes = configuration.get("routes")
    if not isinstance(routes, list):
        return []
    return [
        capabilities_for_route(route).payload()
        for route in routes
        if isinstance(route, dict)
    ]


def effective_reasoning_effort(
    route: dict[str, Any],
    requested: str | None,
    *,
    complex_request: bool,
    remaining_seconds: float,
) -> str | None:
    capabilities = capabilities_for_route(route)
    supported = capabilities.confirmed_reasoning_efforts
    if not supported:
        return None
    desired = (
        requested or capabilities.requested_reasoning_effort or "high"
    ).casefold()
    if desired == "xhigh" and (not complex_request or remaining_seconds < 60):
        desired = "high"
    if desired in supported:
        return desired
    return "high" if "high" in supported else supported[-1]


def _retry_after(response: httpx.Response | None) -> int | None:
    if response is None:
        return None
    value = response.headers.get("Retry-After", "").strip()
    if not value:
        return None
    try:
        return max(0, min(86400, int(float(value))))
    except ValueError:
        try:
            base = response.headers.get("Date", "").strip()
            now = parsedate_to_datetime(base) if base else datetime.now(UTC)
            seconds = int((parsedate_to_datetime(value) - now).total_seconds())
            return max(0, min(86400, seconds))
        except (TypeError, ValueError, OverflowError):
            return None


def classify_provider_failure(exc: Exception) -> ProviderFailure:
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return ProviderFailure("timeout", True)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        text = (exc.response.text or str(exc)).casefold()
        if status in {401, 403}:
            kind: FailureKind = (
                "subscription"
                if any(term in text for term in ("subscription", "usage_limit", "plan"))
                else "authentication"
            )
            return ProviderFailure(kind, False)
        if status == 404 or any(
            term in text
            for term in (
                "model_not_found",
                "model not found",
                "invalid model",
                "does not exist",
            )
        ):
            return ProviderFailure("model", False)
        if status == 429:
            return ProviderFailure("rate_limit", True, _retry_after(exc.response))
        if status >= 500:
            return ProviderFailure("transport", True)
        return ProviderFailure("request", False)
    if isinstance(exc, httpx.TransportError):
        return ProviderFailure("transport", True)
    text = str(exc).casefold()
    if any(
        term in text
        for term in ("not logged", "not angemeldet", "oauth", "authentication")
    ):
        return ProviderFailure("authentication", False)
    if any(
        term in text for term in ("subscription", "usage_limit", "abo", "plan limit")
    ):
        return ProviderFailure("subscription", False)
    if any(
        term in text
        for term in (
            "model not found",
            "model_not_found",
            "invalid model",
            "does not exist",
        )
    ):
        return ProviderFailure("model", False)
    if any(
        term in text for term in ("429", "rate limit", "resource_exhausted", "quota")
    ):
        return ProviderFailure("rate_limit", True)
    return ProviderFailure("unknown", False)
