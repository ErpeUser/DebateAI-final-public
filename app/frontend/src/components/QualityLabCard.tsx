import { useEffect, useMemo, useState } from "react";
import type { ModelInfo } from "../types";
import * as api from "../services/api";
import { blindOrder, isRatingComplete, type LabSide, type QualityRating } from "../lib/qualityLab";

const DIMENSIONS: Array<{ key: keyof Omit<QualityRating, "both_unsuitable">; label: string }> = [
  { key: "naturalness", label: "Natürlichkeit" },
  { key: "strength", label: "Stärke" },
  { key: "precision", label: "Präzision" },
  { key: "source_honesty", label: "Quellenredlichkeit" },
  { key: "usability", label: "Nutzbarkeit" },
];

const blankRating = (): QualityRating => ({ naturalness: null, strength: null, precision: null, source_honesty: null, usability: null, both_unsuitable: false });

function Score({ value, onChange, label }: { value: number | null; onChange: (value: number) => void; label: string }) {
  return (
    <div className="flex items-center gap-1" role="group" aria-label={label}>
      <span className="w-28 shrink-0 font-body text-[11px] text-brand-mid-gray">{label}</span>
      {[1, 2, 3, 4, 5].map((score) => (
        <button
          key={score}
          type="button"
          aria-label={`${label}: ${score} von 5`}
          aria-pressed={value === score}
          onClick={() => onChange(score)}
          className={`min-h-8 min-w-8 rounded border px-1 font-body text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-teal ${value === score ? "border-brand-teal bg-brand-teal text-white" : "border-brand-light-gray-1 bg-surface text-brand-gray hover:border-brand-teal"}`}
        >
          {score}
        </button>
      ))}
    </div>
  );
}

