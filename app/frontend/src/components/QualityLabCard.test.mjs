import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const component = await readFile(
  fileURLToPath(new URL("./QualityLabCard.tsx", import.meta.url)),
  "utf8",
);
const api = await readFile(
  fileURLToPath(new URL("../services/api.ts", import.meta.url)),
  "utf8",
);

test("quality lab shows identities by default and keeps blind rating optional", () => {
  assert.match(component, /Antwort \{side\}/);
  assert.match(component, /Optional blind bewerten/);
  assert.match(component, /!blindRating \|\| revealed/);
  assert.match(component, /candidate\.model_name/);
  assert.match(component, /candidate\.prompt_version/);
  assert.match(component, /candidate\.latency_ms/);
  assert.match(component, /setRevealed\(true\)/);
  assert.match(
    component,
    /disabled=\{!ratingComplete \|\| busy \|\| revealed\}/,
  );
  assert.match(component, /sichtbare Modellvergleich bleibt exportierbar/);
});

test("quality lab exposes repeatable holdout, export, apply, and rollback controls", () => {
  assert.match(component, /Unabhängigen Holdout anfordern/);
  assert.match(component, /!run\.can_apply/);
  assert.match(component, /!run\.can_rollback/);
  assert.match(component, /exportRun/);
  assert.match(component, /applyQualityLabVariant/);
  assert.match(component, /rollbackQualityLab/);
  assert.match(api, /\/quality-lab\/runs/);
});
