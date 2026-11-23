# Abnahmestatus

**Stand:** 23.11.2026
**Gesamtstatus:** `PARTIAL_VERIFICATION`

`DONE` bleibt unzulässig. Tests und Security sind auf dem aktuellen `main`-SHA grün. Das Structure-Gate bleibt wegen geerbter absoluter Sentrux-Regeln rot. Quality-Lab-Apply/Rollback, der versionierte Holdout-Katalog und der DB-basierte WebSocket-Replay sind implementiert und lokal verifiziert. Externe Windows-, Audio-, Provider-, LAN- und Release-Nachweise bleiben offen.

## Repository, Branch, PR und Synchronisierung

| Nachweis | Ergebnis |
|---|---|
| Repository | `ErpeUser/DebateAI-final-public` |
| Branch | `main` |
| Aktueller Remote-/lokaler SHA | `775815aeb81decea6dd56be2f058678c9a57348a` |
| Verhaltensändernder Commit | `775815a` – kontrollierte Prompt-Evaluierung mit Apply/Rollback und UI-Vertrag |
| Vorherige Produkt-Commits | `82c2703` Holdout-Katalog, `fdf10b7` Shared-Session-State, `08b7698` Testbarkeit und Cleanup |
| PR #1 | geschlossen als superseded nach geprüftem Cherry-Pick |
| Dependabot-Branch | entfernt |
| Offene Nicht-`main`-Branches | keine |
| Offene Pull Requests | keine |
| Strict-Sync | `python app/scripts/github_sync.py --pull --strict`, Exit-Code 0 |
| Arbeitsbaum | sauber nach Dokumentationscommit |

Die PR-Änderung wurde nicht blind übernommen. `pytest==9.0.3` wird mit `pytest-asyncio==1.5.0` betrieben, weil die vorherige `pytest-asyncio==0.25.3`-Vorgabe pytest 9 nicht unterstützt.

## Implementierte Änderungen

### Kontrollierte Prompt-Evaluierung

- `QualityLabRunRequest` akzeptiert einen validierten Promptnamen und zwei vollständige Promptvarianten.
- Der Holdout-Katalog `de-debate-holdout-v1` liefert drei versionierte Fälle. Ein ausgewählter Katalogfall setzt `holdout_verified=true` und überschreibt freie Claims mit dem unveränderlichen Kataloginhalt.
- Runs und Ratings bleiben in `quality_lab_runs` persistent.
- `can_apply` wird erst nach verifiziertem Holdout, vollständiger Bewertung, bevorzugter Seite, zwei geeigneten Antworten und zwei Promptvarianten wahr.
- Apply ruft `PromptOptimizationStore.apply` mit gemappten Human-Rating-Metriken und ausdrücklicher Nutzerfreigabe auf. Rejected Decisions werden als `409` sichtbar.
- Rollback ruft `PromptOptimizationStore.rollback` auf und aktualisiert den persistenten Laufstatus.
- Die UI kann Holdout-Fall, Promptnamen und Varianten erfassen und aktualisiert Apply-/Rollback-Zustände nach dem Serverergebnis.

### Gemeinsamer Multiworker-State

- `SharedSessionState` und Migration `035_shared_session_state` speichern aktive Generationen und Replay-Snapshots in der Datenbank.
- `RevealingWebSocket.create` hydratisiert den Zustand vor dem Upgrade und persistiert Snapshot-/Close-Ereignisse.
- Stale Generationen werden beim Öffnen, Speichern und Schließen abgewiesen.
- Transkriptionsjobs und PII-Indizes bleiben prozesslokal. Ein vollständiger gemeinsamer Job-/PII-Adapter ist ein offener Punkt.

### Structure-Gate

Der aktuelle Lauf [45120718086](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45120718086) ist rot. Die unveränderten Befunde sind sechs `max_cc`-, fünf `max_fn_lines`- und acht `max_file_lines`-Verstöße, unter anderem in `orchestrator.py`, `audio_pipeline.py`, `capture.mjs`, `useWebSocket.ts`, `useAudioCapture.ts`, großen Dokumenten und generierten Manifests. Die Gate-Regel wurde nicht abgeschwächt und keine Datei wurde allowlisted. Der Vergleich meldet keine neue Verschlechterung durch die Quality-Lab- oder Shared-State-Änderungen.

## Verifikation auf aktuellem SHA

| Prüfung | Ergebnis |
|---|---|
| Backend Quality-Lab | `12 passed` |
| Shared-State-Tests | bestanden |
| SQLite-Migrationsmatrix | `3/3` |
| Frontend-Gesamtsuite | `386/386` |
| Frontend-Produktionsbuild | erfolgreich, 2146 Module |
| Python-Compileall | bestanden |
| `git diff --check` | bestanden |
| GitHub Tests | [45120718051](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45120718051), `success` |
| GitHub Security | [45120718251](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45120718251), `success` |
| GitHub Structure | [45120718086](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45120718086), `failure` wegen bestehender absoluter Regeln |

## Offene Punkte nach dem Vision-Abgleich

| Priorität | Punkt | Aktueller Zustand |
|---|---|---|
| P0 | Structure-Gesamtgate | Refactor der sechs komplexen, fünf überlangen Funktionen und der acht großen Dateien fehlt. |
| P0 | Signiertes Windows-Release | Authenticode/Zertifikatskette, frischer Installer, Update und Rollback fehlen. |
| P0 | Reale Windows-/Audio-/Provider-Abnahme | Current-SHA-Desktoplauf, echte Aufnahme, ASR-WER/CER/RTF und Providerkosten fehlen. |
| P1 | Unabhängiger Human-Rating-Holdout | Der Katalog ist versioniert und technisch gebunden. Unabhängige Bewertung und produktive Freigabe fehlen. |
| P1 | Multiworker | WebSocket-Replay ist DB-geteilt. Jobstatus, PII-Indizes und Zwei-Worker-Produktionslauf fehlen. |
| P1 | LAN-/Proxy-/DNS-Rebinding | Lokale Guard-Tests bestehen. Der autorisierte reale Netzwerktest fehlt. |
| P2 | Cursor-Last | Lokale Cursorverträge bestehen. Zwei-Worker-Replay und 10.000-Einträge-Last fehlen. |
| P2 | Reproduzierbare Gesamtbuilds | Docs-Site ist reproduzierbar. Vollständige Linux-/Windows-Toolchain-, Lizenz- und Artefakt-Hashes fehlen. |
| P2 | jscpd-Duplikatsschuld | Die bestehende Duplikatsschuld ist noch nicht gezielt abgebaut. |

Diese Punkte sind im [Vision-Ledger](VISION_LEDGER.md) und in [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md) mit Owner, Evidenzmodus und nächstem Nachweis geführt. Historische SHA- und Run-Belege bleiben in `HISTORIE.md`; aktuelle Matrixzeilen verwenden den SHA `775815a` und die aktuellen Tests-/Security-/Structure-Runs.
