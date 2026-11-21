# DebateAI – Offene Punkte

Stand: 2026-11-21. Diese Datei enthält nur Punkte, für die der aktuelle Tree oder ein erreichbarer Nachweis noch keinen vollständigen Abschluss belegt. Erledigte und veraltete Einträge wurden in dieser Fortschreibung entfernt; historische Belege und alte Zielstände bleiben in [HISTORIE.md](HISTORIE.md).

**Aktueller geprüfter Code-/CI-Stand:** Der direkt von `main` geklonte und geprüfte Stand ist `6aa9be935cfdd90c57d64e2f3be1fcee8286a096` (GitHub-Branch-Readback nach Backend-/Frontend-P2.10 und Migrations-Cleanup). Für die bisher umgesetzten Pakete bestanden der gezielte Backend-Vertragstest (2/2), der erweiterte Cursor-Abnahmetest (3/3), der gezielte Antwort-UI-Abnahmetest (19/19), der gezielte Modus-UI-Abnahmetest (4/4), die Frontend-API-Abnahme (10/10), die Frontend-Gesamtsuite (384/384), der bestehende Response-Vertrag (7/7), der Audio-Handler-Vertrag (63/63), der ActiveCall-Abnahmetest (21/21), der Kern-Cursor-Vertrag (5/5), der Session-Router-Test (4/4), der Knowledge-Mutationsschutz (41/41), der Migrations-Lock-/Retry-Lauf (2/2), der Alembic-Transaktionslauf (2/2), der Startup-/Legacy-Pfadtest (20 Tests, 1 Windows-Skip), der echte SQLite-Migrationsmatrixlauf (3/3), `npm run build`, der Docs-Site-Test/-Build und der Repository-Layout-Guard. Der Frontend-Build meldet weiterhin nur die bekannte Vite-Chunk-Warnung. Der lokale `github_sync.py --pull --strict`-Nachweis ist wegen fehlender `gh`-Authentifizierung blockiert (`gh auth login`/`GH_TOKEN` erforderlich); der verbundene GitHub-Connector konnte Repository, `main` und die neuen SHAs unabhängig lesen. Die öffentliche Quellenstrategie bleibt unverändert: Dieses Repository bleibt ein reproduzierbarer, secretsfreier Source-/Test-Stand; Produktfreigabe, Signierung und externe Hardware-/Provider-Gates bleiben getrennte externe Nachweise.

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
| V-09 | § 8 Sitzungsende: Speichern oder komplett ohne Speicherung | PARTIAL | Vollständiger Abschluss, analyseloser Abschluss und der neue explizite No-Retention-Pfad verwenden `ActiveCallView`, `audio_handler._requested_drain_mode` und den bestehenden `DELETE /api/sessions/{id}`-Cleanup. Backend-/UI-Verträge laufen; Provider-Delete- und reale End-to-End-Abnahme fehlen (P1.14). |
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
- Zusätzlich: vollständige Frontend-Suite **384/384** und `npm run build` **bestanden**. Windows-WebView-/manuelle Pre-Call-Abnahme **nicht ausführbar**.

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
- Ausgeführt: Zieltest 4/4, Frontend 384/384, Vite/TypeScript-Build grün.
- Einschränkung: GitHub-CLI-Synchronisation und realer Windows-/WebView-Lauf bleiben mangels Authentifizierung beziehungsweise Hardware offen.

**10. Codex-Desktop-Handoff bei Blockern**

Auf einem autorisierten Windows-Gerät den Desktop-Build starten, „Neue Sitzung“ öffnen, beide Modi nacheinander wählen, Sitzungen erstellen, den Dialog erneut öffnen und die Vorauswahl sowie den tatsächlich an den Backend-Create-Request übergebenen `meeting_type` prüfen. Zusätzlich einen blockierten/privaten Browser-Speicher simulieren; erwartetes Ergebnis ist weiterhin ein erstellbarer Dialog mit „Überzeugend“ als Standard.

### V-09 – Sitzungsende mit Speicherung oder vollständigem No-Retention-Pfad

**Priorität:** P0
**Status:** PARTIAL
**Vision-Referenz:** § 8, ergänzt durch §§ 16 und 17

**1. Verbindliches Ziel**

