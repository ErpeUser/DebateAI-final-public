import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const customerFiles = [
  "../README.md",
  "../docs/HANDBUCH.md",
  "../docs/VISION.md",
  "../docs/OFFENE_PUNKTE.md",
  "../docs/HISTORIE.md",
  "../AGENTS.md",
  "../site/index.html",
  "../site/private-meeting-ai/index.html",
  "../site/analyst-lenses/index.html",
  "../site/blog/index.html",
  "../site/blog/live-meeting-ai-enterprise-gate/index.html",
  "../site/fireflies-alternative/index.html",
  "../site/granola-alternative/index.html",
  "../site/otter-alternative/index.html",
  "../site/vs-meetily/index.html",
  "../site/open-source-meeting-assistants/index.html",
  "../site/vs-anarlog/index.html",
  "../site/fathom-alternative/index.html",
  "../site/read-ai-alternative/index.html",
  "../site/gong-and-backchannel/index.html",
  "../site/vs-clari-copilot/index.html",
  "../site/teams-premium-alternative/index.html",
  "../site/plaud-alternative/index.html",
  "../site/releases/v0.1.0/index.html",
  "../site/releases/v0.1.1/index.html",
  "../site/releases/v0.2.0/index.html",
  "../site/releases/v0.2.1/index.html",
  "../site/releases/v0.2.2/index.html",
  "../site/releases/v0.2.3/index.html",
  "../site/releases/v0.2.4/index.html",
  "../site/releases/v0.2.5/index.html",
  "../site/releases/index.html",
  "../site/releases/v0.6.6/index.html",
  "../site/llms.txt",
  "../site/sitemap.xml",
  "../.github/release-notes/v0.1.1.md",
  "../.github/release-notes/v0.2.0.md",
  "../.github/release-notes/v0.2.1.md",
  "../.github/release-notes/v0.2.2.md",
  "../.github/release-notes/v0.2.3.md",
  "../.github/release-notes/v0.2.4.md",
  "../.github/release-notes/v0.2.5.md",
];
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const customerContent = customerFiles.map((path) => [path, read(path)]);
const portal = "/downloads/";

const html = readFileSync(
  new URL("../site/index.html", import.meta.url),
  "utf8",
);
const seededAgents = read("../backend/app/services/seed_agents.py")
  .split("SEED_CONFIGS = [")[1]
  .split("async def seed_agent_configs")[0];
const marker = 'var form = document.getElementById("interest-form")';
const markerAt = html.indexOf(marker);
const scriptStart = html.lastIndexOf("<script>", markerAt) + "<script>".length;
const scriptEnd = html.indexOf("</script>", markerAt);
const interestScript = html.slice(scriptStart, scriptEnd);

test("public agent crew matches the shipped defaults and triggers", () => {
  const section = html.split('<section id="agents"')[1].split("</section>")[0];
  const slugs = [...section.matchAll(/<code>([^<]+)<\/code>/g)].map(
    (match) => match[1],
  );
  const defaults = [...seededAgents.matchAll(/"slug": "([^"]+)"/g)].map(
    (match) => match[1],
  );
  const modelIds = [...seededAgents.matchAll(/"model_id": "([^"]*)"/g)].map(
    (match) => match[1],
  );

  assert.deepEqual(slugs, defaults);
  assert.equal(modelIds.length, defaults.length);
  assert.ok(modelIds.every((modelId) => modelId === ""));
  assert.match(section, /consolidated_analyst[\s\S]*Every 40s \+ final pass/);
  assert.match(section, /objection_handler[\s\S]*Every 10s over the last 90s/);
  assert.match(
    section,
    /synthesizer[\s\S]*New or updated insights; 75s cooldown, 120s fallback/,
  );
  assert.match(
    section,
    /opportunity_specialist[\s\S]*New opportunities; 55s cooldown \+ final match/,
  );
  assert.match(section, /strategic_signals[\s\S]*Every 45s during the call/);
  for (const slug of [
    "brief_meeting_lens",
    "brief_discovery_lens",
    "brief_arbiter",
  ]) {
    assert.match(
      section,
      new RegExp(`${slug}[\\s\\S]*At call end or on demand`),
    );
  }
});

test("first-run copy describes explicit provider-aware model selection", () => {
  assert.doesNotMatch(
    html,
    /By default, transcription and analysis use the Gemini API/i,
  );
  assert.doesNotMatch(html, /add a Gemini API key in Admin/i);
  assert.match(html, /agents start as Not selected/i);
  assert.match(html, /Recommended/i);
});

