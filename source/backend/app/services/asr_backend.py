"""Stable contracts and a local NeMo-Speech.cpp realtime ASR adapter.

The realtime wire contract is pinned to NeMo-Speech.cpp v0.3.0.  The adapter
does not download a runtime or model.  Each capture track owns one WebSocket,
which is also the unit that owns the runtime's cache-aware encoder state.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import subprocess
import sys
import uuid
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen


NEMO_SPEECH_CPP_VERSION = "0.3.0"
NEMOTRON_BACKEND_ID = "local-nemotron-nemo-speech-cpp"
NEMOTRON_REALTIME_PATH = "/v1/audio/transcriptions/realtime"
_MAX_RECONNECT_AUDIO_BYTES = 30 * 16_000 * 2


@runtime_checkable
class ASRBackend(Protocol):
    """Minimal contract shared by batch and live segment consumers."""

    async def transcribe_segment(self, pcm_bytes: bytes) -> str | None: ...


@dataclass(frozen=True)
class ASRBackendCapability:
    id: str
    label: str
    available: bool
    reason: str
    installed: bool = False
    capable: bool = False
    ready: bool = False
    runtime_version: str = ""


@dataclass(frozen=True)
class StreamingTranscript:
    track: Hashable
    text: str
    revision: int
    words: tuple[dict[str, Any], ...] = ()
    language: str = ""
    event_id: str = ""


@dataclass
class _TrackStream:
    track: Hashable
    socket: Any
    finals: asyncio.Queue[StreamingTranscript | Exception] = field(
        default_factory=asyncio.Queue
    )
    pending_audio: bytearray = field(default_factory=bytearray)
    revision: int = 0
    receiver: asyncio.Task | None = None


def _installed_runtime_version(executable: Path) -> str:
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        completed = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            creationflags=flags,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    match = re.search(r"(?<!\d)v?(\d+\.\d+\.\d+)(?!\d)", completed.stdout + completed.stderr)
    return match.group(1) if match else ""


def _http_base_url() -> str:
    return os.environ.get("NEMO_SPEECH_CPP_URL", "http://127.0.0.1:8080").rstrip("/")


def _server_readiness(base_url: str) -> tuple[bool, str]:
    try:
        with urlopen(f"{base_url}/ready", timeout=0.75) as response:  # noqa: S310 - local opt-in URL
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - capability probes are non-fatal
        return False, f"server is not ready ({type(exc).__name__})"
    if payload.get("ready") is not True:
        return False, "server reported not ready"
    return True, "server and ASR model are ready"


def optional_nemotron_capability() -> ASRBackendCapability:
    """Report installation, protocol compatibility, and readiness separately."""
    executable = Path(os.environ.get("NEMO_SPEECH_CPP_BIN", ""))
    model = Path(os.environ.get("NEMOTRON_ASR_MODEL", ""))
    installed = executable.is_file() and model.is_file()
    version = _installed_runtime_version(executable) if executable.is_file() else ""
    capable = installed and version == NEMO_SPEECH_CPP_VERSION
    ready, ready_reason = _server_readiness(_http_base_url()) if capable else (False, "")
    if not installed:
        reason = "Not installed (set NEMO_SPEECH_CPP_BIN and NEMOTRON_ASR_MODEL)."
    elif not capable:
        actual = version or "unknown"
        reason = (
            f"Installed runtime {actual} is not the pinned protocol version "
            f"{NEMO_SPEECH_CPP_VERSION}."
        )
    else:
        reason = ready_reason
    return ASRBackendCapability(
        id=NEMOTRON_BACKEND_ID,
        label="Nemotron 3.5 via NeMo-Speech.cpp",
        available=installed and capable and ready,
        reason=reason,
        installed=installed,
        capable=capable,
        ready=ready,
        runtime_version=version,
    )


class ManagedNemoSpeechServer:
    """Own exactly one optional local server process and only ever stop it."""

    def __init__(self, executable: Path, model: Path, base_url: str):
        self._executable = executable
        self._model = model
        self._base_url = base_url
        self._process: subprocess.Popen | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._process is not None and self._process.poll() is None:
                return
            if not self._executable.is_file() or not self._model.is_file():
                raise RuntimeError("NeMo-Speech.cpp executable or model is not installed")
            version = await asyncio.to_thread(_installed_runtime_version, self._executable)
            if version != NEMO_SPEECH_CPP_VERSION:
                raise RuntimeError(
                    f"NeMo-Speech.cpp {NEMO_SPEECH_CPP_VERSION} is required; found {version or 'unknown'}"
                )
            parts = urlsplit(self._base_url)
            host = parts.hostname or "127.0.0.1"
            port = parts.port or (443 if parts.scheme == "https" else 80)
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self._process = subprocess.Popen(
                [
                    str(self._executable),
                    "serve",
                    "--asr-model",
                    str(self._model),
                    "--host",
                    host,
                    "--port",
                    str(port),
                    "--no-ui",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )

    async def stop(self) -> None:
        async with self._lock:
            process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(asyncio.to_thread(process.wait), 3.0)
        except TimeoutError:
            # Safe because this object created and owns exactly this process.
            process.kill()
            await asyncio.to_thread(process.wait)


class NemotronStreamingASRBackend:
    """NeMo-Speech.cpp v0.3.0 realtime transcription client.

    `feed_audio` keeps one connection per track, so microphone and system audio
    never share encoder caches.  `transcribe_segment` remains as a compatibility
    bridge for the existing ordered batch-transcription queue.
    """

    def __init__(
        self,
        *,
        language: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        connect: Callable[..., Awaitable[Any]] | None = None,
        on_partial: Callable[[Hashable, str], Any] | None = None,
        on_final: Callable[[StreamingTranscript], Any] | None = None,
        probe_readiness: bool = True,
        event_timeout: float = 30.0,
        server_manager: Any | None = None,
    ):
        self._language = language or "auto"
        self._base_url = (base_url or _http_base_url()).rstrip("/")
        self._api_key = api_key or os.environ.get("NEMO_SPEECH_CPP_API_KEY", "")
        self._connect_override = connect
        self._on_partial = on_partial
        self._on_final = on_final
        self._probe_readiness = probe_readiness
        self._event_timeout = event_timeout
        if server_manager is None and os.environ.get("NEMO_SPEECH_CPP_MANAGED") == "1":
            server_manager = ManagedNemoSpeechServer(
                Path(os.environ.get("NEMO_SPEECH_CPP_BIN", "")),
                Path(os.environ.get("NEMOTRON_ASR_MODEL", "")),
                self._base_url,
            )
        self._server_manager = server_manager
        self._streams: dict[Hashable, _TrackStream] = {}
        self._stream_lock = asyncio.Lock()
        self._closed = False
        self._session_id = ""

    def _websocket_url(self) -> str:
        parts = urlsplit(self._base_url)
        scheme = "wss" if parts.scheme == "https" else "ws"
        # Credentials must not travel in the URL: proxies, access logs, browser
        # history, and exception messages routinely persist query strings.
        return urlunsplit((scheme, parts.netloc, NEMOTRON_REALTIME_PATH, "", ""))

    async def _connect(self):
        if self._connect_override is not None:
            return await self._connect_override(self._websocket_url())
        import websockets

        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        return await websockets.connect(
            self._websocket_url(),
            additional_headers=headers,
            open_timeout=self._event_timeout,
            close_timeout=2,
            max_size=2**20,
        )

    async def _check_readiness(self) -> None:
        if not self._probe_readiness:
            return
        ready, reason = await asyncio.to_thread(_server_readiness, self._base_url)
        if ready:
            return
        if self._server_manager is None:
            raise RuntimeError(f"NeMo-Speech.cpp is not ready: {reason}")
        await self._server_manager.start()
        deadline = asyncio.get_running_loop().time() + self._event_timeout
        while True:
            ready, reason = await asyncio.to_thread(_server_readiness, self._base_url)
            if ready:
                return
            if asyncio.get_running_loop().time() >= deadline:
                raise RuntimeError(f"NeMo-Speech.cpp is not ready: {reason}")
            await asyncio.sleep(0.1)

    @staticmethod
    async def _event(socket: Any) -> dict[str, Any]:
        raw = await socket.recv()
        if isinstance(raw, bytes):
            raise RuntimeError("NeMo-Speech.cpp returned an unexpected binary event")
        event = json.loads(raw)
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise RuntimeError("NeMo-Speech.cpp returned a malformed event")
        if event["type"] == "error":
            message = event.get("message") or event.get("error", {}).get("message") or "unknown error"
            raise RuntimeError(f"NeMo-Speech.cpp realtime error: {message}")
        return event

    async def _open_stream(self, track: Hashable) -> _TrackStream:
        await self._check_readiness()
        socket = await self._connect()
        try:
            created = await asyncio.wait_for(self._event(socket), self._event_timeout)
            if created["type"] != "session.created":
                raise RuntimeError(f"Expected session.created, got {created['type']}")
            session = {
                "sample_rate": 16_000,
                "language": self._language,
                "automatic_punctuation": True,
                "verbatim": False,
                "word_timestamps": True,
            }
            await socket.send(json.dumps({"type": "session.update", "session": session}))
            updated = await asyncio.wait_for(self._event(socket), self._event_timeout)
            if updated["type"] != "session.updated":
                raise RuntimeError(f"Expected session.updated, got {updated['type']}")
        except Exception:
            await socket.close()
            raise
        stream = _TrackStream(track=track, socket=socket)
        stream.receiver = asyncio.create_task(
            self._receive_events(stream),
            name=f"nemotron-asr-{track}",
        )
        return stream

    async def _ensure_stream(self, track: Hashable) -> _TrackStream:
        if self._closed:
            raise RuntimeError("Nemotron streaming backend is closed")
        stream = self._streams.get(track)
        if stream is not None and stream.receiver is not None and not stream.receiver.done():
            return stream
        async with self._stream_lock:
            stream = self._streams.get(track)
            if stream is not None and stream.receiver is not None and not stream.receiver.done():
                return stream
            if stream is not None:
                stream = await self._replace_stream(track, stream)
                return stream
            stream = await self._open_stream(track)
            self._streams[track] = stream
            return stream

    async def _callback(self, callback: Callable[..., Any] | None, *args: Any) -> None:
        if callback is None:
            return
        result = callback(*args)
        if inspect.isawaitable(result):
            await result

    async def _receive_events(self, stream: _TrackStream) -> None:
        try:
            while True:
                event = await self._event(stream.socket)
                event_type = event["type"]
                if event_type.endswith(".delta"):
                    delta = str(event.get("delta") or event.get("text") or "")
                    await self._callback(self._on_partial, stream.track, delta)
                elif event_type.endswith(".completed"):
                    stream.revision += 1
                    result = StreamingTranscript(
                        track=stream.track,
                        text=str(event.get("transcript") or event.get("text") or ""),
                        revision=stream.revision,
                        words=tuple(event.get("words") or ()),
                        language=str(event.get("language") or ""),
                        event_id=str(event.get("event_id") or ""),
                    )
                    stream.pending_audio.clear()
                    await stream.finals.put(result)
                    await self._callback(self._on_final, result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # receiver failure is surfaced by flush/feed reconnect
            await stream.finals.put(exc)

    async def _replace_stream(self, track: Hashable, previous: _TrackStream) -> _TrackStream:
        replay = bytes(previous.pending_audio)
        await self._close_stream(previous)
        replacement = await self._open_stream(track)
        replacement.pending_audio.extend(replay)
        replacement.revision = previous.revision
        self._streams[track] = replacement
        if replay:
            await replacement.socket.send(replay)
        return replacement

    async def feed_audio(self, track: Hashable, pcm_bytes: bytes) -> None:
        if not pcm_bytes or len(pcm_bytes) % 2:
            raise ValueError("Nemotron streaming audio must be non-empty PCM16")
        stream = await self._ensure_stream(track)
        stream.pending_audio.extend(pcm_bytes)
        if len(stream.pending_audio) > _MAX_RECONNECT_AUDIO_BYTES:
            del stream.pending_audio[:-_MAX_RECONNECT_AUDIO_BYTES]
        try:
            await stream.socket.send(pcm_bytes)
        except Exception:
            await self._replace_stream(track, stream)

    async def flush(self, track: Hashable) -> StreamingTranscript:
        stream = await self._ensure_stream(track)
        deadline = asyncio.get_running_loop().time() + self._event_timeout
        for attempt in range(2):
            try:
                await stream.socket.send(json.dumps({"type": "input_audio_buffer.commit"}))
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError
                result = await asyncio.wait_for(stream.finals.get(), remaining)
                if isinstance(result, Exception):
                    raise result
                return result
            except TimeoutError:
                raise
            except Exception:
                if attempt:
                    raise
                stream = await self._replace_stream(track, stream)
        raise RuntimeError("NeMo-Speech.cpp realtime flush failed")

    async def cancel(self, track: Hashable) -> None:
        stream = self._streams.pop(track, None)
        if stream is None:
            return
        try:
            await stream.socket.send(json.dumps({"type": "input_audio_buffer.clear"}))
        except Exception:
            pass
        await self._close_stream(stream)

    async def _close_stream(self, stream: _TrackStream) -> None:
        receiver, stream.receiver = stream.receiver, None
        if receiver is not None:
            receiver.cancel()
        try:
            await stream.socket.close()
        finally:
            if receiver is not None:
                await asyncio.gather(receiver, return_exceptions=True)

    async def switch_session(self, session_id: str) -> None:
        if session_id == self._session_id:
            return
        self._session_id = session_id
        streams = list(self._streams.values())
        self._streams.clear()
        await asyncio.gather(*(self._close_stream(stream) for stream in streams))

    async def close(self) -> None:
        self._closed = True
        await self.switch_session(f"closed-{uuid.uuid4().hex}")
        if self._server_manager is not None:
            await self._server_manager.stop()

    async def transcribe_segment(self, pcm_bytes: bytes) -> str | None:
        track = f"segment-{uuid.uuid4().hex}"
        try:
            await self.feed_audio(track, pcm_bytes)
            result = await self.flush(track)
            return result.text or None
        finally:
            await self.cancel(track)