Der Nutzer kann einen normalen Abschluss mit dauerhaftem Transkript und optionaler Aufnahme wählen oder ausdrücklich „Komplett ohne Speicherung/Verbesserung“ fortfahren. Diese zweite Wahl muss die normale Aufbewahrung für genau diese Sitzung überstimmen: Nach dem Abschluss dürfen deren Transkript, Aufnahme, Argumentextrakte, Sitzungs-Token und lokale Chat-/Optimierungsartefakte nicht als Sitzung zurückbleiben. Die bestehende, vollständige Löschroutine muss auch lokale Audiodateien und zugängliche Provider-Dateien abarbeiten.

**2. Konkretes Nutzungsbeispiel**

Während einer aktiven Sitzung öffnet der Nutzer das Ende-Menü und wählt „Komplett ohne Speicherung/Verbesserung“. Der Backend-Socket führt nur den notwendigen minimalen Abschluss ohne späte Analyse aus. Erst wenn der Abschluss bestätigt ist, löscht der Client die Sitzung über `DELETE /api/sessions/{id}`; danach verschwindet sie aus der Sitzungsliste. Bei einem langsamen oder nicht bestätigten Abschluss bleibt die Löschung aus und der Nutzer erhält keinen falschen Erfolgsstatus.

**3. Tatsächlicher Ist-Zustand**

- `app/frontend/src/components/ActiveCall/ActiveCallView.tsx` bietet weiterhin den normalen vollständigen Abschluss, „Ohne Auswertung beenden“ (Transkript bleibt) und jetzt zusätzlich die klar bezeichnete No-Retention-Aktion mit `onEndCall("minimal")`.
- `app/backend/app/ws/audio_handler.py` akzeptiert `minimal` nun ausdrücklich als absichtlichen Stop-Modus. Der vorhandene Minimalpfad stoppt Analyse-Tasks, leert die Transkriptionswarteschlange und markiert die Sitzung erst danach abgeschlossen.
- `app/frontend/src/App.tsx` wartet bei `minimal` auf die Abschlussbestätigung und ruft anschließend die bestehende Löschroutine auf. Diese löscht über Kaskaden die Sitzungsdaten, räumt den Audio-Unterordner, vergisst lokale Journale/PII-Sitzungszustände und fordert Provider-Dateilöschungen für gespeicherte Dokumente an.
- Unabhängige Nachweise: `test_audio_handler.py` prüft die akzeptierte `minimal`-Anforderung und den analyselosen Finalisierungspfad; `ActiveCallView.test.mjs` prüft die drei getrennten Aktionen und die sichtbare No-Retention-Beschriftung.

**4. Genaue Abweichung**

Der lokale Codepfad und die Vertragsprüfungen sind vorhanden. Es fehlt der echte Windows-/WebView-/Provider-Durchlauf mit einer realen Sitzung sowie eine autorisierte Provider-Abnahme für absichtlich fehlschlagende und erfolgreich wiederholte Löschungen. Deshalb bleibt das Ziel `PARTIAL`.

**5. Unabhängige Abnahmetests**

- **Test A – Backend-Funktion und Grenzfall:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_audio_handler.py' -v`; prüft, dass nur der explizite `minimal`-Stop angenommen wird, unbekannte Werte weiter sicher auf `full` fallen und der Minimal-Finalizer keine Analyse-Drain-Stufen startet. **Bestanden: relevante Audio-Handler-Suite 63/63.**
- **Test B – kritische UI-Prüfung:** `TMPDIR="$PWD/.tmp" node --test src/components/ActiveCall/ActiveCallView.test.mjs`; prüft getrennte Full-/Skip-/Minimal-Aktionen sowie die sichtbare Erklärung, dass Transkript, Aufnahme und Sitzungsdaten gelöscht werden. **Bestanden: 21/21.**
- Zusätzlich: Frontend-Gesamtsuite **384/384**, `npm run build` und Repository-Layout-Guard **bestanden**. Reale Provider-/Windows-/Audio-Abnahme **nicht ausführbar**.

**6. Recherche vorhandener Lösungen**

Der vorhandene `minimal`-Finalizer und die bestehende `DELETE /api/sessions/{id}`-Routine decken bereits Prozess-, Datenbank-, Audio- und Provider-Cleanup ab. Diese Pfade werden wiederverwendet; ein paralleler „ephemeral session“-Speicher oder eine zweite Löschlogik würde widersprüchliche Datenschutzgarantien erzeugen.

**7. Exakter Umsetzungsplan**