test("active locality and language copy follows the implementation claim matrix", () => {
  const claimMatrix = read("../docs/HANDBUCH.md");
  const configuration = read("../docs/HANDBUCH.md");
  const releaseNotes = read("../backend/app/release_notes.py");
  const comparison = read("../site/open-source-meeting-assistants/index.html");
  const privacy = read("../site/private-meeting-ai/index.html");

  assert.match(claimMatrix, /Documents without the PII Shield/);
  assert.match(claimMatrix, /experimental, CPU-heavy/);
  assert.match(configuration, /desktop\/runtime default is German \(`de`\)/i);
  assert.doesNotMatch(configuration, /`auto` \(the default\)/i);
  assert.match(releaseNotes, /desktop Debate Copilot starts on German/i);
  assert.match(
    html,
    /supported <code>\.txt<\/code>, <code>\.md<\/code> and <code>\.docx<\/code> uploads are parsed/i,
  );
  assert.match(
    html,
    /A completely offline run requires local batch transcription/i,
  );
  assert.doesNotMatch(
    html,
    /Uploaded documents are read on this machine and never sent as files/i,
  );
  assert.match(
    comparison,
    /Conditional -- local ONNX transcription and diarization/i,
  );
  assert.doesNotMatch(
    comparison,
    /A fully local DebateAI runs end to end with Privacy First on/i,
  );
  assert.match(
    privacy,
    /supported <code>\.txt<\/code>, <code>\.md<\/code>, <code>\.markdown<\/code> and <code>\.docx<\/code>/i,
  );
  assert.doesNotMatch(
    privacy,
    /Uploaded documents are read on this machine and never sent as files/i,
  );
});

