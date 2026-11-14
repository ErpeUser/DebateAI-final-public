# DebateAI Quality Progress

> Fuehrender Stand fuer den Auftrag vom 7. November 2026:
> `.ai/DEBATE_AI_OPTIMIERUNG.md`. Diese Datei bleibt als historisches
> Detailprotokoll erhalten.

## Laufender Checkpoint 17:20

- **P07 IN ARBEIT - belegte Ursache:** Im realen Paket starteten mehrere
  Analyse-Agenten gleichzeitig Oracle gegen dasselbe dedizierte Chrome-Profil.
  Ein Lauf schloss das Fenster eines anderen (`Chrome window closed...`),
  weitere scheiterten am Modellschalter. Gewoehnliche Analyse aktivierte zudem
  allein wegen Woertern wie Quelle/Recherche im Systemprompt Browser-Recherche.
- **P07 Quellcode umgesetzt, Pruefung offen:** Oracle ist nun ueber den ganzen
  Browserlebenszyklus single-flight; Recherche wird nur noch durch explizite
  Web-Recherche oder einen Recherche-Call aktiviert. Gezielte Regressionchecks,
  Login-Serialisierung und die UI fuer `Erneut anmelden / Konto wechseln`
  folgen als naechster Schritt.
- **P08 REALER PAKETBEFUND:** Mikrofon und Systemton liefen parallel, finale
  Transkripte wurden gespeichert und echte Qwen-Antworten kamen in etwa
  0,8-1,1 s. Die Final-ASR verschlechterte jedoch ein korrektes Live-Partial
  `abtreiben` zu `Abkälbungen/abtraining`; darauf erfand Qwen unbrauchbare
  persoenliche Saetze. Ursache und Laufzeitpfad sind damit lokalisiert, aber
  noch nicht behoben.
- **P07 Gemini OFFEN:** Anmeldung, persistierte Sitzung, exaktes
  `gemini-3.1-pro` und High/Katalog sind real bestaetigt. Die gepackte Bridge
  lieferte eine Minimalantwort trotz Upstream-Abschluss nicht innerhalb 120 s
  an den Client; der Abschluss bleibt offen. Ein separater Cold-start-Fehler
  bei `{"data": null}` ist im Quellcode korrigiert, aber noch nicht neu gebaut.
- **P05/P06:** Der aktuelle `dist`-Build bestand EXE, ASR, Update und Rollback;
  GUI-Schliessen/Neuoeffnen stellte zweimal dieselbe Einzelinstanz wieder her.
  Da nach dem Build Quellkorrekturen folgten, ist er kein finales Artefakt.
  Fester Drei-Minuten-Wartetest entfällt nach Nutzeranweisung; kurzer finaler
  Restore-/Health-Smoke bleibt.
- **Naechster Schritt:** P07 Regressiontests und Kontowechsel, dann P08
  ASR-/Promptkorrektur und Gemini-Antwortabschluss; erst danach ein Neubau.

## Abarbeitungsreihenfolge – nicht überspringen

1. **P09 echte lokale KI abschließen:** nativer Qwen-Pfad, keine Templates,
   natürlicher deutscher Sofortsatz und konsistente strukturierte Felder.
2. **P07 Web-Provider jetzt prüfen/reparieren:** ChatGPT Web/Oracle normal
   GPT-6 Extra High zuerst; Gemini Web-to-API Gemini 3.1 Pro High danach;
   Work/Codex und Gemini CLI nur Fallback. Status, Session, Modell und je eine
   echte Antwort; bei notwendiger Browserbestätigung klar BLOCKIERT.
3. **P10 Idealstandard fertigstellen:** bekannte alte Standards einmalig
   migrieren, individuelle Werte erhalten; Deutsch, Recherche, Argumente,
   Speicherung und Abschluss aktiv; „Ich“ sofort; genau zwei Debattenstile;
   deutsche automatische Assistenten ohne normale Schalterflut.
