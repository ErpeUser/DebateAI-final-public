import assert from "node:assert/strict";
import { test } from "node:test";
import {
  mergeSocketEvents,
  processedSocketSequence,
  shouldResetMessageCursor,
  shouldResetForServerEpoch,
  shouldReconnectVisibleSession,
  socketPayloadEvents,
  stageSocketPayload,
} from "./wsEventStream.ts";

test("a changed server epoch resets a stale reconnect cursor", () => {
  assert.equal(shouldResetForServerEpoch("", "epoch-a"), false);
  assert.equal(shouldResetForServerEpoch("epoch-a", "epoch-a"), false);
  assert.equal(shouldResetForServerEpoch("epoch-a", "epoch-b"), true);
});

test("resume keeps cursors while a real session switch resets them", () => {
  assert.equal(shouldResetMessageCursor("", "s1"), false);
  assert.equal(shouldResetMessageCursor("s1", "s1"), false);
  assert.equal(shouldResetMessageCursor("s2", "s1"), true);
});

test("visibility recovery leaves open and connecting sockets alone", () => {
  assert.equal(shouldReconnectVisibleSession("visible", "s1", true, 1), false);
  assert.equal(shouldReconnectVisibleSession("visible", "s1", true, 0), false);
  assert.equal(shouldReconnectVisibleSession("visible", "s1", true, 3), true);
  assert.equal(shouldReconnectVisibleSession("hidden", "s1", true, 3), false);
  assert.equal(shouldReconnectVisibleSession("visible", "", true, 3), false);
  assert.equal(shouldReconnectVisibleSession("visible", "s1", false, 3), false);
});

test("reconnect snapshots expand into their sequenced events", () => {
  const events = socketPayloadEvents({
    type: "session_snapshot",
    data: {
      session_id: "s1",
      through_sequence: 4,
      full: true,
      events: [
        { type: "status", data: { state: "ready" }, session_sequence: 1, event_id: 1 },
        { type: "debate_update", data: { answer_now: "Antwort" }, session_sequence: 4, event_id: 4 },
      ],
    },
  });

  assert.deepEqual(events.map((event) => event.session_sequence), [1, 4]);
});

test("duplicates are ignored and stale interim revisions are coalesced", () => {
  const first = { type: "interim_transcript", data: { segment_id: "a", text: "Alt" }, session_sequence: 1, event_id: 1 };
  const newer = { type: "interim_transcript", data: { segment_id: "a", text: "Neu" }, session_sequence: 2, event_id: 2 };
  const merged = mergeSocketEvents([first], [first, newer], 10);

  assert.equal(merged.length, 1);
  assert.equal(merged[0].data.text, "Neu");
  assert.equal(merged[0].session_sequence, 2);
});

test("unrendered append deltas are folded without losing earlier words", () => {
  const first = { type: "interim_transcript", data: { segment_id: "a", mode: "append", text: "Nicht " }, session_sequence: 1, event_id: 1 };
  const second = { type: "interim_transcript", data: { segment_id: "a", mode: "append", text: "zustimmen." }, session_sequence: 2, event_id: 2 };

  const staged = stageSocketPayload([], {
    type: "session_snapshot",
    data: { events: [first, second] },
  }, 0, 10);

  assert.equal(staged.events.length, 1);
  assert.equal(staged.events[0].data.text, "Nicht zustimmen.");
  assert.equal(staged.events[0].data.mode, "append");
});

test("an unrendered replacement still replaces after an append is folded into it", () => {
  const first = { type: "interim_transcript", data: { mode: "replace", text: "Hallo " }, session_sequence: 1 };
  const next = { type: "interim_transcript", data: { mode: "append", text: "Welt" }, session_sequence: 2 };

  const staged = stageSocketPayload([first], next, 0);

  assert.deepEqual(staged.events[0].data, { mode: "replace", text: "Hallo Welt" });
});

