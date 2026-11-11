# Deep-Research-Auftrag: DebateAI gezielt wissenschaftlich verbessern

Stand: 2026-11-11. Diesen Auftrag mit RESEARCH_DE.md, RECONCILIATION_MATRIX_DE.md und dem aktuellen Git-Commit verwenden. Fragen sind Forschungsauftraege, keine bereits bewiesenen Ergebnisse.

## Vision und Grenzen

Privater deutscher Windows-Live-Debattenassistent: Mikrofon/Systemaudio getrennt, genaue Transkripte/Sprecher/Revisionen, Argumentgedaechtnis, kurze sofort sprechbare Hilfe und gegebenenfalls Gegenfrage; Modi Hart/Ueberzeugen. Wahrheitsbindung, Korrektur, begruendete Zustimmung und Nichtausgabe sind wichtiger als Widerspruch um jeden Preis. Erste brauchbare Antwort lokal; explizit erlaubte Recherche/Cloudanalyse getrennt und nicht blockierend. Daten/Keys/Anmeldungen/Modelle/Playbooks erhalten. Keine automatische Siegerkonfiguration aus kleinen Tests oder einem LLM-Urteil.

## Rechercheauftrag

Nutze aktuelle Primaerarbeiten, offizielle Modellkarten/Dokumentation und reproduzierbaren Upstream-Code. Gib Datum/Version/Commit, Sprache, Hardware, Daten und Messdefinition an. Trenne englische Benchmarks/Rechenzentrums-GPUs von deutschem Windows-PC-Einsatz. Issues/Foren liefern Hypothesen, keine eigene Reproduktion. Priorisiere messbaren Nutzen, Datenschutz, Komplexitaet und Rueckbaubarkeit, nicht trendige Frameworklisten.

## A. Prompt, lokale KI und weitere Agenten

1. Wann reicht ein einzelner guter Prompt gegenueber zusaetzlichen Judge-/Recherche-/Kritikeragenten? Gleiche Eingaben, Kontext-, Zeit- und Tokenbudgets; Promptqualitaet von Modellgroesse trennen.
2. Wann verbessert ein lokaler Kritiker Faktentreue, Relevanz oder Sprechbarkeit? Wie oft verschlechtert er eine bereits richtige Antwort? Zusatzlatenz/Ressourcen messen.
3. Wann ist ein staerkeres getrenntes Hintergrundmodell nuetzlicher als ein zweiter lokaler Agent? Konkurrenz auf CPU/GPU, Netzausfall und inzwischen fortgeschrittene Debatte beachten.
4. Welche Pruefungen gehoeren deterministisch in Code (Schema, Revision, Quellenherkunft, leere Ausgabe), welche brauchen semantisches Modellurteil oder Menschen? Fehlerkosten begruenden.
5. Wann darf eine spaetere Antwort eine sichtbare Hilfe ersetzen? Claim-IDs, Korrekturen, veraltete Recherche, Qualitaetsgewinn und kognitive Ablenkung gemeinsam messen.

Minimalexperiment: A bestehender lokaler Einzelpfad; B gleicher Pfad plus lokaler Kritiker; C gleicher Pfad plus getrennte staerkere Hintergrundanalyse. Eine Variable je Ablation, gleicher kausaler Kontext, beide Modi. Erste Antwort und spaetere Verbesserung getrennt auswerten, nicht nur das Endergebnis.

## B. Deutsche Sprache und echte Streamingqualitaet

6. Welche tatsaechlich verfuegbaren deutschen Streaming-Checkpoints lassen sich auf Zielhardware und Windows rechtlich/technisch paketieren? ONNX Whisper Turbo, Parakeet v3, cache-aware Alternativen kontrolliert vergleichen; offline/chunked nicht als gleichwertig streaming ausgeben.
7. Wie beeinflussen Chunklaenge, VAD, Endpunktdetektion und LocalAgreement stabile Wortlatenz, Revisionen und Fehler bei Unterbrechung? p50/p95 statt nur RTF, kein Zukunftsaudio im Replay.
8. Welche Challenge-Saetze entdecken verloren gegangenes nicht/kein, Zahlen, Dezimalstellen, Einheiten, Eigennamen und Selbstkorrekturen? Exakte Annotation und Slotmetriken; Tokenvergleich allein ist kein semantischer Wahrheitsbeweis.
9. Wie verhalten sich zwei Windows-Audioquellen bei 44,1/48kHz, Bluetooth, Geraetewechsel, Sleep/Resume, Echo und Overlap? Reproduzierbaren Drift-/Drop-/Crosstalk-Test entwerfen.
10. Welche Quantisierung, ONNX-Provider und Threadbudgets liefern unter gleichzeitiger ASR/LLM/UI Reserven? RAM/VRAM, thermische Dauerlast und Warteschlangen messen; unterschiedliche Rechner nicht zu einer Rangliste vermischen.

