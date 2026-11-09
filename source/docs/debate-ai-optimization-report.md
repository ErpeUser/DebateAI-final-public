# Debate AI - Optimierungsbericht

Stand: 4. November 2026

## Ergebnis

Die bestehende Backchannel-Anwendung bleibt erhalten, ist im sichtbaren Kern aber auf einen deutschen Live-Debattenassistenten optimiert. Der erste Sprechzug entsteht lokal und deterministisch; Qwen-Analyse und Recherche laufen nur danach. Die zwei vorhandenen Modi `debate_forceful` und `debate_persuasive` bleiben erhalten.

## Entscheidungsmatrix

| Bereich | Entscheidung | Kleinste begründete Änderung |
| --- | --- | --- |
| PCM16-Audio, WebSocket, Sprechertrennung | KEEP | Funktionierender Echtzeitpfad, kein Architekturwechsel. |
| Deutsche Transkription | OPTIMIZE | Standardsprache `de`, bestehendes lokales Parakeet weiterverwenden. |
| Sofortsatz | KEEP + OPTIMIZE | Deterministische Erstkarte; konkrete Regeln für Zahlen, Themenflucht, gestapelte Behauptungen und Verneinungen. |
| Qwen-Tiefenrevision | OPTIMIZE | Kompakter Prompt und Claim-/Revisionsgate vor sichtbarer Ersetzung. |
| Qwen3 4B | KEEP | Aktuell einziges installiertes Ollama-Modell; kein zusätzlicher Download. |
| Andere Qwen-Varianten | DO NOT KEEP | Kein zweites Modell und kein weiterer Hintergrunddienst verbleibt. |
| Live-Agenten im Debattenmodus | SIMPLIFY | Bestehende Kernpfade wiederverwenden; keine Agentenbibliothek hinzugefügt. |
| LangGraph, CrewAI, DSPy | DO NOT ADD | Mehr Laufzeit- und Betriebsaufwand ohne nachgewiesenen Vorteil für den Sofortpfad. |
| Recherche | KEEP + OPTIMIZE | Auto-Recherche schaltbar, Wenig/Normal/Oft und manuelle Kategorien; niemals Blocker der Erstkarte. |
| Post-Debatten-Evaluation | KEEP + OPTIMIZE | Lokale Auswertung, Änderungen nur nach manueller Bestätigung. |
| Windows-Unterprozesse | OPTIMIZE | Versteckte Prozessflags für verwaltete PostgreSQL-, Ollama-, Transkriptions- und Bridge-Prozesse. |
| Oberfläche | OPTIMIZE | Deutsch, dominante Empfehlung plus genau eine Alternative, Quellenstatus statt Beweisvortäuschung. |

## Umgesetzte P0-Korrekturen

- Teiltranskripte sind ersetzbare Hypothesen pro Äußerung. Ein finales `nicht` ersetzt den Zwischenstand; eine langsame Antwort auf den alten Wortlaut wird verworfen.
- Transkript-, Claim- und sichtbare Empfehlungsrevision sind getrennt. Eine spätere Modellantwort darf denselben Claim verbessern, aber keinen neueren Claim überschreiben.
- Gesprochene Nutzerbefehle wie `Debate AI, Recherche aus` sind Steuerereignisse statt Gegnerargumente. Externe Sprecher können sie nicht auslösen.
- Zahlen gelten erst mit claim-bezogener, unterstützender Quelle als bestätigt. `Gefunden`, `gelesen`, `stützt`, `widerspricht` und `unklar` sind getrennte Zustände.
- Die sichtbare Karte bestätigt ihre konkrete Revision an den Server. Der Benchmark zählt nur eine tatsächlich sichtbare Modellrevision als Modellerfolg.
- Der Built-in-Prompt wird versions- und hashbasiert migriert; echte benutzerdefinierte Prompts bleiben erhalten.
- Die Wortbegrenzung entfernt keine abschließende Verneinung, Bedingung oder Einheit nur zur Einhaltung einer starren Zahl.

## Messungen

Realer lokaler Pfad: Ollama `qwen3:4b`, 20 deutsche Debattenzüge, Recherche aus.

| Messung | Ergebnis |
| --- | ---: |
| Deterministische Erstkarte, Median | 0,194 ms |
| Deterministische Erstkarte, p95 | 0,284 ms |
| Sichtbar akzeptierte Qwen-Revision, Median | 6.396,833 ms |
| Sichtbar akzeptierte Qwen-Revision, p95 | 7.027,819 ms |
| Sichtbar akzeptierte Modellverbesserungen | 8/20 |
| Absichtlich verworfene, nicht bessere Modellformulierungen | 12/20 |
| Kompakter Live-Prompt | 1.465 Zeichen |
| Installierte Ollama-Modelle | nur `qwen3:4b` (2,5 GB) |

