# DebateAI Identity Decoupling Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task by task. Steps use checkbox syntax for tracking.

Goal: Remove active Backchannel coupling and ship a canonical DebateAI runtime with an explicit, safe legacy-data migration boundary.
Architecture: Rename the desktop Python package and build spec, centralize canonical identity and migration in debateai_identity.py, update backend/frontend/update contracts to DebateAI-only names, and consolidate active documentation while preserving historical evidence.
Tech Stack: Python 3.12, FastAPI, pytest/unittest, React/Vite, Node 24, PyInstaller, GitHub Actions.
Spec: source/docs/identity-decoupling-design.md

## Global Constraints

- Keep repository private and preserve Git history.
- Do not invent update URLs; require explicit HTTPS configuration.
- Never overwrite or delete a non-empty user data directory during migration.
- Keep historical release and provenance snapshots, but label them historical.
- Do not claim Windows, hardware, signing or real-model acceptance without fresh evidence.

## Review Focus

- Empty DebateAI destination with populated legacy data migrates exactly once and remains idempotent.
- Non-empty destination blocks migration without data loss.
- Missing update endpoints disable updates instead of contacting a legacy domain.
- Canonical headers and environment variables are used by every backend, desktop and frontend boundary.
- Frozen-build paths, updater extraction and archive manifests agree on DebateAI names.

## File Map

- source/desktop/debateai_identity.py: canonical constants plus safe migration.
- source/desktop/debateai_desktop/*.py: renamed desktop package and imports.
- source/desktop/debateai.spec: renamed PyInstaller spec and canonical environment.
- source/backend/app/routers/updates.py, source/backend/app/services/update_service.py and source/backend/app/services/debateai_update_channel.py: canonical update contract.
- source/frontend/src/services/desktopUpdateApi.ts and Vite/runtime config: canonical update contract.
- source/docs/DEBATEAI_CANONICAL_INDEX.md, source/docs/DESKTOP_FINAL.md and source/docs/FINAL_STATUS_AND_OPEN_ITEMS.md: active documentation.
- Desktop, backend and frontend tests plus structure and release workflows: regression coverage.

## Completion status — 2026-11-11

The implementation work is complete on `codex/debateai-identity-decoupling`. The checkboxes below distinguish changes that are present in the branch from checks that still require a provisioned Windows/Node/Python environment.

### 1. Contract coverage

- [x] Identity migration tests cover populated, empty-destination and conflicting roots.
- [x] Update tests reject legacy defaults, missing assets and invalid signing authorities.
- [x] A scoped active-runtime scan test rejects legacy env/header/package/archive/domain identifiers; explicit migration and historical-evidence files stay outside its runtime scope.
- [ ] Final focused test execution is pending because the local execution environment was unavailable during the last verification pass.

### 2. Canonical identity and migration

- [x] Typed canonical constants and a structured migration result are in `debateai_identity.py`.
- [x] Migration is idempotent, preserves the legacy source and refuses a non-empty destination.
- [x] Active runtime reads only DebateAI environment/header names; legacy names are isolated to data migration and negative tests.
- [ ] Identity and launcher suites must be rerun in a provisioned environment after the final branch commits.

### 3. Desktop runtime

- [x] `bcdesktop` became `debateai_desktop`; imports, mocks and frozen-source checks follow the new package.
- [x] `backchannel.spec` and `backchannel-loopback.patch` became DebateAI-named files.
- [x] PyInstaller hidden imports, resource paths, child-process names, updater paths and archive names use the canonical identity.
- [ ] Windows packaging, rollback and DPI/hardware acceptance remain external gates.

### 4. Backend, frontend and update contracts

- [x] Backend, desktop, frontend, Docker and release tooling use `DEBATEAI_*`, `X-DebateAI-Instance` and `debateai.instance.*`.
- [x] Update endpoints are explicit deployment configuration; production signing requires an exact HTTPS URL and test loopback is opt-in.
- [x] Release metadata and CI checks require DebateAI archive/executable names and the canonical user-agent.
- [ ] Backend/frontend suites and the real signing endpoint must be rerun with CI provisioning.

### 5. Documentation and metadata

- [x] `DEBATEAI_CANONICAL_INDEX.md` is the maintained entry point; historical audits, plans and manifests are labeled.
- [x] README, quickstart, start-here, design, deployment and active site metadata were reconciled.
- [x] No historical manifest or provenance record was rewritten; duplicate active guidance was consolidated by linking to the canonical index.
- [x] The exact blocker handoff prompt below records the remaining environment-dependent verification.

### 6. Review and integration

- [x] Complete changed-path inventory and PR diff were reviewed through the GitHub API.
- [x] The branch is committed and draft PR #6 is open for review.
- [ ] Final local/CI gates are intentionally unclaimed until they execute on a provisioned runner.

## Exact verification handoff prompt

Run this prompt on a Windows runner with Python 3.12, Node 24, PowerShell 7 and the release credentials supplied through the deployment secret store:

```text
In the private repository ErpeUser/DebateAI, checkout codex/debateai-identity-decoupling at the PR head. Do not change master, rewrite history, or invent a signing/download domain.

1. Install source/backend/requirements.txt and source/desktop/requirements.txt, then run the focused Python suites for source/backend/tests and source/desktop/tests. Run the frontend tests/build with Node 24.
2. Run the PowerShell release-contract and immutable-publisher fixtures under source/scripts/tests, then build the PyInstaller bundle from source/desktop/debateai.spec.
3. Run source/desktop/scripts/smoke_test.py and smoke_update_archive.py for every declared platform. Verify the executable, updater, mutex, log, archive and rollback names are all DebateAI.
4. Set DEBATEAI_RELEASE_SIGNING_URL and DEBATEAI_RELEASE_SIGNING_PRODUCTION_URL to the same deployment-owned HTTPS endpoint, run the remote-signing fixture, and confirm that HTTP, redirects, userinfo, query, fragment, wrong-port and wrong-path variants fail before any R2 write.
5. Run an active-text scan over runtime directories. Permit old identifiers only in debateai_identity.py migration constants, pg.py legacy-role migration, PII legacy-purpose fallback, explicit negative tests, migration scripts, and historical manifests/provenance/docs.
6. Record every failure with the exact command and traceback. Mark the release accepted only after Windows DPI/rollback, real audio/ASR, human rhetoric, Authenticode and the concrete DNS/update deployment gates have fresh evidence.
```

The implementation can be reviewed or merged independently of those external gates; no claim of successful build, hardware, signing or real-model acceptance is made here.