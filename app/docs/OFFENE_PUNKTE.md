# DebateAI – Offene Punkte

Stand: 2026-11-21. Diese Datei enthält nur Punkte, für die der aktuelle Tree oder ein erreichbarer Nachweis noch keinen vollständigen Abschluss belegt. Erledigte und veraltete Einträge wurden in dieser Fortschreibung entfernt; historische Belege und alte Zielstände bleiben in [HISTORIE.md](HISTORIE.md).

**Aktueller geprüfter Code-/CI-Stand:** Der direkt von `main` geklonte und geprüfte Stand ist `68b783d6124cb09157a5c72696ff66f8582652d0` (GitHub-Branch-Readback nach dem Modus-Commit). Für die bisher umgesetzten Pakete bestanden der gezielte Backend-Vertragstest (2/2), der gezielte Antwort-UI-Abnahmetest (19/19), der gezielte Modus-UI-Abnahmetest (4/4), die Frontend-Gesamtsuite (381/381), der bestehende Response-Vertrag (7/7), `npm run build`, der Docs-Site-Test/-Build und der Repository-Layout-Guard; der Frontend-Build meldet weiterhin nur die bekannte Vite-Chunk-Warnung. Der lokale `github_sync.py --pull --strict`-Nachweis ist wegen fehlender `gh`-Authentifizierung blockiert (`gh auth login`/`GH_TOKEN` erforderlich); der verbundene GitHub-Connector konnte Repository, `main` und SHA unabhängig lesen. Die öffentliche Quellenstrategie bleibt unverändert: Dieses Repository bleibt ein reproduzierbarer, secretsfreier Source-/Test-Stand; Produktfreigabe, Signierung und externe Hardware-/Provider-Gates bleiben getrennte externe Nachweise.

## Vision-Abdeckungsmatrix (Bestandsaufnahme 21.11.2026)

Die folgenden stabilen IDs ordnen jeden relevanten Visionsabschnitt mindestens einer prüfbaren Produktanforderung zu. `IMPLEMENTED_UNVERIFIED` bedeutet, dass Code und fokussierte Tests existieren, aber ein externer Hardware-, Provider-, Nutzungs- oder Release-Nachweis fehlt. `PARTIAL` bedeutet, dass der Code nur einen Teil des beobachtbaren Vertrags erfüllt.

