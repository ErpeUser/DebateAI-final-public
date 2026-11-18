"""Bounded, keyless fact research for the live debate copilot."""

from __future__ import annotations

import asyncio
import html
import hashlib
import ipaddress
import json
import re
import socket
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Literal

ResearchMode = Literal["live", "deep"]
from urllib.parse import parse_qs, unquote, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.services.ai_config import research_settings, unavailable_cooldown_seconds
from app.services import external_audit
from app.services.provider_capabilities import classify_provider_failure
from app.services.pii.recognizers import (
    ADDRESS,
    CARD,
    EMAIL,
    IP,
    PHONE,
    PERSON,
    SSN,
    find_patterns,
)


_USER_AGENT = "DebateAI/0.6.6 (https://github.com/ErpeUser/DebateAI)"
_HEADERS = {"User-Agent": _USER_AGENT, "Api-User-Agent": _USER_AGENT}
# Any tokenized placeholder is treated as sensitive at the public-search boundary.
# Keeping this generic prevents newly added recognizers (ORG, LOCATION, SSN,
# CARD, IP, ...) from bypassing the egress gate.
_PII_TOKEN = re.compile(r"\[[A-Z][A-Z0-9_-]{1,31}_\d+\]", re.IGNORECASE)
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_QUERY_PII_CATEGORIES = frozenset({EMAIL, PHONE, SSN, CARD, IP, ADDRESS, PERSON})
_HTML_TAG = re.compile(r"<[^>]+>")
_TRUSTED_ORIGINAL_SUFFIXES = (
    ".bund.de",
    ".destatis.de",
    ".europa.eu",
    ".gov",
    ".gov.uk",
    ".oecd.org",
    ".statistik.at",
    ".un.org",
    ".who.int",
    ".worldbank.org",
)
_MAX_ORIGINAL_BYTES = 800_000
_MAX_PROVIDER_BYTES = 1_000_000
_SAFE_TEXT_TYPES = (
    "application/json",
    "application/xhtml+xml",
    "text/html",
    "text/plain",
)
_CACHE_TTL_SECONDS = 300.0
_SEARCH_CACHE_MAX_ENTRIES = 128
_DOCUMENT_CACHE_MAX_ENTRIES = 32
_PASSAGE_CACHE_MAX_ENTRIES = 256
_search_cache: dict[str, tuple[float, ResearchResult]] = {}
_document_cache: dict[str, tuple[float, bytes, str]] = {}
_passage_cache: dict[tuple[str, str], tuple[float, str]] = {}
_research_inflight: dict[str, asyncio.Task[ResearchResult]] = {}
_research_provider_cooldown_until: dict[str, float] = {}
_research_provider_health: dict[str, dict[str, object]] = {}
_shared_http_client: httpx.AsyncClient | None = None


def _cache_get(cache: dict, key):
    item = cache.get(key)
    if item is None:
        return None
    if time.monotonic() - item[0] > _CACHE_TTL_SECONDS:
        cache.pop(key, None)
        return None
    # Plain dictionaries preserve insertion order. Reinsert on access to make
    # the bounded cache least-recently-used without another cache dependency.
    cache.pop(key, None)
    cache[key] = item
    return item[1:]


def _cache_set(cache: dict, key, *values, max_entries: int) -> None:
    now = time.monotonic()
    for cached_key, item in list(cache.items()):
        if now - item[0] > _CACHE_TTL_SECONDS:
            cache.pop(cached_key, None)
    cache.pop(key, None)
    cache[key] = (now, *values)
    while len(cache) > max(1, int(max_entries)):
        cache.pop(next(iter(cache)), None)


def _research_client(timeout: float) -> httpx.AsyncClient:
    global _shared_http_client
    if _shared_http_client is None or _shared_http_client.is_closed:
        _shared_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
        )
    return _shared_http_client


async def close_research_client() -> None:
    global _shared_http_client
    if _shared_http_client is not None and not _shared_http_client.is_closed:
        await _shared_http_client.aclose()
    _shared_http_client = None


