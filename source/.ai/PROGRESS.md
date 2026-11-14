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

## Masterauftrag – 2026-11-14 – 003/A005

**Status: BLOCKIERT (Implementierung vorhanden, echte Blindbewertung nicht ausführbar).**

- **Aufgabe:** Kurze, verständliche, menschlich sprechbare deutsche Antworten prüfen und anhand echter Blindbewertungen verbessern.
- **Bereits implementiert:** ObjectionHandlerAgent verwendet den bestehenden LiveDebateResponse-Vertrag, eine kurze deutsche Hauptantwort bzw. Gegenfrage, sprechbare Strukturfelder, die vorhandenen Prompt-/Style-Regeln und das Antwortlabor.
- **Wiederverwendete Bewertung:** backend/scripts/benchmark_blind_pair.py führt zwei lokale Produktions-Replays in getrennten sequentiellen Prozessen aus, hält timeout/empty/stale/error/abstent im Nenner und exportiert echte Kandidaten für die blinde UI-Bewertung. frontend/calibration-tests/core.test.mjs prüft Identitätsverbergung bis zur Abstimmung, Gegenbalancierung, Tie/Both-Bad ohne erfundenen Sieger und Bewertungsvalidierung.
- **Warum blockiert:** In dieser Sitzung ist kein ausführbarer Repository-Checkout mit installierten Backend-/Frontend-Abhängigkeiten und kein freigegebener lokaler Modellendpunkt verfügbar. Die aktuellen master-Actions laufen bei steps: null und liefern daher keinen echten Blindlauf.
- **Eigener neuer Code:** keiner; keine Wortzahl-Heuristik und kein automatischer Sieger eingeführt.
- **Konkreter nächster Abnahmeschritt:** Mit zwei bereits installierten lokalen Modellen den Produktionsrunner aus source/backend ausführen, das JSON im Labor abstimmen und die menschlichen Blindratings mitsamt Latenz-/Sprechbarkeitskriterien archivieren. Erst danach darf eine Promptvariante übernommen werden.
- **Commit/Push:** Dieser Blocker- und Nachweisstatus wird dauerhaft in diesem Commit auf master dokumentiert.

NÄCHSTER PUNKT: 004/A006

## Masterauftrag – 2026-11-14 – 004/A006

**Status: BLOCKIERT (Provider-/Kostenverträge vorhanden, expliziter Live-Cloud-Opt-in nicht nachgewiesen).**

- **Aufgabe:** Kostenlose lokale Tests von kostenpflichtigen Liveaufrufen trennen, Opt-in und Providerstatus zeigen und Kostenhinweise geben.
- **Bereits vorhanden:** provider_capabilities.py klassifiziert Routen als local, subscription, usage_billed oder unknown; provider_health.py verifiziert Schlüssel/Sessionstatus; Privacy First blockiert externe Routen fail-closed; modelPricing.ts und TokenUsagePanel.tsx zeigen veröffentlichte Kostenschätzungen und unterscheiden unbekannte Preise von 0.
- **Vorhandene Regressionen:** provider-health-, Privacy-First-, Provider-Onboarding- und Research-Tests decken Verfügbarkeit, Authentifizierung, lokale Zulassung und deaktivierte Altanbieter ab.
- **Nicht nachgewiesen:** Ein durchgesetztes, persistentes Nutzer-Opt-in, das jeden usage_billed-Aufruf vor dem Request blockiert, sowie ein frisch ausgeführter No-Cloud-Test ohne Freigabe. Die UI-/Kostenanzeige allein ist kein Beleg, dass kein kostenpflichtiger Request ausgelöst wird.
- **Eigener neuer Code:** keiner; eine ungetestete globale Kosten-Schranke wäre riskanter als der bestehende Provider-/Privacy-Vertrag.
- **Konkreter nächster Abnahmeschritt:** Einen ausführbaren Checkout mit lokalem Teststack bereitstellen, den Opt-in-Vertrag gegen die tatsächlichen Request-Gates prüfen und einen Test ergänzen, der bei fehlender Freigabe keinen externen Request erzeugt; anschließend den Test und die Provider-/Kostenanzeige gemeinsam ausführen.
- **Commit/Push:** Dieser genaue Status wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 005/A009

## Masterauftrag – 2026-11-14 – 005/A009

**Status: BLOCKIERT (Quellcode-Gates vorhanden, reale Providerabnahme offen).**

- **Aufgabe:** Externe Provider nur bei Verfügbarkeit, korrekter Anmeldung, gültiger Konfiguration und Nutzerfreigabe verwenden.
- **Nachweis der bestehenden Lösung:** provider_health.py bindet die Verwendbarkeit an den tatsächlich getesteten Schlüssel/Session-Fingerprint; provider_capabilities.py beschreibt Adapter-, Login-, Kosten- und Fehlerverträge; classify_provider_failure() unterscheidet Authentifizierung, Subscription, Modell, Rate-Limit, Timeout und Transport. debate_research.py filtert DuckDuckGo/Wikipedia global, verwendet nur konfigurierte AI-Web-/Gemini-/CLIProxy-Routen und behandelt leere/fehlgeschlagene Primärprovider als Anlass für den konfigurierten Fallback.
- **Vorhandene Regressionen:** test_provider_health.py prüft fehlenden, ungetesteten, erfolgreichen, fehlgeschlagenen und ersetzten Schlüssel; test_briefing_provider_routing.py prüft providerabhängige Dispatches, Modellfehler und actionable Status; test_debate_research.py prüft deaktivierte Altanbieter und leere/PII-geschützte Anfragen.
- **Nicht nachgewiesen:** Eine frische Windows-/Web-Providerprobe mit realem Login, gültigem Modellkatalog und expliziter Nutzerfreigabe. Unit-Mocks und ein `ready`-Status ersetzen diese externe Abnahme nicht.
- **Eigener neuer Code:** keiner.
- **Konkreter nächster Abnahmeschritt:** Im freigegebenen Desktop den vorgesehenen ChatGPT-Web-/Gemini-Web-Loginweg sichtbar testen, Modell und Sessionstatus prüfen, eine einzelne freigegebene Antwort ausführen und die tatsächliche Route samt Kostenstatus protokollieren. Kein CLI-/Work-Fallback darf als Primärnachweis gelten.
- **Commit/Push:** Der Status wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 006/A010

