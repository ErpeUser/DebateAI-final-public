import test from "node:test";
import assert from "node:assert/strict";
import { shouldAcceptDebateOverlaySnapshot } from "./debateOverlaySnapshot.mjs";

const snapshot = (overrides = {}) => ({
  active: true,
  session_id: "session-1",
  recommendation: {
    transcript_revision: 4,
    claim_revision: 2,
    recommendation_revision: 3,
    revision: 3,
    generated_at: "2026-11-20T12:00:03Z",
    ...overrides,
  },
});

test("rejects a late response from an older transcript revision", () => {
  assert.equal(
    shouldAcceptDebateOverlaySnapshot(snapshot(), snapshot({ transcript_revision: 3 })),
    false,
  );
});

test("accepts a newer turn even when the response timestamp is close", () => {
  assert.equal(
    shouldAcceptDebateOverlaySnapshot(snapshot(), snapshot({ transcript_revision: 5, generated_at: "2026-11-20T11:59:59Z" })),
    true,
  );
});

test("accepts a fresh session reset", () => {
  assert.equal(
    shouldAcceptDebateOverlaySnapshot(snapshot(), { ...snapshot(), session_id: "session-2", recommendation: null }),
    true,
  );
});
