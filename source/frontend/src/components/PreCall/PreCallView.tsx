import { useEffect, useState, type ReactNode } from "react";
import type { Directive, Document, Session, Speaker } from "../../types";
import * as api from "../../services/api";
import DocumentUpload from "./DocumentUpload";
import DirectiveInput from "./DirectiveInput";
import DirectiveList from "./DirectiveList";
import MeetingContextSetup, { MEETING_TYPES } from "./MeetingContextSetup";
import SpeakerSetup from "./SpeakerSetup";
import TranscriptImport from "./TranscriptImport";
import EditableSessionName from "../EditableSessionName";
import InfoTooltip from "../InfoTooltip";
import DeviceSetupAssistant from "./DeviceSetupAssistant";
import PreparationDossier from "./PreparationDossier";

interface Props {
  session: Session;
  directives: Directive[];
  documents: Document[];
  speakers: Speaker[];
  transcriptCount: number;
  processingTranscript?: boolean;
  processingError?: string | null;
  startError?: string | null;
  isStarting?: boolean;
  onStartCall: () => void;
  onOpenVoiceSettings: () => void;
  captureSystemAudio?: boolean;
  onToggleSystemAudio?: (enabled: boolean) => void;
  onProcessTranscript: () => void;
  onRefreshDirectives: () => void;
  onRefreshDocuments: () => void;
  onRefreshSpeakers: () => void;
  onRefreshTranscripts: () => Promise<void>;
  onRenameSession: (name: string) => Promise<void>;
  onUpdateSessionContext: (data: { meeting_type?: Session["meeting_type"]; meeting_context?: string }) => Promise<void>;
}

