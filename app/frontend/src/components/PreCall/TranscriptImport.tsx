import { useEffect, useRef, useState } from "react";
import * as api from "../../services/api";
import type { TranscriptionJob } from "../../types";
import TranscriptionJobProgress from "../TranscriptionJobProgress";

interface Props {
  sessionId: string;
  onImported?: () => void;
}

export default function TranscriptImport({ sessionId, onImported }: Props) {
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<TranscriptionJob | null>(null);
  const transcriptRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLInputElement>(null);
  const pollAbortRef = useRef<AbortController | null>(null);
  const busy = loading || (job ? api.transcriptionJobActive(job) : false);

  useEffect(() => {
    pollAbortRef.current?.abort();
    pollAbortRef.current = null;
    setJob(null);
    setLoading(false);
    setStatus("");
    return () => {
      pollAbortRef.current?.abort();
      pollAbortRef.current = null;
    };
  }, [sessionId]);

  const handleTranscript = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setStatus("");
    try {
      const result = await api.importTranscript(sessionId, file);
      setStatus(
        `${result.imported} Abschnitte aus ${result.filename} importiert`,
      );
      onImported?.();
    } catch (err: any) {
      setStatus(`Fehler: ${err.message}`);
    } finally {
      setLoading(false);
      if (transcriptRef.current) transcriptRef.current.value = "";
    }
  };

  const handleAudio = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setStatus("Audio wird hochgeladen …");
    const controller = new AbortController();
    pollAbortRef.current = controller;
    try {
      const queued = await api.importAudio(sessionId, file, controller.signal);
      if (controller.signal.aborted) return;
      setJob(queued);
      setLoading(false);
      setStatus("");
      const result = await api.waitForTranscriptionJob(
        sessionId,
        queued,
        setJob,
        1000,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      if (result.status === "completed") {
        setStatus(
          `${result.entries} Transkripteinträge aus ${result.filename} importiert.`,
        );
        onImported?.();
      } else if (result.status === "canceled") {
        setStatus(
          "Audioimport abgebrochen. Es wurde kein Teiltranskript gespeichert.",
        );
      } else {
        setStatus(`Fehler: ${result.error || "Audioimport fehlgeschlagen."}`);
      }
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      setStatus(
        `Fehler: ${err instanceof Error ? err.message : "Audioimport fehlgeschlagen."}`,
      );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
      if (pollAbortRef.current === controller) pollAbortRef.current = null;
      if (audioRef.current) audioRef.current.value = "";
    }
  };

  const handleCancel = async () => {
    try {
      setJob(await api.cancelTranscriptionJob(sessionId, "audio_import"));
    } catch (err) {
      setStatus(
        `Fehler: ${err instanceof Error ? err.message : "Audioimport konnte nicht abgebrochen werden."}`,
      );
    }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-4">
        {/* Transcript file import */}
        <button
          type="button"
          disabled={busy}
          onClick={() => transcriptRef.current?.click()}
          className="min-h-11 rounded-lg border-2 border-dashed border-brand-light-gray-1 p-4 text-center transition-colors hover:border-brand-teal hover:bg-brand-teal/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal disabled:cursor-not-allowed disabled:opacity-50"
        >
          <p className="font-display text-sm font-semibold text-brand-dark-gray">
            Transkript importieren
          </p>
          <p className="mt-1 font-body text-xs text-brand-mid-gray">
            .txt, .md, .docx
          </p>
        </button>
        <input
          ref={transcriptRef}
          type="file"
          accept=".txt,.md,.docx"
          onChange={handleTranscript}
          className="hidden"
        />

        {/* Audio file import */}
        <button
          type="button"
          disabled={busy}
          onClick={() => audioRef.current?.click()}
          className="min-h-11 rounded-lg border-2 border-dashed border-brand-light-gray-1 p-4 text-center transition-colors hover:border-brand-amber hover:bg-orange-50/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal disabled:cursor-not-allowed disabled:opacity-50"
        >
          <p className="font-display text-sm font-semibold text-brand-dark-gray">
            Audio importieren
          </p>
          <p className="mt-1 font-body text-xs text-brand-mid-gray">
            .m4a, .mp3, .wav
          </p>
        </button>
        <input
          ref={audioRef}
          type="file"
          accept=".m4a,.mp3,.wav,.ogg,.flac"
          onChange={handleAudio}
          className="hidden"
        />
      </div>

      {job && api.transcriptionJobActive(job) && (
        <TranscriptionJobProgress job={job} onCancel={handleCancel} />
      )}

      {/* Status message */}
      {(loading || status) && (
        <div
          role="status"
          aria-live="polite"
          className={`rounded-lg px-4 py-2 text-sm font-body ${
            loading
              ? "bg-brand-teal/10 text-brand-teal"
              : status.startsWith("Fehler")
                ? "bg-red-50 text-red-600"
                : "bg-green-50 text-green-700"
          }`}
        >
          {loading && !status.startsWith("Fehler") ? (
            <span className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-brand-teal border-t-transparent" />
              {status || "Wird verarbeitet ..."}
            </span>
          ) : (
            status
          )}
        </div>
      )}
    </div>
  );
}