| ID | Vision-Referenz | Status | Code-/Testbeleg und verbleibende Lücke |
| --- | --- | --- | --- |
| V-01 | §§ 1, 3, 6 Live-Kern, Dual-Track, Sprecherzuordnung | IMPLEMENTED_UNVERIFIED | `app/backend/app/ws/audio_handler.py`, `services/speaker_diarizer.py`, `services/transcription_runtime.py`; Tests `test_local_live_captioner.py`, `test_audio_echo.py`, `test_speaker_assignment.py`. Reale 120-s-WASAPI-/Gerätewechsel- und Langzeitwerte fehlen (P0.3/P2.3). |
| V-02 | §§ 2, 6 Deutsch-V1, lokale ASR und Privacy First | IMPLEMENTED_UNVERIFIED | `services/transcription_language.py`, `transcription_runtime.py`, `privacy.py`; Tests `test_transcription_language.py`, `test_pii_audio_policy.py`. Offline-/Hardware-SLA ist nicht belegt (P2.3). |
| V-03 | § 3 Argument-/Strategie-Agent und Kontext | IMPLEMENTED_UNVERIFIED | `services/agents/orchestrator.py`, `objection_handler.py`, `strategic_signals.py`; Tests `test_debate_copilot.py`, `test_agent_activity.py`, `test_argument_graph.py`. Deutscher Live-Nutzen ist nicht unabhängig bewertet. |
| V-04 | § 4 beste Antwort plus höchstens zwei Alternativen, Revision/Stale | IMPLEMENTED_UNVERIFIED | `normalize_standard_strategies()` erzeugt drei lineage-markierte Züge; `ActiveCall/DebateCoachPanel.tsx` zeigt eine Primärkarte und höchstens zwei sekundäre Züge. Neue Tests `test_standard_strategy_options.py` und `DebateCoachPanel.test.mjs`; echte Windows-/Nutzerbewertung bleibt offen. |
| V-05 | § 5 genau „Hart“/„Überzeugend“, Vorauswahl | IMPLEMENTED_UNVERIFIED | `DebateSettingsCard.tsx`, `services/debate_settings.py`, `NewSessionModal.tsx`; `test_debate_settings.py`, `DebateSettingsCard.test.mjs`, `NewSessionModal.test.mjs` (4/4). Der letzte der zwei Modi wird jetzt lokal für den nächsten Sitzungsdialog vorgemerkt; ein echter Windows-/Pre-Call-Lauf bleibt offen. |
| V-06 | §§ 2, 7 ChatGPT Web/Gemini Web und lokaler Erstpfad | IMPLEMENTED_UNVERIFIED | `routers/chatgpt_web.py`, `routers/gemini_web.py`, `services/debate_research.py`, Desktop-Bridges; Adapterverträge vorhanden. Authentifizierte Provider- und Ausfallabnahme fehlt (P0.3). |
| V-07 | § 7 „Jetzt recherchieren“, Stop/Replace/Priorisieren | PARTIAL | Voice-/UI-Befehl und Research-Lanes existieren, aber kein vollständiger nachgewiesener Cancel/Replace/Reuse-End-to-End-Vertrag ohne lokalen Pfadstopp. |
| V-08 | §§ 7, 20 adaptive Denkintensität/Providerwechsel | EXPERIMENTAL | `services/adaptive_reasoning.py` plus `test_adaptive_reasoning.py`; zuverlässige Web-Steuerbarkeit ist ausdrücklich noch zu prüfen. |
| V-09 | § 8 Sitzungsende: Speichern oder komplett ohne Speicherung | PARTIAL | Audio-/Transkript-Retention und lokaler Cleanup sind vorhanden (`test_audio_cleanup_preservation.py`, `test_audio_failure_preservation.py`), aber die zwei mutually-exclusive UI-Optionen und Provider-Delete-Abnahme fehlen (P1.14). |
| V-10 | § 9 Windows-Dashboard und Antwort-Hierarchie | IMPLEMENTED_UNVERIFIED | `App.tsx`, `DebateCoachPanel.tsx`, `useWebSocket.ts`; Frontend-Komponententests grün. WebView2/DPI/zweiter Monitor und reale Nutzbarkeit fehlen (P0.3). |
| V-11 | §§ 10–11 Onboarding, Modell-/Sprachvergleich | PARTIAL | Calibration-/Admin-Lab und `test_calibration_*` vorhanden; vollständiger blinder A/B-/WER/CER-/RTF-Nachweis fehlt (P1.10/P2.3). |
| V-12 | §§ 13–14 Audio-/Video-Labor und profilgebundene Optimierung | EXPERIMENTAL | `video_eval_*`, Calibration- und Optimierungsdienste vorhanden; Baseline→gezielte Änderung→Regression→Freigabe ist nicht vollständig nachgewiesen. |
| V-13 | § 15 vollständige Cloud-Testinstanz und automatische GitHub-Bugmeldung | MISSING/BLOCKED | Workflows decken CI ab, aber keine vollständige steuerbare Cloud-Instanz mit Replay/Optimierung/Issue-Pipeline ist belegt; Credentials/Operatorzugriff fehlen. |
| V-14 | § 12, § 15 WebSocket-Journale und Multiworker | IMPLEMENTED_UNVERIFIED (Single-Worker) / MISSING (Multiworker) | `services/ws_event_stream.py`, `transcription_jobs.py`, `useWebSocket.ts`; 25 Journal- und 3 Job-Tests laufen, aber State ist prozesslokal; Redis/DB-Adapter und Zwei-Worker-Test fehlen (P1.15/P2.12). |
| V-15 | § 16 Sicherheit, PII, Origin und Einwilligung | IMPLEMENTED_UNVERIFIED | Request-Guard-/PII-/Privacy-Tests und Instance-Token vorhanden. Reale LAN-/Reverse-Proxy-/DNS-Rebinding- und Provider-Delete-Abnahme fehlt (P1.16). |
| V-16 | §§ 19, 21 Windows-Distribution, Signierung, Rollback | PARTIAL/BLOCKED | Bundle-, Hash- und Rollback-Smokes sowie `desktop-release.yml` vorhanden; Authenticode, produktiver Download und frischer Client fehlen (P0.2/P1.4). |
| V-17 | §§ 17, 21 CI-/Structure-Gesamtgate | PARTIAL/BLOCKED | Tests/Security-Workflows vorhanden; Structure-Gesamtlauf bleibt wegen absoluter Sentrux-Schulden offen (P0.1). |
| V-18 | §§ 18, 20 Reproduzierbarer Build und externe Abnahme | IMPLEMENTED_UNVERIFIED/BLOCKED | Lockfiles, Layout-/Source-Guards und Buildpfade vorhanden; unabhängiger Clean-Checkout-Build mit Artefakt-/Lizenzhashes und Windows-/Provider-Abnahme fehlt (P2.2/P0.3). |

