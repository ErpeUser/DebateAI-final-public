# DebateAI

DebateAI is a private, local-first live debate assistant. The canonical product
name is **DebateAI**. This branch integrates its German calibration laboratory
into the application and begins a migration-safe separation from the inherited
product identity and hosted update infrastructure.

**Status:** integrated source and focused regression tests, not a newly built,
signed or installed Windows release. The complete desktop binary/package rename,
full-project release gates and native acceptance are still required. A repository
rename alone does not complete that migration.

## Use the integrated test laboratory

Open the application and select **Testlabor**. The same-origin dialog keeps the
live application mounted. It compares the same short recording across cached
German local ASR models, displays recognition errors and latency separately, and
supports blinded answer-pair/suite import, human ratings and JSON export.

Opening the laboratory does not request microphone access. Recording is explicit.
Heavy diagnostic work is blocked while tracked live work is running. Closing the
laboratory stops its recording, preserves its displayed results, and does not
pretend that a still-running native inference worker has stopped.

The entry page is `source/frontend/public/calibration.html`; the production API
is `source/backend/app/routers/calibration.py`. Test sources live inside this
repository under `source/backend/tests/`, `source/frontend/calibration-tests/`,
`source/desktop/tests/` and `source/scripts/tests/`. No separate recovery ZIP or
manual source overlay is needed.

## Independent identity and safe migration

Fresh desktop installs select a DebateAI data directory. Existing nonempty legacy
data remains readable through narrowly scoped compatibility aliases; credentials,
model caches, profiles and databases are never silently discarded or moved while
running. Automatic updates are disabled unless independently configured HTTPS
endpoints and an explicit public trust-key file are supplied. Existing signature,
archive-validation and rollback requirements remain in force.

The intended repository name is `ErpeUser/DebateAI`. The checked-in
`source/scripts/rename_debateai_repository.py` verifies the immutable repository
ID and private visibility, previews by default, and changes the remote and local
origin only with `--apply` using an existing authenticated GitHub CLI. Its presence
does **not** mean that the GitHub repository has already been renamed.

## Finalization and verification

Read [the exact Codex handoff](source/docs/CODEX_DEBATEAI_FINAL.md),
[verification evidence and limits](source/docs/debateai-verification-2026-11-11.md),
`AGENTS.md`, `source/AGENTS.md`, `source/docs/windows-final-runbook.md`, and
`source/docs/releasing.md` together. The latest user-authorized standalone identity
supersedes older branding instructions, not data protection or signing checks.

Historical release manifests, privacy audit, source provenance and required
copyright/license notices are retained. Historical checksums describe their
original artifacts; they are not evidence of a new DebateAI Windows build. Do not
install an old archive and call it the current source revision.
