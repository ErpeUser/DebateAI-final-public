import {
  AlertTriangle,
  Copy,
  HelpCircle,
  Lightbulb,
  Loader2,
  Languages,
  MessageSquare,
  Pin,
  PinOff,
  Radio,
  RefreshCw,
  Search,
  Square,
  ThumbsUp,
} from "lucide-react";
import { useState } from "react";
import { DE } from "../../i18n/de";
import SourceInspector from "../SourceInspector";
import type {
  AgentActivityRecord,
  DebateRecommendation,
  DebateResearchCategory,
  ExternalLaneArtifact,
} from "../../types";

interface DebateCoachPanelProps {
  sessionId: string;
  recommendation: DebateRecommendation | null;
  activity: AgentActivityRecord | null;
  onResearch?: (category: DebateResearchCategory) => void;
  researchEnabled?: boolean;
  privacyFirst?: boolean;
  onResearchEnabledChange?: (enabled: boolean) => void;
  onQuickAction?: (directive: string) => void;
  onGoodAnswer?: (claimId: string, recommendationRevision: number) => void;
  onExperimentalOptionSelected?: (
    claimId: string,
    recommendationRevision: number,
    optionId: string,
  ) => void;
  onCancelAnalysis?: () => void;
}

const quickActions = [
  ["rebuttal", "Widerlegen", "Strategie: Widerlegung"],
  [
    "counter_question",
    "Gegenfrage",
    "Strategie: Gegenfrage zur tragenden Prämisse",
  ],
  ["line_by_line", "Zeile für Zeile", "Strategie: Zeile für Zeile"],
  ["weigh_impacts", "Folgen abwägen", "Strategie: Folgen abwägen"],
  ["concede_pivot", "Zugestehen & drehen", "Strategie: Zugestehen und drehen"],
  ["premises", "Prämissen prüfen", "Strategie: Prämissen und Schluss prüfen"],
  ["contradiction", "Widerspruch", "Strategie: Logischen Widerspruch prüfen"],
  ["fallacy", "Fehlschluss", "Strategie: Möglichen Fehlschluss prüfen"],
  [
    "double_standard",
    "Doppelstandard",
    "Strategie: Doppelstandard und gleiche Maßstäbe prüfen",
  ],
  ["burden", "Beweislast", "Strategie: Beweislast klar zuordnen"],
  ["analogy", "Analogie", "Strategie: Treffende Analogie liefern"],
  [
    "open_question",
    "Offene Frage",
    "Strategie: Offene Frage wieder aufgreifen",
  ],
  ["fact_check", "Faktencheck", "Debate AI, Faktencheck zum aktuellen Claim"],
  ["statistics", "Zahlen prüfen", "Debate AI, Zahlen und Statistik prüfen"],
  [
    "original_source",
    "Originalquelle",
    "Debate AI, Originalquelle suchen und lesen",
  ],
  ["deep", "Besonders gründlich", "Debate AI, besonders gründlich analysieren"],
] as const;

const answerMove = {
  key: "answer_now",
  label: "Sofortsatz",
  icon: MessageSquare,
} as const;

const questionMove = {
  key: "counter_question",
  label: "Gegenfrage",
  icon: HelpCircle,
} as const;

const questionStatusLabels: Record<
  DebateRecommendation["question_status"],
  string
> = {
  none: "",
  open: "Offene Frage",
  partial: "Teilweise beantwortet",
  answered: "Beantwortet",
  unclear: "Antwort unklar",
  evaded: "Frage umgangen",
};

function confidenceLabel(confidence: DebateRecommendation["confidence"]) {
  if (confidence === "high") return "Hohe Sicherheit";
  if (confidence === "medium") return "Mittlere Sicherheit";
  return DE.live.runtimeStatus.sourceUnclear;
}

