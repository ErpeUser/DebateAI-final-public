import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const component = await readFile(
  fileURLToPath(new URL("./VideoEvalCard.tsx", import.meta.url)),
  "utf8",
);
const api = await readFile(
  fileURLToPath(new URL("../services/api.ts", import.meta.url)),
  "utf8",
);

test("video evaluation UI follows the shared job contract and shows consent", () => {
  for (const path of ["/video-eval/jobs", "/consent", "/cancel", "/artifact"])
    assert.match(api, new RegExp(path.replaceAll("/", "\\/")));
  assert.match(component, /Gemini-Fallback erlauben/);
  assert.match(component, /Analyse abbrechen/);
  assert.match(component, /Claims und Quellen öffnen/);
  assert.match(component, /setInterval/);
});
