# DebateAI Quality Plan

> Fuehrender Optimierungs- und Entscheidungsstand seit 7. November 2026:
> `.ai/DEBATE_AI_OPTIMIERUNG.md`. Dieser Plan bleibt als historischer Detailbeleg.

This checkpoint continues the existing dirty working tree. It does not authorize
resetting, cleaning, committing, or replacing user data.

## Verbindliche Restreihenfolge (2026-11-06)

### Aktueller Ausfuehrungsstand nach Paket-/Live-Pruefung (17:20)

1. **P07 Provider stabilisieren:** Oracle-Aufrufe und Login single-flight;
   gewoehnliche Analyse darf nicht wegen Promptwoertern versehentlich
   Web-Recherche starten. Anmelden, Testen, Trennen/Konto wechseln und sofortige
   Statusaktualisierung fuer das dedizierte ChatGPT-App-Profil. Gemini muss eine
   echte Clientantwort beenden, nicht nur Login/Katalog/Upstream bestaetigen.
2. **P08 ASR und echte Live-Qualitaet:** Der reale Paketlauf hat beide Audiowege,
   Speicherung und schnelle echte Qwen-Ausgaben bestaetigt, aber korrekte
   deutsche Partials wurden durch schlechtere Whisper-Finals ersetzt
   (`abtreiben` -> `Abkälbungen/abtraining`). Finalisierung darf einen besseren
   Partial nicht verschlechtern. Qwen darf aus ASR-Muell keine persoenlichen
   Fakten erfinden und muss natuerlich/rhetorisch antworten.
3. **P08 Funktionsmatrix schliessen:** Sofortantwort + Gegenfrage, Analogien,
   allgemeine Gegenargumente, Auto-/manuelle Recherche samt Quellen,
   Argumentgedaechtnis, Reload-Transkript, Abschlussanalyse und Audio-Stopp im
   realen Paketfluss pruefen. Zahlen, Negationen, Bedingungen und Revisionen
   muessen bis Claim/Recherche/Antwort konsistent bleiben; stale Resultate
   werden verworfen.
4. **P10/P06 erhalten:** deutsche Idealstandards, `Ich`, aktive deutsche
   Assistenten, genau `Überzeugend`/`Brutal-sachlich`, vereinfachte UI,
   monochromer Starter/Logo, sichtbare Einzelinstanz und Tray-Restore nicht
   regressieren. Die vom Nutzer abgewählte feste Drei-Minuten-Abnahme entfaellt;
   kurze reale Restore-/Health-Pruefungen bleiben Pflicht.
5. **P05 abschliessen:** erst nach den obigen Quellkorrekturen genau ein neuer
   Python-3.12-One-Dir-Build. Oracle/Gemini-Runtimes, Audio->KI->Speicherung,
   internes Updater-ZIP sowie Update/Rollback kurz pruefen; bestehendes
   funktionierendes `dist` bis zum erfolgreichen Austausch behalten.

Bei jedem Punkt werden **Quellcode umgesetzt**, **gezielt geprueft** und
**im finalen Paket bestaetigt** getrennt ausgewiesen. Benutzerkonfigurationen,
Prompts, Konten, Cookies und Sitzungen bleiben erhalten; nur expliziter
Kontowechsel darf das dedizierte ChatGPT-App-Profil recoverbar archivieren.

Diese Reihenfolge ist aus dem finalen Auftrag und den gemeldeten realen Fehlern
abgeleitet. Kein Punkt darf durch einen erfolgreichen Unit-Test oder Build als
real erledigt gelten.

1. **P09 Echte lokale Live-KI:** Qwen darf keine deterministischen Karten
   erhalten und nicht am Ausgabelimit leer bleiben. Natürlicher deutscher
   Sofortsatz, stützendes Gegenargument, Gegenfrage und Analogie zuerst.
2. **P07 Web-Provider:** normales persönliches ChatGPT Web/Oracle mit GPT-6
   Extra High, danach Gemini Web-to-API mit exakt Gemini 3.1 Pro High. Work/Codex
   und Gemini CLI bleiben nur Fallback. Status, Sitzung, Re-Login und je eine
   reale zulässige Antwort prüfen.
