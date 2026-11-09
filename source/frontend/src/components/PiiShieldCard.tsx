import { useEffect, useState } from "react";
import type { PiiCategory, PiiEgressEntry, PiiPreview, PiiShieldSettings, PiiShieldStatus } from "../types";
import * as api from "../services/api";
import { ModelDownloadRow } from "./ModelDownloads";

// The PII Shield settings card: the switch, what it covers (honestly), the
// categories it looks for, the user's own protected terms, the on-device
// model's state, and a scratch box to see what a sentence turns into.

const SAMPLE =
  "Hi, this is Sarah Connor from Cyberdyne. Email me at sarah.connor@cyberdyne.com or call 555-867-5309 about the Q3 renewal.";

const CATEGORY_HINTS: Partial<Record<PiiCategory, string>> = {
  PERSON: "Sprechernamen immer; weitere Namen über das lokale Modell und Vorstellungen.",
  ORG: "Unternehmensnamen über das lokale Modell und eigene geschützte Begriffe.",
  LOCATION: "Standardmäßig aus: Ortsnamen sind meist Analyseinhalt statt Identität.",
};

const TERM_LABELS: Partial<Record<PiiCategory, string>> = { ORG: "org", PERSON: "person", LOCATION: "place" };

type Update = Partial<PiiShieldSettings>;

const checkboxClass = "h-4 w-4 rounded border-brand-light-gray-1 text-brand-teal";
const smallButtonClass =
  "rounded-md border border-brand-light-gray-1 px-2.5 py-1 font-body text-xs font-medium text-brand-dark-gray transition-colors hover:bg-brand-light-gray-2 disabled:opacity-60";

function CoverageRow({ label, covered, detail }: { label: string; covered: boolean; detail: string }) {
  return (
    <li className="flex items-start gap-2.5 py-1.5">
      <span
        aria-hidden="true"
        className={`mt-1 inline-block h-2 w-2 shrink-0 rounded-full ${covered ? "bg-brand-teal" : "bg-amber-500"}`}
      />
      <div className="min-w-0">
        <p className="font-body text-xs font-semibold text-brand-dark-gray">
          {label}
          <span className={`ml-2 font-normal ${covered ? "text-brand-teal" : "text-amber-700 dark:text-amber-300"}`}>
            {covered ? "geschützt" : "nicht geschützt"}
          </span>
        </p>
        <p className="font-body text-[11px] leading-relaxed text-brand-mid-gray">{detail}</p>
      </div>
    </li>
  );
}

function CoverageList({ status }: { status: PiiShieldStatus }) {
  const { coverage, settings } = status;
  const gateway = coverage.live_gateway;
  const refinement = coverage.refinement;
  const gatewayDetail = gateway.paused
    ? `${gateway.model_id} ist eingerichtet, wird bei aktivem Schutz aber übersprungen: Ein Cloud-Gateway würde zurückgehaltene Namen hören. Live-Untertitel bleiben aus, solange die Audio Bridge nicht den lokalen Untertitler nutzt.`
    : !gateway.covered
      ? `Live-Audio wird für Zwischentexte an ${gateway.model_id} gesendet. Auf den lokalen Untertitler umstellen oder unter Agenten deaktivieren.`
      : gateway.model_id
        ? `Das Gateway läuft lokal (${gateway.model_id}).`
        : "Das Audio-Gateway ist aus oder hat kein Modell gewählt; Live-Audio verlässt diesen Rechner nicht.";
  return (
    <ul className="mt-4 divide-y divide-brand-light-gray-2 rounded-lg border border-brand-light-gray-1 px-3">
      <CoverageRow
        label="Transkripte, Erkenntnisse, Briefings, Chat und Dokumente"
        covered={coverage.text}
        detail={settings.enabled
          ? "Jede Zeile wird beim Schreiben tokenisiert; Modell-Prompts entstehen nur aus bereinigtem Text. Cloud-Textmodelle erhalten ausschließlich Platzhalter."
          : "Den Schutz einschalten, um neuen Text zu tokenisieren. Bereits aufgezeichnete Gespräche bleiben unverändert, bis sie geschützt werden."}
      />
      <CoverageRow
        label="Transkriptionsaudio"
        covered={coverage.transcription.covered}
        detail={coverage.transcription.covered
          ? coverage.enforced
            ? `Audio kann nicht tokenisiert werden. Bei aktivem Schutz bleibt die Transkription deshalb auf dem lokalen Modell ${coverage.transcription.model_id}; Cloud-Transkription ist unter Transkription & Audio gesperrt.`
            : `Die Transkription läuft auf diesem Rechner (${coverage.transcription.model_id}); Audio verlässt ihn nicht.`
          : `Gesprächsaudio wird zur Transkription an ${coverage.transcription.model_id} gesendet, einschließlich gesprochener Namen. Den Schutz einschalten, um ein lokales Modell zu erzwingen.`}
      />
      <CoverageRow label="Live-Untertitel (Audio-Gateway)" covered={gateway.covered} detail={gatewayDetail} />
      {/* The badge answers a privacy question; whether the stage runs is a
          detail below it. Reading the agent's on/off switch as coverage put a
          red "not covered" on a state that leaks nothing (ALP-366). */}
      <CoverageRow
        label="Transkriptverbesserung"
        covered={refinement.covered}
        detail={refinement.covered
          ? `Die Verbesserung liest ausschließlich tokenisierten Text und bleibt daher bei lokalen wie Cloud-Modellen geschützt. Eine Überarbeitung wird nur übernommen, wenn sie exakt dieselben Platzhalter enthält. ${refinement.enabled
              ? `Läuft mit ${refinement.model_id}, alle ${refinement.interval_seconds} Sekunden und am Gesprächsende.`
              : "Derzeit aus; die Transkriptverbesserung unter Agenten aktivieren, um Zeichensetzung, Großschreibung und Verhörer zu korrigieren."}`
          : "Den Schutz einschalten, um neuen Text zu tokenisieren; bis dahin liest die Verbesserung den vorhandenen Transkriptinhalt."}
      />
    </ul>
  );
}

