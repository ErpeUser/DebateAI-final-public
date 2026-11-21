import { useCallback, useEffect, useState } from "react";
import type { PrivacyConfig } from "../types";
import * as api from "../services/api";
import {
  onboardingStage,
  setupReadiness,
  toReadinessAgentModels,
  type ReadinessTranscription,
  type SetupReadiness,
} from "../lib/providerOnboarding";

interface ProviderOnboardingCardProps {
  privacy: PrivacyConfig | null;
  onPrivacyChanged: (config: PrivacyConfig) => void;
  // Bumped by the parent whenever a credential changes so readiness re-checks.
  refreshToken: number;
  onContinue: () => void;
  onOpenQualityLab?: () => void;
}

// Contextual first-run setup state shown above Connections when the screen was
// entered from the welcome checklist. Credentials make models available;
// explicit selections determine whether the configuration is usable.
export default function ProviderOnboardingCard({
  privacy,
  onPrivacyChanged,
  refreshToken,
  onContinue,
  onOpenQualityLab,
}: ProviderOnboardingCardProps) {
  const [anyKeySaved, setAnyKeySaved] = useState(false);
  const [readiness, setReadiness] = useState<SetupReadiness | null>(null);
  const [privacyBusy, setPrivacyBusy] = useState(false);
  const [smartTestBusy, setSmartTestBusy] = useState(false);
  const [smartTestMessage, setSmartTestMessage] = useState<string | null>(null);
  const [showLab, setShowLab] = useState(false);

  const localOnly = privacy?.local_only === true;

  const check = useCallback(async () => {
    try {
      const [credentials, transcription, agents, models] = await Promise.all([
        api.listCredentials(),
        api.getTranscriptionReadiness().catch(() => null),
        api.listAgents(),
        api.listModels(),
      ]);
      setAnyKeySaved(credentials.some((c) => c.configured || c.env_fallback));
      setReadiness(
        setupReadiness({
          localOnly,
          transcription: transcription as ReadinessTranscription | null,
          agentModels: toReadinessAgentModels(agents, models),
        })
      );
      return true;
    } catch (err) {
      console.error("Failed to check setup readiness", err);
      return false;
    }
  }, [localOnly]);

  useEffect(() => {
    check();
  }, [check, refreshToken]);

  const handleSmartTest = async () => {
    setSmartTestBusy(true);
    setSmartTestMessage("Prüfe Transkription, Modelle und Datenschutz …");
    try {
      const ok = await check();
      setSmartTestMessage(
        ok
          ? "Schnelltest abgeschlossen. Die Anzeige wurde aktualisiert."
          : "Schnelltest konnte nicht vollständig abgeschlossen werden. Details oben prüfen."
      );
    } catch {
      setSmartTestMessage("Schnelltest konnte nicht vollständig abgeschlossen werden.");
    } finally {
      setSmartTestBusy(false);
    }
  };

  const handlePrivacyFirst = async () => {
    setPrivacyBusy(true);
    try {
      onPrivacyChanged(await api.updatePrivacyConfig(true));
    } catch (err) {
      console.error("Failed to enable Privacy First", err);
    } finally {
      setPrivacyBusy(false);
    }
  };

  const stage = readiness ? onboardingStage({ anyKeySaved, readiness }) : "choose";
  const disabledImpact = privacy?.impact.disabled ?? [];

  return (
    <div className="rounded-xl border border-brand-teal/30 bg-surface p-5 shadow-sm">
      <p className="font-body text-[10px] font-semibold uppercase tracking-wider text-brand-teal">
        Ersteinrichtung
      </p>
      <h3 className="mt-0.5 font-display text-base font-bold text-brand-dark-gray">
        Dienste verbinden, danach Modelle wählen
      </h3>
      <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
        Die integrierte lokale Transkription funktioniert ohne Schlüssel. Nur gewünschte
        Dienste hinzufügen und danach unter Agenten sowie Transkription &amp; Audio die
        Modelle wählen. „Empfohlen“ kennzeichnet einen guten Ausgangspunkt.
      </p>

      <div className="mt-3 rounded-lg border border-brand-teal/40 bg-brand-teal/5 p-3.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="font-display text-sm font-bold text-brand-dark-gray">
              Spielerischer Schnelltest
            </h4>
            <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
              Drei echte Bereitschaftsprüfungen zeigen dir sofort, ob Transkription,
              Agentenmodelle und Datenschutz zusammenpassen.
            </p>
          </div>
          <button
            type="button"
            onClick={handleSmartTest}
            disabled={smartTestBusy}
            className="rounded-lg bg-brand-teal px-3.5 py-2 font-body text-xs font-semibold text-white transition-colors hover:bg-brand-teal/90 disabled:opacity-40"
          >
            {smartTestBusy ? "Test läuft …" : "Schnelltest starten"}
          </button>
        </div>
        {smartTestMessage && (
          <p className="mt-2 font-body text-xs font-medium text-brand-teal">
            {smartTestMessage}
          </p>
        )}
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-brand-teal/40 bg-brand-teal/5 p-3.5">
          <h4 className="font-display text-sm font-bold text-brand-dark-gray">
            Cloud-KI
          </h4>
          <p className="mt-1.5 font-body text-xs leading-relaxed text-brand-gray">
            Ein Google- oder OpenAI-Schlüssel stellt die Modelle dieses Anbieters
            für Transkription, Live-Untertitel und Agenten bereit. Beim Speichern
            wird die Verbindung geprüft; die Modellauswahl bleibt unverändert.
          </p>
        </div>

        <div className="rounded-lg border border-brand-light-gray-1 p-3.5">
          <h4 className="font-display text-sm font-bold text-brand-dark-gray">
            Lokale KI und Datenschutzmodus
          </h4>
          <p className="mt-1.5 font-body text-xs leading-relaxed text-brand-gray">
            Lokale Transkription benötigt keinen Schlüssel. Für lokale Analysen unten
            einen selbst gehosteten Dienst verbinden, den Eignungstest ausführen und
            unter Assistenten eine passende Empfehlung wählen. Der Datenschutzmodus sperrt Cloud-Wege.
            {disabledImpact.length > 0 && (
              <>
                {" "}Einschränkung: {disabledImpact.map((i) => i.feature).join(", ")}{" "}
                bleiben deaktiviert, bis ein Cloud-Schlüssel hinzugefügt wird.
              </>
            )}
          </p>
          {localOnly ? (
            <p className="mt-2 font-body text-xs font-medium text-brand-teal">
              Der Datenschutzmodus ist aktiv.
            </p>
          ) : (
            <button
              type="button"
              onClick={handlePrivacyFirst}
              disabled={privacyBusy}
              className="mt-2 rounded border border-brand-light-gray-1 px-3 py-1.5 font-body text-xs font-medium text-brand-dark-gray transition-colors hover:border-brand-teal hover:text-brand-teal disabled:opacity-40"
            >
              Datenschutzmodus einschalten
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-brand-light-gray-1 bg-white p-3.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="font-display text-sm font-bold text-brand-dark-gray">
              Lokales Transkriptionslabor
            </h4>
            <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
              Vergleiche lokale Transkription mit echten Beispielen. Dieser Test prüft
              Audioqualität und Latenz; er ändert keine Einstellungen automatisch.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {onOpenQualityLab && (
              <button
                type="button"
                onClick={onOpenQualityLab}
                className="rounded-lg border border-brand-light-gray-1 px-3.5 py-2 font-body text-xs font-semibold text-brand-dark-gray transition-colors hover:border-brand-teal hover:text-brand-teal"
              >
                A/B- und Sprachlabor öffnen
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowLab((value) => !value)}
              className="rounded-lg border border-brand-teal px-3.5 py-2 font-body text-xs font-semibold text-brand-teal transition-colors hover:bg-brand-teal/5"
            >
              {showLab ? "Labor schließen" : "Transkriptionslabor öffnen"}
            </button>
          </div>
        </div>
        {showLab && (
          <iframe
            src="/calibration.html"
            title="Modell-Labor"
            className="mt-3 h-[640px] w-full rounded-lg border border-brand-light-gray-1 bg-surface"
          />
        )}
      </div>

      {stage === "partial" && readiness && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5">
          <p className="font-body text-xs font-semibold text-amber-900">
            Fast geschafft: Der Schlüssel ist gespeichert, die aktuelle Einrichtung ist aber noch nicht lauffähig.
          </p>
          <p className="mt-1 font-body text-xs leading-relaxed text-amber-900">
            {readiness.reason}
          </p>
        </div>
      )}

      {stage === "ready" && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-teal/40 bg-brand-teal/5 px-3.5 py-2.5">
          <p className="font-body text-xs font-medium text-brand-dark-gray">
            {localOnly
              ? "Einrichtung abgeschlossen: Die gewählten lokalen Transkriptions- und Agentenmodelle sind bereit."
              : "Einrichtung abgeschlossen: Die gewählten Transkriptions- und Agentenmodelle sind bereit."}
          </p>
          <button
            type="button"
            onClick={onContinue}
            className="rounded-lg bg-brand-teal px-3.5 py-2 font-body text-xs font-semibold text-white transition-colors hover:bg-brand-teal/90"
          >
            Zum ersten Gespräch
          </button>
        </div>
      )}
    </div>
  );
}
