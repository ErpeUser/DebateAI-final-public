"""Archive regressions: real temporary files, no microphone/model required."""
import struct
import tempfile
import unittest
import uuid
import wave
from pathlib import Path
from unittest.mock import patch

from app.services.audio_store import SegmentAudioWriter, audio_file_path, repair_wav_file


def header() -> bytes:
    # Independent on-disk fixture: RIFF, PCM16, mono, 16000 Hz, empty size fields.
    return struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36, b'WAVE', b'fmt ',
                       16, 1, 1, 16000, 32000, 2, 16, b'data', 0)


class AudioRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = self.root / 'interrupted.wav'

    def assert_untouched_rejection(self, content):
        self.file.write_bytes(content)
        self.assertFalse(repair_wav_file(self.file))
        self.assertEqual(content, self.file.read_bytes())

    def test_recovery_rejects_foreign_or_malformed_format_without_rewriting(self):
        changes = [(0, b'RF64'), (8, b'NOPE'), (12, b'JUNK'),
                   (16, struct.pack('<I', 18)), (20, struct.pack('<H', 3)),
                   (22, struct.pack('<H', 2)), (24, struct.pack('<I', 48000)),
                   (28, struct.pack('<I', 1)), (32, struct.pack('<H', 4)),
                   (34, struct.pack('<H', 8)), (36, b'JUNK')]
        for offset, replacement in changes:
            with self.subTest(offset=offset):
                content = bytearray(header() + b'\x01\x02' * 8)
                content[offset:offset + len(replacement)] = replacement
                self.assert_untouched_rejection(bytes(content))

    def test_recovery_rejects_incomplete_pcm_sample_without_rewriting(self):
        self.assert_untouched_rejection(header() + b'\x01\x02\xff')

    def test_recovery_rejects_short_header(self):
        self.assert_untouched_rejection(header()[:43])

    def test_recovery_repairs_only_sizes_and_preserves_pcm(self):
        pcm = b'\x01\x02' * 160
        self.file.write_bytes(header() + pcm)
        self.assertTrue(repair_wav_file(self.file))
        content = self.file.read_bytes()
        self.assertEqual(356, struct.unpack_from('<I', content, 4)[0])
        self.assertEqual(320, struct.unpack_from('<I', content, 40)[0])
        self.assertEqual(header()[8:40], content[8:40])
        self.assertEqual(pcm, content[44:])
        with wave.open(str(self.file), 'rb') as wav:
            self.assertEqual((1, 2, 16000, 160),
                             (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()))
            self.assertEqual(pcm, wav.readframes(160))
        self.assertTrue(repair_wav_file(self.file))
        self.assertEqual(content, self.file.read_bytes())

    def test_recovery_does_not_follow_symlink(self):
        target = self.root / 'target.wav'
        original = header() + b'\x01\x02' * 8
        target.write_bytes(original)
        try:
            self.file.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('Symlink creation unavailable on this host')
        self.assertFalse(repair_wav_file(self.file))
        self.assertEqual(original, target.read_bytes())

    def test_missing_file_is_not_created(self):
        self.assertFalse(repair_wav_file(self.file))
        self.assertFalse(self.file.exists())

    def test_directory_is_not_a_recoverable_file(self):
        self.assertFalse(repair_wav_file(self.root))


class AudioWriterLifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        override = patch('app.services.audio_store.data_dir', return_value=self.root)
        override.start()
        self.addCleanup(override.stop)
        self.session = uuid.uuid4()

    def test_append_after_close_cannot_truncate_accepted_audio(self):
        writer = SegmentAudioWriter(self.session, 1)
        writer.append(b'\x01\x02' * 10)
        writer.close()
        path = audio_file_path(self.session, 1)
        saved = path.read_bytes()
        try:
            with self.assertRaises(RuntimeError):
                writer.append(b'\x03\x04')
            self.assertEqual(saved, path.read_bytes())
        finally:
            if writer._file is not None:
                writer._file.close()

    def test_second_writer_cannot_replace_existing_archive(self):
        first = SegmentAudioWriter(self.session, 1)
        first.append(b'\x01\x02' * 10)
        first.close()
        path = audio_file_path(self.session, 1)
        saved = path.read_bytes()
        second = SegmentAudioWriter(self.session, 1)
        try:
            with self.assertRaises(FileExistsError):
                second.append(b'\x03\x04')
            self.assertEqual(saved, path.read_bytes())
        finally:
            if second._file is not None:
                second._file.close()

    def test_close_fsync_failure_still_releases_descriptor(self):
        writer = SegmentAudioWriter(self.session, 1)
        writer.append(b'\x01\x02' * 10)
        handle = writer._file
        try:
            with patch('app.services.audio_store.os.fsync', side_effect=OSError('injected fsync failure')):
                with self.assertRaises(OSError):
                    writer.close()
            self.assertTrue(handle.closed)
            with self.assertRaises(RuntimeError):
                writer.append(b'\x03\x04')
            self.assertTrue(repair_wav_file(audio_file_path(self.session, 1)))
        finally:
            handle.close()

    def test_closed_empty_writer_cannot_restart(self):
        writer = SegmentAudioWriter(self.session, 1)
        self.assertIsNone(writer.close())
        try:
            with self.assertRaises(RuntimeError):
                writer.append(b'\x01\x02')
            self.assertFalse(audio_file_path(self.session, 1).exists())
        finally:
            if writer._file is not None:
                writer._file.close()


if __name__ == '__main__':
    unittest.main()