1. `audio_handler._STOP_DRAIN_MODES` und `_requested_drain_mode` um den ausdrücklich angeforderten `minimal`-Stop erweitern.
2. `StopDrainMode`, `ActiveCallView` und `App.handleEndCall` so verbinden, dass die No-Retention-Wahl sichtbar ist und erst nach bestätigtem Abschluss löscht.
3. Bei ausbleibender Bestätigung über den vorhandenen Poll-/Timeout-Pfad die Löschung auslassen und den Zustand als nicht bestätigt anzeigen.
4. Backend- und UI-Abnahmen sowie Frontend-Regressionen ausführen; anschließend Windows-/Provider-Nachweise ergänzen.

**8. Erfüllungskriterien**

- [x] Normaler Abschluss und No-Retention-Abschluss sind sichtbar und eindeutig beschriftet.
- [x] Der No-Retention-Weg fordert `minimal` an und startet keine späten Analyse-Stufen.
- [x] Die Sitzung wird erst nach bestätigtem Abschluss über den vorhandenen Cleanup gelöscht.
- [x] Bei fehlender Bestätigung wird nicht voreilig gelöscht.
- [x] Backend-Test A und UI-Test B bestehen.
- [x] Frontend-Gesamtsuite, Produktionsbuild und Layout-Guard bestehen.
- [ ] Echte Sitzung auf Windows/WebView2 mit Audio und anschließender lokaler/Provider-Löschbestätigung besteht.

**9. Implementierungsnachweise**

- Änderungen: `app/backend/app/ws/audio_handler.py`, `app/backend/tests/test_audio_handler.py`, `app/frontend/src/types/index.ts`, `app/frontend/src/components/ActiveCall/ActiveCallView.tsx`, `app/frontend/src/components/ActiveCall/ActiveCallView.test.mjs`, `app/frontend/src/App.tsx`.
- Commit-SHA: `7a149b0b60261dace3cb4cd0376b6751c6faa9ff` (GitHub `main`, Branch-Readback verifiziert).
- Ausgeführt: Audio-Handler 63/63, ActiveCallView 21/21, Frontend 384/384, Vite/TypeScript-Build grün, Layout-Guard grün.
- Einschränkung: Provider-Delete bleibt extern; der lokale `gh`-Pull ist weiterhin wegen fehlender CLI-Authentifizierung blockiert.

**10. Codex-Desktop-Handoff bei Blockern**

Auf einem autorisierten Windows-Gerät eine kurze echte Sitzung starten, einmal den normalen Abschluss und einmal die No-Retention-Option durchführen. Vorher/nachher prüfen: `GET /api/sessions`, Audio-Unterordner unter `DATA_DIR/audio/{session_id}`, Transkript-/Question-/Synthesis-/Token-Zeilen und Browser-Chat-Key. Für Provider-Dokumente die Provider-Konsole beziehungsweise autorisierte Delete-API prüfen; einen absichtlichen Fehlerfall einmal wiederholen und Retry-/Backoff-Nachweis dokumentieren.

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

- **Status:** PARTIAL. Die Kernlisten `GET /api/sessions`, `/api/sessions/{id}/segments` und `/api/sessions/{id}/transcripts` sowie jetzt Fragen, Direktiven, Dokumente, Knowledge-Quellen und Knowledge-Records akzeptieren versionsbehaftete, endpointgebundene Cursor und liefern bei weiteren Seiten `X-Next-Cursor`, ohne das bisherige Array-Format zu brechen. Die bestehenden Frontend-Consumer für die fünf erweiterten Sammlungen folgen den opaken Cursorn automatisch und liefern weiterhin vollständige Arrays an `useSession` und `KnowledgeManager`. Vollständige Cursor-Consumer für die Kernlisten, SQL-seitige Chat-Priorisierung und ein begrenzter Last-/Multiworker-Nachweis bleiben offen.
- **Benötigt:** Cursor-Regressionen über alle Sortierungen, eine definierte Provisional-Transcript-Strategie für weitere UI-Consumer, ein begrenzter Lastnachweis und die noch fehlende SQL-seitige Chat-Priorisierung.

#### P2.10a – Opaque-Cursor-Grundvertrag für Sitzungslisten

**Priorität:** P2
**Status:** IMPLEMENTED_UNVERIFIED
**Vision-Referenz:** § 18, ergänzt durch §§ 9 und 12

**1. Verbindliches Ziel**

Große Sitzungs-, Segment- und Transkriptlisten müssen über stabile, serverseitig ausgewertete Cursor fortsetzbar sein. Bestehende Clients dürfen weiterhin Arrays mit `limit` erhalten; neue Clients senden den undurchsichtigen Cursor unverändert zurück und erkennen die nächste Seite am `X-Next-Cursor`-Header.

**2. Konkretes Nutzungsbeispiel**