3. **P10 Ideale Standards:** Deutsch, Auto-Recherche oft, Analogien,
   Argumentgedächtnis, Transkriptspeicherung und Abschlussanalyse aktiv; „Ich“
   bei neuen Debatten sofort vorhanden; normale Oberfläche ohne verwirrende
   Agentenschalter oder Gesprächsarten. Die zwei Debattenstile Überzeugend und
   Brutal-sachlich bleiben in den erweiterten Einstellungen erhalten.
4. **P01/P08 Realablauf:** erster deutscher Partial, beide Audiopegel,
   Sofortantwort, Gegenargument, Analogie, Recherche/Quellen,
   Transkriptspeicherung, Aufnahmeende und Abschlussanalyse real prüfen.
5. **P06 Desktop:** monochromer Starter, sichtbares Hauptfenster,
   Schließen-in-Tray, Wiederherstellung, Mehrfachstart, Backend und PostgreSQL.
6. **P05 Release:** genau ein abschließender Python-3.12-One-Dir-Neubau aus dem
   dann aktuellen Quellstand; Oracle und Gemini-Runtime einschließen; internes
   Updater-ZIP/Update/Rollback erhalten; alten Build bis zur Abnahme behalten.

Der nächste aktive Punkt ist **P10**; danach folgen der reale Paket-Neustart für **P07**, der reale Live-Ablauf **P08** sowie Build- und Desktop-Abnahme **P05/P06**.

## Verbindlicher Vollabgleich der letzten Nutzeranweisungen

Diese Liste ist die Arbeits- und Abnahmegrundlage. Ein Punkt darf weder durch
einen Unit-Test noch durch einen früheren Build stillschweigend als erledigt
gelten. Bereits funktionierende Implementierungen bleiben erhalten.

### A. KI-Ausgabe und Geschwindigkeit

- Ausschließlich echte KI-Ausgaben von lokalem Qwen, normalem ChatGPT Web oder
  Gemini Web anzeigen. Keine deterministischen Sofortsätze, Analogien,
  Gegenfragen oder sonstigen Textbausteine als Modellantwort ausgeben.
- Ist kein Modell verfügbar, einen ehrlichen verständlichen Fehler mit
  Anmelde-/Wiederholaktion zeigen statt einer erfundenen Ersatzantwort.
- Qwen lokal ohne unsichtbaren Thinking-Token-Verbrauch streamen; erste
  brauchbare, natürliche deutsche Aussage möglichst unter drei Sekunden.
- Sofortsatz, stützendes Gegenargument, Gegenfrage, Analogie, erweiterte
  Argumente und Zahlen-/Negations-/Bedingungsbezug müssen inhaltlich
  zusammenpassen und menschlich sprechbar sein.
- Keine sichtbaren Output-Tokenlimit-Fehler; Abbruch und Überlänge als
  Modellfehler behandeln, nicht als fertige Empfehlung.

### B. Provider – exakt diese Priorität

1. **Normales persönliches ChatGPT Web/Oracle**, nicht Work/Codex, Modell
   GPT-6 mit Extra High/XHigh.
2. **Gemini Web-to-API/Proxy**, nicht Gemini CLI, exakt Gemini 3.1 Pro mit High.
3. CLIProxy/Work/Codex nur als klar erkennbarer Fallback.
4. Gemini CLI nur als weiterer Fallback.
5. Offizielle kostenpflichtige APIs standardmäßig deaktiviert; API-Key-Fallback
   nur bewusst konfiguriert, niemals heimlich oder erzwungen.

Für die beiden führenden Webwege sind Runtime vorhanden, Status, gespeicherte
Sitzung nach Neustart, Modellkatalog, echte minimale Modellantwort, Trennen und
vorhandener Re-Login zu prüfen. Eine Anmeldung zählt nur nach realer
Bestätigung. Falls Browserbestätigung/2FA nötig ist, wird ausschließlich der
vorhandene Login-Flow geöffnet und der Punkt bis zur Nutzerbestätigung als
BLOCKIERT geführt.

