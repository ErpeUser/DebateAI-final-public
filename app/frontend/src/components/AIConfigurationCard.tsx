import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Brain, Download, FolderOpen, RotateCcw, Save, Upload } from "lucide-react";
import type { AIConfiguration, AIPromptConfig, AIProviderRoute, ModelInfo } from "../types";
import * as api from "../services/api";

const effortLabels: Record<string, string> = {
  low: "Niedrig", medium: "Mittel", high: "Hoch", xhigh: "Sehr hoch",
};

function numberValue(value: unknown, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function AIConfigurationCard({ models }: { models: ModelInfo[] }) {
  const [config, setConfig] = useState<AIConfiguration | null>(null);
  const [providers, setProviders] = useState<AIConfiguration["providers"] | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [promptDraft, setPromptDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const importInput = useRef<HTMLInputElement>(null);

  const load = async () => {
    try {
      const value = await api.getAIConfiguration();
      setConfig(value);
      setProviders(value.providers);
      const next = selectedPrompt || value.prompts[0]?.name || "";
      setSelectedPrompt(next);
      setPromptDraft(value.prompts.find((prompt) => prompt.name === next)?.content || "");
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => { void load(); }, []);

  const prompt = useMemo(
    () => config?.prompts.find((item) => item.name === selectedPrompt) || null,
    [config, selectedPrompt],
  );

  const selectPrompt = (name: string) => {
    setSelectedPrompt(name);
    setPromptDraft(config?.prompts.find((item) => item.name === name)?.content || "");
  };

  const updateRoute = (index: number, patch: Partial<AIProviderRoute>) => {
    if (!providers) return;
    const routes = providers.routes.map((route, position) => position === index ? { ...route, ...patch } : route);
    setProviders({ ...providers, routes });
  };

  const moveRoute = (index: number, delta: number) => {
    if (!providers) return;
    const next = index + delta;
    if (next < 0 || next >= providers.routes.length) return;
    const routes = [...providers.routes];
    [routes[index], routes[next]] = [routes[next], routes[index]];
    setProviders({ ...providers, routes });
  };

  const saveProviders = async () => {
    if (!providers) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const saved = await api.updateAIProviders(providers);
      setProviders(saved);
      setConfig((current) => current ? { ...current, providers: saved } : current);
      setMessage("Anbieterfolge gespeichert. Sie gilt ab dem nächsten Analyseauftrag.");
    } catch (err) { setError(String(err)); }
    finally { setSaving(false); }
  };

  const resetProviders = async () => {
    if (!window.confirm("Anbieter, Denkstufen und Recherchewerte wirklich auf den Auslieferungsstandard zurücksetzen?")) return;
    setSaving(true); setError("");
    try {
      const saved = await api.resetAIProviders();
      setProviders(saved);
      setConfig((current) => current ? { ...current, providers: saved } : current);
      setMessage("Auslieferungsstandard wiederhergestellt.");
    } catch (err) { setError(String(err)); }
    finally { setSaving(false); }
  };

  const replacePrompt = (saved: AIPromptConfig) => {
    setConfig((current) => current ? {
      ...current,
      prompts: current.prompts.map((item) => item.name === saved.name ? saved : item),
    } : current);
    setPromptDraft(saved.content);
  };

  const savePrompt = async () => {
    if (!selectedPrompt) return;
    setSaving(true); setError("");
    try {
      replacePrompt(await api.updateAIPrompt(selectedPrompt, promptDraft));
      setMessage("Prompt gespeichert. Die neue Version gilt beim nächsten passenden KI-Aufruf.");
    } catch (err) { setError(String(err)); }
    finally { setSaving(false); }
  };

  const resetPrompt = async () => {
    if (!selectedPrompt) return;
    if (!window.confirm("Diesen Prompt wirklich auf den Auslieferungsstandard zurücksetzen? Die aktuelle Fassung bleibt im Versionsverlauf erhalten.")) return;
    setSaving(true); setError("");
    try {
      replacePrompt(await api.resetAIPrompt(selectedPrompt));
      setMessage("Prompt auf den Auslieferungsstandard zurückgesetzt.");
    } catch (err) { setError(String(err)); }
    finally { setSaving(false); }
  };

  const restorePrompt = async (version: string) => {
    if (!selectedPrompt || !version) return;
    setSaving(true); setError("");
    try {
      replacePrompt(await api.restoreAIPrompt(selectedPrompt, version));
      setMessage("Frühere Promptversion wiederhergestellt.");
    } catch (err) { setError(String(err)); }
    finally { setSaving(false); }
  };

  const exportConfiguration = () => {
    if (!config || !providers) return;
    const payload = {
      schema: "debate-ai-settings-v1",
      exported_at: new Date().toISOString(),
      providers,
      prompts: config.prompts.map(({ name, content }) => ({ name, content })),
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "debate-ai-ki-einstellungen.json"; anchor.click();
    URL.revokeObjectURL(url);
  };

  const importConfiguration = async (file: File) => {
    setSaving(true); setError("");
    try {
      const payload = JSON.parse(await file.text()) as { providers?: AIConfiguration["providers"]; prompts?: Array<{ name: string; content: string }> };
      if (!payload.providers?.routes?.length) throw new Error("Die Datei enthält keine gültige Anbieterfolge.");
      if (!window.confirm("Die importierten Anbieter- und Promptwerte jetzt übernehmen? Vorhandene Fassungen bleiben im Versionsverlauf erhalten.")) return;
      await api.updateAIProviders(payload.providers);
      for (const item of payload.prompts || []) {
        if (item.name && item.content) await api.updateAIPrompt(item.name, item.content);
      }
      await load();
      setMessage("KI-Einstellungen und Promptdateien importiert.");
    } catch (err) { setError(String(err)); }
    finally { setSaving(false); if (importInput.current) importInput.current.value = ""; }
  };

  if (!config || !providers) {
    return <section className="rounded-xl border border-brand-light-gray-1 bg-surface p-5 font-body text-sm text-brand-mid-gray">KI-Konfiguration wird geladen …</section>;
  }

  const adaptive = providers.adaptive_reasoning || {};
  const research = (providers.research || {}) as Record<string, unknown>;
  const researchProviders = Array.isArray(research.providers) ? research.providers as Array<{ id: string; label: string; enabled: boolean }> : [];

  return (
    <section className="rounded-xl border border-brand-light-gray-1 bg-surface shadow-sm">
      <header className="flex flex-wrap items-center gap-3 border-b border-brand-light-gray-1 px-5 py-4">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-teal/10 text-brand-teal"><Brain className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-base font-semibold text-brand-dark-gray">KI-Anbieter, Denkstufen und Promptdateien</h2>
          <p className="font-body text-xs text-brand-mid-gray">Diese Werte steuern direkt das Backend. Keine Zugangsdaten werden exportiert.</p>
        </div>
        <button type="button" onClick={() => void api.openAIConfigurationFolder()} className="inline-flex items-center gap-1 rounded border border-brand-light-gray-1 px-2.5 py-1.5 font-body text-xs"><FolderOpen className="h-3.5 w-3.5" /> ai-Ordner öffnen</button>
      </header>

      <div className="space-y-7 px-5 py-5">
        <div>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div><h3 className="font-display text-sm font-semibold text-brand-dark-gray">Externe Analyse – echte Ausweichreihenfolge</h3><p className="font-body text-[11px] text-brand-mid-gray">Von oben nach unten; deaktivierte Einträge werden übersprungen. Qwen bleibt davon unabhängig.</p></div>
            <div className="flex gap-2"><button type="button" onClick={resetProviders} className="inline-flex items-center gap-1 rounded px-2 py-1 font-body text-xs text-brand-mid-gray"><RotateCcw className="h-3.5 w-3.5" /> Standard</button><button type="button" disabled={saving} onClick={saveProviders} className="inline-flex items-center gap-1 rounded bg-brand-teal px-3 py-1.5 font-body text-xs font-semibold text-white"><Save className="h-3.5 w-3.5" /> Speichern</button></div>
          </div>
          <div className="space-y-2">
            {providers.routes.map((route, index) => {
              const available = models.some((model) => model.id === route.model_id && (!model.requires_key || model.key_available));
              return <div key={route.id} className="grid gap-2 rounded-lg border border-brand-light-gray-1 bg-brand-light-gray-2/30 p-3 lg:grid-cols-[auto_1fr_1.2fr_auto_auto] lg:items-center">
                <div className="flex gap-1"><button type="button" aria-label="Nach oben" disabled={index === 0} onClick={() => moveRoute(index, -1)} className="rounded p-1 disabled:opacity-25"><ArrowUp className="h-4 w-4" /></button><button type="button" aria-label="Nach unten" disabled={index === providers.routes.length - 1} onClick={() => moveRoute(index, 1)} className="rounded p-1 disabled:opacity-25"><ArrowDown className="h-4 w-4" /></button></div>
                <div><label className="flex items-center gap-2 font-body text-xs font-semibold text-brand-dark-gray"><input type="checkbox" checked={route.enabled} onChange={(event) => updateRoute(index, { enabled: event.target.checked })} className="accent-brand-teal" />{route.label}</label><span className={`font-body text-[10px] ${available ? "text-emerald-700" : "text-amber-700"}`}>{available ? "Modell aktuell verfügbar" : "Modell derzeit nicht bestätigt"}{route.lazy_start ? " · Start bei Bedarf" : ""}</span></div>
                <input value={route.model_id} onChange={(event) => updateRoute(index, { model_id: event.target.value })} list="ai-models" className="rounded border border-brand-light-gray-1 bg-surface px-2 py-1.5 font-mono text-xs" aria-label={`Modell für ${route.label}`} />
                <select value={route.reasoning_effort} onChange={(event) => updateRoute(index, { reasoning_effort: event.target.value as AIProviderRoute["reasoning_effort"] })} className="rounded border border-brand-light-gray-1 bg-surface px-2 py-1.5 font-body text-xs">{Object.entries(effortLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                <div className="flex flex-wrap items-center gap-1 font-body text-[10px] text-brand-mid-gray"><input type="number" min={1} max={86400} value={route.timeout_seconds} onChange={(event) => updateRoute(index, { timeout_seconds: numberValue(event.target.value, 180) })} className="w-16 rounded border border-brand-light-gray-1 px-1 py-1 text-right" /> s Zeitlimit<input type="number" min={1} max={86400} value={route.cooldown_seconds} onChange={(event) => updateRoute(index, { cooldown_seconds: numberValue(event.target.value, 900) })} className="ml-1 w-16 rounded border border-brand-light-gray-1 px-1 py-1 text-right" /> s Pause</div>
              </div>;
            })}
          </div>
          <datalist id="ai-models">{models.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}</datalist>
          <div className="mt-3 grid gap-3 rounded-lg border border-brand-light-gray-1 p-3 sm:grid-cols-4">
            <label className="font-body text-xs">Ausweichwege<select value={providers.fallback_enabled === false ? "off" : "on"} onChange={(event) => setProviders({ ...providers, fallback_enabled: event.target.value === "on" })} className="mt-1 w-full rounded border px-2 py-1.5"><option value="on">Automatisch</option><option value="off">Nur erste Verbindung</option></select></label>
            <label className="font-body text-xs">Verbindung festlegen<select value={providers.forced_model || ""} onChange={(event) => setProviders({ ...providers, forced_model: event.target.value })} className="mt-1 w-full rounded border px-2 py-1.5"><option value="">Automatisch</option>{providers.routes.filter((route) => route.enabled).map((route) => <option key={route.id} value={route.model_id}>{route.label}</option>)}</select></label>
            <label className="font-body text-xs">Wartezeit nach Fehler<input type="number" min={60} max={86400} value={providers.unavailable_cooldown_seconds || 900} onChange={(event) => setProviders({ ...providers, unavailable_cooldown_seconds: numberValue(event.target.value, 900) })} className="mt-1 w-full rounded border px-2 py-1.5" /></label>
            <label className="font-body text-xs">Parallele Hintergrundanalysen<input type="number" min={1} max={8} value={providers.max_parallel_analyses || 1} onChange={(event) => setProviders({ ...providers, max_parallel_analyses: numberValue(event.target.value, 1) })} className="mt-1 w-full rounded border px-2 py-1.5" /></label>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-brand-light-gray-1 p-4"><h3 className="font-display text-sm font-semibold">Denkstufen-Automatik</h3><div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="font-body text-xs"><input type="checkbox" checked={adaptive.enabled !== false} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, enabled: event.target.checked } })} className="mr-2 accent-brand-teal" />Automatik aktiv</label>
            <label className="font-body text-xs">Neues Thema<select value={String(adaptive.new_topic_effort || "xhigh")} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, new_topic_effort: event.target.value } })} className="mt-1 w-full rounded border px-2 py-1"><option value="xhigh">Sehr hoch</option><option value="high">Hoch</option></select></label>
            <label className="font-body text-xs">Folgeargument<select value={String(adaptive.follow_up_effort || "high")} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, follow_up_effort: event.target.value } })} className="mt-1 w-full rounded border px-2 py-1"><option value="high">Hoch</option><option value="xhigh">Sehr hoch</option></select></label>
            <label className="font-body text-xs">Gezielte Tiefenanalyse<select value={String(adaptive.deep_reanalysis_effort || "xhigh")} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, deep_reanalysis_effort: event.target.value } })} className="mt-1 w-full rounded border px-2 py-1"><option value="xhigh">Sehr hoch</option><option value="high">Hoch</option></select></label>
            <label className="font-body text-xs">Latenzgrenze (ms)<input type="number" min={1000} max={600000} value={numberValue(adaptive.latency_threshold_ms, 45000)} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, latency_threshold_ms: numberValue(event.target.value, 45000) } })} className="mt-1 w-full rounded border px-2 py-1" /></label>
            <label className="font-body text-xs">Warteschlangengrenze<input type="number" min={1} max={20} value={numberValue(adaptive.queue_threshold, 1)} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, queue_threshold: numberValue(event.target.value, 1) } })} className="mt-1 w-full rounded border px-2 py-1" /></label>
            <label className="font-body text-xs">Stabile Aufrufe bis Sehr hoch<input type="number" min={1} max={20} value={numberValue(adaptive.stable_calls_to_restore, 2)} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, stable_calls_to_restore: numberValue(event.target.value, 2) } })} className="mt-1 w-full rounded border px-2 py-1" /></label>
            <label className="font-body text-xs">Themenschwelle<input type="number" min={0.1} max={0.95} step={0.01} value={numberValue(adaptive.topic_similarity_threshold, 0.46)} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, topic_similarity_threshold: numberValue(event.target.value, 0.46) } })} className="mt-1 w-full rounded border px-2 py-1" /></label>
            <label className="font-body text-xs"><input type="checkbox" checked={adaptive.reuse_topic_analysis !== false} onChange={(event) => setProviders({ ...providers, adaptive_reasoning: { ...adaptive, reuse_topic_analysis: event.target.checked } })} className="mr-2 accent-brand-teal" />Themenanalyse wiederverwenden</label>
          </div></div>
          <div className="rounded-lg border border-brand-light-gray-1 p-4"><h3 className="font-display text-sm font-semibold">Recherche und Quellen</h3><div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="font-body text-xs"><input type="checkbox" checked={research.enabled !== false} onChange={(event) => setProviders({ ...providers, research: { ...research, enabled: event.target.checked } })} className="mr-2 accent-brand-teal" />Rechercheebene aktiv</label>
            <label className="font-body text-xs">Rechercheschritte<input type="number" min={1} max={5} value={numberValue(research.steps, 2)} onChange={(event) => setProviders({ ...providers, research: { ...research, steps: numberValue(event.target.value, 2) } })} className="mt-1 w-full rounded border px-2 py-1" /></label>
            <label className="font-body text-xs"><input type="checkbox" checked={research.original_sources_required !== false} onChange={(event) => setProviders({ ...providers, research: { ...research, original_sources_required: event.target.checked } })} className="mr-2 accent-brand-teal" />Originalquellen lesen</label>
            <div className="col-span-full flex flex-wrap gap-2">{researchProviders.map((item, index) => <label key={item.id} className="rounded-full border px-3 py-1 font-body text-xs"><input type="checkbox" checked={item.enabled} onChange={(event) => { const next = researchProviders.map((candidate, position) => position === index ? { ...candidate, enabled: event.target.checked } : candidate); setProviders({ ...providers, research: { ...research, providers: next } }); }} className="mr-2 accent-brand-teal" />{item.label}</label>)}</div>
          </div></div>
        </div>

        <div className="border-t border-brand-light-gray-1 pt-6"><div className="mb-3 flex flex-wrap items-end justify-between gap-3"><div><h3 className="font-display text-sm font-semibold">Zentraler Prompteditor</h3><p className="font-body text-[11px] text-brand-mid-gray">Aktiver Pfad: <span className="font-mono">{config.directory}</span></p></div><div className="flex gap-2"><button type="button" onClick={exportConfiguration} className="inline-flex items-center gap-1 rounded border px-2 py-1 font-body text-xs"><Download className="h-3.5 w-3.5" /> Exportieren</button><button type="button" onClick={() => importInput.current?.click()} className="inline-flex items-center gap-1 rounded border px-2 py-1 font-body text-xs"><Upload className="h-3.5 w-3.5" /> Importieren</button><input ref={importInput} type="file" accept="application/json" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) void importConfiguration(file); }} /></div></div>
          <select value={selectedPrompt} onChange={(event) => selectPrompt(event.target.value)} className="w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-2 font-body text-sm">{config.prompts.map((item) => <option key={item.name} value={item.name}>{item.category} · {item.title}</option>)}</select>
          {prompt && <div className="mt-3"><div className="mb-2 grid gap-1 font-body text-[11px] text-brand-mid-gray sm:grid-cols-2"><span>Datei: <span className="font-mono">{prompt.path}</span></span><span>Aktive Version: <span className="font-mono">{prompt.version}</span></span><span>Quelle: {prompt.active_source}</span><span>Platzhalter: {prompt.placeholders.join(", ") || "keine"}</span></div><textarea value={promptDraft} onChange={(event) => setPromptDraft(event.target.value)} rows={16} className="w-full resize-y rounded border border-brand-light-gray-1 bg-brand-light-gray-2/20 px-3 py-2 font-mono text-xs leading-relaxed" /><div className="mt-2 flex flex-wrap items-center justify-end gap-2"><select defaultValue="" onChange={(event) => { if (event.target.value) void restorePrompt(event.target.value); event.target.value = ""; }} className="rounded border px-2 py-1 font-body text-xs"><option value="">Frühere Version …</option>{prompt.versions.map((version) => <option key={version.version} value={version.version}>{version.version}</option>)}</select><button type="button" onClick={resetPrompt} className="inline-flex items-center gap-1 rounded px-2 py-1 font-body text-xs text-brand-mid-gray"><RotateCcw className="h-3.5 w-3.5" /> Standard</button><button type="button" disabled={saving || !promptDraft.trim()} onClick={savePrompt} className="inline-flex items-center gap-1 rounded bg-brand-teal px-3 py-1.5 font-body text-xs font-semibold text-white disabled:opacity-50"><Save className="h-3.5 w-3.5" /> Prompt speichern</button></div></div>}
        </div>

        {message && <p role="status" className="rounded bg-emerald-50 px-3 py-2 font-body text-xs text-emerald-800">{message}</p>}
        {error && <p role="alert" className="rounded bg-red-50 px-3 py-2 font-body text-xs text-red-800">{error}</p>}
      </div>
    </section>
  );
}
