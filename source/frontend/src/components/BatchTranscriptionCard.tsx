import { useCallback, useEffect, useMemo, useState } from "react";
import type { ModelInfo, TranscriptionConfig } from "../types";
import * as api from "../services/api";
import { groupModels, optionLabel, optionState, runsLocally } from "../lib/modelOptions";
import { languageMismatch } from "../lib/transcriptionLanguage";

interface BatchTranscriptionCardProps {
  models: ModelInfo[];
  localOnly?: boolean;
  // Names the switch behind localOnly: Privacy First or the PII Shield.
  lockLabel?: string;
  /** Called after the live preview model changes; it edits the Audio Gateway agent's model. */
  onLiveModelChanged?: () => void;
  /** Audio Gateway agent's current model (same underlying setting as the live
      preview model); changing it on the Agents tab triggers a refetch here. */
  gatewayModelId?: string;
}

export default function BatchTranscriptionCard({ models, localOnly = false, lockLabel = "Privacy First", onLiveModelChanged, gatewayModelId }: BatchTranscriptionCardProps) {
  const [config, setConfig] = useState<TranscriptionConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setConfig(await api.getTranscriptionConfig());
      setError(null);
    } catch (err) {
      console.error("Failed to load transcription config", err);
      setError("Transkriptionseinstellungen konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Reload when Privacy First flips (the backend coerces the effective batch
  // model to a local one) or when the Audio Bridge model is edited on the
  // Agents tab (it is the same row as the live preview model shown here).
  useEffect(() => { void load(); }, [load, localOnly, gatewayModelId]);

  const batchModels = useMemo(
    () => models.filter((model) => model.supports_batch_audio),
    [models]
  );
  const liveModels = useMemo(
    () => models.filter((model) => model.supports_live_audio),
    [models]
  );

  const selectedModel = batchModels.find((model) => model.id === config?.batch_model_id);
  const liveModel = liveModels.find((model) => model.id === config?.live_preview_model_id);
  // Under Privacy First a local live model (the experimental on-device captioner)
  // is still usable; only a cloud gateway is off.
  const liveIsLocal = liveModel ? runsLocally(liveModel) : false;
  const livePreviewOff = Boolean(config?.live_preview_model_id && localOnly && !liveIsLocal);
  const hasLocalLiveModel = liveModels.some((model) => runsLocally(model));
  const language = config?.language ?? "auto";
  const languageName = (code: string) =>
    config?.language_options.find((option) => option.code === code)?.name ?? code;
  const languageWarnings = [
    languageMismatch(selectedModel, language, languageName),
    livePreviewOff ? null : languageMismatch(liveModel, language, languageName),
  ].filter((warning): warning is string => Boolean(warning));

  const update = async (data: { batch_model_id?: string; live_preview_model_id?: string; language?: string }) => {
    setSaving(true);
    try {
      setConfig(await api.updateTranscriptionConfig(data));
      setError(null);
      if (data.live_preview_model_id !== undefined) onLiveModelChanged?.();
    } catch (err) {
      console.error("Failed to update transcription config", err);
      setError(err instanceof Error ? err.message : "Transkriptionsmodell konnte nicht aktualisiert werden.");
    } finally {
      setSaving(false);
    }
  };

  const renderOptions = (
    available: ModelInfo[],
    currentId: string | undefined,
    role: "batch_transcription" | "audio_gateway",
  ) => (
    <>
      <option value="">Nicht ausgewählt</option>
      {groupModels(available).map((group) => (
        <optgroup key={group.provider} label={group.provider}>
          {group.models.map((model) => {
            const { locked, suffix } = optionState(model, currentId, localOnly, lockLabel);
            return (
              <option key={model.id} value={model.id} disabled={locked}>
                {optionLabel(model, role)}{suffix}
              </option>
            );
          })}
        </optgroup>
      ))}
    </>
  );

  return (
    <div className={`rounded-xl bg-surface p-5 shadow-sm transition-opacity ${saving ? "opacity-70" : ""}`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-base font-bold text-brand-dark-gray">Datei-Transkription</h3>
            <span className="inline-flex rounded-full border border-slate-500 bg-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-50">
              Endgültiges Transkript
            </span>
          </div>
          <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
            Legt das Modell fest, das gespeicherte Transkriptzeilen aus Audioimporten und abgeschlossenen diarisierten Live-Segmenten erzeugt.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading || saving}
          className="rounded border border-brand-light-gray-1 px-3 py-1.5 font-body text-xs text-brand-dark-gray transition-colors hover:border-brand-teal hover:text-brand-teal disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Wird geprüft ..." : "Aktualisieren"}
        </button>
      </div>

      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <div className="rounded border border-brand-light-gray-1 bg-brand-light-gray-2/30 p-3">
          <p className="font-body text-[10px] uppercase text-brand-mid-gray">Dateimodell</p>
          <p className="mt-1 truncate font-display text-sm font-bold text-brand-dark-gray" title={config?.batch_model_id ?? ""}>
            {selectedModel?.name || config?.batch_model_id || "Nicht ausgewählt"}
          </p>
          <p className="mt-1 truncate font-mono text-[10px] text-brand-mid-gray">{config?.batch_model_id}</p>
        </div>
        <div className="rounded border border-brand-light-gray-1 bg-brand-light-gray-2/30 p-3">
          <p className="font-body text-[10px] uppercase text-brand-mid-gray">Live-Vorschaumodell</p>
          <p className="mt-1 truncate font-display text-sm font-bold text-brand-dark-gray" title={config?.live_preview_model_id ?? ""}>
            {livePreviewOff ? "Aus (Privacy First)" : liveModel?.name || config?.live_preview_model_id || "Nicht ausgewählt"}
          </p>
          <p className="mt-1 truncate font-mono text-[10px] text-brand-mid-gray">{config?.live_preview_model_id}</p>
        </div>
      </div>

      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <div>
          <label className="mb-1 block font-body text-xs font-medium text-brand-gray">Modell für Datei-Transkription</label>
          <select
            value={config?.batch_model_id ?? ""}
            disabled={!config || saving}
            onChange={(event) => void update({ batch_model_id: event.target.value })}
            className="w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-1.5 text-sm text-brand-dark-gray transition-colors focus:border-brand-teal disabled:cursor-not-allowed disabled:bg-brand-light-gray-2"
          >
            {renderOptions(batchModels, config?.batch_model_id, "batch_transcription")}
          </select>
        </div>
        <div>
          <label className="mb-1 block font-body text-xs font-medium text-brand-gray">Modell für Live-Zwischentext</label>
          <select
            value={config?.live_preview_model_id ?? ""}
            disabled={!config || saving}
            onChange={(event) => void update({ live_preview_model_id: event.target.value })}
            className="w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-1.5 text-sm text-brand-dark-gray transition-colors focus:border-brand-teal disabled:cursor-not-allowed disabled:bg-brand-light-gray-2"
          >
            {renderOptions(liveModels, config?.live_preview_model_id, "audio_gateway")}
          </select>
        </div>
      </div>

      <div className="mb-4 grid gap-x-4 gap-y-1 md:grid-cols-2">
        <div>
          <label htmlFor="transcription-language" className="mb-1 block font-body text-xs font-medium text-brand-gray">
            Gesprächssprache
          </label>
          <select
            id="transcription-language"
            value={config?.language ?? "auto"}
            disabled={!config || saving}
            onChange={(event) => void update({ language: event.target.value })}
            className="w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-1.5 text-sm text-brand-dark-gray transition-colors focus:border-brand-teal disabled:cursor-not-allowed disabled:bg-brand-light-gray-2"
          >
            {(config?.language_options ?? [{ code: "auto", name: "Automatisch erkennen" }]).map((option) => (
              <option key={option.code} value={option.code}>
                {option.name}
              </option>
            ))}
          </select>
        </div>
        <p className="font-body text-[11px] leading-relaxed text-brand-mid-gray md:col-span-2">
          Teilt Whisper, Gemini und OpenAI die erwartete Sprache für das gespeicherte Transkript und die
          Live-Untertitel mit. Gesprochenes wird transkribiert, aber nicht übersetzt. Parakeet benötigt keine
          Sprachwahl: v2 unterstützt nur Englisch, v3 erkennt 25 europäische Sprachen automatisch.
        </p>
        {languageWarnings.map((warning) => (
          <p
            key={warning}
            role="status"
            className="rounded border border-amber-200 bg-amber-50 px-3 py-2 font-body text-xs text-amber-900 md:col-span-2"
          >
            {warning}
          </p>
        ))}
      </div>

      {localOnly && (
        <p className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 font-body text-xs text-amber-900">
          {lockLabel === "Privacy First" ? "Privacy First" : "Der Schutz für personenbezogene Daten"} ist aktiv: Nur lokale ONNX-Modelle dürfen transkribieren. Cloud-Dienste für Live-Untertitel sind
          abgeschaltet; der experimentelle lokale Untertitler ({hasLocalLiveModel ? "Parakeet Live" : "falls verfügbar"})
          kann hier einsprachig oder mehrsprachig (Parakeet v3 Live) gewählt werden. Er belastet die CPU deutlich;
          bitte zuerst den Eignungstest für Live-Untertitel prüfen.
          Nach dem Ausschalten werden die vorherigen Cloud-Einstellungen wiederhergestellt.
        </p>
      )}

      <div className="rounded border border-brand-light-gray-1 bg-brand-light-gray-2/30 px-3 py-2">
        <p className="font-body text-xs leading-relaxed text-brand-gray">
          Die Stapeltranskription läuft nach der Segmentierung durch die Sprechertrennung und erzeugt das
          gespeicherte Transkript. Die Live-Vorschau ist davon getrennt: Der Audio-Bridge-Agent (je nach Modell
          Gemini Live oder OpenAI Realtime) zeigt während eines aktiven Gesprächs nur Zwischentexte. Eine Änderung
          hier aktualisiert dieselbe Modelleinstellung wie im Reiter Agenten. Selbst gehostete, OpenAI-kompatible
          Chatmodelle verarbeiten nur Text und erscheinen deshalb nicht hier. Für vollständig lokale Transkription
          ein lokales ONNX-Modell wählen (Whisper Base, Parakeet v2 für Englisch oder Parakeet v3 für 25 europäische
          Sprachen) und für die Analyse-Agenten ein selbst gehostetes Chatmodell verwenden.
        </p>
      </div>

      {error && (
        <p className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 font-body text-xs text-red-700">{error}</p>
      )}
    </div>
  );
}