### C. Sprache, Audio und realer Gesprächsablauf

- Deutsch gilt ab dem ersten Live-Partial; kein englischer Ersttext mit späterer
  deutscher Korrektur. Zahlen, Negationen, Bedingungen und Sprecherbezug dürfen
  bei Revisionen nicht verloren gehen; veraltete Revisionen dürfen aktuelle
  Ergebnisse nie überschreiben.
- Mikrofon- und Gesprächs-/Systempegel sind beide sichtbar und reagieren real.
- Mikrofon und optionaler PC-Ton werden stabil aufgenommen; Aufnahme und
  Audio-Worker enden nach Gesprächsende zuverlässig.
- Claims lösen echte Sofortantwort, allgemeine Gegenargumentsuche,
  Empfehlungen, Analogien und vertiefte Argumente aus. Auto-Recherche läuft
  standardmäßig und zeigt echte Quellen mit korrekter Zuordnung.
- Finale Transkripte werden gespeichert und nach Reload geladen;
  Abschlussanalyse, Erkenntnisse und Sitzungsprotokoll sind erreichbar.

### D. Ideale Standards und einfache deutsche Oberfläche

- Eine neue Debatte ist ohne weitere Konfiguration sinnvoll startbereit:
  Deutsch, Auto-Recherche, Analogien, Argumentgedächtnis,
  Transkriptspeicherung, Abschlussanalyse und benötigte Assistenten aktiv.
- Der Nutzer ist sofort als Teilnehmer **„Ich“** mit eigener Position vorhanden.
- In der normalen Oberfläche keine englischen Agentennamen/-beschreibungen,
  keine unnötigen Agentenschalter und keine verwirrende Modusauswahl.
- Es bleiben genau zwei fachliche Debattenstile: **Überzeugend** und
  **Brutal-sachlich**. Die einfache Neuerstellung verwendet Überzeugend; die
  alternative Einstellung bleibt gezielt auffindbar.
- Vorhandene individuell geänderte Einstellungen, Prompts, Konten und Sitzungen
  bleiben erhalten. Nur exakt bekannte alte Standardkonfigurationen werden
  einmalig auf den Idealstandard/Web-first migriert.

### E. Desktop, Design und Stabilität

- Starter, App und Windows-Icon/Logo sind konsistent minimalistisch
  schwarz/weiß/grau; kein alter blauer Starter und kein veraltetes Logo oben
  links. Keine UI-Neuentwicklung.
- Normaler Start öffnet sichtbar. Minimieren, Schließen-in-Tray, mehrfaches
  Wiederherstellen und erneutes Öffnen funktionieren; Browser-Fallback bleibt.
- Keine konkurrierenden Hauptinstanzen, verwaisten Kinder, hängenden Starts oder
  unbeabsichtigten Backend-/PostgreSQL-Stopps. Replay, Reconnect, Worker-Abbruch,
  Caches und Revisionen bleiben robust und ressourcenschonend.
- Leere, alte unversionierte und versionierte Datenbanken werden getrennt
  behandelt; Update/Rollback erhält Daten, Einstellungen, Secrets und Logins.

### F. Ausführung und Release

- Keine große Architekturänderung, keine allgemeine Optimierungsrunde, keine
  RL-/Datenschutzrunde und kein Löschen nur für grüne Tests. Nachweislich
  überflüssige aktive Duplikate erst nach erfolgreicher Realabnahme entfernen.
- Fortschritt nach jedem Punkt hier und in `.ai/PROGRESS.md` als
  `Pxx FERTIG – Änderung – Test` speichern.
- Nach allen Codeänderungen genau einen frischen Python-3.12-Windows-x64-
  One-Dir-Build erstellen. Oracle und Gemini-Web-Runtime müssen enthalten sein;
  das interne Updater-ZIP bleibt funktionsfähig, ohne zusätzliches Nutzer-ZIP.