Ein Client ruft `/api/sessions?limit=2` ab, erhält zwei absteigend nach `created_at` und stabil per `id` sortierte Sitzungen sowie `X-Next-Cursor`. Der zweite Request sendet diesen Wert als `cursor` und erhält die nächste Seite ohne Überschneidung. Ein Segment- oder Transkriptcursor darf nicht versehentlich an einer anderen Route akzeptiert werden.

**3. Tatsächlicher Ist-Zustand**

- `app/backend/app/services/cursor_pagination.py` erzeugt und prüft kompakte, URL-sichere Base64-JSON-Hüllen mit Versions- und Endpoint-Bindung.
- `app/backend/app/routers/sessions.py` implementiert Cursorfilter und Tie-Breaker für Sitzungen und Call-Segmente.
- `app/backend/app/routers/transcripts.py` implementiert den Sequenz-/ID-Tie-Breaker. Ephemere Provisional-Rows erscheinen nur auf der Legacy-Erstseite und werden auf Cursor-Seiten nicht wiederholt; der WebSocket bleibt dafür der Livekanal.
- `app/backend/tests/test_cursor_pagination.py` prüft Roundtrip, falschen Endpoint, ungültige Cursor und den Next-Cursor-Header.

**4. Genaue Abweichung**

Die API-Grundlage ist implementiert, aber weitere Listenendpunkte und ein UI-Weiterblättern fehlen. Der Cursorpfad ist deshalb kein vollständiger Produktabschluss für alle großen Listen.

**5. Unabhängige Abnahmetests**

- **Test A – Vertrags- und Robustheitsprüfung:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_cursor_pagination.py' -v`; prüft Versions-/Endpointbindung, Roundtrip und `X-Next-Cursor` nur bei tatsächlich weiteren Datensätzen. **Bestanden: 5/5.**
- **Test B – Regression der bestehenden Session-Router:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_sessions_router.py' -v`; prüft weiterhin Start-, Ende-, Resume- und Delete-Verträge nach Einbau der Response-/Cursorparameter. **Bestanden: 4/4.**
- Zusätzlich: Backend-`compileall` **bestanden**. Die erweiterten Listen-/UI-/Lasttests sind als P2.10b dokumentiert.

**6. Recherche vorhandener Lösungen**

Der Bestand verwendet bereits stabile Composite-Sortierungen und Limits. Die neue kleine Helper-Funktion ergänzt nur die fehlende Cursorhülle; ein neues Paging-Framework oder ein JSON-Formatwechsel wäre für die vorhandenen Frontend-Clients unnötig.

**7. Exakter Umsetzungsplan**

1. Cursorhülle mit Version und Endpoint-Tag einführen.
2. Für jede Sortierung den letzten Datensatz als Tie-Breaker codieren und SQL-seitig `limit + 1` abfragen.
3. Nur bei weiterer Seite `X-Next-Cursor` setzen; Array-Antworten und Provisional-Erstseite kompatibel halten.
4. Fragen, Direktiven, Dokumente, Knowledge-Records und UI-Weiterblättern in einem Folgepaket ergänzen.

**8. Erfüllungskriterien**

- [x] Cursor ist undurchsichtig, versioniert und endpointgebunden.
- [x] Sitzungen, Segmente und dauerhafte Transkripte haben stabile Tie-Breaker.
- [x] Bestehende Array-/Limit-Clients bleiben kompatibel.
- [x] Weitere Seiten werden ausschließlich über `X-Next-Cursor` signalisiert.
- [x] Test A und Test B bestehen.
- [ ] Alle betroffenen Listen und das UI unterstützen Cursor-Seiten.
- [ ] Last- und Multiworker-Nachweis besteht.

**9. Implementierungsnachweise**

- Änderungen: `app/backend/app/services/cursor_pagination.py`, `app/backend/app/routers/sessions.py`, `app/backend/app/routers/transcripts.py`, `app/backend/tests/test_cursor_pagination.py`.
- Commit-SHA: `c101be8a800ea6a06a67cbeb7186c4beb5626314` (GitHub `main`, Branch-Readback verifiziert).
- Ausgeführt: Cursor 5/5, Sessions-Router 4/4, bestehende Transcript-/Backend-Regressionen und `compileall` grün.
- Einschränkung: Die Frontend-Consumer für Sessions/Segmente/Transkripte und ein begrenzter Last-/Multiworker-Nachweis fehlen weiterhin.

**10. Codex-Desktop-Handoff bei Blockern**