4. **P08 echter Gesamtfluss:** erster deutscher Partial, beide Pegel,
   Sofortsatz, Gegenargumente, Analogie, erweiterte Argumente,
   Recherche/Quellen, gespeichertes Transkript, Abschlussanalyse und Audio-Stopp.
5. **P06 Desktop real:** monochromer Starter plus aktuelles Logo, sichtbares
   Fenster, Tray-Wiederherstellung mehrfach, Einzelinstanz, Backend und
   PostgreSQL mindestens drei Minuten stabil.
6. **P05 genau ein finaler Build:** Python 3.12 One-Dir mit Oracle und
   Gemini-Web-Runtime, EXE-Smoke sowie internes Update/Rollback; alten Build bis
   zur Abnahme behalten und erst dann Hash/Pfad dokumentieren.

Nicht als Erfolg zulässig: deterministische Karten, ChatGPT Work statt normalem
Web, Gemini CLI statt Web-Proxy, englischer Ersttext, nur Unit-getestete
Behauptungen, bezahlte API ohne Freigabe oder ein Build vor Abschluss von P07–P10.

## Aktiver Checkpoint – verbindlich

- **P09 FERTIG – Änderung – Test:** Nur der lokale Debate-Copilot auf
  `endpoint:german-debate-ollama:*` nutzt jetzt Ollamas natives `/api/chat` mit
  `think=false`, echtem Pydantic-JSON-Schema und gestreamtem `answer_now`.
  Deterministische Antwortkarten bleiben entfernt; Qualitäts-/Revisionsgates
  erzeugen keinen Text. Reale lokale Modellprobe: erste vollständige echte
  Antwort nach 1,94 s, vollständige strukturierte Ausgabe nach 6,28 s, kein
  `length`-Abbruch. Die neue EXE wird erst in P08 abgenommen.
- **Aktuell P07:** ChatGPT Web/Oracle normal GPT-6 Extra High und danach Gemini
  Web-to-API Gemini 3.1 Pro High. CLI-/Work-Ergebnisse zählen nicht.
- **P07 ChatGPT-Teil REAL GETESTET:** Der laufende Paketstatus zeigte den
  richtigen persönlichen Oracle-Weg, wurde aber intern zunächst fälschlich von
  der API-Key-Schranke blockiert. Diese Schranke gilt nun nicht mehr für
  `chatgpt-web`; Windows erkennt vorhandenes Edge als Chromium-Runtime und
  Oracle meldet stdout-basierte Fehler verständlich. Strikte Realprobe über
  die normale ChatGPT-Weboberfläche: `GPT-6` verifiziert, `Extra High`
  verifiziert, Antwort `WEB-OK`, 24,2 s. Kein Work/Codex und keine API. Ein
  einmaliger strikter Retry behandelt nur den kalten, verspätet montierten
  Modellschalter; es gibt keinen unbestätigten `current`-/`ignore`-Fallback.
- **P07 Gemini-Login und Katalog REAL GETESTET:** Der vorhandene WebView2-Flow
  wurde sichtbar/fokussiert geöffnet, die interaktive Google-Anmeldung wurde
  abgeschlossen und verschlüsselt gespeichert. Eine frische Web-to-API-Bridge
  entdeckte real `gemini-3.1-pro`, wählte exakt dieses Modell mit
  `reasoning_effort=high` und erhielt die Gemini-Webantwort nach 26,0 s. Weder
  Gemini CLI noch eine kostenpflichtige API wurden verwendet.
- **P07 verbleibender Paketpunkt:** Der aktuell noch laufende alte
  `gemini-web-to-api.exe`-Kindprozess startete um 15:37, das bestätigte neue
  Login wurde erst um 16:10 gespeichert. Der alte Kindprozess übernahm diese
  Sitzung nicht. Der Cookie-Watcher wartet nun länger auf den asynchronen
  Live-Katalog, überlebt Prozess-/Dateifehler und der Backend-Abgleich wartet
  auf den ersetzten Pro-Katalog. Re-Login-Persistenz und eine vom Client
  empfangene Minimalantwort werden nach dem einzigen P05-Neubau erneut real
  geprüft; bis dahin ist P07 noch nicht als komplett FERTIG markiert.