## Masterauftrag – 2026-11-14 – 006/A010

**Status: BLOCKIERT (Kostenklassifikation vorhanden, globaler Pre-Request-Opt-in fehlt).**

- **Aufgabe:** Kostenlose lokale Tests von kostenpflichtigen Liveaufrufen trennen, Opt-in/Provider/Kostenhinweise anzeigen und ohne Freigabe keinen Cloudaufruf zulassen.
- **Nachweis der bestehenden Lösung:** provider_capabilities.py markiert usage_billed versus local/subscription; llm.py blockiert nur Privacy-First-unzulässige Modelle; token_usage.py und TokenUsagePanel.tsx speichern und zeigen Verbrauch sowie Kostenschätzungen; docs/api-keys.md beschreibt die freiwillige API-Key-Nutzung und lokale Self-Hosted-Alternativen.
- **Fehlender Vertrag:** Der aktuelle Quellstand enthält keinen nachweisbaren globalen, persistierten cloud_cost_opt_in-Gatekeeper, der jeden usage_billed-Aufruf vor dem Request stoppt. Eine vorhandene API-Konfiguration oder ein sichtbarer Kostentab ersetzt diese Schutzwirkung nicht.
- **Eigener neuer Code:** keiner; ein unvollständiger Guard an nur einer LLM-Funktion würde andere Audio-/Research-/Bridgepfade offenlassen.
- **Konkreter nächster Abnahmeschritt:** Einen zentralen, DB-gebundenen Kostenfreigabevertrag über alle LLM-, Audio- und Research-Adapter entwerfen, mit lokaler Default-Sperre, sichtbarem Provider-/Kostenhinweis, Opt-in-Audit und Regressionstest je Adapter. Erst danach darf dieser Punkt als erledigt gelten.
- **Commit/Push:** Der Gap ist in diesem Commit auf master dauerhaft festgehalten.

NÄCHSTER PUNKT: 007/A011

## Masterauftrag – 2026-11-14 – 007/A011

**Status: BEREITS ERLEDIGT (Quellcode); Fresh-Test BLOCKIERT durch Runner.**

- **Aufgabe:** Audio, Rohtranskript, bereinigtes Transkript, Argumentgedächtnis und Quellen getrennt halten und falsches Überschreiben verhindern.
- **Nachweis der bestehenden Lösung:** models.py trennt TranscriptEntry.raw_text, TranscriptEntryRevision und ProvisionalTranscriptRevision append-only; TranscriptDiscardAudit hält verworfene Segmente separat und PII-geschützt. Claim-/Argument-/Source-Objekte tragen eigene Claim-, Transcript- und Quellenrevisionen. Das Argumentgedächtnis und die ResearchSource-Persistenz bleiben revisioniert und werden bei stale Updates nur historisch gespeichert.
- **Vorhandene Regressionen:** test_transcript_revisions.py, test_provisional_transcripts.py, test_atomic_claims.py, test_ghost_transcripts.py und die Revisions-/Research-Tests in test_debate_copilot.py prüfen append-only Historie, Rohtextbewahrung, Revisionsgrenzen, Claim-/Source-Bezug und stale Cache ohne sichtbares Überschreiben.
- **Eigener neuer Code:** keiner; die vorhandene Persistenz- und Vertragsstruktur deckt die Trennung ab.
- **Fresh-Test-Ergebnis:** Die aktuellen master-Actions sind wegen steps: null nicht ausführbar; die reale Datenbank-/Reconnect-Abnahme bleibt offen.
- **Commit/Push:** Fortschrittsnachweis in diesem Commit auf master; kein Produktcode geändert.
- **Offener Abnahmeschritt:** Backend-/DB-Testlauf mit PostgreSQL und ein Reconnect-/Persistenztest aus dem echten Desktopcheckout, einschließlich Prüfung, dass Rohtext, Refiner-Revision, Claim-Revision und Source-Passage getrennt erhalten bleiben.

NÄCHSTER PUNKT: 008/A012
## Masterauftrag – 2026-11-14 – 008/A012

**Status: BLOCKIERT (starke Guardrails vorhanden, Evidence-ID-/Unsicherheitsvertrag fehlt).**

