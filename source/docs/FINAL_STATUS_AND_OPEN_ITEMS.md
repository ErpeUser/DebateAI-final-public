# Finale Bestandsaufnahme und offene Arbeiten
Stand: 2026-11-10; Basis bei Sichtung: `master` = `a5ada5a51a16423be5f5027ac10a080e786ac738`. Dies ist ein **Evidenzregister**, kein pauschaler Fertigstellungsbericht.

## Aktueller Stand — 2026-11-12

Die Bestandsaufnahme darunter bleibt als historisches Evidenzregister für den
damaligen Stand erhalten. Die vollständige DebateAI-Identitätsumstellung und
die nachgelagerte Vertrags-Härtung sind in `master` enthalten:

- Identity-Decoupling-Merge: `fcdfc798f97f62f44768b242a9a039c8787bf6ea`.
- Post-Merge-Härtung: `d8cbb535881d9ef80bc35e6f5498d97dab174a2e`.
- Aktive Desktop-, Backend-, Frontend-, Docker-, Update- und Releasepfade
  verwenden die kanonischen DebateAI-Namen.
- Alte AppData-, PostgreSQL-, PII- und Browser-Schlüssel werden ausschließlich
  in isolierten, nicht destruktiven Migrationen gelesen; die PII-Migration ist
  idempotent und stoppt bei Entschlüsselungsfehlern oder Digest-Kollisionen.
- Die Produktions-Signaturprüfung verlangt eine explizite HTTPS-URL aus der
  Deployment-Konfiguration; es gibt keinen eingebetteten Hersteller- oder
  Download-Domain-Fallback.
- Der aktive Laufzeitscan schützt die Runtime-/Admin-/Download-/Buildpfade
  vor der Rückkehr alter Env-/Header-/Paket-/Archiv-/Domain-/DB-Bezeichner.
- Windows-Build, reale Audio-/ASR-Messung, Hardware-/DPI-/Rollback-Abnahme,
  Authenticode, reale Signatur-/DNS-Veröffentlichung und CI-Provisionierung
  bleiben externe Gates, bis frische Belege vorliegen. Die Push-Läufe des
  Merge-Commits endeten vor jedem Job-Schritt mit `steps: null`; daraus
  folgt kein grüner Testnachweis.

## Gesichtet: bestehende und bereits versionierte Fähigkeiten
- Desktop-/Windows-Launcher: WebView2, Tray, separates Always-on-top-Overlay, Laufzeitverwaltung für PostgreSQL/Ollama/Bridges; Dateiverweis `source/desktop/launcher.py`.
- Debate-Backend: `source/backend/app/services/agents/orchestrator.py`, `objection_handler.py` mit kurzem `answer_now`, `counter_question`, strategischem `primary_move`, Revisionen, lokalem Qwen-Pfad über native Ollama-API.
- Deutsche Prompt-/Rhetorik-Konfiguration: editierbare Ressourcen, lokale Benutzerkonfigurationspriorität, Playbook-/Provider-Dateien. Keine alten Defaults über echte lokale Benutzeranpassungen ausrollen.
- Lokale ASR-Angebote: Whisper Base, Whisper Large v3 Turbo, Parakeet v2/v3, experimentelle Parakeet-Live-Varianten und optional vorhandene weitere Backends; verfügbare konkrete Modelle zur Laufzeit feststellen. `LocalModelFitCard` misst **Geschwindigkeit** (RTF), nicht die inhaltliche Wortgenauigkeit.
- `source/frontend/src/hooks/useClipRecorder.ts` existiert; `LocalModelFitCard.tsx` bietet eine kurze Audioaufzeichnung für den Fit-Test, **noch keinen fertig veröffentlichten Wortgenauigkeitsvergleich**.
- Bestehende FastAPI-Diagnostik `source/backend/app/routers/diagnostics.py` bietet `/api/diagnostics/local-fit/asr`; derzeit keine verifizierte öffentliche separate Sprachlabor-/Blindvergleich-End-to-End-API.
- Frontendtest via `npm test` und `npm run build` vorgesehen; Backend- und Desktop-`unittest` sowie Windows-Bundle-/Archivsmokes dokumentiert.

## Wichtig: noch nicht auf master nachgewiesen
Die im Chat zuletzt angekündigten/teilweise vorbereiteten **Sprachlabor-, Antwortlabor- und Polling-/Recorder-Verbesserungen** sind beim Prüfen dieses Head **nicht als übernommener GitHub-Commit** verifiziert worden. Ein erzeugtes Git-Tree-Objekt oder einzelne lokale Fixture-Screenshots sind **keine Veröffentlichung, kein vollständiger Browser-/Hardwaretest und keine fertige Integration**. Wenn im Windows-Checkout oder einem Staging-/Codex-Branch tatsächlich entsprechende Dateien existieren, semantisch mit `origin/master` vergleichen und deren brauchbare Implementierung nach Tests übernehmen; sonst aus der Vision umsetzen.

## Nach Priorität verbleibend
### P0 – Synchronisation und Datenverlustschutz
- Tatsächlich bestehenden Windows-Arbeitsordner finden und auf **neuesten** `origin/master` bringen, lokale Abweichungen automatisch fachlich prüfen. Veraltetes verwerfen, einzigartige Erweiterungen integrieren, keine Nutzerdaten löschen. `source/scripts/sync_final_workspace.py` und Tests kontrollieren. Falls lokale Fixes noch nicht auf GitHub: nach Tests aufnehmen.
- Sicherstellen, dass User-AppData und ignorierte lokale Dateien auch bei Konflikten/Updates nicht versehentlich entfernt werden; Test für `git clean`-/ignored-/untracked-/Stash-Edge-Cases.
- Erst synchronisieren, **dann** aus genau diesem Commit bauen. Head, ZIP und tatsächlich startende EXE miteinander verknüpfen.

