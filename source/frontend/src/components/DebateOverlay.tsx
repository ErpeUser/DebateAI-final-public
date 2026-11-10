import { useEffect, useState } from "react";
import * as api from "../services/api";
import type { DebateOverlaySnapshot } from "../services/api";
import { DE } from "../i18n/de";

const confidenceLabel = { high: "hoch", medium: "mittel", low: "vorsichtig" } as const;

export default function DebateOverlay() {
  const [snapshot, setSnapshot] = useState<DebateOverlaySnapshot>({ active: false, session_id: "", recommendation: null });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    document.title = "Debate AI Overlay";
    let stopped = false;
    const refresh = async () => {
      try {
        const next = await api.getDebateOverlaySnapshot();
        if (!stopped) setSnapshot(next);
      } catch {
        if (!stopped) setSnapshot({ active: false, session_id: "", recommendation: null });
      }
    };
    void refresh();
    const timer = window.setInterval(() => {
      // The overlay is a fallback transport for the detached always-on-top
      // window. Do not keep polling while Windows has hidden the window.
      if (document.visibilityState === "visible") void refresh();
    }, 1200);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, []);

  const recommendation = snapshot.recommendation;
  const primaryIsQuestion = recommendation?.primary_move === "question"
    && Boolean(recommendation?.counter_question?.trim());
  const answer = primaryIsQuestion
    ? recommendation?.counter_question || ""
    : recommendation?.answer_now || recommendation?.counterargument || "";
  const secondary = primaryIsQuestion
    ? recommendation?.answer_now || recommendation?.counterargument || ""
    : recommendation?.counter_question || "";
  const primaryLabel = primaryIsQuestion ? "Gegenfrage" : "Sofortantwort";
  const copyAnswer = async () => {
    if (!answer) return;
    await navigator.clipboard.writeText(answer);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <main className="min-h-screen bg-[#111318] p-4 text-white">
      <header className="mb-4 flex items-center justify-between border-b border-white/10 pb-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">Debate AI</p>
          <p className="mt-1 text-sm text-white/65">
            {snapshot.active ? "Gespräch aktiv" : "Warte auf ein aktives Gespräch"}
          </p>
        </div>
        <button type="button" onClick={() => window.close()} className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:bg-white/10">
          Schließen
        </button>
      </header>

      {!recommendation ? (
        <section className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 text-sm leading-6 text-white/60">
          Starte ein Gespräch im Hauptfenster. Die aktuelle Empfehlung erscheint hier automatisch.
        </section>
      ) : (
        <div className="space-y-3">
          {recommendation.target_claim && (
            <section className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-white/45">Aktuelle Aussage</p>
              <p className="text-sm leading-5 text-white/75">{recommendation.target_claim}</p>
            </section>
          )}

          <section aria-live="polite" aria-atomic="true" className="rounded-2xl border border-emerald-400/25 bg-emerald-400/[0.08] p-4 shadow-lg shadow-black/20">
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-emerald-300">{primaryLabel}</p>
              <button type="button" onClick={copyAnswer} disabled={!answer} className="rounded-lg bg-white/10 px-2.5 py-1 text-xs text-white/75 hover:bg-white/15 disabled:opacity-40">
                {copied ? "Kopiert" : "Kopieren"}
              </button>
            </div>
            <p className="text-[17px] font-medium leading-7 text-white">{answer || "Die Modellantwort wird gerade erzeugt …"}</p>
          </section>

          {secondary && (
            <section className="rounded-xl border border-sky-400/20 bg-sky-400/[0.06] p-3">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.16em] text-sky-300">{primaryIsQuestion ? "Sofortantwort" : "Gegenfrage"}</p>
              <p className="text-sm leading-5 text-white/85">{secondary}</p>
            </section>
          )}

          <footer className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-[11px] text-white/45">
            <span>Sicherheit: {confidenceLabel[recommendation.confidence]}</span>
            {recommendation.latency_ms != null && <span>{Math.round(recommendation.latency_ms)} ms</span>}
            {recommendation.analysis_status === "analyzing" && <span>{DE.live.runtimeStatus.deepening}</span>}
            {recommendation.analysis_status === "completed" && <span>{DE.live.runtimeStatus.deepeningComplete}</span>}
          </footer>
        </div>
      )}
    </main>
  );
}