Für die nächste Ausbaustufe zuerst die echten Frontend-API-Consumer für Sessions, Fragen, Direktiven, Dokumente und Knowledge-Records auf `X-Next-Cursor` umstellen; danach pro Route zwei Seiten mit künstlichen Gleichständen und gelöschten Zwischenzeilen prüfen. Die Provisional-Transcript-Anzeige muss dabei entweder einen eigenen Cursorteil erhalten oder ausdrücklich live-only bleiben.

#### P2.10b – Cursor-Fortsetzung für Fragen, Direktiven, Dokumente und Knowledge

**Priorität:** P2
**Status:** IMPLEMENTED_UNVERIFIED
**Vision-Referenz:** § 18, ergänzt durch §§ 9, 12 und 16

**1. Verbindliches Ziel**

Die fünf großen Sammlungen `questions`, `directives`, `documents`, `knowledge_sources` und `knowledge_records` müssen mit demselben undurchsichtigen Cursorvertrag wie die Kernlisten fortsetzbar sein. Sortierung und Tie-Breaker müssen stabil bleiben, ein Cursor darf nur am vorgesehenen Endpunkt akzeptiert werden, und bestehende Array-Clients dürfen ohne API-Formatwechsel weiterarbeiten. Die Frontend-Consumer müssen `X-Next-Cursor` URL-sicher zurücksenden und alle Seiten bis zum Ende zusammenführen.

**2. Konkretes Nutzungsbeispiel**

Eine Sitzung enthält mehr als 200 Fragen, Direktiven oder Dokumente; eine Wissensquelle enthält mehr als 500 Records. Die bestehende Session- beziehungsweise Knowledge-Oberfläche ruft die erste Seite ab, folgt dem zurückgegebenen Cursor automatisch, fügt die nächste Seite in der bestehenden Reihenfolge an und rendert dadurch die vollständige Sammlung. Ein Cursor einer anderen Route oder ein beschädigter Wert führt zu `400`, statt eine falsche Seite oder Duplikate zu liefern.

**3. Tatsächlicher Ist-Zustand**

- Backend: `app/backend/app/routers/questions.py::list_questions`, `directives.py::list_directives`, `documents.py::list_documents` sowie `knowledge.py::list_sources` und `list_records` verwenden `limit + 1`, `X-Next-Cursor`, `decode_cursor`/`encode_cursor` und stabile Composite-Sortierungen. Fragen sortieren `created_at DESC, id`; die übrigen vier Listen sortieren aufsteigend, Records zusätzlich `title, created_at, id`.
- Frontend: `app/frontend/src/services/api.ts::requestCursorPage` und `requestAllCursorPages` lesen den Header, setzen den Cursor per `URLSearchParams`, erkennen wiederholte Cursor und begrenzen die Seitenfolge. `listQuestions`, `listDirectives`, `listDocuments`, `listKnowledgeSources` und `listKnowledgeRecords` behalten ihre Array-Rückgabetypen; dadurch erhalten `useSession.ts` und `KnowledgeManager.tsx` ohne parallele UI-Architektur vollständige Daten.
- Testpfade: `app/backend/tests/test_cursor_pagination_extended.py` und `app/frontend/src/services/api.test.mjs`.

**4. Genaue Abweichung**

Die Funktion ist lokal und synthetisch nachgewiesen. Der vollständige Backend-Gesamtlauf ist in dieser Umgebung wegen unabhängiger fehlender optionaler Abhängigkeiten/Modelle nicht als Gesamtgate verwendbar; reale Windows-WebView-Nutzung, 10.000+-Seitenlast, Multiworker-Konsistenz und Provider-/Datenbank-Lastmessung fehlen. Die bereits implementierten Kernlisten haben noch keine gleichwertige automatische Frontend-Seitenfolge.

**5. Unabhängige Abnahmetests**

- **Test A – funktionale Backend-/SQL-Abnahme:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_cursor_pagination_extended.py' -v`; prüft Header-/Marker-Verträge für alle fünf Routen, falsche und beschädigte Cursor sowie mit `aiosqlite` zwei echte Seiten mit identischen Zeitstempeln, stabilen ID-Tie-Breakern, exakter Reihenfolge, keinen Überschneidungen und keinem Cursor am Ende. **Bestanden: 3/3.**
- **Test B – unabhängige Frontend-Consumer-Abnahme:** `TMPDIR="$PWD/.tmp" node --test src/services/api.test.mjs`; prüft eine mehrseitige opake Cursorfolge inklusive URL-Encoding und Reihenhalt sowie separat alle fünf Consumer, korrektes Ende ohne Header und Weitergabe eines HTTP-Fehlers. **Bestanden: 10/10, davon 2 neue Cursorfälle.**
- Zusätzlich: `npm test` im Frontend **384/384**, `npm run build`, Backend-`compileall`, Knowledge-Mutationsschutz **41/41**, `git diff --check` und Repository-Layout-Guard **bestanden**. Der unabhängige Gesamt-Backendlauf bleibt wegen externer Testumgebungsfehlern offen; seine konkreten Blocker sind `socksio`/SOCKS, ein fehlendes ONNX-`ecapa`-Modell und ein Subprozess ohne `PYTHONPATH`.

