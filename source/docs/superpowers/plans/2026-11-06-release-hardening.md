# Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden revision propagation, schema adoption, reconnect behavior, desktop visibility, and OpenAI login, then produce a smoke-tested Windows x64 one-dir bundle and ZIP.

**Architecture:** Keep the existing orchestrator, Alembic startup, replay journal, and React hook. Add only guards and pure decision helpers at the existing boundaries.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy/Alembic, React/TypeScript, stdlib unittest, Node test runner, PyInstaller, PowerShell.

**Spec:** `docs/superpowers/specs/2026-11-06-release-hardening-design.md`

## Global Constraints

- Preserve user data, settings, secrets, current dirty source changes, and the previous working `dist` release until staged smokes pass.
- No privacy-first/privacy round, RL tests, broad architecture change, large refactor, full test suite, publication, or signing.
- Use failing regression tests before each product change.

## Review Focus

- A corrected claim using the same query must not inherit the cached result's old claim text.
- Older research finishing after a corrected revision must not overwrite newer topic knowledge or a newer visible answer.
- An empty database must execute migrations; an existing unversioned database must be adopted without replaying historical migrations.
- Visibility changes must not replace a healthy OPEN or CONNECTING socket.
- A WebView child without a visible top-level window must fall back to a visible system browser instead of being reported as successfully opened.
- The OpenAI OAuth page must be reserved from the original click and navigated when the authorization URL arrives; popup blocking must retain the manual link.
- Failed staged build or smoke must leave the previous `dist` artifacts available.

---

### Task 1: Revision-safe research and live delivery

**Files:** Modify `backend/app/services/agents/orchestrator.py`; test `backend/tests/test_debate_copilot.py`.

**Interfaces:** Cached `ResearchResult` values are rebound to the active target claim; `_remember_topic_knowledge` is monotone by `claim_revision`; `_send_debate_update` ignores explicit stale revisions.

- [ ] Add tests for corrected cached claim attribution, monotone topic knowledge, and stale server update rejection.
- [ ] Run the focused tests and confirm they fail for the intended reasons.
- [ ] Implement the minimal guards/rebinding.
- [ ] Run the focused tests to green.

### Task 2: Empty versus adopted database startup

**Files:** Modify `backend/app/main.py`; test `backend/tests/test_main_schema.py`.

**Interfaces:** `_schema_startup_action(tables: set[str]) -> Literal["upgrade", "adopt"]` selects adoption only when application tables exist without `alembic_version`.

- [ ] Add failing decision and command-selection tests.
- [ ] Run the schema tests red.
- [ ] Implement the helper and branch startup accordingly.
- [ ] Run schema and migration-focused tests green.

### Task 3: Visibility reconnect suppression

**Files:** Modify `frontend/src/lib/wsEventStream.ts`, `frontend/src/hooks/useWebSocket.ts`; test `frontend/src/lib/wsEventStream.test.mjs`.

**Interfaces:** `shouldReconnectVisibleSession(...) -> boolean` returns false for hidden/no-session/disabled/OPEN/CONNECTING states and true only for a reconnectable disconnected socket.

- [ ] Add the failing pure helper test.
- [ ] Run it red.
- [ ] Implement and wire the helper.
- [ ] Run the WebSocket tests and frontend production build green.

### Task 4: Visible desktop window and direct OpenAI OAuth

**Files:** Modify `desktop/launcher.py`, `desktop/tests/test_launcher.py`, `frontend/src/components/SubscriptionAccountsCard.tsx`; create `frontend/src/lib/oauthWindow.ts` and `frontend/src/lib/oauthWindow.test.mjs`.

**Interfaces:** `open_desktop_window(...) -> bool` means a visible embedded window or a successfully dispatched browser fallback; OAuth reserves and navigates one browser window from the click event.

- [ ] Add failing tests for invisible/early-exit GUI fallback and reserved OAuth navigation/failure cleanup.
- [ ] Run the desktop/frontend tests red.
- [ ] Implement bounded visible-window detection, browser fallback, and OAuth placeholder navigation.
- [ ] Run focused launcher, login, frontend tests and frontend production build green.

### Task 5: Focused verification and staged release

**Files:** No product edits unless a focused failure exposes a regression; update final audit facts after verification.

- [ ] Run focused backend ASR/revision/research/schema/replay/worker tests.
- [ ] Run focused desktop packaging/database tests and the build-script contract tests.
- [ ] Run `git diff --check` on changed release-hardening files.
- [ ] Run `scripts/build_debate_assistant.ps1 -SkipDownloads`; require staged EXE smoke and archive/update/rollback smoke before publication.
- [ ] Record artifact paths, sizes, hashes, and any honest remaining limits.
