import asyncio
import unittest

from app.services.local_live_captioner import (
    COMMIT_SECONDS,
    LocalLiveCaptioner,
    is_local_live_model,
)


class FakeTranscriber:
    def __init__(self, model_id):
        self.model_id = model_id
        self.chunks: list[int] = []

    async def transcribe_segment(self, pcm_bytes):
        self.chunks.append(len(pcm_bytes))
        return "hello world"


class SequenceTranscriber:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.chunks: list[int] = []

    async def transcribe_segment(self, pcm_bytes):
        self.chunks.append(len(pcm_bytes))
        return next(self.responses)


class IsLocalLiveModelTests(unittest.TestCase):
    def test_only_the_live_id_matches(self):
        self.assertTrue(is_local_live_model("local-parakeet-live"))
        self.assertFalse(is_local_live_model("local-parakeet-tdt-0.6b"))
        self.assertFalse(is_local_live_model("gemini-3.1-flash-live-preview"))
        self.assertFalse(is_local_live_model(""))


class LocalLiveCaptionerTests(unittest.IsolatedAsyncioTestCase):
    async def test_audio_arriving_during_decode_does_not_move_the_result_span(self):
        started = asyncio.Event()
        release = asyncio.Event()

        class BlockingTranscriber:
            async def transcribe_segment(self, chunk):
                started.set()
                await release.wait()
                return "original chunk"

        cap = self._captioner()
        cap._transcriber = BlockingTranscriber()
        cap.session = True
        await cap.send_audio(b"\x01\x02" * 20000)
        gen = cap.receive_responses()
        pending = asyncio.create_task(anext(gen))
        try:
            await asyncio.wait_for(started.wait(), 2)
            await cap.send_audio(b"\x03\x04" * 16000)
            release.set()
            event = await asyncio.wait_for(pending, 2)
            self.assertEqual(0, event["audio_start_sample"])
            self.assertEqual(20000, event["audio_end_sample"])
            self.assertEqual(32000, len(cap._pending))
        finally:
            release.set()
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
            await cap.close()
            await gen.aclose()

    def test_default_commit_leaves_inference_headroom_for_three_second_first_text(self):
        self.assertLess(COMMIT_SECONDS, 3.0)

    def _captioner(self, commit_seconds=0.02):
        return LocalLiveCaptioner(
            "local-parakeet-live",
            commit_seconds=commit_seconds,
            make_transcriber=FakeTranscriber,
        )

    async def test_explicit_blank_model_is_not_replaced(self):
        self.assertEqual("", LocalLiveCaptioner(model_override="")._asr_model_id)

    async def test_send_audio_trims_to_max(self):
        cap = self._captioner()
        over = cap._max_pending_bytes + 5000
        await cap.send_audio(b"\x00" * over)
        self.assertEqual(len(cap._pending), cap._max_pending_bytes)

    async def test_emits_a_caption_from_the_accumulated_chunk(self):
        cap = self._captioner()
        await cap.connect()
        # >= MIN_COMMIT (1s = 32000 bytes) of non-silent audio.
        await cap.send_audio(b"\x01\x02" * 20000)  # 40000 bytes
        gen = cap.receive_responses()
        try:
            event = await asyncio.wait_for(gen.__anext__(), timeout=2)
        finally:
            await cap.close()
            await gen.aclose()
        self.assertEqual("transcript", event["type"])
        self.assertEqual("hello world", event["data"])
        self.assertEqual("replace", event["mode"])
        self.assertEqual("mixed", event["track_id"])
        self.assertEqual(1, event["segment_revision"])
        self.assertEqual(0, event["audio_start_sample"])
        self.assertEqual(20000, event["audio_end_sample"])
        self.assertTrue(event["segment_id"])
        # The pending buffer was drained by the commit.
        self.assertEqual(len(cap._pending), 0)

    async def test_retranscribes_a_bounded_rolling_window_as_one_replaceable_hypothesis(self):
        cap = self._captioner()
        transcriber = SequenceTranscriber(["erste Hypothese", "erste korrigierte Hypothese"])
        cap._transcriber = transcriber
        cap.session = True
        gen = cap.receive_responses()
        try:
            await cap.send_audio(b"\x01\x02" * 20000)
            first = await asyncio.wait_for(gen.__anext__(), timeout=2)
            await cap.send_audio(b"\x03\x04" * 20000)
            second = await asyncio.wait_for(gen.__anext__(), timeout=2)
        finally:
            await cap.close()
            await gen.aclose()

        self.assertEqual(first["mode"], "replace")
        self.assertEqual(second["data"], "erste korrigierte Hypothese")
        self.assertEqual(transcriber.chunks, [40000, 80000])

    async def test_below_min_chunk_is_not_transcribed(self):
        cap = self._captioner()
        transcriber = FakeTranscriber("x")
        cap._transcriber = transcriber
        cap.session = True
        await cap.send_audio(b"\x00" * 10000)  # < 32000, below MIN_COMMIT
        gen = cap.receive_responses()
        # No event should arrive; the loop keeps waiting.
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(gen.__anext__(), timeout=0.2)
        await cap.close()
        await gen.aclose()
        self.assertEqual(transcriber.chunks, [])  # never transcribed the tiny chunk

    async def test_close_marks_session_gone(self):
        cap = self._captioner()
        await cap.connect()
        self.assertTrue(cap.session)
        await cap.close()
        self.assertIsNone(cap.session)

    async def test_fixed_german_caption_does_not_flash_common_english_greeting(self):
        cap = LocalLiveCaptioner(
            "local-parakeet-v3-live",
            language="de",
            commit_seconds=0.02,
            make_transcriber=lambda _model: SequenceTranscriber(
                ["Yes. Hello, test, test, test."]
            ),
        )
        cap._transcriber = cap._make_transcriber(cap._asr_model_id)
        cap.session = True
        await cap.send_audio(b"\x01\x02" * 20000)
        gen = cap.receive_responses()
        try:
            event = await asyncio.wait_for(gen.__anext__(), timeout=2)
        finally:
            await cap.close()
            await gen.aclose()

        self.assertEqual("Ja. Hallo, test, test, test.", event["data"])

    async def test_fixed_german_caption_suppresses_english_until_german_is_available(self):
        transcriber = SequenceTranscriber(
            ["That's like for Bolton side.", "Das ist die falsche Seite."]
        )
        cap = LocalLiveCaptioner(
            "local-parakeet-v3-live",
            language="de",
            commit_seconds=0.02,
            make_transcriber=lambda _model: transcriber,
        )
        cap._transcriber = transcriber
        cap.session = True
        gen = cap.receive_responses()
        pending = asyncio.create_task(gen.__anext__())
        try:
            await cap.send_audio(b"\x01\x02" * 20000)
            await asyncio.sleep(0.08)
            self.assertFalse(pending.done())
            await cap.send_audio(b"\x03\x04" * 20000)
            event = await asyncio.wait_for(pending, timeout=2)
        finally:
            await cap.close()
            await gen.aclose()

        self.assertEqual("Das ist die falsche Seite.", event["data"])


if __name__ == "__main__":
    unittest.main()
