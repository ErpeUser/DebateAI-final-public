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

test("quality lab keeps both sides blind until a complete rating is saved", () => {
  assert.match(component, /Antwort \{side\}/);
  assert.match(component, /setRevealed\(true\)/);
  assert.match(
    component,
    /disabled=\{!ratingComplete \|\| busy \|\| revealed\}/,
  );
  assert.match(component, /Modell- und Promptdetails sind jetzt sichtbar/);
});

test("quality lab exposes repeatable holdout, export, apply, and rollback controls", () => {
  assert.match(component, /Unabhängigen Holdout verwenden/);
  assert.match(component, /exportRun/);
  assert.match(component, /applyQualityLabVariant/);
  assert.match(component, /rollbackQualityLab/);
  assert.match(api, /\/quality-lab\/runs/);
});