function CategoryPicker({ status, saving, onToggle }: { status: PiiShieldStatus; saving: boolean; onToggle: (id: PiiCategory) => void }) {
  return (
    <section>
      <h4 className="font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">Erkennt</h4>
      <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
        {status.categories.map((category) => (
          <label key={category.id} className="flex cursor-pointer items-start gap-2 rounded-md px-1.5 py-1 hover:bg-brand-light-gray-2">
            <input
              type="checkbox"
              checked={status.settings.categories.includes(category.id)}
              onChange={() => onToggle(category.id)}
              disabled={saving}
              className={`mt-0.5 ${checkboxClass}`}
            />
            <span className="font-body text-xs text-brand-dark-gray">
              {category.label}
              {CATEGORY_HINTS[category.id] && (
                <span className="block text-[11px] text-brand-mid-gray">{CATEGORY_HINTS[category.id]}</span>
              )}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}

function NerSection({ status, saving, onApply, onReload }: { status: PiiShieldStatus; saving: boolean; onApply: (u: Update) => void; onReload: () => Promise<void> }) {
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { ner, settings } = status;
  const label: Record<PiiShieldStatus["ner"]["state"], string> = {
    off: "Off",
    ready: "Ready",
    not_downloaded: settings.enabled ? "Nicht heruntergeladen" : "Download nach Aktivierung",
    downloading: "Downloading",
    unavailable: "Unavailable",
  };
  const badge = ner.state === "ready"
    ? "bg-brand-teal/10 text-brand-teal"
    : ner.state === "unavailable" ? "bg-red-50 text-red-700"
      : ner.state === "downloading" ? "bg-amber-50 text-amber-700"
        : "bg-brand-light-gray-2 text-brand-mid-gray";

  // Kicks the download off and returns; the progress row below reports it.
  // Waiting on the transfer here is what made the button look like a hang.
  const install = async () => {
    setStarting(true);
    setError(null);
    try {
      await api.installPiiNer();
      await onReload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Das lokale Modell konnte nicht installiert werden.");
    } finally {
      setStarting(false);
    }
  };

  const running = ner.state === "downloading";

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">Lokale Namenserkennung</h4>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge}`}>{label[ner.state]}</span>
      </div>
      <p className="mt-1 font-body text-[11px] leading-relaxed text-brand-mid-gray">
        Ein kleines Modell zur Entitätserkennung ({ner.model}, etwa 110 MB) findet Personen, Unternehmen und Orte
        in Freitext. Es wird einmal heruntergeladen und läuft danach offline auf der CPU. Auch ohne dieses Modell
        erkennt der Schutz Sprechernamen, geschützte Begriffe, Vorstellungen, bereits bekannte Namen und strukturierte Kennungen.
      </p>
      {(error || (ner.state === "unavailable" && ner.error && !ner.download)) && (
        <p className="mt-1 font-mono text-[11px] text-red-700">{error || ner.error}</p>
      )}
      {ner.download && (
        <ModelDownloadRow download={ner.download} onRetry={() => void install()} />
      )}
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 font-body text-xs text-brand-dark-gray">
          <input
            type="checkbox"
            checked={settings.ner}
            onChange={(e) => onApply({ ner: e.target.checked })}
            disabled={saving}
            className={checkboxClass}
          />
          Lokales Modell verwenden
        </label>
        {settings.ner && ner.state !== "ready" && !running && (
          <button type="button" onClick={() => void install()} disabled={starting} className={smallButtonClass}>
            {starting ? "Wird gestartet ..." : ner.state === "unavailable" ? "Download erneut versuchen" : "Jetzt herunterladen"}
          </button>
        )}
      </div>
    </section>
  );
}

function TermsSection({ settings, saving, onApply }: { settings: PiiShieldSettings; saving: boolean; onApply: (u: Update) => void }) {
  const [value, setValue] = useState("");
  const [category, setCategory] = useState<PiiCategory>("ORG");

  const add = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setValue("");
    if (settings.protected_terms.some((t) => t.value.toLowerCase() === trimmed.toLowerCase())) return;
    onApply({ protected_terms: [...settings.protected_terms, { value: trimmed, category }] });
  };
  const remove = (term: string) =>
    onApply({ protected_terms: settings.protected_terms.filter((t) => t.value !== term) });

  return (
    <section>
      <h4 className="font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">Geschützte Begriffe</h4>
      <p className="mt-1 font-body text-[11px] leading-relaxed text-brand-mid-gray">
        Namen, die das Modell übersehen könnte und die diesen Rechner nie verlassen dürfen, etwa Kundenunternehmen,
        Projektcodes oder nie vorgestellte Personen. Die Suche erfolgt in jedem Gespräch wortgenau.
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
          placeholder="Acme Corporation"
          maxLength={200}
          className="min-w-[12rem] flex-1 rounded-md border border-brand-light-gray-1 bg-surface px-3 py-1.5 font-body text-xs text-brand-dark-gray placeholder:text-brand-mid-gray focus:border-brand-teal focus:ring-1 focus:ring-brand-teal-light"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as PiiCategory)}
          className="rounded-md border border-brand-light-gray-1 bg-surface px-2 py-1.5 font-body text-xs text-brand-dark-gray"
          aria-label="Begriffskategorie"
        >
          <option value="ORG">Organisation</option>
          <option value="PERSON">Person</option>
          <option value="LOCATION">Ort</option>
        </select>
        <button
          type="button"
          onClick={add}
          disabled={saving || !value.trim()}
          className="rounded-md bg-brand-teal px-3 py-1.5 font-body text-xs font-semibold text-white transition-colors hover:bg-brand-teal-dark disabled:opacity-50"
        >
          Hinzufügen
        </button>
      </div>
      {settings.protected_terms.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {settings.protected_terms.map((term) => (
            <li key={term.value} className="inline-flex items-center gap-1 rounded-full border border-brand-light-gray-1 bg-brand-light-gray-2 py-0.5 pl-2.5 pr-1 font-body text-xs text-brand-dark-gray">
              {term.value}
              <span className="text-[10px] uppercase text-brand-mid-gray">{TERM_LABELS[term.category] ?? term.category.toLowerCase()}</span>
              <button
                type="button"
                onClick={() => remove(term.value)}
                aria-label={`${term.value} entfernen`}
                className="rounded-full p-0.5 text-brand-mid-gray hover:bg-brand-light-gray-1 hover:text-brand-dark-gray"
              >
                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PreviewSection() {
  const [sample, setSample] = useState(SAMPLE);
  const [preview, setPreview] = useState<PiiPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!sample.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setPreview(await api.previewPiiShield(sample));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vorschau fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h4 className="font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">Satz testen</h4>
      <textarea
        value={sample}
        onChange={(e) => setSample(e.target.value)}
        rows={3}
        className="mt-2 w-full resize-none rounded-md border border-brand-light-gray-1 bg-surface px-3 py-2 font-body text-xs text-brand-dark-gray focus:border-brand-teal focus:ring-1 focus:ring-brand-teal-light"
      />
      <div className="mt-2 flex items-center gap-3">
        <button type="button" onClick={() => void run()} disabled={busy || !sample.trim()} className={`px-3 py-1.5 ${smallButtonClass}`}>
          {busy ? "Wird geprüft ..." : "Modellansicht anzeigen"}
        </button>
        <span className="font-body text-[11px] text-brand-mid-gray">Nichts wird gespeichert; die Vorschau nummeriert Platzhalter ab 1.</span>
      </div>
      {error && <p className="mt-2 font-body text-xs text-red-700">{error}</p>}
      {preview && (
        <div className="mt-3 rounded-md border border-brand-light-gray-1 bg-brand-light-gray-2/60 p-3">
          <p className="font-mono text-xs leading-relaxed text-brand-dark-gray">{preview.protected}</p>
          {preview.findings.length === 0 ? (
            <p className="mt-2 font-body text-[11px] text-brand-mid-gray">Der Text enthält nichts aus den aktivierten Kategorien.</p>
          ) : (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {preview.findings.map((f, i) => (
                <li key={i} className="rounded-full border border-brand-light-gray-1 bg-surface px-2 py-0.5 font-body text-[11px] text-brand-dark-gray">
                  <span className="font-mono">{f.token}</span> = {f.text}
                  <span className="ml-1 text-brand-mid-gray">({f.source})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

// What actually left for the models: the prompt log, newest first. Tokens
// show as tokens here (the route is not session-scoped), which is the point.
function EgressSection({ settings, saving, onApply }: { settings: PiiShieldSettings; saving: boolean; onApply: (u: Update) => void }) {
  const [entries, setEntries] = useState<PiiEgressEntry[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true);
    try {
      setEntries((await api.getPiiEgress(50)).entries);
    } catch (err) {
      console.error("Failed to load the prompt log", err);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const clear = async () => {
    await api.clearPiiEgress().catch(() => {});
    setEntries([]);
  };

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">Ausgehende Prompts</h4>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => void load()} disabled={busy} className={smallButtonClass}>{busy ? "Wird geladen..." : "Aktualisieren"}</button>
          <button type="button" onClick={() => void clear()} disabled={busy || entries.length === 0} className={smallButtonClass}>Protokoll leeren</button>
        </div>
      </div>
      <p className="mt-1 font-body text-[11px] leading-relaxed text-brand-mid-gray">
        Bei aktivem Protokoll wird jeder Prompt genauso im Datenverzeichnis erfasst, wie er an ein Modell
        gesendet wird. So lässt sich prüfen, dass Modelle nur Platzhalter sehen. Enthält ein Prompt trotz
        aktivem Schutz einen Tresorwert, wird er vor dem Versand blockiert und hier entsprechend markiert.
      </p>
      <label className="mt-2 flex items-center gap-2 font-body text-xs text-brand-dark-gray">
        <input
          type="checkbox"
          checked={settings.prompt_log}
          onChange={(e) => onApply({ prompt_log: e.target.checked })}
          disabled={saving}
          className={checkboxClass}
        />
        Ausgehende Prompts protokollieren
      </label>
      {entries.length > 0 && (
        <ul className="mt-3 divide-y divide-brand-light-gray-2 rounded-md border border-brand-light-gray-1">
          {entries.map((entry, i) => {
            const key = `${entry.at}-${i}`;
            const expanded = open === key;
            return (
              <li key={key} className="px-3 py-2">
                <button type="button" onClick={() => setOpen(expanded ? null : key)} aria-expanded={expanded} className="flex w-full flex-wrap items-center gap-x-3 gap-y-1 text-left">
                  <span className="font-mono text-[11px] text-brand-mid-gray">{new Date(entry.at).toLocaleTimeString()}</span>
                  <span className="font-body text-xs font-semibold text-brand-dark-gray">{entry.source || "text"}</span>
                  <span className="font-mono text-[11px] text-brand-mid-gray">{entry.model_id}</span>
                  <span className="font-body text-[11px] text-brand-mid-gray">{entry.chars.toLocaleString()} Zeichen</span>
                  {entry.blocked ? (
                    <span className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-700">blockiert: {entry.leaks.map((l) => l.category).join(", ")}</span>
                  ) : entry.tokens_present ? (
                    <span className="rounded-full bg-brand-teal/10 px-2 py-0.5 text-[10px] font-semibold text-brand-teal">nur Platzhalter</span>
                  ) : (
                    <span className="rounded-full bg-brand-light-gray-2 px-2 py-0.5 text-[10px] font-semibold text-brand-mid-gray">keine Platzhalter</span>
                  )}
                </button>
                {expanded && (
                  <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded bg-brand-light-gray-2/60 p-2 font-mono text-[11px] leading-relaxed text-brand-dark-gray">{entry.prompt}{entry.truncated ? "\n[gekürzt]" : ""}</pre>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default function PiiShieldCard({ onChanged }: { onChanged?: (status: PiiShieldStatus) => void }) {
  const [status, setStatus] = useState<PiiShieldStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const load = async () => {
    try {
      const next = await api.getPiiShield();
      setStatus(next);
      onChanged?.(next);
    } catch (err) {
      console.error("Failed to load PII Shield status", err);
      setError(err instanceof Error ? err.message : "Datenschutzfilter konnte nicht geladen werden.");
    }
  };

  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // While the model downloads, poll until it is ready or fails.
  const downloading = Boolean(status?.settings.enabled && status.settings.ner && status.ner.state === "downloading");
  useEffect(() => {
    if (!downloading) return;
    const id = window.setInterval(() => { void load(); }, 2000);
    return () => window.clearInterval(id);
  }, [downloading]); // eslint-disable-line react-hooks/exhaustive-deps

  const apply = async (update: Update) => {
    setSaving(true);
    setError(null);
    try {
      const next = await api.updatePiiShield(update);
      setStatus(next);
      onChanged?.(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Datenschutzfilter konnte nicht aktualisiert werden.");
    } finally {
      setSaving(false);
    }
  };

  const enabled = status?.settings.enabled ?? false;
  const toggleCategory = (id: PiiCategory) => {
    if (!status) return;
    const current = status.settings.categories;
    void apply({ categories: current.includes(id) ? current.filter((c) => c !== id) : [...current, id] });
  };

  return (
    <div className={`rounded-xl bg-surface p-5 shadow-sm transition-opacity ${saving ? "opacity-70" : ""} ${enabled ? "ring-1 ring-brand-teal" : ""}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-base font-bold text-brand-dark-gray">Datenschutzfilter</h3>
            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
              enabled
                ? "border-teal-600 bg-teal-700 text-white dark:border-teal-500 dark:bg-teal-900 dark:text-teal-100"
                : "border-slate-500 bg-slate-700 text-slate-50"
            }`}>
              {enabled ? "Personendaten tokenisiert" : "Personendaten im Wortlaut gespeichert"}
            </span>
          </div>
          <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
            Ersetzt Namen, Kontaktdaten und Kennungen durch Platzhalter wie
            <span className="font-mono"> [PERSON_1]</span>, bevor Inhalte gespeichert oder einem
            lokalen beziehungsweise Cloud-Modell gezeigt werden. Die echten Werte liegen verschlüsselt
            auf diesem Rechner und werden nur in dieser Ansicht oder ausdrücklich angeforderten Exporten eingesetzt.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void apply({ enabled: !enabled })}
          disabled={!status || saving}
          role="switch"
          aria-checked={enabled}
          aria-label={enabled ? "Datenschutzfilter ausschalten" : "Datenschutzfilter einschalten"}
          className={`h-6 w-11 shrink-0 rounded-full transition-colors disabled:cursor-not-allowed ${enabled ? "bg-brand-teal" : "bg-brand-light-gray-1"}`}
        >
          <span className={`block h-5 w-5 rounded-full bg-surface shadow transition-transform ${enabled ? "translate-x-5" : "translate-x-0.5"}`} />
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded border border-red-200 bg-red-50 px-3 py-2 font-body text-xs text-red-700">{error}</p>
      )}

      {status && <CoverageList status={status} />}

      {status && enabled && (
        <p className="mt-3 font-body text-[11px] text-brand-mid-gray">
          Tresor: {status.vault.entries} geschützte Werte über alle Gespräche.
          In den letzten 24 Stunden in dieser Ansicht offengelegt: {status.reveals_24h.tokens} Platzhalter in {status.reveals_24h.requests} Anfragen.
        </p>
      )}

      <button
        type="button"
        onClick={() => setShowDetails((v) => !v)}
        aria-expanded={showDetails}
        className="mt-3 inline-flex items-center gap-1.5 font-body text-xs font-semibold text-brand-teal hover:underline"
      >
        <svg className={`h-3 w-3 transition-transform ${showDetails ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {showDetails ? "Ausblenden" : "Anzeigen"}: Suchkriterien und Testsatz
      </button>

      {showDetails && status && (
        <div className="mt-4 space-y-5">
          <CategoryPicker status={status} saving={saving} onToggle={toggleCategory} />
          <NerSection status={status} saving={saving} onApply={(u) => void apply(u)} onReload={load} />
          <TermsSection settings={status.settings} saving={saving} onApply={(u) => void apply(u)} />
          <PreviewSection />
          <EgressSection settings={status.settings} saving={saving} onApply={(u) => void apply(u)} />
        </div>
      )}
    </div>
  );
}