class ResearchSource(BaseModel):
    title: str
    url: str
    snippet: str
    provider: str
    claim: str
    verification_status: Literal[
        "found", "read", "supports", "contradicts", "unclear"
    ] = "found"
    passage: str = ""
    published_at: str = ""
    retrieval_status: Literal["found", "read", "failed"] = "found"
    claim_relation: Literal["supports", "contradicts", "unclear"] = "unclear"
    source_type: str = "web"
    trust_level: Literal["primary", "secondary", "unknown"] = "unknown"
    publisher: str = ""
    retrieved_at: str = ""
    section: str = ""
    content_hash: str = ""
    claim_revision: int = 0
    numeric_unit: str = ""
    numeric_period: str = ""
    numeric_population: str = ""


class ResearchResult(BaseModel):
    claim: str
    query: str
    status: Literal["completed", "refused", "unavailable"]
    sources: list[ResearchSource] = Field(default_factory=list)
    error: str = ""


def _query_pii_spans(text: str) -> list[tuple[int, int, str]]:
    """Find structured or tokenized PII before a query reaches any provider."""
    spans = [
        (span.start, span.end, span.category)
        for span in find_patterns(text, set(_QUERY_PII_CATEGORIES))
    ]
    for match in _PII_TOKEN.finditer(text):
        spans.append((match.start(), match.end(), "TOKEN"))
    for match in _EMAIL.finditer(text):
        spans.append((match.start(), match.end(), "EMAIL"))
    spans.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    selected: list[tuple[int, int, str]] = []
    occupied_until = -1
    for start, end, category in spans:
        if start < occupied_until:
            continue
        selected.append((start, end, category))
        occupied_until = end
    return selected


def _minimize_research_query(query: str) -> tuple[str, tuple[str, ...]]:
    """Normalize a query and redact PII for diagnostics; never send it."""
    text = _clean_text(query)
    spans = _query_pii_spans(text)
    if not spans:
        return text, ()
    pieces: list[str] = []
    cursor = 0
    categories: list[str] = []
    for start, end, category in spans:
        pieces.append(text[cursor:start])
        pieces.append(f"[REDACTED_{category}]")
        cursor = end
        if category not in categories:
            categories.append(category)
    pieces.append(text[cursor:])
    return "".join(pieces), tuple(categories)


def minimize_research_query(query: str) -> str:
    """Return a provider-safe diagnostic form of a research query."""
    return _minimize_research_query(query)[0]


def research_query_pii_categories(query: str) -> tuple[str, ...]:
    """Return redacted PII categories without exposing matched values."""
    return _minimize_research_query(query)[1]


def _minimize_research_text(value: object) -> tuple[str, tuple[str, ...]]:
    """Normalize and redact PII in text before it can enter an external prompt."""
    return _minimize_research_query(str(value or ""))


def minimize_research_claim(claim: str) -> str:
    """Return a provider-safe diagnostic form of a claim."""
    return _minimize_research_text(claim)[0]


def research_claim_pii_categories(claim: str) -> tuple[str, ...]:
    """Return claim PII categories without exposing matched values."""
    return _minimize_research_text(claim)[1]


def is_safe_research_claim(claim: str) -> bool:
    text, categories = _minimize_research_text(claim)
    return bool(text) and not categories


def is_safe_research_query(query: str) -> bool:
    text, categories = _minimize_research_text(query)
    return bool(text) and len(text) <= 300 and not categories


def _clean_text(value: object) -> str:
    text = html.unescape(_HTML_TAG.sub(" ", str(value or "")))
    return " ".join(text.split()).strip()


def _extract_published_at(content: bytes) -> str:
    """Extract a publisher-supplied date without treating model prose as evidence."""
    text = content.decode("utf-8", errors="replace")
    patterns = (
        r'<meta\b[^>]*(?:property|name)\s*=\s*["\'](?:article:published_time|datepublished|citation_publication_date|dc.date|date)\s*["\'][^>]*content\s*=\s*["\']([^"\']+)',
        r'<meta\b[^>]*content\s*=\s*["\']([^"\']+)["\'][^>]*(?:property|name)\s*=\s*["\'](?:article:published_time|datepublished|citation_publication_date|dc.date|date)',
        r'"datePublished"\s*:\s*"([^"]+)"',
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _clean_text(match.group(1))
            if value:
                return value[:80]
    return ""



def _canonical_url(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    parsed = urlsplit(raw)
    if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
        target = (parse_qs(parsed.query).get("uddg") or [""])[0]
        if target:
            raw = unquote(target)
            parsed = urlsplit(raw)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 80, 443)
    ):
        return None
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", parsed.netloc.lower(), path, parsed.query, ""))