**6. Recherche vorhandener Lösungen**

Der bestehende `app/backend/app/services/cursor_pagination.py`-Helper und die bereits eingeführten SQL-Tie-Breaker wurden wiederverwendet. Für das Frontend reichen die vorhandene Fetch-Schicht, `Response.headers` und die Web-Standardklasse `URLSearchParams`; ein neues Paging-Framework oder ein JSON-Wrapper hätte die bestehenden Array-Verträge unnötig gebrochen. Eine externe Bibliothek wurde deshalb nicht ergänzt.

**7. Exakter Umsetzungsplan**

1. Die fünf Router-Listen um Cursorparameter, `limit + 1`, endpointgebundene Marker und `X-Next-Cursor` ergänzen.
2. Je Sortierung den letzten Datensatz inklusive ID als Marker codieren und den nächsten SQL-Bereich strikt danach filtern.
3. Die gemeinsame Frontend-Fetch-Schicht so erweitern, dass sie Cursor URL-sicher sendet, Seiten in Reihenfolge zusammenführt und bei Wiederholungen beziehungsweise endlosen Sequenzen fail-closed abbricht.
4. Die bestehenden `useSession`- und `KnowledgeManager`-Aufrufer unverändert über die Array-Kompatibilität integrieren.
5. Route-nahe SQL-/Robustheitstests und unabhängige Frontend-Consumer-Tests ausführen; danach Regressionen, Build und Layout-Guard prüfen.

**8. Erfüllungskriterien**

- [x] Alle fünf erweiterten Endpunkte akzeptieren einen versionierten, endpointgebundenen Cursor.
- [x] `limit + 1` und `X-Next-Cursor` verhindern fehlende oder doppelte Seiten.
- [x] Alle Sortierungen besitzen dokumentierte stabile Tie-Breaker.
- [x] Falsche und beschädigte Cursor werden mit `400` abgewiesen.
- [x] Bestehende Array-Clients und die vorhandenen UI-Consumer bleiben kompatibel.
- [x] Test A und Test B bestehen unabhängig voneinander.
- [x] Frontend-Build, relevante Regressionen und Layout-Guard bestehen.
- [ ] Kernlisten-Consumer, echte Windows-/WebView-Abnahme, Last- und Multiworker-Nachweis bestehen.

**9. Implementierungsnachweise**

- Änderungen Backend: `questions.py`, `directives.py`, `documents.py`, `knowledge.py`, `test_cursor_pagination_extended.py`.
- Backend-Commit: `4687dc718b876d77138e0b396b6baa660e6eff75`; Branch-Readback von `main` bestätigt.
- Änderungen Frontend: `app/frontend/src/services/api.ts`, `app/frontend/src/services/api.test.mjs`.
- Frontend-Commit: `47d45acb16e8a5ae879e3a1657ba58f33a94bebb`; Branch-Readback von `main` bestätigt.
- Ausgeführte Nachweise: erweiterter Cursor 3/3, Kerncursor 5/5, Frontend-API 10/10, Frontend 384/384, `npm run build`, `compileall`, Knowledge-Guards, `git diff --check`, Layout-Guard.

**10. Codex-Desktop-Handoff bei Blockern**

Auf einem autorisierten Windows-/WebView2-Checkout zuerst `python app/scripts/github_sync.py --pull --strict` nach erfolgreicher CLI-Authentifizierung ausführen. Danach die Sitzungslisten-, Segment- und Transkript-Consumer auf dieselbe automatische Cursorfolge umstellen, eine Sitzung mit mindestens zwei Seiten je Liste laden und die Provisional-Transcript-Strategie prüfen. Anschließend einen 10.000+-Eintrags-Lastlauf, einen Zwei-Worker-Lauf mit identischer Datenbank und einen echten Knowledge-/Dokument-Upload-/Löschdurchlauf ausführen; Ergebnisse mit Route, Sortierung, Cursor, Commit-SHA und Laufzeit dokumentieren.

