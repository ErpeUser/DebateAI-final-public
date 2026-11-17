"""Host and Origin guards for an API that has no user login.

DebateAI trusts whoever can reach it: the desktop build binds loopback and
the Docker stack sits behind the frontend proxy, so the API itself never asks
for credentials. Two browser tricks turn that trust into a problem for a
person who merely visits a hostile web page:

- DNS rebinding. The page's domain resolves to the attacker's server just long
  enough to load, then to 127.0.0.1. Later requests from that page hit the
  local API as a same-origin call, with the attacker's hostname in ``Host``.
- Cross-origin requests. A page on any origin can send requests to
  ``http://localhost:<port>``; the browser only withholds the *response* when
  CORS says so, and a form-shaped POST needs no preflight at all.

Both leave a fingerprint the server can check. The first carries a ``Host``
that is not one of ours; the second carries an ``Origin`` that is not one of
ours. This middleware rejects each before any router runs. Because the
allowed set must include every way a legitimate user reaches the app, the
rule is: loopback names and addresses, the Docker service
name, and anything listed in the environment:

- ``DEBATEAI_ALLOWED_HOSTS``: extra hostnames, comma-separated, for a
  Docker deployment reached by name (``debateai.lan``). ``*`` disables the
  Host check.
- ``DEBATEAI_ALLOWED_ORIGINS``: extra origins (``https://tools.example``)
  that may call the API cross-origin, also used for CORS. ``*`` disables the
  Origin check (CORS then still restricts itself to the loopback pattern).
"""

from __future__ import annotations

import ipaddress
import hmac
import logging
import os
import re
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.services.identity import env_value

logger = logging.getLogger(__name__)

ALLOWED_HOSTS_ENV = "DEBATEAI_ALLOWED_HOSTS"
ALLOWED_ORIGINS_ENV = "DEBATEAI_ALLOWED_ORIGINS"
# Names that only ever mean "this machine" (plus the Compose service name,
# which resolves nowhere outside the stack's own network).
LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1", "backend"})

# Origins CORS accepts without configuration. Everything a local frontend
# could be served from: the app's own port, the Vite dev server, a preview.
CORS_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\]|[A-Za-z0-9.-]+\.localhost)(:\d+)?$"
WS_TOKEN_PROTOCOL_PREFIX = "debateai.instance."
INSTANCE_COOKIE = "debateai_instance"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_DESKTOP_FRONTEND_FILES = frozenset({
    "/", "/calibration.html", "/favicon.ico", "/manifest.webmanifest",
})
_DESKTOP_FRONTEND_PREFIXES = ("/assets/", "/calibration/", "/icons/")


def _env_list(name: str) -> list[str]:
    raw = env_value(name)
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def _hostname_of(host_header: str) -> str:
    """Host header -> lowercase hostname without port; "" when unparseable."""
    try:
        return (urlsplit("//" + host_header.strip()).hostname or "").lower()
    except ValueError:
        return ""


def _desktop_frontend_path(path: str, method: str, host: str) -> bool:
    """Allow the local WebView to load its non-sensitive frontend assets."""
    if method not in {"GET", "HEAD"} or _hostname_of(host) not in LOOPBACK_NAMES:
        return False
    return path in _DESKTOP_FRONTEND_FILES or any(
        path.startswith(prefix) for prefix in _DESKTOP_FRONTEND_PREFIXES
    )


