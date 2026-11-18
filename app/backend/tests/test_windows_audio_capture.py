import array
import unittest
from unittest.mock import AsyncMock, patch

import numpy as np

from app.services.native_audio_bridge import (
    enqueue_native_message,
    register_native_audio_session,
    unregister_native_audio_session,
)
from app.services.windows_audio_capture import (
    NativeWindowsAudioCapture,
    Pcm16Converter,
    select_default_devices,
    select_devices,
)


class _FakeAudio:
    def get_default_input_device_info(self):
        return {
            "index": 2,
            "name": "Headset Mic",
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
        }

    def get_default_wasapi_loopback(self):
        return {
            "index": 7,
            "name": "Speakers [Loopback]",
            "maxInputChannels": 2,
            "defaultSampleRate": 48000,
            "isLoopbackDevice": True,
        }

    def get_default_wasapi_device(self, *, d_in=False, d_out=False):
        if not d_in or d_out:
            raise AssertionError("expected the WASAPI input endpoint")
        return {
            "index": 5,
            "name": "Headset Mic",
            "hostApi": 2,
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
        }


class WindowsAudioCaptureTests(unittest.TestCase):
    def test_defaults_keep_microphone_and_loopback_separate(self):
        microphone, loopback = select_default_devices(_FakeAudio())
        self.assertEqual(5, microphone.index)
        self.assertFalse(microphone.loopback)
        self.assertEqual(7, loopback.index)
        self.assertTrue(loopback.loopback)

    def test_explicit_devices_are_used_for_the_session(self):
        audio = _FakeAudio()
        audio.get_device_info_by_index = lambda index: {
            "index": index,
            "name": "Chosen loopback" if index == 9 else "Chosen mic",
            "maxInputChannels": 2 if index == 9 else 1,
            "defaultSampleRate": 48000,
            "isLoopbackDevice": index == 9,
        }
        microphone, loopback = select_devices(audio, 4, 9)
        self.assertEqual(4, microphone.index)
        self.assertEqual(9, loopback.index)
        self.assertTrue(loopback.loopback)

    def test_converter_produces_mono_pcm16_at_16khz(self):
        stereo = np.zeros((4800, 2), dtype="<i2")
        stereo[:, 0] = 1200
        stereo[:, 1] = -400
        converted = Pcm16Converter(48000, 2).convert(stereo.tobytes())
        self.assertGreaterEqual(len(converted), 3190)
        self.assertLessEqual(len(converted), 3210)
        self.assertEqual(0, len(converted) % 2)

    def test_converter_keeps_rate_state_across_44100hz_tail_blocks(self):
        source = (np.ones(44_100, dtype="<i2") * 700).tobytes()
        converter = Pcm16Converter(44_100, 1)
        pieces = [source[:29_400], source[29_400:58_800], source[58_800:]]
        converted = b"".join(converter.convert(piece) for piece in pieces)

        self.assertEqual(16_000, len(converted) // 2)
        self.assertEqual(0, len(converted) % 2)
        self.assertTrue(np.all(np.frombuffer(converted, dtype="<i2") == 700))

    def test_each_track_has_an_independent_resampler_state(self):
        source = (np.arange(4_800, dtype="<i2") * 3).tobytes()
        mic = Pcm16Converter(48_000, 1)
        system = Pcm16Converter(44_100, 1)

        mic_first = mic.convert(source[:4_000])
        system_first = system.convert(source[:4_000])
        mic_second = mic.convert(source[4_000:])
        system_second = system.convert(source[4_000:])

        self.assertNotEqual(len(mic_first + mic_second), len(system_first + system_second))
        self.assertEqual(0, len(mic_first + mic_second) % 2)
        self.assertEqual(0, len(system_first + system_second) % 2)

    def test_bridge_preserves_accepted_pcm_and_signals_byte_budget_overflow(self):
        queue = register_native_audio_session("overflow-contract")
        first = {"bytes": bytes((0,)) + (b"\x00" * 64_000)}
        second = {"bytes": bytes((1,)) + (b"\x00" * 64_000)}
        overflow = {"bytes": bytes((0,)) + b"\x00\x00"}
        try:
            self.assertTrue(enqueue_native_message(queue, first))
            self.assertTrue(enqueue_native_message(queue, second))
            self.assertFalse(enqueue_native_message(queue, overflow))

            self.assertIs(first, queue.get_nowait())
            self.assertIs(second, queue.get_nowait())
            marker = queue.get_nowait()
            self.assertEqual("native_audio_overflow", marker["native_overflow"]["state"])
            self.assertIn('"type": "stop"', marker["text"])
        finally:
            unregister_native_audio_session("overflow-contract", queue)

    def test_active_stream_without_callbacks_is_restarted(self):
        capture = NativeWindowsAudioCapture()
        microphone, loopback = select_default_devices(_FakeAudio())
        capture._audio = _FakeAudio()
        capture._streams = {0: _ActiveStream(), 1: _ActiveStream()}
        capture._devices = {0: microphone, 1: loopback}
        capture._last_callback_at = {0: 10.0, 1: 19.0}

        with patch("app.services.windows_audio_capture.time.monotonic", return_value=20.0):
            restart, reason = capture._restart_needed_sync()

        self.assertTrue(restart)
        self.assertIn("keine Audiodaten", reason)

    def test_device_rate_change_is_treated_as_a_capture_restart(self):
        capture = NativeWindowsAudioCapture()
        microphone, loopback = select_default_devices(_FakeAudio())
        capture._audio = _FakeAudio()
        capture._streams = {0: _ActiveStream(), 1: _ActiveStream()}
        capture._devices = {0: microphone, 1: loopback}
        capture._last_callback_at = {0: 20.0, 1: 20.0}

        class ChangedRateAudio(_FakeAudio):
            def get_default_wasapi_device(self, *, d_in=False, d_out=False):
                info = super().get_default_wasapi_device(d_in=d_in, d_out=d_out)
                info["defaultSampleRate"] = 44_100
                return info

        capture._audio = ChangedRateAudio()
        with patch("app.services.windows_audio_capture.time.monotonic", return_value=20.1):
            restart, reason = capture._restart_needed_sync()

        self.assertTrue(restart)
        self.assertIn("Standardgeraet", reason)

    def test_device_endpoint_swap_with_same_stream_shape_is_restart(self):
        capture = NativeWindowsAudioCapture()
        microphone, loopback = select_default_devices(_FakeAudio())
        capture._audio = _FakeAudio()
        capture._streams = {0: _ActiveStream(), 1: _ActiveStream()}
        capture._devices = {0: microphone, 1: loopback}
        capture._last_callback_at = {0: 20.0, 1: 20.0}

        class ChangedEndpointAudio(_FakeAudio):
            def get_default_wasapi_device(self, *, d_in=False, d_out=False):
                info = super().get_default_wasapi_device(d_in=d_in, d_out=d_out)
                info["deviceUID"] = "new-microphone-endpoint"
                return info

            def get_default_wasapi_loopback(self):
                info = super().get_default_wasapi_loopback()
                info["deviceUID"] = "new-loopback-endpoint"
                return info

        capture._audio = ChangedEndpointAudio()
        with patch("app.services.windows_audio_capture.time.monotonic", return_value=20.1):
            restart, reason = capture._restart_needed_sync()

        self.assertTrue(restart)
        self.assertIn("Standardgeraet", reason)

    def test_native_callback_reports_a_scaled_live_meter_level(self):
        capture = NativeWindowsAudioCapture()
        capture._converters[0] = Pcm16Converter(16000, 1)
        capture._sample_counters[0] = 0
        captured = []
        capture._enqueue = captured.append
        pcm = array.array("h", [1638] * 1024).tobytes()

        receive = capture._callback(0, 0)
        receive(pcm, 1024, {}, 0)

        level = captured[0]["audio_meta"]["level"]
        self.assertGreater(level, 0.45)
        self.assertLess(level, 0.55)


class NativeAudioSessionOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_matching_session_is_stopped(self):
        capture = NativeWindowsAudioCapture()
        capture._session_id = "session-a"
        capture.stop = AsyncMock(return_value={"active": False})

        result = await capture.stop_session("session-a")

        self.assertEqual({"active": False}, result)
        capture.stop.assert_awaited_once()

    async def test_older_session_cannot_stop_a_new_capture(self):
        capture = NativeWindowsAudioCapture()
        capture._session_id = "session-b"
        capture.stop = AsyncMock(return_value={"active": False})

        result = await capture.stop_session("session-a")

        self.assertEqual("session-b", result["session_id"])
        capture.stop.assert_not_awaited()


class _ActiveStream:
    def is_active(self):
        return True


if __name__ == "__main__":
    unittest.main()
