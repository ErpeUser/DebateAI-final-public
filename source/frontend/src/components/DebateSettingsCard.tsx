import React, { useEffect, useState } from "react";
import { Search, ShieldAlert, Sparkles } from "lucide-react";
import type { DebateProfile, DebateSettings } from "../types";
import * as api from "../services/api";

type DebateSettingsPatch = Partial<Pick<
  DebateSettings,
  "mode" | "research_enabled" | "research_frequency" | "always_analogy"
  | "style_focus" | "voice_commands_enabled" | "argument_memory_enabled"
  | "transcript_retention_enabled" | "audio_archive_enabled" | "session_retrieval_enabled"
  | "learning_examples_enabled" | "graph_recording_enabled"
  | "memory_similarity_threshold"
  | "performance_profile"
  | "simple_1to1_audio_mode"
>>;

interface ControlsProps {
  settings: DebateSettings;
  privacyFirst: boolean;
  saving: boolean;
  onChange: (patch: DebateSettingsPatch) => void;
}

const modes = [
  { value: "persuasive", label: "Überzeugen", hint: "Publikum, gemeinsame Basis, eigene Maßstäbe und Beispiele" },
  { value: "forceful", label: "Hart", hint: "Position, Beweislast, Konsistenz und Falsifikator" },
] as const;

const frequencies = [
  { value: "low", label: "Wenig" },
  { value: "normal", label: "Normal" },
  { value: "often", label: "Oft" },
] as const;

const styleFocuses = [
  { value: "balanced", label: "Ausgewogen" },
  { value: "natural", label: "Natürlich" },
  { value: "concise", label: "Sehr kurz" },
  { value: "evidence", label: "Belegfokus" },
] as const;