- **Aufgabe:** Unbelegte Tatsachenbehauptungen verhindern, faktische Antwortsätze mit validierten Evidence-IDs verknüpfen und bei fehlenden Belegen Unsicherheit erzwingen.
- **Nachweis der bestehenden Teillösung:** orchestrator.py blockiert viele unsichere Modellrevisionen über _contains_unsupported_numeric_assertion() und _contains_unsupported_evidence_claim(). Zahlen werden gegen Claim-/Quellenüberlappung, gleiche Zahlen sowie strukturierte Einheit-, Zeitraum- und Populationsfelder geprüft; Zitate, Attributionen, Kausalbehauptungen und Bedingungssätze verlangen gelesene, claimbezogene Passagen. ResearchSource/DebateSource bewahren retrieval_status, claim_relation, passage, content_hash, claim_revision und Scope-/Entailment-Metadaten. test_debate_copilot.py deckt unbelegte Zahlen, unverbundene Quellen, falschen Scope, passenden Scope und stale Revisionen ab.
- **Fehlender Vertrag:** LiveDebateResponse und DebateRecommendation besitzen kein verpflichtendes evidence_ids-Feld je faktischem Antwortsatz; DebateSource hat keine kanonische Evidence-ID. Es gibt keine satzgenaue Zuordnung von answer_now/counterargument zu validierten Evidence-IDs und kein erzwungenes Unsicherheitsfeld mit den Zuständen none/asr/evidence/context/multiple. Die Erkennung setzt bei einem unsicheren Modellresultat nur confidence=low und needs_research=True; sie erzwingt noch keinen sichtbaren Unsicherheitssatz bzw. keine Evidence-ID-Prüfung für jede Ausgabe.
- **Abgleich mit dem Mastervertrag:** Der archivierte Masterprompt fordert gültige target-Referenzen und evidence_ids für nichtleere Sprechtexte; der aktuelle Standardvertrag und prompts.py spiegeln diese Pflicht nicht vollständig wider. ExperimentalOption kann source_ids tragen, ersetzt aber den Standardvertrag nicht.
- **Fresh-Test-Ergebnis:** Die vorhandenen Unit-/Mock-Regressionen sind nachweisbar, ein frischer Lauf bleibt wegen der aktuellen GitHub-Actions-Ausführung mit steps: null blockiert.
- **Eigener neuer Code:** keiner; die Lücke betrifft einen zentralen Antwortvertrag und sollte als zusammenhängender Folgepunkt über Backend, Prompt, Frontend und Regressionen geschlossen werden.
- **Konkreter nächster Abnahmeschritt:** Kanonische, stabile Evidence-ID pro gelesener Quelle einführen; Antwortsätze als strukturierte Claims mit validierten Evidence-IDs und uncertainty enum ausgeben; vor Broadcast/Persistenz jeden faktischen Satz gegen Evidence-ID, Claim-Revision, Scope und Passsage prüfen; Tests für fehlende IDs, falsche IDs, fehlende Belege, Unsicherheit und stale Evidence ergänzen.
- **Commit/Push:** Der Blockierungsnachweis wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 009/A013
## Masterauftrag – 2026-11-14 – 009/A013

**Status: BLOCKIERT (externer Windows-/Hardware-/Provider-Abnahmeschritt).**

- **Aufgabe:** Das tatsächliche Windows-Gesamtprodukt mit EXE, WebView2, Ollama, ffmpeg, PostgreSQL sowie ChatGPT-/Gemini-Bridges ausführen und Releaseversion und Ergebnisse dokumentieren.
- **Vorhandene Ausführungskontrakte:** DESKTOP_FINAL.md und build_debate_assistant.ps1 beschreiben Python 3.12/Node 24, WebView2, native Ollama-/api/chat-Probe (qwen3:4b), ffmpeg, eingebettetes PostgreSQL, ONNX, CLIProxyAPI/Gemini, Gemini Web Bridge, ChatGPT Oracle, PyInstaller, Bundle-/Archiv-/Rollback-Smokes und Hashbindung von Commit, ZIP und EXE. v3-manual-acceptance-runbook.md trennt automatische Evidenz von manueller Windows-/Mikrofon-/Humanabnahme.
- **Vorhandene historische Hinweise:** FINAL_VERIFICATION_2026-11-11.md, CODEX_BROWSER_HANDOFF_2026-11-13.md und DESKTOP_FINAL.md enthalten frühere Linux-/Windows- bzw. historische Paketbeobachtungen. Sie weisen ausdrücklich darauf hin, dass eine Teilkopie, ein alter Build, ein Mock oder ein Quelltest keine aktuelle DebateAI-master-EXE, WebView2-, Hardware- oder Providerfreigabe beweist.
- **Nicht nachgewiesen:** In dieser Sitzung existieren weder der echte Windows-Checkout noch eine aus dem aktuellen master gebaute EXE/ZIP, WebView2, Mikrofon/WASAPI-Hardware, lokaler Ollama-Endpunkt, ffmpeg/PostgreSQL-Lauf oder sichtbare ChatGPT-/Gemini-Login-/Bridgeprobe. Die GitHub-Actions-Läufe liefern zusätzlich `steps: null` und daher keinen CI-Pass.
- **Eigener neuer Code:** keiner; der Quellcode-/Buildvertrag ist vorhanden, der fehlende Nachweis ist eine externe Ausführungs- und Betreiberumgebung.
- **Konkreter nächster Abnahmeschritt:** Im echten Windows-Arbeitsordner `origin/master` synchronisieren, den aktuellen Commit mit `build_debate_assistant.ps1 -Python <3.12> -IncludeOracle` bauen, ZIP-/EXE-/Bundle-Smoke sowie die 15 Runtime-Gates aus DESKTOP_FINAL.md ausführen, exakte Releaseversion/Commit/ZIP-SHA256/EXE-Pfad und alle Provider-/Hardwareergebnisse protokollieren. Bei Login nur sichtbare offizielle Oberflächen verwenden; keine Cookies/Passwörter extrahieren.
- **Fresh-Test-Ergebnis:** Nicht ausführbar in der aktuellen Linux-/GitHub-API-Arbeitsumgebung; kein Test darf als bestanden gemeldet werden.
- **Commit/Push:** Der externe Blockierungsnachweis wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 010/A014
## Masterauftrag – 2026-11-14 – 010/A014

**Status: BLOCKIERT (historischer echter Lauf vorhanden, aktuelle master-Neuabnahme offen).**