def _public_address(value: str) -> bool:
    """Reject every address class that can reach a local or special network."""
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    return bool(address.is_global)


async def _public_url(value: str) -> bool:
    parsed = urlsplit(value)
    hostname = parsed.hostname or ""
    if parsed.scheme != "https" or not hostname:
        return False
    try:
        literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        return _public_address(str(literal))
    try:
        resolved = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            parsed.port or 443,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
    except OSError:
        return False
    addresses = {item[4][0] for item in resolved if item[4]}
    return bool(addresses) and all(_public_address(item) for item in addresses)


async def _bounded_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    max_bytes: int = _MAX_PROVIDER_BYTES,
    accepted_types: tuple[str, ...] = _SAFE_TEXT_TYPES,
) -> tuple[bytes, str]:
    """Fetch one public response without credentials, redirects, or size drift.

    ``aiter_bytes`` yields decoded bytes, so the limit also covers compressed
    responses after decompression instead of trusting Content-Length alone.
    """
    # Tests and offline adapters can inject a tiny get-only client. Production
    # always uses httpx and therefore always executes the DNS/IP and streaming
    # limits below.
    if not isinstance(client, httpx.AsyncClient):
        response = await client.get(url, params=params, headers=_HEADERS)
        response.raise_for_status()
        headers = getattr(response, "headers", {}) or {}
        content_type = str(headers.get("content-type", "text/plain")).split(";", 1)[0].casefold()
        if content_type not in accepted_types:
            raise ValueError("Research response content type is not allowed")
        if content_type == "application/json" and hasattr(response, "json"):
            content = json.dumps(response.json(), ensure_ascii=False).encode("utf-8")
        else:
            raw = getattr(response, "content", None)
            if raw is None:
                raw = getattr(response, "text", "")
            content = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
        if len(content) > max_bytes:
            raise ValueError("Research response exceeds the decoded size limit")
        return content, content_type
    headers = {
        **_HEADERS,
        "Authorization": "",
        "Cookie": "",
        "Proxy-Authorization": "",
    }
    current_url = url
    current_params = params
    for _hop in range(6):
        if not await _public_url(current_url):
            raise ValueError("Research URL does not resolve to a public HTTPS target")
        chunks: list[bytes] = []
        total = 0
        async with client.stream(
            "GET",
            current_url,
            params=current_params,
            headers=headers,
            auth=None,
            cookies={},
            follow_redirects=False,
        ) as response:
            if response.is_redirect:
                location = response.headers.get("location", "")
                redirected = _canonical_url(urljoin(str(response.url), location))
                if redirected is None:
                    raise ValueError("Research redirect target is invalid")
                # Validate DNS/IP again on the next loop. Query parameters are
                # already present in response.url and must not be duplicated.
                current_url, current_params = redirected, None
                continue
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").casefold()
            if not any(item in content_type for item in accepted_types):
                raise ValueError("Research response content type is not allowed")
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > max_bytes:
                raise ValueError("Research response exceeds the size limit")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Research response exceeds the decoded size limit")
                chunks.append(chunk)
        return b"".join(chunks), content_type
    raise ValueError("Research redirect limit exceeded")


