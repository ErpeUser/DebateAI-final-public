import asyncio
import unittest
import uuid

from app.services.ws_event_stream import ClientSendBuffer, SessionEventJournal


class SessionEventJournalTests(unittest.TestCase):
    def test_snapshot_exposes_server_epoch(self):
        journal = SessionEventJournal("session")

        snapshot = journal.snapshot()

        self.assertTrue(snapshot["data"]["server_epoch"])

    def test_old_epoch_cursor_forces_full_snapshot_after_restart(self):
        previous = SessionEventJournal("session")
        restarted = SessionEventJournal("session")
        restarted.record({"type": "transcript", "data": {"id": "new", "text": "Neu"}})

        snapshot = restarted.snapshot(
            after_sequence=1,
            after_epoch=previous.server_epoch,
        )

        self.assertTrue(snapshot["data"]["full"])
        self.assertEqual(["new"], [event["data"]["id"] for event in snapshot["data"]["events"]])

    def test_sequences_are_monotone_and_replay_only_returns_newer_events(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=8)

        first = journal.record({"type": "status", "data": {"state": "ready"}})
        second = journal.record({"type": "transcript", "data": {"id": "t1", "text": "Hallo"}})

        self.assertEqual(1, first["session_sequence"])
        self.assertEqual(2, second["session_sequence"])
        snapshot = journal.snapshot(after_sequence=1)
        self.assertFalse(snapshot["data"]["full"])
        self.assertEqual([2], [event["session_sequence"] for event in snapshot["data"]["events"]])

    async def _reverse_commit_delta_fixture(self):
        journal = SessionEventJournal("reverse-commit")
        baseline = journal.record({"type": "status", "data": {"state": "ready"}})
        release_a = asyncio.Event()
        committed_b = asyncio.Event()

        async def writer_a():
            await release_a.wait()
            return journal.record({"type": "transcript", "data": {"id": "a", "text": "A"}})

        async def writer_b():
            event = journal.record({"type": "transcript", "data": {"id": "b", "text": "B"}})
            committed_b.set()
            return event

        task_a = asyncio.create_task(writer_a())
        task_b = asyncio.create_task(writer_b())
        await committed_b.wait()
        delta = journal.snapshot(after_sequence=baseline["session_sequence"])
        release_a.set()
        event_a, event_b = await asyncio.gather(task_a, task_b)
        return journal, delta, event_a, event_b

    def test_reverse_commit_order_keeps_delta_cursor_and_late_writer_replayable(self):
        journal, delta, event_a, event_b = asyncio.run(self._reverse_commit_delta_fixture())

        self.assertEqual([event_b["session_sequence"]], [event["session_sequence"] for event in delta["data"]["events"]])
        follow_up = journal.snapshot(after_sequence=delta["data"]["through_sequence"])
        self.assertEqual([event_a["session_sequence"]], [event["session_sequence"] for event in follow_up["data"]["events"]])

    def test_new_connection_generation_supersedes_old_sender(self):
        journal = SessionEventJournal(uuid.uuid4())
        old_generation = journal.open_generation()
        new_generation = journal.open_generation()

        self.assertFalse(journal.is_current_generation(old_generation))
        self.assertTrue(journal.is_current_generation(new_generation))

    def test_full_snapshot_keeps_latest_state_and_final_transcripts(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=2, max_state_events=8)
        journal.record({"type": "status", "data": {"state": "ready"}})
        journal.record({"type": "transcript", "data": {"id": "t1", "text": "Erster Satz"}})
        journal.record({"type": "debate_update", "data": {"claim_id": "c1", "answer_now": "Antwort"}})

        snapshot = journal.snapshot(after_sequence=0)
        event_types = [event["type"] for event in snapshot["data"]["events"]]

        self.assertTrue(snapshot["data"]["full"])
        self.assertIn("status", event_types)
        self.assertIn("transcript", event_types)
        self.assertIn("debate_update", event_types)
        self.assertEqual([1, 2, 3], [event["session_sequence"] for event in snapshot["data"]["events"]])

    def test_interim_revisions_are_coalesced_in_snapshot_state(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=1, max_state_events=8)
        journal.record({
            "type": "interim_transcript",
            "data": {"segment_id": "s1", "segment_revision": 1, "text": "Alt"},
        })
        journal.record({
            "type": "interim_transcript",
            "data": {"segment_id": "s1", "segment_revision": 2, "text": "Neu"},
        })

        events = journal.snapshot(after_sequence=0)["data"]["events"]

        self.assertEqual(1, len(events))
        self.assertEqual("Neu", events[0]["data"]["text"])
        self.assertEqual(2, events[0]["session_sequence"])

    def test_append_interims_accumulate_before_coalescing(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=1, max_state_events=8)
        journal.record({
            "type": "interim_transcript",
            "data": {"segment_id": "s1", "segment_revision": 1, "mode": "append", "text": "Nicht "},
        })
        latest = journal.record({
            "type": "interim_transcript",
            "data": {"segment_id": "s1", "segment_revision": 2, "mode": "append", "text": "zustimmen."},
        })

        self.assertEqual("zustimmen.", latest["data"]["text"])
        self.assertEqual("append", latest["data"]["mode"])
        events = journal.snapshot(after_sequence=0)["data"]["events"]
        self.assertEqual(["Nicht zustimmen."], [event["data"]["text"] for event in events])

    def test_full_snapshot_keeps_transcript_creation_before_its_update(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=1, max_state_events=8)
        journal.record({"type": "transcript", "data": {"id": "t1", "text": "Original"}})
        journal.record({"type": "transcript_updated", "data": {"id": "t1", "text": "Korrigiert"}})

        events = journal.snapshot(after_sequence=0)["data"]["events"]

        self.assertEqual(["transcript", "transcript_updated"], [event["type"] for event in events])

    def test_incremental_snapshot_drops_superseded_completed_status(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=8, max_state_events=8)
        journal.record({"type": "transcript", "data": {"id": "t1", "text": "Eins"}})
        journal.record({"type": "status", "data": {"state": "completed"}})
        journal.record({"type": "status", "data": {"state": "connecting"}})

        events = journal.snapshot(after_sequence=1)["data"]["events"]
        self.assertEqual(["connecting"], [
            event["data"]["state"] for event in events if event["type"] == "status"
        ])

    def test_live_audio_levels_keep_only_the_latest_value_per_track(self):
        journal = SessionEventJournal(uuid.uuid4(), max_events=1, max_state_events=8)
        journal.record({"type": "audio_level", "data": {"track": 0, "level": 0.2}})
        journal.record({"type": "audio_level", "data": {"track": 1, "level": 0.4}})
        journal.record({"type": "audio_level", "data": {"track": 0, "level": 0.8}})

        events = journal.snapshot(after_sequence=0)["data"]["events"]

        self.assertEqual(2, len(events))
        by_track = {event["data"]["track"]: event["data"]["level"] for event in events}
        self.assertEqual({0: 0.8, 1: 0.4}, by_track)