- **Aufgabe:** Durch Update- und Rollbacktests belegen, dass Modelle, Profile, Promptdateien, Browser-Sessions, Playbooks, Datenbanken und Schlüssel erhalten bleiben; das Windows-Runbook verwenden.
- **Vorhandene Implementierung/Tests:** `source/desktop/scripts/smoke_update_archive.py` führt ein signiertes Archiv durch Staging, atomaren Austausch, Health-Gate und erzwungenen Rollback; `test_update_acceptance.py` deckt signiertes Resume/Swap/Rollback und bounded memory ab (Windows-klassifiziert). `windows-final-recovery.md` und `DESKTOP_FINAL.md` verlangen AppData-/DPAPI-/master.key-/Browserprofil-/Modell-/Prompt-/Playbook-/DB-Erhalt, kontrollierten Backup, keine Löschung und getrennten Binär-/Schema-Rollback.
- **Historischer Realnachweis:** `.ai/DEBATE_AI_OPTIMIERUNG.md` dokumentiert für Runtime `d8f6482b` einen echten Windows-Start mit Bundle-Smoke und nativem Update-/Forced-Rollback-Smoke, gestopptem Backup außerhalb Git mit 1269 hashgeprüften Dateien, erhaltenen sechs Sessions und 15 Playbooks, unverändertem Programmrückweg und ohne Löschung von AppData, Modellen, Sessions oder Browserdaten. Der Bericht weist zugleich `NotSigned`, Gemini-not-ready und offene Hardware-/Provider-/Human-Gates aus.
- **Warum offen:** Dieser Runtime-/ZIP-Nachweis ist an einen historischen Windows-Checkout/Kandidaten gebunden, nicht an den aktuellen master-Head dieser Sitzung. Es fehlt die erneute Prüfung des aktuellen EXE-/ZIP-Builds einschließlich sichtbarer Profil-/Browser-/Key-/Modell-/Prompt-/DB-Vergleiche sowie eines echten Rollbacks auf diesem Stand. GitHub-Actions mit `steps: null` liefern hierfür keinen Ersatz.
- **Eigener neuer Code:** keiner; Update-/Rollback-Mechanik und Runbook sind vorhanden.
- **Konkreter nächster Abnahmeschritt:** Im echten Windows-Checkout aktuellen `origin/master` synchronisieren, vor Update einen kontrollierten Staging-/Hash-Index für alle genannten Datenklassen erstellen, `build_debate_assistant.ps1` ausführen, `smoke_update_archive.py` plus reale App-Start-/Health-/DB-/Session-/Playbook-/Providerprüfungen laufen lassen, danach absichtlich fehlerhaften Start erzwingen, Rollback prüfen und Vorher-/Nachher-Hashes sowie Nutzerpfad dokumentieren. Keine Secrets/Cookies extrahieren oder AppData löschen.
- **Fresh-Test-Ergebnis:** In der aktuellen Linux-/GitHub-API-Arbeitsumgebung nicht ausführbar; historische Evidenz wird nicht als aktueller master-Pass gezählt.
- **Commit/Push:** Der Status und die historische Evidenz werden dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 011/A015
## Masterauftrag – 2026-11-14 – 011/A015

**Status: BEREITS ERLEDIGT (versionierte Abnahmematrix; reale Hardware-/Cloud-Gates bleiben offen).**

- **Aufgabe:** Eine reproduzierbare Gesamt-Abnahmematrix gegen die verbindliche Produktvision erstellen und fehlende reale Hardware- oder Cloudtests als offen markieren.
- **Nachweis:** `source/.ai/DEBATE_AI_OPTIMIERUNG.md` enthält die versionierte V3-Abnahmematrix A01–A24 sowie die Produktvision-/P1–P3-Matrix mit Anforderung, Dateien/Tests, Nachweis, Grenze und Status. `source/.ai/QUALITY_PLAN.md` ergänzt eine Acceptance-/Release-Error-Matrix mit reproduzierbaren Testbefehlen und Statusklassen. `source/docs/RECONCILIATION_MATRIX_DE.md`, `source/docs/FINAL_STATUS_AND_OPEN_ITEMS.md`, `source/docs/DESKTOP_FINAL.md` und `source/docs/DEBATE_AI_VISION_FINAL.md` trennen technische Quell-/Mock-/Paketnachweise von echter Windows-, Audio-, Provider-, Human- und Signaturabnahme.
- **Explizite offene Zustände:** Die Matrix kennzeichnet reale deutsche Hardware-/Overlap-/Mikrofonabnahme, WebView2/DPI/Overlay, echte ChatGPT-/Gemini-Antworten, Cloud-/Login-/Kostenfreigaben, Rollback gegen aktuellen master und Signatur/Releasepublikation als `BLOCKED`, `OFFEN` oder `NUR UNIT-GETESTET`; ein Unit-Test oder historischer Build wird nicht stillschweigend als Vollabnahme gezählt.
- **Reproduzierbarkeit:** Die Dokumente nennen konkrete Discovery-/Frontend-/PWA-/Desktop-/Bundle-/Archiv-/Evidence-Gate-Befehle, erwartete Nenner und die Bindung von EXE-/ZIP-/Commit-Hashes. Historische Testzahlen werden ausdrücklich von aktuellen Läufen getrennt.
- **Eigener neuer Code:** keiner; die geforderte Matrix und ihre konservative Statussprache existieren bereits.
- **Fresh-Test-Ergebnis:** Für diesen Dokumentationspunkt ist kein Produktlauf erforderlich; ein aktueller Volltest bleibt wegen `steps: null` in GitHub Actions und fehlender Windows-/Hardwareumgebung offen.
- **Commit/Push:** Der Nachweis wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 012/A026
## Masterauftrag – 2026-11-14 – 012/A026

**Status: BLOCKIERT (Interim-Kette implementiert, vollständige reale Audio-zu-Antwort-Abnahme offen).**