- **P10 FERTIG – Änderung – Test:** Die normale Neuerstellung verwendet ohne
  Moduswahl `debate_persuasive`; „Ich“ wird bereits mit dem Session-Datensatz
  angelegt; die normale Vorbereitung zeigt keine Agentenschalterflut. Bekannte
  alte Desktop-Standards werden einmalig auf Deutsch, Recherche oft, Analogien,
  Argumentgedächtnis, Transkriptspeicherung und Abschlussanalyse migriert,
  individuelle Werte bleiben erhalten. Bekannte alte Analyse-Agenten mit
  `gemini-3.8-flash` wechseln auf normales ChatGPT Web; dessen schmale
  Fallbackkette folgt der gespeicherten Reihenfolge zu Gemini Web, Work/Codex
  und Gemini CLI. Die zwei erweiterten Stile heißen konsistent „Überzeugend“
  und „Brutal-sachlich“. Quellvertrag und Python-Kompilierung sind geprüft;
  Paketabnahme folgt in P08.
- **Jetzt:** finalen Python-3.12-Kandidaten frisch im Staging bauen; danach P07
  Paket-Neustart, P08 Live-Gesamtfluss und P06 Desktop/Tray real abnehmen.
- Quelle der Reihenfolge:
  `C:/Users/User/.codex/attachments/f4cdfe69-93d9-47e6-a907-3bb4b92f8751/pasted-text.txt`.

- Branch/baseline: current user working tree; many pre-existing uncommitted files; no reset, clean, stash, commit, or push.
- Last completed source points: P01-P04, P09 and P10. P07 ChatGPT Web and Gemini login/catalog are real-tested; only packaged Gemini restart/client delivery remains.
- Current point: P05 - one final rebuild with Oracle and Gemini Web after the focused titleless-WebView, cookie-watcher, fixed-German ASR, true Qwen and web-first agent fixes.
- Next points: P07 packaged Gemini-Web persistence, P08 original-error live matrix, then P06 real GUI/tray/backend/PostgreSQL acceptance and controlled publication.
- Changed in this continuation: live recommendation/token budget, native audio levels and ownership, fixed-German live captions, WebSocket level coalescing, embedded Alembic logging preservation, packaged prompt merge cache, console scan interval, monochrome CSS tokens, and focused regression tests.
- Latest tests:
  - 85 focused debate-copilot/language tests passed after removing deterministic template publication and preserving stale-revision protection.
  - 81 focused desktop launcher, Gemini-Web, ChatGPT-Web and release-contract tests passed.
  - 262 focused frontend tests passed; production build passed (2,139 modules, existing >500 kB chunk warning only).
  - Real local ASR smoke passed: Windows-generated 16 kHz German speech was transcribed directly in German by cached Whisper Base with `language=de`.
  - 82 relevant backend tests passed; one unrelated file-persistence case was blocked by the managed Windows temp ACL.
  - 5 critical live language/recommendation/token tests passed.
  - 25 targeted frontend OAuth/meter/replay/review tests passed.
  - 8 Windows console suppression tests passed.
  - Frontend production build passed (2,139 modules); existing >500 kB chunk warning remains.
  - Generated monochrome logo assets validated as PNG/ICO/ICNS; release/rollback contract passed after making post-publication backup cleanup best-effort.
  - `git diff --check` passed (line-ending warnings only).