### V-04 – Antwort-Hierarchie und Alternativen

**Priorität:** P0
**Status:** IMPLEMENTED_UNVERIFIED
**Vision-Referenz:** § 4, ergänzt durch §§ 3, 9, 17

**1. Verbindliches Ziel**

Jeder aktuelle Standard-Live-Zug zeigt eine beste, direkt sprechbare Antwort und höchstens zwei nachgeordnete, strategisch verschiedene Alternativen. Jede Option bleibt an Sitzung, Claim, Transkript- und Empfehlungsrevision gebunden; veraltete Vorschläge dürfen nicht als aktuell erscheinen.

**2. Konkretes Nutzungsbeispiel**

Während eines deutschen Videocalls erzeugt der lokale Agent eine Sofortantwort, eine Gegenfrage und einen konkreten Gegenfall. Die UI hebt die Sofortantwort hervor und stellt die beiden anderen Züge aufklappbar bereit. Eine vierte Modelloption wird im Standard-Livepfad nicht angezeigt; eine spätere Revision ersetzt beziehungsweise markiert die alte Karte.

**3. Tatsächlicher Ist-Zustand**

- Backend: `app/backend/app/services/agents/objection_handler.py::normalize_standard_strategies` erzeugt drei lineage-markierte Optionen.
- Frontend: `app/frontend/src/components/ActiveCall/DebateCoachPanel.tsx` zeigt die Primärkarte und begrenzt Standard- sowie experimentelle Nebenoptionen auf zwei sichtbare Einträge.
- Tests: `app/backend/tests/test_standard_strategy_options.py` (2 Tests), `app/frontend/src/components/ActiveCall/DebateCoachPanel.test.mjs` (19 Tests inklusive 2-Alternativen-Fall).

**4. Genaue Abweichung**

Die Nachweise sind synthetische Backend-/SSR-Tests. Ein echter Windows-WebView-Nutzungstest, eine menschliche Bewertung von Strategieverschiedenheit und die vollständige Revision unter laufender Audio-/ASR-Korrektur bleiben offen.

**5. Unabhängige Abnahmetests**

- **Test A – funktionaler Backend-Vertrag:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_standard_strategy_options.py' -v`; prüft drei eindeutige, rangierte, claim-/transcript-revisionsgebundene Züge und sichere Fallbacks. **Bestanden: 2/2.**
- **Test B – kritische sichtbare UI-Prüfung:** `TMPDIR="$PWD/.tmp" node --test src/components/ActiveCall/DebateCoachPanel.test.mjs`; speist vier Optionen ein und prüft genau eine Primärkarte, genau zwei sichtbare Alternativen sowie das Ausblenden des vierten Zuges. **Bestanden: 19/19.**
- Zusätzlich: `npm run build` (TypeScript/Vite) **bestanden**. Windows/WebView2-/Human-Rating-Abnahme **nicht ausführbar**.

**6. Recherche vorhandener Lösungen**

Der vorhandene `normalize_standard_strategies`-Vertrag und `DebateCoachPanel` wurden erweitert; der experimentelle Vier-Züge-Pfad bleibt für Laborzwecke intern. Ein neues UI-Framework oder eine parallele Antwortarchitektur wäre unnötig.

**7. Exakter Umsetzungsplan**

1. Standardoptionen im bestehenden Panel nach der Primärkarte rendern.
2. Primärstrategie anhand `primary_move`/`selected_strategy_id` ausschließen und sichtbare Nebenoptionen auf zwei begrenzen.
3. Experimentelle Vier-Züge-Daten unverändert als Backend-/Laborartefakt erhalten, aber den Live-View ebenfalls begrenzen.
4. Backend- und SSR-Abnahmetests ausführen; anschließend Frontend-Build und relevante Regressionen prüfen.