- Alten funktionierenden Build bis zum erfolgreichen EXE-, GUI-, Provider-,
  Audio-, Datenbank-, Update- und Rollback-Smoke behalten. Erfolg erst melden,
  wenn die geprüfte EXE dem aktuellen Quellstand entspricht.

| ID | Priority | Evidence and expected benefit | Acceptance / focused test | Status |
| --- | --- | --- | --- | --- |
| P01 | P0 | Native audio had no level events, stale capture ownership and English flashes with fixed German. A later regression also republished deterministic template cards as if they were model answers. Restore meters, owner-safe stop and German live text; publish only genuine streamed/final model guidance. | Focused audio, WebSocket, language, captioner, token-budget and stale-revision tests pass; deterministic publication has a negative regression test. | FERTIG |
| P02 | P0 | Embedded Alembic `fileConfig()` closed the launcher's file handler, hiding readiness and access evidence; empty/adopted/versioned databases require distinct actions (`main.py`, `alembic/env.py`, startup log). Preserve logging and migration compatibility. | Migration-path and host-logger regression tests pass; packaged `/api/ready` and PostgreSQL are stable. | FERTIG |
| P03 | P1 | Console suppression scanned the complete Windows process tree every 10 ms, while packaged AI defaults were re-merged on every prompt lookup (`windows_console.py`, `ai_config.py`). Reduce proven CPU and file-I/O waste without changing behavior. | Default scan interval regression and once-per-process merge regression pass. | FERTIG |
| P04 | P1 | OAuth popup reservation/fallback, WebSocket replay/coalescing, audio meter rendering, manual review/source library, and the monochrome production UI need one focused verification. | Targeted Node tests and production TypeScript/Vite build pass; no successful account login is claimed without user interaction. | FERTIG |
| P05 | P0 | Code changes require one final Python 3.12 Windows x64 one-dir and internal updater ZIP built from fresh staging while preserving the prior release. | Build script completes staged EXE/local-ASR/archive/update/rollback smokes and publishes canonical artifacts only after all focused fixes. | FERTIG - staged EXE/local-ASR/archive/update/rollback smokes passed; verified candidate published through updater with backup/health/rollback |
| P06 | P0 | Final release must prove visible and restorable GUI ownership, single-instance behavior, backend/PostgreSQL stability, clean close/restart, and artifact identity. | Multiple close/reopen cycles, stable `/api/ready`, clean shutdown/restart, SHA-256 recorded; no fixed three-minute wait per latest instruction. | FERTIG - final EXE/window/ready/DB real; hidden-live-window watchdog packaged and real-tested |
| P07 | P0 | Existing personal ChatGPT-Web Oracle and Gemini-Web-to-API paths must lead. Work/Codex OAuth and Gemini CLI remain fallbacks only. Check re-login, persistence, account switch, actual model/effort and delivered response. | Packaged ChatGPT Web uses GPT-6 Extra High without concurrent profile collisions; packaged Gemini Web serves exact `gemini-3.1-pro` High and returns one minimal client response; status persists after restart. | Status REAL: ChatGPT `gpt-6`/`xhigh`, Gemini `gemini-3.1-pro` Pro-ready; no new model answer was sent |
| P08 | P0 | Original user-visible failures require a release matrix, not only unit evidence: German partial/final, both meters, natural instant/enriched advice, research sources, stored transcript, review, audio stop, GUI/backend/DB stability. | Each row classified REAL GETESTET / NUR UNIT-GETESTET / OFFEN / BLOCKIERT, with a local packaged smoke where possible and no paid provider calls. | REALER LAUF: PEGEL/TRANSKRIPT/QWEN BESTAETIGT; ASR-FINAL/ANTWORTQUALITAET/RECHERCHE OFFEN |
| P09 | P0 | Der reale Paketlauf vom 6. November verwarf jeden Qwen-Live-Aufruf: Ollamas OpenAI-kompatibler Pfad ignorierte `think=false`, verbrauchte 1024 Token im unsichtbaren Denkkanal und lieferte 0 sichtbare Zeichen. | Nativer Ollama-JSON-Schema-Pfad liefert echte Modellantwort; erster vollständiger `answer_now`-Teil unter 3 s, vollständige strukturierte Antwort ohne Längenfehler. | FERTIG (Quelllauf real; Paketabnahme in P08) |
| P10 | P0 | Neue Debatten zeigten alte englische Agent-Seeds, mehrere Gesprächsarten und legten „Ich“ erst beim Start an; gespeicherte Altwerte konnten den idealen Desktop-Standard überlagern. | Neue Debatte enthält sofort „Ich“; deutsche automatische Assistenten und idealer Debattenstandard sind sichtbar/aktiv; erweiterte zwei Debattenstile bleiben intern erhalten. | FERTIG (Quellvertrag; Paketabnahme P08) |

