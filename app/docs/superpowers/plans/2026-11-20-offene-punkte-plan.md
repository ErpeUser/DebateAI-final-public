# Offene Punkte 2026-11-20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Alle lokal behebbaren Punkte aus `app/docs/OFFENE_PUNKTE.md` auf dem aktuellen `main`-Stand umsetzen, externe Gates mit frischem Evidence/Blocker abgleichen und den Standardbranch verifizieren/synchronisieren.

**Architecture:** Bestehende FastAPI/SQLAlchemy-, React/Vite- und Docs-Site-Verträge bleiben erhalten. Änderungen werden in begrenzten, rückwärtskompatiblen Schichten vorgenommen: query-/memory-budgets im Backend, idempotente Cleanup-/TTL-Lifecycle, reproduzierbare Analyse-/Evidence-Dokumentation und konsistente Produktclaims.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy/Alembic, unittest/pytest, React/Vite, Node test runner, Astro/Starlight, GitHub Actions.

**Spec:** `app/docs/OFFENE_PUNKTE.md` (aktueller Backlog; externe Operator-/Hardware-Gates bleiben als solche ausgewiesen).

## Global Constraints

- Direkte Arbeit auf `main`; kein Force-Push, kein History-Rewrite, kein Feature-Branch.
- Vor Pull/Push `python app/scripts/github_sync.py --pull --strict` ausführen; wenn CLI-Auth fehlt, GitHub-Connector/`git ls-remote` als getrennte Evidence dokumentieren.
- Keine Secrets, echten Providerdaten oder Produktionsartefakte in den Tree schreiben.
- Bestehende API-Kompatibilität und sichere Default-Limits beibehalten.

## Review Focus

- Große Chat-/Reveal-Payloads dürfen weder unkontrolliert im SQL-Query noch doppelt im Worker wachsen.
- Session-Löschung muss lokale, Browser- und externe Artefakte idempotent behandeln und Fehler sichtbar machen.
- Globale Journale/PII-Indizes dürfen nach TTL/LRU-Sweep nicht unbounded wachsen oder zulässiges Reconnect-Replay verlieren.
- Cursor-/Limit-Parameter müssen stabile Tie-Breaker und kompatible Defaults haben.
- Backlog-Status darf nur mit frischen Commit-/Test-/CI-/Device-Belegen aktualisiert werden.

### Task 1: Discovery, ledger und Evidence

**Files:**
- Create: `.superpowers/sdd/2026-11-20-offene-punkte/progress.md`
- Create: `docs/superpowers/plans/2026-11-20-offene-punkte-plan.md`
- Modify: `app/docs/OFFENE_PUNKTE.md`

- [ ] Vollständiges Ledger aller 37 `### P*`-Einträge mit `status_before`, `status_after`, `evidence_or_blocker` erstellen.
- [ ] Aktuellen lokalen SHA, Remote-Head, GitHub-Repo-Metadaten, Actions-Runs und Desktop-Gerät getrennt belegen.
- [ ] Nach jeder Changeset-/Test-/CI-Verifikation die passenden Statuszeilen und Header aktualisieren.

### Task 2: Backend query/memory budgets (P2.8, P2.10)

**Files:**
- Modify: `app/backend/app/routers/chat.py`
- Modify: `app/backend/app/routers/{sessions,transcripts,questions,knowledge,documents,directives,speakers}.py`
- Test: `app/backend/tests/test_chat_prompt.py`, passende Router-/Limit-Tests

- [ ] Failing tests für SQL-seitige Priorisierung, sichere Obergrenzen, stabile Cursor/Tie-Breaker und kontrollierte 413/Truncation schreiben.
- [ ] Implementieren und vollständige Backend-Regression ausführen.

### Task 3: Cleanup outbox/retry and lifecycle bounds (P1.14, P2.12)

**Files:**
- Modify: `app/backend/app/routers/sessions.py`
- Modify: `app/backend/app/services/{pii/vault.py,pii/redaction.py,transcription_jobs.py,ws_event_stream.py}`
- Create/Modify: migrations/models/tests as needed

- [ ] Failing tests für idempotente Provider-Delete-Outbox/Retry, Session-Cleanup, TTL/LRU und zulässiges Replay.
- [ ] Implementieren, ohne externe Provider zu erzwingen; Status/Audit muss sichtbar bleiben.

### Task 4: Migration and single-worker safety (P1.15, P1.16, P2.11)

**Files:**
- Modify: `app/backend/app/main.py`, `app/backend/scripts/start_backend.py`, request-guard tests/docs
- Test: startup/migration/request-guard suites

- [ ] Fehler-/Retry-Matrix für parallele Migrationen und LAN-Origin/Bind-Defaults ergänzen.
- [ ] Bestehende Single-worker-Verträge und Advisory-Lock-Logik explizit verifizieren.

### Task 5: Product claims, language contract, static-analysis baseline (P1.5, P2.4, P3.4)

**Files:**
- Modify: `app/site/index.html`, `app/docs/{configuration.md,VISION.md}`, runtime/seed/frontend copy as needed
- Create: `app/docs/static-analysis-baseline.md`, config/scripts/tests as needed

- [ ] Claims als lokal/cloud-gebunden/experimentell/ungeprüft markieren und Link-/Asset-Scan grün halten.
- [ ] Ein verbindlicher Sprach-/Provider-Default wird in Code, Seed, UI und Doku synchronisiert.
- [ ] Read-only Knip/deptry/dependency-cruiser Baseline mit expliziten Ausnahmen und Report erzeugen.

### Task 6: Verification and delivery

- [ ] Backend gezielte Tests plus vollständige verfügbare Suiten ausführen.
- [ ] Docs-Site `npm ci`, `npm test`, `npm run build`; Frontend `npm ci`, `npm test`, `npm run build` soweit verfügbar.
- [ ] Remote Actions exakt auf Ziel-SHA prüfen; Windows-Desktop-Smoke/Release-Gates mit echter Ausgabe durchführen, soweit Gerät/Signatur/Provider vorhanden.
- [ ] `github_sync.py --pull --strict` (oder Auth-Blocker) dokumentieren, committen, `git push origin main`, danach lokal/remote/origin-Refs und Clean-Status getrennt verifizieren.
