# CODEX – finaler Fortsetzungsauftrag nach 2026-11-10
**Lies diese Datei als Ausführungsauftrag, nicht als Diskussionsentwurf.**

## Phase 0: Autoritative Quellen und Standort
Prüfe zuerst den neuesten Remote-Branch `origin/master`; niemals auf einen hier hartcodierten SHA zurückspringen. Lies vollständig in dieser Reihenfolge:
`AGENTS.md` (Repository-Wurzel), `source/AGENTS.md`, `source/docs/DEBATE_AI_VISION_FINAL.md`, `source/docs/FINAL_STATUS_AND_OPEN_ITEMS.md`, `source/docs/windows-final-runbook.md`, `source/docs/releasing.md`. Die beiden AGENTS-Dateien und das Windows-Runbook sind **gemeinsam** verbindlich. Bei älteren Konflikten gelten die expliziten synchronisierenden Nutzerregeln: neuer geprüfter Remote-Code ist Basis; nur tatsächlich einzigartige lokale Verbesserungen werden integriert.

**Wichtiges Statuswissen:** Die Vision ist eine Zielvorgabe; das Evidenzregister listet nur Stand der GitHub-Sichtung. Insbesondere Sprachlabor/Antwortlabor sind **nicht** als auf `master` vollständig umgesetzt oder real auf Windows getestet zu betrachten.

## Phase 1: Echten lokalen Checkout finalisieren – autonom
Den bereits benutzten Windows-Repositoryordner auffinden; dort `git status`, `git log`, `git remote -v`, `git fetch origin`. Keine bloße Arbeit in einem temporären Klon. Vor dem Abgleich veraltete, lokale-only, ignored und untracked Dateien/Commits einschließlich vorhandener Staging-Versuche sichern und **semantisch** vergleichen. Nutze `source/scripts/sync_final_workspace.py` gemäß AGENTS; prüfe dessen Tests. Veraltetes lokales Code-Verhalten entfernen, echte unabhängige Verbesserungen mit den neueren Fixes verbinden. Unbedingt behalten: `%LOCALAPPDATA%\Backchannel`, DPAPI-Keys, Session-DB, Transkripte, Audio, AppData-KI-Konfiguration, persönliche Profile/Playbooks, installierte Ollama-Modelle, Browserprofile. Kein blindes `git reset --hard`, `git clean -fdx`, Stash-Apply oder Force-Push.

## Phase 2: Bestehende Testlabore finden und fertig integrieren
Prüfe, ob im lokalen Checkout/Staging bereits `calibration.html`, `CalibrationApp`, `clipRecorder.mjs`, `snapshotPolling.mjs` oder vergleichbare Labor-UI/Tests vorhanden sind. Ein uncommittetes Git-Tree-Objekt ist keine Integration. Bei vorhandener besserer Lösung: integrieren und mit echten Tests belegen; sonst zielgerichtet nach Produktvision implementieren.

**Sprachlabor:** deutscher Referenzsatz, echtes Mikrofon oder identischer Datei-Import, dieselbe Aufnahme gegen verfügbare ASR-Modelle, angezeigte Transkripte, WER + falsch/fehlend/zusätzlich erkannte Wörter, RTF und Latenz, Laufzeit-/Kosten-/Datenschutzhinweise, realistische Leer-/Fehler-/Offlinezustände. Sichere Größen-/Dauerlimits, asynchrone Decodierung, Testisolierung von aktiver Debatte. Cloudmodelle nur nach explizitem Opt-in und Kostenhinweis. Keine heimliche Speicherung.

**Antwortlabor:** gleiche These/Position/Stil/Prompt-Eingabe für zwei echte Provider oder Promptvarianten; verdeckte Modellnamen bis zum Nutzerurteil, A/B-Seiten zufällig aber reproduzierbar, Antwort-/Gegenfrage-/Latenzmetriken, Bewertungsfelder, Reveal, sicherer lokaler Export und Vorschlag einer Konfiguration ohne Auto-Apply. Bei laufender Debatte Hintergrundtests schonend planen/verschieben. Bestehende Provider-Routen und Privacy-/PII-Schutz benutzen, keine parallelen ungeschützten HTTP-Aufrufe.