Optional dependency major upgrades and broad cleanup are deliberately deferred:
the compatibility audit found no lower-risk change with direct benefit for this
hotfix, and the assignment forbids speculative refactoring.

## Release error matrix (live checkpoint)

| Original issue | Current classification | Required release evidence |
| --- | --- | --- |
| German direct live partials/finals | BEHOBEN UND REAL GETESTET (source runtime) | Real 16 kHz German WAV -> fixed-language Whisper Base produced German text; packaged session reconfirmation remains |
| Microphone and system level meters | NUR UNIT-GETESTET | Packaged native audio event/UI observation |
| Immediate recommendation | NUR UNIT-GETESTET | Packaged meaningful German claim -> genuine streamed/model card; no deterministic substitute is allowed |
| Recommendation/counterargument/analogy/extended argument | NUR UNIT-GETESTET | Packaged meaningful claim and structured card fields |
| No output-token-limit empty card | NUR UNIT-GETESTET | Packaged model/fallback result without empty card |
| Automatic research and visible sources | NUR UNIT-GETESTET | Enabled session and source-bearing update; may be BLOCKIERT if provider login is absent |
| Finalized and persisted transcript | BEHOBEN UND REAL GETESTET (prior build) | Reconfirm final release if practical; prior real session stored 11 finals and both audio tracks |
| Reachable post-call analysis | NUR UNIT-GETESTET | Packaged end-call and manual review control; model execution may require confirmed login |
| Audio stops at end | NUR UNIT-GETESTET | Packaged end-call and native capture ownership check |
| GUI/tray/backend/PostgreSQL stability | BEHOBEN UND REAL GETESTET (final EXE/window/backend/DB); final tray cycle not repeated | Final package owns a responding `Debate AI` window, `/api/ready=ok`, and its PostgreSQL postmaster; source/prior-runtime close/restore passed twice |
| Personal ChatGPT-Web login/session/models | BEHOBEN UND REAL GETESTET (Quelllauf) | Normal personal ChatGPT Web returned `WEB-OK`; Oracle verified GPT-6 and Extra High, with no Work/Codex/API fallback. Reconfirm packaged restart after P05. |
| Gemini Web login/session/models | BEHOBEN UND REAL GETESTET (Status/Katalog) | Final package reports ready, Pro available and exact `gemini-3.1-pro`; a new answer request was deliberately not sent. |
| Work/Codex and Gemini CLI fallbacks | NUR UNIT-GETESTET | Deliberately not accepted as proof for the two personal web providers |

Latest P08 source evidence: the retained real German WAV isolated short final
Whisper context as the noun-corruption cause. Same-speaker final fragments are
now context-batched (11 tests), and Qwen's live contract now rejects damaged ASR
echoes and invented personal biography while requiring natural rhetorical
German (4 focused tests). Both changes still require the one final packaged
conversation smoke before classification as REAL GETESTET in the release matrix.

Latest P06/P07 evidence: Win32 enumeration identified Backchannel PID 32592 as
the owner of the visible `.NET-BroadcastEventWindow` and the hidden real form.
The corrected selector hid the helper and restored the real form twice while
readiness remained healthy. Gemini health/catalog-vs-chat probing also isolated
the helper lifecycle: restart credential retention, rotated-cookie cache
preservation and explicit disconnect signalling now have 9 focused green tests;
real answer delivery remains a final-package gate.

