import asyncio
import importlib
import importlib.util
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class StreamingProvisionalRelayTests(unittest.IsolatedAsyncioTestCase):
    def relay(self, callback, **kwargs):
        name = "app.ws.streaming_provisional"
        self.assertIsNotNone(
            importlib.util.find_spec(name),
            "local streaming has no shared provisional relay",
        )
        cls = importlib.import_module(name).StreamingProvisionalRelay
        value = cls(callback, capture_id="synthetic-capture", interval=0.01, **kwargs)
        self.addAsyncCleanup(value.close)
        return value

    async def test_deltas_are_coalesced_and_forwarded_as_one_full_hypothesis(self):
        callback = AsyncMock()
        relay = self.relay(callback)
        first = relay.append(0, "Das ist ")
        second = relay.append(0, "nicht richtig.")
        await asyncio.sleep(0.04)
        callback.assert_awaited_once_with(
            "Das ist nicht richtig.", utterance_id=first[0], segment_revision=2
        )
        self.assertEqual(first[0], second[0])

    async def test_tracks_do_not_share_hypotheses_or_ids(self):
        callback = AsyncMock()
        relay = self.relay(callback)
        mic = relay.append(0, "Microphone statement")
        system = relay.append(1, "System statement")
        await asyncio.sleep(0.04)
        self.assertNotEqual(mic[0], system[0])
        callback.assert_any_await(
            "Microphone statement", utterance_id=mic[0], segment_revision=1
        )
        callback.assert_any_await(
            "System statement", utterance_id=system[0], segment_revision=1
        )

    async def test_finalize_cancels_pending_provisional_and_returns_its_exact_id(self):
        callback = AsyncMock()
        relay = self.relay(callback)
        segment, _revision = relay.append(0, "Old hypothesis")
        self.assertEqual(segment, await relay.finalize(0))
        fresh = relay.append(0, "New hypothesis")
        await asyncio.sleep(0.04)
        self.assertNotEqual(segment, fresh[0])
        self.assertEqual(1, fresh[1])
        callback.assert_awaited_once_with(
            "New hypothesis", utterance_id=fresh[0], segment_revision=1
        )

    async def test_close_prevents_late_work(self):
        callback = AsyncMock()
        relay = self.relay(callback)
        relay.append(0, "Pending hypothesis")
        await relay.close()
        await asyncio.sleep(0.03)
        callback.assert_not_awaited()
        with self.assertRaises(RuntimeError):
            relay.append(0, "Late hypothesis")

    async def test_callback_failure_does_not_disable_later_context(self):
        callback = AsyncMock(side_effect=[RuntimeError("synthetic"), None])
        relay = self.relay(callback)
        relay.append(0, "First context")
        await asyncio.sleep(0.04)
        relay.append(0, " and more")
        await asyncio.sleep(0.04)
        self.assertEqual(2, callback.await_count)
        self.assertEqual("First context and more", callback.await_args.args[0])

    async def test_text_and_pending_work_are_bounded(self):
        callback = AsyncMock()
        relay = self.relay(callback, max_chars=20)
        for _ in range(200):
            relay.append(0, "a")
        await asyncio.sleep(0.04)
        self.assertEqual(1, callback.await_count)
        self.assertEqual(20, len(callback.await_args.args[0]))
        with self.assertRaises(ValueError):
            relay.append(3, "not a known track")

    async def test_new_delta_during_delivery_is_not_lost(self):
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def deliver(text, **kwargs):
            calls.append((text, kwargs))
            if len(calls) == 1:
                started.set()
                await release.wait()

        relay = self.relay(deliver)
        relay.append(0, "First ")
        await asyncio.wait_for(started.wait(), 0.5)
        relay.append(0, "second")
        release.set()
        await asyncio.sleep(0.05)
        self.assertEqual(["First ", "First second"], [text for text, _ in calls])


class QueuedProvisionalIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_identity_is_bound_to_each_result_not_last_active_track(self):
        import inspect

        from app.services.ordered_transcription import OrderedTranscriptionQueue

        self.assertIn(
            "emit_with_identity",
            inspect.signature(OrderedTranscriptionQueue).parameters,
        )
        seen = []

        async def emit(speaker, pcm, text, identity):
            seen.append((speaker, text, identity))

        queue = OrderedTranscriptionQueue(
            AsyncMock(), AsyncMock(), emit_with_identity=emit
        )
        await queue.add_result("mic", b"aa", "First", provisional_segment_id="mic-1")
        await queue.add_result("sys", b"bb", "Second", provisional_segment_id="sys-9")
        await queue.drain()
        self.assertEqual([("mic", "First", "mic-1"), ("sys", "Second", "sys-9")], seen)


class PipelineProvisionalIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_pipeline_forwards_partials_and_tags_each_queued_final(self):
        import uuid
        from types import SimpleNamespace

        from app.ws import audio_handler, audio_pipeline

        stream = SimpleNamespace(
            flush=AsyncMock(
                side_effect=lambda track: SimpleNamespace(text=f"Final {track}")
            ),
            close=AsyncMock(),
        )
        orchestrator = MagicMock(
            start=AsyncMock(),
            privacy_blocked_agents=[],
            capture_id="capture",
            feed_interim_transcript=AsyncMock(),
        )

        async def start():
            await stream._on_partial(0, "Das ist ")
            await stream._on_partial(0, "nicht richtig.")
            await stream._on_partial(1, "Eine zweite Aussage.")
            await asyncio.sleep(0.35)

        orchestrator.start.side_effect = start
        websocket = MagicMock(
            send_json=AsyncMock(),
            receive=AsyncMock(
                return_value={"text": '{"type":"stop","drain_mode":"full"}'}
            ),
        )
        queue = MagicMock(add_result=AsyncMock())

        async def worker(frames, diarizer, create, on_segment, *rest):
            while (item := await frames.get()) is not None:
                await on_segment(item, SimpleNamespace(speaker_id="s", pcm_bytes=b"00"))

        native = MagicMock(stop_session=AsyncMock())
        with (
            patch.object(
                audio_pipeline,
                "register_native_audio_session",
                return_value=asyncio.Queue(),
            ),
            patch.object(audio_pipeline, "unregister_native_audio_session"),
            patch.object(audio_pipeline, "_run_diarization_worker", side_effect=worker),
            patch.object(audio_pipeline, "native_windows_audio", native),
        ):
            await asyncio.wait_for(
                audio_pipeline._run_audio_pipeline(
                    uuid.uuid4(),
                    websocket,
                    False,
                    MagicMock(),
                    orchestrator,
                    queue,
                    MagicMock(),
                    audio_handler._requested_drain_mode,
                    AsyncMock(return_value=None),
                    AsyncMock(),
                    streaming_transcriber=stream,
                ),
                timeout=2,
            )
        partials = [
            call.args[0]["data"]
            for call in websocket.send_json.await_args_list
            if call.args[0].get("type") == "interim_transcript"
        ]
        self.assertEqual(2, orchestrator.feed_interim_transcript.await_count)
        for track, text in ((0, "Das ist nicht richtig."), (1, "Eine zweite Aussage.")):
            identity = next(
                item["segment_id"] for item in partials if item["track"] == track
            )
            orchestrator.feed_interim_transcript.assert_any_await(
                text, utterance_id=identity, segment_revision=2 if track == 0 else 1
            )
            matches = [
                call
                for call in queue.add_result.await_args_list
                if call.args[2] == f"Final {track}"
            ]
            self.assertEqual(identity, matches[0].kwargs["provisional_segment_id"])
        stream.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
