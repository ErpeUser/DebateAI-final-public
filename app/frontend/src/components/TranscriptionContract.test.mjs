import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("transcription UI fallback matches the German desktop default", async () => {
  const source = await read("./BatchTranscriptionCard.tsx");

  assert.match(source, /const language = config\?\.language \?\? "de"/);
  assert.match(source, /\{ code: "de", name: "Deutsch" \}/);
  assert.doesNotMatch(source, /config\?\.language \?\? "auto"/);
});

test("local fit guidance names the experimental local captioner", async () => {
  const source = await read("./LocalModelFitCard.tsx");

  assert.match(source, /experimentelle lokale Parakeet-Untertitler verfügbar/);
  assert.match(source, /Transkription &amp; Audio explizit/);
  assert.doesNotMatch(source, /Fuer Live-Zwischentitel gibt es derzeit keine lokale Option/);
});

test("docs and release notes expose the same language contract", async () => {
  const configuration = await read("../../../docs/configuration.md");
  const releaseNotes = await read("../../../backend/app/release_notes.py");

  assert.match(configuration, /desktop\/runtime default is German \(`de`\)/i);
  assert.match(releaseNotes, /desktop Debate Copilot starts on German/i);
  assert.doesNotMatch(releaseNotes, /starts on\s+\n\s*Detect automatically/i);
});