Die Erstkarte erfüllt den Drei-Sekunden-Vertrag mit großem Abstand, sobald verwertbarer Text vorliegt. Qwen darf sie nur ersetzen, wenn die Revision für denselben aktuellen Claim sichtbar besser ist. Die 12 verworfenen Revisionen sind daher keine leere UI, sondern der ehrliche Nachweis der Anti-Flacker-/Qualitätssperre.

Messdatei: `docs/evidence/debate-vnext-benchmark.json`. Der Benchmark zählt die Schablonen-Sofortkarte nicht als Modell-Erfolg und bestätigt `claim_id` plus `recommendation_revision`.

## Verifikation

- Backend: 1.472 Tests bestanden, 2 übersprungen.
- Desktop: 149 Tests bestanden, 1 übersprungen.
- Frontend: 249 Tests bestanden.
- TypeScript/Vite-Produktionsbuild: erfolgreich; bestehender Hinweis auf ein JavaScript-Chunk über 500 kB bleibt.
- Fokussierte P0-Suite: 92 Tests bestanden.
- Benchmark-Suite nach Reparatur der Mehrfachereignis-Messung: 14 Tests bestanden.

## Externe Prüfung

- [Ollama API-Dokumentation](https://github.com/ollama/ollama/blob/main/docs/api.md): strukturierte JSON-Ausgabe, Streaming, `keep_alive` sowie Token- und Laufzeitmetriken sind offiziell dokumentiert; kein zusätzlicher Server nötig.
- [ArguMentor Prompt-Aufteilung](https://github.com/TeslaNeuro/ArguMentor/blob/main/packages/debate-core/src/prompts.ts): öffentlich sichtbare Trennung von Debattenrolle, Analyse und Coaching sowie Regeln gegen erfundene Quellen. Übernommen wurden nur Prinzipien.
- [Debatrix Memory-Modell](https://github.com/ljcleo/debatrix/blob/main/debatrix/panel/interface/common/memory.py): typisierte, quellenmarkierte und gefiltert abrufbare Gesprächsteile stützen die kleine Claim-/Utterance-/Revision-Struktur statt eines unkontrollierten Volltranskripts.
- [RealtimeSTT Engine Comparison](https://github.com/koljab/realtimestt/blob/01ce19decaa5506873ee7824510b062edbf31a03/docs/transcription-engines.md): ein ASR-Wechsel bleibt ohne eigenen deutschen WER-/Latenznachweis unnötig.

## Verbleibende Grenzen

### Technische Rubrik fuer die Benchmark-Auswertung

Der Produktionsbenchmark prueft angenommene Debattenkarten zusaetzlich mit
einer deterministischen Vertragsrubrik. Sie umfasst Schema, sprechbaren
Primaerzug, Wortgrenzen, Zielclaim und Evidence-Guards fuer unbelegte Zahlen
oder Attributionen. Das Ergebnis wird als technischer Vorcheck protokolliert;
es ist kein Ersatz fuer eine menschliche Bewertung von deutscher Rhetorik,
Sprechbarkeit oder strategischer Qualitaet. `human_review_required` bleibt
deshalb bewusst wahr.

- Qwen3 4B formuliert nicht jedes Mal besser: Im aktuellen Lauf wurden nur 8 von 20 Revisionen sichtbar angenommen. Der Sofortsatz bleibt trotzdem verfügbar.
- Suchtreffer-Snippets bleiben `gefunden`, bis ein gelesener Passagebeleg den Claim wirklich stützt oder widerlegt. Beliebige Webseiten werden im kleinsten Patch noch nicht vollständig automatisch gelesen.
- Lokales Parakeet kann bei sehr kurzen, überlappenden oder stark verrauschten Segmenten Fehler machen. Ein späterer ASR-Wechsel braucht einen aufgenommenen deutschen A/B-Test.
- Die echte Discord-Ende-zu-Ende-Latenz mit Hardware-Audio wurde in diesem Lauf nicht neu gemessen; belegt ist die Pipeline ab verwertbarem Text.
- Eine bereits installierte EXE erhält Quelländerungen erst nach einem neuen Desktop-Build. Der laufende Benutzerprozess und seine Datenbank wurden während dieser Arbeit nicht beendet oder überschrieben.
