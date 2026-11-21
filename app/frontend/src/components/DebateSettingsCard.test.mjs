import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const componentPath = fileURLToPath(
  new URL("./DebateSettingsCard.tsx", import.meta.url),
);
const outputDir = await mkdtemp(join(tmpdir(), "debate-settings-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  stdin: {
    contents: `
      import React from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      import { DebateSettingsControls } from "./DebateSettingsCard.tsx";
      export function render(props) {
        return renderToStaticMarkup(React.createElement(DebateSettingsControls, props));
      }
    `,
    resolveDir: dirname(componentPath),
    sourcefile: "debate-settings-test-entry.tsx",
    loader: "tsx",
  },
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: outputPath,
});

const { render } = createRequire(import.meta.url)(outputPath);
after(async () => rm(outputDir, { recursive: true, force: true }));

const settings = {
  mode: "forceful",
  research_enabled: true,
  research_frequency: "often",
  always_analogy: true,
  cooldown_seconds: 20,
  style_focus: "balanced",
  voice_commands_enabled: true,
  argument_memory_enabled: true,
  audio_archive_enabled: false,
  memory_similarity_threshold: 0.34,
};

test("renders the two rhetoric modes and three research frequencies", () => {
  const html = render({
    settings,
    privacyFirst: false,
    saving: false,
    onChange: () => {},
  });
  assert.match(html, /Überzeugen/);
  assert.match(html, /Hart/);
  assert.match(html, /Wenig/);
  assert.match(html, /Normal/);
  assert.match(html, /Oft/);
  assert.match(html, /aria-pressed="true"[^>]*>Hart/s);
  assert.match(html, /20 Sekunden/);
  assert.match(html, /Publikum.*eigene Maßstäbe/s);
  assert.match(html, /Position.*Beweislast.*Konsistenz/s);
  assert.match(html, /Ausgewogen/);
  assert.match(html, /Natürlich/);
  assert.match(html, /Sehr kurz/);
  assert.match(html, /Belegfokus/);
  assert.match(html, /Sprachbefehle vom eigenen Mikrofon/);
  assert.match(html, /Argumentged.*chtnis/);
  assert.match(html, /Audio dauerhaft archivieren/);
  assert.match(html, /0.34/);
});

test("zeigt, dass der Datenschutzmodus öffentliche Recherche blockiert", () => {
  const html = render({
    settings,
    privacyFirst: true,
    saving: false,
    onChange: () => {},
  });
  assert.match(html, /Datenschutzmodus/);
  assert.match(html, /Öffentliche Recherche ist blockiert/);
});