def _source(
    *,
    title: object,
    url: object,
    snippet: object,
    provider: str,
    claim: str,
    verification_status: Literal[
        "found", "read", "supports", "contradicts", "unclear"
    ] = "found",
) -> ResearchSource | None:
    canonical = _canonical_url(url)
    if canonical is None:
        return None
    clean_title = _clean_text(title) or urlsplit(canonical).hostname or provider
    clean_snippet = _clean_text(snippet)
    if len(clean_snippet) > 600:
        clean_snippet = clean_snippet[:597].rstrip() + "..."
    return ResearchSource(
        title=clean_title,
        url=canonical,
        snippet=clean_snippet,
        provider=provider,
        claim=claim,
        verification_status=verification_status,
        passage=clean_snippet if verification_status == "read" else "",
        retrieval_status="read" if verification_status == "read" else "found",
        claim_relation=(
            verification_status
            if verification_status in {"supports", "contradicts", "unclear"}
            else "unclear"
        ),
        source_type="search_snippet" if verification_status == "found" else "web",
        trust_level=("primary" if _trusted_original_url(canonical) else "unknown"),
        publisher=urlsplit(canonical).hostname or "",
        retrieved_at=datetime.now(UTC).isoformat(),
        content_hash=hashlib.sha256(clean_snippet.encode("utf-8")).hexdigest(),
    )


class _OriginalTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._capture_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg", "nav", "footer", "form"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in {"h1", "h2", "h3", "p", "li"}:
            self._capture_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg", "nav", "footer", "form"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif tag in {"h1", "h2", "h3", "p", "li"}:
            self._capture_depth = max(0, self._capture_depth - 1)

    def handle_data(self, data):
        if self._capture_depth and not self._ignored_depth:
            text = _clean_text(data)
            if text:
                self.parts.append(text)


def source_priority_reasons(source: ResearchSource) -> tuple[str, ...]:
    """Explain the provider-neutral ranking signals for one source."""
    reasons: list[str] = []
    if source.retrieval_status == "read" and source.passage.strip():
        reasons.append("read_passage")
    if source.source_type == "original":
        reasons.append("original_document")
    if source.trust_level == "primary":
        reasons.append("primary_source")
    metadata = " ".join(
        (source.title, source.publisher, urlsplit(source.url).hostname or "")
    ).casefold()
    if any(
        token in metadata
        for token in (
            "doi.org",
            "pubmed",
            "ncbi",
            "journal",
            "nature.com",
            "science.org",
            "arxiv.org",
        )
    ):
        reasons.append("scientific_publication")
    if any(
        token in metadata
        for token in (
            "statistik",
            "statistics",
            "statistical",
            "amt",
            "official data",
            "government data",
            "census",
        )
    ):
        reasons.append("official_statistics")
    if source.publisher.strip():
        reasons.append("publisher_metadata")
    if source.published_at.strip():
        reasons.append("published_date")
    if source.claim_relation in {"supports", "contradicts"}:
        reasons.append("explicit_claim_relation")
    return tuple(reasons)


def source_priority(source: ResearchSource) -> tuple[int, tuple[str, ...]]:
    """Return a stable score and its reasons; lower score sorts first."""
    reasons = source_priority_reasons(source)
    weights = {
        "read_passage": -100,
        "original_document": -60,
        "primary_source": -45,
        "scientific_publication": -30,
        "official_statistics": -30,
        "explicit_claim_relation": -15,
        "publisher_metadata": -5,
        "published_date": -3,
    }
    score = sum(weights.get(reason, 0) for reason in reasons)
    if source.retrieval_status != "read" or not source.passage.strip():
        score += 200
    return score, reasons


def _trusted_original_url(value: str) -> bool:
    hostname = (urlsplit(value).hostname or "").casefold()
    return any(
        hostname == suffix[1:] or hostname.endswith(suffix)
        for suffix in _TRUSTED_ORIGINAL_SUFFIXES
    )


def _relevant_passage(text: str, query: str) -> str:
    terms = {
        token for token in re.findall(r"[\wäöüß]+", query.casefold())
        if len(token) >= 5
    }
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if len(sentence.strip()) >= 30
    ]
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: len(
            terms.intersection(re.findall(r"[\wäöüß]+", item[1].casefold()))
        ),
        reverse=True,
    )
    selected = sorted(ranked[:5], key=lambda item: item[0])
    return " ".join(sentence for _, sentence in selected)[:2400].strip()