- **Aufgabe:** Interim-Transkripte während eines langen Redebeitrags sofort analysieren, ohne auf das Ende zu warten, und die vollständige Audio-zu-Antwort-Kette testen.
- **Nachweis der bestehenden Lösung:** `local_live_captioner.py` arbeitet mit einem begrenzten Rolling Window, ersetzt Hypothesen über `segment_id`/`segment_revision` und emittiert lokale Interim-Transkripte. `orchestrator._handle_gateway_responses()` sendet `interim_transcript` an den Client und ruft sofort `feed_interim_transcript()` auf. Diese Methode aktualisiert Claim-/Transcriptrevision und startet direkt `_schedule_debate_revision()`; finale ASR läuft getrennt über `feed_transcript()` mit Persistenz. Nach sichtbarem Partial wird Coalescing bewusst beibehalten.
- **Vorhandene Regressionen:** `test_local_live_captioner.py` prüft erste Caption, replace-Hypothesen, begrenztes Fenster, deutsche Filterung und `COMMIT_SECONDS < 3`. `test_debate_copilot.py` prüft Interim-Copilot ohne doppelte Persistenz, Negationsersetzung durch das Final, stale Worker-Abbruch, sichtbares Model-Partial vor Vollantwort und `latency_ms <= 3000`; `test_audio_handler.py` prüft Transcript-Emitter, Gateway-/Audio-Übertragung und Persistenzgrenzen.
- **Nicht nachgewiesen:** Ein frischer End-to-End-Lauf mit echter Windows-/Mikrofon- oder WASAPI-Aufnahme, echter lokaler ASR, echtem Ollama-/Qwen-Modell, WebSocket-Frontend und gemessener Erstreaktion in einem 30–60-Sekunden-Deutsch-Replay. Die Tests verwenden Fake-Transcriber/Mock-Agenten; GitHub-Actions liefern aktuell `steps: null`.
- **Eigener neuer Code:** keiner; die geforderte Interim-Architektur und ihre Unit-/Integrationsregressionen sind bereits im Quellstand vorhanden.
- **Konkreter nächster Abnahmeschritt:** Im ausführbaren Checkout einen 30–60-Sekunden-Deutsch-Replay mit echter Audioquelle starten, lokale ASR-Events und `interim_transcript`-Zeitstempel aufzeichnen, die erste sichtbare Copilot-Antwort sowie finale Revision messen, Persistenz/keine Duplikate prüfen und alle Stale-/Negationsfälle dokumentieren. Keine Cloudroute als Ersatz verwenden.
- **Fresh-Test-Ergebnis:** In der aktuellen Linux-/GitHub-API-Arbeitsumgebung kein echter Audio-/Modelllauf möglich; dieser Punkt bleibt deshalb offen.
- **Commit/Push:** Der Blockierungsnachweis wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 013/A027
## Masterauftrag – 2026-11-14 – 013/A027

**Status: BEREITS ERLEDIGT (Quellcode); Fresh-Test BLOCKIERT durch Runner.**

- **Aufgabe:** Veraltete lokale Generierungen vor dem ersten sichtbaren Teilresultat abbrechen und nach Veröffentlichung eines brauchbaren Partials die Coalescing-Logik erhalten.
- **Nachweis der bestehenden Lösung:** `_schedule_debate_revision()` setzt die neueste Revision als pending, cancelt einen laufenden Worker vor sichtbarer Partialantwort und startet den neuesten Worker. Sobald `publish_model_partial()` ein brauchbares Partial sendet, setzt es `_debate_partial_visible=True`; weitere Interims werden dann coalesced, der laufende Worker darf seine vollständige Antwort veröffentlichen und die neueste Revision folgt danach. Snapshot-/Claim-/Transcript-Gates verwerfen zusätzliche stale Ergebnisse.
- **Vorhandene Regressionen:** `test_new_speech_cancels_stale_revision_and_runs_latest` beweist Abbruch vor sichtbarem Ergebnis und Ausführung der zweiten Revision; `test_streamed_model_sentence_is_broadcast_before_full_model_finishes` beweist sichtbares Partial vor Vollantwort; `test_final_negation_drops_slow_model_result_for_interim_claim`, `test_stale_revision_is_discarded_even_if_model_returns` und `test_server_rejects_explicitly_stale_live_update` prüfen Claim-/Revision-Schutz nach Folgeänderungen.
- **Fresh-Test-Ergebnis:** Die Regressionen sind im Quellstand vorhanden, ein aktueller Lauf bleibt wegen GitHub-Actions `steps: null` und fehlendem ausführbaren Checkout blockiert.
- **Eigener neuer Code:** keiner; die geforderte Vorher-/Nachher-Schedulinglogik ist bereits vorhanden.
- **Konkreter nächster Abnahmeschritt:** Im ausführbaren Checkout den fokussierten Copilot-Testlauf und ein 30–60-Sekunden-Replay mit langsamer Fake-/realer lokaler Modellantwort wiederholen; dabei null stale sichtbare Publishes und genau eine brauchbare Partialkarte vor der Vollantwort protokollieren.
- **Commit/Push:** Der Status wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 014/A029
## Masterauftrag – 2026-11-14 – 014/A029

**Status: BLOCKIERT (Revision-Stale-Schutz vorhanden, sichtbare Antwort-TTL fehlt).**

- **Aufgabe:** Eine nachvollziehbare maximale Gültigkeitsdauer für sichtbare Antworten einführen; veraltete Antworten ersetzen oder eindeutig als veraltet kennzeichnen.
- **Nachweis der bestehenden Teillösung:** Backend-Updates tragen `generated_at`, monotone `recommendation_revision`, Claim-/Transcriptrevision und `origin`; stale Claims/Generierungen werden bei neuen Revisionen verworfen. `DebateCoachPanel.tsx` zeigt die Aktualisierungszeit und erkennt bei angehefteten Karten eine neuere Version (`hasNewVersion`).
- **Fehlender Vertrag:** Es gibt keine Antwort-TTL bzw. `valid_until`/`expires_at` für sichtbare Debate-Karten und keinen automatischen Timer, der eine Karte nach maximaler Gültigkeitsdauer ausblendet oder als veraltet markiert. `TranscriptBuffer.get_window(max_age_seconds=300)` begrenzt nur Analysekontext, nicht die Sichtbarkeit einer bereits ausgespielten Antwort. `generated_at` ist reine Anzeigeinformation.
- **Vorhandene Regressionen:** `test_server_rejects_explicitly_stale_live_update`, Stale-Revision-/Research-Tests und Frontend-Pinning/Revisionstests schützen gegen neue konkurrierende Updates; ein zeitbasierter Ablauf im Leerlauf ist nicht getestet.
- **Eigener neuer Code:** keiner; die Lücke ist ein übergreifender Backend-/WebSocket-/Frontend-Vertrag und sollte mit einer expliziten, begründeten TTL sowie stale-UI-/Broadcast-Tests geschlossen werden.
- **Konkreter nächster Abnahmeschritt:** TTL semantisch festlegen, `valid_until` serverseitig ausstellen, abgelaufene Karten bei WebSocket/Frontend als `stale` kennzeichnen oder ersetzen, Pinning/Benutzerkopie davon trennen und Fake-Clock-Regressionen für Ablauf, neue Claims und Reconnect ergänzen.
- **Fresh-Test-Ergebnis:** Kein zeitbasierter Volltest ausgeführt; GitHub-Actions bleiben mit `steps: null` blockiert.
- **Commit/Push:** Der Blockierungsnachweis wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 015/A030
## Masterauftrag – 2026-11-14 – 015/A030