class ClientSendBufferTests(unittest.IsolatedAsyncioTestCase):
    async def test_replaces_stale_interim_for_the_same_segment(self):
        buffer = ClientSendBuffer(maxsize=2)

        await buffer.put({"type": "interim_transcript", "data": {"segment_id": "s1", "text": "Alt"}})
        await buffer.put({"type": "interim_transcript", "data": {"segment_id": "s1", "text": "Neu"}})

        self.assertEqual(1, buffer.qsize())
        self.assertEqual("Neu", (await buffer.get())["data"]["text"])

    async def test_replaces_stale_audio_level_for_the_same_track(self):
        buffer = ClientSendBuffer(maxsize=2)

        await buffer.put({"type": "audio_level", "data": {"track": 0, "level": 0.2}})
        await buffer.put({"type": "audio_level", "data": {"track": 0, "level": 0.7}})

        self.assertEqual(1, buffer.qsize())
        self.assertEqual(0.7, (await buffer.get())["data"]["level"])

    async def test_wrapped_interims_keep_distinct_segments(self):
        buffer = ClientSendBuffer(maxsize=3)
        await buffer.put({
            "type": "interim_transcript",
            "payload": {"type": "interim_transcript", "data": {"segment_id": "s1", "text": "Eins"}},
        })
        await buffer.put({
            "type": "interim_transcript",
            "payload": {"type": "interim_transcript", "data": {"segment_id": "s2", "text": "Zwei"}},
        })

        self.assertEqual(2, buffer.qsize())

    async def test_final_overflow_returns_immediately_and_requests_snapshot_resync(self):
        buffer = ClientSendBuffer(maxsize=1)
        await buffer.put({"type": "status", "data": {"state": "ready"}})

        accepted = await asyncio.wait_for(
            buffer.put({"type": "transcript", "data": {"id": "t1", "text": "Final"}}),
            timeout=0.05,
        )

        self.assertFalse(accepted)
        self.assertTrue(buffer.needs_resync)
        self.assertEqual("status", (await buffer.get())["type"])

    async def test_snapshot_replacement_discards_stale_delivery_backlog(self):
        buffer = ClientSendBuffer(maxsize=2)
        await buffer.put({"type": "status", "data": {"state": "ready"}})
        await buffer.put({"type": "transcript", "data": {"id": "old", "text": "Alt"}})
        self.assertFalse(await asyncio.wait_for(
            buffer.put({"type": "transcript", "data": {"id": "new", "text": "Neu"}}),
            timeout=0.05,
        ))

        await buffer.replace_with_snapshot({
            "type": "session_snapshot",
            "data": {"through_sequence": 3, "events": [{"type": "transcript", "data": {"id": "new"}}]},
        })

        self.assertFalse(buffer.needs_resync)
        self.assertEqual("session_snapshot", (await buffer.get())["type"])
        self.assertEqual(0, buffer.qsize())

    async def test_interim_is_dropped_when_only_final_events_fill_the_buffer(self):
        buffer = ClientSendBuffer(maxsize=1)
        await buffer.put({"type": "transcript", "data": {"id": "t1", "text": "Final"}})

        accepted = await buffer.put(
            {"type": "interim_transcript", "data": {"segment_id": "s1", "text": "Zwischenstand"}}
        )

        self.assertFalse(accepted)
        self.assertEqual(1, buffer.qsize())
        self.assertEqual("transcript", (await buffer.get())["type"])


if __name__ == "__main__":
    unittest.main()