// One setup step. Collapsed by default when it holds nothing yet, open when
// it does, and the header always says how much is in it, so the page reads
// as a checklist rather than a form.
function SetupSection({
  title,
  summary,
  tooltip,
  defaultOpen,
  optional = false,
  children,
}: {
  title: string;
  summary: string;
  tooltip?: { content: string; details: string[] };
  defaultOpen: boolean;
  optional?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const id = `precall-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;
  return (
    <section className="rounded-xl border border-brand-light-gray-1 bg-surface shadow-sm">
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={id}
          className="flex min-w-0 flex-1 items-center gap-3 text-left"
        >
          <svg
            className={`h-3.5 w-3.5 shrink-0 text-brand-mid-gray transition-transform ${open ? "rotate-90" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span className="min-w-0">
            <span className="font-display text-sm font-semibold text-brand-dark-gray">
              {title}
              {optional && <span className="ml-1.5 font-body text-[11px] font-normal text-brand-mid-gray">optional</span>}
            </span>
            <span className="block truncate font-body text-xs text-brand-mid-gray">{summary}</span>
          </span>
        </button>
        {tooltip && <InfoTooltip content={tooltip.content} details={tooltip.details} />}
      </div>
      <div id={id} hidden={!open} className="border-t border-brand-light-gray-1 px-4 py-4">
        {children}
      </div>
    </section>
  );
}

function pluralize(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

export default function PreCallView({
  session,
  directives,
  documents,
  speakers,
  transcriptCount,
  processingTranscript = false,
  processingError = null,
  startError = null,
  isStarting = false,
  onStartCall,
  onOpenVoiceSettings,
  captureSystemAudio,
  onToggleSystemAudio,
  onProcessTranscript,
  onRefreshDirectives,
  onRefreshDocuments,
  onRefreshSpeakers,
  onRefreshTranscripts,
  onRenameSession,
  onUpdateSessionContext,
}: Props) {
  const [hasImport, setHasImport] = useState(false);
  const [voiceEnrolled, setVoiceEnrolled] = useState<boolean | null>(null);
  const [showConsent, setShowConsent] = useState(false);
  const hasImportedTranscript = hasImport || transcriptCount > 0;

  useEffect(() => {
    let active = true;
    api.getVoiceProfileStatus()
      .then((status) => {
        if (active) setVoiceEnrolled(status.enrolled);
      })
      .catch((err) => console.error("Failed to load voice profile status", err));
    return () => { active = false; };
  }, []);

  const handleImported = () => {
    setHasImport(true);
    void onRefreshTranscripts();
  };

  const typeLabel = MEETING_TYPES.find((t) => t.value === session.meeting_type)?.label ?? "Allgemein";
  const activeDirectives = directives.filter((d) => d.active).length;
  const readiness = [
    typeLabel,
    documents.length ? pluralize(documents.length, "Dokument", "Dokumente") : null,
    activeDirectives ? pluralize(activeDirectives, "Anweisung", "Anweisungen") : null,
    speakers.length ? pluralize(speakers.length, "Teilnehmer", "Teilnehmer") : "Teilnehmer werden automatisch erkannt",
  ].filter(Boolean).join(" · ");

  const soleUserNeedsVoice = speakers.filter((s) => s.is_user).length === 1 && voiceEnrolled === false;
  const error = hasImportedTranscript ? processingError : startError;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-12">
      {/* Action bar: the one thing this screen is for stays in reach while
          the setup below scrolls. */}
      <div className="sticky top-0 z-10 -mx-4 border-b border-brand-light-gray-1 bg-canvas/95 px-4 pb-3 pt-5 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="min-w-0 flex-1">
            <EditableSessionName
              name={session.name}
              onRename={onRenameSession}
              className="text-brand-teal-dark"
            />
            <p className="mt-0.5 truncate font-body text-xs text-brand-mid-gray">{readiness}</p>
          </div>
          {hasImportedTranscript ? (
            <button
              type="button"
              onClick={onProcessTranscript}
              disabled={processingTranscript}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-brand-amber px-5 py-2.5 font-display text-sm font-semibold text-white shadow-md transition-colors hover:bg-amber-600 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-brand-amber focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {processingTranscript ? "Wird verarbeitet ..." : "Transkript verarbeiten"}
            </button>
          ) : (
            <button
              type="button"
              onClick={onStartCall}
              disabled={isStarting}
              className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-brand-teal px-5 py-2.5 font-display text-sm font-semibold text-white shadow-md transition-colors hover:bg-brand-teal-dark hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-brand-teal-light focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span className={`inline-block h-2 w-2 rounded-full ${isStarting ? "animate-pulse bg-white/70" : "bg-white"}`} aria-hidden="true" />
              {isStarting ? "Wird gestartet ..." : "Gespräch starten"}
            </button>
          )}
        </div>
        {error && (
          <div role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 font-body text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      <div className="mt-5 space-y-3">
        {!hasImportedTranscript && (
          <SetupSection
            title="Geräte & lokale Bereitschaft"
            summary="Mikrofon, Wiedergabemix, Pegel und lokale Modelle prüfen"
            defaultOpen={false}
          >
            <DeviceSetupAssistant />
          </SetupSection>
        )}
        {/* Live-call options and the recording notice sit right under the
            button they qualify; an import has neither. */}
        {!hasImportedTranscript && (
          <div className="rounded-xl border border-brand-light-gray-1 bg-surface p-4 shadow-sm">
            <label className="flex cursor-pointer items-start justify-between gap-4">
              <span className="min-w-0">
                <span className="font-display text-sm font-semibold text-brand-dark-gray">PC-Ton des Gesprächs ebenfalls aufnehmen</span>
                <span className="mt-0.5 block font-body text-xs leading-relaxed text-brand-mid-gray">
                  Das Mikrofon wird immer aufgenommen. Der Windows-Systemton wird als getrennte Spur
                  erfasst, damit Discord-, WhatsApp- und andere entfernte Stimmen von deiner Stimme
                  unterschieden werden.
                </span>
              </span>
              <span className="relative mt-0.5 inline-flex shrink-0">
                <input
                  type="checkbox"
                  role="switch"
                  checked={captureSystemAudio ?? false}
                  onChange={(e) => onToggleSystemAudio?.(e.target.checked)}
                  className="peer sr-only"
                />
                <span className="h-6 w-11 rounded-full bg-brand-light-gray-1 transition-colors peer-checked:bg-brand-teal peer-focus-visible:ring-2 peer-focus-visible:ring-brand-teal-light" aria-hidden="true" />
                <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-surface shadow transition-transform peer-checked:translate-x-5" aria-hidden="true" />
              </span>
            </label>
            {captureSystemAudio === false && (
              <p className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 font-body text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
                Nur Mikrofon: Entfernte Teilnehmer werden nur transkribiert, wenn dein Mikrofon sie
                hört. Bei Kopfhörern fehlt deshalb meist die Gegenseite.
                {soleUserNeedsVoice && (
                  <>
                    {" "}Eine Stimmkalibrierung verbessert außerdem deine Sprechererkennung.{" "}
                    <button type="button" onClick={onOpenVoiceSettings} className="font-semibold underline">
                      Transkription &amp; Audio öffnen
                    </button>
                  </>
                )}
              </p>
            )}
            <p className="mt-3 flex flex-wrap items-center gap-x-2 font-body text-xs text-brand-gray">
              <span className="text-brand-amber" aria-hidden="true">&#9888;</span>
              <span>Dieses Gespräch wird aufgenommen und transkribiert. Informiere alle Beteiligten und hole die erforderliche Zustimmung ein.</span>
              <button
                type="button"
                onClick={() => setShowConsent((v) => !v)}
                aria-expanded={showConsent}
                className="font-semibold text-brand-teal hover:underline"
              >
                {showConsent ? "Weniger" : "Mehr"}
              </button>
            </p>
            {showConsent && (
              <p className="mt-2 font-body text-xs leading-relaxed text-brand-mid-gray">
                Debate AI transkribiert Live-Audio, um Fragen und Hinweise zu erzeugen. Stelle vor
                dem Start sicher, dass alle Teilnehmer informiert sind und der Aufnahme sowie
                Transkription zugestimmt haben. Du bist für die Einhaltung geltender Gesetze und
                Unternehmensrichtlinien verantwortlich.
              </p>
            )}
          </div>
        )}

        <SetupSection
          title="Kontext"
          summary={session.meeting_context ? session.meeting_context : "Beschreibe Art und Ziel des Gesprächs"}
          defaultOpen
          tooltip={{
            content: "Beschreibe den Gesprächstyp, damit die KI den passenden Blickwinkel verwendet.",
            details: [
              "Internes Lernen: Begriffe, Missverständnisse, Lernfragen und Folgematerial",
              "Anbieter oder Partner: Planung, Aktualisierungen, Zusagen und Zusammenarbeit",
              "Kunde oder Umsetzung: Ziele, Risiken, Entscheidungen, Chancen und nächste Schritte",
            ],
          }}
        >
          <MeetingContextSetup session={session} onUpdate={onUpdateSessionContext} />
        </SetupSection>

        <SetupSection
          title="Dokumente"
          optional
          summary={documents.length ? documents.map((d) => d.filename).join(", ") : "Referenzmaterial für die Analyse"}
          defaultOpen={documents.length > 0}
          tooltip={{
            content: "Lade vor dem Gespräch Referenzmaterial hoch. Die KI verwendet es als Kontext für Fragen und Hinweise.",
            details: [
              "Hochgeladene Dateien werden zusammen mit dem Live-Transkript analysiert",
              "Im lokalen Datenschutzmodus bleiben geeignete Textdateien auf diesem Gerät",
              "Unterstützt PDF-, Word-, Tabellen- und Textdateien",
              "Dokumente bleiben beim Gespräch gespeichert und können jederzeit entfernt werden",
            ],
          }}
        >
          <DocumentUpload sessionId={session.id} documents={documents} onRefresh={onRefreshDocuments} />
        </SetupSection>

        <SetupSection
          title="Lokales Vorbereitungsdossier"
          optional
          summary="Kernthesen, Begriffe, Gegenpositionen und ausgewählte Unterlagen"
          defaultOpen={false}
        >
          <PreparationDossier sessionId={session.id} />
        </SetupSection>

        <SetupSection
          title="Transkript oder Aufnahme importieren"
          optional
          summary={hasImportedTranscript ? `${transcriptCount || "Importierte"} Zeilen bereit` : "Ein früheres Gespräch statt eines Live-Gesprächs analysieren"}
          defaultOpen={hasImportedTranscript}
          tooltip={{
            content: "Importiere ein vorhandenes Transkript oder eine Audioaufnahme. Die KI verarbeitet es wie ein abgeschlossenes Gespräch.",
            details: [
              "Transkripte: .txt, .md, .docx - werden in Sprecherabschnitte zerlegt",
              "Audio: .m4a, .mp3, .wav, .ogg, .flac - wird zuerst transkribiert",
              "Nach dem Import erscheint die Aktion \"Transkript verarbeiten\"",
            ],
          }}
        >
          <TranscriptImport sessionId={session.id} onImported={handleImported} />
        </SetupSection>

        <SetupSection
          title="Coaching-Anweisungen"
          optional
          summary={activeDirectives ? pluralize(activeDirectives, "aktive Anweisung", "aktive Anweisungen") : "Worauf die KI im Gespräch achten soll"}
          defaultOpen={directives.length > 0}
          tooltip={{
            content: "Gib der KI konkrete Anweisungen. Sie steuern die Fragen und Hinweise aller Assistenten.",
            details: [
              "Beispiel: \"Erfasse unklare Begriffe und passende Rückfragen\"",
              "Anweisungen lassen sich ohne Löschen ein- und ausschalten",
              "Aktive Anweisungen werden bei jeder Analyse berücksichtigt",
              "Neue Anweisungen können auch während des Gesprächs ergänzt werden",
            ],
          }}
        >
          <div className="space-y-4">
            <DirectiveInput sessionId={session.id} onAdded={onRefreshDirectives} />
            <DirectiveList sessionId={session.id} directives={directives} onRefresh={onRefreshDirectives} />
          </div>
        </SetupSection>

        <SetupSection
          title="Teilnehmer"
          optional
          summary={speakers.length ? speakers.map((s) => s.name).join(", ") : "Werden im Gespräch erkannt; Namen können vorab festgelegt werden"}
          defaultOpen={speakers.length > 0}
          tooltip={{
            content: "Lege Teilnehmer vorab an, damit Transkriptabschnitte Stimmen zugeordnet werden. Andernfalls werden Sprecher automatisch erkannt.",
            details: [
              "Namen, Rollen und Farben je Teilnehmer vergeben",
              "Einen Sprecher als \"Ich\" markieren",
              "Eine gespeicherte eigene Stimme verbessert die Zuordnung",
              "Automatisch erkannte Sprecher lassen sich später umbenennen",
            ],
          }}
        >
          <SpeakerSetup sessionId={session.id} speakers={speakers} onRefresh={onRefreshSpeakers} />
        </SetupSection>

        <section className="rounded-xl border border-brand-light-gray-1 bg-surface px-5 py-4 shadow-sm">
          <p className="font-display text-sm font-semibold text-brand-dark-gray">KI-Assistenten sind automatisch aktiv</p>
          <p className="mt-1 font-body text-xs leading-5 text-brand-mid-gray">
            Deutsche Live-Transkription, Sofortantwort, Gegenargument, Analogie, Auto-Recherche,
            Gesamtanalyse und Abschlussanalyse verwenden die geprüften Standardwerte.
          </p>
        </section>
      </div>
    </div>
  );
}
