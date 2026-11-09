import type { Session, SessionSynthesis, SynthesisSectionItem } from "../../types";

// The briefing's layout rules as plain data, with no React in the way: which
// section names a meeting type uses, which items are readable, which sections
// sit side by side, and what the footer says about sections that came back
// empty. BriefingView renders whatever this produces.

// Section names are sentence case in source. The heading style sets them as
// small caps, and the same string reads naturally in the "not captured" note.
export function sectionLabels(session: Pick<Session, "meeting_type">) {
  switch (session.meeting_type) {
    case "internal_enablement":
      return {
        objectives: "Lernziele",
        opportunities: "Befähigungschancen",
        questions: "Offene Lernfragen",
      };
    case "internal_checkin":
      return {
        objectives: "Ziele und Bedürfnisse",
        opportunities: "Unterstützungschancen",
        questions: "Offene Fragen",
      };
    case "vendor_partner":
      return {
        objectives: "Anbieter- und Programmziele",
        opportunities: "Partnerchancen",
        questions: "Offene Anbieter- und Programmfragen",
      };
    case "customer_delivery":
      return {
        objectives: "Projektziele",
        opportunities: "Umsetzungschancen",
        questions: "Offene Umsetzungsfragen",
      };
    case "client_sales":
      return {
        objectives: "Kundenziele",
        opportunities: "Wichtigste Chancen",
        questions: "Ungeklärte Analysefragen",
      };
    default:
      return {
        objectives: "Ziele",
        opportunities: "Wichtigste Chancen",
        questions: "Offene Fragen",
      };
  }
}

// An item with neither a title nor a summary has nothing to read and is
// dropped before it can render as an empty row or count toward a section.
export function presentItems(items: SynthesisSectionItem[] | null | undefined): SynthesisSectionItem[] {
  return (items || []).filter((item) => (item.title || "").trim() || (item.summary || "").trim());
}

// "a", "a and b", "a, b, and c".
export function formatList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return `${items[0]} und ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} und ${items[items.length - 1]}`;
}

export interface SectionSpec {
  key: string;
  label: string;
  items: SynthesisSectionItem[];
}

// A block is one row of the page. A pair only exists when both of its
// sections have content; otherwise the survivor takes the full measure.
export type SectionBlock =
  | { kind: "lead"; section: SectionSpec }
  | { kind: "single"; section: SectionSpec }
  | { kind: "pair"; cols: string; sections: [SectionSpec, SectionSpec] };

export interface BriefingLayout {
  blocks: SectionBlock[];
  missingNote: string | null;
}

// The action plan takes the wider column: it is the list a reader acts on.
export const ACTION_RISK_COLS = "lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]";
export const EVEN_COLS = "lg:grid-cols-2";

function pairOrSingles(a: SectionSpec, b: SectionSpec, cols: string): SectionBlock[] {
  if (a.items.length > 0 && b.items.length > 0) return [{ kind: "pair", cols, sections: [a, b] }];
  return [a, b].filter((section) => section.items.length > 0).map((section) => ({ kind: "single", section }));
}

export function buildBriefingLayout(
  session: Pick<Session, "meeting_type">,
  synthesis: SessionSynthesis | null,
): BriefingLayout {
  if (!synthesis) return { blocks: [], missingNote: null };
  const labels = sectionLabels(session);
  const spec = (key: string, label: string, items: SynthesisSectionItem[] | null | undefined): SectionSpec => ({
    key,
    label,
    items: presentItems(items),
  });

  const outcomes = spec("outcomes", "Wichtigste Ergebnisse", synthesis.top_outcomes);
  const actions = spec("actions", "Aktionsplan", synthesis.action_plan);
  const risks = spec("risks", "Risiken und Hindernisse", synthesis.risks_blockers);
  const objectives = spec("objectives", labels.objectives, synthesis.client_objectives);
  const opportunities = spec("opportunities", labels.opportunities, synthesis.top_opportunities);
  const questions = spec("questions", labels.questions, synthesis.unresolved_discovery_questions);
  const signals = spec("signals", "Strategische Signale", synthesis.strategic_signals);

  const blocks: SectionBlock[] = [];
  if (outcomes.items.length > 0) blocks.push({ kind: "lead", section: outcomes });
  blocks.push(...pairOrSingles(actions, risks, ACTION_RISK_COLS));
  blocks.push(...pairOrSingles(objectives, opportunities, EVEN_COLS));
  if (questions.items.length > 0) blocks.push({ kind: "single", section: questions });
  if (signals.items.length > 0) blocks.push({ kind: "single", section: signals });

  // Signals are optional output, so only the six core sections are named
  // when they come back empty.
  const core = [outcomes, actions, risks, objectives, opportunities, questions];
  const missing = core.filter((section) => section.items.length === 0).map((section) => section.label.toLowerCase());
  const missingNote =
    missing.length === 0
      ? null
      : missing.length === core.length
        ? "In diesem Briefing wurde noch nichts erfasst."
        : `In diesem Briefing nicht erfasst: ${formatList(missing)}.`;

  return { blocks, missingNote };
}