**8. Erfüllungskriterien**

- [x] Eine Primärkarte wird visuell priorisiert.
- [x] Höchstens zwei Alternativen sind im Live-View sichtbar.
- [x] Alternativen unterscheiden sich nach `kind`/Text und werden nicht als bloße Duplikate erzeugt.
- [x] Claim-/Transkript-/Generationsbezug bleibt erhalten.
- [x] Backend-Test A und UI-Test B bestehen.
- [ ] Echte Windows-/WebView2-/Human-Rating-Abnahme besteht.

**9. Implementierungsnachweise**

- Änderungen: `DebateCoachPanel.tsx`, `DebateCoachPanel.test.mjs`, `test_standard_strategy_options.py`.
- Commit-SHA: `9b3901e4f94a25db7fc3bbd42e323de9046411f0` (GitHub `main`, verifiziert über Branch- und Commit-Readback).
- Ausgeführt: Backend 2/2, Frontend 19/19, `npm run build` grün.
- Einschränkung: Der lokale `github_sync.py`-Pull ist mangels `gh`-Auth nicht ausführbar; der GitHub-Connector bleibt der externe SHA-Nachweis.

**10. Codex-Desktop-Handoff bei Blockern**

Auf einem autorisierten Windows-Gerät `npm test`, den installierten WebView2-Desktop-Smoke und einen manuellen deutschen Debattenlauf mit mindestens einer ASR-Revision ausführen. Prüfen: Primärkarte bleibt vorne, maximal zwei Alternativen, veraltete Karte wird ersetzt/markiert, keine vierte Option im Standard-Livepfad. Ergebnis mit Commit-SHA und Bildschirm-/Event-Evidenz in diesem Punkt ergänzen.

### V-05 – Debattenmodus im nächsten Sitzungsdialog vorwählen

**Priorität:** P1
**Status:** IMPLEMENTED_UNVERIFIED
**Vision-Referenz:** § 5, ergänzt durch §§ 7–8

**1. Verbindliches Ziel**

Der Nutzer wählt zwischen genau den zwei vorgesehenen Rhetorikmodi „Überzeugend“ und „Hart / brutal-sachlich“. Der zuletzt gewählte Debattenmodus wird beim nächsten Öffnen des Sitzungsdialogs wieder vorausgewählt; ungültige oder fremde gespeicherte Werte fallen sicher auf „Überzeugend“ zurück. Die bestehende Admin-Einstellung bleibt davon getrennt und wird nicht durch einen stillen dritten Modus ergänzt.

**2. Konkretes Nutzungsbeispiel**

Der Nutzer öffnet „Neue Sitzung“, wählt „Hart / brutal-sachlich“ und erstellt die Debatte. Beim nächsten Öffnen stehen weiterhin beide Modi bereit und „Hart / brutal-sachlich“ ist bereits markiert. Ist der Browser-Speicher beschädigt oder enthält er etwa `client_sales`, erscheint wieder „Überzeugend“ und die Sitzung kann trotzdem erstellt werden.

**3. Tatsächlicher Ist-Zustand**

- `app/frontend/src/components/NewSessionModal.tsx` verwendet den bestehenden Modus-Selector, liest den Schlüssel `debateai:last-debate-mode` beim Initialisieren und bei jedem Öffnen und speichert nur `debate_persuasive` beziehungsweise `debate_forceful`.
- `app/frontend/src/components/DebateSettingsCard.tsx` und `app/backend/app/services/debate_settings.py` bleiben die bestehende Admin-/Persistenzschnittstelle für die globale Konfiguration.
- `app/frontend/src/components/NewSessionModal.test.mjs` enthält zwei unabhängige UI-Verhaltensfälle: Wiederherstellung des gewählten Modus sowie sichere Rückkehr zum Standard bei ungültigem Speicherwert.

**4. Genaue Abweichung**

Die lokale Browserpersistenz und SSR-Vertragsprüfung sind implementiert. Ein realer Windows-WebView-/Pre-Call-Durchgang mit Sitzungserstellung und anschließendem erneutem Öffnen ist in dieser Umgebung nicht ausführbar; deshalb bleibt das Ziel `IMPLEMENTED_UNVERIFIED`.

**5. Unabhängige Abnahmetests**

