import asyncio
import json
import os
import unittest
from unittest import mock

from app.services.asr_backend import (
    ASRBackend,
    NEMO_SPEECH_CPP_VERSION,
    NemotronStreamingASRBackend,
    optional_nemotron_capability,
)
from app.services.local_transcriber import LocalTranscriber, create_transcriber


class _FakeSocket:
    def __init__(self, events):
        self.events = asyncio.Queue()
        for event in events:
            self.events.put_nowait(json.dumps(event))
        self.sent = []
        self.closed = False

    async def recv(self):
        return await self.events.get()

    async def send(self, value):
        self.sent.append(value)
        if isinstance(value, str):
            event = json.loads(value)
            if event["type"] == "session.update":
                self.events.put_nowait(json.dumps({"type": "session.updated"}))
            elif event["type"] == "input_audio_buffer.commit":
                self.events.put_nowait(json.dumps({
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "Der Preis bleibt 10 Euro.",
                    "words": [{"word": "10", "start": 1.0, "end": 1.2}],
                }))
                self.events.put_nowait(json.dumps({"type": "input_audio_buffer.committed"}))

    async def close(self):
        self.closed = True


class _BrokenAfterHandshakeSocket(_FakeSocket):
    async def recv(self):
        if self.events.empty():
            raise ConnectionError("socket dropped")
        return await super().recv()


class _FailCommitSocket(_FakeSocket):
    async def send(self, value):
        if isinstance(value, str) and json.loads(value)["type"] == "input_audio_buffer.commit":
            raise ConnectionError("socket dropped before commit")
        await super().send(value)


class _FakeServerManager:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    async def start(self):
        self.started += 1

    async def stop(self):
        self.stopped += 1


class ASRBackendContractTests(unittest.TestCase):
    def test_default_parakeet_adapter_satisfies_shared_contract(self):
        backend = LocalTranscriber("local-parakeet-tdt-0.6b-v3", language="de")
        self.assertIsInstance(backend, ASRBackend)

    def test_nemotron_is_not_falsely_advertised_without_installed_files(self):
        with mock.patch.dict(
            os.environ,
            {"NEMO_SPEECH_CPP_BIN": "", "NEMOTRON_ASR_MODEL": ""},
            clear=False,
        ):
            capability = optional_nemotron_capability()
        self.assertFalse(capability.available)
        self.assertIn("Not installed", capability.reason)

    def test_installed_capable_and_ready_are_reported_separately(self):
        with (
            mock.patch("app.services.asr_backend.Path.is_file", return_value=True),
            mock.patch(
                "app.services.asr_backend._installed_runtime_version",
                return_value=NEMO_SPEECH_CPP_VERSION,
            ),
            mock.patch(
                "app.services.asr_backend._server_readiness",
                return_value=(False, "server is not running"),
            ),
            mock.patch.dict(
                os.environ,
                {
                    "NEMO_SPEECH_CPP_BIN": "nemo-speech.exe",
                    "NEMOTRON_ASR_MODEL": "nemotron.gguf",
                },
                clear=False,
            ),
        ):
            capability = optional_nemotron_capability()

        self.assertTrue(capability.installed)
        self.assertTrue(capability.capable)
        self.assertFalse(capability.ready)
        self.assertFalse(capability.available)

    def test_factory_selects_nemotron_without_replacing_parakeet_default(self):
        backend = create_transcriber("local-nemotron-nemo-speech-cpp", language="de")
        self.assertIsInstance(backend, NemotronStreamingASRBackend)
        self.assertIsInstance(
            create_transcriber("local-parakeet-tdt-0.6b-v3", language="de"),
            LocalTranscriber,
        )


class NemotronStreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_handshake_error_survives_a_socket_cleanup_error(self):
        socket = _FakeSocket([{"type": "unexpected"}])
        socket.close = mock.AsyncMock(side_effect=OSError("cleanup failed"))

        async def connect(_url):
            return socket

        backend = NemotronStreamingASRBackend(connect=connect, probe_readiness=False)
        with self.assertRaisesRegex(RuntimeError, "Expected session.created"):
            await backend._open_stream("mic")
        socket.close.assert_awaited_once()

    async def test_cancelled_handshake_closes_the_unregistered_socket(self):
        started = asyncio.Event()
        socket = _FakeSocket([])

        async def recv():
            started.set()
            await asyncio.Event().wait()

        socket.recv = recv

        async def connect(_url):
            return socket

        backend = NemotronStreamingASRBackend(connect=connect, probe_readiness=False)
        task = asyncio.create_task(backend._open_stream("mic"))
        try:
            await asyncio.wait_for(started.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(socket.closed)
            self.assertEqual({}, backend._streams)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await backend.close()

    async def test_tracks_keep_independent_streams_and_flush_preserves_metadata(self):
        sockets = []

        async def connect(_url, **_kwargs):
            socket = _FakeSocket([{"type": "session.created"}])
            sockets.append(socket)
            return socket

        backend = NemotronStreamingASRBackend(
            language="de-DE",
            connect=connect,
            probe_readiness=False,
        )
        try:
            await backend.feed_audio(0, b"\x01\x00" * 320)
            await backend.feed_audio(1, b"\x02\x00" * 320)
            mic = await backend.flush(0)
            system = await backend.flush(1)
        finally:
            await backend.close()

        self.assertEqual(2, len(sockets))
        self.assertEqual(b"\x01\x00" * 320, sockets[0].sent[1])
        self.assertEqual(b"\x02\x00" * 320, sockets[1].sent[1])
        self.assertEqual("Der Preis bleibt 10 Euro.", mic.text)
        self.assertEqual("10", mic.words[0]["word"])
        self.assertEqual(0, mic.track)
        self.assertEqual(1, system.track)

    async def test_cancel_clears_only_the_selected_track(self):
        sockets = []

        async def connect(_url, **_kwargs):
            socket = _FakeSocket([{"type": "session.created"}])
            sockets.append(socket)
            return socket

        backend = NemotronStreamingASRBackend(connect=connect, probe_readiness=False)
        await backend.feed_audio(0, b"\x00\x00" * 320)
        await backend.feed_audio(1, b"\x00\x00" * 320)
        await backend.cancel(0)
        self.assertTrue(sockets[0].closed)
        self.assertFalse(sockets[1].closed)
        await backend.close()

    async def test_reconnect_replays_uncommitted_audio_on_the_same_track(self):
        sockets = []

        async def connect(_url, **_kwargs):
            socket_type = _BrokenAfterHandshakeSocket if not sockets else _FakeSocket
            socket = socket_type([{"type": "session.created"}])
            sockets.append(socket)
            return socket

        backend = NemotronStreamingASRBackend(connect=connect, probe_readiness=False)
        first = b"\x01\x00" * 320
        second = b"\x02\x00" * 320
        await backend.feed_audio(0, first)
        await asyncio.sleep(0)
        await backend.feed_audio(0, second)
        replayed = b"".join(value for value in sockets[1].sent if isinstance(value, bytes))
        self.assertEqual(first + second, replayed)
        await backend.close()

    async def test_flush_reconnects_and_commits_replayed_audio(self):
        sockets = []

        async def connect(_url, **_kwargs):
            socket_type = _FailCommitSocket if not sockets else _FakeSocket
            socket = socket_type([{"type": "session.created"}])
            sockets.append(socket)
            return socket

        backend = NemotronStreamingASRBackend(connect=connect, probe_readiness=False)
        audio = b"\x03\x00" * 320
        try:
            await backend.feed_audio(0, audio)
            result = await backend.flush(0)
        finally:
            await backend.close()

        self.assertEqual("Der Preis bleibt 10 Euro.", result.text)
        replayed = b"".join(value for value in sockets[1].sent if isinstance(value, bytes))
        self.assertEqual(audio, replayed)
        self.assertEqual(2, len(sockets))

    async def test_session_switch_discards_both_track_contexts_but_keeps_backend_usable(self):
        sockets = []

        async def connect(_url, **_kwargs):
            socket = _FakeSocket([{"type": "session.created"}])
            sockets.append(socket)
            return socket

        backend = NemotronStreamingASRBackend(connect=connect, probe_readiness=False)
        await backend.switch_session("session-a")
        await backend.feed_audio(0, b"\x00\x00" * 320)
        await backend.feed_audio(1, b"\x00\x00" * 320)
        await backend.switch_session("session-b")
        self.assertTrue(sockets[0].closed)
        self.assertTrue(sockets[1].closed)
        await backend.feed_audio(0, b"\x00\x00" * 320)
        self.assertEqual(3, len(sockets))
        await backend.close()

    async def test_readiness_timeout_stops_owned_server_immediately(self):
        manager = _FakeServerManager()
        backend = NemotronStreamingASRBackend(
            server_manager=manager,
            connect=lambda _url: None,
            event_timeout=0.001,
        )
        with mock.patch(
            "app.services.asr_backend._server_readiness",
            return_value=(False, "still down"),
        ):
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                await backend._check_readiness()

        self.assertEqual(1, manager.started)
        self.assertEqual(1, manager.stopped)

    async def test_owned_server_is_started_for_readiness_and_stopped_on_close(self):
        manager = _FakeServerManager()
        backend = NemotronStreamingASRBackend(
            server_manager=manager,
            connect=lambda _url: None,
        )
        with mock.patch(
            "app.services.asr_backend._server_readiness",
            side_effect=[(False, "down"), (True, "ready")],
        ):
            await backend._check_readiness()
        await backend.close()
        self.assertEqual(1, manager.started)
        self.assertEqual(1, manager.stopped)


if __name__ == "__main__":
    unittest.main()