## C. Faire Bewertung

11. Wie verzerren Position, Laenge, Autoritaetston, Sprache, Modellfamilie und Selbstpraeferenz einen LLM-Judge? Gegen verdeckte menschliche Urteile kalibrieren.
12. Wie werden Faktentreue, Sprechbarkeit, Relevanz, Nutzerposition, unnoetige Aggressivitaet und Unsicherheit separat bewertet? Beliebtheit/rhetorische Wirkung ist nicht Wahrheit.
13. Welche Fallzahl genuegt fuer persoenliche Kalibrierung, welche fuer allgemeine Aussagen? Effektgroesse, statistische Einheit, Konfidenzintervalle, Mehrfachvergleiche und Abbruchregeln begruenden. Wiederholungen desselben Falls nicht als unabhaengige Faelle zaehlen.
14. Wie bleiben Timeouts, leere/veraltete Antworten, Fehler, Gleichstand und beide ungeeignet im Nenner? Beispiel einer irrefuehrenden Rangumkehr durch Weglassen von Fehlern liefern.
15. Wie verbindet man Ausgaben, Promptversion, kausalen Kontext, Last und Ratings reproduzierbar ohne private Audio-/Sitzungs-/Keydatenexporte? Hash ist Herkunftshilfe, keine Wahrheits-/Vollstaendigkeitsgarantie.

Pilot: mindestens20 unterschiedliche deutsche Faelle, beide Modi, order-balanced Blindvergleiche, Nullbewertung statt vorbelegter Skalen und Zweitrater auf Teilstichprobe. Diese Groesse ist keine universelle Signifikanzgarantie; weitere Fallzahl anhand Varianz/Effekt planen. Faktenlabels und Nutzwert getrennt.

## D. Gedachtnis, Quellen und Wahrheit

16. Welche Mischung exakter Claims, Argumentgraph und semantischen Retrievals hilft ohne aehnliche gegensaetzliche Aussagen zu verwechseln? Negation, Rollenwechsel, spaete Revision testen.
17. Wie misst man Quellenstuetzung nach Passage, Zeitraum, Population, Einheit und Gegenbelegen? URL/ID allein nicht als Beweis. Prompt-Injection und veraltete Quellen testen.
18. Wann sollte die Hilfe zustimmen, eingrenzen, rueckfragen oder schweigen? Beide Modi ohne erfundene/aggressive Gegenargumente als Erfolg zu belohnen testen.

## E. Zuverlaessigkeit und Werkzeuge

19. Welche minimale Architektur begrenzt native Worker, Uploads und Warteschlangen? Task-Abbruch, Threadende und Prozessende trennen; Browserabbruch und fremd gestarteten Ollama-Server schuetzen.
20. Welche Windows-Update-/Datenmigration bewahrt DPAPI, PostgreSQL, Browserprofile und Playbooks bei Rebranding, Datei-/Antivirussperre, Stromausfall, Startfehler und Rollback? Binaerrollback ist kein DB-Rollback.
21. Welche kleine Bibliothek oder Erweiterung bringt gegenueber bestehendem unittest/pytest, Node, Playwright, pip-audit, Bandit, npm-Lockfile, PyInstaller messbaren Nutzen? Lizenz/Wartung/Offlinebetrieb/Angriffsflaeche/Integrationskosten benennen.

## Verbindliches Ergebnisformat

Zuerst Entscheidungsmatrix: Frage, Evidenz, Uebertragbarkeit, sofort/Experiment/verwerfen/unklar, Nutzen, Risiko, Aufwand. Widerspruechliche Evidenz beidseitig darstellen. Danach je Vorschlag Projektkomponente, kleinster Integrationsschritt, Primaerquelle mit Datum und wirklich stuetzender Aussage, reproduzierbarer Versuch mit Baseline/Kontrollen/Dateneinwilligung, Erfolgskriterium, Fehlernenner, Unsicherheit und Rueckbaukriterium. Prioritaet P0/P1/P2. Hoechstens5 priorisierte Implementierungsempfehlungen.

Zusaetzlich maschinenlesbares JSON pro Experiment: id, hypothesis, variants, controls, metrics, failure_denominator, dataset_requirements, hardware_requirements, privacy_constraints, sources, acceptance_rule, rollback_rule.

Keine perfekte KI, universell beste Agentenzahl, unbelegte Leistungswerte oder fertige Windows-Abnahme behaupten. Forschungsbericht und Quellen an ChatGPT/Codex zurueckgeben; danach gezielte Experimente statt pauschalem Architekturtausch.
