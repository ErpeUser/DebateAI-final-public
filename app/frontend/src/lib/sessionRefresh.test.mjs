import assert from "node:assert/strict";
import { test } from "node:test";
import {
  hideActiveProvisionalRevisions,
  isCurrentSessionResponse,
  shouldRecoverTranscriptsFromStatus,
} from "./sessionRefresh.ts";

test("late session responses cannot overwrite a newly selected session", () => {
  assert.equal(isCurrentSessionResponse("session-a", "session-a"), true);
  assert.equal(isCurrentSessionResponse("session-a", "session-b"), false);
  assert.equal(isCurrentSessionResponse("session-a", null), false);
});

test("replayed live interim does not duplicate its durable provisional projection", () => {
  const rows = [
    { id: "p1", provisional: true, utterance_id: "segment-1", text: "Entwurf" },
    { id: "f1", provisional: false, text: "Final" },
  ];

  assert.deepEqual(
    hideActiveProvisionalRevisions(rows, new Set(["segment-1"])),
    [rows[1]],
  );
  assert.deepEqual(hideActiveProvisionalRevisions(rows, new Set()), rows);
});

test("a reconnect status reloads durable transcript drafts for the visible session", () => {
  assert.equal(shouldRecoverTranscriptsFromStatus("connecting", true), true);
  assert.equal(shouldRecoverTranscriptsFromStatus("active", true), true);
  assert.equal(shouldRecoverTranscriptsFromStatus("completed", true), true);
  assert.equal(shouldRecoverTranscriptsFromStatus("active", false), false);
  assert.equal(shouldRecoverTranscriptsFromStatus("audio_received", true), false);
});
