# DebateAI - repository agent guidance

Current versioned source lives under app/, NOT under historical source/.
See app/README.md and app/docs/DEBATEAI_CANONICAL_INDEX.md for detailed
implementation context. Native testable Windows bundle: DebateAI_Generated/runtime/DebateAI/.

The root .github/workflows/ must remain for GitHub Actions. Python/Node
dependencies, downloaded models, caches, release artifacts and test outputs
belong under DebateAI_Generated/ or are regenerated from app package lockfiles
and existing download/build scripts. Generated must NEVER hold unique user
data or indispensable versioned source. Do not make app tests/scripts/config
depend on Generated path aliases.

Protect private data at %LOCALAPPDATA%/DebateAI, API/OAuth sessions,
transcripts, personal playbooks, encryption keys and PostgreSQL files.
Do not destroy model/AI prompt assets in app/ai/; these are product resources.
Never follow junctions while deduplicating, and never alter
DebateAI_Generated/runtime/DebateAI/_internal/ by finding identically named
or hashed files.

Git metadata may live outside this worktree, referenced by a tiny .git file.
Preserve branch, HEAD, origin, stashes, reflogs, worktrees and all preexisting
uncommitted changes. Never force-push, reset or rewrite history merely to
make the reorganization look clean. Keep repository private.

Before cleanup or publication run backend/frontend/desktop/docs-site and
release tests as applicable. Current Windows bundle smoke passes; a fresh
Windows release build of modified source has not yet been completed.
Historical documentation and the independent pre-migration fallback remain
outside this active project in the existing 2026-11-18 snapshot.