- **Test A – funktionale Wiederherstellung:** `TMPDIR="$PWD/.tmp" node --test src/components/NewSessionModal.test.mjs`; setzt den Speicherwert `debate_forceful`, rendert den Dialog und prüft, dass „Hart / brutal-sachlich“ aktiv und „Überzeugend“ inaktiv ist. **Bestanden: 1/1 Fall.**
- **Test B – kritischer Fallback:** derselbe Testlauf setzt `client_sales` als fremden Wert und prüft, dass `readLastDebateMode()` exakt `debate_persuasive` liefert. **Bestanden: 1/1 Fall.**
- Zusätzlich: vollständige Frontend-Suite **381/381** und `npm run build` **bestanden**. Windows-WebView-/manuelle Pre-Call-Abnahme **nicht ausführbar**.

**6. Recherche vorhandener Lösungen**

Der vorhandene `NewSessionModal`-Selector und die Browser-Storage-Muster der Frontend-Komponenten wurden wiederverwendet. Ein neues Zustandsframework oder eine zweite Modusverwaltung wäre unnötig; eine kleine, fail-safe Helper-Funktion schützt den Dialog vor Storage-/Privatmodusfehlern.

**7. Exakter Umsetzungsplan**

1. `NewSessionModal.tsx` um einen typisierten Schlüssel und einen sicheren Reader für die zwei erlaubten Debattenmodi ergänzen.
2. Beim Öffnen und beim Umschalten den gespeicherten Wert lesen beziehungsweise aktualisieren; Fehler im Browser-Speicher dürfen die Sitzungserstellung nicht blockieren.
3. `NewSessionModal.test.mjs` um einen Positiv- und einen ungültigen-Wert-Fall ergänzen.
4. Zieltest, Frontend-Gesamtsuite und Produktionsbuild ausführen; den Status erst nach dem realen Desktop-Durchgang auf `VERIFIED` heben.

**8. Erfüllungskriterien**

- [x] Genau die zwei vorgesehenen Debattenmodi bleiben erreichbar.
- [x] Der letzte gültige Modus wird beim nächsten Öffnen vorausgewählt.
- [x] Fremde oder beschädigte Speicherwerte erzeugen keinen ungültigen Sitzungsmodus.
- [x] Ein Storage-Fehler verhindert die Sitzungserstellung nicht.
- [x] Test A und Test B prüfen beobachtbares Dialogverhalten und bestehen.
- [x] Frontend-Regressionen und Produktionsbuild bestehen.
- [ ] Echter Windows-/WebView-/Pre-Call-Durchgang mit anschließender Sitzungserstellung besteht.

**9. Implementierungsnachweise**

- Änderungen: `app/frontend/src/components/NewSessionModal.tsx`, `app/frontend/src/components/NewSessionModal.test.mjs`.
- Commit-SHA: `68b783d6124cb09157a5c72696ff66f8582652d0` (GitHub `main`, Branch-Readback verifiziert).
- Ausgeführt: Zieltest 4/4, Frontend 381/381, Vite/TypeScript-Build grün.
- Einschränkung: GitHub-CLI-Synchronisation und realer Windows-/WebView-Lauf bleiben mangels Authentifizierung beziehungsweise Hardware offen.

**10. Codex-Desktop-Handoff bei Blockern**

Auf einem autorisierten Windows-Gerät den Desktop-Build starten, „Neue Sitzung“ öffnen, beide Modi nacheinander wählen, Sitzungen erstellen, den Dialog erneut öffnen und die Vorauswahl sowie den tatsächlich an den Backend-Create-Request übergebenen `meeting_type` prüfen. Zusätzlich einen blockierten/privaten Browser-Speicher simulieren; erwartetes Ergebnis ist weiterhin ein erstellbarer Dialog mit „Überzeugend“ als Standard.

## P0 – vor einer belastbaren Produkt- oder Releasefreigabe

### P0.1 GitHub-Actions-Gesamtgate

- **Status:** teilweise nachgewiesen; für `9c384608` sind Tests und Security grün, der Structure-Gesamtlauf bleibt wegen absoluter, geerbter Sentrux-Schulden rot.
- **Offen:** Die verbleibenden absoluten Findings entweder im Code abbauen oder als bewusst akzeptierte Qualitätsverschuldung mit Owner und Termin entscheiden.
- **Fertigstellungsnachweis:** grüner Structure-Gesamtlauf ohne absolute Findings oder eine datierte, verantwortete Ausnahmeentscheidung; Tests/Security müssen weiterhin auf exakt demselben SHA grün sein.
- **Quelle:** Runs `44683868125`, `44683868162`, `44683868692`; Sentrux-Job `136113438257`.

