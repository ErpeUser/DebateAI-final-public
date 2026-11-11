# DESKTOP_FINAL Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the checked-out `ErpeUser/backchannel-v6-private` master source through every automatable requirement in `source/docs/DESKTOP_FINAL.md`, then build and smoke-test the Windows desktop candidate while leaving human and hardware gates explicit.

**Architecture:** Treat `source/` as the application source tree and the repository root as the private snapshot/controller. Preserve Backchannel identifiers as migration aliases until the executable, updater, archive, API headers, data paths, manifests, and release workflows pass together. Each subsystem is changed behind a focused contract test; the final build consumes only the tested source tree and produces a staged bundle before any archive or installation action.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, stdlib `unittest`, React/Vite/Node 24, PowerShell release scripts, PyInstaller, embedded PostgreSQL/ffmpeg/ONNX assets, signed Ed25519 update descriptors, GitHub Actions and Cloudflare R2 release transport.

**Spec:** `source/docs/DESKTOP_FINAL.md`

## Global Constraints

- Work only on `master` with `HEAD == origin/master` before each integration checkpoint; never force-push or rewrite history.
- Preserve `%LOCALAPPDATA%\Backchannel`, `%LOCALAPPDATA%\DebateAI`, databases, DPAPI/master keys, credentials, browser profiles, prompts, transcripts, models, and user configuration; never use `git clean` or broad deletion against user data.
- Keep `Backchannel`, `BACKCHANNEL_*`, `X-Backchannel-Instance`, `Backchannel.exe`, and legacy data roots as controlled compatibility aliases until the complete migration contract is proven.
- No credentials, cookies, OAuth state, transcripts, database files, model weights, or generated bundles may enter the source snapshot, logs, manifests, or tests.
- Python release target is 3.12; Node release target is 24; use existing lockfiles and pinned constraints; do not perform unbounded dependency upgrades.
- A signed production release requires real signing infrastructure and a native archive/update/rollback smoke; test keys and mock providers never count as publication evidence.
- Human gates A06, A18, A21, and A22 and the 15 runtime gates must remain separately labeled until the user performs the real Windows/audio/model/provider acceptance.

## Review Focus

- A partially failed update must preserve the installed bundle, backup, grant, and resumable state; test interrupted download, swap, health timeout, and rollback together in Task 3.
- A legacy Backchannel data path or header must not be silently dropped during DebateAI migration; test both canonical and legacy aliases in Task 2.
- A source snapshot must not contain local credentials or runtime data; test filename, content, manifest, and secret scans in Task 1 and Task 8.
- A build must not claim a release when the staged bundle, archive, native launcher, or signature differs from source; test provenance hashes and archive smoke in Task 4 and Task 9.
- A local-model or strict-local setting must never silently route to cloud, browser ASR, or an unknown proxy; test endpoint admission and missing-model readiness in Task 6.

---

### Task 1: Synchronize and inventory the actual master workspace

**Files:**
- Inspect: `source/docs/DESKTOP_FINAL.md`, `AGENTS.md`, `source/AGENTS.md`, `source/docs/windows-final-recovery.md`, `source/docs/releasing.md`, `source/docs/RECONCILIATION_MATRIX_DE.md`, `source/docs/FINAL_VERIFICATION_2026-11-11.md`
- Inspect: `source/scripts/sync_final_workspace.py`, `.github/workflows/*`, `source/.github/workflows/*`
- Modify: `source/.ai/DEBATE_AI_OPTIMIERUNG.md`
- Test: `source/scripts/tests/test_sync_final_workspace.py`

**Interfaces:** Produces a clean, verified `master` baseline, a classified inventory of tracked/local/generated files, and a list of exact gaps used by later tasks.

- [ ] Fetch `origin/master`, verify the allowed private remote, branch, HEAD equality, and minimum fixed commit.
- [ ] Run the single-file workspace synchronizer against the repository root; stop on collisions and preserve any user data outside Git operations.
- [ ] Reconcile root/controller workflows with the `source/` snapshot and decide the missing `source/.github/workflows/desktop-release.yml` contract without copying files blindly.
- [ ] Run the sync safety tests and `git diff --check`; record baseline, decisions, and next action in the leading progress file.

