import { useEffect, useState } from "react";
import type { DebateReview } from "../../types";
import * as api from "../../services/api";
import SourceInspector from "../SourceInspector";

const traceLabels = {
  open_question: "Offene Fragen",
  unsupported_claim: "Unbelegte Behauptungen",
  corrected_statement: "Korrigierte Aussagen",
  concession: "Zugeständnisse",
  late_recommendation: "Zu späte Empfehlungen",
} as const;

export default function DebateReviewCard({ sessionId }: { sessionId: string }) {
  const [review, setReview] = useState<DebateReview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.getDebateReview(sessionId)
      .then((value) => { if (!cancelled) setReview(value); })
      .catch(() => { /* A missing review is an ordinary first-use state. */ });
    return () => { cancelled = true; };
  }, [sessionId]);

  const generate = async () => {
    if (!window.confirm("Debatte jetzt mit dem eingestellten KI-Modell auswerten? Es werden keine Einstellungen automatisch geändert.")) return;
    setBusy(true);
    setError("");
    try {
      setReview(await api.generateDebateReview(sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auswertung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const apply = async () => {
    if (!window.confirm("Die vorgeschlagenen sicheren Stil-Einstellungen für künftige Debatten übernehmen?")) return;
    setBusy(true);
    setError("");
    try {
      setReview(await api.applyDebateReview(sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Übernehmen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rounded-xl border border-brand-light-gray-1 bg-surface p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-brand-dark-gray">Debatten-Feinschliff</h2>
          <p className="mt-1 max-w-3xl font-body text-xs leading-5 text-brand-gray">
            Nur manuell: bewertet Kürze, Natürlichkeit, Argumente, offene Fragen, Quellen und gemessene Antwortzeit. Die Login-Bridge erzeugt keinen separaten Online-Chat; Auswertung und wichtige Diagnosewerte bleiben lokal gespeichert.
          </p>
        </div>
        <button type="button" disabled={busy} onClick={() => void generate()} className="rounded-lg bg-brand-teal px-3 py-2 font-body text-xs font-semibold text-white disabled:opacity-60">
          {busy ? "Bitte warten…" : review ? "Neu auswerten" : "Debatte auswerten"}
        </button>
      </div>

      {error && <p role="alert" className="mt-3 font-body text-xs text-red-700">{error}</p>}
      {review && (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-lg bg-brand-light-gray-2 p-3">
            <p className="font-body text-sm font-semibold text-brand-dark-gray">{review.summary}</p>
            <p className="mt-2 font-body text-xs text-brand-gray">
              {review.metrics.recommendations} Vorschläge · Ø {review.metrics.average_latency_ms} ms · maximal {review.metrics.maximum_latency_ms} ms
            </p>
            {review.source_quality && <p className="mt-2 font-body text-xs leading-5 text-brand-gray"><strong>Quellen:</strong> {review.source_quality}</p>}
          </div>
          <div className="rounded-lg border border-brand-light-gray-1 p-3">
            <p className="font-body text-xs font-semibold text-brand-dark-gray">Konkrete Verbesserungen</p>
            <ul className="mt-2 space-y-2">
              {review.improvements.map((item, index) => (
                <li key={`${item.issue}-${index}`} className="font-body text-xs leading-5 text-brand-gray">
                  <strong>{item.issue}:</strong> {item.better}
                </li>
              ))}
            </ul>
            <button type="button" disabled={busy || Boolean(review.applied_at)} onClick={() => void apply()} className="mt-3 rounded-lg border border-brand-teal px-3 py-1.5 font-body text-xs font-semibold text-brand-teal disabled:opacity-50">
              {review.applied_at ? "Einstellungen übernommen" : "Vorschlag prüfen und übernehmen"}
            </button>
          </div>
          {((review.traces ?? []).length > 0 || (review.learning_notes ?? []).length > 0) && (
            <div className="md:col-span-2 rounded-lg border border-brand-light-gray-1 p-3">
              <p className="font-body text-xs font-semibold text-brand-dark-gray">Nachvollziehbare Lernspuren</p>
              <p className="mt-1 font-body text-xs leading-5 text-brand-gray">
                Keine pauschale Gewonnen-Wertung: Jeder Hinweis verweist auf die gespeicherte Originalpassage.
              </p>
              {(review.learning_notes ?? []).length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 font-body text-xs leading-5 text-brand-gray">
                  {review.learning_notes.map((note) => <li key={note}>{note}</li>)}
                </ul>
              )}
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {(review.traces ?? []).map((trace, index) => (
                  <details key={`${trace.category}-${trace.claim_id}-${index}`} className="rounded-lg bg-brand-light-gray-2 p-3">
                    <summary className="cursor-pointer font-body text-xs font-semibold text-brand-dark-gray">
                      {traceLabels[trace.category]}: {trace.title}
                    </summary>
                    <p className="mt-2 font-body text-xs leading-5 text-brand-gray">{trace.explanation}</p>
                    <blockquote className="mt-2 border-l-2 border-brand-teal pl-2 font-body text-xs italic leading-5 text-brand-gray">
                      „{trace.transcript_quote}“
                    </blockquote>
                    <p className="mt-1 font-body text-[11px] text-brand-gray">
                      {trace.speaker || "Unbekannt"}{trace.timestamp ? ` · ${new Date(trace.timestamp).toLocaleString("de-DE")}` : ""}
                    </p>
                    {trace.recommendation && (
                      <p className="mt-2 font-body text-xs leading-5 text-brand-gray">
                        <strong>Empfehlung:</strong> {trace.recommendation}
                      </p>
                    )}
                  </details>
                ))}
              </div>
            </div>
          )}
          {review.sources.length > 0 && (
            <details className="md:col-span-2 rounded-lg border border-brand-light-gray-1 bg-brand-light-gray-2 p-3">
              <summary className="cursor-pointer font-body text-xs font-semibold text-brand-dark-gray">
                Quellenbibliothek ({review.sources.length})
              </summary>
              <ul className="mt-2 grid gap-2 md:grid-cols-2">
                {review.sources.map((source) => (
                  <li key={source.url}>
                    <SourceInspector
                      sessionId={sessionId}
                      claimId={source.claim_id || ""}
                      source={source}
                      onCorrected={(corrected) => setReview((current) => current ? {
                        ...current,
                        sources: current.sources.map((item) => item.url === corrected.url ? corrected : item),
                      } : current)}
                    />
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