### P0.2 Signiertes produktives Windows-Release

- **Status:** extern offen. Bundle-, Hash- und Rollback-Smokes sind vorhanden; Authenticode, Zertifikatskette, Operatorfreigabe, R2/Access/DNS und produktiver Download sind nicht belegt.
- **Benötigt:** Zertifikat oder autorisierter Remote-Signing-Prozess, Hold-Commit, Release-Manifest und ein frischer Windows-Client mit Update/Restart/Rollback-Nachweis.
- **Blocker/Owner:** Operator-/Release-Owner; im aktuellen Chat sind weder Zertifikat noch Produktionszugriff autorisiert.

### P0.3 Reale Windows-/Audio-/GUI-/Provider-Abnahme

- **Status:** teilweise nachgewiesen. Der installierte Windows-Build, WebView-Start, Backend-Health, ChatGPT-Web/Gemini-Web-Anmeldestatus, CUDA-Sortformer und ein echter GPU-Benchmark sind geprüft. Ein echter 120+-Sekunden-Mikrofon-/WASAPI-/Loopback-Lauf, Gerätewechsel, WebView2/DPI sowie eine kostenrelevante Provider-Abnahme bleiben extern offen.
- **Benötigt:** frisches Windows-Gerät, reale Audiohardware, autorisierte Providerkonten und Rohmetriken für ASR, Latenz, CPU/RAM sowie Bildschirm-/Event-Evidenz.
- **Blocker/Owner:** Operator-/Hardware-Owner; keine ungeprüften Logins oder Kostenaktionen auslösen.

## P1 – vor einer vollständigen Funktions- und Qualitätsaussage

### P1.4 Release-/Update-Cutover

- **Status:** extern offen. Runbook und isolierte Smokes sind versioniert; ein produktiver Hold-Commit mit Manifest, Signatur, Download, Update und getrenntem Binary-/Daten-Rollback fehlt.
- **Benötigt:** Operator-kontrollierte Probeveröffentlichung auf einem frischen Client; Nachweise müssen auf denselben Release-SHA und dieselben Artefakt-Hashes zeigen.

### P1.5 Distributable-Site-/Asset-Gate

- **Status:** Claim-Matrix, Privacy-/Locality-Texte und die aktive Linkprüfung sind im Code abgeglichen. Offen bleibt nur der distributable Snapshot: jeder aktive Link und jedes Asset muss im veröffentlichten Paket vorhanden sein oder aus den Seiten entfernt werden.
- **Benötigt:** frischer Site-Asset-Scan, Docs-Site-Test/Build und ein veröffentlichter oder ausdrücklich als nicht-produktiv markierter Snapshot.

### P1.10 A/B- und Sprachlabor als zugängliches Produktfeature

- **Status:** im Hauptprodukt jetzt über Admin → Labor und den Onboarding-Schnelltest erreichbar; der vollständige Qualitätsnachweis bleibt offen.
- **Benötigt:** zugänglicher, blinder A/B-Vergleich mit Reveal und Export, unabhängige Datensätze, WER/CER/RTF sowie Rater-Übereinstimmung; das eingebettete Transkriptionslabor und die Quality-/Video-Labs allein erfüllen diesen Produktvertrag nicht.

### P1.14 Löschpfad für externe, lokale und Browser-Artefakte

- **Status:** lokaler, Browser- und Prozess-Cleanup sowie idempotente Retry-Outbox sind implementiert. Offen bleibt die echte Provider-/Operator-Abnahme.
- **Benötigt:** autorisierter Provider-Test mit absichtlich fehlschlagender Löschung, Retry-/Backoff-Logs, bestätigtem finalem Delete und Prüfung, dass kein zulässiges Reconnect-Replay verloren geht.

### P1.15 Live-State und WebSocket-Journale für Multiworker-Betrieb

- **Status:** offizielle Startpfade erzwingen einen Worker; Journale und Stale-Guards sind begrenzt. Ein gemeinsamer Redis-/DB-State-Adapter und ein Zwei-Worker-Produktionsnachweis fehlen.
- **Benötigt:** autorisierte Multiworker-Umgebung mit gemeinsamem State, Reconnect-/Replay-Test und Nachweis ohne doppelte Persistierung.