test("a final transcript clears the pending preview before the next append on the same track", () => {
  const interim = { type: "interim_transcript", data: { mode: "append", text: "Alt" }, session_sequence: 1 };
  const final = { type: "transcript", data: { id: "final", text: "Alt." }, session_sequence: 2 };
  const next = { type: "interim_transcript", data: { mode: "append", text: "Neu" }, session_sequence: 3 };
  const finalized = stageSocketPayload([interim], final, 0);
  const staged = stageSocketPayload(finalized.events, next, 0);

  assert.deepEqual(staged.events, [final, next]);
});

test("append after an acknowledged delta keeps only the new text", () => {
  const first = { type: "interim_transcript", data: { segment_id: "a", mode: "append", text: "Nicht " }, session_sequence: 1, event_id: 1 };
  const second = { type: "interim_transcript", data: { segment_id: "a", mode: "append", text: "zustimmen." }, session_sequence: 2, event_id: 2 };

  const staged = stageSocketPayload([first], second, 1, 10);

  assert.equal(staged.events.length, 1);
  assert.equal(staged.events[0].data.text, "zustimmen.");
});

test("native audio levels are coalesced per track without growing message history", () => {
  const oldMic = { type: "audio_level", data: { track: 0, level: 0.2 }, session_sequence: 1, event_id: 1 };
  const system = { type: "audio_level", data: { track: 1, level: 0.4 }, session_sequence: 2, event_id: 2 };
  const newMic = { type: "audio_level", data: { track: 0, level: 0.8 }, session_sequence: 3, event_id: 3 };

  const merged = mergeSocketEvents([oldMic], [system, newMic], 10);

  assert.equal(merged.length, 2);
  assert.deepEqual(merged.map((event) => [event.data.track, event.data.level]), [[1, 0.4], [0, 0.8]]);
});

test("events received while rendering is paused are retained before the resume cursor advances", () => {
  const transcript = {
    type: "transcript",
    data: { id: "t1", text: "Final" },
    session_sequence: 7,
    event_id: 7,
  };

  const staged = stageSocketPayload([], transcript, 0, 10);

  assert.deepEqual(staged.events, [transcript]);
  assert.equal(staged.needsResync, false);
  assert.equal(processedSocketSequence([], 0), 0);
  assert.equal(processedSocketSequence(staged.events, 0), 7);
});

test("a replay received before rendering is deduplicated without losing the final event", () => {
  const transcript = {
    type: "transcript",
    data: { id: "t1", text: "Final" },
    session_sequence: 7,
    event_id: 7,
  };

  const firstDelivery = stageSocketPayload([], transcript, 0, 10);
  const replayedDelivery = stageSocketPayload(firstDelivery.events, transcript, 0, 10);

  assert.deepEqual(replayedDelivery.events, [transcript]);
  assert.equal(replayedDelivery.needsResync, false);
  assert.equal(processedSocketSequence(replayedDelivery.events, 0), 7);
});

test("more unrendered final events than the client bound request resynchronization", () => {
  const finals = Array.from({ length: 1001 }, (_, index) => ({
    type: "transcript",
    data: { id: `t${index + 1}`, text: `Final ${index + 1}` },
    session_sequence: index + 1,
    event_id: index + 1,
  }));

  const staged = stageSocketPayload([], {
    type: "session_snapshot",
    data: { events: finals },
  }, 0, 1000);

  assert.equal(staged.needsResync, true);
  assert.deepEqual(staged.events, []);
  assert.equal(processedSocketSequence(staged.events, 0), 0);
});

test("bounded client history discards interims before final state", () => {
  const finalTranscript = { type: "transcript", data: { id: "t1", text: "Final" }, session_sequence: 1, event_id: 1 };
  const status = { type: "status", data: { state: "ready" }, session_sequence: 2, event_id: 2 };
  const interim = { type: "interim_transcript", data: { segment_id: "a", text: "Zwischenstand" }, session_sequence: 3, event_id: 3 };

  const merged = mergeSocketEvents([], [finalTranscript, status, interim], 2);

  assert.deepEqual(merged.map((event) => event.type), ["transcript", "status"]);
});
