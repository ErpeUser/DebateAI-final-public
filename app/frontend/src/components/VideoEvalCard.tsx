import { useEffect, useState } from "react";
import * as api from "../services/api";

const ACTIVE: api.VideoEvalJobStatus[] = [
  "queued",
  "processing",
  "awaiting_consent",
];

export default function VideoEvalCard() {
  const [url, setUrl] = useState("");
  const [job, setJob] = useState<api.VideoEvalJob | null>(null);
  const [artifact, setArtifact] = useState<Record<string, unknown> | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || !ACTIVE.includes(job.status)) return;
    const timer = window.setInterval(() => {
      void api
        .getVideoEvalJob(job.id)
        .then(setJob)
        .catch((err) =>
          setError(
            err instanceof Error
              ? err.message
              : "Status konnte nicht geladen werden.",
          ),
        );
    }, 1500);
    return () => window.clearInterval(timer);
  }, [job]);

  const start = async () => {
    const trimmed = url.trim();
    if (!/^https?:\/\//i.test(trimmed)) {
      setError("Bitte einen gültigen http(s)-Videolink eingeben.");
      return;
    }
    setBusy(true);
    setError(null);
    setArtifact(null);
    try {
      setJob(await api.createVideoEvalJob(trimmed));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Videoanalyse konnte nicht gestartet werden.",
      );
    } finally {
      setBusy(false);
    }
  };

  const consent = async (approved: boolean) => {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      setJob(await api.consentVideoEvalJob(job.id, approved));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Einwilligung konnte nicht gespeichert werden.",
      );
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      setJob(await api.cancelVideoEvalJob(job.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Abbruch fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const openArtifact = async () => {
    if (!job) return;
    setBusy(true);
    setError(null);
    try {
      setArtifact(await api.getVideoEvalArtifact(job.id));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Ergebnis konnte nicht geladen werden.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="rounded-xl bg-surface p-5 shadow-sm ring-1 ring-brand-light-gray-1/60"
      aria-labelledby="video-eval-title"
    >
      <h2
        id="video-eval-title"
        className="font-display text-base font-bold text-brand-dark-gray"
      >
        Videolink-Analyse
      </h2>
      <p className="mt-1 max-w-2xl font-body text-xs leading-5 text-brand-mid-gray">
        Link einfügen, Arbeitsschritte verfolgen und Claims, Quellen und
        rhetorische Erkenntnisse nach Abschluss öffnen. Es wird kein Video
        hochgeladen.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <label htmlFor="video-eval-url" className="sr-only">
          Videolink
        </label>
        <input
          id="video-eval-url"
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://…"
          className="min-h-11 min-w-0 flex-1 rounded border border-brand-light-gray-1 px-3 font-body text-sm"
        />
        <button
          type="button"
          onClick={() => void start()}
          disabled={busy || !url.trim()}
          className="min-h-11 rounded bg-brand-teal px-4 font-body text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Analyse starten
        </button>
      </div>
      {error && (
        <p
          role="alert"
          className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 font-body text-xs text-red-800"
        >
          {error}
        </p>
      )}
      {job && (
        <div
          className="mt-4 rounded border border-brand-light-gray-1 p-4"
          aria-live="polite"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-body text-sm font-semibold text-brand-dark-gray">
                {job.status === "awaiting_consent"
                  ? "Untertitel fehlen"
                  : `Job ${job.status}`}
              </p>
              <p className="mt-1 font-body text-xs text-brand-mid-gray">
                {job.step || "Analyse wird vorbereitet"}
              </p>
            </div>
            <span className="rounded-full bg-brand-light-gray-2 px-2 py-1 font-mono text-[10px] text-brand-mid-gray">
              {job.id}
            </span>
          </div>
          {typeof job.progress === "number" && (
            <progress
              className="mt-3 h-2 w-full"
              value={job.progress}
              max={100}
              aria-label={`Videoanalyse ${job.progress} Prozent`}
            />
          )}
          {job.status === "awaiting_consent" && (
            <div className="mt-3 rounded bg-amber-50 p-3">
              <p className="font-body text-xs leading-5 text-amber-900">
                Für diesen Link wurden keine Untertitel gefunden. Soll der
                optionale Gemini-Fallback verwendet werden?
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void consent(true)}
                  className="min-h-10 rounded bg-brand-teal px-3 font-body text-xs font-semibold text-white"
                >
                  Gemini-Fallback erlauben
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void consent(false)}
                  className="min-h-10 rounded border border-brand-light-gray-1 px-3 font-body text-xs"
                >
                  Ablehnen
                </button>
              </div>
            </div>
          )}
          {ACTIVE.includes(job.status) && job.status !== "awaiting_consent" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void cancel()}
              className="mt-3 min-h-10 rounded border border-red-200 px-3 font-body text-xs text-red-700"
            >
              Analyse abbrechen
            </button>
          )}
          {job.status === "completed" && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="font-body text-xs text-emerald-700">
                Analyse abgeschlossen.
              </span>
              <button
                type="button"
                disabled={busy}
                onClick={() => void openArtifact()}
                className="min-h-10 rounded border border-brand-teal px-3 font-body text-xs font-semibold text-brand-teal"
              >
                Claims und Quellen öffnen
              </button>
            </div>
          )}
          {job.status === "failed" && (
            <p className="mt-3 font-body text-xs text-red-700">
              {job.error || "Die Analyse ist fehlgeschlagen."}
            </p>
          )}
          {job.status === "cancelled" && (
            <p className="mt-3 font-body text-xs text-brand-mid-gray">
              Analyse wurde abgebrochen.
            </p>
          )}
        </div>
      )}
      {artifact && (
        <details
          open
          className="mt-3 rounded border border-brand-light-gray-1 p-3"
        >
          <summary className="cursor-pointer font-body text-xs font-semibold text-brand-dark-gray">
            Ergebnisdetails (Claims · Quellen · Rhetorik)
          </summary>
          <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-brand-gray">
            {JSON.stringify(artifact, null, 2)}
          </pre>
        </details>
      )}
    </section>
  );
}
