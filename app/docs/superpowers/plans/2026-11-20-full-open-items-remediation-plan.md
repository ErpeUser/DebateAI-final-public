# Full Open-Items Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Each task is test-first and ends with fresh verification.

**Goal:** Implement every repository-local, reproducible item in `app/docs/OFFENE_PUNKTE.md`, record external gates that require unavailable credentials/hardware, and leave `main` synchronized locally and remotely.

**Architecture:** Prefer existing contracts and smallest compatible fixes. Group changes by subsystem: docs/site, security/startup, PII/data lifecycle, cross-worker state, API limits/performance, UX/accessibility, CI/release contracts, and evaluation tooling. External operator gates remain explicit blockers rather than fabricated passes.

**Tech Stack:** Python 3.12, FastAPI/SQLAlchemy/Alembic, React/TypeScript, Node test runners/Astro, GitHub Actions, existing PowerShell and repository guard scripts.

**Spec:** `app/docs/OFFENE_PUNKTE.md`, `app/docs/VISION.md`, `AGENTS.md`, and the current repository tests/workflows.

## Global Constraints

- Work directly on `main`; never force-push, rewrite history, or create a PR.
- Preserve `.ai`, `runtime/DebateAI/_internal`, Generated/private-data boundaries, lockfiles, and secrets.
- Do not install new tools or dependencies; use existing packages, scripts, lockfiles, and available CI/remote-device capabilities.
- Every behavior change gets a failing regression test before implementation.
- No claim of signing, hardware, provider, private-ledger, human-rating, or GitHub-billing completion without the required external evidence.
- Update `OFFENE_PUNKTE.md` only after implementation evidence exists; preserve IDs and history.

## Review Focus

- Missing docs paths and stale `master/source` references must fail tests before the docs/site fix.
- Non-loopback API access without an explicit token must remain denied while loopback development remains usable.
- Session deletion must remove remote/local/browser artifacts and PII indexes without breaking retries or reconnect replay.
- Multi-session PII must never use only the first session's roster.
- Cross-worker WS/REST state, pagination limits, migration races, and large reveal bodies must have bounded behavior.
- Standard debate output must preserve turn/revision identity and stale-result handling.

## Tasks

### Task 1: Docs-site and active repository contract

**Files:** `app/docs-site/site.test.js`, `sync-docs.mjs`, `assemble.mjs`, `astro.config.mjs`, active README/docs/site/release references, targeted docs tests.

**Acceptance:** existing docs-site tests and build pass; only existing docs are linked; repository/branch/layout references use `ErpeUser/DebateAI-final-public`, `main`, and `app`; historical examples are labeled.

### Task 2: Startup, LAN-origin, and release branch contracts

**Files:** `app/backend/scripts/start_backend.py`, request guard tests, `app/backend/app/services/request_guard.py` if needed, GPU/quickstart scripts, `app/scripts/release_desktop.ps1`, PowerShell contract tests.

**Acceptance:** default native/GPU start is loopback or token-protected, reload is explicit development-only, foreign private origin without token gets 403, release scripts are branch-aware for `main`.

### Task 3: PII scope and deletion lifecycle

**Files:** chat router/shield/vault/redaction, session/document deletion routers, frontend MeetingChat/App, backend/frontend tests.

**Acceptance:** multi-session protection unions the selected sessions, session deletion is idempotent and queues remote cleanup, local files and sessionStorage are cleared, and global PII indexes have bounded session-aware lifecycle.

### Task 4: Cross-worker state and migration serialization

**Files:** orchestrator/event journal/transcription job registries, migration startup path, integration tests.

**Acceptance:** either shared state or an explicit single-worker/sticky contract is enforced; concurrent startup tests produce one migration head without duplicate/lock errors.

### Task 5: API pagination and bounded chat/reveal processing

**Files:** list routers, schemas, frontend session hook, chat prompt/reveal middleware, API/performance tests.

**Acceptance:** stable limit/cursor defaults protect sessions, transcripts, questions, directives, documents, speakers, and knowledge; prompt/reveal paths have bounded memory and deterministic truncation/413 behavior.

### Task 6: Accessibility and standard debate experience

**Files:** `PiiShieldCard.tsx`, `ConfirmProvider.tsx`, `DebateOverlay.tsx`, live-role orchestration/settings, frontend/backend tests.

**Acceptance:** named controls and focus trap/restore pass DOM/a11y tests; standard mode provides three current alternatives and live strategic signals with revision identity.

### Task 7: CI, dependency baseline, PostgreSQL, and structural gates

**Files:** `.github/workflows/tests.yml`, `structure.yml`, requirements/package manifests only when existing lockfiles support it, CI contract tests/docs.

**Acceptance:** PostgreSQL tests run in a visible job without skip; Sentrux policy distinguishes approved baseline from new violations; reload default and dependency/static-analysis baseline are documented and tested.

### Task 8: Audio race, diagnostics, and evaluation paths

**Files:** audio pipeline, diagnostics/AdminPanel, calibration/A-B UI where existing APIs support it, tests.

**Acceptance:** simultaneous WS/native completions do not drop native data; diagnostics export is redacted; existing calibration API has a documented, reproducible user path or remains explicitly blocked.

### Task 9: External-only gates and final ledger

**Files:** `app/docs/OFFENE_PUNKTE.md` for current gaps and `app/docs/HISTORIE.md` for dated evidence only after evidence.

**Acceptance:** mark only verifiable local items complete; preserve explicit blockers for signing, hardware/provider, private ledger, human ratings, billing, separate repositories, and operator cutover. Run full available test matrix, layout/source guards, review diff, commit to `main`, push through the authorized GitHub write path, and fast-forward the local checkout.
