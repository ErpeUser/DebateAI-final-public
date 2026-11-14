import asyncio
import hashlib
import sys
import pathlib
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from app.services.calibration_metrics import score_transcript, percentile
from app.services.calibration_runner import compare_asr, SingleFlight, CalibrationBusy
from app.services.diagnostic_audio import read_audio_clip, MAX_UPLOAD_BYTES, AudioInputError


class MetricsTests(unittest.TestCase):
    def test_edit_distance_delegates_to_jiwer(self):
        word_output = SimpleNamespace(substitutions=0, deletions=1, insertions=0, wer=0.5)
        char_output = SimpleNamespace(
            cer=0.25, substitutions=0, deletions=0, insertions=0
        )
        with (
            patch(
                "app.services.calibration_metrics.jiwer.process_words",
                return_value=word_output,
            ) as process_words,
            patch(
                "app.services.calibration_metrics.jiwer.process_characters",
                return_value=char_output,
            ) as process_characters,
        ):
            result = score_transcript("Nein wirklich", "Nein")

        process_words.assert_called_once()
        process_characters.assert_called_once()
        self.assertEqual(1, result["deletions"])
        self.assertEqual(0.5, result["wer"])
        self.assertEqual(0.25, result["cer"])
    def test_perfect_unicode_and_punctuation(self):
        x = score_transcript('Gr\u00fc\u00dfe, Herr M\u00fcller!', 'GR\u00dcSSE Herr Mu\u0308ller')
        self.assertEqual(x['wer'], 0)
        self.assertEqual(x['cer'], 0)

    def test_negation_loss_is_visible(self):
        x = score_transcript('Ich stimme nicht zu', 'Ich stimme zu')
        self.assertEqual(x['deletions'], 1)
        self.assertEqual(x['wer'], .25)
        self.assertEqual(x['critical_reference_tokens'], ['nicht'])
        self.assertEqual(x['false_deletions'], 1)
        self.assertEqual(x['false_deletion_tokens'], ['nicht'])

    def test_decimal_is_not_merged_into_integer(self):
        x = score_transcript('3,5 Prozent', '35 Prozent')
        self.assertEqual(x['substitutions'], 1)
        self.assertGreater(x['wer'], 0)

    def test_number_deletion_is_marked_critical(self):
        x = score_transcript("3,5 Prozent", "Prozent")
        self.assertEqual(1, x["false_deletions"])
        self.assertEqual(["3,5"], x["false_deletion_tokens"])
    def test_negative_number_sign_is_not_discarded(self):
        self.assertGreater(score_transcript("-3,5 Grad", "3,5 Grad")["wer"], 0)

    def test_percent_unit_is_not_discarded(self):
        self.assertGreater(score_transcript("5%", "5")["wer"], 0)

    def test_empty_reference_exposes_hallucinations(self):
        x = score_transcript('', 'Danke f\u00fcrs Zuschauen')
        self.assertIsNone(x['wer'])
        self.assertEqual(x['hallucinated_words'], 3)
        self.assertEqual(score_transcript('', '')['hallucinated_words'], 0)

    def test_insertions_can_exceed_one(self):
        self.assertEqual(score_transcript('ja', 'ja wirklich ganz sicher')['wer'], 3)

    def test_no_text_is_full_deletion_not_pass(self):
        x = score_transcript('Nein wirklich nicht', '')
        self.assertEqual(x['deletions'], 3)
        self.assertEqual(x['wer'], 1)

    def test_oversize_text_is_rejected(self):
        with self.assertRaises(ValueError):
            score_transcript('x' * 4001, 'ok')

    def test_percentiles_validate(self):
        self.assertEqual(percentile([1, 2, 3], .5), 2)
        self.assertIsNone(percentile([], .95))
        with self.assertRaises(ValueError):
            percentile([float('nan')], .5)