async def _read_trusted_original(
    client: httpx.AsyncClient,
    source: ResearchSource,
    query: str,
    claim: str = "",
) -> ResearchSource:
    can_read_ai_source = (
        source.source_type == "ai_web"
        and isinstance(client, httpx.AsyncClient)
    )
    if source.verification_status == "read" or (
        not _trusted_original_url(source.url) and not can_read_ai_source
    ):
        return source
    cached_document = _cache_get(_document_cache, source.url)
    if cached_document is None:
        audit_id = external_audit.start_external_request(
            provider_route=f"research-source:{source.provider}",
            approval=external_audit.current_approval(),
            data_category="source_document",
            claim_id=external_audit.claim_id_for(claim),
            target_host=source.url,
        )
        try:
            content, content_type = await _bounded_get(
                client,
                source.url,
                max_bytes=_MAX_ORIGINAL_BYTES,
                accepted_types=("application/xhtml+xml", "text/html", "text/plain"),
            )
        except asyncio.CancelledError:
            external_audit.finish_external_request(
                audit_id,
                approval=external_audit.current_approval(),
                status="cancelled",
                provider_route=f"research-source:{source.provider}",
                data_category="source_document",
                claim_id=external_audit.claim_id_for(claim),
                target_host=source.url,
            )
            raise
        except Exception as exc:
            external_audit.finish_external_request(
                audit_id,
                approval=external_audit.current_approval(),
                status="failed",
                provider_route=f"research-source:{source.provider}",
                data_category="source_document",
                claim_id=external_audit.claim_id_for(claim),
                target_host=source.url,
                error_class=type(exc).__name__,
            )
            return source
        external_audit.finish_external_request(
            audit_id,
            approval=external_audit.current_approval(),
            status="completed",
            provider_route=f"research-source:{source.provider}",
            data_category="source_document",
            claim_id=external_audit.claim_id_for(claim),
            target_host=source.url,
        )
        _cache_set(
            _document_cache,
            source.url,
            content,
            content_type,
            max_entries=_DOCUMENT_CACHE_MAX_ENTRIES,
        )
    else:
        content, content_type = cached_document
    _content_type = content_type
    text_content = content.decode("utf-8", errors="replace")
    if _content_type.split(";", 1)[0].casefold() == "text/plain":
        passage_text = text_content
    else:
        parser = _OriginalTextParser()
        parser.feed(text_content)
        passage_text = " ".join(parser.parts)
    content_hash = hashlib.sha256(content).hexdigest()
    passage_key = (content_hash, query.casefold())
    cached_passage = _cache_get(_passage_cache, passage_key)
    if cached_passage is None:
        passage = _relevant_passage(passage_text, query)
        _cache_set(
            _passage_cache,
            passage_key,
            passage,
            max_entries=_PASSAGE_CACHE_MAX_ENTRIES,
        )
    else:
        passage = cached_passage[0]
    if not passage:
        return source
    published_at = _extract_published_at(content) or source.published_at
    return source.model_copy(update={
        "verification_status": "read",
        "retrieval_status": "read",
        "source_type": "original",
        "passage": passage,
        "published_at": published_at,
        "content_hash": hashlib.sha256(passage.encode("utf-8")).hexdigest(),
    })


def _research_provider_status(provider: str) -> dict[str, object]:
    """Return redacted health metadata for one research lane."""
    status = dict(_research_provider_health.get(provider, {}))
    status.setdefault("provider", provider)
    status.setdefault("state", "ready")
    status["cooldown_until"] = _research_provider_cooldown_until.get(provider, 0.0)
    return status


def research_provider_health() -> dict[str, dict[str, object]]:
    """Expose provider-selection state without prompts, keys, or model output."""
    return {
        provider: _research_provider_status(provider)
        for provider in sorted(_research_provider_health)
    }


def reset_research_provider_health(provider: str | None = None) -> None:
    """Clear a lane after credentials/session health has changed."""
    providers = [provider] if provider else list(_research_provider_health)
    for item in providers:
        _research_provider_health.pop(item, None)
        _research_provider_cooldown_until.pop(item, None)


