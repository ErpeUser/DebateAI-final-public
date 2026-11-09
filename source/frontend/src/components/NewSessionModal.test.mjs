import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const componentPath = fileURLToPath(new URL("./NewSessionModal.tsx", import.meta.url));
const outputDir = await mkdtemp(join(tmpdir(), "new-session-modal-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  stdin: {
    contents: `
      import React from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      import NewSessionModal from "./NewSessionModal.tsx";
      import { MEETING_TYPES } from "./PreCall/MeetingContextSetup.tsx";
      export { MEETING_TYPES };
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

const { MEETING_TYPES, render } = createRequire(import.meta.url)(outputPath);
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
