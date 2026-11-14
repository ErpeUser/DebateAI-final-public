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
from urllib.parse import parse_qs, unquote, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.services.ai_config import research_settings


WIKIPEDIA_API = "https://de.wikipedia.org/w/api.php"
DUCKDUCKGO_API = "https://api.duckduckgo.com/"
DUCKDUCKGO_HTML = "https://html.duckduckgo.com/html/"
_USER_AGENT = "DebateAI/0.6.6 (https://github.com/ErpeUser/DebateAI)"
_HEADERS = {"User-Agent": _USER_AGENT, "Api-User-Agent": _USER_AGENT}
# Any tokenized placeholder is treated as sensitive at the public-search boundary.
# Keeping this generic prevents newly added recognizers (ORG, LOCATION, SSN,
# CARD, IP, ...) from bypassing the egress gate.
_PII_TOKEN = re.compile(r"\[[A-Z][A-Z0-9_-]{1,31}_\d+\]", re.IGNORECASE)
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
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


def is_safe_research_query(query: str) -> bool:
    text = (query or "").strip()
    return bool(text) and len(text) <= 300 and not _PII_TOKEN.search(text) and not _EMAIL.search(text)


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
        if hasattr(response, "json"):
            content = json.dumps(response.json(), ensure_ascii=False).encode("utf-8")
            if len(content) > max_bytes:
                raise ValueError("Research response exceeds the decoded size limit")
            return content, "application/json"
        raise ValueError("Injected research client returned no readable body")
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


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture = ""
        self._parts: list[str] = []

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        value = next((value or "" for key, value in attrs if key == "class"), "")
        return set(value.split())

    def _finish(self) -> None:
        if self._current and self._current.get("url"):
            self.rows.append(self._current)
        self._current = None

    def handle_starttag(self, tag, attrs):
        classes = self._classes(attrs)
        if tag == "a" and "result__a" in classes:
            self._finish()
            href = next((value or "" for key, value in attrs if key == "href"), "")
            self._current = {"title": "", "url": href, "snippet": ""}
            self._capture = "title"
            self._parts = []
        elif self._current is not None and "result__snippet" in classes:
            self._capture = "snippet"
            self._parts = []

    def handle_data(self, data):
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if self._current is None or not self._capture:
            return
        if tag in {"a", "div", "span"}:
            self._current[self._capture] = _clean_text(" ".join(self._parts))
            self._capture = ""
            self._parts = []

    def close(self):
        super().close()
        self._finish()


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
        try:
            content, content_type = await _bounded_get(
                client,
                source.url,
                max_bytes=_MAX_ORIGINAL_BYTES,
                accepted_types=("application/xhtml+xml", "text/html", "text/plain"),
            )
        except Exception:
            return source
        _cache_set(
            _document_cache,
            source.url,
            content,
            content_type,
            max_entries=_DOCUMENT_CACHE_MAX_ENTRIES,
        )
    else:
        content, _content_type = cached_document
    parser = _OriginalTextParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    content_hash = hashlib.sha256(content).hexdigest()
    passage_key = (content_hash, query.casefold())
    cached_passage = _cache_get(_passage_cache, passage_key)
    if cached_passage is None:
        passage = _relevant_passage(" ".join(parser.parts), query)
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


def _parse_duckduckgo_html(value: str) -> list[dict[str, str]]:
    parser = _DuckDuckGoHTMLParser()
    parser.feed(value or "")
    parser.close()
    rows = []
    for row in parser.rows:
        canonical = _canonical_url(row.get("url"))
        if canonical:
            rows.append({**row, "url": canonical})
    return rows


async def _wikipedia_sources(
    client: httpx.AsyncClient,
    claim: str,
    query: str,
) -> list[ResearchSource]:
    raise RuntimeError("Legacy research provider disabled")
    content, _content_type = await _bounded_get(
        client,
        WIKIPEDIA_API,
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": settings.DEBATE_RESEARCH_MAX_SOURCES,
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "inprop": "url",
            "format": "json",
            "utf8": 1,
        },
    )
    pages = ((json.loads(content) or {}).get("query") or {}).get("pages") or {}
    sources = []
    for page in sorted(pages.values(), key=lambda item: item.get("index", 10_000)):
        item = _source(
            title=page.get("title"),
            url=page.get("fullurl"),
            snippet=page.get("extract"),
            provider="wikipedia",
            claim=claim,
            verification_status="read",
        )
        if item is not None:
            sources.append(item)
    return sources


