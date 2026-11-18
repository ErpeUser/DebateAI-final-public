"""Compatibility-module attributes must remain importable for existing callers."""

import unittest

from app import config
from app.services import privacy, privacy_state
from app.ws import audio_handler, audio_persistence, audio_runtime


class ExplicitReexportsTests(unittest.TestCase):
    def test_runtime_handlers_keep_their_historical_names(self):
        names = (
            "_QueuedAudioFrame", "_decode_audio_frame",
            "_new_speaker_registry", "_queued_speaker_auto_id",
            "_receive_websocket_message", "_reconnect_audio_gateway",
            "_record_audio_flow", "_run_diarization_worker",
            "_send_gateway_audio", "_split_track_established_after_frame",
            "_split_track_established_after_message", "_stop_diarization_worker",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(audio_handler, name), getattr(audio_runtime, name))

    def test_persistence_compatibility_alias(self):
        self.assertIs(audio_handler._append_audio_frames, audio_persistence._append_audio_frames)

    def test_settings_and_privacy_compatibility_aliases(self):
        self.assertIs(audio_handler.settings, config.settings)
        self.assertIs(privacy.set_local_only, privacy_state.set_local_only)


if __name__ == "__main__":
    unittest.main()
