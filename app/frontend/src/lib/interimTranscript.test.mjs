import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const sourcePath = fileURLToPath(new URL("./interimTranscript.ts", import.meta.url));
const outputDir = await mkdtemp(join(tmpdir(), "interim-transcript-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  entryPoints: [sourcePath],
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: outputPath,
});

const { updateInterimText } = createRequire(import.meta.url)(outputPath);

after(async () => {
  await rm(outputDir, { recursive: true, force: true });
});

test("a corrected streaming hypothesis replaces the previous partial", () => {
  assert.equal(
    updateInterimText("Die Kosten sinken", "Die Kosten sinken nicht", "replace"),
    "Die Kosten sinken nicht",
  );
});

test("append-mode cloud chunks remain compatible and bounded", () => {
  assert.equal(updateInterimText("Guten ", "Tag", "append"), "Guten Tag");
  assert.equal(updateInterimText("a".repeat(500), "Ende", "append").length, 500);
});