- Decisions: normal ChatGPT-Web Oracle (GPT-6 Extra High) and Gemini Web-to-API (exact Gemini 3.1 Pro High) lead. Work/Codex OAuth and Gemini CLI are fallbacks only and do not count as provider success. No paid API is forced.
- Build status: the Python 3.12 intermediate candidate passed PyInstaller and was published, including the titleless-window fix. Its command returned failure only because a stale rollback DLL was locked after publication; that cleanup is now deferred safely. The user-requested icon change requires one final rebuild.
- New release gate: unit evidence alone is insufficient. Provider status/model catalogs and the original-error matrix must be checked in the packaged desktop. Browser confirmation/2FA is BLOCKIERT until the user completes it; no paid model request is allowed without approval.
- New root-cause evidence: the prior package omitted `_internal/chatgpt_oracle`, so the normal ChatGPT-Web route could not be ready even though its encrypted profile and earlier verification marker survived. Gemini Web's stored session now yields an empty catalog; its login helper previously sampled cookies only once, and now polls through post-login navigation.
- Next exact action: build the final Python 3.12 candidate with Oracle included, then repeat P06 and perform P07 real web-provider checks before closing P08.

## Checkpoint 2026-11-06 - ASR/Qwen source corrections

- **P07 ChatGPT concurrency/account source FERTIG - Aenderung - Test:** Oracle
  serializes use of its dedicated browser profile; only explicit research jobs
  enable browser research. Login reserves that profile. The settings UI now
  exposes status, connection test, re-login, disconnect and recoverable account
  switch without touching normal Chrome data. Five backend and one frontend
  focused tests passed. Packaged reconfirmation remains in P05/P07.
- **P08 Whisper context source FERTIG - Aenderung - Test:** the user's retained
  German microphone WAV reproduced the failure. Whisper Base recognized
  `Abtreibung` correctly with 10+ seconds of context, while short VAD fragments
  corrupted the noun; Parakeet made a different error. Final local-Whisper jobs
  now coalesce consecutive same-speaker fragments to the measured context size,
  while live Parakeet partials remain immediate. Eleven ordered-transcription
  tests passed.
- **P08 Qwen language contract FERTIG - Aenderung - Test:** the live prompt now
  treats ASR as fallible, forbids invented personal history/family claims,
  avoids echoing visibly damaged wording, silently normalizes only at high
  confidence and otherwise asks a natural clarification. It also requires a
  human rhetorical move via concession, contrast or consequence. The source,
  bundled default and built-in fallback agree; four focused tests passed.
- **Still open:** real packaged ASR/Qwen confirmation, Gemini Web client response
  delivery, the persistent `.NET-BroadcastEventWindow` owner/lifecycle, then one
  final Python 3.12 build and short release smoke.
- **P07 Gemini lifecycle source FERTIG - Aenderung - Test:** direct probing
  proved that health and the exact Pro catalog stayed green while chat requests
  hung and the helper could exit. The watcher now restarts a failed helper from
  its in-memory one-time credential, preserves the upstream rotated-cookie
  cache across ordinary restarts, and consumes an empty handoff as an explicit
  disconnect signal. Eight desktop bridge tests and one backend signal test
  passed. A real delivered answer remains a final-package gate.
- **P06 `.NET-BroadcastEventWindow` FERTIG - Ursache - Test:** PID/handle
  inspection proved Backchannel's WinForms WebView child owned both the hidden
  real `Debate AI` form and a visible internal broadcast window. The old focus
  predicate accepted the first titled window and restored the framework helper.
  Restore now accepts the explicit Debate AI title, rejects/hides framework
  helpers, and retained hidden-main restore support. Four tests passed; two real
  close-to-tray/restore cycles succeeded and `/api/ready` stayed `ok`.

## Checkpoint 2026-11-06 - final staged candidate published

- **P05 FERTIG - Aenderung - Test:** no second build was started. The existing
  Python 3.12 candidate had completed PyInstaller and all staged desktop,
  local-ASR, archive, update and rollback smokes. The old package blocked only
  publication. Its normal update shutdown stopped WebView, backend, Gemini and
  PostgreSQL, then the known old `WinFunctionType` window-cleanup defect left a
  launcher exception dialog. After verifying the owned services were gone,
  only old PID 29772 was ended. The existing updater then performed the atomic
  bundle swap with backup, health gate and rollback; it accepted the new bundle
  and removed stage/backup/failed recovery directories.
