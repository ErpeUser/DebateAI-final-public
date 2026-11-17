"""Already accepted archived audio must survive a later append failure."""
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from app.services.audio_store import SegmentAudioWriter, audio_file_path, cleanup_orphan_track_audio
from app.ws.audio_persistence import _append_audio_frames, _close_audio_writers


class ArchiveFailurePreservationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for target in ('app.services.audio_store.data_dir', 'app.ws.audio_persistence.data_dir'):
            context = patch(target, return_value=self.root)
            context.start()
            self.addCleanup(context.stop)
        self.session = uuid.uuid4()

    def test_later_append_failure_preserves_confirmed_pcm_outside_orphan_cleanup(self):
        mixed = SegmentAudioWriter(self.session, 1)
        mic = SegmentAudioWriter(self.session, 1, track='mic')
        accepted = b'\x01\x02' * 16
        mic.append(accepted)
        writers = {'mixed': mixed, 'mic': mic, 'system': None}
        with patch.object(mic, 'append', side_effect=OSError('injected disk failure')):
            _append_audio_frames(writers, (b'\x03\x04', b'\x05\x06', b''))
        self.assertIsNone(writers['mic'])
        self.assertIs(mixed, writers['mixed'])
        mixed.close()
        recovered = list((self.root / 'audio-recovery').glob('*/*.wav'))
        self.assertEqual(1, len(recovered), 'An append error deleted previously accepted PCM')
        self.assertEqual(accepted, recovered[0].read_bytes()[44:])
        cleanup_orphan_track_audio(set())
        self.assertTrue(recovered[0].exists())
        metadata = json.loads(recovered[0].with_suffix('.json').read_text())
        self.assertEqual(32, metadata['confirmed_pcm_bytes'])
        self.assertEqual('incomplete_not_accepted', metadata['status'])

    def test_failed_final_fsync_does_not_delete_the_archive(self):
        writer = SegmentAudioWriter(self.session, 2, track='mic')
        accepted = b'\x01\x02' * 16
        writer.append(accepted)
        writers = {'mixed': None, 'mic': writer, 'system': None}
        with patch('app.services.audio_store.os.fsync', side_effect=OSError('disk unavailable')):
            _append_audio_frames(writers, (b'', b'\x03\x04', b''))
        candidates = list((self.root / 'audio-recovery').glob('*/*.wav'))
        self.assertEqual(1, len(candidates))
        self.assertEqual(accepted, candidates[0].read_bytes()[44:76])
        self.assertIsNone(writer._file)
        self.assertIsNone(writers['mic'])

    def test_finalization_failure_is_kept_out_of_auxiliary_cleanup(self):
        writer = SegmentAudioWriter(self.session, 5, track='mic')
        writer.append(b'\x01\x02' * 8)
        with patch('app.services.audio_store.os.fsync', side_effect=OSError('final fsync failed')):
            paths = _close_audio_writers({'mixed': None, 'mic': writer, 'system': None}, True)
        self.assertIsNone(paths['mic_audio_path'])
        cleanup_orphan_track_audio(set())
        candidates = list((self.root / 'audio-recovery').glob('*/*.wav'))
        self.assertEqual(1, len(candidates))
        self.assertEqual(b'\x01\x02' * 8, candidates[0].read_bytes()[44:])

    def test_collision_cannot_quarantine_another_writers_archive(self):
        first = SegmentAudioWriter(self.session, 3)
        first.append(b'\x01\x02' * 4)
        first.close()
        path = audio_file_path(self.session, 3)
        saved = path.read_bytes()
        second = SegmentAudioWriter(self.session, 3)
        writers = {'mixed': second, 'mic': None, 'system': None}
        _append_audio_frames(writers, (b'\x03\x04', b'', b''))
        self.assertEqual(saved, path.read_bytes())
        self.assertEqual([], list((self.root / 'audio-recovery').glob('*/*.wav')))

    def test_quarantine_is_idempotent_and_writer_cannot_restart(self):
        writer = SegmentAudioWriter(self.session, 4)
        writer.append(b'\x01\x02')
        method = getattr(writer, 'quarantine_failed_archive', None)
        self.assertTrue(callable(method), 'Failure quarantine is missing')
        relative = method()
        self.assertEqual(relative, method())
        self.assertTrue((self.root / relative).exists())
        with self.assertRaises(RuntimeError): writer.append(b'\x03\x04')


if __name__ == '__main__':
    unittest.main()
