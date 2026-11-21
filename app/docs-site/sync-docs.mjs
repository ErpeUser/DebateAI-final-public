// Derives ../docs/*.md into the ignored Starlight build staging directory.
// The repo docs/ folder is the only editorial source. The staging directory is
// removed after a normal build, so the Docs-Site never owns a second document
// copy.
import {
  copyFileSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";

const SRC = join(import.meta.dirname, "..", "docs");
const OUT = join(import.meta.dirname, "src", "content", "docs");
const REPO_URL = "https://github.com/ErpeUser/DebateAI-final-public";

rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });

for (const file of readdirSync(SRC).filter((f) => f.endsWith(".md"))) {
  // The technical handbook is the docs root. Keep its source filename
  // descriptive while preserving the stable /docs/ URL expected by the site.
  const slug =
    file === "HANDBUCH.md"
      ? "index"
      : file.replace(/\.md$/, "").toLowerCase();
  let text = readFileSync(join(SRC, file), "utf8");

  // Drop the GitHub-only wordmark banner; Starlight has its own header.
  text = text.replace(/^<p align="center">[\s\S]*?<\/p>\s*/, "");

  const h1 = text.match(/^# (.+)$/m);
  if (!h1) throw new Error(`${file}: no H1 to derive a title from`);
  // Replace only the heading text, not the trailing newline: on Windows
  // checkouts the line ends \r\n, and "h1[0] + '\n'" would fail to match,
  // leaving a duplicate H1 under Starlight's own page title.
  text = text.replace(h1[0], "");

  // Links to repo files outside docs/ go to GitHub.
  text = text
    .replaceAll("](../README.md)", `](${REPO_URL}#readme)`)
    .replaceAll("](../architecture.svg)", "](./architecture.svg)");

  // "foo.md" / "foo.md#hash" -> relative page URL. Pages live at /<slug>/,
  // so siblings are one level up -- except from the index page.
  const prefix = slug === "index" ? "./" : "../";
  text = text.replace(
    /\]\(([\w-]+)\.md(#[^)]*)?\)/g,
    (_, name, hash = "") =>
      `](${prefix}${name === "README" || name === "HANDBUCH" ? "" : name.toLowerCase() + "/"}${hash})`,
  );

  // Per-page meta description: first prose block (headings/tables/images/code
  // skipped), markdown stripped, truncated to ~155 chars. Prefer whole
  // sentences so SERP snippets and og:description never cut off mid-thought;
  // fall back to a word boundary plus ellipsis only when the first sentence
  // alone exceeds the budget.
  const block = text
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .find((b) => b && !/^[#|<!`]/.test(b));
  const plain = (block ?? h1[1])
    .replace(/^\s*(?:[-*]|\d+\.)\s+/gm, "")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[`*]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  let description = plain;
  if (plain.length > 155) {
    const sentences = plain.match(/[^.!?]+[.!?]+(?:\s|$)/g);
    description = "";
    for (const sentence of sentences ?? []) {
      if (description.length + sentence.trim().length + 1 > 155) break;
      description += (description ? " " : "") + sentence.trim();
    }
    if (!description)
      description = plain.slice(0, 152).replace(/\s+\S*$/, "") + "...";
  }

  writeFileSync(
    join(OUT, `${slug}.md`),
    `---\ntitle: ${JSON.stringify(h1[1])}\ndescription: ${JSON.stringify(description)}\n---\n\n${text}`,
  );
}

// Referenced by HANDBUCH.md; stored with versioned docs at app/docs.
copyFileSync(join(SRC, "architecture.svg"), join(OUT, "architecture.svg"));

// Screenshots and other images referenced by the docs as assets/<file>.
const ASSETS = join(SRC, "assets");
mkdirSync(join(OUT, "assets"), { recursive: true });
for (const file of readdirSync(ASSETS).filter((f) =>
  /\.(png|svg|jpe?g|gif|webp)$/i.test(f),
)) {
  copyFileSync(join(ASSETS, file), join(OUT, "assets", file));
}
console.log("Synced docs from", SRC);
