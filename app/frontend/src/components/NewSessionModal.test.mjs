import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const componentPath = fileURLToPath(
  new URL("./NewSessionModal.tsx", import.meta.url),
);
const outputDir = await mkdtemp(join(tmpdir(), "new-session-modal-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  stdin: {
    contents: `
      import React from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      import NewSessionModal, { LAST_DEBATE_MODE_KEY, readLastDebateMode } from "./NewSessionModal.tsx";
      import { MEETING_TYPES } from "./PreCall/MeetingContextSetup.tsx";
      export { MEETING_TYPES };
      export { LAST_DEBATE_MODE_KEY, readLastDebateMode };
      export function render() {
        return renderToStaticMarkup(React.createElement(NewSessionModal, {
          open: true,
          onClose: () => {},
          onCreate: async () => {},
        }));
      }
    `,
    resolveDir: dirname(componentPath),
    sourcefile: "new-session-modal-test-entry.tsx",
    loader: "tsx",
  },
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: outputPath,
});

const { LAST_DEBATE_MODE_KEY, MEETING_TYPES, readLastDebateMode, render } =
  createRequire(import.meta.url)(outputPath);
after(async () => rm(outputDir, { recursive: true, force: true }));

test("keeps both advanced debate styles available", () => {
  assert.equal(MEETING_TYPES[0].value, "debate_persuasive");
  assert.equal(MEETING_TYPES[1].value, "debate_forceful");
  assert.match(MEETING_TYPES[0].label, /Debatte.*Überzeugen/);
  assert.match(MEETING_TYPES[1].label, /Debatte.*Brutal-sachlich/);
  assert.ok(MEETING_TYPES.some((type) => type.value === "general"));
  assert.ok(MEETING_TYPES.some((type) => type.value === "client_sales"));
});

test("opens in German with both debate modes and persuasive preselected", () => {
  const html = render();
  assert.match(html, /Neue Debatte/);
  assert.match(html, /Debatte.*Überzeugen/);
  assert.match(html, /Debatte.*Brutal-sachlich/);
  assert.match(html, /aria-pressed="true"/);
  assert.match(html, /aria-pressed="false"/);
  assert.doesNotMatch(html, /Allgemein \/ automatisch erkennen/);
  assert.match(html, /Abbrechen/);
  assert.match(html, /Erstellen/);
});

test("restores the last selected debate mode from browser storage", () => {
  const previousWindow = globalThis.window;
  const values = new Map([[LAST_DEBATE_MODE_KEY, "debate_forceful"]]);
  globalThis.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    },
  };
  try {
    assert.equal(readLastDebateMode(), "debate_forceful");
    const html = render();
    assert.match(html, /aria-pressed="false"[^>]*>.*Überzeugen/s);
    assert.match(html, /aria-pressed="true"[^>]*>.*Brutal-sachlich/s);
  } finally {
    globalThis.window = previousWindow;
  }
});

test("ignores invalid persisted meeting types and keeps the safe default", () => {
  const previousWindow = globalThis.window;
  globalThis.window = {
    localStorage: {
      getItem: () => "client_sales",
      setItem: () => {},
    },
  };
  try {
    assert.equal(readLastDebateMode(), "debate_persuasive");
  } finally {
    globalThis.window = previousWindow;
  }
});