function formattedTime(value: string) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "gerade eben";
  return date.toLocaleTimeString("de-AT", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function EmptyState({ activity }: { activity: AgentActivityRecord | null }) {
  if (activity?.state === "failing") {
    return (
      <div
        role="alert"
        className="flex min-h-20 items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800 dark:border-red-900/70 dark:bg-red-950/30 dark:text-red-200"
      >
        <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-body text-sm font-semibold">
            Empfehlung gerade nicht verfügbar
          </p>
          <p className="mt-0.5 font-body text-xs leading-5">
            {activity.last_error?.remedy ||
              "Das lokale Modell prüfen und den nächsten Beitrag abwarten."}
          </p>
        </div>
      </div>
    );
  }

  if (activity?.state === "blocked" || activity?.state === "off") {
    return (
      <div
        role="status"
        className="min-h-20 rounded-lg border border-amber-300/80 bg-amber-50 px-4 py-3 text-amber-950 dark:border-amber-700/70 dark:bg-amber-950/30 dark:text-amber-100"
      >
        <p className="font-body text-sm font-semibold">
          Assistent nicht verfügbar
        </p>
        <p className="mt-0.5 font-body text-xs leading-5">
          {activity.remedy ||
            "Den Debate Copilot unter Admin → Agents aktivieren."}
        </p>
      </div>
    );
  }

  if (activity?.state === "running") {
    return (
      <div
        role="status"
        className="flex min-h-20 items-center gap-3 rounded-lg border border-brand-teal/30 bg-brand-teal/5 px-4 py-3 text-brand-dark-gray"
      >
        <Loader2
          aria-hidden="true"
          className="h-4 w-4 shrink-0 animate-spin text-brand-teal motion-reduce:animate-none"
        />
        <div>
          <p className="font-body text-sm font-semibold">
            Analysiert den neuesten Beitrag
          </p>
          <p className="mt-0.5 font-body text-xs text-brand-gray">
            Die nächste Sprechspur erscheint hier.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      role="status"
      className="min-h-20 rounded-lg border border-dashed border-brand-light-gray-1 bg-brand-light-gray-2 px-4 py-3"
    >
      <p className="font-body text-sm font-semibold text-brand-dark-gray">
        Bereit für den nächsten Beitrag
      </p>
      <p className="mt-0.5 font-body text-xs leading-5 text-brand-gray">
        Der Copilot reagiert auf Aussagen, Fragen und Einwände im Gespräch.
      </p>
    </div>
  );
}

export default function DebateCoachPanel({
  sessionId,
  recommendation: liveRecommendation,
  activity,
  onResearch,
  researchEnabled = false,
  privacyFirst = false,
  onResearchEnabledChange,
  onQuickAction,
  onGoodAnswer,
  onExperimentalOptionSelected,
  onCancelAnalysis,
}: DebateCoachPanelProps) {
  const [pinnedRecommendation, setPinnedRecommendation] =
    useState<DebateRecommendation | null>(null);
  const [copied, setCopied] = useState(false);
  const recommendation = pinnedRecommendation ?? liveRecommendation;
  const pinnedVersion =
    pinnedRecommendation?.recommendation_revision ??
    pinnedRecommendation?.revision ??
    0;
  const liveVersion =
    liveRecommendation?.recommendation_revision ??
    liveRecommendation?.revision ??
    0;
  const hasNewVersion = Boolean(
    pinnedRecommendation &&
    liveRecommendation &&
    (liveRecommendation.claim_id !== pinnedRecommendation.claim_id ||
      liveVersion > pinnedVersion),
  );
  const centralCorrection =
    hasNewVersion &&
    liveRecommendation?.research_alert &&
    liveRecommendation.research_alert !== pinnedRecommendation?.research_alert
      ? liveRecommendation.research_alert
      : "";
  const selectedOption =
    recommendation?.pipeline_mode === "experimental_debateai"
      ? recommendation.strategy_options?.find(
          (option) => option.id === recommendation.selected_strategy_id,
        )
      : undefined;
  const preferredMove =
    recommendation?.primary_move === "question" ? questionMove : answerMove;
  const fallbackMove =
    preferredMove.key === "counter_question" ? answerMove : questionMove;
  const primaryMove =
    recommendation?.pipeline_mode === "experimental_debateai"
      ? {
          key: "answer_now" as const,
          label: selectedOption?.title || "Sofortsatz",
          icon: MessageSquare,
        }
      : recommendation?.[preferredMove.key]
        ? preferredMove
        : fallbackMove;
  const alternativeMove =
    primaryMove.key === "counter_question" ? answerMove : questionMove;
  const primaryText =
    recommendation?.pipeline_mode === "experimental_debateai"
      ? recommendation.answer_now
      : (recommendation?.[primaryMove.key] ?? "");
  const alternativeText =
    recommendation?.pipeline_mode === "experimental_debateai"
      ? ""
      : (recommendation?.[alternativeMove.key] ?? "");
  const copyRecommendation = async () => {
    const text = primaryText || recommendation?.counterargument || "";
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  const hasGuidance = Boolean(
    recommendation &&
    (recommendation.answer_now || recommendation.counter_question),
  );
  const questionStatus = recommendation
    ? questionStatusLabels[recommendation.question_status ?? "none"]
    : "";
  const nextFollowUp = recommendation?.follow_ups?.[0];
  const researchPoints =
    recommendation?.research_status === "completed"
      ? recommendation.argument_points.slice(0, 3)
      : [];
  const strategyPoints =
    recommendation?.research_status !== "completed"
      ? (recommendation?.argument_points.slice(0, 4) ?? [])
      : [];
  const laneArtifacts: ExternalLaneArtifact[] =
    recommendation?.pipeline_mode === "experimental_debateai"
      ? (recommendation.external_lane_artifacts ?? [])
      : [];

  return (
    <section aria-labelledby="debate-coach-title" className="px-4 pb-3">
      <div className="rounded-xl border border-brand-light-gray-1 bg-surface shadow-sm">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-light-gray-1 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="bc-accent-text relative flex h-7 w-7 items-center justify-center rounded-full bg-brand-teal/10">
              <Radio aria-hidden="true" className="h-4 w-4" />
              <span className="absolute right-0 top-0 h-2 w-2 rounded-full border-2 border-surface bg-brand-teal" />
            </span>
            <div>
              <h2
                id="debate-coach-title"
                className="font-display text-sm font-semibold text-brand-dark-gray"
              >
                Sprechspur
              </h2>
              <p className="font-body text-[11px] text-brand-gray">
                Live-Debattenassistent
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-1.5 font-body text-[10px]">
            {hasGuidance && recommendation && (
              <>
                <button
                  type="button"
                  onClick={() =>
                    setPinnedRecommendation(
                      pinnedRecommendation ? null : recommendation,
                    )
                  }
                  className="inline-flex items-center gap-1 rounded-full border border-brand-light-gray-1 px-2 py-1 font-semibold text-brand-gray hover:border-brand-teal/40 hover:text-brand-dark-gray"
                  title={
                    pinnedRecommendation
                      ? "Fixierung lösen"
                      : "Diese Sprechkarte sichtbar halten"
                  }
                >
                  {pinnedRecommendation ? (
                    <PinOff aria-hidden="true" className="h-3 w-3" />
                  ) : (
                    <Pin aria-hidden="true" className="h-3 w-3" />
                  )}
                  {pinnedRecommendation
                    ? `Fixiert v${pinnedVersion || "-"}`
                    : "Fixieren"}
                </button>
                <button
                  type="button"
                  onClick={() => void copyRecommendation()}
                  className="inline-flex items-center gap-1 rounded-full border border-brand-light-gray-1 px-2 py-1 font-semibold text-brand-gray hover:border-brand-teal/40 hover:text-brand-dark-gray"
                >
                  <Copy aria-hidden="true" className="h-3 w-3" />
                  {copied ? "Kopiert" : "Kopieren"}
                </button>
              </>
            )}
            <button
              type="button"
              role="switch"
              aria-checked={researchEnabled}
              onClick={() => onResearchEnabledChange?.(!researchEnabled)}
              disabled={!onResearchEnabledChange || privacyFirst}
              className={`rounded-full border px-2 py-1 font-semibold ${
                researchEnabled
                  ? "border-brand-teal/40 bg-brand-teal/10 text-brand-teal"
                  : "border-brand-light-gray-1 text-brand-gray"
              } disabled:opacity-50`}
              title={
                privacyFirst
                  ? "Der Datenschutzmodus blockiert öffentliche Recherche"
                  : "Manuelle Recherche bleibt verfügbar"
              }
            >
              Auto-Recherche {researchEnabled ? "an" : "aus"}
            </button>
            {hasGuidance && recommendation?.analysis_status === "analyzing" && (
              <span className="bc-accent-text inline-flex items-center gap-1 rounded-full bg-brand-teal/10 px-2 py-1 font-semibold">
                <Loader2
                  aria-hidden="true"
                  className="h-3 w-3 animate-spin motion-reduce:animate-none"
                />
                {DE.live.runtimeStatus.deepening}
              </span>
            )}
            {hasGuidance &&
              recommendation?.analysis_status === "analyzing" &&
              recommendation.analysis_can_cancel && (
                <button
                  type="button"
                  onClick={onCancelAnalysis}
                  disabled={!onCancelAnalysis}
                  className="inline-flex items-center gap-1 rounded-full border border-red-300 bg-red-50 px-2 py-1 font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200"
                >
                  <Square aria-hidden="true" className="h-3 w-3" />
                  Tiefenanalyse abbrechen
                </button>
              )}
            {hasGuidance && recommendation?.analysis_status === "cancelled" && (
              <span className="rounded-full bg-brand-light-gray-2 px-2 py-1 font-semibold text-brand-gray">
                Tiefenanalyse abgebrochen
              </span>
            )}
            {hasGuidance && recommendation?.analysis_status === "completed" && (
              <span className="bc-accent-text rounded-full bg-brand-teal/10 px-2 py-1 font-semibold">
                {DE.live.runtimeStatus.deepeningComplete}
              </span>
            )}
            {hasGuidance &&
              activity?.state === "running" &&
              recommendation?.analysis_status !== "analyzing" && (
                <span className="bc-accent-text inline-flex items-center gap-1 rounded-full bg-brand-teal/10 px-2 py-1 font-semibold">
                  <Loader2
                    aria-hidden="true"
                    className="h-3 w-3 animate-spin motion-reduce:animate-none"
                  />
                  Optimiert im Hintergrund
                </span>
              )}
            {hasGuidance && recommendation && (
              <>
                <span
                  className={`rounded-full px-2 py-1 font-semibold ${
                    recommendation.confidence === "low"
                      ? "bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-200"
                      : "bc-accent-text bg-brand-teal/10"
                  }`}
                >
                  {confidenceLabel(recommendation.confidence)}
                </span>
                <time
                  dateTime={recommendation.generated_at}
                  className="text-brand-mid-gray"
                >
                  Aktualisiert {formattedTime(recommendation.generated_at)}
                </time>
              </>
            )}
          </div>
        </header>

        <div className="p-3">
          {!hasGuidance || !recommendation ? (
            <EmptyState activity={activity} />
          ) : (
            <div aria-live="polite" aria-atomic="true">
              {hasNewVersion && (
                <div
                  role="status"
                  className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-brand-teal/30 bg-brand-teal/5 px-3 py-2 font-body text-xs text-brand-dark-gray"
                >
                  <span>
                    Eine neuere Sprechkarte ist verfügbar (v{liveVersion || "-"}
                    ).
                  </span>
                  <button
                    type="button"
                    onClick={() => setPinnedRecommendation(null)}
                    className="rounded-md bg-brand-teal px-2 py-1 font-semibold text-white hover:opacity-90"
                  >
                    Neue Version anzeigen
                  </button>
                </div>
              )}
              {centralCorrection && (
                <div
                  role="alert"
                  className="mb-2 flex items-start gap-2 rounded-lg border-2 border-red-400 bg-red-50 px-3 py-2 font-body text-xs leading-5 text-red-900 dark:bg-red-950/40 dark:text-red-100"
                >
                  <AlertTriangle
                    aria-hidden="true"
                    className="mt-0.5 h-4 w-4 shrink-0"
                  />
                  <span>
                    <strong>
                      Zentrale Sachkorrektur in der neuen Version:
                    </strong>{" "}
                    {centralCorrection}
                  </span>
                </div>
              )}
              {recommendation.target_claim && (
                <p className="mb-2 border-l-2 border-brand-amber pl-2 font-body text-xs leading-5 text-brand-gray">
                  <span className="font-semibold text-brand-dark-gray">
                    Bezug:
                  </span>{" "}
                  {recommendation.target_claim}
                </p>
              )}
              <article
                data-priority="primary"
                className="min-w-0 rounded-xl border border-brand-teal/50 bg-brand-teal/5 px-4 py-3 shadow-sm transition-colors"
              >
                <div className="bc-accent-text flex items-center gap-1.5">
                  <primaryMove.icon
                    aria-hidden="true"
                    className="h-3.5 w-3.5 shrink-0"
                  />
                  <h3 className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em]">
                    JETZT SAGEN · {primaryMove.label}
                  </h3>
                </div>
                <p className="mt-2 [overflow-wrap:anywhere] font-body text-base font-semibold leading-6 text-brand-dark-gray">
                  {primaryText}
                </p>
                <p className="mt-1 font-body text-[10px] text-brand-mid-gray">
                  Wird bei neuen Worten laufend aktualisiert
                </p>
              </article>

              {recommendation.pipeline_mode === "experimental_debateai" &&
                recommendation.strategy_options &&
                recommendation.strategy_options.length > 0 && (
                  <div
                    className="mt-2 space-y-1.5"
                    aria-label="Experimentelle Antwortzüge"
                  >
                    <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-brand-mid-gray">
                      Weitere Züge auswählen
                    </p>
                    {recommendation.strategy_options
                      .filter(
                        (option) =>
                          option.id !== recommendation.selected_strategy_id,
                      )
                      .map((option) => (
                        <details
                          key={option.id}
                          className="rounded-lg border border-brand-light-gray-1 bg-surface px-3 py-2 font-body text-xs text-brand-gray"
                        >
                          <summary className="cursor-pointer select-none font-semibold text-brand-dark-gray">
                            {option.title}
                          </summary>
                          <p className="mt-1.5 leading-5">{option.text}</p>
                          {option.example && (
                            <p className="mt-1 leading-5">
                              <span className="font-semibold text-brand-dark-gray">
                                Beispiel:
                              </span>{" "}
                              {option.example}
                            </p>
                          )}
                          {option.rationale && (
                            <p className="mt-1 leading-5">
                              <span className="font-semibold text-brand-dark-gray">
                                Warum:
                              </span>{" "}
                              {option.rationale}
                            </p>
                          )}
                          <button
                            type="button"
                            onClick={() =>
                              onExperimentalOptionSelected?.(
                                recommendation.claim_id,
                                recommendation.recommendation_revision,
                                option.id,
                              )
                            }
                            disabled={!onExperimentalOptionSelected}
                            className="mt-2 rounded-md border border-brand-teal/30 bg-brand-teal/5 px-2 py-1 font-semibold text-brand-teal disabled:cursor-not-allowed disabled:opacity-45"
                          >
                            Diese Antwort verwenden
                          </button>
                        </details>
                      ))}
                    {recommendation.selection_reason && (
                      <p className="text-[11px] text-brand-mid-gray">
                        Ausgewählt: {recommendation.selection_reason}
                      </p>
                    )}
                  </div>
                )}

              {laneArtifacts.length > 0 && (
                <section
                  className="mt-2 space-y-1.5"
                  aria-label="Eintreffende Debatte-Lanes"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-brand-mid-gray">
                      Eintreffende Recherche &amp; Widerlegung
                    </p>
                    <span className="font-body text-[10px] text-brand-mid-gray">
                      {
                        laneArtifacts.filter(
                          (artifact) => artifact.status === "completed",
                        ).length
                      }
                      /{laneArtifacts.length} fertig
                    </span>
                  </div>
                  {laneArtifacts.map((artifact) => (
                    <details
                      key={artifact.lane_id}
                      className="rounded-lg border border-brand-light-gray-1 bg-surface px-3 py-2 font-body text-xs text-brand-gray"
                    >
                      <summary className="cursor-pointer select-none font-semibold text-brand-dark-gray">
                        {artifact.lane === "adversarial"
                          ? "Widerlegung & Gegenbeispiele"
                          : artifact.lane === "rhetoric"
                            ? "Schlagfertige Formulierung"
                            : "Quellen & Faktencheck"}
                        {" · "}
                        {artifact.status === "completed"
                          ? "eingetroffen"
                          : artifact.status}
                      </summary>
                      {artifact.error && (
                        <p className="mt-1 leading-5 text-amber-800 dark:text-amber-200">
                          {artifact.error}
                        </p>
                      )}
                      {artifact.external_insights &&
                      artifact.external_insights.length > 0 ? (
                        <div className="mt-1.5 space-y-1.5">
                          {artifact.external_insights.map((insight) => (
                            <details
                              key={insight.insight_id}
                              className="rounded-md bg-brand-light-gray-2 px-2.5 py-1.5"
                            >
                              <summary className="cursor-pointer select-none font-semibold text-brand-dark-gray">
                                {insight.kind === "counterexample"
                                  ? "Gegenbeispiel"
                                  : insight.kind === "counter_question"
                                    ? "Gegenfrage"
                                    : insight.kind === "source"
                                      ? "Quelle"
                                      : "Widerlegung"}
                              </summary>
                              <p className="mt-1 leading-5">{insight.text}</p>
                            </details>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-1 leading-5 text-brand-mid-gray">
                          Noch kein ausklappbarer Befund eingetroffen.
                        </p>
                      )}
                    </details>
                  ))}
                </section>
              )}

              {(alternativeText || recommendation.counterargument) && (
                <details className="mt-2 rounded-lg border border-brand-light-gray-1 bg-brand-light-gray-2 px-3 py-2 font-body text-xs text-brand-gray">
                  <summary className="cursor-pointer select-none font-semibold text-brand-dark-gray">
                    {alternativeText
                      ? "Alternative anzeigen"
                      : "Begründung anzeigen"}
                  </summary>
                  {alternativeText && (
                    <p className="mt-2 leading-5">
                      <span className="font-semibold text-brand-dark-gray">
                        {alternativeMove.label}:
                      </span>{" "}
                      {alternativeText}
                    </p>
                  )}
                  {recommendation.counterargument && (
                    <p className="mt-1.5 leading-5">
                      <span className="font-semibold text-brand-dark-gray">
                        Kernargument:
                      </span>{" "}
                      {recommendation.counterargument}
                    </p>
                  )}
                </details>
              )}

              <div
                className="mt-2 flex flex-wrap items-center gap-1.5"
                aria-label="Schnellaktionen"
              >
                <span className="mr-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-brand-mid-gray">
                  Neu ausrichten
                </span>
                {quickActions.map(([key, label, directive]) => (
                  <button
                    key={key}
                    type="button"
                    data-quick-action={key}
                    onClick={() => onQuickAction?.(directive)}
                    disabled={!onQuickAction}
                    className="rounded-md border border-brand-light-gray-1 bg-surface px-2 py-1 font-body text-[11px] font-semibold text-brand-gray transition-colors hover:border-brand-teal/40 hover:bg-brand-teal/5 hover:text-brand-dark-gray disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    {label}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    onGoodAnswer?.(
                      recommendation.claim_id,
                      recommendation.recommendation_revision,
                    )
                  }
                  disabled={
                    !onGoodAnswer ||
                    !recommendation.claim_id ||
                    !recommendation.recommendation_revision
                  }
                  className="ml-auto inline-flex items-center gap-1 rounded-md border border-brand-teal/30 bg-brand-teal/5 px-2 py-1 font-body text-[11px] font-semibold text-brand-teal hover:bg-brand-teal/10 disabled:cursor-not-allowed disabled:opacity-45"
                  title="Diese situationsbezogene Antwort als gutes Beispiel merken"
                >
                  <ThumbsUp aria-hidden="true" className="h-3 w-3" />
                  Gute Antwort merken
                </button>
              </div>

              {recommendation.analogy && (
                <div className="mt-2 flex min-w-0 items-start gap-2 rounded-md bg-brand-light-gray-2 px-2.5 py-2">
                  <Lightbulb
                    aria-hidden="true"
                    className="bc-accent-text mt-0.5 h-3.5 w-3.5 shrink-0"
                  />
                  <p className="font-body text-xs leading-5 text-brand-gray">
                    <span className="font-semibold text-brand-dark-gray">
                      Passende Analogie:
                    </span>{" "}
                    {recommendation.analogy}
                  </p>
                </div>
              )}

              {recommendation.research_status === "searching" && (
                <div
                  role="status"
                  className="mt-2 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 font-body text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
                >
                  <Loader2
                    aria-hidden="true"
                    className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none"
                  />
                  Faktencheck läuft im Hintergrund. Die Sofortantwort ist noch
                  ungeprüft.
                </div>
              )}
              {recommendation.research_status === "unavailable" && (
                <div
                  role="status"
                  className="mt-2 rounded-lg bg-amber-50 px-3 py-2 font-body text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
                >
                  Quellen nicht verfügbar · Ungeprüft
                </div>
              )}

              {recommendation.research_alert && (
                <div
                  role="alert"
                  className="mt-2 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 font-body text-xs leading-5 text-red-800 dark:border-red-900/70 dark:bg-red-950/30 dark:text-red-200"
                >
                  <AlertTriangle
                    aria-hidden="true"
                    className="mt-0.5 h-3.5 w-3.5 shrink-0"
                  />
                  <span>
                    <strong>Recherche-Alarm:</strong>{" "}
                    {recommendation.research_alert}
                  </span>
                </div>
              )}

              {researchPoints.length > 0 && (
                <div className="mt-2 rounded-lg border border-brand-teal/20 bg-brand-teal/5 px-3 py-2 font-body text-xs text-brand-gray">
                  <p className="font-semibold text-brand-dark-gray">
                    Recherche-Kernpunkte
                  </p>
                  <ol className="mt-1 list-inside list-decimal space-y-0.5">
                    {researchPoints.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ol>
                </div>
              )}

              <div className="mt-2 border-t border-brand-light-gray-1 pt-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-brand-gray">
                    Jetzt recherchieren
                  </p>
                  <button
                    type="button"
                    data-research-action="primary"
                    onClick={() => onResearch?.("all")}
                    disabled={
                      privacyFirst ||
                      !onResearch ||
                      !recommendation.target_claim ||
                      recommendation.research_status === "searching"
                    }
                    className="inline-flex items-center gap-1 rounded-md bg-brand-teal px-2.5 py-1.5 font-body text-[11px] font-semibold text-white shadow-sm hover:bg-brand-teal-dark disabled:cursor-not-allowed disabled:opacity-45"
                  >
                    <Search aria-hidden="true" className="h-3 w-3" />
                    Jetzt recherchieren
                  </button>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {(
                    [
                      ["counterevidence", "Widerlegung suchen", Search],
                      ["translation", "Übersetzung prüfen", Languages],
                      ["interpretation", "Interpretation prüfen", Search],
                      ["all", "Alles neu prüfen", RefreshCw],
                    ] as const
                  ).map(([category, label, Icon]) => (
                    <button
                      key={category}
                      type="button"
                      data-research-action={category}
                      onClick={() => onResearch?.(category)}
                      disabled={
                        privacyFirst ||
                        !onResearch ||
                        !recommendation.target_claim ||
                        recommendation.research_status === "searching"
                      }
                      className="bc-accent-text inline-flex cursor-pointer items-center gap-1 rounded-md border border-brand-teal/30 bg-brand-teal/5 px-2 py-1 font-body text-[11px] font-semibold hover:bg-brand-teal/10 disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <Icon
                        aria-hidden="true"
                        className={`h-3 w-3 ${category === "all" && recommendation.research_status === "searching" ? "animate-spin motion-reduce:animate-none" : ""}`}
                      />
                      {label}
                    </button>
                  ))}
                </div>
                {privacyFirst ? (
                  <p
                    role="status"
                    className="mt-1 font-body text-[10px] leading-4 text-amber-800 dark:text-amber-200"
                  >
                    Der Datenschutzmodus blockiert öffentliche Recherche. Lokale
                    Sofortantworten bleiben aktiv.
                  </p>
                ) : (
                  <p className="mt-1 font-body text-[10px] leading-4 text-brand-mid-gray">
                    Manuell suchen bleibt auch bei ausgeschalteter
                    Auto-Recherche verfügbar. Nutzt nur die aktuelle Behauptung
                    und verdichteten Kontext.
                  </p>
                )}
              </div>

              {(questionStatus ||
                recommendation.open_question ||
                nextFollowUp ||
                strategyPoints.length > 0 ||
                recommendation.sources.length > 0) && (
                <details className="mt-2 border-t border-brand-light-gray-1 pt-2 font-body text-xs text-brand-gray">
                  <summary className="cursor-pointer select-none font-semibold text-brand-dark-gray">
                    Mehr Strategie &amp; Quellen
                  </summary>
                  {(questionStatus ||
                    recommendation.open_question ||
                    nextFollowUp) && (
                    <div className="mt-2 rounded-md bg-brand-light-gray-2 px-2.5 py-2 leading-5">
                      {questionStatus && (
                        <p className="font-semibold text-brand-dark-gray">
                          {questionStatus}
                        </p>
                      )}
                      {recommendation.open_question && (
                        <p>
                          <span className="font-semibold text-brand-dark-gray">
                            Offen:
                          </span>{" "}
                          {recommendation.open_question}
                        </p>
                      )}
                      {nextFollowUp && (
                        <p className="mt-1">
                          <span className="font-semibold text-brand-dark-gray">
                            Danach:
                          </span>{" "}
                          {nextFollowUp.condition}: {nextFollowUp.question}
                        </p>
                      )}
                    </div>
                  )}
                  {strategyPoints.length > 0 && (
                    <div className="mt-2 rounded-md bg-brand-light-gray-2 px-2.5 py-2 leading-5">
                      <p className="font-semibold text-brand-dark-gray">
                        Argumentstruktur
                      </p>
                      <ol className="mt-1 list-inside list-decimal">
                        {strategyPoints.map((point) => (
                          <li key={point}>{point}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                  {recommendation.sources.length > 0 && (
                    <div className="mt-2">
                      <p className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em] text-brand-gray">
                        Quellen zum Faktencheck
                      </p>
                      <ul className="mt-1.5 grid gap-1.5 sm:grid-cols-2">
                        {recommendation.sources.map((source) => (
                          <li key={source.url}>
                            <SourceInspector
                              sessionId={sessionId}
                              claimId={recommendation.claim_id}
                              source={source}
                              atomicClaims={recommendation.atomic_claims}
                            />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </details>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