def _related_topics(items: list[dict]) -> list[dict]:
    flattened = []
    for item in items:
        if isinstance(item.get("Topics"), list):
            flattened.extend(_related_topics(item["Topics"]))
        else:
            flattened.append(item)
    return flattened


async def _duckduckgo_sources(
    client: httpx.AsyncClient,
    claim: str,
    query: str,
) -> list[ResearchSource]:
    raise RuntimeError("Legacy research provider disabled")
    content, _content_type = await _bounded_get(
        client,
        DUCKDUCKGO_API,
        params={
            "q": query,
            "format": "json",
            "no_html": 1,
            "no_redirect": 1,
            "skip_disambig": 1,
        },
    )
    payload = json.loads(content) or {}
    candidates = [
        {
            "title": payload.get("Heading") or payload.get("AbstractSource"),
            "url": payload.get("AbstractURL"),
            "snippet": payload.get("AbstractText"),
        }
    ]
    candidates.extend(
        {
            "title": topic.get("Text", "").split(" - ", 1)[0],
            "url": topic.get("FirstURL"),
            "snippet": topic.get("Text"),
        }
        for topic in _related_topics(payload.get("RelatedTopics") or [])
    )
    sources = []
    for candidate in candidates:
        item = _source(
            **candidate,
            provider="duckduckgo",
            claim=claim,
        )
        if item is not None:
            sources.append(item)
    return sources


async def _ai_web_sources(
    claim: str,
    query: str,
    providers: set[str],
) -> list[ResearchSource]:
    """Ask an enabled AI web lane for source-backed findings.

    AI web output is treated as an untrusted source index: only explicit URLs
    are persisted as sources and the final answer still passes the normal
    source verification gates. Legacy search endpoints are never called.
    """
    chatgpt_generate = None
    try:
        from app.services.chatgpt_web import generate as chatgpt_generate
    except Exception:
        pass
    fallback_model = next(
        (
            model
            for provider, model in (
                ("gemini_web", "endpoint:gemini-web:gemini-3.1-pro"),
                ("gemini_api", "gemini-3.1-pro-preview"),
                ("cliproxyapi", "endpoint:subscription-ai:gpt-6-sol"),
            )
            if provider in providers
        ),
        "",
    )
    if chatgpt_generate is None and not fallback_model:
        return []
    prompt = (
        "Recherchiere diese Debattenaussage mit Originalquellen. "
        "Gib pro Quelle eine kurze Begründung und die vollständige URL aus. "
        "Keine Wikipedia- oder DuckDuckGo-Links. Aussage: " + claim[:800] +
        " Recherchefrage: " + query[:500]
    )
    try:
        if chatgpt_generate is not None and "chatgpt_web" in providers:
            answer = await chatgpt_generate(
                prompt,
                system="Du bist die Quellenrecherche. Arbeite faktenorientiert und nenne nur nachprüfbare Originalquellen.",
                reasoning_effort="high",
                research="search",
            )
        else:
            from app.services.llm import generate_text
            answer = await generate_text(
                fallback_model,
                prompt,
                system="Du bist die Quellenrecherche. Arbeite faktenorientiert und nenne nur nachprüfbare Originalquellen.",
                source="debate_research",
            )
    except Exception:
        return []
    provider_label = "chatgpt_web" if chatgpt_generate is not None and "chatgpt_web" in providers else next((provider for provider in ("gemini_web", "gemini_api", "cliproxyapi") if provider in providers), "ai_web")
    urls = []
    for match in re.findall(r"https?://\S+", answer or ""):
        raw_url = match.rstrip(".,;:)]}")
        canonical = _canonical_url(raw_url)
        if canonical is None:
            continue
        hostname = (urlsplit(canonical).hostname or "").casefold().rstrip(".")
        # Keep the legacy providers disabled even when an AI response returns
        # mixed-case, subdomain, or redirected-looking links.
        if (
            hostname == "wikipedia.org"
            or hostname.endswith(".wikipedia.org")
            or hostname == "duckduckgo.com"
            or hostname.endswith(".duckduckgo.com")
        ):
            continue
        if canonical not in urls:
            urls.append(canonical)
    snippet = " ".join((answer or "").split())[:900]
    return [
        ResearchSource(
            title="KI-Recherche: " + (urlsplit(url).hostname or "Quelle"),
            url=url,
            snippet=snippet,
            # The model's URL list is only a finding. Do not present its
            # surrounding prose as a read source passage until the URL was
            # fetched and parsed by the bounded source reader.
            passage="",
            provider=provider_label,
            claim=claim,
            verification_status="found",
            retrieval_status="found",
            source_type="ai_web",
            trust_level="unknown",
            publisher=urlsplit(url).hostname or "",
            retrieved_at=datetime.now(UTC).isoformat(),
        )
        for url in urls[: settings.DEBATE_RESEARCH_MAX_SOURCES]
    ]