### Task 2: Complete the DebateAI desktop identity and compatibility contract

**Files:**
- Modify: `source/desktop/launcher.py`, `source/desktop/updater.py`, `source/desktop/backchannel.spec`, `source/desktop/bcdesktop/*`, `source/backend/app/services/update_service.py`, `source/backend/app/services/update_signing.py`
- Modify: relevant `source/frontend` tray/about/update components, package metadata, and API headers
- Test: `source/desktop/tests/test_launcher.py`, `test_paths.py`, `test_version_resource.py`, `test_release_contract.py`, `source/backend/tests/test_debateai_identity.py`

**Interfaces:** Canonical product names are DebateAI/DebateAI.exe/DebateAIUpdater.exe and `DEBATEAI_*`; every old Backchannel name remains an explicit migration alias with the same data and security semantics.

- [ ] Write failing tests for canonical names, legacy aliases, root/launcher resolution, instance headers, resource names, and About/tray labels.
- [ ] Implement the smallest coordinated identity change across launcher, updater, spec, embedded resources, frontend, API, and paths; do not rename a single layer in isolation.
- [ ] Verify old installations and data directories remain discoverable and no two processes can share one database.
- [ ] Run the focused desktop/backend identity suite and update the progress matrix.

### Task 3: Harden the independent update channel and native rollback path

**Files:**
- Modify: `source/backend/app/routers/updates.py`, `source/backend/app/services/update_service.py`, `source/backend/app/services/update_signing.py`, `source/desktop/updater.py`, `source/desktop/scripts/smoke_update_archive.py`
- Test: `source/desktop/tests/test_update_acceptance.py`, `test_updater.py`, `test_smoke_test.py`, `source/backend/tests/test_update_service.py`, `test_debateai_update_channel.py`

**Interfaces:** Update descriptors remain independently signed; downloads are grant-bound, resumable, bounded in memory/disk, staged beside the install root, health-token-bound, and rollback-safe.

- [ ] Add failing coverage for grant expiry/revocation, resume ranges, descriptor/signature mismatch, path traversal, free-space checks, old-process timeout, new-process health mismatch, and rollback preservation.
- [ ] Implement only the missing contract behavior, preserving existing canonical signing fields and compatibility aliases.
- [ ] Run the full focused update acceptance and archive-helper suites, including the native-path tests available on Windows.

### Task 4: Make build, archive, manifest, and provenance contracts coherent

**Files:**
- Modify: `source/scripts/build_debate_assistant.ps1`, `source/scripts/release_desktop.ps1`, `source/scripts/publish_release_platform.ps1`, `source/desktop/Dockerfile.release-linux`, `source/desktop/scripts/build_*manifest.py`, `source/docs/releasing.md`
- Test: `source/scripts/tests/test_build_debate_assistant.ps1`, `test_release_desktop.ps1`, `source/desktop/tests/test_release_manifest.py`, `test_platform_release_manifest.py`, `test_release_contract.py`

**Interfaces:** Build output is staged and provenance-linked; the canonical pre-migration artifact remains `dist/Backchannel-DebateAI-windows-x64.zip` until the complete name migration passes.

- [ ] Add failing checks for source commit, version, archive filename, expanded roots, exact asset tuples, descriptor signatures, and no-overwrite/idempotency behavior.
- [ ] Fix workflow/controller placement or test-root resolution so the release contract checks the intended repository layout.
- [ ] Run PowerShell contract tests, manifest tests, and `git diff --check` before any real build.

### Task 5: Reconcile frontend, packages, and test-lab integration

**Files:**
- Modify: `source/frontend/package.json`, lockfile, `src/App.tsx`, tray/about/update components, calibration/test-lab assets, PWA metadata
- Test: frontend `npm test`, `npm run build`, `npm run test:pwa -- --dist`, calibration Node/Python suites, `source/frontend/scripts/verify-pwa-assets.mjs`

**Interfaces:** UI labels and package metadata use DebateAI while persisted/API compatibility remains controlled; test-lab exports preserve case IDs, hashes, status/failure denominators, and both debate modes.

