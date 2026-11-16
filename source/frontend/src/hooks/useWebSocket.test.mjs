import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

test("the stop wait is bounded by silence, not by total drain length", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");

  // Every message rearms the deadline, so a drain that legitimately runs for
  // minutes survives as long as progress or heartbeats keep arriving (ALP-171).
  assert.match(hook, /armStopDeadline\(\);\s*\n\s*const completed = accepted\.find/);
  // The old failure mode: one fixed timer armed at send time and never reset.
  assert.doesNotMatch(hook, /setTimeout\(\(\) => resolveStop\(false\), 180000\)/);
});

test("a silent backend is reported as still processing, not as a lost connection", async () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");

  // Silence and a closed socket are different answers: only the latter means
  // the recording may actually be gone.
  assert.match(hook, /resolveStop\("still_processing"\)/);
  assert.match(hook, /resolveStop\("disconnected"\)/);
  assert.match(hook, /export type StopOutcome =/);
});

test("the end-call caller distinguishes the three stop outcomes", () => {
  const app = readFileSync(new URL("../App.tsx", import.meta.url), "utf8");

  assert.match(app, /stopOutcome === "completed"/);
  // Silence hands off to a poller instead of the unconfirmed/resume path.
  assert.match(app, /stopOutcome === "still_processing"/);
  assert.match(app, /pollSessionCompletion\(activeSessionId\)/);
  assert.match(app, /backgroundPostProcessing/);
});

test("reconnect resumes after the last processed session sequence", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");

  assert.match(hook, /after_sequence/);
  assert.match(hook, /lastSequenceRef/);
  assert.match(hook, /socketPayloadEvents/);
  assert.match(hook, /stageSocketPayload/);
  assert.match(hook, /reconnectTimerRef/);
});

test("reconnect carries capture identity while explicit disconnect rotates it", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");

  assert.match(hook, /captureIdRef/);
  assert.match(hook, /query\.set\("capture_id", captureIdRef\.current\)/);
  assert.match(hook, /captureIdRef\.current = ""/);
});

test("audio send applies browser WebSocket high/low-water backpressure", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");

  assert.match(hook, /bufferedAmount/);
  assert.match(hook, /AUDIO_SEND_HIGH_WATER_BYTES/);
  assert.match(hook, /AUDIO_SEND_LOW_WATER_BYTES/);
  assert.match(hook, /audioBackpressureRef/);
  assert.match(hook, /chunksDropped: audioStatsRef\.current\.chunksDropped \+ 1/);
});

test("hidden-window delivery does not depend on an animation frame and resyncs when visible", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");

  assert.doesNotMatch(hook, /requestAnimationFrame/);
  assert.match(hook, /document\.addEventListener\("visibilitychange"/);
  assert.match(hook, /stageSocketPayload/);
  assert.match(hook, /needsResync/);
  assert.match(hook, /processedSocketSequence/);
});

test("the replay cursor advances only after the app processes the delivered batch", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");
  const app = readFileSync(new URL("../App.tsx", import.meta.url), "utf8");

  assert.match(hook, /const acknowledgeMessages = useCallback/);
  assert.doesNotMatch(
    hook,
    /useEffect\(\(\) => \{\s*lastSequenceRef\.current = processedSocketSequence/,
  );

  const processingStart = app.indexOf("for (const msg of newMessages)");
  const acknowledgement = app.indexOf("acknowledgeMessages(newMessages)", processingStart);
  const effectEnd = app.indexOf("}, [messages", processingStart);
  assert.ok(processingStart >= 0, "the message processing loop must exist");
  assert.ok(acknowledgement > processingStart, "the batch must be acknowledged after processing");
  assert.ok(acknowledgement < effectEnd, "the acknowledgement must remain inside the message effect");
});

test("socket sends survive a close between readyState check and send", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");
  assert.match(hook, /export function safeSocketSend/);
  assert.match(hook, /if \(!safeSocketSend\(socket, framed\.buffer\)\)/);
  assert.match(hook, /if \(!safeSocketSend\(socket, JSON\.stringify\(payload\)\)/);
  assert.doesNotMatch(hook, /wsRef\.current\.send\(/);
});

test("app replay cursor resets when the server epoch changes", () => {
  const hook = readFileSync(new URL("./useWebSocket.ts", import.meta.url), "utf8");
  const app = readFileSync(new URL("../App.tsx", import.meta.url), "utf8");
  assert.match(hook, /const \[serverEpoch, setServerEpoch\] = useState\(\"\"\)/);
  assert.match(hook, /setServerEpoch\(incomingEpoch\)/);
  assert.match(app, /processedEpochRef/);
  assert.match(app, /serverEpoch !== processedEpochRef\.current/);
  assert.match(app, /processedSequenceRef\.current = 0;/);
});