### P2.11 Parallele Migrationsstarts

**Priorität:** P2
**Status:** PARTIAL
**Vision-Referenz:** §§ 15, 18 und 21

**1. Verbindliches Ziel**

Mehrere Worker dürfen die Datenbankmigration beim Start parallel anfordern, aber genau ein PostgreSQL-Advisory-Lock muss die Schemaarbeit serialisieren. Ein fehlgeschlagener Lauf muss seine Transaktion zurückrollen, den Lock und die Lock-Session freigeben und einen späteren Retry ermöglichen. Frische, versionierte und unversionierte Legacy-Datenbanken müssen deterministisch auf genau einen Alembic-Head gelangen.

**2. Konkretes Nutzungsbeispiel**

Zwei Prozesse starten gleichzeitig. Einer führt die Migration aus, der andere wartet am Advisory-Lock und erreicht danach denselben Head. Schlägt die Migration fehl, bleiben keine halb angewendeten DDL-/Versionseinträge zurück; der nächste Start kann nach Behebung der Ursache erneut laufen. Eine leere Datenbank wird gebootstrapped, eine alte `create_all`-Datenbank wird adoptiert und eine versionierte Datenbank wird nur bis `head` hochgezogen.

**3. Tatsächlicher Ist-Zustand**

- `app/backend/app/main.py::_run_schema_migrations` hält die PostgreSQL-Lock-Session für den gesamten Ablauf offen; `_schema_startup_action` unterscheidet `bootstrap`, `adopt` und `upgrade`.
- `app/backend/alembic/env.py` führt DDL und Alembic-Schritte transaktional aus. Die neue Cleanup-Struktur schließt die Lock-Session auch dann, wenn `pg_advisory_unlock` selbst fehlschlägt.
- `app/backend/tests/test_schema_migration_lock_retry.py` deckt einen fehlgeschlagenen Lauf mit anschließendem Retry sowie den Unlock-Fehler mit garantiertem `close()` ab.
- `app/backend/tests/test_alembic_transaction.py` prüft Commit/Rollback eines echten isolierten SQLite-Transaktionslaufs; `test_main_schema.py` deckt die drei Startup-Pfade ab; `test_schema_migration_sqlite.py` führt den echten frischen und unversionierten Legacy-Pfad aus, prüft den migration-only Index-Tail, resequenziert doppelte Transcript-Sequenzen und wiederholt beide Starts idempotent. Der echte PostgreSQL-Zwei-Worker-Lauf bleibt über `DEBATEAI_TEST_POSTGRES_URL`, `DEBATEAI_TEST_POSTGRES_RUN_ID` und `DEBATEAI_TEST_POSTGRES_ALLOW_SHARED=true` zuschaltbar.

**4. Genaue Abweichung**

Die lokale Fehler-/Retry- und Legacy-Pfadmatrix ist reproduzierbar grün, einschließlich echter SQLite-Adoption eines unversionierten Schemas mit doppelten Transcript-Sequenzen, Constraint-Rebuild und sicherem Retry. Ein autorisierter isolierter PostgreSQL-Runner mit zwei echten Prozessen, die vollständige historische Legacy-Datenbankmatrix und der Nachweis eines sichtbaren Startup-Fehlers in der Desktop-UI fehlen in dieser Umgebung. Deshalb bleibt das Ziel `PARTIAL`.

**5. Unabhängige Abnahmetests**

- **Test A – funktionale Failure-/Retry-Abnahme:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_schema_migration_lock_retry.py' -v`; erzwingt zuerst einen echten Runner-Fehler und anschließend einen Retry (2/2 Lock-/Cleanup-Fälle), einschließlich eines fehlschlagenden Unlocks, bei dem die Session trotzdem geschlossen wird. **Bestanden: 2/2.**
- **Test B – unabhängige Transaktions-/Legacy-Abnahme:** `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_alembic_transaction.py' -v` plus `... -p 'test_main_schema.py' -v`; prüft Rollback/Commit und `bootstrap`/`adopt`/`upgrade` getrennt. **Bestanden: 2/2 Transaktionsfälle und 20 Startup-/Schemafälle, ein Windows-only Skip.**
- Zusätzlich: SQLite-Migrationsmatrix **3/3**, `compileall` und `git diff --check` **bestanden**. Der autorisierte PostgreSQL-Integrationstest ist ohne isolierte Zugangsdaten nicht ausführbar.

**6. Recherche vorhandener Lösungen**

