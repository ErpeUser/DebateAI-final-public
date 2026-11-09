/** Zentrale deutsche Oberflaechentexte. Technische Modellnamen bleiben unveraendert. */

export const DE = {
  admin: {
    title: "Einstellungen",
    loading: "Konfiguration wird geladen ...",
    tabs: {
      agents: { label: "Assistenten", hint: "Modelle, Anweisungen und Verhalten der Analyse-Assistenten" },
      transcription: { label: "Transkription & Audio", hint: "Sprechererkennung und Transkription einstellen" },
      privacy: { label: "Datenschutz", hint: "Persönliche Daten bei lokaler und Cloud-Verarbeitung schützen" },
      keys: { label: "Verbindungen", hint: "KI-Anbieter und eigene Modellserver verbinden" },
      about: { label: "Info", hint: "Programmversion und Änderungen" },
    },
    sections: {
      listening: { title: "Zuhören", blurb: "Überträgt das Gespräch an die stille Live-Transkription für sofortige Zwischenergebnisse." },
      live: { title: "Live-Analyse", blurb: "Analysiert das Gespräch laufend, verbessert Erkenntnisse und hält die Live-Empfehlungen aktuell." },
      post: { title: "Nachbesprechung", blurb: "Läuft nach dem normalen Beenden oder manuell: Zwei unabhängige Analysen werden zu einer Zusammenfassung verbunden." },
      other: { title: "Weitere", blurb: "Assistenten, die noch keinem Bereich zugeordnet sind." },
    },
  },
  agentTypes: {
    audio: "Audio",
    text: "Textanalyse",
    meta: "Meta",
    db: "Wissen",
  },
  live: {
    strategicSignals: "Strategische Live-Signale",
    updated: "Aktualisiert",
    signal: "Signal",
    risk: "Risiko",
    nextQuestion: "Nächste Frage",
    opportunity: "Chance",
    actionCue: "Handlungsimpuls",
    enablement: "Befähigung",
    partner: "Partner",
    delivery: "Umsetzung",
    support: "Unterstützung",
    owner: "Zuständig",
    status: "Status",
    partial: "Die Zusammenfassung beruht auf einer unvollständigen Modellantwort.",
    chat: "Frage",
    directive: "Anweisung",
    chooseModel: "Wähle ein Modell für Fragen zum Gespräch. Die Empfehlung ist ein guter Ausgangspunkt.",
    postProcessing: "Nachbearbeitung läuft ...",
    resumeToAsk: "Audio fortsetzen, um eine Frage zu stellen ...",
    askAnything: "Dieses Gespräch fragen ...",
    directiveExample: "z. B. Gehe auf den letzten Widerspruch ein ...",
    readingCall: "Gespräch wird ausgewertet ...",
    reloadIfActive: "Lade die App neu, falls das Gespräch weiterhin als aktiv angezeigt wird.",
    backgroundCompletion: "Das Gespräch erscheint nach Abschluss automatisch als beendet.",
    runtimeStatus: {
      localReady: "Lokal bereit",
      ready: "Bereit",
      deepening: "Vertiefung läuft",
      deepeningComplete: "Vertiefung abgeschlossen",
      sourceUnclear: "Quelle unklar",
      signInRequired: "Anmeldung erforderlich",
      localOnly: "Nur lokal",
      connecting: "Verbindung wird hergestellt ...",
    },
    modelPicker: {
      title: "Modell für Fragen auswählen",
      none: "Nicht ausgewählt",
      recommended: "Empfohlen",
    },
    activity: {
      listening: "Die Assistenten hören zu.",
      firstExpected: "erste Hinweise in etwa",
      nextCheck: "nächste Prüfung in",
      checksEvery: "prüft alle",
      never: "Noch nie",
      ago: "zuvor",
      dueNow: "jetzt fällig",
      runningLate: "verspätet",
      eventDriven: "bei neuem Ereignis",
      atCallEnd: "beim Gesprächsende",
      next: "nächste Prüfung",
      states: {
        off: "Aus",
        blocked: "Einrichtung fehlt",
        waiting: "Bereit",
        running: "Läuft",
        failing: "Fehler",
      },
      reasons: {
        no_model: "Anmeldung oder Modellauswahl erforderlich",
        privacy_first: "Nur lokale Verarbeitung erlaubt",
        pii_shield: "Lokale Schutzfunktion verhindert die Übertragung",
        meeting_type: "Für diese Gesprächsart nicht aktiv",
        disabled: "Ausgeschaltet",
      },
    },
  },
  agents: {
    audio_gateway: {
      name: "Audio-Transkription",
      description: "Stille Audio-Weiterleitung für die laufende Transkription. Sie analysiert nichts und erzeugt keine Erkenntnisse.",
    },
    consolidated_analyst: {
      name: "Gesamtanalyse",
      description: "Analysiert das Gespräch in einem Aufruf aus mehreren einstellbaren Perspektiven und erstellt Fragen, Beobachtungen, Chancen und Aufgaben.",
    },
    objection_handler: {
      name: "Debatten-Assistent",
      description: "Reagiert live auf Aussagen, Fragen und Einwände mit sofort aussprechbaren Empfehlungen auf Deutsch und prüft unsichere Fakten bei Bedarf im Hintergrund.",
    },
    synthesizer: {
      name: "Hauptanalyse",
      description: "Prüft Erkenntnisse, verbindet Zusammenhänge und erkennt übergeordnete Ziele, Muster und Widersprüche.",
    },
    opportunity_specialist: {
      name: "Chancen-Abgleich",
      description: "Gleicht erkannte Chancen mit den ausgewählten Wissensquellen ab und ergänzt passende Belege.",
    },
    strategic_signals: {
      name: "Strategische Signale",
      description: "Verdichtet live das wichtigste Signal, Risiko, die nächste Frage, Chance und Handlungsempfehlung.",
    },
    transcript_refiner: {
      name: "Transkript-Korrektur",
      description: "Korrigiert Zeichensetzung, Groß-/Kleinschreibung, Satzgrenzen und offensichtliche Verhörer, ohne den Inhalt umzuschreiben.",
    },
    brief_meeting_lens: {
      name: "Sitzungsprotokoll",
      description: "Erfasst Ergebnisse, Entscheidungen, Hindernisse, Zusagen und Folgeschritte für die Nachbesprechung.",
    },
    brief_discovery_lens: {
      name: "Erkenntnisanalyse",
      description: "Erfasst Ziele, Probleme, Wissenslücken, Chancen, Risiken und offene Punkte für die Nachbesprechung.",
    },
    brief_arbiter: {
      name: "Abschlussredaktion",
      description: "Vergleicht beide Nachbesprechungen, klärt Abweichungen und erstellt die endgültige Zusammenfassung.",
    },
  } satisfies Record<string, { name: string; description: string }>,
  audioGatewayPrompt: "Du bist eine stille Audio-Weiterleitung. Deine einzige Aufgabe ist, einem Live-Gespräch zuzuhören und die Transkription zu ermöglichen. Sprich nicht, analysiere nicht, kommentiere nicht und erzeuge keine eigene Ausgabe. Höre nur zu.",
} as const;

export type GermanAgentSlug = keyof typeof DE.agents;

export function germanAgent(slug: string) {
  return DE.agents[slug as GermanAgentSlug];
}