export default function QualityLabCard({ models }: { models: ModelInfo[] }) {
  const eligible = useMemo(() => models.filter((model) => model.supports_text && (model.runs_locally || model.key_available)), [models]);
  const [modelIds, setModelIds] = useState<[string, string]>(["", ""]);
  const [claim, setClaim] = useState("");
  const [context, setContext] = useState("");
  const [sources, setSources] = useState("");
  const [datasetId, setDatasetId] = useState("interactive");
  const [holdout, setHoldout] = useState(false);
  const [run, setRun] = useState<api.QualityLabRun | null>(null);
  const [ratings, setRatings] = useState<Record<LabSide, QualityRating>>({ A: blankRating(), B: blankRating() });
  const [preferred, setPreferred] = useState<LabSide | "tie" | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [agreement, setAgreement] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!eligible.length) return;
    setModelIds((previous) => [previous[0] && eligible.some((model) => model.id === previous[0]) ? previous[0] : eligible[0].id, previous[1] && eligible.some((model) => model.id === previous[1]) ? previous[1] : (eligible[1] || eligible[0]).id]);
  }, [eligible]);

  const candidateBySide = useMemo(() => {
    const result: Partial<Record<LabSide, api.QualityLabCandidate>> = {};
    const order = run?.blind_order?.length === 2 ? run.blind_order : blindOrder(run?.run_id || "pending");
    run?.candidates.slice(0, 2).forEach((candidate, index) => { result[order[index]] = candidate; });
    return result;
  }, [run]);

  const ratingComplete = isRatingComplete(ratings.A) && isRatingComplete(ratings.B) && preferred !== null;

  const updateRating = (side: LabSide, key: keyof QualityRating, value: number | boolean) => {
    setRatings((previous) => ({ ...previous, [side]: { ...previous[side], [key]: value } }));
  };

  const startRun = async () => {
    if (!claim.trim() || !modelIds[0] || !modelIds[1] || modelIds[0] === modelIds[1]) return;
    setBusy(true); setError(null); setNotice(null); setRevealed(false); setPreferred(null); setRatings({ A: blankRating(), B: blankRating() });
    try {
      const result = await api.runQualityLab({ claim: claim.trim(), context: context.trim(), allowed_sources: sources.split("\n").map((item) => item.trim()).filter(Boolean), dataset_id: datasetId.trim() || "interactive", holdout, model_ids: modelIds });
      if (result.candidates.length < 2 || result.candidates.slice(0, 2).some((candidate) => candidate.available === false)) throw new Error("Für diese Runde sind zwei verfügbare Modelle oder Promptvarianten erforderlich.");
      setRun(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Laborlauf konnte nicht gestartet werden.");
    } finally { setBusy(false); }
  };

  const submitRating = async () => {
    if (!run || !ratingComplete) return;
    setBusy(true); setError(null);
    try {
      const saved = await api.submitQualityLabRating(run.run_id, { ratings, preferred, holdout, dataset_id: run.dataset_id });
      setAgreement(saved.agreement);
      setRevealed(true);
      setNotice("Bewertung gespeichert. Die Modell- und Promptdetails sind jetzt sichtbar.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bewertung konnte nicht gespeichert werden.");
    } finally { setBusy(false); }
  };

  const exportRun = () => {
    if (!run || !revealed) return;
    const payload = { schema: "debate-ai-quality-lab-v1", run, ratings, preferred, exported_at: new Date().toISOString() };
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    anchor.download = `debate-ai-labor-${run.run_id}.json`;
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  };

  const apply = async (side: LabSide) => {
    const candidate = candidateBySide[side];
    if (!run || !candidate || preferred !== side || ratings.A.both_unsuitable || ratings.B.both_unsuitable) return;
    if (!window.confirm(`Variante ${side} wirklich produktiv übernehmen? Die bisherige Version bleibt für den Rollback erhalten.`)) return;
    setBusy(true); setError(null);
    try { await api.applyQualityLabVariant(run.run_id, candidate.variant_id); setNotice("Variante atomar übernommen. Die vorherige Version bleibt per Rollback verfügbar."); }
    catch (err) { setError(err instanceof Error ? err.message : "Übernahme fehlgeschlagen; aktive Version blieb unverändert."); }
    finally { setBusy(false); }
  };

  const rollback = async () => {
    if (!run) return;
    setBusy(true); setError(null);
    try { await api.rollbackQualityLab(run.run_id); setNotice("Vorherige Promptversion wiederhergestellt."); }
    catch (err) { setError(err instanceof Error ? err.message : "Rollback fehlgeschlagen."); }
    finally { setBusy(false); }
  };

  return (
    <section className="rounded-xl bg-surface p-5 shadow-sm ring-1 ring-brand-light-gray-1/60" aria-labelledby="quality-lab-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 id="quality-lab-title" className="font-display text-base font-bold text-brand-dark-gray">A/B- und Sprachlabor</h2><p className="mt-1 max-w-2xl font-body text-xs leading-5 text-brand-mid-gray">Gleiche Eingabe, gleicher Kontext, zwei verfügbare Modelle oder Promptvarianten. Die Reihenfolge bleibt bis zur Bewertung blind.</p></div>
        <span className="rounded-full bg-brand-light-gray-2 px-2 py-1 font-body text-[10px] text-brand-mid-gray">Live-Debatte bleibt unberührt</span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="font-body text-xs font-semibold text-brand-dark-gray">Modell/Variante A<select value={modelIds[0]} onChange={(event) => setModelIds(([_, second]) => [event.target.value, second])} className="mt-1 block min-h-10 w-full rounded border border-brand-light-gray-1 bg-surface px-2 py-2 font-normal"><option value="">Auswählen</option>{eligible.map((model) => <option key={model.id} value={model.id}>{model.name} · {model.provider}</option>)}</select></label>
        <label className="font-body text-xs font-semibold text-brand-dark-gray">Modell/Variante B<select value={modelIds[1]} onChange={(event) => setModelIds(([first]) => [first, event.target.value])} className="mt-1 block min-h-10 w-full rounded border border-brand-light-gray-1 bg-surface px-2 py-2 font-normal"><option value="">Auswählen</option>{eligible.map((model) => <option key={model.id} value={model.id}>{model.name} · {model.provider}</option>)}</select></label>
        <label className="font-body text-xs font-semibold text-brand-dark-gray sm:col-span-2">Claim oder Debattenfrage<textarea value={claim} onChange={(event) => setClaim(event.target.value)} rows={2} className="mt-1 block w-full resize-y rounded border border-brand-light-gray-1 px-3 py-2 font-normal" placeholder="Soll die Kommune ...?" /></label>
        <label className="font-body text-xs font-semibold text-brand-dark-gray">Kontext<textarea value={context} onChange={(event) => setContext(event.target.value)} rows={2} className="mt-1 block w-full resize-y rounded border border-brand-light-gray-1 px-3 py-2 font-normal" placeholder="Rolle, Ziel, Gesprächsverlauf" /></label>
        <label className="font-body text-xs font-semibold text-brand-dark-gray">Erlaubte Quellen<textarea value={sources} onChange={(event) => setSources(event.target.value)} rows={2} className="mt-1 block w-full resize-y rounded border border-brand-light-gray-1 px-3 py-2 font-normal" placeholder="Eine URL oder Quellen-ID je Zeile" /></label>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3 font-body text-xs text-brand-gray"><label className="inline-flex items-center gap-2"><span>Datensatz</span><input value={datasetId} onChange={(event) => setDatasetId(event.target.value)} className="min-h-9 w-36 rounded border border-brand-light-gray-1 px-2" /></label><label className="inline-flex items-center gap-2"><input type="checkbox" checked={holdout} onChange={(event) => setHoldout(event.target.checked)} className="accent-brand-teal" />Unabhängigen Holdout verwenden</label><button type="button" disabled={busy || !claim.trim() || !modelIds[0] || !modelIds[1] || modelIds[0] === modelIds[1] || eligible.length < 2} onClick={() => void startRun()} className="ml-auto min-h-10 rounded bg-brand-teal px-4 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">{busy && !run ? "Labor läuft …" : "Runde starten"}</button></div>
      {eligible.length < 2 && <p className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 font-body text-xs text-amber-900">Mindestens zwei tatsächlich verfügbare Textmodelle oder Promptvarianten werden benötigt. Nicht verfügbare Cloudmodelle werden nicht als Erfolg gewertet.</p>}
      {error && <p role="alert" className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 font-body text-xs text-red-800">{error}</p>}
      {notice && <p role="status" className="mt-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 font-body text-xs text-emerald-800">{notice}</p>}
      {run && <div className="mt-5 space-y-3" aria-live="polite">
        <div className="grid gap-3 md:grid-cols-2">
          {(["A", "B"] as LabSide[]).map((side) => {
            const candidate = candidateBySide[side];
            const rating = ratings[side];
            return <article key={side} className="rounded-lg border border-brand-light-gray-1 p-4"><div className="flex items-center justify-between"><h3 className="font-display text-sm font-bold text-brand-dark-gray">Antwort {side}</h3>{revealed && candidate && <span className="font-mono text-[10px] text-brand-mid-gray">{candidate.model_id}</span>}</div><p className="mt-3 whitespace-pre-wrap font-body text-sm leading-6 text-brand-dark-gray">{candidate?.answer || "Keine Antwort geliefert."}</p><div className="mt-4 space-y-1.5">{DIMENSIONS.map((dimension) => <Score key={dimension.key} value={rating[dimension.key]} onChange={(value) => updateRating(side, dimension.key, value)} label={dimension.label} />)}</div><label className="mt-2 inline-flex min-h-10 items-center gap-2 font-body text-xs text-brand-gray"><input type="checkbox" checked={rating.both_unsuitable} onChange={(event) => updateRating(side, "both_unsuitable", event.target.checked)} className="accent-brand-teal" />Diese Antwort ungeeignet</label></article>;
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-brand-light-gray-1 pt-3"><span className="font-body text-xs font-semibold text-brand-gray">Bessere Antwort</span>{(["A", "B", "tie"] as const).map((side) => <button key={side} type="button" aria-pressed={preferred === side} onClick={() => setPreferred(side)} className={`min-h-10 rounded border px-3 font-body text-xs ${preferred === side ? "border-brand-teal bg-brand-teal/10 text-brand-teal" : "border-brand-light-gray-1 text-brand-gray"}`}>{side === "tie" ? "Gleich gut" : `Antwort ${side}`}</button>)}<button type="button" disabled={!ratingComplete || busy || revealed} onClick={() => void submitRating()} className="ml-auto min-h-10 rounded bg-brand-teal px-4 font-body text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">Bewertung abschließen</button></div>
        {revealed && <div className="flex flex-wrap items-center gap-2 rounded bg-brand-light-gray-2 px-3 py-2 font-body text-xs text-brand-gray"><span>Runde {run.run_id} · Datensatz {run.dataset_id} · {run.holdout ? "Holdout" : "Entwicklung"}</span><span>·</span><span>Latenz {run.candidates.map((candidate) => `${candidate.latency_ms} ms`).join(" / ")}</span><span>·</span><span>Übereinstimmung {agreement == null ? "noch keine zweite Bewertung" : `${Math.round(agreement * 100)} %`}</span><button type="button" onClick={exportRun} className="ml-auto min-h-9 rounded border border-brand-light-gray-1 bg-surface px-3">Exportieren</button><button type="button" disabled={busy || (preferred !== "A" && preferred !== "B") || ratings.A.both_unsuitable || ratings.B.both_unsuitable} onClick={() => { if (preferred === "A" || preferred === "B") void apply(preferred); }} className="min-h-9 rounded border border-brand-teal px-3 text-brand-teal">Übernehmen</button><button type="button" disabled={busy} onClick={() => void rollback()} className="min-h-9 rounded border border-brand-light-gray-1 px-3">Rollback</button></div>}
      </div>}
    </section>
  );
}
