# DebateAI Identity Decoupling Design

Date: 2026-11-11
Status: Implemented on `codex/debateai-identity-decoupling`; final runtime/build and external release gates remain separately unclaimed.
Scope: active runtime, desktop package, update channel, frontend contracts, documentation and release metadata.

## Intent

DebateAI is the canonical product identity. The starting master carried active Backchannel package names, environment variables, HTTP headers, updater paths, default download URLs and desktop imports. The branch makes DebateAI self-contained while preserving existing user data through an explicit, isolated migration boundary.

## Goals

- Make active Python, TypeScript, HTML, shell/PowerShell and CI contracts use DebateAI names.
- Rename the desktop Python package and PyInstaller spec to debateai_desktop and debateai.spec.
- Use DEBATEAI_* environment variables and X-DebateAI-Instance as the only runtime contract.
- Use DebateAI executable, updater and archive roots consistently.
- Remove the inherited vendor update URL as a default; updates require explicit HTTPS deployment endpoints and trusted keys.
- Update active documentation and indexes, consolidate stale status/runbook references, and identify historical snapshots clearly.
- Add regression tests proving no active Backchannel dependency remains and that legacy user data can be migrated without data loss.

## Non-goals

- Rewriting Git history, force-pushing, deleting the default branch, or changing repository visibility.
- Deleting historical release notes, provenance manifests, or source snapshots solely because they contain old names.
- Claiming Windows hardware, signing, microphone, real-model or production-release acceptance from Linux/API checks.
- Inventing a replacement download domain or silently enabling an update service.

## Approaches

1. String-only rename: rejected because it leaves data migration, updater safety and environment compatibility undefined.
2. Permanent compatibility aliases: rejected because active runtime behavior remains coupled to Backchannel.
3. Canonical DebateAI runtime with isolated migration: selected. Core code has no legacy fallback. A small migration module detects an existing legacy data root or explicitly supplied legacy environment, verifies the destination, and copies or renames only after the new root is empty. The migration is observable and idempotent; callers then use DebateAI paths exclusively.

## Architecture

desktop/debateai_identity.py owns canonical names, executable paths, headers, data roots and migration entry points. desktop/debateai_desktop/ contains the renamed desktop runtime package. Backend and frontend use canonical environment and header constants. The updater accepts only DebateAI archive layout and its defaults are disabled until explicit DEBATEAI_UPDATE_DESCRIPTOR_URL, DEBATEAI_UPDATE_ASSET_URL, installation and trust-key paths are configured.

Runtime data-root selection is side-effect-free and never searches, copies or selects an older product directory. The optional `tools/legacy_data_import.py` is invoked explicitly outside the bundle: it verifies same-user ownership, creates a digest-verified backup, refuses target conflicts and publishes file-only data once. Database/browser stores are refused in their entirety pending a database-aware export/restore; that migration gate remains open. Originals and backups are never removed. No BACKCHANNEL_* variable or X-Backchannel-* header is read by active runtime code.

## Documentation and cleanup policy

app/docs/windows-final-recovery.md is the current Windows runbook; current gaps are maintained in app/docs/OFFENE_PUNKTE.md and dated historical evidence is consolidated in app/docs/HISTORIE.md. A new app/docs/DEBATEAI_CANONICAL_INDEX.md links current contracts and marks dated audits and plans as historical. Dated release pages and provenance files remain, but active pages, URLs, examples and generated metadata use DebateAI.

## Verification

- Python unit tests for identity migration, updater layout, canonical headers and backend update configuration.
- Frontend Node tests for the canonical desktop update header and endpoint.
- Syntax and import checks for all renamed desktop modules.
- Scoped active-runtime scan that fails on BACKCHANNEL_*, X-Backchannel-Instance, bcdesktop, backchannel.spec, Backchannel.exe and legacy download/signing domains within runtime directories; migration and evidence records remain outside that scope.
- CI workflow and manifest checks updated to renamed paths.
- Full available test suites should run before merge. Any unavailable Windows, hardware, release or real-model gate is documented with an exact reproduction command and acceptance condition in the implementation plan.
