import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const componentPath = fileURLToPath(new URL("./TranscriptReview.tsx", import.meta.url));
const outputDir = await mkdtemp(join(tmpdir(), "transcript-review-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  stdin: {
    contents: `
      import React from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      import TranscriptReview from "./TranscriptReview.tsx";
      export function render(props) {
        return renderToStaticMarkup(React.createElement(TranscriptReview, props));
      }
    `,
    resolveDir: dirname(componentPath),
    sourcefile: "transcript-review-test-entry.tsx",
    loader: "tsx",
  },
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: outputPath,
});

const { render } = createRequire(import.meta.url)(outputPath);

after(async () => {
  await rm(outputDir, { recursive: true, force: true });
});

test("durable final text offers a revisioned manual correction", () => {
  const html = render({
    transcripts: [{
      id: "t1",
      session_id: "s1",
      text: "Fuenfzig Prozent.",
      timestamp: "2026-11-07T12:00:00Z",
      sequence: 1,
      manual_corrected_at: "2026-11-07T12:01:00Z",
    }],
    speakers: [],
    onCorrectTranscript: () => {},
  });

  assert.match(html, /Text korrigieren/);
  assert.match(html, /Manuell korrigiert/);
  assert.doesNotMatch(html, /key=\{idx\}/);
});

test("provisional text stays read-only until it has a durable final identity", () => {
  const html = render({
    transcripts: [{
      id: "p1",
      session_id: "s1",
      text: "Noch ein Entwurf.",
      timestamp: "2026-11-07T12:00:00Z",
      sequence: 1,
      provisional: true,
    }],
    speakers: [],
    onCorrectTranscript: () => {},
  });

  assert.doesNotMatch(html, /Text korrigieren/);
});

test("list keys use transcript identity instead of the array index", () => {
  const source = readFileSync(componentPath, "utf8");
  assert.doesNotMatch(source, /<li key=\{idx\}/);
  assert.match(source, /entry\.id \?\? entry\.utterance_id/);
});
