import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./DebateReviewCard.tsx", import.meta.url), "utf8");
const apiSource = await readFile(new URL("../../services/api.ts", import.meta.url), "utf8");

test("post-debate review and applying settings both require manual confirmation", () => {
  assert.match(source, /window\.confirm/);
  assert.match(source, /generateDebateReview/);
  assert.match(source, /applyDebateReview/);
  assert.match(apiSource, /confirmed:\s*true/);
});

test("the card explains that the login bridge creates no remote chat history", () => {
  assert.match(source, /keinen separaten Online-Chat/);
  assert.match(source, /lokal gespeichert/);
});

test("the manual review contains a compact claim-linked source library", () => {
  assert.match(source, /Quellenbibliothek/);
  assert.match(source, /SourceInspector/);
  assert.doesNotMatch(source, />Belegt zu:</);
  assert.match(source, /review\.sources/);
  assert.match(source, /claimId=\{source\.claim_id/);
});