### P1.16 LAN-Origin-Vertrauen und Bind-Defaults

- **Status:** Loopback-/Reload-Defaults, Origin-/Host-Allowlist und Instance-Token sind durch Request-Guard-Tests abgesichert. Offen bleibt die vollständige Bedrohungsprüfung auf einem realen LAN mit Reverse Proxy und DNS-Rebinding-Szenarien.
- **Benötigt:** autorisierter LAN-/Proxy-Test mit aufgezeichneten erlaubten und blockierten Origin-, Host-, WebSocket- und Mutation-Fällen.

## P2 – technische Schulden und belastbare Messung

### P2.1 Ruff-/Duplikat-Schulden

- **Status:** F-Fehler und vulture sind bereinigt; breite Style-/jscpd-Last bleibt.
- **Benötigt:** priorisierte, produktionskritische Triage mit begründeten Ausnahmen, ohne ungezielte Massenformatierung während Releasearbeit.

### P2.2 Reproduzierbarkeit des vollständigen Builds

- **Status:** private historische Evidenz ist vorhanden; eine unabhängige Wiederholung aus sauberem Checkout mit Toolchain-, Lockfile-, Lizenz- und Artefakt-Hashes fehlt.
- **Benötigt:** sauberer Linux-/Windows-Checkout und eine versionierte Build-Matrix. Der aktuelle Windows-Desktop-Clone ist für Code-/CI-Tests vorhanden, aber noch kein frischer Release-Build.

### P2.3 ASR-/Latenz-/Rhetorikmessung auf Zielhardware

- **Status:** Labor-/synthetische Messungen sind vorhanden; reale Streaming-, Dual-Track-, Sprecherfehler-, Tail-Latency- und Langzeitsitzungsdaten fehlen.
- **Benötigt:** referenzierte deutsche Audiofälle, WASAPI-Mikrofon/Loopback, WER/CER, first-speakable/final latency, RTF, CPU/RAM, Modell-/Prompt-Hashes und Wiederholungsangaben.

### P2.10 Listen-, Transcript- und Knowledge-APIs

- **Status:** kompatible Array-Limits, stabile Tie-Breaker und Composite-Indizes sind vorhanden. Echte Cursor-Fortsetzung, UI-Seitenabruf und vollständige SQL-seitige Chat-Priorisierung bleiben offen.
- **Benötigt:** versionskompatibler Cursorvertrag für alle betroffenen Endpunkte, UI-Weiterblättern, Cursor-Regressionen und ein begrenzter Lastnachweis.

### P2.11 Parallele Migrationsstarts

- **Status:** PostgreSQL-Advisory-Lock, isolierter Paralleltest und die aktuelle Migrations-Regression sind grün. Offen bleiben die vollständige Failure-/Retry-Matrix und die Legacy-Datenbankmatrix.
- **Benötigt:** reproduzierbarer Failure-/Retry-Test mit realem Datenbankrunner, frische und Legacy-Schemata, exakt ein Alembic-Head und sichtbarer Fehlerstatus ohne halb angewendetes Schema.

### P2.12 Prozessweite Journale und PII-Scrub-Indizes

- **Status:** TTL/LRU, Byte-/Registry-Limits, sessionweises Cleanup und terminale Job-TTL sind implementiert und regressionsgetestet. Ein 10.000-Session-Langzeittest und produktiver Multiworker-Replay-Nachweis fehlen.
- **Benötigt:** definierte RAM-/Indexbudgets, synthetischer 10.000-Session-Lauf, Reconnect-Replay-Prüfung und ein autorisierter Multiworker-Nachweis.

## P3 – Inventar und externe Zuständigkeiten

### P3.2 Repository-/Projekt-Inventar

- **Status:** öffentliche Refs, Open-PRs, Issues, Releases und Actions sind für den aktuellen Connectorzugriff geprüft; Open-PRs/Issues/Releases sind leer. Branch-Protection/Rulesets und private Projects/Tags sind über die aktuelle Integration nicht vollständig lesbar (403 bzw. nicht unterstützte API).
- **Benötigt:** authentifizierter Export der fehlenden privaten Inventare mit Zeitpunkt, Cursor/Seitenzahl und Abgleich gegen lokale Refs.