test("active website pages do not promise an offline pipeline by default", () => {
  const staleClaims = [
    /A fully local DebateAI runs end to end/i,
    /DebateAI(?: now)? runs end to end with Privacy First/i,
    /DebateAI[^.]{0,180}(?:whole|entire) pipeline runs/i,
    /there is no cloud caveat left/i,
  ];
  for (const [path, content] of customerContent) {
    if (/\/releases\//i.test(path)) continue;
    for (const pattern of staleClaims)
      assert.doesNotMatch(content, pattern, path);
  }
});

test("network failures keep the email valid and show an actionable retry", async () => {
  let submit;
  const emailAttributes = new Map();
  const button = { disabled: false };
  const status = { dataset: {}, textContent: "" };
  const email = {
    removeAttribute(name) {
      emailAttributes.delete(name);
    },
    setAttribute(name, value) {
      emailAttributes.set(name, value);
    },
  };
  const form = {
    addEventListener(_name, handler) {
      submit = handler;
    },
    querySelector() {
      return button;
    },
    removeAttribute() {},
    reportValidity() {
      return true;
    },
    reset() {},
    setAttribute() {},
  };
  const document = {
    getElementById(id) {
      return {
        "interest-form": form,
        "interest-email": email,
        "interest-status": status,
      }[id];
    },
  };
  class FakeFormData {
    get(name) {
      return name === "email" ? "person@example.com" : "turnstile-token";
    }
  }

  vm.runInNewContext(interestScript, {
    document,
    fetch: async () => {
      throw new TypeError("Failed to fetch");
    },
    FormData: FakeFormData,
    window: { turnstile: { reset() {} } },
  });
  submit({ preventDefault() {} });
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(
    status.textContent,
    "We couldn't save this right now. Please try again.",
  );
  assert.equal(emailAttributes.has("aria-invalid"), false);
  assert.equal(button.disabled, false);
});

test("customer guidance never uses GitHub as the executable access boundary", () => {
  const forbidden = [
    /github\.com\/[^\s"'<>)]*\/releases\/download\//i,
    /private GitHub repository/i,
    /(?:assets|bundles|executables)[^.\n]{0,100}attach(?:ed|es)?[^.\n]{0,100}GitHub release/i,
    /downloads?[^.\n]{0,120}(?:GitHub (?:login|account|membership)|authenticated GitHub access)/i,
    /(?:GitHub (?:login|account|membership)|authenticated GitHub access)[^.\n]{0,120}(?:downloads?|install)/i,
  ];
  for (const [path, content] of customerContent) {
    for (const pattern of forbidden)
      assert.doesNotMatch(content, pattern, path);
  }
});

test("customer download entry points use the authenticated DebateAI portal", () => {
  for (const path of [
    "../README.md",
    "../docs/HANDBUCH.md",
    "../site/index.html",
    "../site/private-meeting-ai/index.html",
    "../site/analyst-lenses/index.html",
    "../site/fireflies-alternative/index.html",
    "../site/granola-alternative/index.html",
    "../site/otter-alternative/index.html",
    "../site/vs-meetily/index.html",
    "../site/open-source-meeting-assistants/index.html",
    "../site/vs-anarlog/index.html",
    "../site/fathom-alternative/index.html",
    "../site/read-ai-alternative/index.html",
    "../site/gong-and-backchannel/index.html",
    "../site/vs-clari-copilot/index.html",
    "../site/teams-premium-alternative/index.html",
    "../site/plaud-alternative/index.html",
    "../site/llms.txt",
  ])
    assert.match(
      read(path),
      new RegExp(portal.replaceAll(".", "\\."), "i"),
      path,
    );
});

test("release archive metadata is unique and historical status is explicit", () => {
  const index = read("../site/releases/index.html");
  const itemList = index.slice(index.indexOf('"@type": "ItemList"'));
  const positions = [...itemList.matchAll(/"position":\s*(\d+)/g)].map(
    (match) => match[1],
  );
  assert.equal(new Set(positions).size, positions.length);
  assert.equal(positions.length, 29);
  assert.match(itemList, /"numberOfItems": 29/);
  assert.match(index, /Historical snapshot: v0\.6\.6/);
  assert.match(
    read("../site/releases/v0.6.6/index.html"),
    /historical release record/i,
  );
});

test("historical release pages deep-link only their own entitled version", () => {
  const releasePaths = new Set();
  for (const version of [
    "v0.1.0",
    "v0.1.1",
    "v0.2.0",
    "v0.2.1",
    "v0.2.2",
    "v0.2.3",
    "v0.2.4",
    "v0.2.5",
  ]) {
    const path = `../site/releases/${version}/index.html`;
    releasePaths.add(path);
    const content = read(path);
    assert.match(
      content,
      new RegExp(`${portal.replaceAll(".", "\\.")}\\?version=${version}`, "i"),
      path,
    );
    for (const other of [
      "v0.1.0",
      "v0.1.1",
      "v0.2.0",
      "v0.2.1",
      "v0.2.2",
      "v0.2.3",
      "v0.2.4",
      "v0.2.5",
    ]) {
      if (other !== version)
        assert.doesNotMatch(
          content,
          new RegExp(`/downloads/\\?version=${other}`, "i"),
          path,
        );
    }
  }
  for (const [path, content] of customerContent) {
    if (!releasePaths.has(path))
      assert.doesNotMatch(content, /\/downloads\/\?version=/i, path);
  }
});

test("public GitHub source, issue, license, and star links remain canonical", () => {
  const content = customerContent.map(([, value]) => value).join("\n");
  assert.match(
    content,
    /https:\/\/github\.com\/ErpeUser\/DebateAI-final-public(?:\.git)?["')\s]/i,
  );
  assert.match(
    content,
    /https:\/\/github\.com\/ErpeUser\/DebateAI-final-public\/issues/i,
  );
  assert.match(
    content,
    /https:\/\/github\.com\/ErpeUser\/DebateAI-final-public\/blob\/main\/LICENSE/i,
  );
  assert.match(
    read("../site/index.html"),
    /href="https:\/\/github\.com\/ErpeUser\/DebateAI-final-public"[^>]*>Star on GitHub/i,
  );
  assert.doesNotMatch(content, /talberthoule\/backchannel/i);
});

test("active docs use only checked-in pages and the canonical repository layout", () => {
  const docs = new Set(
    readdirSync(new URL("../docs/", import.meta.url))
      .filter((name) => name.endsWith(".md"))
      .map((name) => name.replace(/\.md$/, "")),
  );
  assert.deepEqual(
    [...docs].sort(),
    ["HANDBUCH", "HISTORIE", "OFFENE_PUNKTE", "VISION"].sort(),
  );
  const sourceFiles = [
    "../README.md",
    "../docs/HANDBUCH.md",
    "../site/index.html",
  ];
  for (const path of sourceFiles) {
    const content = read(path);
    for (const match of content.matchAll(
      /\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)/g,
    )) {
      const target = match[1];
      if (/^(?:https?:|mailto:|\/|#)/i.test(target)) continue;
      if (!target.endsWith(".md")) continue;
      const resolved = new URL(target, new URL(path, import.meta.url));
      const name = resolved.pathname.split("/").pop().replace(/\.md$/, "");
      assert.ok(
        docs.has(name),
        `${path} references missing docs page ${target}`,
      );
    }
    for (const match of content.matchAll(
      /(?:href|src)=["']([^"']*\/docs\/([^/#?]+)\/?)((?:[?#][^"']*)?)["']/g,
    )) {
      const target = match[2];
      if (target === "docs") continue;
      const docName =
        target === "index"
          ? "HANDBUCH"
          : target === "offene_punkte" || target === "vision" || target === "historie"
            ? target.toUpperCase()
            : target;
      assert.ok(
        docs.has(docName),
        `${path} references missing docs page ${target}`,
      );
    }
  }
  for (const name of docs) {
    const path = `../docs/${name}.md`;
    const content = read(path);
    for (const match of content.matchAll(
      /(?<!!)\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)/g,
    )) {
      const target = match[1];
      if (/^(?:https?:|mailto:|\/|#)/i.test(target) || !target.endsWith(".md"))
        continue;
      const resolved = new URL(target, new URL(path, import.meta.url));
      const targetName = resolved.pathname
        .split("/")
        .pop()
        .replace(/\.md$/, "");
      assert.ok(
        docs.has(targetName),
        `${path} references missing docs page ${target}`,
      );
    }
  }
  const active = sourceFiles.map((path) => read(path)).join("\n");
  assert.match(active, /ErpeUser\/DebateAI-final-public/);
  assert.match(active, /\bmain\b/);
  assert.doesNotMatch(
    active,
    /(?:cd|enter)\s+source\b|origin\/master|blob\/master/i,
  );
});

// Adding a page to this site is never one file: it also has to reach the
// sitewide footer, the sitemap, and llms.txt. Walking the directory rather
// than listing paths means a page added later is held to the same rule.
function everySitePage() {
  const root = new URL("../site/", import.meta.url);
  const found = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir)) {
      const child = new URL(
        `${entry}${statSync(new URL(entry, dir)).isDirectory() ? "/" : ""}`,
        dir,
      );
      if (child.href.endsWith("/")) walk(child);
      else if (entry === "index.html") found.push(child);
    }
  };
  walk(root);
  return found;
}

test("the privacy deep-dive is reachable from every page that carries the footer", () => {
  const target = "/private-meeting-ai/";
  const orphans = [];
  let carriers = 0;
  for (const page of everySitePage()) {
    const content = readFileSync(page, "utf8");
    if (!content.includes("footer-compare")) continue;
    carriers += 1;
    if (!content.includes(`href="${target}"`)) orphans.push(page.pathname);
  }
  assert.ok(
    carriers > 20,
    `expected the footer on most pages, saw ${carriers}`,
  );
  assert.deepEqual(
    orphans,
    [],
    "pages carrying the footer but not linking the privacy page",
  );
});

test("the privacy deep-dive is indexed for crawlers and for agents", () => {
  assert.match(
    read("../site/sitemap.xml"),
    /<loc>\/private-meeting-ai\/<\/loc>/,
  );
  assert.match(read("../site/llms.txt"), /\/private-meeting-ai\//);
  assert.match(
    read("../site/private-meeting-ai/index.html"),
    /rel="canonical" href="\/private-meeting-ai\/"/,
  );
});

test("the analyst lenses walkthrough is linked, indexed, and ships both themes of every shot", () => {
  const page = read("../site/analyst-lenses/index.html");
  assert.match(read("../site/sitemap.xml"), /<loc>\/analyst-lenses\/<\/loc>/);
  assert.match(read("../site/llms.txt"), /\/analyst-lenses\//);
  assert.match(page, /rel="canonical" href="\/analyst-lenses\/"/);
  const agents = html.split('<section id="agents"')[1].split("</section>")[0];
  assert.match(agents, /href="\/analyst-lenses\/"/);
  assert.match(
    page,
    /<script src="\/analyst-lenses\/walkthrough\.js" defer><\/script>/,
  );
  statSync(new URL("../site/analyst-lenses/walkthrough.js", import.meta.url));
  // The walkthrough styles live beside the page, not in style.css, which sits
  // at the structural gate's 3000-line limit (sentrux max_file_lines).
  assert.match(
    page,
    /<link rel="stylesheet" href="\/analyst-lenses\/walkthrough\.css" \/>/,
  );
  statSync(new URL("../site/analyst-lenses/walkthrough.css", import.meta.url));
  assert.doesNotMatch(read("../site/style.css"), /\.lw-/);

  // Every screenshot the page references exists, and each has its other-theme twin.
  const shots = new Set(
    [...page.matchAll(/\/assets\/lenses\/([a-z-]+?)(?:-dark)?\.webp/g)].map(
      (m) => m[1],
    ),
  );
  assert.ok(
    shots.size >= 4,
    `expected the page to show its captures, saw ${shots.size}`,
  );
  for (const stem of shots) {
    for (const file of [`${stem}.webp`, `${stem}-dark.webp`]) {
      statSync(new URL(`../site/assets/lenses/${file}`, import.meta.url));
    }
  }

  // The lenses are prompt sections of one call with a fixed reply shape; the
  // page must not describe them otherwise.
  assert.doesNotMatch(page, /dynamic schema|agent-like/i);
  assert.match(
    page,
    /Step 1 sketches the design DebateAI avoids, so its three findings are examples/,
  );
});

test("the sitemap remains a same-host index while public pages link to the portal", () => {
  const sitemap = read("../site/sitemap.xml");
  const locations = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(
    (match) => match[1],
  );
  assert.ok(locations.length > 0);
  assert.ok(locations.every((location) => location.startsWith("/")));
  assert.doesNotMatch(sitemap, /\/downloads/i);
  assert.match(read("../site/index.html"), /\/downloads\//i);
});

test("historical migration normalizes peeled commit timestamps to strict UTC", () => {
  const releasing = read("../docs/HANDBUCH.md");
  assert.match(releasing, /\[DateTimeOffset\]::Parse/);
  assert.match(
    releasing,
    /\.UtcDateTime\.ToString\("yyyy-MM-dd'T'HH:mm:ss'Z'"/,
  );
  for (const version of ["v0.1.0", "v0.1.1", "v0.2.0", "v0.2.1"]) {
    assert.match(
      releasing,
      new RegExp(`git rev-parse ['"]${version}\\^\\{commit\\}['"]`),
    );
  }
  assert.doesNotMatch(
    releasing,
    /\$v\d+Time\s*=\s*\(& git show[^\n]+\)\.Trim\(\)/,
  );
});

test("production deployment always rebuilds immediately before Wrangler deploy", () => {
  const deployment = read("../docs/HANDBUCH.md");
  assert.match(deployment, /^npm run deploy$/m);
  assert.doesNotMatch(deployment, /^npx wrangler deploy$/m);
  assert.match(
    deployment,
    /never deploy (?:a )?preexisting `dist-site`|fresh build immediately before deploy/i,
  );
});

test("rollout order documents a real hold gate before catalog publication", () => {
  const deployment = read("../docs/HANDBUCH.md");
  const releasing = read("../docs/HANDBUCH.md");
  for (const runbook of [deployment, releasing]) {
    assert.match(runbook, /No executable hold commit is currently recorded/i);
    assert.match(runbook, /git cat-file -e <hold-sha>\^\{commit\}/);
    assert.match(
      runbook,
      /git merge-base --is-ancestor <hold-sha> origin\/main/,
    );
    assert.doesNotMatch(runbook, /git merge-base --is-ancestor [0-9a-f]{40}/);
    assert.doesNotMatch(runbook, /git revert [0-9a-f]{40}/);
  }
  assert.match(deployment, /Migrate `v0\.1\.0` once as the seed/i);
  assert.match(deployment, /Do not migrate the\s+seed version again/i);
});

test("staged link cutover never embeds an invented commit", () => {
  for (const path of ["../docs/HANDBUCH.md"]) {
    const runbook = read(path);
    assert.doesNotMatch(runbook, /git revert [0-9a-f]{40}/);
    assert.match(runbook, /create a dedicated hold commit/i);
  }
  assert.match(
    read("../docs/HANDBUCH.md"),
    /Follow \[Deployment\]\(HANDBUCH\.md#deployment-und-betrieb\).*ordered gate/is,
  );
});

test("D1 exports require operator-supplied absolute paths outside the repository", () => {
  const deployment = read("../docs/HANDBUCH.md");
  assert.match(deployment, /DEBATEAI_D1_BACKUP_PATH/);
  assert.match(deployment, /\[IO\.Path\]::IsPathRooted\(/);
  assert.match(deployment, /--output="\$backupPath"/);
  assert.doesNotMatch(
    deployment,
    /--output=(?:debateai-interest-backup|interest-subscribers)\.sql/,
  );
});

test("progressive release recovery names the platform boundary precisely", () => {
  const releasing = read("../docs/HANDBUCH.md");
  assert.match(
    releasing,
    /failure before one platform's manifest is created leaves that platform\s+hidden/i,
  );
  assert.match(
    releasing,
    /Latest may name the progressive\s+release as soon as its first platform is complete/i,
  );
  assert.match(releasing, /GitHub note creation fails after Latest advances/i);
  assert.doesNotMatch(releasing, /point Latest at a partial release/i);
});
