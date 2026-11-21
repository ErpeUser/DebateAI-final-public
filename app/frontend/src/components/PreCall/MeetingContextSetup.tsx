import { useEffect, useState } from "react";
import type { MeetingType, Session } from "../../types";

interface Props {
  session: Session;
  onUpdate: (data: {
    meeting_type?: MeetingType;
    meeting_context?: string;
  }) => Promise<void>;
}

export const MEETING_TYPES: {
  value: MeetingType;
  label: string;
  hint: string;
  placeholder: string;
}[] = [
  {
    value: "debate_persuasive",
    label: "Debatte · Überzeugen",
    hint: "Fertig eingestellt: Gemeinsamkeiten, starke Belege und passende Analogien überzeugen Gegner und Zuhörer.",
    placeholder: "Optional: Thema, eigene Position und Ziel der Debatte.",
  },
  {
    value: "debate_forceful",
    label: "Debatte · Brutal-sachlich",
    hint: "Fertig eingestellt: Die schwächste Prämisse direkt angreifen, Belege fordern und Widersprüche präzise offenlegen.",
    placeholder:
      "Optional: Thema, gegnerische Position und besonders strittige Behauptungen.",
  },
  {
    value: "general",
    label: "Allgemein / automatisch erkennen",
    hint: "Die KI erkennt die Gesprächsform aus Transkript und Kontext.",
    placeholder:
      "Beispiel: Interne Diskussion über das Thema und die gewünschten Ergebnisse.",
  },
  {
    value: "client_sales",
    label: "Kunde / Interessent",
    hint: "Für Bedarfsermittlung, Kundenstrategie, Kaufsignale und Vertriebsnachbereitung.",
    placeholder:
      "Beispiel: Gespräch mit einem Kunden über Ziele, Risiken, Zeitplan und mögliche Unterstützung.",
  },
  {
    value: "customer_delivery",
    label: "Kundenumsetzung",
    hint: "Für Umsetzung, Projekte, Betrieb oder technische Arbeitssitzungen.",
    placeholder:
      "Beispiel: Wöchentliche Planung mit Hindernissen, Zuständigen, Umfang und nächsten Schritten.",
  },
  {
    value: "internal_enablement",
    label: "Interne Befähigung",
    hint: "Für Schulungen, Wissenstransfer und technische Weiterbildung.",
    placeholder:
      "Beispiel: Eine Fachperson erklärt dem Team ein technisches Thema und seine klare Vermittlung.",
  },
  {
    value: "internal_checkin",
    label: "Internes Gespräch",
    hint: "Für Einzelgespräche, Coaching oder informellen internen Austausch.",
    placeholder:
      "Beispiel: Kurzer Austausch zu aktuellen Aufgaben und benötigter Unterstützung.",
  },
  {
    value: "vendor_partner",
    label: "Anbieter / Partner",
    hint: "Für Planung, Programme, Partnerschaften oder Anbieter-Aktualisierungen.",
    placeholder:
      "Beispiel: Partner-Update zu Planung, offenen Anforderungen und Zusagen.",
  },
];

export default function MeetingContextSetup({ session, onUpdate }: Props) {
  const [meetingContext, setMeetingContext] = useState(
    session.meeting_context || session.notes || "",
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setMeetingContext(session.meeting_context || session.notes || "");
  }, [
    session.id,
    session.meeting_type,
    session.meeting_context,
    session.notes,
  ]);

  const selected =
    MEETING_TYPES.find((type) => type.value === session.meeting_type) ||
    MEETING_TYPES[0];
  const dirty = meetingContext !== (session.meeting_context || "");

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate({
        meeting_context: meetingContext.trim(),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-brand-light-gray-1 bg-surface p-4 shadow-sm">
      <div className="grid gap-3 md:grid-cols-[220px,1fr]">
        <div>
          <label className="mb-1 block font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">
            Gesprächstyp
          </label>
          <div className="rounded-md border border-brand-light-gray-1 bg-brand-light-gray-2 px-3 py-2 font-body text-sm font-semibold text-brand-dark-gray">
            {selected.label}
          </div>
          <p className="mt-2 font-body text-xs leading-relaxed text-brand-mid-gray">
            {selected.hint}
          </p>
        </div>

        <div>
          <label className="mb-1 block font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray">
            Ziel / Kontext
          </label>
          <textarea
            value={meetingContext}
            onChange={(event) => setMeetingContext(event.target.value)}
            rows={4}
            placeholder={selected.placeholder}
            className="w-full resize-none rounded-md border border-brand-light-gray-1 bg-surface px-3 py-2 font-body text-sm text-brand-dark-gray placeholder:text-brand-mid-gray focus:border-brand-teal-light focus:ring-1 focus:ring-brand-teal-light"
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <p className="font-body text-xs text-brand-mid-gray">
              Der Kontext wird mit diesem Gespräch gespeichert.
            </p>
            <button
              type="button"
              onClick={handleSave}
              disabled={!dirty || saving}
              className="rounded-md bg-brand-teal px-3 py-1.5 font-body text-xs font-semibold text-white transition-colors hover:bg-brand-teal-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Wird gespeichert ..." : "Kontext speichern"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
