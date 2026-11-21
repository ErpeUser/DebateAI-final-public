import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const componentPath = fileURLToPath(new URL("./DebateCoachPanel.tsx", import.meta.url));
const outputDir = await mkdtemp(join(tmpdir(), "debate-panel-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  stdin: {
    contents: `
      import React from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      import DebateCoachPanel from "./DebateCoachPanel.tsx";
      export function render(props) {
        return renderToStaticMarkup(React.createElement(DebateCoachPanel, props));
      }
    `,
    resolveDir: dirname(componentPath),
    sourcefile: "debate-panel-test-entry.tsx",
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

const activity = (state, overrides = {}) => ({
  slug: "objection_handler",
  name: "Debate Copilot",
  trigger: "event",
  state,
  enabled: true,
  blocked_reason: "",
  remedy: "",
  interval_seconds: null,
  last_run_started_at: null,
  last_run_ms: null,
  next_due_at: null,
  last_outcome: null,
  last_error: null,
  counts: { runs: 0, insights: 0, deduped: 0, errors: 0 },
  ...overrides,
});

const ready = {
  answer_now: "Die aktuelle Zahl stuetzt diese Schlussfolgerung nicht.",
  counterargument: "Eine einzelne Zahl belegt noch keinen dauerhaften Trend.",
  counter_question: "Welche Vergleichsbasis verwenden Sie?",
  primary_move: "answer",
  question_status: "partial",
  open_question: "Welche Vergleichsbasis gilt hier?",
  follow_ups: [{
    condition: "Wenn keine Vergleichsbasis genannt wird",
    question: "Warum soll die Einzelzahl dann genuegen?",
  }],
  analogy: "Das ist wie ein einzelnes Foto, das noch keinen ganzen Film beweist.",
  target_claim: "Die Inflation lag bei acht Prozent.",
  argument_points: [
    "Amtlich wurden 2,2 Prozent gemessen",
    "Acht Prozent widersprechen der Erhebung",
    "Eine Einzelzahl belegt keinen dauerhaften Trend",
    "Dieser vierte Nebenpunkt soll nicht die Live-Ansicht ueberladen",
  ],
  research_alert: "Gegenbeleg gefunden: Die amtliche Rate lag deutlich darunter.",
  confidence: "low",
  needs_research: false,
  research_query: "Inflationsrate Deutschland 2025",
  research_status: "completed",
  sources: [{
    title: "Amtliche Inflationsrate",
    url: "https://example.test/inflation",
    snippet: "Die amtliche Rate lag bei 2,2 Prozent.",
    verification_status: "found",
    passage: "",
    published_at: "",
    provider: "test",
    claim: "Die Inflation lag bei acht Prozent.",
  }],
  revision: 3,
  generated_at: "2026-11-02T10:05:00Z",
};

test("ready state renders one primary speaking move and keeps the alternative secondary", () => {
  const html = render({ recommendation: ready, activity: activity("waiting") });

  assert.match(html, /Sofortsatz/);
  assert.match(html, /JETZT SAGEN/);
  assert.match(html, /data-priority="primary"/);
  assert.doesNotMatch(html, /data-priority="alternative"/);
  assert.match(html, /Wird bei neuen Worten laufend aktualisiert/);
  assert.match(html, /Gegenfrage/);
  assert.equal((html.match(/<article/g) || []).length, 1);
  assert.match(html, /Alternative anzeigen/);
  assert.ok(html.indexOf("Sofortsatz") < html.indexOf("Gegenfrage"));
  assert.match(html, /Kernargument/);
  assert.match(html, /Eine einzelne Zahl belegt noch keinen dauerhaften Trend/);
  assert.match(html, /einzelnes Foto/);
  assert.match(html, /Die aktuelle Zahl/);
  assert.match(html, /Aktualisiert/);
  assert.match(html, /Fixieren/);
  assert.match(html, /Kopieren/);
});

test("ready state offers all compact manual debate actions without adding prompt panels", () => {
  const html = render({ recommendation: ready, activity: activity("waiting"), onQuickAction: () => {} });

  for (const label of ["Widerlegen", "Gegenfrage", "Prämissen prüfen", "Doppelstandard", "Faktencheck", "Originalquelle", "Besonders gründlich"]) {
    assert.match(html, new RegExp(label.replace("&", "&amp;")));
  }
  assert.equal((html.match(/data-quick-action=/g) || []).length, 16);
  assert.equal((html.match(/<article/g) || []).length, 1);
});

test("question-first recommendation makes only the question the primary card", () => {
  const html = render({
    recommendation: { ...ready, primary_move: "question" },
    activity: activity("waiting"),
  });

  const article = html.match(/<article[\s\S]*?<\/article>/)?.[0] ?? "";
  assert.equal((html.match(/<article/g) || []).length, 1);
  assert.match(article, /Gegenfrage/);
  assert.doesNotMatch(article, /Sofortsatz/);
  assert.match(html, /Alternative anzeigen/);
});

test("question-only recommendation renders without empty alternative placeholders", () => {
  const html = render({
    recommendation: {
      ...ready,
      answer_now: "",
      counterargument: "",
      analogy: "",
      primary_move: "question",
    },
    activity: activity("waiting"),
  });

  assert.equal((html.match(/<article/g) || []).length, 1);
  assert.match(html, /Welche Vergleichsbasis verwenden Sie/);
  assert.doesNotMatch(html, /Noch keine belastbare Formulierung/);
  assert.doesNotMatch(html, /Alternative anzeigen/);
});

test("analogy and question context stay compact instead of becoming extra cards", () => {
  const html = render({ recommendation: ready, activity: activity("waiting") });

  assert.equal((html.match(/<article/g) || []).length, 1);
  assert.match(html, /Passende Analogie/);
  assert.match(html, /Teilweise beantwortet/);
  assert.match(html, /Welche Vergleichsbasis gilt hier/);
  assert.match(html, /Wenn keine Vergleichsbasis genannt wird/);
  assert.match(html, /Mehr Strategie &amp; Quellen/);
});

test("completed research shows only the three strongest evidence points", () => {
  const html = render({ recommendation: ready, activity: activity("waiting") });

  assert.match(html, /Recherche-Kernpunkte/);
  assert.match(html, /Amtlich wurden 2,2 Prozent gemessen/);
  assert.match(html, /Acht Prozent widersprechen der Erhebung/);
  assert.match(html, /Eine Einzelzahl belegt keinen dauerhaften Trend/);
  assert.doesNotMatch(html, /Dieser vierte Nebenpunkt/);
  assert.doesNotMatch(html, /Argumente erkannt/);
});

test("unresearched argument parsing does not crowd the speaking view", () => {
  const html = render({
    recommendation: { ...ready, research_status: "idle", sources: [] },
    activity: activity("waiting"),
  });

  assert.doesNotMatch(html, /Recherche-Kernpunkte/);
  assert.match(html, /Argumentstruktur/);
  assert.match(html, /Amtlich wurden 2,2 Prozent gemessen/);
  assert.match(html, /Dieser vierte Nebenpunkt/);
  assert.equal((html.match(/<article/g) || []).length, 1);
});

test("running activity keeps the previous guidance visible", () => {
  const html = render({ recommendation: ready, activity: activity("running") });

  assert.match(html, /Die aktuelle Zahl/);
  assert.match(html, /Optimiert im Hintergrund/);
  assert.doesNotMatch(html, /Die nächste Sprechspur erscheint hier/);
});

test("manual deep analysis exposes a cancel action while automatic work does not", () => {
  const manual = render({
    recommendation: { ...ready, analysis_status: "analyzing", analysis_can_cancel: true },
    activity: activity("running"),
    onCancelAnalysis: () => {},
  });
  const automatic = render({
    recommendation: { ...ready, analysis_status: "analyzing", analysis_can_cancel: false },
    activity: activity("running"),
    onCancelAnalysis: () => {},
  });

  assert.match(manual, /Tiefenanalyse abbrechen/);
  assert.doesNotMatch(automatic, /Tiefenanalyse abbrechen/);
});

test("completed deep analysis hides provider internals in the live card", () => {
  const html = render({
    recommendation: { ...ready, analysis_status: "completed", analyst_provider: "gemini-cli-oauth" },
    activity: activity("waiting"),
  });

  assert.match(html, /Vertiefung abgeschlossen/);
  assert.doesNotMatch(html, /gemini-cli-oauth/);
});

test("low confidence is explicitly unverified and sources stay claim-linked", () => {
  const html = render({ recommendation: ready, activity: activity("waiting"), onResearch: () => {} });

  assert.match(html, /Quelle unklar/);
  assert.match(html, /Gefunden zu/);
  assert.match(html, /Gepr.*fte Aussage:.*Inflation lag bei acht Prozent/s);
  assert.match(html, /target="_blank"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(html, /Gegenbeleg gefunden/);
  assert.match(html, /Recherche-Kernpunkte/);
  assert.match(html, /Widerlegung suchen/);
  assert.match(html, /Übersetzung prüfen/);
  assert.match(html, /Interpretation prüfen/);
  assert.match(html, /Alles neu prüfen/);
});

test("a search snippet is labelled as found, never as proof", () => {
  const markup = render({ recommendation: ready, activity: null });

  assert.match(markup, /Gefunden zu/);
  assert.doesNotMatch(markup, /Belegt zu:/);
});

test("the live panel exposes an explicit Jetzt recherchieren action", () => {
  const html = render({
    recommendation: ready,
    activity: activity("waiting"),
    onResearch: () => {},
  });

  assert.match(html, /data-research-action="primary"/);
  assert.match(html, /Jetzt recherchieren/);
});

test("live research switch can be off while manual checks remain available", () => {
  const html = render({
    recommendation: ready,
    activity: activity("waiting"),
    onResearch: () => {},
    researchEnabled: false,
    onResearchEnabledChange: () => {},
  });

  assert.match(html, /Auto-Recherche aus/);
  assert.match(html, /Manuell suchen bleibt/);
  assert.match(html, /Widerlegung suchen/);
});

test("der Datenschutzmodus deaktiviert jede öffentliche Live-Recherche ehrlich", () => {
  const html = render({
    recommendation: ready,
    activity: activity("waiting"),
    onResearch: () => {},
    researchEnabled: true,
    onResearchEnabledChange: () => {},
    privacyFirst: true,
  });

  assert.match(html, /Datenschutzmodus blockiert öffentliche Recherche/);
  assert.doesNotMatch(html, /Manuell suchen bleibt/);
  assert.match(html, /Auto-Recherche an/);
  assert.match(html, /aria-checked="true"[^>]*disabled=""/s);
  assert.match(html, /data-research-action="counterevidence"[^>]*disabled=""/s);
});

test("loading state reserves a calm analysis region", () => {
  const html = render({ recommendation: null, activity: activity("running") });
  assert.match(html, /Analysiert den neuesten Beitrag/);
  assert.match(html, /role="status"/);
});

test("blocked state explains the remedy", () => {
  const html = render({
    recommendation: null,
    activity: activity("blocked", { remedy: "Lokales Modell auswählen." }),
  });
  assert.match(html, /Assistent nicht verfügbar/);
  assert.match(html, /Lokales Modell auswählen/);
});

test("error state keeps the failure visible without raw internals", () => {
  const html = render({
    recommendation: null,
    activity: activity("failing", {
      last_error: { kind: "api_error", detail: "Modell antwortet nicht.", remedy: "Modell prüfen.", at: "2026-11-02T10:05:00Z" },
    }),
  });
  assert.match(html, /Empfehlung gerade nicht verfügbar/);
  assert.match(html, /Modell prüfen/);
  assert.match(html, /role="alert"/);
});