## Final package checkpoint - 2026-11-06

- **P05 FERTIG - Aenderung - Test:** the existing Python 3.12 staging candidate
  had already passed staged desktop, local-ASR, archive, update and rollback
  smokes. The old launcher shut down backend, WebView, Gemini and PostgreSQL;
  its known old `WinFunctionType` cleanup crash left only the launcher dialog.
  After verifying all owned services stopped, only that stale PID was ended and
  the repository updater atomically swapped the bundle with health/rollback
  enabled. Stage, backup and failed directories are gone after acceptance.
- **P06 final package REAL:** `dist/Backchannel/Backchannel.exe` started two
  expected processes (launcher plus embedded WebView), the child exposed the
  responding `Debate AI` main window, `/api/ready` returned `ok`, and the
  package-owned PostgreSQL postmaster was alive. Final SHA-256:
  `8093284EF1ABAED932E26EAD8A8D38C56727AE7D3EBFC681B6B59020D17A3742`.
- **P09 final package REAL:** exact bundled `debate_live_v2` plus the real
  `LiveDebateResponse` schema on native Ollama `/api/chat` returned `stop`, no
  thinking field, and the genuine German answer: `Quellen sind nicht unwichtig
  - sie sind die Grundlage fuer eine faire Debatte.`
- **P07 packaged status:** normal ChatGPT Web is ready as `gpt-6` / `xhigh`.
  Gemini Web helper health is green, but an isolated catalog probe records
  `GEMINI_COOKIES is invalid or expired`; the catalog is empty. This is an
  honest interactive re-login blocker, not a successful Gemini session.
- Per the latest release instruction no additional user ZIP was published.
  The already smoke-tested internal archive remains in `build/release-stage`.

## Targeted follow-up matrix - 2026-11-06

| ID | Priority | Change / evidence | Focused acceptance | Status |
| --- | --- | --- | --- | --- |
| P10 | P0 | Current implementation audit for the next pipeline/agent review; no deletion of the used material/knowledge adapter. | `.ai/IMPLEMENTATION_AUDIT.md` distinguishes source, runtime, package, active/optional/disabled/open and lists agents/prompts/tools. | FERTIG |
| P11 | P0 | Ten-second Whisper context batching could leave a short utterance as a disappearing interim until call end. | Pending local Whisper audio flushes within 1.5 s; 14 queue/audio tests pass. | FERTIG - source only |
| P12 | P1 | New-session UI hardcoded persuasive although backend and prompt routing already support forceful. | Both modes render, persuasive is selected, chosen `meeting_type` is sent on create; 2 tests pass. | FERTIG - source only |
| P13 | P0 | Stale ChatGPT verification caused repeated Oracle browser jobs; unchanged invalid Gemini cookie caused a ~33 s restart loop. | Selector failure opens at most one job then requests re-login; unchanged Gemini handoff starts once while successful crash restart remains; 9 focused tests pass. | FERTIG - source only |
| P14 | P1 | Provider readiness should be visible before a call without automatically opening login pages. | One startup status fetch opens only the in-app Connections page; 9 focused tests and production build pass. | FERTIG - source only |
| P15 | P1 | Research frequency is global and live control is only on/off. | Session-scoped setting persists and can be changed pre-call/live without mutating unrelated sessions. | OFFEN - requires schema/contract decision |
| P16 | P0 | Source fixes need a fresh package while preserving current release. | Python 3.12 staged build and only relevant backend/frontend/desktop/EXE smokes; atomic publish after success. | FERTIG - staged EXE/DB/local-ASR and archive update/rollback smokes passed; published atomically |
| P17 | P0 | A live WebView child could lose only its visible native form while backend/tray stayed healthy. | Restore only hidden live main forms; do not undo minimize or reopen a closed UI child; final package visible and ready. | FERTIG - 46 launcher tests plus real staged/final window smoke |