def _is_ip_literal(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def hostname_allowed(hostname: str, extra_hosts: list[str] | None = None) -> bool:
    extra = _env_list(ALLOWED_HOSTS_ENV) if extra_hosts is None else extra_hosts
    if "*" in extra:
        return env_value("DEBATEAI_ENV", "development").lower() != "production"
    name = (hostname or "").lower()
    if not name:
        return False
    if name in LOOPBACK_NAMES:
        return True
    if _is_ip_literal(name):
        try:
            address = ipaddress.ip_address(name)
            # Literal private/LAN addresses cannot be DNS-rebound. They are
            # legitimate frontend/desktop origins in a home or office network
            # and must receive the same treatment as loopback.
            return address.is_loopback or address.is_private or address.is_link_local
        except ValueError:
            return False
    return name in extra


def host_header_allowed(host_header: str, extra_hosts: list[str] | None = None) -> bool:
    return hostname_allowed(_hostname_of(host_header), extra_hosts)


def origin_allowed(
    origin: str,
    extra_hosts: list[str] | None = None,
    extra_origins: list[str] | None = None,
) -> bool:
    """Whether a browser Origin may issue state-changing requests.

    An origin is fine when its host is one of ours (same rule as Host) or it
    is listed verbatim in the environment. ``null`` - a sandboxed frame, a
    file:// page, a redirect from another site - is never ours.
    """
    origins = _env_list(ALLOWED_ORIGINS_ENV) if extra_origins is None else extra_origins
    if "*" in origins:
        return env_value("DEBATEAI_ENV", "development").lower() != "production"
    value = (origin or "").strip().lower()
    if not value or value == "null":
        return False
    if value in origins:
        return True
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or parts.path not in ("", "/"):
        return False
    return hostname_allowed(parts.hostname or "", extra_hosts)


def cors_allowed_origins() -> list[str]:
    """Explicit origins for CORSMiddleware, from the environment."""
    return [o for o in _env_list(ALLOWED_ORIGINS_ENV) if o != "*"]


def _websocket_instance_protocol(headers: Headers) -> tuple[str, str] | None:
    """Return the offered instance-token subprotocol and its token.

    Query-string tokens are deliberately unsupported: URLs are routinely
    copied into browser history, reverse-proxy logs, access logs, and tracing
    systems. WebSocket subprotocols are carried in the handshake headers and
    echoed only after validation.
    """
    protocols = [
        value.strip()
        for header in headers.getlist("sec-websocket-protocol")
        for value in header.split(",")
        if value.strip().startswith(WS_TOKEN_PROTOCOL_PREFIX)
    ]
    if len(protocols) != 1:
        return None
    protocol = protocols[0]
    return protocol, protocol[len(WS_TOKEN_PROTOCOL_PREFIX):]


def instance_token_matches(supplied: str | None, expected: str) -> bool:
    """Compare a single ASCII instance secret; malformed input fails closed."""
    return bool(
        isinstance(supplied, str)
        and supplied
        and isinstance(expected, str)
        and expected
        and supplied.isascii()
        and expected.isascii()
        and hmac.compare_digest(supplied, expected)
    )


def _instance_cookie(headers: Headers) -> str:
    # Reject ambiguity rather than accepting whichever cookie a parser chose
    # last. SimpleCookie also accepts whitespace-separated assignments, so
    # those duplicates must be rejected too. Multiple Cookie headers may
    # carry unrelated legitimate cookies.
    raw = "; ".join(headers.getlist("cookie"))
    if len(re.findall(r"(?:^|[;\s])" + re.escape(INSTANCE_COOKIE) + r"\s*=", raw)) != 1:
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(raw)
    except (CookieError, TypeError, ValueError):
        return ""
    morsel = cookie.get(INSTANCE_COOKIE)
    return morsel.value if morsel is not None else ""


def _request_instance_token(headers: Headers) -> str:
    supplied = headers.getlist("x-debateai-instance")
    if supplied:
        # An explicit malformed header must not be rescued by a valid cookie.
        return supplied[0] if len(supplied) == 1 else ""
    return _instance_cookie(headers)


class RequestGuardMiddleware:
    """Reject requests whose Host or Origin is not one of ours.

    Applies to HTTP and WebSocket handshakes alike; a websocket with a foreign
    Host is closed before it is accepted, which the client sees as a 403.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: list[str] | None = None,
        allowed_origins: list[str] | None = None,
    ) -> None:
        self.app = app
        self.allowed_hosts = allowed_hosts
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        host = headers.get("host", "")
        if not host_header_allowed(host, self.allowed_hosts):
            logger.warning(
                "Rejected request for unrecognized host %r; set %s to allow it",
                host[:120],
                ALLOWED_HOSTS_ENV,
            )
            await self._reject(scope, receive, send, 400, "Host header is not allowed")
            return
        # Browsers put an Origin on every WebSocket handshake and on every
        # state-changing HTTP request; a page on a foreign origin gets neither.
        # WebSockets are checked unconditionally because CORS never applied to
        # them: without this, a hostile page could open ws://127.0.0.1/ws/<id>
        # and both read the live transcript and drive the call.
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        health_path = path in {"/health", "/api/health", "/api/ready"}
        bootstrap_path = (
            path == "/api/meta" and _hostname_of(host) in LOOPBACK_NAMES
        ) or _desktop_frontend_path(path, method, host)
        origin_checked = scope["type"] == "websocket" or method not in _SAFE_METHODS
        if origin_checked:
            origin = headers.get("origin")
            if origin is None and method not in _SAFE_METHODS and scope["type"] != "websocket":
                expected = env_value("DEBATEAI_INSTANCE_TOKEN")
                supplied = _request_instance_token(headers)
                if expected and not instance_token_matches(supplied, expected):
                    await self._reject(scope, receive, send, 403, "Origin or instance authorization is required")
                    return
            elif origin is not None and not origin_allowed(origin, self.allowed_hosts, self.allowed_origins):
                logger.warning(
                    "Rejected cross-origin %s from %r; set %s to allow it",
                    "websocket" if scope["type"] == "websocket" else method,
                    origin[:120],
                    ALLOWED_ORIGINS_ENV,
                )
                await self._reject(scope, receive, send, 403, "Origin is not allowed")
                return
        selected_ws_protocol: str | None = None
        if scope["type"] == "websocket":
            expected = env_value("DEBATEAI_INSTANCE_TOKEN")
            if expected:
                offered = _websocket_instance_protocol(headers)
                supplied = offered[1] if offered else ""
                if not instance_token_matches(supplied, expected):
                    await self._reject(
                        scope,
                        receive,
                        send,
                        403,
                        "Desktop session authorization is required",
                    )
                    return
                selected_ws_protocol = offered[0]
        elif method not in {"OPTIONS"} and not health_path:
            expected = env_value("DEBATEAI_INSTANCE_TOKEN")
            supplied = _request_instance_token(headers)
            if expected and not instance_token_matches(supplied, expected) and not bootstrap_path:
                await self._reject(
                    scope,
                    receive,
                    send,
                    403,
                    "Desktop session authorization is required",
                )
                return
        if scope["type"] == "http" and bootstrap_path:
            expected = env_value("DEBATEAI_INSTANCE_TOKEN")
            async def send_bootstrap(message):
                if message["type"] == "http.response.start" and expected:
                    headers_out = list(message.get("headers") or [])
                    headers_out.append((b"x-debateai-instance", expected.encode("utf-8")))
                    headers_out.append(
                        (
                            b"set-cookie",
                            f"{INSTANCE_COOKIE}={expected}; Path=/; HttpOnly; SameSite=Strict".encode("utf-8"),
                        )
                    )
                    message = {**message, "headers": headers_out}
                await send(message)
            await self.app(scope, receive, send_bootstrap)
            return
        if scope["type"] == "websocket" and selected_ws_protocol:
            async def send_websocket(message):
                if message["type"] == "websocket.accept":
                    message = {**message, "subprotocol": selected_ws_protocol}
                await send(message)
            await self.app(scope, receive, send_websocket)
            return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, status: int, message: str) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008, "reason": message})
            return
        response = PlainTextResponse(message, status_code=status)
        await response(scope, receive, send)