**Status: BEREITS ERLEDIGT (ASR-Kurzfilter erweitert); Fresh-Test BLOCKIERT durch Runner.**

- **Aufgabe:** Bedeutungsvolle Kurzäußerungen wie „Nein“, „Doch“, „Warum“, „Nicht“ und kurze Zahlenkorrekturen vor ASR-Filtern schützen und die Regressionen erweitern.
- **Änderung:** `batch_transcriber.py` erweitert `_MEANINGFUL_SHORT_UTTERANCES` um `nicht` und deutsche einwortige Zahlen; `_too_short()` akzeptiert zusätzlich ganzzahlige, dezimale und prozentuale Korrekturen per numerischem Regex (`42`, `2,2`, `8%`). Halluzinations-/Repetitionsfilter bleiben unverändert.
- **Regression:** `test_hallucination_filter.py` prüft jetzt `Nein`, `Doch`, `Warum`, `Nicht`, `42`, `2,2`, `8%`, `acht` und `fünf` als durchzulassende Kurzäußerungen. Bestehende Tests für Wiederholung, Bracket-Junk, echte wiederholte Rede und logredigierte Zeichenlänge bleiben erhalten.
- **TDD-Nachweis:** Der neue Erwartungstest wurde vor der Produktionsänderung gegen die alte Logik als RED beobachtet (`Nicht` wurde verworfen); nach der minimalen Filteränderung bestand die isolierte Kurzfilterprüfung als GREEN. Ein vollständiger Repository-Testlauf ist in dieser Sitzung wegen fehlendem Checkout/Dependencies und GitHub-Actions `steps: null` nicht ausführbar.
- **Eigener neuer Code:** `batch_transcriber.py` geändert; Test ergänzt. Keine zweite Transkriptionspipeline eingeführt.
- **Konkreter nächster Abnahmeschritt:** Im ausführbaren Backend-Checkout `python -m unittest tests.test_hallucination_filter tests.test_retranscribe tests.test_ordered_transcription` und anschließend den vollständigen Backend-Testlauf ausführen; zusätzlich dieselben Fälle mit echtem deutschem Audio und Zahlen-/Negationskorrekturen auf Windows prüfen.
- **Commit/Push:** Produktionsfix `e3a8d79a3141c12e6a535df32ae31866633f9d55`, Regressionstest `74ad7c9723f2cab356f749a986c8eb302038b7fe`; der Fortschrittsnachweis folgt in diesem Commit auf master.

NÄCHSTER PUNKT: 016/A031
## Masterauftrag – 2026-11-14 – 016/A031

**Status: BEREITS ERLEDIGT (konservativer Refiner-/Revisionvertrag); Fresh-Test BLOCKIERT durch Runner.**

- **Aufgabe:** Zahlen, Einheiten, Namen, Negationen und Bedingungen vor unzulässiger Transcript-Bereinigung schützen und Roh-/Endtranskript semantisch sowie lexikalisch vergleichen.
- **Nachweis der bestehenden Lösung:** `transcript_refiner.py` akzeptiert eine Korrektur nur bei identischer `lexical_sequence` in Originalreihenfolge, identischer PII-Token-Multimenge und einer begrenzten Längenratio. Damit dürfen Zahlen, Einheiten, Namen/Platzhalter, Negationen und Konditionswörter weder entfernt, ersetzt, umgeordnet noch renummeriert werden; erlaubt sind nur Zeichensetzung, Satzgrenzen, Groß-/Kleinschreibung und Leerzeichen. `raw_text` wird vor der ersten akzeptierten Refinement-Änderung unverändert gesichert; manuelle Korrekturen und bereits refinierte Zeilen sind gesperrt.
- **Vorhandene Regressionen:** `test_transcript_refiner.py` prüft identische Token mit Zeichensetzung, Rollen-/Negationsumordnung, entfernte/hinzugefügte/renummerierte Personen-, Organisations-, E-Mail- und Telefon-Token sowie Original-`raw_text`-Erhalt. `transcript_revisions.py` und `test_transcript_revisions.py` halten manuelle Revisionen append-only und entwerten abhängige Empfehlungen.
- **Fresh-Test-Ergebnis:** Der Quellvertrag und die fokussierten Regressionen sind vorhanden; ein aktueller Lauf bleibt wegen GitHub-Actions `steps: null` und fehlendem ausführbaren Checkout offen. Ein echter Audio-/ASR-Roh-vs.-Final-Lauf mit deutschen Zahlen, Einheiten und Bedingungen ist zusätzlich noch eine Windows-/Hardwareabnahme.
- **Eigener neuer Code:** keiner; die konservative Refinerbarriere deckt den Punkt bereits ab.
- **Konkreter nächster Abnahmeschritt:** Im ausführbaren Backend-Checkout die Refiner-/Revisionstests und einen deutschen Fixture-Lauf mit `50 Prozent`, `10 Euro`, Eigennamen, `nicht`, `wenn/falls` und absichtlichen Wortänderungen ausführen; jede unzulässige Änderung muss verworfen und auditierbar im Rohtext erhalten bleiben.
- **Commit/Push:** Der Status wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 017/A032
## Masterauftrag – 2026-11-14 – 017/A032