- **P06 final EXE REAL - Test:** the new launcher and embedded WebView run from
  `dist/Backchannel`; a responding main window is titled `Debate AI`,
  `/api/ready` is `ok`, and package PostgreSQL is running from the preserved
  `%LOCALAPPDATA%/Backchannel/pgdata`. Final tray restore was not repeated after
  the explicit no-GUI/no-tray instruction; the same source fix passed two prior
  real restore cycles and four focused tests.
- **P09 final EXE REAL - Test:** native Ollama `/api/chat` with the bundled
  `debate_live_v2` prompt and exact `LiveDebateResponse` schema returned a real
  short German answer, counterargument, question and analogy with
  `done_reason=stop` and no thinking text.
- **P07 packaged status - Test:** ChatGPT Web reports ready with normal
  `gpt-6`, `xhigh`. Gemini Web binary and `/health` work, but the provider
  rejects the persisted personal Web cookie as expired/invalid; catalog and
  Pro status are empty. Existing Re-Login is therefore an honest interactive
  blocker. No Gemini CLI, Work/Codex or paid API result was substituted.
- **Final artifact:**
  `C:/Users/User/Datein/Coding/DebateAI/dist/Backchannel/Backchannel.exe`,
  26,875,004 bytes, SHA-256
  `8093284EF1ABAED932E26EAD8A8D38C56727AE7D3EBFC681B6B59020D17A3742`.
  Per the latest instruction no additional user ZIP was published; the already
  smoke-tested internal archive remains under `build/release-stage`.
- Remaining release evidence, not repeated or overclaimed: interactive Gemini
  re-login/client answer, final-package tray cycle, both live meter observation,
  full transcript/research/post-call user flow. These stay BLOCKED/OFFEN in the
  matrix rather than being inferred from unit tests.

## Checkpoint 2026-11-06 - audit and targeted live defects

- **P10 FERTIG - Audit - Quell-/Laufzeitabgleich:**
  `.ai/IMPLEMENTATION_AUDIT.md` documents the actually implemented audio/ASR,
  model/provider, agent, prompt, research, bridge, storage and UI pipeline. It
  separates active, optional, disabled and open behavior and records the live
  provider/ASR status plus current artifact hashes. The historic offerings
  adapter remains because it is a used knowledge-source adapter, not proven
  dead code.
- **P11 FERTIG - Finaltranskript-Latenz - Test:** local Whisper keeps its
  measured context batching, but a short utterance can no longer remain only
  as a disappearing live partial until the call ends. Pending same-speaker
  audio is now flushed after at most 1.5 seconds. The new test failed on the
  missing timer first; all 14 affected queue/audio tests pass.
- **P12 FERTIG - Zwei Debattenmodi - Test:** `NewSessionModal` no longer
  hardcodes `debate_persuasive`. The two already implemented session modes
  `Überzeugen` and `Brutal-sachlich` are visible/selectable; persuasive remains
  the default. Both focused modal tests pass.
- **P13 FERTIG - Provider-Retryschutz - Test:** logs proved two independent
  loops: Oracle repeatedly opened jobs after the saved verification no longer
  matched the current ChatGPT selector, and Gemini restarted the same rejected
  cookie every ~33 seconds. Oracle now uses the already verified current model
  selection, records a recoverable verification-failure sidecar after a selector
  break, blocks follow-up jobs, and returns `Erneut anmelden`; it does not erase
  the browser profile. Gemini tries one unchanged credential once and waits for
  a changed login handoff, while a previously successful provider can still
  restart after a crash. Seven ChatGPT and two focused Gemini tests pass.
- **P14 FERTIG - Startprüfung ohne Browserzwang - Test:** the app checks both
  Web-provider status endpoints once on startup. An installed unready provider
  opens only Backchannel's internal Connections tab; external login remains an
  explicit click. Nine provider-onboarding tests and the TypeScript/Vite
  production build pass.
- **Release note:** P11-P13 are source changes after the published EXE hash
  `8093284E...`. A new Python 3.12 staging build is therefore required after
  the remaining small fixes; the currently functional package stays in place
  until that candidate passes focused smokes.

## Checkpoint 2026-11-06 - targeted fixes packaged and verified