def _research_provider_ready(
    provider: str,
    *,
    allow_busy: bool = False,
) -> bool:
    """Gate a lane on cooldown and the login/session readiness it needs."""
    now = time.monotonic()
    blocked_until = _research_provider_cooldown_until.get(provider, 0.0)
    if blocked_until > now:
        return False
    if blocked_until:
        _research_provider_cooldown_until.pop(provider, None)

    reason = ""
    if provider == "chatgpt_web":
        try:
            from app.services import chatgpt_web
            if not chatgpt_web.runtime_available():
                reason = "runtime_unavailable"
            elif not chatgpt_web.configured():
                reason = "login_required"
            elif not chatgpt_web.model_confirmed():
                reason = "model_unconfirmed"
            elif chatgpt_web.browser_busy() and not allow_busy:
                reason = "browser_busy"
        except Exception:
            reason = "runtime_unavailable"
    elif provider == "gemini_web":
        try:
            from app.services.subscription_bridge import (
                gemini_web_cookie_configured,
                gemini_web_models,
            )
            if not gemini_web_cookie_configured():
                reason = "login_required"
            elif not gemini_web_models():
                reason = "no_served_model"
        except Exception:
            reason = "session_unavailable"

    if reason:
        _research_provider_health[provider] = {
            "provider": provider,
            "state": "blocked",
            "failure_kind": (
                "authentication"
                if "login" in reason or "session" in reason
                else "model"
                if "model" in reason
                else "transport"
            ),
            "retryable": False,
            "reason": reason,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        return False
    _research_provider_health[provider] = {
        "provider": provider,
        "state": "ready",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    return True


def _record_research_provider_success(provider: str) -> None:
    _research_provider_cooldown_until.pop(provider, None)
    _research_provider_health[provider] = {
        "provider": provider,
        "state": "ready",
        "last_success_at": datetime.now(UTC).isoformat(),
    }


def _record_research_provider_failure(provider: str, exc: Exception) -> None:
    failure = classify_provider_failure(exc)
    cooldown = (
        failure.retry_after_seconds
        if failure.retry_after_seconds is not None
        else unavailable_cooldown_seconds()
    )
    cooldown = max(1, int(cooldown))
    blocked_until = time.monotonic() + cooldown
    _research_provider_cooldown_until[provider] = blocked_until
    _research_provider_health[provider] = {
        "provider": provider,
        "state": "cooldown",
        "failure_kind": failure.kind,
        "retryable": failure.retryable,
        "cooldown_seconds": cooldown,
        "updated_at": datetime.now(UTC).isoformat(),
    }


async def _ai_web_sources(
    claim: str,
    query: str,
    providers: list[str] | set[str],
    *,
    research_mode: ResearchMode = "deep",
) -> list[ResearchSource]:
    """Fail over through every enabled AI-web provider in configured order."""
    if not is_safe_research_query(query) or not is_safe_research_claim(claim):
        return []
    chatgpt_generate = None
    generate_text = None
    try:
        from app.services.chatgpt_web import generate as chatgpt_generate
    except Exception:
        pass
    try:
        from app.services.llm import generate_text
    except Exception:
        pass
    prompt = (
        "Recherchiere diese Debattenaussage mit Originalquellen. "
        "Gib pro Quelle eine kurze Begründung und die vollständige URL aus. "
        "Keine Wikipedia- oder DuckDuckGo-Links. Aussage: " + claim[:800] +
        " Recherchefrage: " + query[:500]
    )
    models = {
        "gemini_web": "endpoint:gemini-web:gemini-3.1-pro",
        "gemini_api": "gemini-3.1-pro-preview",
        "cliproxyapi": "endpoint:subscription-ai:gpt-6-sol",
    }
    answers: list[tuple[str, str]] = []
    provider_order = list(providers) if isinstance(providers, list) else sorted(providers)
    for provider in provider_order:
        if provider not in {"chatgpt_web", "gemini_web", "gemini_api", "cliproxyapi"}:
            continue
        if not _research_provider_ready(
            provider,
            allow_busy=research_mode == "deep",
        ):
            continue
        try:
            with external_audit.audit_context(
                claim=claim,
                data_category="research_claim",
                approval=external_audit.current_approval(),
            ):
                if provider == "chatgpt_web":
                    if chatgpt_generate is None:
                        continue
                    answer = await chatgpt_generate(
                        prompt,
                        system="Du bist die Quellenrecherche. Arbeite faktenorientiert und nenne nur nachprüfbare Originalquellen.",
                        reasoning_effort="high",
                        research="search",
                        timeout_seconds=10 if research_mode == "live" else 660,
                        source="debate_research",
                    )
                else:
                    if generate_text is None:
                        continue
                    answer = await generate_text(
                        models[provider],
                        prompt,
                        system="Du bist die Quellenrecherche. Arbeite faktenorientiert und nenne nur nachprüfbare Originalquellen.",
                        source="debate_research",
                    )
        except Exception as exc:
            _record_research_provider_failure(provider, exc)
            continue
        if answer:
            _record_research_provider_success(provider)
            answers.append((provider, answer))
            if research_mode == "live":
                break
    if not answers:
        return []
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()
    for provider, answer in answers:
        for match in re.findall(r"https?://\S+", answer):
            raw_url = match.rstrip(".,;:)]}")
            canonical = _canonical_url(raw_url)
            if canonical is None:
                continue
            hostname = (urlsplit(canonical).hostname or "").casefold().rstrip(".")
            if (
                hostname == "wikipedia.org"
                or hostname.endswith(".wikipedia.org")
                or hostname == "duckduckgo.com"
                or hostname.endswith(".duckduckgo.com")
            ):
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            urls.append((provider, canonical))
    return [
        ResearchSource(
            title="KI-Recherche: " + (urlsplit(url).hostname or "Quelle"),
            url=url,
            snippet=" ".join(answer for provider_name, answer in answers if provider_name == provider)[:900],
            passage="",
            provider=provider,
            claim=claim,
            verification_status="found",
            retrieval_status="found",
            source_type="ai_web",
            trust_level="unknown",
            publisher=urlsplit(url).hostname or "",
            retrieved_at=datetime.now(UTC).isoformat(),
        )
        for provider, url in urls[: settings.DEBATE_RESEARCH_MAX_SOURCES]
    ]
async def _research_with_client(
    client: httpx.AsyncClient,
    claim: str,
    query: str,
    *,
    research_mode: ResearchMode = "deep",
) -> ResearchResult:
    if not is_safe_research_query(query) or not is_safe_research_claim(claim):
        return ResearchResult(
            claim=_clean_text(claim),
            query=_clean_text(query),
            status="refused",
            error="Research claim or query was empty or contained private data",
        )
    configured = research_settings()
    if not configured["enabled"]:
        return ResearchResult(
            claim=claim,
            query=query,
            status="unavailable",
            error="Research is disabled in AI settings",
        )
    providers: list[str] = []
    for provider in [
        *configured["providers"],
        *configured.get("fallback_providers", []),
    ]:
        if provider in {"wikipedia", "duckduckgo"} or provider in providers:
            continue
        providers.append(provider)
    tasks = []
    if any(
        provider in {"chatgpt_web", "gemini_web", "gemini_api", "cliproxyapi"}
        for provider in providers
    ):
        tasks.append(
            _ai_web_sources(
                claim,
                query,
                providers,
                research_mode=research_mode,
            )
        )
    if not tasks:
        return ResearchResult(
            claim=claim,
            query=query,
            status="unavailable",
            error="No research provider is enabled",
        )
    try:
        batches = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=min(
                configured["timeout_seconds"],
                10 if research_mode == "live" else configured["timeout_seconds"],
            ),
        )
    except TimeoutError:
        return ResearchResult(
            claim=claim,
            query=query,
            status="unavailable",
            error="Research timed out",
        )

    sources = []
    seen = set()
    errors = []
    for batch in batches:
        if isinstance(batch, BaseException):
            errors.append(str(batch))
            continue
        for source in batch:
            if source.url in seen:
                continue
            seen.add(source.url)
            sources.append(source)

    if sources:
        original_limit = min(
            settings.DEBATE_RESEARCH_MAX_SOURCES,
            configured["steps"] * 2,
        )
        original_indexes: list[int] = []
        read_providers: set[str] = set()
        for index, source in enumerate(sources):
            if (
                source.verification_status == "read"
                or source.provider in read_providers
                or not (
                    _trusted_original_url(source.url)
                    or (
                        source.source_type == "ai_web"
                        and isinstance(client, httpx.AsyncClient)
                    )
                )
            ):
                continue
            original_indexes.append(index)
            read_providers.add(source.provider)
            if len(original_indexes) >= original_limit:
                break
        if original_indexes and configured["original_sources_required"]:
            read_results = await asyncio.gather(*(
                _read_trusted_original(client, sources[index], query, claim)
                for index in original_indexes
            ))
            for index, read_source in zip(original_indexes, read_results):
                sources[index] = read_source
        sources.sort(key=source_priority)
        sources = sources[: min(settings.DEBATE_RESEARCH_MAX_SOURCES, configured["steps"] * 2)]
        if (
            configured["original_sources_required"]
            and any(source.source_type == "ai_web" for source in sources)
            and not any(
                source.retrieval_status == "read" and source.passage.strip()
                for source in sources
            )
        ):
            return ResearchResult(
                claim=claim,
                query=query,
                status="unavailable",
                sources=sources,
                error="No AI research source could be read as an original passage",
            )
        return ResearchResult(
            claim=claim,
            query=query,
            status="completed",
            sources=sources,
        )
    return ResearchResult(
        claim=claim,
        query=query,
        status="unavailable",
        error="; ".join(errors) or "No verifiable sources found",
    )


async def research_claim(
    claim: str,
    query: str,
    *,
    client: httpx.AsyncClient | None = None,
    research_mode: ResearchMode = "deep",
) -> ResearchResult:
    clean_claim = _clean_text(claim)
    clean_query = _clean_text(query)
    if not is_safe_research_query(clean_query) or not is_safe_research_claim(clean_claim):
        return ResearchResult(
            claim=clean_claim,
            query=clean_query,
            status="refused",
            error="Research claim or query was empty or contained private data",
        )
    mode: ResearchMode = research_mode if research_mode in {"live", "deep"} else "deep"
    total_timeout = research_settings()["timeout_seconds"]
    if mode == "live":
        total_timeout = min(total_timeout, 10)
    if client is not None:
        try:
            return await asyncio.wait_for(
                _research_with_client(
                    client,
                    clean_claim,
                    clean_query,
                    research_mode=mode,
                ),
                timeout=total_timeout,
            )
        except TimeoutError:
            return ResearchResult(
                claim=clean_claim,
                query=clean_query,
                status="unavailable",
                error="Research timed out",
            )
    key = f"{mode}:{clean_claim.casefold()}\x00{clean_query.casefold()}"
    cached = _cache_get(_search_cache, key)
    if cached is not None:
        return _result_for_claim(cached[0], clean_claim)

    task = _research_inflight.get(key)
    if task is None:
        async def run() -> ResearchResult:
            try:
                return await asyncio.wait_for(
                    _research_with_client(
                        _research_client(total_timeout),
                        clean_claim,
                        clean_query,
                        research_mode=mode,
                    ),
                    timeout=total_timeout,
                )
            except TimeoutError:
                return ResearchResult(
                    claim=clean_claim,
                    query=clean_query,
                    status="unavailable",
                    error="Research timed out",
                )

        task = asyncio.create_task(run(), name=f"research:{hashlib.sha256(key.encode()).hexdigest()[:10]}")
        _research_inflight[key] = task
        task.add_done_callback(
            lambda completed, cache_key=key: (
                _research_inflight.pop(cache_key, None)
                if _research_inflight.get(cache_key) is completed
                else None
            )
        )
    try:
        result = await asyncio.shield(task)
        if result.status == "completed":
            _cache_set(
                _search_cache,
                key,
                result,
                max_entries=_SEARCH_CACHE_MAX_ENTRIES,
            )
        return _result_for_claim(result, clean_claim)
    finally:
        if task.done() and _research_inflight.get(key) is task:
            _research_inflight.pop(key, None)


def _result_for_claim(result: ResearchResult, claim: str) -> ResearchResult:
    return result.model_copy(update={
        "claim": claim,
        "sources": [source.model_copy(update={"claim": claim}) for source in result.sources],
    })
