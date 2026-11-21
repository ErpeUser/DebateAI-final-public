import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import {
  validateBlindSuite,
  validateBlindImport,
  comparisonSummary,
} from "../public/calibration/core.mjs";
const good = () => ({
  case_id: "de-001",
  mode: "hart",
  context: "Gegenseite: Test.",
  candidates: [
    { id: "one", text: "Antwort A" },
    { id: "two", text: "Antwort B" },
  ],
});
const failed = () => ({
  schema_version: 1,
  kind: "production_replay_blind_suite",
  cases: [],
  failures: [
    {
      case_id: "de-001",
      mode: "hart",
      errors: [{ candidate_id: "one", status: "failed" }],
    },
  ],
  summary: {
    attempted_pairs: 1,
    votable_pairs: 0,
    failed_pairs: 1,
    attempted_candidates: 2,
    failed_candidates: 1,
  },
});
test("all failed experiment has no fake answers", () => {
  const v = failed();
  assert.deepEqual(validateBlindSuite(v), []);
  assert.deepEqual(comparisonSummary(v), v.summary);
});
test("invalid or missing failure denominator rejected", () => {
  for (const change of [
    (v) => (v.summary.failed_pairs = 0),
    (v) => (v.summary.failed_candidates = 3),
    (v) => (v.failures = []),
    (v) => (v.summary.attempted_pairs = NaN),
  ]) {
    const v = failed();
    change(v);
    assert.throws(() => validateBlindSuite(v));
  }
});
test("manual import remains compatible", () => {
  assert.equal(validateBlindSuite(good()).length, 1);
  assert.equal(comparisonSummary(good()).attempted_pairs, 1);
});
test("context hash is really verified", async () => {
  const v = good();
  v.context_sha256 = "a".repeat(64);
  await assert.rejects(validateBlindImport(v, webcrypto.subtle), /Pruefsumme/);
});
test("valid context hash imports", async () => {
  const v = good();
  v.context_sha256 = Buffer.from(
    await webcrypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(v.context),
    ),
  ).toString("hex");
  assert.equal((await validateBlindImport(v, webcrypto.subtle)).length, 1);
});
test("failed and successful cases cannot share one identity", () => {
  const v = failed();
  v.cases = [good()];
  v.summary = {
    attempted_pairs: 2,
    votable_pairs: 1,
    failed_pairs: 1,
    attempted_candidates: 4,
    failed_candidates: 1,
  };
  assert.throws(() => validateBlindSuite(v));
});