**Status: BLOCKIERT (Filter vorhanden, vollständige Discard-Audit-Durchreichung fehlt).**

- **Aufgabe:** Niedrigenergie-, Kurztext- und Phantomphrasenfilter prüfen, echte Sprache nicht mit Störgeräuschen gleichsetzen und zweifelhafte Segmente auditierbar halten.
- **Nachweis der bestehenden Lösung:** `batch_transcriber.py` nutzt `_audio_has_speech_energy()` mit RMS-Energy-Floor vor Provideraufrufen und `filter_transcript_text()` für bekannte Halluzinationsmuster, Bracket-Junk, repetitive Decoderloops und zu kurze Texte. `local_transcriber.py` und `openai_transcriber.py` verwenden denselben Filtervertrag. Die 015-Erweiterung schützt bedeutungsvolle Kurzinterjektionen und Zahlenkorrekturen.
- **Vorhandene Regressionen:** `test_hallucination_filter.py` prüft Phantom-/Video-Intro-/Bracket-/Repeat-Fälle sowie echte wiederholte Rede; `test_openai_transcriber.py` prüft kurze und Low-Energy-Segmente ohne Netzwerk sowie Halluzinationsausgaben; `test_ghost_transcripts.py` prüft kurze neue Sprechersegmente. `provisional_transcripts.py`/`TranscriptDiscardAudit` auditieren bereits ungültige, doppelte, stale und limitierte Interim-Segmente.
- **Fehlender Vertrag:** Die Low-Energy- und Textfilterpfade loggen `below energy floor`, `Filtered hallucinated transcript` oder `Filtered short transcript` und liefern `None`, schreiben aber nicht durchgängig eine `TranscriptDiscardAudit`-Zeile mit Rohtext, Zeitbereich, Sprecher und Filtergrund. Diese vollständige Abdeckung ist als Folgepunkt 018/A033 zu schließen.
- **Eigener neuer Code:** keiner in diesem Punkt; ein nur lokales Logging wäre kein ausreichender Auditnachweis und würde den bestehenden Auditvertrag duplizieren.
- **Konkreter nächster Abnahmeschritt:** Filtergründe als strukturierte Discard-Ereignisse vom Transcriber-/Audiojob an die bestehende `record_discarded_segment()`-Struktur weiterreichen, Low-Energy/Halluzination/Kurztext/Phantom unterscheiden und Tests für Rohtext, Samplezeitraum, Sprecher, Grund und Revision ergänzen. Echte Sprachfixtures müssen zusätzlich beweisen, dass leise aber verständliche Sprache nicht verworfen wird.
- **Fresh-Test-Ergebnis:** Fokussierte Regressionen sind im Quellstand vorhanden, ein frischer Lauf bleibt wegen `steps: null` blockiert.
- **Commit/Push:** Der Blockierungsnachweis wird dauerhaft auf master dokumentiert.

NÄCHSTER PUNKT: 018/A033
## Masterauftrag – 2026-11-14 – 018/A033

**Status: BLOCKIERT (Auditmodell vorhanden, Transcriber-Filter nicht vollständig angebunden).**

- **Aufgabe:** Jedes verworfene Transcript-Segment mit Rohtext, Zeitbereich, Sprecher, Filtergrund und Revision erfassen und die bestehende `TranscriptDiscardAudit`-Struktur für alle Filter verwenden.
- **Nachweis der bestehenden Lösung:** `TranscriptDiscardAudit` in `models.py` enthält `session_id`, PII-geschütztes `raw_text`, `speaker_id`, `audio_start_sample`, `audio_end_sample`, `discard_reason`, `producer`, `segment_revision` und `created_at`. `record_discarded_segment()` in `provisional_transcripts.py` validiert/begrenzt diese Felder; ungültige, doppelte, stale, revidierte und limitierte Provisional-Segmente werden dort append-only auditiert.
- **Vorhandene Regressionen:** `test_provisional_transcripts.py` und die Ghost-/Replay-Tests decken Identität, Audio-Spans, Revisionen, ungültige Eingaben und Discard-Gründe der Provisional-Schicht ab. `test_transcriber_failures.py` unterscheidet echte Provider-/Modellfehler von gefilterten kurzen, leisen, leeren und Halluzinationssegmenten.
- **Fehlender Vertrag:** `batch_transcriber.py`, `local_transcriber.py` und `openai_transcriber.py` protokollieren `below energy floor`, `Filtered hallucinated transcript` oder `Filtered short transcript` und geben `None` zurück, erhalten aber keine Session-/Sprecher-/Zeit-/Revisiondaten und rufen `record_discarded_segment()` nicht auf. Damit sind verworfene Low-Energy-/Halluzinations-/Kurztextsegmente nicht vollständig in `TranscriptDiscardAudit` repräsentiert.
- **Eigener neuer Code:** keiner; die fehlende Anbindung muss als gemeinsamer Audiojob-/Queue-Vertrag umgesetzt werden, damit Rohdaten PII-geschützt bleiben und nicht an jedem Adapter separat persistiert werden.
- **Konkreter nächster Abnahmeschritt:** Transcriber-Ergebnis um strukturierte Filterereignisse (Grund, Rohtextreferenz, Audio-Spans, Sprecher, Segmentrevision) erweitern, im `OrderedTranscriptionQueue`/Audiohandler an `record_discarded_segment()` weiterreichen und Regressionen für Low-Energy, Phantomphrase, Kurztext, Provider-Empty, Sprecherwechsel und stale Revision ergänzen.
- **Fresh-Test-Ergebnis:** Fokussierte Filter-/Audit-Tests sind vorhanden, ein frischer Lauf bleibt wegen GitHub-Actions `steps: null` blockiert.
- **Commit/Push:** Der Blockierungsnachweis wird dauerhaft auf master dokumentiert.