- **P16 FERTIG - Build - Test:** one clean Python 3.12 build completed after an
  overlapping incomplete staging directory was moved recoverably to
  `build/failed-overlap-20261106-202206`. Staged startup, embedded PostgreSQL,
  bundled local ASR, archive update and forced rollback smokes all passed; the
  verified candidate was then published atomically.
- **P11-P14 FERTIG - final source verification:** 21 focused backend tests,
  8 Gemini bridge tests and 11 focused frontend tests pass. The production
  frontend build also passed inside the release build.
- **P06 final runtime evidence:** `/api/ready` and `/api/health` return `ok`,
  local ASR reports usable, package PostgreSQL is alive, and the real
  `Debate AI` WinForms/WebView window was restored through the owner request
  and remained visible for 48 seconds without interaction. The hidden
  `.NET-BroadcastEventWindow` was not restored.
- **Provider evidence:** ChatGPT Web reports `gpt-6` / `xhigh` ready from the
  persisted verified session. Gemini Web is installed but reports no models;
  the unchanged rejected session is not retried in a browser loop. A real
  Gemini answer remains blocked on interactive re-login.
- **Final EXE:** 26,876,428 bytes, SHA-256
  `E8355E49F3639C9B39718B9643FA8668C63D078201E5E7764B1EC072A010423F`.
- **Still open by design:** per-session/live research frequency needs a schema
  contract; live dual-meter observation, a new real spoken transcript and a
  real Gemini response were not inferred from unit tests.

## Checkpoint 2026-11-06 - final GUI watchdog release

- **P17 FERTIG - GUI-Lebenszyklus - Test:** Ein weiter laufender
  WinForms/WebView-Prozess verlor nur sein sichtbares `Debate AI`-Fenster. Der
  Tray-Waechter stellt jetzt ausschliesslich solche versteckten, noch lebenden
  Hauptfenster wieder her. Minimieren bleibt unberuehrt; Schliessen beendet nur
  das UI-Kind. 46 fokussierte Launcher-Tests bestanden.
- **P18 FERTIG - finaler Build/Release - Test:** Frischer Python-3.12-OneDir-
  Kandidat, Bundle-Smoke (Ready, PostgreSQL, lokale ASR, sauberer Shutdown) und
  natives Windows-Archiv mit erzwungenem Rollback bestanden. Anschliessend
  atomar mit der vorhandenen Backup-/Rollback-Funktion veroeffentlicht.
- **Finale reale Abnahme:** Die `dist`-EXE zeigt das echte Hauptfenster und
  meldet `/api/ready=200`. ChatGPT Web meldet `gpt-6` / `xhigh` bereit; Gemini
  Web meldet `gemini-3.1-pro` und Pro-Verfuegbarkeit bereit. Keine neue
  kostenpflichtige Modellanfrage wurde erzwungen.
- **Finale Artefakte:** EXE 26,876,512 Bytes, SHA-256
  `3652AF94E7B2900F2C300C7ED6BA289B6CA34E5E32F3B7ADC9853C3EEA8A26A6`;
  internes Updater-ZIP 430,128,200 Bytes, SHA-256
  `AB6156E8E7ECB36ED1FA580382359CECF1A83F3028B7672F0A3B815EA5185F28`.
- **Offen, nicht ueberclaimt:** keine neue echte Web-Modellantwort, kein neues
  gesprochenes End-to-End-Gespraech mit beiden Pegeln und keine Umsetzung der
  sitzungsspezifischen Recherchefrequenz.


## Masterauftrag – 2026-11-14 – 001/A002

**Status: BEREITS ERLEDIGT (Quellcode); Fresh-Test BLOCKIERT durch GitHub-Runner.**

