"""Later cleanup must not undo durable-byte preservation after archive failures."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app.services.audio_store import (
    SegmentAudioWriter,
    audio_file_path,
    cleanup_orphan_track_audio,
)
from app.ws import audio_pipeline
from app.ws.audio_persistence import _append_audio_frames, _close_audio_writers


class AudioCleanupPreservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for module in ("app.services.audio_store", "app.ws.audio_persistence"):
            replacement = patch(module + ".data_dir", return_value=self.root)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.session = uuid.uuid4()
        self.pcm = b"\x12\x34" * 160

    def archive(self, track="mic"):
        writer = SegmentAudioWriter(self.session, 1, track)
        writer.append(self.pcm)
        writer.close()
        path = audio_file_path(self.session, 1, track)
        return path, path.read_bytes()

    def test_startup_cleanup_preserves_unreferenced_bytes_and_honest_metadata(self):
        path, original = self.archive()
        self.assertEqual(1, cleanup_orphan_track_audio(set()))
        self.assertFalse(path.exists())
        recovered = list((self.root / "audio-recovery").rglob("archive.wav"))
        self.assertEqual(1, len(recovered))
        self.assertEqual(original, recovered[0].read_bytes())
        metadata = json.loads(recovered[0].with_suffix(".json").read_text())
        self.assertEqual("orphan_unverified", metadata["status"])
        self.assertIsNone(metadata["confirmed_pcm_bytes"])
        self.assertEqual(
            path.relative_to(self.root).as_posix(), metadata["original_path"]
        )
        self.assertEqual(0, cleanup_orphan_track_audio(set()))
        self.assertEqual(original, recovered[0].read_bytes())

    def test_cleanup_failure_leaves_original_untouched(self):
        path, original = self.archive()
        with patch(
            "app.services.audio_store.tempfile.mkdtemp",
            side_effect=PermissionError("injected"),
        ):
            self.assertEqual(0, cleanup_orphan_track_audio(set()))
        self.assertEqual(original, path.read_bytes())

    def test_failed_append_and_failed_quarantine_survive_later_cleanup(self):
        writer = SegmentAudioWriter(self.session, 1, "mic")
        writer.append(self.pcm)
        path = audio_file_path(self.session, 1, "mic")
        writers = {"mixed": None, "mic": writer, "system": None}
        with (
            patch.object(
                writer, "append", side_effect=OSError("injected append failure")
            ),
            patch.object(
                writer,
                "quarantine_failed_archive",
                side_effect=PermissionError("injected quarantine failure"),
            ),
        ):
            _append_audio_frames(writers, (b"", self.pcm, b""))
        self.assertIsNone(writers["mic"])
        original = path.read_bytes()
        cleanup_orphan_track_audio(set())
        survivors = [candidate.read_bytes() for candidate in self.root.rglob("*.wav")]
        self.assertIn(original, survivors)
        self.assertTrue(original.endswith(self.pcm))

    def test_missing_mixed_archive_retains_valid_auxiliary_paths_before_split(self):
        mic = SegmentAudioWriter(self.session, 1, "mic")
        system = SegmentAudioWriter(self.session, 1, "sys")
        mic.append(self.pcm)
        system.append(b"\x00\x00" * 160)
        paths = _close_audio_writers(
            {"mixed": None, "mic": mic, "system": system}, False
        )
        self.assertIsNone(paths["audio_path"])
        self.assertIsNotNone(paths["mic_audio_path"])
        self.assertIsNotNone(paths["system_audio_path"])
        self.assertTrue(
            (self.root / paths["mic_audio_path"]).read_bytes().endswith(self.pcm)
        )
        cleanup_orphan_track_audio({p for p in paths.values() if p})
        self.assertTrue((self.root / paths["mic_audio_path"]).exists())

    def test_referenced_and_mixed_archives_are_not_quarantined(self):
        mic, mic_bytes = self.archive("mic")
        mixed, mixed_bytes = self.archive("mixed")
        self.assertEqual(
            0, cleanup_orphan_track_audio({str(mic.relative_to(self.root))})
        )
        self.assertEqual(mic_bytes, mic.read_bytes())
        self.assertEqual(mixed_bytes, mixed.read_bytes())
        self.assertFalse((self.root / "audio-recovery").exists())

    def test_metadata_write_failure_keeps_audio_recoverable(self):
        _path, original = self.archive()
        with patch(
            "app.services.audio_store.json.dump",
            side_effect=OSError("injected metadata failure"),
        ):
            cleanup_orphan_track_audio(set())
        self.assertIn(
            original, [candidate.read_bytes() for candidate in self.root.rglob("*.wav")]
        )

    def test_pipeline_shutdown_tail_writer_helper_is_bound_and_preserves_pcm(self):
        # The pipeline's finally block must bind this function. A missing
        # import previously raised NameError, which cleanup swallowed.
        self.assertIs(audio_pipeline._append_audio_frames, _append_audio_frames)
        writer = SegmentAudioWriter(self.session, 9, "mic")
        tail = b"\x47\x48" * 16
        writers = {"mixed": None, "mic": writer, "system": None}
        audio_pipeline._append_audio_frames(writers, (b"", tail, b""), True)
        path = audio_file_path(self.session, 9, "mic")
        writer.close()
        self.assertTrue(path.is_file())
        self.assertTrue(path.read_bytes().endswith(tail))


if __name__ == "__main__":
    unittest.main()
