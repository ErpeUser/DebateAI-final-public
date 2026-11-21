"""Credential-free audit records for every outbound provider request.

The audit trail deliberately stores routing and outcome metadata only. Prompts,
responses, URLs with query strings, API keys, cookies, and exception messages
never enter this file. Claim identifiers are one-way digests so a reviewer can
join related requests without recovering the claim text.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import re
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.services.secrets import data_dir

_AUDIT_FILE_NAME = "external-requests.jsonl"
_RECORD_LOCK = threading.Lock()
_CATEGORIES = {
    "model_prompt",
    "research_claim",
    "transcript_excerpt",
    "source_document",
    "unknown",
}
_STATUSES = {"started", "completed", "failed", "blocked", "refused", "cancelled"}
_SAFE_IDENTIFIER = re.compile(r"[^A-Za-z0-9_.:@/-]+")

_claim_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "external_audit_claim_id", default=""
)
_data_category: contextvars.ContextVar[str] = contextvars.ContextVar(
    "external_audit_data_category", default="unknown"
)
_approval: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "external_audit_approval", default=True
)


def _audit_path() -> Path:
    return data_dir() / "audit" / _AUDIT_FILE_NAME


class _ClaimId(str):
    """A digest created here, distinguishable from arbitrary caller text."""


def claim_id_for(value: object) -> str:
    """Return a stable opaque claim id without retaining the claim text."""
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return _ClaimId(hashlib.sha256(text.encode("utf-8")).hexdigest()[:32])


def current_claim_id() -> str:
    return _claim_id.get()


def current_data_category() -> str:
    return _data_category.get()


def current_approval() -> bool:
    return _approval.get()


def data_category_for_source(source: object = "") -> str:
    """Map an internal caller label to a bounded audit data category."""
    value = str(source or "").casefold().replace("-", "_")
    if any(token in value for token in ("research", "recherche", "fact_check")):
        return "research_claim"
    if any(token in value for token in ("transcript", "video", "rhetoric", "debate")):
        return "transcript_excerpt"
    return "model_prompt"


@contextmanager
def audit_context(
    *,
    claim: object | None = None,
    data_category: str | None = None,
    approval: bool | None = None,
) -> Iterator[None]:
    """Attach non-content context to requests made in this async task."""
    claim_token = None
    category_token = None
    approval_token = None
    if claim is not None:
        claim_token = _claim_id.set(claim_id_for(claim))
    if data_category is not None:
        category_token = _data_category.set(
            data_category if data_category in _CATEGORIES else "unknown"
        )
    if approval is not None:
        approval_token = _approval.set(bool(approval))
    try:
        yield
    finally:
        if approval_token is not None:
            _approval.reset(approval_token)
        if category_token is not None:
            _data_category.reset(category_token)
        if claim_token is not None:
            _claim_id.reset(claim_token)


def _identifier(value: object, default: str) -> str:
    text = str(value or "").strip()
    text = _SAFE_IDENTIFIER.sub("-", text)[:160].strip("-")
    return text or default


def _host(value: object) -> str:
    """Accept only a host-like value; never persist a URL or its credentials."""
    text = str(value or "").strip().lower()
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    return _identifier(text.split(":", 1)[0], "unknown")


def _safe_claim_id(value: object | None) -> str:
    if isinstance(value, _ClaimId):
        return str(value)
    text = str(value or "").strip()
    if not text:
        return current_claim_id()
    # Plain strings remain untrusted, even when they look like a digest.
    # Internal callers preserve the marker returned by claim_id_for().
    return claim_id_for(text)


def _append(entry: dict[str, object]) -> None:
    """Best-effort append; an audit I/O failure never changes provider behavior."""
    try:
        path = _audit_path()
        with _RECORD_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.parent.chmod(0o700)
            if path.exists():
                path.chmod(0o600)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        # A provider outage must not be hidden by a read-only audit directory.
        return


def record_external_request(
    *,
    provider_route: str,
    approval: bool,
    data_category: str | None = None,
    status: str,
    claim_id: str | None = None,
    request_id: str | None = None,
    model_id: str | None = None,
    target_host: str | None = None,
    error_class: str | None = None,
) -> str:
    """Write one redacted request event and return its request id."""
    request_id = _identifier(request_id or uuid.uuid4().hex, uuid.uuid4().hex)
    category = data_category or current_data_category()
    category = category if category in _CATEGORIES else "unknown"
    status = status if status in _STATUSES else "failed"
    entry: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "provider_route": _identifier(provider_route, "unknown"),
        "approval": bool(approval),
        "data_category": category,
        "claim_id": _safe_claim_id(claim_id),
        "status": status,
    }
    if model_id:
        entry["model_id"] = _identifier(model_id, "unknown")
    if target_host:
        entry["target_host"] = _host(target_host)
    if error_class:
        entry["error_class"] = _identifier(error_class, "Error")
    _append(entry)
    return request_id


def start_external_request(
    *,
    provider_route: str,
    approval: bool,
    data_category: str | None = None,
    claim_id: str | None = None,
    model_id: str | None = None,
    target_host: str | None = None,
) -> str:
    return record_external_request(
        provider_route=provider_route,
        approval=approval,
        data_category=data_category,
        status="started",
        claim_id=claim_id,
        model_id=model_id,
        target_host=target_host,
    )


def finish_external_request(
    request_id: str,
    *,
    approval: bool,
    status: str,
    provider_route: str,
    data_category: str | None = None,
    claim_id: str | None = None,
    model_id: str | None = None,
    target_host: str | None = None,
    error_class: str | None = None,
) -> None:
    record_external_request(
        provider_route=provider_route,
        approval=approval,
        data_category=data_category,
        status=status,
        claim_id=claim_id,
        request_id=request_id,
        model_id=model_id,
        target_host=target_host,
        error_class=error_class,
    )