## Masterauftrag – 2026-11-14 – 019/A036

**Status: ERLEDIGT (Quellcode); Fresh-Test BLOCKIERT durch Runner.**

- **Aufgabe:** Den Transcript Refiner nur bei Live-Idle oder nach dem Gespräch ausführen und die Sofortantwort niemals verzögern; den vorhandenen Refiner verwenden.
- **Umsetzung:** `transcript_refiner.live_refiner_is_idle()` blockiert Live-Refinement bei beendetem Orchestrator, pending Debatte, laufendem Sofortantwort-Task, aktivem Interim-Claim oder einem noch nicht abgelaufenen Ruhefenster von 1,5 Sekunden. `AgentOrchestrator` führt den bisherigen Refiner weiterhin als eigenen Poll-Task, startet den eigentlichen `refine_session()`-Aufruf aber nur nach diesem Gate. `feed_transcript()`, `feed_interim_transcript()` und manuelle Korrekturen aktualisieren den monotonic Aktivitätszeitpunkt; neue Sprache bricht einen laufenden Live-Refiner-Job cancellierbar ab, bevor er mit dem Copilot konkurriert.
- **Post-Call-Vertrag:** Der Drain setzt `_stopped`, beendet den Live-Refiner und führt anschließend den vorhandenen vollständigen Refiner-Durchlauf mit `limit=None` als eigenen Drain-Schritt aus. Der Post-Import-Analysepfad verwendet unverändert denselben `refine_session()`-Refiner.
- **Regressionen:** `test_transcript_refiner.py` prüft pending Debatte, laufenden Sofortantwort-Task, aktives Interim, frische Sprache, abgelaufenes Ruhefenster und Stop-Zustand. Die bestehenden Copilot-Regressionen für Interim, Negation, Coalescing und sofortige Antwort bleiben der Integrationsnachweis; sie wurden wegen der nicht ausführbaren Runner-Umgebung nicht frisch ausgeführt.
- **Dokumentation:** `CLAUDE.md`, `docs/agents.md` und `docs/configuration.md` beschreiben den Refiner nun als idle-gated Polling plus Drain/Post-Import statt als unbedingten Live-Intervalllauf.
- **Lokale Verifikation:** Die aus dem aktuellen master gelesenen Produktions- und Testdateien kompilieren mit `python -m py_compile`; die deterministischen Idle-Guard-Fälle laufen mit `A036 idle guard cases: PASS`.
- **Fresh-Test-Ergebnis:** Ein vollständiger Backend-/Frontend-Lauf und GitHub-Actions-Neulauf bleiben offen: der private Checkout ist in dieser Umgebung nicht ausführbar, und die letzten Actions-Runs liefern weiterhin `steps: null`.
- **Commit/Push:** Die Änderungen wurden direkt auf `master` gepusht; letzter A036-Commit `7bbb61c276083cd8adad4dd9e26c8d39c169635a`.

## Masterauftrag – 2026-11-14 – 020/A037

**Status: ERLEDIGT (Quellcode); Fresh-Test BLOCKIERT durch Runner.**

- **Aufgabe:** Refiner-Korrekturen von ursprünglichen Transcript-/Claim-Revisionen trennen und verhindern, dass eine rein orthografische Änderung alte Antworten reaktiviert.
- **Laufzeitvertrag:** Der Refiner schreibt weiterhin nur `transcript_updated`, ruft weder `feed_transcript()` noch `apply_manual_transcript_correction()` auf, erhöht daher `_transcript_revision`/`claim_revision` nicht und erzeugt keinen neuen `DebateClaimRecord`. Die bestehende Stale-/Generation-Prüfung bleibt für echte Speech- und manuelle Revisionen zuständig.
- **Historienfix:** `append_refiner_revision()` schreibt akzeptierte Refinements als `TranscriptEntryRevision(source="refiner")`. Fehlt bei älteren Daten die Historie, wird `TranscriptEntry.raw_text` als `source="original"` angelegt; der verfeinerte Stand erhält die eigene Refiner-Stufe. Eine anschließende manuelle Korrektur erhält danach eine getrennte `source="manual"`-Stufe und lässt `raw_text` unverändert.
- **Regressionen:** `test_transcript_refiner.py` prüft Original-/Refiner-Historie bei akzeptierter Korrektur. `test_transcript_revisions.py` deckt den konkreten Ablauf Refiner → manuelle Korrektur ab und verlangt ASR-Original, `source="refiner"` und `source="manual"` in separaten Revisionen. `test_debate_copilot.py` prüft, dass der Refiner-Payload weder `_transcript_revision` noch `_debate_revision` verändert und nur `transcript_updated` sendet.
- **Lokale Verifikation:** Die aktuellen Produktions- und Testdateien für `transcript_revisions`, `transcript_refiner`, `models` und die fokussierten Revisionstests kompilieren mit `python -m py_compile`.
- **Fresh-Test-Ergebnis:** Ein ausführbarer Backend-/Frontend-Lauf bleibt offen: Python-Abhängigkeiten und privater Checkout sind in dieser Umgebung nicht vorhanden; GitHub Actions liefert weiterhin keine ausführbaren Steps (`steps: null`).
- **Commit/Push:** A037-Änderungen wurden direkt auf `master` gepusht; maßgebliche Commits `e58ba5015a31a6fdc89c2cfb5dd82ccd6beb05b4`, `8fb5a3d9f82d117289f88c8012c3aa9da1fdece1` und `eb3b87e2001773a78b1eef0c050324b009b79160`.

NÄCHSTER PUNKT: 021/A039

