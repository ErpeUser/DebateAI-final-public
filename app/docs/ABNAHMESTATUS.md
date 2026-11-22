# Abnahmestatus

**Stand:** 22.11.2026  
**Gesamtstatus:** `PARTIAL_VERIFICATION`

`DONE` ist nicht zulässig. Das Structure-Gate bleibt wegen bestehender
absoluter Sentrux-Regeln rot. Die Quality-Lab-Verbindungen, die Rating-
Grenzfälle, die UI-Vertragskorrektur, die PR-Bereinigung und die lokale
Persistenz der Laborrunden sind dagegen auf dem lokalen Integrationsstand
verifiziert.

## Repository, Branch und Synchronisierung

| Nachweis | Ergebnis |
|---|---|
| Repository | `ErpeUser/DebateAI-final-public` |
| Arbeitsbranch | `main` |
| Remote-Stand vor dieser Integration | `4ff69c4` |
| PR-Commit | `71042c1` – geprüfter Cherry-Pick von PR #1 |
| Kompatibilitätsfix | `4ff69c4` – `pytest-asyncio==1.5.0` für `pytest==9.0.3` |
| Lokaler Integrationsstand | `084096d` – persistente Quality-Lab-Runs und Ratings |
| Veröffentlichter SHA nach Docs-Site-Korrektur | `0720607` |
| Lokaler Arbeitsbaum | sauber vor der Dokumentationsänderung |
| PR #1 | geschlossen als superseded nach kompatibler Integration |
| Dependabot-Branch | entfernt |
| Offene Nicht-`main`-Branches | keine |
| Offene Pull Requests | keine |
| Strict-Sync | zuletzt erfolgreich, Exit-Code 0 |

Die ursprüngliche Dependabot-Änderung wurde nicht blind gemergt. Die
Paketauflösung zeigte, dass `pytest-asyncio==0.25.3` `pytest<9` verlangt.
Der kompatible Teststand hebt `pytest-asyncio` auf 1.5.0 an.

## Verifizierte Änderungen

### Quality Lab

- `/api/quality-lab/runs`, Ratings, Apply und Rollback bleiben registriert.
- Runs und Ratings werden in `quality_lab_runs` persistiert.
- Die Migration `034_quality_lab_runs` ist retry-idempotent.
- Eine Runde bleibt nach dem Leeren des Prozesscaches und in einer neuen
  Datenbanksession verfügbar.
- Holdout bleibt bis zu einem echten versionierten Datensatz unverifiziert.
- Apply und Rollback bleiben bis zu einer kontrollierten Prompt-Evaluation
  fail-closed.

### Vision-Abgleich

Die Vision wurde auf den Stand 22.11.2026 aktualisiert und um einen Abschnitt
zu Infrastruktur-Abnahme, gemeinsamem Zustand, CI-/Cloud-/Release-Nachweisen
und Statusregeln erweitert. Die Vision beschreibt Zielverhalten. Sie hebt
keinen offenen externen Nachweis automatisch auf `VERIFIED`.

## Test- und Qualitätsnachweise

| Prüfung | Ergebnis | Geltungsbereich |
|---|---|---|
| Quality-Lab-Contract und Persistenz | 9/9 bestanden | lokale SQLite-/Mock-Abnahme |
| SQLite-Migrationsmatrix | 3/3 bestanden | frische, Legacy- und Retry-Pfade |
| Backend-Compileall | bestanden | `app/backend/app` und `app/backend/tests` |
| Repository-Layout | 1106 Dateien, `Repository layout OK` | lokaler Checkout |
| `git diff --check` | bestanden | lokaler Diff |
| Runtime Health | HTTP 200, `{"status":"ok"}` | laufendes Windows-Bundle |

### GitHub-Actions auf `0720607`

| Workflow | Run | Ergebnis |
|---|---:|---|
| Tests | [45015260211](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45015260211) | `success` – backend, frontend, workspace-windows, postgres-boundaries und calibration-browser grün |
| Security | [45015260255](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45015260255) | `success` |
| Docs-Site | [45015260258](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45015260258) | `success` |
| Structure | [45015260168](https://github.com/ErpeUser/DebateAI-final-public/actions/runs/45015260168) | `failure` wegen bestehender `max_cc`, `max_fn_lines` und `max_file_lines`-Findings; Quality 6127 |

Ein früherer kompletter Backend-Lauf bestand mit 2246 Tests und 12 Skips,
wies aber zwei unabhängige Baseline-/Umgebungsfälle auf. Diese bleiben als
separate offene Tests dokumentiert und wurden nicht durch Statusänderungen
versteckt.

## Weiterhin offene Gates

- Sentrux-Structure mit sechs `max_cc`-, fünf `max_fn_lines`- und acht
  `max_file_lines`-Befunden.
- Gemeinsamer WebSocket-/Transkriptions-/PII-State über echte Workergrenzen.
- Versionierter Holdout-Datensatz und unabhängige Human-Ratings.
- Vollständige Cloud-Testinstanz mit Replay, Messung und secretbereinigten
  Bugberichten.
- Frischer signierter Windows-Build mit Artefakt-Hash, Update und Rollback.
- Autorisierte echte Audio-, Provider-, LAN- und DNS-Rebinding-Abnahme.
- Frische GitHub-Actions-Nachweise auf dem endgültigen Veröffentlichungs-SHA.

Diese Punkte bleiben `PARTIAL`, `EXTERNAL_BLOCKED` oder `UNVERIFIED`, bis der
jeweilige technische oder externe Nachweis auf demselben Commit vorliegt.
