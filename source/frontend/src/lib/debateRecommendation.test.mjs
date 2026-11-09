import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const sourcePath = fileURLToPath(new URL("./debateRecommendation.ts", import.meta.url));
const outputDir = await mkdtemp(join(tmpdir(), "debate-reducer-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  entryPoints: [sourcePath],
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: outputPath,
});

const { emptyDebateState, reduceDebateUpdate } = createRequire(import.meta.url)(outputPath);

after(async () => {
  await rm(outputDir, { recursive: true, force: true });
});

const recommendation = (revision, answer = `Antwort ${revision}`) => ({
  answer_now: answer,
  counterargument: "Gegenargument",
  counter_question: "Gegenfrage?",
  target_claim: "Behauptung",
  confidence: "medium",
  needs_research: false,
  research_query: "",
  research_status: "idle",
  sources: [],
  revision,
  recommendation_revision: revision,
  transcript_revision: revision,
  claim_id: "claim-1",
  utterance_id: "utt-1",
  provisional: false,
  origin: "model",
  generated_at: `2026-11-02T10:00:0${revision}Z`,
});

test("newest revision replaces the visible recommendation", () => {
  const first = reduceDebateUpdate(emptyDebateState("call-1"), "call-1", recommendation(1));
  const second = reduceDebateUpdate(first, "call-1", recommendation(2));

  assert.equal(second.recommendation.answer_now, "Antwort 2");
});

test("an older result cannot overwrite newer guidance", () => {
  const current = reduceDebateUpdate(emptyDebateState("call-1"), "call-1", recommendation(4));
  const stale = reduceDebateUpdate(current, "call-1", recommendation(3));

  assert.equal(stale, current);
  assert.equal(stale.recommendation.revision, 4);
});

test("same-revision research refinement replaces the immediate draft", () => {
  const current = reduceDebateUpdate(emptyDebateState("call-1"), "call-1", recommendation(2));
  const refined = reduceDebateUpdate(current, "call-1", {
    ...recommendation(2, "Antwort mit Quelle"),
    research_status: "completed",
  });

  assert.equal(refined.recommendation.answer_now, "Antwort mit Quelle");
});

test("starting a different websocket call clears the prior recommendation", () => {
  const previous = reduceDebateUpdate(emptyDebateState("call-1"), "call-1", recommendation(5));
  const reset = emptyDebateState("call-2");

  assert.equal(previous.recommendation.revision, 5);
  assert.equal(reset.sessionId, "call-2");
  assert.equal(reset.recommendation, null);
});

test("a delayed model answer replaces a provisional card for the same claim", () => {
  const draft = reduceDebateUpdate(emptyDebateState("call-1"), "call-1", {
    ...recommendation(4, "Vorlaeufig"),
    provisional: true,
    origin: "instant",
  });
  const model = reduceDebateUpdate(draft, "call-1", {
    ...recommendation(5, "Modellantwort"),
    transcript_revision: 4,
  });

  assert.equal(model.recommendation.answer_now, "Modellantwort");
  assert.equal(model.recommendation.claim_id, "claim-1");
});

test("a delayed result for another claim cannot replace the active card", () => {
  const active = reduceDebateUpdate(emptyDebateState("call-1"), "call-1", {
    ...recommendation(5, "Aktueller Punkt"),
    claim_id: "claim-new",
  });
  const stale = reduceDebateUpdate(active, "call-1", {
    ...recommendation(6, "Alter Punkt"),
    claim_id: "claim-old",
    transcript_revision: 3,
  });

  assert.equal(stale, active);
});
