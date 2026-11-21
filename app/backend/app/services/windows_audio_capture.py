"""Native Windows microphone and WASAPI loopback capture for desktop Debate AI."""

from __future__ import annotations

import array
import asyncio
import audioop
import hashlib
import json
import logging
import re
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
from app.services.native_audio_bridge import enqueue_native_message, native_audio_queue

logger = logging.getLogger(__name__)
TARGET_RATE = 16_000
FRAMES_PER_BUFFER = 1024


def _load_pyaudio():
    if sys.platform != "win32":
        return None
    try:
        import pyaudiowpatch as pyaudio
    except ImportError:
        return None
    return pyaudio


def _wasapi_host_api_index(audio: Any) -> int | None:
    pyaudio = _load_pyaudio()
    if pyaudio is None:
        return None
    get_host_api = getattr(audio, "get_host_api_info_by_type", None)
    if not callable(get_host_api):
        return None
    try:
        return int(get_host_api(pyaudio.paWASAPI)["index"])
    except (KeyError, OSError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class NativeAudioDevice:
    index: int
    name: str
    channels: int
    sample_rate: int
    loopback: bool = False
    endpoint_id: str = ""
    stable_id: str = ""
    is_default: bool = False


class Pcm16Converter:
    """Stateful device-rate/channel conversion to mono PCM16 at 16 kHz."""

    def __init__(self, sample_rate: int, channels: int):
        self.sample_rate = max(1, int(sample_rate))
        self.channels = max(1, int(channels))
        self._rate_state = None

    def convert(self, data: bytes) -> bytes:
        if self.channels == 1:
            mono = data
        elif self.channels == 2:
            mono = audioop.tomono(data, 2, 0.5, 0.5)
        else:
            samples = np.frombuffer(data, dtype="<i2")
            complete = len(samples) - (len(samples) % self.channels)
            if complete <= 0:
                return b""
            frames = samples[:complete].reshape(-1, self.channels)
            mono = np.mean(frames.astype(np.int32), axis=1).astype("<i2").tobytes()
        converted, self._rate_state = audioop.ratecv(
            mono,
            2,
            1,
            self.sample_rate,
            TARGET_RATE,
            self._rate_state,
        )
        return converted


def _stable_endpoint_id(info: dict[str, Any], *, loopback: bool = False) -> str:
    native = str(
        info.get("deviceUID")
        or info.get("deviceId")
        or info.get("endpointId")
        or info.get("endpoint_id")
        or ""
    ).strip()
    if native:
        return f"mmdevice:{native}"
    seed = "|".join(
        (
            str(info.get("hostApi") or ""),
            str(info.get("name") or "").strip().casefold(),
            str(info.get("maxInputChannels") or 0),
            str(info.get("maxOutputChannels") or 0),
            "loopback" if loopback or info.get("isLoopbackDevice") else "input",
        )
    )
    return "wasapi:derived:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _normalized_endpoint_name(value: str) -> str:
    value = re.sub(r"\[loopback\]$", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\(\s*\d+\s*-\s*", "(", value)
    return "".join(character for character in value.casefold() if character.isalnum())


def _resolve_mmdevice_identity(
    info: dict[str, Any], *, loopback: bool = False
) -> tuple[str, str]:
    if sys.platform != "win32" or info.get("_is_wasapi") is False:
        return "", ""
    try:
        import winreg
    except ImportError:
        return "", ""

    flow = "Render" if loopback or info.get("isLoopbackDevice") else "Capture"
    root_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\{flow}"
    target = _normalized_endpoint_name(str(info.get("name") or ""))
    matches: list[tuple[str, str]] = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root_path)
    except OSError:
        return "", ""
    with root:
        for index in range(winreg.QueryInfoKey(root)[0]):
            endpoint_key_name = winreg.EnumKey(root, index)
            try:
                endpoint_key = winreg.OpenKey(root, endpoint_key_name)
                with endpoint_key:
                    state = winreg.QueryValueEx(endpoint_key, "DeviceState")[0]
                if state != 1:
                    continue
                properties = winreg.OpenKey(root, endpoint_key_name + r"\Properties")
                with properties:
                    description = winreg.QueryValueEx(
                        properties,
                        "{a45c254e-df1c-4efd-8020-67d146a850e0},2",
                    )[0]
                    interface_name = winreg.QueryValueEx(
                        properties,
                        "{b3f8fa53-0004-438e-9003-51a46e139bfc},6",
                    )[0]
                    try:
                        stable_id = winreg.QueryValueEx(
                            properties,
                            "{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},12",
                        )[0]
                    except OSError:
                        stable_id = ""
            except OSError:
                continue
            candidate = _normalized_endpoint_name(f"{description} ({interface_name})")
            if candidate != target:
                continue
            prefix = "{0.0.0.00000000}" if flow == "Render" else "{0.0.1.00000000}"
            matches.append((f"{prefix}.{endpoint_key_name}", str(stable_id or "")))
    return matches[0] if len(matches) == 1 else ("", "")


def _device_from_info(
    info: dict[str, Any], *, loopback: bool = False, is_default: bool = False
) -> NativeAudioDevice:
    channels = int(info.get("maxInputChannels") or info.get("maxOutputChannels") or 1)
    resolved_endpoint, resolved_stable = _resolve_mmdevice_identity(
        info, loopback=loopback
    )
    identity_info = dict(info)
    if resolved_endpoint and not any(
        identity_info.get(key)
        for key in ("deviceUID", "deviceId", "endpointId", "endpoint_id")
    ):
        identity_info["endpointId"] = resolved_endpoint
    return NativeAudioDevice(
        index=int(info["index"]),
        name=str(info.get("name") or f"Audio {info['index']}"),
        channels=max(1, channels),
        sample_rate=max(1, int(float(info.get("defaultSampleRate") or TARGET_RATE))),
        loopback=loopback or bool(info.get("isLoopbackDevice")),
        endpoint_id=_stable_endpoint_id(identity_info, loopback=loopback),
        stable_id=str(
            info.get("stableId")
            or info.get("stable_id")
            or info.get("PKEY_AudioEndpoint_StableId")
            or resolved_stable
            or ""
        ).strip(),
        is_default=is_default,
    )


def select_default_devices(
    audio: Any,
) -> tuple[NativeAudioDevice, NativeAudioDevice | None]:
    get_default_wasapi = getattr(audio, "get_default_wasapi_device", None)
    microphone_info = dict(
        get_default_wasapi(d_in=True)
        if callable(get_default_wasapi)
        else audio.get_default_input_device_info()
    )
    if callable(get_default_wasapi):
        microphone_info["_is_wasapi"] = True
    microphone = _device_from_info(microphone_info)
    loopback_info = None
    get_default_loopback = getattr(audio, "get_default_wasapi_loopback", None)
    if callable(get_default_loopback):
        try:
            loopback_info = get_default_loopback()
        except OSError:
            loopback_info = None
    if loopback_info is None:
        get_loopbacks = getattr(audio, "get_loopback_device_info_generator", None)
        if callable(get_loopbacks):
            loopback_info = next(iter(get_loopbacks()), None)
    if loopback_info is not None:
        loopback_info = dict(loopback_info)
        loopback_info["_is_wasapi"] = True
    loopback = (
        _device_from_info(loopback_info, loopback=True)
        if loopback_info is not None
        else None
    )
    return microphone, loopback


def select_devices(
    audio: Any,
    microphone_index: int | None = None,
    loopback_index: int | None = None,
    microphone_id: str | None = None,
    loopback_id: str | None = None,
    microphone_mode: str | None = None,
    loopback_mode: str | None = None,
) -> tuple[NativeAudioDevice, NativeAudioDevice | None]:
    default_microphone, default_loopback = select_default_devices(audio)
    microphone = default_microphone
    loopback = default_loopback
    if microphone_mode == "fixed":
        try:
            microphone = _device_by_endpoint_id(
                audio, microphone_id or "", loopback=False
            )
        except OSError:
            # PyAudio can briefly omit the endpoint from its enumeration while
            # Windows is renewing the default device. Keep an explicitly
            # selected device only when the current default exposes the same
            # stable identity. Other fixed-device failures remain errors.
            if not _device_matches_id(default_microphone, microphone_id):
                raise
            microphone = default_microphone
    elif microphone_index is not None and microphone_mode is None:
        microphone = _device_from_info(audio.get_device_info_by_index(microphone_index))
        if microphone.loopback:
            raise OSError("Das gewaehlte Mikrofon ist ein Loopback-Geraet")
    if loopback_mode == "fixed":
        try:
            loopback = _device_by_endpoint_id(audio, loopback_id or "", loopback=True)
        except OSError:
            if not _device_matches_id(default_loopback, loopback_id):
                raise
            loopback = default_loopback
    elif loopback_index is not None and loopback_mode is None:
        info = audio.get_device_info_by_index(loopback_index)
        if not bool(info.get("isLoopbackDevice")):
            raise OSError("Das gewaehlte Systemgeraet bietet kein Loopback")
        loopback = _device_from_info(info, loopback=True)
    return microphone, loopback


def _device_matches_id(
    device: NativeAudioDevice | None, endpoint_id: str | None
) -> bool:
    if device is None or not endpoint_id:
        return False
    if not device.endpoint_id.startswith("mmdevice:"):
        return False
    legacy_native_id = (
        f"wasapi:{device.endpoint_id.removeprefix('mmdevice:')}"
        if device.endpoint_id.startswith("mmdevice:")
        else ""
    )
    return endpoint_id in (device.endpoint_id, device.stable_id, legacy_native_id)


def _device_by_endpoint_id(
    audio: Any, endpoint_id: str, *, loopback: bool
) -> NativeAudioDevice:
    if not endpoint_id:
        raise OSError("Fuer die feste Geraeteauswahl fehlt die stabile Endpoint-ID")
    matches: list[NativeAudioDevice] = []
    wasapi_host_api = _wasapi_host_api_index(audio)
    for index in range(audio.get_device_count()):
        info = dict(audio.get_device_info_by_index(index))
        if wasapi_host_api is not None:
            info["_is_wasapi"] = int(info.get("hostApi", -1)) == wasapi_host_api
        device = _device_from_info(info, loopback=bool(info.get("isLoopbackDevice")))
        legacy_native_id = (
            f"wasapi:{device.endpoint_id.removeprefix('mmdevice:')}"
            if device.endpoint_id.startswith("mmdevice:")
            else ""
        )
        if endpoint_id not in (device.endpoint_id, device.stable_id, legacy_native_id):
            continue
        if device.loopback != loopback:
            continue
        matches.append(device)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise OSError(
            "Die gespeicherte Geraetezuordnung ist mehrdeutig; bitte das "
            "Windows-Audiogeraet erneut eindeutig auswaehlen"
        )
    raise OSError("Das fest gewaehlte Windows-Audiogeraet ist nicht mehr verfuegbar")


class NativeWindowsAudioCapture:
    def __init__(self):
        self._lock = threading.RLock()
        self._audio = None
        self._streams: dict[int, Any] = {}
        self._devices: dict[int, NativeAudioDevice] = {}
        self._converters: dict[int, Pcm16Converter] = {}
        self._last_callback_at: dict[int, float] = {}
        self._sample_counters: dict[int, int] = {}
        self._session_id: str | None = None
        self._queue: asyncio.Queue[dict] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._system_requested = True
        self._microphone_index: int | None = None
        self._loopback_index: int | None = None
        self._microphone_id: str | None = None
        self._loopback_id: str | None = None
        self._microphone_mode = "follow_default"
        self._loopback_mode = "follow_default"
        self._last_error = ""
        self._monitor_task: asyncio.Task | None = None
        # Generation invalidates an in-flight restart when a caller stops or
        # replaces the capture session while the monitor is reopening streams.
        self._generation = 0

    @property
    def available(self) -> bool:
        return _load_pyaudio() is not None

    def _enqueue(self, message: dict) -> None:
        if self._loop is None or self._queue is None:
            return
        self._loop.call_soon_threadsafe(enqueue_native_message, self._queue, message)

    def _callback(self, track: int, continue_code: int):
        def receive(data, _frame_count, _time_info, status_flags):
            self._last_callback_at[track] = time.monotonic()
            if status_flags:
                self._last_error = f"Audiogeraet meldet Status {status_flags}"
            converter = self._converters.get(track)
            pcm = converter.convert(data) if converter else b""
            if pcm:
                # Scale quiet speech into the same practical 0..1 range used
                # by the browser meter. Clamp loud peaks instead of amplifying
                # the recorded audio itself.
                level = min(1.0, audioop.rms(pcm, 2) / 32768.0 * 10.0)
                counter = self._sample_counters.get(track, 0)
                self._sample_counters[track] = counter + len(pcm) // 2
                device = self._devices.get(track)
                self._enqueue(
                    {
                        "bytes": bytes((track,)) + pcm,
                        "audio_meta": {
                            "origin": "native-wasapi",
                            "sample_rate": TARGET_RATE,
                            "sample_counter": counter,
                            "captured_at_ms": round(time.time() * 1000),
                            "device_id": device.endpoint_id
                            if device
                            else f"native-{track}",
                            "level": round(level, 4),
                        },
                    }
                )
            return (None, continue_code)

        return receive

    def _open_stream(self, pyaudio: Any, device: NativeAudioDevice, track: int):
        self._converters[track] = Pcm16Converter(device.sample_rate, device.channels)
        self._last_callback_at[track] = time.monotonic()
        stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=device.channels,
            rate=device.sample_rate,
            input=True,
            input_device_index=device.index,
            frames_per_buffer=FRAMES_PER_BUFFER,
            stream_callback=self._callback(track, pyaudio.paContinue),
            start=False,
        )
        stream.start_stream()
        self._streams[track] = stream
        self._devices[track] = device

    def _start_sync(self) -> tuple[NativeAudioDevice, NativeAudioDevice | None]:
        with self._lock:
            pyaudio = _load_pyaudio()
            if pyaudio is None:
                raise RuntimeError("PyAudioWPatch ist nicht installiert")
            self._audio = pyaudio.PyAudio()
            try:
                microphone, loopback = select_devices(
                    self._audio,
                    self._microphone_index,
                    self._loopback_index,
                    self._microphone_id,
                    self._loopback_id,
                    self._microphone_mode,
                    self._loopback_mode,
                )
                self._open_stream(pyaudio, microphone, 0)
                if self._system_requested and loopback is not None:
                    self._open_stream(pyaudio, loopback, 1)
                return microphone, loopback if 1 in self._streams else None
            except Exception:
                self._stop_sync()
                raise

    def _stop_sync(self) -> None:
        with self._lock:
            for stream in self._streams.values():
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    logger.debug("Native audio stream already closed", exc_info=True)
            self._streams.clear()
            self._devices.clear()
            self._converters.clear()
            self._last_callback_at.clear()
            self._sample_counters.clear()
            if self._audio is not None:
                try:
                    self._audio.terminate()
                except Exception:
                    logger.debug("Native audio host already terminated", exc_info=True)
            self._audio = None

    async def start(
        self,
        session_id: uuid.UUID | str,
        *,
        system_audio: bool = True,
        microphone_index: int | None = None,
        loopback_index: int | None = None,
        microphone_id: str | None = None,
        loopback_id: str | None = None,
        microphone_mode: str = "follow_default",
        loopback_mode: str = "follow_default",
    ) -> dict:
        await self.stop()
        queue = native_audio_queue(session_id)
        if queue is None:
            raise RuntimeError("Die Live-Verbindung ist noch nicht bereit")
        self._session_id = str(session_id)
        self._queue = queue
        self._loop = asyncio.get_running_loop()
        self._system_requested = bool(system_audio)
        self._microphone_index = microphone_index
        self._loopback_index = loopback_index
        self._microphone_id = microphone_id
        self._loopback_id = loopback_id
        self._microphone_mode = microphone_mode
        self._loopback_mode = loopback_mode
        self._last_error = ""
        microphone, loopback = await asyncio.to_thread(self._start_sync)
        self._enqueue(
            {
                "text": json.dumps(
                    {
                        "type": "track_state",
                        "track": 1,
                        "active": loopback is not None,
                    }
                )
            }
        )
        self._monitor_task = asyncio.create_task(
            self._monitor(), name="native-windows-audio"
        )
        return self.status(microphone=microphone, loopback=loopback)

    async def _monitor(self) -> None:
        while self._session_id is not None:
            await asyncio.sleep(2)
            generation = self._generation
            restart, reason = await asyncio.to_thread(self._restart_needed_sync)
            if (
                not restart
                or generation != self._generation
                or self._session_id is None
            ):
                continue
            self._last_error = reason
            try:
                await asyncio.to_thread(self._stop_sync)
                if generation != self._generation or self._session_id is None:
                    return
                _microphone, loopback = await asyncio.to_thread(self._start_sync)
                if generation != self._generation or self._session_id is None:
                    await asyncio.to_thread(self._stop_sync)
                    return
                self._enqueue(
                    {
                        "text": json.dumps(
                            {
                                "type": "track_state",
                                "track": 1,
                                "active": loopback is not None,
                            }
                        )
                    }
                )
            except Exception as exc:
                self._last_error = str(exc)
                logger.warning("Native audio restart failed: %s", exc)

    def _restart_needed_sync(self) -> tuple[bool, str]:
        """Detect interruptions and Windows default-device changes."""
        with self._lock:
            if self._audio is None or not self._streams:
                return True, "Audiogeraet wurde unterbrochen; Verbindung wird erneuert"
            if not all(stream.is_active() for stream in self._streams.values()):
                return True, "Audiogeraet wurde unterbrochen; Verbindung wird erneuert"
            now = time.monotonic()
            stalled = [
                track
                for track in self._streams
                if now - self._last_callback_at.get(track, 0.0) > 6.0
            ]
            if stalled:
                return (
                    True,
                    "Audiogeraet liefert keine Audiodaten; Verbindung wird erneuert",
                )
            try:
                microphone, loopback = select_devices(
                    self._audio,
                    self._microphone_index,
                    self._loopback_index,
                    self._microphone_id,
                    self._loopback_id,
                    self._microphone_mode,
                    self._loopback_mode,
                )
            except Exception:
                return (
                    True,
                    "Windows-Audiogeraet ist nicht mehr verfuegbar; Verbindung wird erneuert",
                )
            expected = {0: microphone}
            if self._system_requested and loopback is not None:
                expected[1] = loopback
            current = {
                track: (
                    device.index,
                    device.sample_rate,
                    device.channels,
                    device.endpoint_id,
                    device.stable_id,
                )
                for track, device in self._devices.items()
            }
            selected = {
                track: (
                    device.index,
                    device.sample_rate,
                    device.channels,
                    device.endpoint_id,
                    device.stable_id,
                )
                for track, device in expected.items()
            }
            if current != selected:
                return (
                    True,
                    "Windows-Standardgeraet wurde gewechselt; Aufnahme wird umgestellt",
                )
            return False, ""

    async def stop(self) -> dict:
        # Invalidate any monitor restart that may currently be between
        # stop_sync() and start_sync(). The generation is checked after every
        # blocking transition so a disconnected WebSocket cannot resurrect
        # native capture or enqueue into a stale queue.
        with self._lock:
            self._generation += 1
            self._session_id = None
        monitor, self._monitor_task = self._monitor_task, None
        if monitor is not None and monitor is not asyncio.current_task():
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)
        if self._queue is not None:
            self._enqueue(
                {
                    "text": json.dumps(
                        {"type": "track_state", "track": 1, "active": False}
                    )
                }
            )
        await asyncio.to_thread(self._stop_sync)
        self._queue = None
        self._loop = None
        return self.status()

    async def stop_session(self, session_id: uuid.UUID | str) -> dict:
        """Stop only when the caller still owns the native capture."""
        if self._session_id != str(session_id):
            return self.status()
        return await self.stop()

    def status(
        self,
        *,
        microphone: NativeAudioDevice | None = None,
        loopback: NativeAudioDevice | None = None,
    ) -> dict:
        microphone = microphone or self._devices.get(0)
        loopback = loopback or self._devices.get(1)
        return {
            "available": self.available,
            "active": bool(self._streams),
            "session_id": self._session_id,
            "microphone": microphone.__dict__ if microphone else None,
            "system_audio": loopback.__dict__ if loopback else None,
            "system_audio_active": 1 in self._streams,
            "last_error": self._last_error,
        }

    def devices(self) -> list[dict]:
        pyaudio = _load_pyaudio()
        if pyaudio is None:
            return []
        audio = pyaudio.PyAudio()
        try:
            devices = []
            default_mic, default_loopback = select_default_devices(audio)
            default_ids = {
                default_mic.endpoint_id,
                default_loopback.endpoint_id if default_loopback else "",
            }
            wasapi_host_api = _wasapi_host_api_index(audio)
            for index in range(audio.get_device_count()):
                info = dict(audio.get_device_info_by_index(index))
                if int(info.get("maxInputChannels") or 0) <= 0:
                    continue
                if wasapi_host_api is not None:
                    info["_is_wasapi"] = int(info.get("hostApi", -1)) == wasapi_host_api
                loopback = bool(info.get("isLoopbackDevice"))
                device = _device_from_info(info, loopback=loopback)
                devices.append(
                    {**device.__dict__, "is_default": device.endpoint_id in default_ids}
                )
            return devices
        finally:
            audio.terminate()

    def _probe_microphone_sync(self, device_index: int) -> float:
        pyaudio = _load_pyaudio()
        if pyaudio is None:
            raise RuntimeError("PyAudioWPatch ist nicht installiert")
        audio = pyaudio.PyAudio()
        stream = None
        try:
            device = _device_from_info(audio.get_device_info_by_index(device_index))
            if device.loopback:
                raise OSError("Loopback ist kein Mikrofon")
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=device.channels,
                rate=device.sample_rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )
            peak = 0
            for _ in range(8):
                samples = array.array(
                    "h", stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                )
                if samples:
                    peak = max(
                        peak,
                        max(
                            abs(value) for value in samples[:: max(1, device.channels)]
                        ),
                    )
            return min(1.0, peak / 32768.0)
        finally:
            if stream is not None:
                stream.close()
            audio.terminate()

    async def probe_microphone(self, device_index: int) -> float:
        if self._streams:
            raise RuntimeError("Die Aufnahme laeuft bereits")
        return await asyncio.to_thread(self._probe_microphone_sync, device_index)


native_windows_audio = NativeWindowsAudioCapture()