class AudioTests(unittest.IsolatedAsyncioTestCase):
    class Upload:
        filename = 'sample.wav'
        def __init__(self, data):
            self.data = data
            self.requested = None
        async def read(self, size):
            self.requested = size
            return self.data[:size]

    async def test_bounded_read_and_decode_in_worker(self):
        import threading
        main = threading.get_ident()
        seen = {}
        def decoder(data, fmt, *, max_seconds):
            seen.update(thread=threading.get_ident(), seconds=max_seconds, fmt=fmt)
            return b'\0\0' * 16000
        upload = self.Upload(b'encoded')
        pcm = await read_audio_clip(upload, decoder, min_seconds=.5, max_seconds=30)
        self.assertEqual(len(pcm), 32000)
        self.assertNotEqual(seen['thread'], main)
        self.assertEqual(upload.requested, MAX_UPLOAD_BYTES + 1)
        self.assertEqual(seen['seconds'], 31)

    async def test_oversize_no_decoder(self):
        called = False
        def decode(*args, **kwargs):
            nonlocal called
            called = True
        with self.assertRaises(AudioInputError) as cm:
            await read_audio_clip(self.Upload(b'x' * (MAX_UPLOAD_BYTES + 1)), decode)
        self.assertEqual(cm.exception.status_code, 413)
        self.assertFalse(called)

    async def test_overlong_pcm_rejected_not_silently_truncated(self):
        with self.assertRaises(AudioInputError):
            await read_audio_clip(self.Upload(b'x'), lambda *a, **k: b'\0\0' * 16000 * 31)

    async def test_malformed_decode_has_no_path_leak(self):
        def decode(*a, **k):
            raise RuntimeError('secret C:/Users/private/key-value')
        with self.assertRaises(AudioInputError) as cm:
            await read_audio_clip(self.Upload(b'x'), decode)
        self.assertNotIn('private', str(cm.exception))

    async def test_unsupported_extension(self):
        upload = self.Upload(b'x')
        upload.filename = 'sample.exe'
        with self.assertRaises(AudioInputError):
            await read_audio_clip(upload, lambda *a, **k: b'')


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_clip_language_repeats_and_failures(self):
        seen = []
        class Transcriber:
            def __init__(self, model):
                self.model = model
            async def transcribe_segment(self, pcm):
                seen.append((self.model, hashlib.sha256(pcm).hexdigest()))
                if self.model == 'broken':
                    raise RuntimeError('private details')
                return 'Ich stimme nicht zu'
        pcm = b'\x01\x00' * 16000
        result = await compare_asr(pcm, 'Ich stimme nicht zu', ['good', 'broken'], 2, Transcriber)
        self.assertEqual(result['attempted_trials'], 4)
        self.assertEqual(result['failed_trials'], 2)
        self.assertEqual(result['models'][0]['trials'][0]['metrics']['wer'], 0)
        self.assertEqual(len({h for _, h in seen}), 1)
        self.assertNotIn('private details', str(result))
        self.assertEqual(result['models'][1]['latency_p50_seconds'], None)

    async def test_empty_recognition_counts_failed_for_speech(self):
        class Empty:
            async def transcribe_segment(self, pcm):
                return None
        x = await compare_asr(b'\0\0' * 16000, 'ja', ['empty'], 1, lambda _: Empty())
        self.assertEqual(x['failed_trials'], 1)
        self.assertEqual(x['models'][0]['trials'][0]['metrics']['wer'], 1)

    async def test_silence_is_a_separate_case(self):
        class Empty:
            async def transcribe_segment(self, pcm):
                return None
        x = await compare_asr(b'\0\0' * 16000, '', ['empty'], 1, lambda _: Empty())
        self.assertEqual(x['failed_trials'], 0)

    async def test_cancellation_keeps_lane_until_physical_job_finishes(self):
        lane = SingleFlight()
        started, finish = asyncio.Event(), asyncio.Event()
        async def job(cancel):
            started.set()
            await finish.wait()
            return {'ok': True}
        first = asyncio.create_task(lane.run(job, timeout=5))
        await started.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertTrue(lane.busy)
        with self.assertRaises(CalibrationBusy):
            await lane.run(job, timeout=5)
        finish.set()
        await asyncio.sleep(.01)
        self.assertFalse(lane.busy)

    async def test_timeout_keeps_lane_until_drained(self):
        lane = SingleFlight()
        release = asyncio.Event()
        async def job(cancel):
            await release.wait()
            return 1
        with self.assertRaises(TimeoutError):
            await lane.run(job, timeout=.01)
        self.assertTrue(lane.busy)
        release.set()
        await asyncio.sleep(.01)
        self.assertFalse(lane.busy)

    async def test_invalid_repetition_is_rejected(self):
        with self.assertRaises(ValueError):
            await compare_asr(b'\0\0' * 16000, 'ja', ['x'], 0, lambda _: None)

if __name__ == '__main__':
    unittest.main()
