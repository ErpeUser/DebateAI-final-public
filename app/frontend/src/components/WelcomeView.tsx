import { useCallback, useEffect, useState } from "react";
import * as api from "../services/api";
import { setupReadiness, toReadinessAgentModels, type SetupReadiness } from "../lib/providerOnboarding";

interface WelcomeViewProps {
  hasSessions: boolean;
  onNewSession: () => void;
  onOpenApiKeys: () => void;
}

function CheckIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function StepCard({
  step,
  done,
  title,
  description,
  notice,
  action,
}: {
  step: number;
  done: boolean;
  title: string;
  description: string;
  // Plain-language explanation of why the step is still incomplete even
  // though the user already did something (e.g. saved a mismatched key).
  notice?: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="flex items-start gap-4 rounded-xl bg-surface p-5 text-left shadow-sm ring-1 ring-brand-light-gray-1/60">
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-display text-sm font-bold ${
          done ? "bg-brand-teal text-white" : "bg-brand-light-gray-2 text-brand-gray"
        }`}
        aria-label={done ? `Schritt ${step} abgeschlossen` : `Schritt ${step}`}
      >
        {done ? <CheckIcon /> : step}
      </span>
      <div className="min-w-0 flex-1">
        <h3 className="font-display text-sm font-bold text-brand-dark-gray">{title}</h3>
        <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">{description}</p>
        {notice && !done && (
          <p className="mt-2 rounded border border-amber-200 bg-amber-50 px-2.5 py-1.5 font-body text-[11px] leading-relaxed text-amber-900">
            {notice}
          </p>
        )}
      </div>
      {action && !done && (
        <button
          type="button"
          onClick={action.onClick}
          className="shrink-0 self-center rounded-lg bg-brand-teal px-3.5 py-2 font-body text-xs font-semibold text-white transition-colors hover:bg-brand-teal/90"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Shown in the content area when no session is selected. For a brand-new
// workspace (no sessions yet) it becomes a first-run checklist driven by real
// setup state and the first session. Once sessions exist it stays a quiet
// empty state.
export default function WelcomeView({ hasSessions, onNewSession, onOpenApiKeys }: WelcomeViewProps) {
  const [readiness, setReadiness] = useState<SetupReadiness | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [smartCheckRunning, setSmartCheckRunning] = useState(false);
  const [smartCheckStep, setSmartCheckStep] = useState(0);
  const [smartCheckDone, setSmartCheckDone] = useState(false);

  const runSmartCheck = useCallback(async () => {
    setSmartCheckRunning(true);
    setSmartCheckDone(false);
    setSmartCheckStep(1);
    try {
      const [privacy, transcription, agents, models] = await Promise.all([
        api.getPrivacyConfig().catch(() => null),
        api.getTranscriptionReadiness().catch(() => null),
        api.listAgents().catch(() => []),
        api.listModels().catch(() => []),
      ]);
      setSmartCheckStep(2);
      const next = setupReadiness({
        localOnly: privacy?.local_only === true,
        transcription,
        agentModels: toReadinessAgentModels(agents, models),
      });
      setReadiness(next);
      setSmartCheckStep(3);
      setSmartCheckDone(true);
    } finally {
      setSmartCheckRunning(false);
    }
  }, []);

  useEffect(() => {
    if (!hasSessions) {
      // Step 1 completes only when the currently selected transcription and
      // agent configuration can actually run.
      Promise.all([
        api.getPrivacyConfig().catch(() => null),
        api.getTranscriptionReadiness().catch(() => null),
        api.listAgents().catch(() => []),
        api.listModels().catch(() => []),
      ]).then(([p, transcription, agents, models]) => {
        setReadiness(
          setupReadiness({
            localOnly: p?.local_only === true,
            transcription,
            agentModels: toReadinessAgentModels(agents, models),
          })
        );
      });
    }
    api.getAppMeta().then((m) => setVersion(m.version)).catch(() => null);
  }, [hasSessions]);

  const versionFooter = version && (
    <p className="mt-8 text-center font-body text-[11px] text-brand-mid-gray">Debate AI · v{version}</p>
  );

  if (hasSessions) {
    return (
      <div className="flex h-full items-center justify-center bg-brand-light-gray-2 p-6 text-brand-mid-gray">
        <div className="max-w-xl text-center">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-brand-teal">Live-Debatten-Copilot</p>
          <h2 className="mt-2 font-display text-3xl font-bold text-brand-dark-gray">Bereit für die nächste Debatte</h2>
          <p className="mt-3 font-body leading-6">Wähle links eine Debatte oder starte eine neue. Sofortsatz, Gegenfrage und Faktencheck erscheinen während des Gesprächs.</p>
          <button type="button" onClick={onNewSession} className="mt-5 rounded-lg bg-brand-teal px-5 py-2.5 font-body text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-teal-dark">
            Neue Debatte
          </button>
          {versionFooter}
        </div>
      </div>
    );
  }

  const setupReady = readiness?.ready === true;
  const checklistLoaded = readiness !== null;
  const setupNotice =
    checklistLoaded && !setupReady ? readiness.reason : undefined;

  return (
    <div className="flex h-full items-start justify-center overflow-auto bg-brand-light-gray-2 p-6">
      <div className="w-full max-w-4xl py-8">
        <div className="mb-7 text-center">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-brand-teal">Deutsch · Lokal zuerst · Recherche optional</p>
          <h2 className="mt-2 font-display text-4xl font-bold tracking-tight text-brand-dark-gray">Debate AI</h2>
          <p className="mx-auto mt-3 max-w-2xl font-body text-sm leading-6 text-brand-gray">
            Dein Live-Copilot für Discord-Debatten: sofort sprechbare Antworten, präzise Gegenfragen
            und belegte Nachbesserungen — ohne dass die erste Reaktion auf Recherche warten muss.
          </p>
        </div>

        <section className="mb-6 rounded-2xl border border-brand-teal/30 bg-surface p-5 shadow-sm" aria-labelledby="smart-check-title">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-brand-teal">Dein 30-Sekunden-Start</p>
              <h3 id="smart-check-title" className="mt-1 font-display text-xl font-bold text-brand-dark-gray">Smart-Check statt Einstellungs-Marathon</h3>
              <p className="mt-1 max-w-2xl font-body text-xs leading-5 text-brand-gray">
                Wir prüfen die echte Transkription, die gewählten Modelle und den Datenschutzmodus gemeinsam.
                Danach weißt du, ob du direkt loslegen kannst oder nur eine Verbindung fehlt.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void runSmartCheck()}
              disabled={smartCheckRunning}
              className="shrink-0 rounded-lg bg-brand-teal px-4 py-2.5 font-body text-xs font-semibold text-white shadow-sm transition-colors hover:bg-brand-teal-dark disabled:cursor-wait disabled:opacity-60"
            >
              {smartCheckRunning ? "Prüfung läuft ..." : smartCheckDone ? "Noch einmal prüfen" : "Smart-Check starten"}
            </button>
          </div>
          <ol className="mt-4 grid gap-2 sm:grid-cols-3" aria-live="polite">
            {["Transkription", "Modelle", "Datenschutz"].map((label, index) => {
              const step = index + 1;
              const active = smartCheckRunning && smartCheckStep === step;
              const complete = smartCheckDone && smartCheckStep >= step;
              return (
                <li key={label} className={`flex items-center gap-2 rounded-lg px-3 py-2 font-body text-xs ${complete ? "bg-brand-teal/10 text-brand-teal" : active ? "bg-amber-50 text-amber-900" : "bg-brand-light-gray-2 text-brand-gray"}`}>
                  <span className="font-mono text-[10px] font-semibold">{complete ? "✓" : `0${step}`}</span>
                  {active ? `Prüfe ${label.toLowerCase()} ...` : label}
                </li>
              );
            })}
          </ol>
        </section>

        <div className="mb-6 grid gap-3 md:grid-cols-3">
          {[
            ["01", "Sofort reagieren", "Ein kurzer Satz erscheint direkt aus dem laufenden Transkript."],
            ["02", "Stärker argumentieren", "Angriff, Verteidigung, Analogie und Folgefrage werden gemeinsam bewertet."],
            ["03", "Fakten nachziehen", "Auto-Recherche bleibt schaltbar; manuelle Prüfungen sind jederzeit möglich."],
          ].map(([number, title, description]) => (
            <div key={number} className="rounded-xl border border-brand-light-gray-1 bg-surface p-4 shadow-sm">
              <p className="font-mono text-[10px] font-semibold text-brand-teal">{number}</p>
              <h3 className="mt-2 font-display text-sm font-bold text-brand-dark-gray">{title}</h3>
              <p className="mt-1.5 font-body text-xs leading-5 text-brand-gray">{description}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <StepCard
            step={1}
            done={checklistLoaded && setupReady}
            title="Modelle prüfen"
            description="Die lokale Transkription funktioniert ohne Schlüssel. Verbinde nur gewünschte Dienste und wähle die als Empfohlen markierten Modelle. Das ändert deine Modellauswahl nicht automatisch."
            notice={setupNotice}
            action={{ label: "Einstellungen", onClick: onOpenApiKeys }}
          />
          <StepCard
            step={2}
            done={hasSessions}
            title="Debatte anlegen"
            description="Eine Debatte bündelt Modus, Beteiligte, Transkript, Quellen und die spätere Auswertung."
            action={{ label: "Neue Debatte", onClick: onNewSession }}
          />
          <StepCard
            step={3}
            done={false}
            title="Gespräch starten"
            description="Starte Mikrofon und optional Systemaudio oder importiere ein vorhandenes Transkript."
          />
        </div>

        <p className="mt-6 text-center font-body text-xs text-brand-mid-gray">
          Modelle, Recherchehäufigkeit, Modi und Datenschutz bleiben jederzeit unter Einstellungen änderbar.
        </p>
        {versionFooter}
      </div>
    </div>
  );
}
