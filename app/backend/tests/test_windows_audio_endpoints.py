import os
import unittest
from unittest.mock import patch

from app.services import windows_audio_capture
from app.services.windows_audio_capture import _device_from_info, select_devices


class _Audio:
    def __init__(self, devices):
        self.devices = devices

    def get_device_count(self):
        return len(self.devices)

    def get_device_info_by_index(self, index):
        return self.devices[index]

    def get_default_input_device_info(self):
        return self.devices[0]


class WindowsAudioEndpointTests(unittest.TestCase):
    def test_native_mmdevice_and_stable_ids_are_preferred_when_binding_exposes_them(self):
        device = _device_from_info({
            "index": 3,
            "name": "USB Mic",
            "hostApi": 2,
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
            "deviceUID": "{0.0.1.00000000}.endpoint",
            "stableId": "stable:endpoint",
        })
        self.assertEqual("mmdevice:{0.0.1.00000000}.endpoint", device.endpoint_id)
        self.assertEqual("stable:endpoint", device.stable_id)

    def test_endpoint_id_survives_index_changes(self):
        base = {"name": "USB Mic", "hostApi": 2, "maxInputChannels": 1, "defaultSampleRate": 48000}
        first = _device_from_info({**base, "index": 1})
        second = _device_from_info({**base, "index": 7})
        self.assertEqual(first.endpoint_id, second.endpoint_id)

    def test_mmdevice_lookup_supplies_endpoint_and_stable_identity(self):
        info = {
            "index": 7,
            "name": "USB Mic",
            "hostApi": 2,
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
        }
        with patch.object(
            windows_audio_capture,
            "_resolve_mmdevice_identity",
            return_value=("{0.0.1}.endpoint", "stable:endpoint"),
        ):
            device = _device_from_info(info)

        self.assertEqual("mmdevice:{0.0.1}.endpoint", device.endpoint_id)
        self.assertEqual("stable:endpoint", device.stable_id)

    def test_missing_fixed_endpoint_never_falls_back_to_default(self):
        audio = _Audio([{"index": 0, "name": "Default", "hostApi": 2, "maxInputChannels": 1, "defaultSampleRate": 48000}])
        with self.assertRaisesRegex(OSError, "nicht mehr verfuegbar"):
            select_devices(
                audio,
                microphone_id="wasapi:missing",
                microphone_mode="fixed",
            )

    def test_ambiguous_legacy_id_never_selects_first_identical_device(self):
        base = {
            "name": "Identical USB Mic",
            "hostApi": 2,
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
        }
        devices = [{**base, "index": 0}, {**base, "index": 1}]
        endpoint_id = _device_from_info(devices[0]).endpoint_id
        with self.assertRaisesRegex(OSError, "mehrdeutig"):
            select_devices(
                _Audio(devices),
                microphone_id=endpoint_id,
                microphone_mode="fixed",
            )

    def test_mmdevice_id_resolves_only_to_the_wasapi_capture_path(self):
        if os.name != "nt":
            self.skipTest("WASAPI endpoint selection is Windows-specific")
        base = {
            "name": "USB Mic",
            "maxInputChannels": 1,
            "defaultSampleRate": 48000,
        }
        audio = _Audio([
            {**base, "index": 0, "hostApi": 0},
            {**base, "index": 1, "hostApi": 1},
            {**base, "index": 2, "hostApi": 2},
        ])
        audio.get_host_api_info_by_type = lambda _host_type: {"index": 2}

        def resolve(info, *, loopback=False):
            if info.get("_is_wasapi"):
                return "{0.0.1}.endpoint", "stable:endpoint"
            return "", ""

        with patch.object(windows_audio_capture, "_resolve_mmdevice_identity", side_effect=resolve):
            microphone, _loopback = select_devices(
                audio,
                microphone_id="mmdevice:{0.0.1}.endpoint",
                microphone_mode="fixed",
            )

        self.assertEqual(2, microphone.index)


if __name__ == "__main__":
    unittest.main()
