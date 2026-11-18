# DebateAI - repository agent guidance

Current versioned source lives under app/, NOT under historical source/.
See app/README.md and app/docs/DEBATEAI_CANONICAL_INDEX.md for detailed
implementation context. Native testable Windows bundle: runtime/DebateAI/.

The root .github/workflows/ must remain for GitHub Actions.
The repository layout and tracked-file hygiene contract is defined in
app/scripts/verify_repository_layout.py and tested by
app/scripts/tests/test_repository_layout.py. Run these guards before
staging or publishing changes. GitHub Actions are allowed to remain advisory
only for Sentrux metrics; the repository-layout job must fail on violations.
Never bypass or soften the layout gate merely to make CI green.
DebateAI_Generated/ is fully disposable, never a home for Git history,
unique data, executable runtime, credentials, source code or configuration.
Build dependencies/caches may be recreated using pinned source scripts.
The installed bundle at runtime/DebateAI/ works without Generated.
Start-DebateAI.ps1 is the recovery entrypoint and must stay versioned.
Signed Windows recovery uses the pinned Ed25519 key document,
app/scripts/recover_release.py and explicitly configured HTTPS update URLs.
Never add guessed update domains, downloaded public keys or an unsigned
fallback. Local build archives/venv/caches belong under Generated;
app/scripts/build_debate_assistant.ps1 owns that local contract.

Protect private data at %LOCALAPPDATA%/DebateAI, API/OAuth sessions,
transcripts, personal playbooks, encryption keys and PostgreSQL files.
Do not destroy model/AI prompt assets in app/ai/; these are product resources.
Never follow junctions while deduplicating, and never alter
runtime/DebateAI/_internal/ by finding identically named
or hashed files.

Git metadata is in the internal `.git/` directory at the repository root.
Legacy pointer checkouts may be read during migration, but new checkouts use
the normal internal layout. Never move Git metadata into Generated.
The workspace reference resolver lives at app/scripts/workspace_refs.py;
it must work even when Generated is absent. Never treat missing packages
as installed. Never move runtime/DebateAI/_internal members independently.
Preserve branch, HEAD, origin, stashes, reflogs, worktrees and all preexisting
uncommitted changes. Never force-push, reset or rewrite history merely to
make the reorganization look clean. Keep repository private.

Before cleanup or publication run backend/frontend/desktop/docs-site and
release tests as applicable. Current Windows bundle smoke passes; a fresh
Windows release build of modified source has not yet been completed.
Historical documentation and the independent pre-migration fallback remain
outside this active project in the existing 2026-11-18 snapshot.