export function DebateSettingsControls({ settings, privacyFirst, saving, onChange }: ControlsProps) {
  return (
    <div className="space-y-5">
      <div>
        <p className="mb-2 font-body text-xs font-medium text-brand-gray">Rhetorischer Modus</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {modes.map((mode) => (
            <button
              key={mode.value}
              type="button"
              aria-pressed={settings.mode === mode.value}
              disabled={saving}
              onClick={() => onChange({ mode: mode.value })}
              className={`rounded-lg border px-3 py-2 text-left transition-colors ${
                settings.mode === mode.value
                  ? "border-brand-teal bg-brand-teal/10 text-brand-dark-gray"
                  : "border-brand-light-gray-1 bg-surface text-brand-gray hover:border-brand-teal/50"
              }`}
            >{mode.label}<span className="mt-0.5 block font-body text-[11px] font-normal text-brand-mid-gray">{mode.hint}</span></button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 font-body text-xs font-medium text-brand-gray">Gesprächsstil</p>
        <div className="flex flex-wrap gap-2">
          {styleFocuses.map((style) => (
            <button
              key={style.value}
              type="button"
              aria-pressed={settings.style_focus === style.value}
              disabled={saving}
              onClick={() => onChange({ style_focus: style.value })}
              className={`rounded-full border px-3 py-1 font-body text-xs font-medium ${
                settings.style_focus === style.value
                  ? "border-brand-teal bg-brand-teal/10 text-brand-teal"
                  : "border-brand-light-gray-1 text-brand-gray"
              }`}
            >{style.label}</button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="font-body text-xs font-medium text-brand-gray">Internet-Recherche</p>
            <button
              type="button"
              role="switch"
              aria-checked={settings.research_enabled}
              disabled={saving}
              onClick={() => onChange({ research_enabled: !settings.research_enabled })}
              className={`h-5 w-9 rounded-full transition-colors ${settings.research_enabled ? "bg-brand-teal" : "bg-brand-light-gray-1"}`}
              title={settings.research_enabled ? "Recherche ist an" : "Recherche ist aus"}
            >
              <span className={`block h-4 w-4 rounded-full bg-white shadow transition-transform ${settings.research_enabled ? "translate-x-4.5" : "translate-x-0.5"}`} />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {frequencies.map((frequency) => (
              <button
                key={frequency.value}
                type="button"
                aria-pressed={settings.research_frequency === frequency.value}
                disabled={saving || !settings.research_enabled}
                onClick={() => onChange({ research_frequency: frequency.value })}
                className={`rounded-full border px-3 py-1 font-body text-xs font-medium ${
                  settings.research_frequency === frequency.value
                    ? "border-brand-teal bg-brand-teal/10 text-brand-teal"
                    : "border-brand-light-gray-1 text-brand-gray"
                } disabled:opacity-50`}
              >{frequency.label}</button>
            ))}
          </div>
        </div>
        <p className="font-body text-[11px] text-brand-mid-gray">
          Mindestabstand: {settings.cooldown_seconds} Sekunden
        </p>
      </div>

      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-brand-light-gray-1 bg-brand-light-gray-2 px-3 py-2.5">
        <input
          type="checkbox"
          checked={settings.always_analogy}
          disabled={saving}
          onChange={(event) => onChange({ always_analogy: event.target.checked })}
          className="h-4 w-4 accent-brand-teal"
        />
        <span className="font-body text-sm text-brand-dark-gray">Beste Analogie immer mitliefern</span>
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-brand-light-gray-1 px-3 py-2.5">
          <input
            type="checkbox"
            checked={settings.voice_commands_enabled}
            disabled={saving}
            onChange={(event) => onChange({ voice_commands_enabled: event.target.checked })}
            className="h-4 w-4 accent-brand-teal"
          />
          <span className="font-body text-sm text-brand-dark-gray">Sprachbefehle vom eigenen Mikrofon</span>
        </label>
        <label className="rounded-lg border border-brand-light-gray-1 px-3 py-2.5 font-body text-sm text-brand-dark-gray">
          <span className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={settings.argument_memory_enabled}
              disabled={saving}
              onChange={(event) => onChange({ argument_memory_enabled: event.target.checked })}
              className="h-4 w-4 accent-brand-teal"
            />
            Argumentgedächtnis
          </span>
          <span className="mt-2 flex items-center gap-2 text-xs text-brand-mid-gray">
            Ähnlichkeit
            <input
              type="number"
              min={0.1}
              max={0.95}
              step={0.01}
              value={settings.memory_similarity_threshold}
              disabled={saving || !settings.argument_memory_enabled}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (!Number.isFinite(value)) return;
                onChange({
                  memory_similarity_threshold: Math.min(0.95, Math.max(0.1, value)),
                });
              }}
              className="w-20 rounded border border-brand-light-gray-1 px-2 py-1 text-right"
            />
          </span>
        </label>
      </div>

      <div>
        <p className="mb-2 font-body text-xs font-medium text-brand-gray">Speicherung getrennt steuern</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {([
            ["transcript_retention_enabled", "Transkript speichern"],
            ["audio_archive_enabled", "Audio dauerhaft archivieren"],
            ["session_retrieval_enabled", "Frühere Sitzungsclaims abrufen"],
            ["learning_examples_enabled", "Bestätigte Lernbeispiele nutzen"],
            ["graph_recording_enabled", "Claimgraph aufzeichnen"],
          ] as const).map(([key, label]) => (
            <label key={key} className="flex cursor-pointer items-center gap-2 rounded-lg border border-brand-light-gray-1 px-3 py-2 font-body text-xs text-brand-dark-gray">
              <input
                type="checkbox"
                checked={settings[key]}
                disabled={saving}
                onChange={(event) => onChange({ [key]: event.target.checked })}
                className="h-4 w-4 accent-brand-teal"
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      <label className="block rounded-lg border border-brand-light-gray-1 px-3 py-2.5">
        <span className="mb-1 block font-body text-xs font-medium text-brand-gray">Leistungsprofil</span>
        <select
          value={settings.performance_profile}
          disabled={saving}
          onChange={(event) => onChange({ performance_profile: event.target.value as DebateSettings["performance_profile"] })}
          className="w-full rounded border border-brand-light-gray-1 bg-surface px-2 py-1.5 font-body text-sm text-brand-dark-gray"
        >
          <option value="balanced">Ausgewogen</option>
          <option value="economy">Schwächerer Rechner</option>
        </select>
        <span className="mt-1 block font-body text-[11px] text-brand-mid-gray">
          Das sparsame Profil reduziert Zwischenstände, Live-Retrieval und automatische Hintergrundrecherche. Manuelle Vertiefung bleibt verfügbar.
        </span>
      </label>

      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-brand-light-gray-1 px-3 py-2.5">
        <input
          type="checkbox"
          checked={settings.simple_1to1_audio_mode}
          disabled={saving}
          onChange={(event) => onChange({ simple_1to1_audio_mode: event.target.checked })}
          className="mt-0.5 h-4 w-4 accent-brand-teal"
        />
        <span className="font-body text-sm text-brand-dark-gray">
          Einfacher 1:1-Audiomodus
          <span className="mt-0.5 block text-[11px] text-brand-mid-gray">Mikrofon und Systemaudio werden vorläufig getrennten Sprechern zugeordnet. Ein Mikrofon gilt dabei nicht automatisch als Ihre Identität.</span>
        </span>
      </label>

      {privacyFirst && settings.research_enabled && (
        <div role="status" className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 font-body text-xs text-amber-900">
          <ShieldAlert aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <span><strong>Datenschutzmodus:</strong> Öffentliche Recherche ist blockiert, bis der Modus ausgeschaltet wird.</span>
        </div>
      )}
    </div>
  );
}

export default function DebateSettingsCard({ privacyFirst }: { privacyFirst: boolean }) {
  const [settings, setSettings] = useState<DebateSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [profiles, setProfiles] = useState<DebateProfile[]>([]);
  const [preview, setPreview] = useState<DebateProfile | null>(null);

  useEffect(() => {
    api.getDebateSettings().then(setSettings).catch((err) => setError(String(err)));
    api.getDebateProfiles().then(setProfiles).catch(() => setProfiles([]));
  }, []);

  const applyProfile = async () => {
    if (!preview) return;
    setSaving(true);
    setError("");
    try {
      setSettings(await api.applyDebateProfile(preview.id));
      setPreview(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  const update = async (patch: DebateSettingsPatch) => {
    setSaving(true);
    setError("");
    try {
      setSettings(await api.updateDebateSettings(patch));
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-xl border border-brand-light-gray-1 bg-surface shadow-sm">
      <header className="flex items-center gap-3 border-b border-brand-light-gray-1 px-5 py-4">
        <span className="bc-accent-text flex h-9 w-9 items-center justify-center rounded-full bg-brand-teal/10"><Sparkles aria-hidden="true" className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-base font-semibold text-brand-dark-gray">Debatten-Copilot</h2>
          <p className="font-body text-xs text-brand-mid-gray">Antwortstil, Analogie und automatische Faktenrecherche</p>
        </div>
        {saving ? <Search aria-label="Speichert" className="h-4 w-4 animate-pulse text-brand-teal" /> : null}
      </header>
      <div className="px-5 py-4">
        {profiles.length > 0 && (
          <div className="mb-5 rounded-lg border border-brand-light-gray-1 bg-brand-light-gray-2 p-3">
            <p className="font-body text-xs font-semibold text-brand-dark-gray">Debattenprofil</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {profiles.map((profile) => (
                <button key={profile.id} type="button" aria-pressed={settings?.profile_id === profile.id} onClick={() => setPreview(profile)} className={`rounded-full border px-3 py-1 font-body text-xs font-semibold ${settings?.profile_id === profile.id ? "border-brand-teal bg-brand-teal/10 text-brand-teal" : "border-brand-light-gray-1 bg-surface text-brand-gray"}`}>
                  {profile.name}
                </button>
              ))}
            </div>
            {preview && (
              <div className="mt-3 rounded border border-brand-teal/30 bg-surface p-3 font-body text-xs leading-5 text-brand-gray">
                <p className="font-semibold text-brand-dark-gray">Vorschau: {preview.name}</p>
                <p>{preview.description}</p>
                <p className="mt-1">Modus: {preview.mode === "forceful" ? "Hart" : "Überzeugen"} · Stil: {preview.style_focus} · Recherche: {preview.research_frequency}</p>
                <p>Die Gesprächsphase wird automatisch zwischen neuem Thema, Folgezug und Tiefenanalyse gewählt. Faktenregeln und lokale Datenschutzwahl bleiben unverändert.</p>
                {preview.profile_directive && <p className="mt-1"><strong>Strategie:</strong> {preview.profile_directive.replace("[PLAYBOOK] ", "")}</p>}
                <div className="mt-2 flex gap-2">
                  <button type="button" disabled={saving} onClick={() => void applyProfile()} className="rounded bg-brand-teal px-3 py-1.5 font-semibold text-white disabled:opacity-50">Profil anwenden</button>
                  <button type="button" onClick={() => setPreview(null)} className="rounded border px-3 py-1.5">Abbrechen</button>
                </div>
              </div>
            )}
          </div>
        )}
        {settings ? <DebateSettingsControls settings={settings} privacyFirst={privacyFirst} saving={saving} onChange={update} /> : <p className="font-body text-sm text-brand-mid-gray">Einstellungen werden geladen...</p>}
        {error && <p role="alert" className="mt-3 font-body text-xs text-red-700">Speichern fehlgeschlagen: {error}</p>}
      </div>
    </section>
  );
}