- **Aufgabe:** Nützliche lokale Sofortantwort während eines langen, noch laufenden Redebeitrags.
- **Nachweis der bestehenden Lösung:** backend/app/services/local_live_captioner.py dekodiert ein begrenztes rollierendes Fenster lokal und liefert ersetzbare Interim-Hypothesen (mode=replace) mit Segment-/Revisions-IDs. backend/app/services/agents/orchestrator.py übernimmt diese Hypothesen über feed_interim_transcript() in den lokalen Debate-Copilot und startet die Debattenrevision, ohne auf das finale Transkript zu warten.
- **Vorhandene Regressionen:** backend/tests/test_local_live_captioner.py prüft das rollierende Ersetzen und die Latenzgrenze; backend/tests/test_debate_copilot.py prüft test_live_partial_triggers_copilot_without_saving_duplicate_transcript, die 3-Sekunden-Latenzgrenze für kurze Interim-Texte und die laufende Revision während längerer Rede.
- **Fresh-Test-Ergebnis:** Die beiden aktuellen GitHub-Actions-Läufe für master bei f3321922e4c7ccdd47df253f4129162e6d3f6cd7 (Tests-Lauf 43632783683, Security-Lauf 43632783688) endeten mit failure; alle Jobs melden steps: null. Das ist laut Repository-Vertrag ein Runner-/Infrastrukturfehler und kein Testpass. Ein ausführbarer lokaler Windows-/Linux-Checkout steht in dieser Sitzung nicht zur Verfügung.
- **Eigener neuer Code:** keiner; der bestehende lokale Interim-Pfad erfüllt den Vertrag bereits.
- **Commit/Push:** Fortschrittsnachweis in diesem Commit auf master; kein Produktcode geändert.
- **Offener Abnahmeschritt:** Einen ausführbaren Checkout oder einen reparierten GitHub-Runner bereitstellen und mindestens python -m unittest backend/tests/test_local_live_captioner.py backend/tests/test_debate_copilot.py ausführen; danach den realen 30–60-Sekunden-Replay messen.

NÄCHSTER PUNKT: 002/A004

## Masterauftrag – 2026-11-14 – 002/A004

**Status: BEREITS ERLEDIGT (Quellcode); Fresh-Test BLOCKIERT durch GitHub-Runner.**

- **Aufgabe:** Verhindern, dass veraltete Generierungen aktuellere Claims sichtbar überschreiben.
- **Nachweis der bestehenden Lösung:** AgentOrchestrator führt Claim-, Transcript-, Recommendation- und Generation-IDs. _send_debate_update() verwirft einen explizit älteren Claim-/Transcript-Stand; _analysis_context_is_current() bindet Hintergrundresultate zusätzlich an Session, Claim, Revision, Directive-Revision und Config-Generation. _schedule_debate_revision() bricht vor dem ersten sichtbaren Partial veraltete Worker ab und coalesct nach einem sichtbaren Partial.
- **Vorhandene Regressionen:** backend/tests/test_debate_copilot.py deckt test_new_speech_cancels_stale_revision_and_runs_latest, test_final_negation_drops_slow_model_result_for_interim_claim, test_stale_revision_is_discarded_even_if_model_returns, test_server_rejects_explicitly_stale_live_update, test_stale_research_is_cached_without_broadcast und die Empfehlungsversionierung zwischen Instant- und Model-Card ab.
- **Eigener neuer Code:** keiner; die vorhandenen Claim-/Transcript-/Generation-Verträge erfüllen den Quellcode-Teil.
- **Fresh-Test-Ergebnis:** Nachweisbare aktuelle master-Actions für f3321922e4c7ccdd47df253f4129162e6d3f6cd7 (Tests 43632783683, Security 43632783688) endeten mit failure und steps: null. Das Repository klassifiziert dies als Runner-/Infrastrukturfehler; ein ausführbarer lokaler Checkout steht in dieser Sitzung nicht zur Verfügung.
- **Commit/Push:** Fortschrittsnachweis in diesem Commit auf master; kein Produktcode geändert.
- **Offener Abnahmeschritt:** Die fokussierten Backendtests in einem ausführbaren Checkout ausführen und zusätzlich ein deterministisches 30–60-Sekunden-Replay mit null Stale-Publishes aufzeichnen.

NÄCHSTER PUNKT: 003/A005