**Overlay/Recorder:** alte Snapshotkarte bei Verbindungsfehler sichtbar und als veraltet markiert; nur eine Pollinganfrage in flight; keine Timer im Hidden-Tab; Recorder-Start-/Stop-/Permission-/Unmount-Races; Fehler und Recovery sichtbar.

## Phase 3: Testen vor und nach Fixes
TDD mit nachweislich rotem und danach grünem Regressionstest je Fehler; Ursache statt kosmetische Symptome beheben. Alle relevanten bestehenden Tests ausführen:
- `cd source/frontend; npm ci; npm test; npm run build`
- `cd source/backend; python -m unittest discover -s tests`
- `cd source/desktop; python -m unittest discover -s tests`
- relevante Sentrux-/Strukturgates gemäß `source/AGENTS.md`
- reale Browser-Interaktion samt responsivem Layout, Tastatur/Screenreader; ASR- und A/B-Test mit echten (nicht erfundenen) Modellantworten.

Testfälle: deutsche Eigennamen/Zahlen, Satzkorrektur, Stille/kurzer Clip, fehlendes Gerät, Mikrofon verweigert, Aufnahmewechsel, großer Datei-Upload, Offline, Cloud ohne Login, fehlerhafte JSON-Modellantwort, Revisionen, schnelle Folgeturns, Provider-Timeout, zwei parallel gestartete Benchmarks, Beenden während Aufnahme, wiederholter Einstieg. Jede fehlgeschlagene Prüfung mit Log/Fix/Retest belegen, nicht verschweigen.

## Phase 4: Windows vollständig bauen, installieren und nachweisen
Erst aus dem synchronisierten, getesteten Checkout `source/scripts/build_debate_assistant.ps1 -IncludeOracle` mit installiertem Python 3.12 und Node 24 nach **aktueller** Runbook-Syntax starten. Gewünschtes Ziel `source/dist/Backchannel-DebateAI-windows-x64.zip`. Prüfe Bridge-/Oracle-/ffmpeg-/ONNX-/PostgreSQL-/Updater-Bundle sowie Archiv-Smokes. Erstelle SHA256-Nachweis. Bewahre Benutzer-AppData; nutze Backup/Staging/Rollback statt blindem Löschen des installierten Ordners. Starte die neue EXE, belege exe-Pfad und tatsächlich laufende Version. Teste Windows-Mikrofon, Systemaudio, Transkript, Qwen-Ollama, Overlay, Sprachlabor und Antwortlabor. Kontologins nur sichtbar/interaktiv, keine Secrets auslesen. Kein vorgetäuschtes Authenticode ohne Zertifikat.

## Phase 5: Finaler GitHub-/Installationsabgleich
Falls Codeänderungen nötig waren, einzeln testen und sauber committen. GitHub-Abgleich ohne Force-Push; nach möglichem Remote-Fortschritt erneut mergen. Nachweis: `git rev-parse HEAD` und `git rev-parse origin/master` stimmen überein; der Build stammt exakt aus diesem Stand. Die installierte EXE ist damit nicht nur zufällig eine alte, parallel liegende Kopie. Nur echte Blockaden (Hardware, Zertifikat, interaktiver Login, Netz/Infrastruktur) als offen stehen lassen.

## Abschlussausgabe – nur Fakten
**Ein** Abschlussbericht mit Pfad des bestehenden Windows-Checkouts, finaler Remote-/Local-SHA, integrierten vs. verworfenen Änderungen, testbaren Laborfunktionen, Testmatrix (Befehl/Anzahl/Ergebnis), SHA256 des ZIP, gestarteter EXE-Pfad, tatsächlich geprüften Providern, erhaltenen Daten, echten offenen Blockern. Kein pauschales 'alles perfekt' ohne Messung.

**Arbeitsprinzip:** Arbeite möglichst selbstständig; frage nur bei irreversiblen, externen oder sicherheitsrelevanten Aktionen. Vorhandene Funktionen nicht neu erfinden; erweitern, messen, stabilisieren. Nicht beim Dokumentieren, bloßen Pullen oder ZIP-Erzeugen stoppen.