async def _duckduckgo_html_sources(
    client: httpx.AsyncClient,
    claim: str,
    query: str,
) -> list[ResearchSource]:
    raise RuntimeError("Legacy research provider disabled")
    content, _content_type = await _bounded_get(
        client,
        DUCKDUCKGO_HTML,
        params={"q": query},
        accepted_types=("application/xhtml+xml", "text/html", "text/plain"),
    )
    sources = []
    for candidate in _parse_duckduckgo_html(content.decode("utf-8", errors="replace")):
        item = _source(
            **candidate,
            provider="duckduckgo-search",
            claim=claim,
        )
        if item is not None:
            sources.append(item)
        if len(sources) >= settings.DEBATE_RESEARCH_MAX_SOURCES:
            break
    return sources


async def _research_with_client(
    client: httpx.AsyncClient,
    claim: str,
    query: str,
) -> ResearchResult:
    configured = research_settings()
    if not configured["enabled"]:
        return ResearchResult(
            claim=claim,
            query=query,
            status="unavailable",
            error="Research is disabled in AI settings",
        )
    providers = {
        provider for provider in configured["providers"]
        if provider not in {"wikipedia", "duckduckgo"}
    }
    tasks = []
    if providers.intersection({"chatgpt_web", "gemini_web", "gemini_api", "cliproxyapi"}):
        tasks.append(_ai_web_sources(claim, query, providers))
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
            timeout=configured["timeout_seconds"],
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
        original_indexes = [
            index for index, source in enumerate(sources)
            if source.verification_status != "read"
            and (
                _trusted_original_url(source.url)
                or (
                    source.source_type == "ai_web"
                    and isinstance(client, httpx.AsyncClient)
                )
            )
        ][:2]
        if original_indexes and configured["original_sources_required"]:
            read_results = await asyncio.gather(*(
                _read_trusted_original(client, sources[index], query)
                for index in original_indexes
            ))
            for index, read_source in zip(original_indexes, read_results):
                sources[index] = read_source
        sources.sort(key=lambda source: (
            0 if source.verification_status == "read" and (
                _trusted_original_url(source.url) or source.source_type == "original"
            )
            else 1 if source.verification_status == "read"
            else 2 if _trusted_original_url(source.url) or source.source_type == "ai_web"
            else 3
        ))
        sources = sources[: min(settings.DEBATE_RESEARCH_MAX_SOURCES, configured["steps"] * 2)]
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
) -> ResearchResult:
    clean_claim = _clean_text(claim)
    clean_query = _clean_text(query)
    if not is_safe_research_query(clean_query):
        return ResearchResult(
            claim=clean_claim,
            query=clean_query,
            status="refused",
            error="Research query was empty or contained private data",
        )
    total_timeout = research_settings()["timeout_seconds"]
    if client is not None:
        try:
            return await asyncio.wait_for(
                _research_with_client(client, clean_claim, clean_query),
                timeout=total_timeout,
            )
        except TimeoutError:
            return ResearchResult(
                claim=clean_claim,
                query=clean_query,
                status="unavailable",
                error="Research timed out",
            )
    key = clean_query.casefold()
    cached = _cache_get(_search_cache, key)
    if cached is not None:
        return _result_for_claim(cached[0], clean_claim)

    task = _research_inflight.get(key)
    if task is None:
        async def run() -> ResearchResult:
            try:
                return await asyncio.wait_for(
                    _research_with_client(_research_client(total_timeout), clean_claim, clean_query),
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
