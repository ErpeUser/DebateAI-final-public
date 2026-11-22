"""Rejected local ASR finals cannot survive as another track's coach context."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.objection_handler import DebateRecommendation
from app.services.ordered_transcription import OrderedTranscriptionQueue
from app.ws import audio_handler, audio_pipeline

import tests.test_debate_copilot as copilot_helpers


class RecordingAgent:
    def __init__(self):
        self.windows = []
        self.latest_recommendation = DebateRecommendation()
        self.last_outcome = {"kind": "no_findings", "items": 0}
        self.partial_started = asyncio.Event()
        self.partial_cancelled = asyncio.Event()
        self.release = asyncio.Event()

    async def run_cycle(self, **kwargs):
        text = kwargs["transcript_window"]
        self.windows.append(text)
        if "Abandoned microphone hypothesis" in text and len(self.windows) == 1:
            await kwargs["on_model_partial"](
                DebateRecommendation(
                    answer_now="Guidance from an unconfirmed hypothesis.",
                    target_claim="Abandoned microphone hypothesis",
                    provisional=True,
                )
            )
            self.partial_started.set()
            try:
                await self.release.wait()
            except asyncio.CancelledError:
                self.partial_cancelled.set()
                raise
        self.latest_recommendation = DebateRecommendation()
        return []


class ProvisionalRetirementTests(unittest.IsolatedAsyncioTestCase):
    def orchestrator(self, agent):
        value = copilot_helpers.DebateOrchestratorTests()._orchestrator(agent)
        value.capture_id = "synthetic-capture"
        value._interim_segment_revisions = {}
        value._finalized_interim_segments = set()
        value.privacy_blocked_agents = []
        self.addAsyncCleanup(self.cleanup, value)
        return value

    @staticmethod
    async def cleanup(value):
        task = value._objection_task
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def exercise_pipeline(self, *, raises):
        agent = RecordingAgent()
        orchestrator = self.orchestrator(agent)
        websocket = orchestrator.websocket
        websocket.receive = AsyncMock(
            return_value={"text": '{"type":"stop","drain_mode":"full"}'}
        )
        stream = SimpleNamespace(close=AsyncMock())

        async def flush(track):
            if track == 0:
                if raises:
                    raise RuntimeError("synthetic ASR failure")
                return SimpleNamespace(text="")
            return SimpleNamespace(text="Independent system statement")

        stream.flush = flush

        async def start():
            await stream._on_partial(0, "Abandoned microphone hypothesis")
            await asyncio.wait_for(agent.partial_started.wait(), 1)

        orchestrator.start = start
        emitted = []

        async def emit(speaker, pcm, text, identity):
            emitted.append((text, identity))
            await orchestrator.feed_transcript(
                text,
                "Synthetic",
                utterance_id="system-final",
                provisional_segment_id=identity,
            )

        queue = OrderedTranscriptionQueue(
            AsyncMock(), AsyncMock(), emit_with_identity=emit
        )

        async def worker(frames, diarizer, create, on_segment, on_error, *_rest):
            while (item := await frames.get()) is not None:
                try:
                    await on_segment(
                        item, SimpleNamespace(speaker_id="s", pcm_bytes=b"00")
                    )
                except Exception as error:
                    await on_error(item, error)

        async def finalize(*args, **kwargs):
            await queue.drain()
            agent.release.set()
            if orchestrator._objection_task is not None:
                await asyncio.wait_for(orchestrator._objection_task, 1)

        with (
            patch.object(
                audio_pipeline,
                "register_native_audio_session",
                return_value=asyncio.Queue(),
            ),
            patch.object(audio_pipeline, "unregister_native_audio_session"),
            patch.object(audio_pipeline, "_run_diarization_worker", side_effect=worker),
            patch.object(
                audio_pipeline,
                "native_windows_audio",
                MagicMock(stop_session=AsyncMock()),
            ),
        ):
            await asyncio.wait_for(
                audio_pipeline._run_audio_pipeline(
                    orchestrator.session_id,
                    websocket,
                    False,
                    MagicMock(),
                    orchestrator,
                    queue,
                    MagicMock(),
                    audio_handler._requested_drain_mode,
                    AsyncMock(return_value=None),
                    finalize,
                    streaming_transcriber=stream,
                ),
                3,
            )
        self.assertEqual(
            ["Independent system statement"], [text for text, _ in emitted]
        )
        self.assertEqual({}, orchestrator._interim_debate_hypotheses)
        self.assertTrue(
            agent.partial_cancelled.is_set(), "unconfirmed guidance was not cancelled"
        )
        self.assertGreaterEqual(len(agent.windows), 2)
        self.assertNotIn("Abandoned microphone hypothesis", agent.windows[-1])
        retired = [
            call.args[0]["data"]
            for call in websocket.send_json.await_args_list
            if call.args[0].get("type") == "debate_update"
            and call.args[0]["data"].get("analysis_status") == "cancelled"
        ]
        self.assertTrue(
            retired, "the visible provisional recommendation was not invalidated"
        )
        self.assertEqual("", retired[-1]["answer_now"])

    async def test_empty_mic_final_retires_context_before_system_final(self):
        await self.exercise_pipeline(raises=False)

    async def test_failed_mic_final_retires_context_before_system_final(self):
        await self.exercise_pipeline(raises=True)

    async def test_retirement_is_idempotent_rejects_late_partial_and_stale_card(self):
        agent = RecordingAgent()
        orchestrator = self.orchestrator(agent)
        await orchestrator.feed_interim_transcript(
            "Abandoned microphone hypothesis", utterance_id="mic-1", segment_revision=1
        )
        await asyncio.wait_for(agent.partial_started.wait(), 1)
        old = agent.latest_recommendation.model_copy()
        retire = getattr(orchestrator, "retire_interim_transcript", None)
        self.assertTrue(
            callable(retire), "missing production provisional-retirement contract"
        )
        self.assertTrue(await retire("mic-1"))
        revision = orchestrator._transcript_revision
        self.assertFalse(await retire("mic-1"))
        self.assertEqual(revision, orchestrator._transcript_revision)
        self.assertFalse(
            await orchestrator.feed_interim_transcript(
                "Late replay hypothesis", utterance_id="mic-1", segment_revision=20
            )
        )
        before = orchestrator.websocket.send_json.await_count
        await orchestrator._send_debate_update(1, old, origin="model_stream")
        self.assertEqual(before, orchestrator.websocket.send_json.await_count)
        self.assertEqual(
            "(No recent transcript)",
            await orchestrator.transcript_buffer.get_window(999),
        )

    async def test_retiring_an_old_identity_does_not_cancel_other_active_claim(self):
        agent = RecordingAgent()
        orchestrator = self.orchestrator(agent)
        await orchestrator.feed_interim_transcript(
            "Independent system hypothesis", utterance_id="system-1", segment_revision=1
        )
        await orchestrator._objection_task
        previous = orchestrator._transcript_revision
        task = orchestrator._objection_task
        retire = getattr(orchestrator, "retire_interim_transcript", None)
        self.assertTrue(
            callable(retire), "missing production provisional-retirement contract"
        )
        await retire("mic-1")
        self.assertEqual(
            {"system-1": "Independent system hypothesis"},
            orchestrator._interim_debate_hypotheses,
        )
        self.assertEqual(previous, orchestrator._transcript_revision)
        self.assertIs(task, orchestrator._objection_task)
        self.assertEqual("system-1", orchestrator._active_claim_id)
        self.assertFalse(
            await orchestrator.feed_interim_transcript(
                "Late microphone replay", utterance_id="mic-1", segment_revision=1
            )
        )


if __name__ == "__main__":
    unittest.main()