- [ ] Add failing tests for navigation, German test-lab cases, import/export hashes, stale/empty/timeout/error statuses, and PWA metadata.
- [ ] Implement missing UI/package/test-lab pieces without introducing a second prompt stack or hiding incomplete states.
- [ ] Run the focused frontend/lab suite and production build.

### Task 6: Verify local AI, privacy, providers, and benchmark contracts

**Files:**
- Modify only where required: `source/backend/app/services/privacy.py`, `llm.py`, `custom_endpoints.py`, `transcription_readiness.py`, `scripts/benchmark_blind_pair.py`, prompt/playbook resources, model manifests
- Test: privacy/endpoint/LLM/readiness tests, benchmark export tests, `source/docs/model-manifest.json` validators

**Interfaces:** Strict-local admission is destination-based; missing local models fail honestly; no cloud/browser-ASR fallback is silent; benchmark errors remain in the denominator and never invent quality scores.

- [ ] Add or repair failing tests for loopback/LAN/cloud classification, provider credentials, model provenance, prompt override/reset, and benchmark replay status.
- [ ] Implement missing guards and export validation; never download models or contact paid providers implicitly.
- [ ] If Ollama and two approved local models are present, run the real visible-answer smoke and blind pair benchmark; otherwise record the exact human/environment gate.

### Task 7: Complete repository administration and snapshot hygiene

**Files:**
- Inspect/modify only with proof: `source/scripts/rename_debateai_repository.py`, `SOURCE_SNAPSHOT_MANIFEST.json`, `SOURCE_PROVENANCE.md`, `.github/CODEOWNERS`, `source/.github/*`
- Test: `source/scripts/tests/test_rename_debateai_repository.py`, `test_workspace_safety.py`, privacy/manifest scans

**Interfaces:** Private repository identity, branch protections, release notes, source provenance, and snapshot exclusions remain verifiable without exposing credentials or deleting user data.

- [ ] Run rename preflight and inspect repository ID/private state using existing authenticated tooling; do not apply a rename without a non-conflicting target and explicit confirmation.
- [ ] Rebuild the source manifest only from the tested tree; scan filenames/content for credentials, cookies, databases, logs, models, and runtime bundles.
- [ ] Verify branch/ref cleanup only after merge-base proof; otherwise leave refs untouched and document the blocker.

### Task 8: Execute the complete automated gate and record evidence

**Files:**
- Modify: `source/.ai/DEBATE_AI_OPTIMIERUNG.md`, `source/docs/FINAL_VERIFICATION_2026-11-11.md` only after evidence exists
- Test: backend and desktop unittest discovery, frontend build/tests, docs-site focused suites/build, release script tests, compileall/node-check, structural gate if available

**Interfaces:** Every result is tied to an exact command, interpreter/version, commit, artifact hash, and explicit limitation; no mocked result is promoted to a runtime/human gate.

- [ ] Run the full backend and desktop suites in the project Python 3.12 environment, then frontend/docs/release gates.
- [ ] Run Sentrux check/gate if the configured executable is available; otherwise record a tooling blocker.
- [ ] Update the progress matrix with passed, skipped, failed, and unavailable gates, preserving the next concrete action.

### Task 9: Produce and verify the final Windows candidate

**Files:**
- Generate only: `source/dist/*`, `source/build/*` and staged smoke outputs (never commit runtime data)
- Execute: `source/scripts/build_debate_assistant.ps1 -Python <Python3.12> -IncludeOracle`, native bundle smoke, archive/update/rollback smoke

**Interfaces:** The candidate is built from the verified commit, its EXE/archive provenance and SHA-256 are recorded, and the old install/data remain recoverable until acceptance.

- [ ] Confirm Node 24, Python 3.12, npm, WebView2, ffmpeg, PostgreSQL, ONNX, Oracle runtime, and required local model/provider prerequisites.
- [ ] Build into isolated staging, run health/ASR/shutdown and native archive/update/rollback smokes, and hash the resulting artifact.
- [ ] Do not publish or replace an installation until the user performs the 15 runtime gates and A06/A18/A21/A22 human/hardware gates.
- [ ] Record the exact remaining acceptance actions and stop with the goal active if any external gate is not available.