### P1 – Sprachlabor produktionsfähig
- In die bestehende Admin-Navigation integrieren; mobile und Windows-Desktop-Tastaturbedienung. Gerätesuche, Berechtigungen, Aufnahme, Stopp/Abbruch, Import, Wiederverwenden **derselben** Aufnahme.
- WER/Wortvergleich gegen editierbare Vorlage, Audio-Runtime/RTF, Modell-Verfügbarkeit und Fehlerstatus je Modell. Echte Modellantwort, keine vorgetäuschten Erfolgskarten. Deutschsprachige Testfälle und sichere Datei-/Dauer-/Formatlimits.
- Vorhandene `local-fit/asr`-Diagnostik möglichst **wiederverwenden** statt parallelen Transkriptionsstack einzuführen. Für WER fehlt der echte Modelltext im Fit-Contract; neue begrenzte, sichere Schnittstelle oder dediziertes read-only Testresultat benötigt.
- Labor darf keine aktive Live-Debatte beeinträchtigen: Abbruch, Busy/Queue-Gate, Modell-Warmup-/Download-Hinweis und Cleanup.

### P1 – Antwortlabor produktionsfähig
- Zwei Provider/Varianten, gleicher Promptkontext, anonymisiertes A/B, nachvollziehbarer Seed, blindes Vote, erst danach Reveal; strukturierte Latenz- und Sprechbarkeitskriterien.
- Testaufrufe nur explizit durch Nutzer, Privacy-First respektieren; Kosten und tatsächliche Verfügbarkeit vorher prüfen; keine unsichtbare Cloud-Ausführung.
- Sieger **niemals** automatisch als aktive Einstellung übernehmen. Export ohne Keys/PII, persistierte Testresultate nur nach ausdrücklicher Freigabe, Restore-/Undo-Pfad.

### P1 – Tests und Stabilitätsreparaturen
- Recorder-Races: Permission-Auflösung nach Navigation, MediaRecorder-Konstruktorfehler, leerer Clip, onerror, Gerätewechsel, Stop während Start; Tests reproduzierbar.
- Overlay: höchstens eine gleichzeitige Snapshot-Anfrage; verschwundene Fenster/hidden Tabs; bei kurzem API-Ausfall letzte gültige Antwort sichtbar **mit Warnung**, nicht leere Karte; Copy-Fehler behandeln.
- Diagnostik: ASR-Upload derzeit `await file.read()` ohne explizites Größenlimit und direktes `convert_to_pcm16` im async Endpunkt (Stand `a5ada5`); Limit, bounded decode, `asyncio.to_thread`, aktive Aufnahme-Schonung, Regressionstests.
- Veraltete Korrekturen, Wechsel von Gespräch/Modus/Provider, unvollständiges Streaming-JSON, Stop/Cancel und verlorener Backend-Start gezielt mit echten Assertions prüfen.
- Frontend-Suite, TypeScript-Build, Backend-`unittest`, Desktop-`unittest`, Build-/Bundle-Smokes und ggf. Projekt-Structure-Gates durchführen; bei Fehlschlägen Ursache vor Fix bestimmen.

### P2 – Realwelt-/Release-Abnahme auf Windows
- Mikrofon + WASAPI/Systemaudio auf echter Hardware; lokale Qwen-/Ollama-Inferenz und verfügbare ASR-Modelle; Bedienung des eingebauten Labors und vollständiger Debattenfluss.
- Bestehende ChatGPT-/Gemini-Browser-Loginwege nur über offizielle sichtbare Loginoberflächen testen; keine Cookie-/Token-Extraktion. Provider-Kosten/Verfügbarkeit nicht aus einem Mock als bestätigt melden.
- Windows-Build gemäß `source/docs/DESKTOP_FINAL.md`: portable Node24, Oracle, CLIProxyAPI/Gemini-Plugin, Gemini Web Bridge, ffmpeg, ONNX, PostgreSQL, Bundle-Smoke, ZIP-Prüfung, Start und sicheren Austausch der Programmdateien. AppData erhalten.
- GitHub-Actions-Status neu prüfen. Frühere Jobs auf `master` hatten keine ausgeführten Schritte (`steps:null`), daher kein CI-Pass. Infrastrukturfehler von reproduzierbaren Codefehlern trennen.
- Authenticode-Signierung/öffentliche Releasefreigabe bleiben extern blockiert, solange echtes Distributorzertifikat/Freigabe fehlt.

## Abnahmebericht Pflicht
Pro Bereich `bestanden` / `fehlgeschlagen` / `nicht ausführbar`, genaue Befehle, Testanzahl, Commit, ZIP-Pfad+SHA256, installierter EXE-Pfad, Log-/Fehlerhinweis. Keine falschen Aussagen über erfolgreichen Test oder aktuelle Produktivinstallation.


## Additive implementation delta – 2026-11-11

- `app/services/response_contract.py` now validates deterministic replay and
  laboratory event invariants without changing the live orchestrator or adding
  a database migration.
- `benchmark_blind_pair.py` validates each candidate record at the export
  boundary and keeps timeout, empty, stale and error outcomes in the denominator.
- `tests.yml` and `security.yml` expose `workflow_dispatch` for explicit
  reruns; a run with `steps: []` remains an Actions infrastructure blocker.
- The native Windows, A06/A18/A21/A22, update/rollback and human-review gates
  remain open until their real evidence is produced.
- Historical Backchannel file, EXE and AppData names are retained only as
  migration inputs or evidence records. The active branch uses DebateAI names;
  migration remains non-destructive and historical documentation is retained
  when it is referenced by an audit or integrity contract.