Die bestehende SQLAlchemy-/Alembic-Integration und PostgreSQL `pg_advisory_lock` sind die passende Lösung für den bereits produktiv vorgesehenen Startpfad. Ein neues Lock- oder Migrationsframework würde die vorhandenen Transaktions- und Desktop-Recovery-Verträge duplizieren; die Änderung bleibt auf den `finally`-Cleanup und die unabhängigen Nachweise begrenzt.

**7. Exakter Umsetzungsplan**

1. Lock-Session über den gesamten Migrationslauf halten und den Startup-Pfad vor der Schemaarbeit klassifizieren.
2. Unlock in einem verschachtelten `finally` ausführen, damit `close()` auch bei Datenbankfehlern garantiert wird.
3. Fehler-/Retry-, Transaktions- und Legacy-Pfadtests getrennt ausführen.
4. Auf einem isolierten PostgreSQL-Runner zwei echte parallele Prozesse, einen absichtlichen Fehler/Retry und die endgültige Alembic-Version prüfen.

**8. Erfüllungskriterien**

- [x] Advisory-Lock wird pro PostgreSQL-Migrationslauf gehalten.
- [x] Fehler im Runner und Fehler beim Unlock lassen die Lock-Session nicht offen.
- [x] Retry nach einem fehlgeschlagenen Lauf ist lokal nachgewiesen.
- [x] Commit/Rollback sowie `bootstrap`/`adopt`/`upgrade` sind separat getestet.
- [x] Test A und Test B bestehen.
- [ ] Echte Zwei-Prozess-PostgreSQL-, vollständige Legacy- und sichtbare Desktop-Fehlerabnahme bestehen.

**9. Implementierungsnachweise**

- Änderungen: `app/backend/app/main.py`, `app/backend/alembic/versions/029_unique_transcript_sequence.py`, `app/backend/tests/test_schema_migration_lock_retry.py`, `app/backend/tests/test_schema_migration_sqlite.py`.
- Commit-SHAs: `e2b8fa93e1b9418a1d2ddbb3b13294138725f00a` (Lock-Cleanup), `4ad315a41758fa9064420fadd0a97e34a3bf1eb1` (fresh/Legacy-Matrix) und `6aa9be935cfdd90c57d64e2f3be1fcee8286a096` (idempotente SQLite-Retry-Reparatur); Branch-Readback von `main` bestätigt.
- Ausgeführt: Lock-/Retry 2/2, SQLite-Migrationsmatrix 3/3, Alembic-Transaktion 2/2, Startup-/Schemafälle 20 (1 Windows-Skip), `compileall`, `git diff --check`.
- Einschränkung: PostgreSQL-Integration und echte Desktop-Fehleranzeige benötigen autorisierte externe Umgebung.

**10. Codex-Desktop-Handoff bei Blockern**

Auf einem isolierten PostgreSQL-Testsystem `DEBATEAI_TEST_POSTGRES_URL`, `DEBATEAI_TEST_POSTGRES_RUN_ID` und `DEBATEAI_TEST_POSTGRES_ALLOW_SHARED=true` setzen und `PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -p 'test_schema_migrations_postgres.py' -v` ausführen. Parallel zwei echte Desktop-/Backend-Prozesse starten, eine Migration absichtlich abbrechen, danach retryen und `SELECT version_num FROM alembic_version` sowie die sichtbare Startup-Fehlermeldung dokumentieren.

### P2.12 Prozessweite Journale und PII-Scrub-Indizes

- **Status:** TTL/LRU, Byte-/Registry-Limits, sessionweises Cleanup und terminale Job-TTL sind implementiert und regressionsgetestet. Ein 10.000-Session-Langzeittest und produktiver Multiworker-Replay-Nachweis fehlen.
- **Benötigt:** definierte RAM-/Indexbudgets, synthetischer 10.000-Session-Lauf, Reconnect-Replay-Prüfung und ein autorisierter Multiworker-Nachweis.

## P3 – Inventar und externe Zuständigkeiten

### P3.2 Repository-/Projekt-Inventar

- **Status:** öffentliche Refs, Open-PRs, Issues, Releases und Actions sind für den aktuellen Connectorzugriff geprüft; Open-PRs/Issues/Releases sind leer. Branch-Protection/Rulesets und private Projects/Tags sind über die aktuelle Integration nicht vollständig lesbar (403 bzw. nicht unterstützte API).
- **Benötigt:** authentifizierter Export der fehlenden privaten Inventare mit Zeitpunkt, Cursor/Seitenzahl und Abgleich gegen lokale Refs.
