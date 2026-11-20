import assert from "node:assert/strict";
import { test } from "node:test";
import { blindOrder, isRatingComplete, raterAgreement } from "./qualityLab.ts";

test("blindOrder is deterministic for a run and swaps with the seed", () => {
  const first = blindOrder("run-a", 0);
  assert.deepEqual(blindOrder("run-a", 0), first);
  assert.deepEqual(new Set(first), new Set(["A", "B"]));
  assert.notDeepEqual(blindOrder("run-a", 1), first);
});

test("rating is complete only after all dimensions or both unsuitable", () => {
  assert.equal(isRatingComplete({ naturalness: 5, strength: 4, precision: 4, source_honesty: 5, usability: 4, both_unsuitable: false }), true);
  assert.equal(isRatingComplete({ naturalness: 5, strength: null, precision: 4, source_honesty: 5, usability: 4, both_unsuitable: false }), false);
  assert.equal(isRatingComplete({ naturalness: null, strength: null, precision: null, source_honesty: null, usability: null, both_unsuitable: true }), true);
});

test("rater agreement is the normalized absolute distance across submitted ratings", () => {
  assert.equal(raterAgreement([{ naturalness: 5 }, { naturalness: 3 }]), 0.5);
  assert.equal(raterAgreement([{ naturalness: 5, strength: 4 }, { naturalness: 5, strength: 4 }]), 1);
  assert.equal(raterAgreement([]), null);
  assert.equal(raterAgreement([{ naturalness: 5 }]), null);
});
