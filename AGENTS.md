# DebateAI - repository agent guidance

Current versioned source lives under app/, NOT under historical source/.
See app/README.md and app/docs/DEBATEAI_CANONICAL_INDEX.md for detailed
implementation context. Canonical installed bundle location is runtime/DebateAI/;
the previously installed bundle was relocated during the 2026-11-19 source-only
audit into DebateAI_Generated/archive/installed-release-2026-11-19/.
It remains recoverable, but runtime/DebateAI/ is not presently launch-ready.

The root .github/workflows/ must remain for GitHub Actions.
The repository layout and tracked-file hygiene contract is defined in
app/scripts/verify_repository_layout.py and tested by
app/scripts/tests/test_repository_layout.py. Run these guards before
staging or publishing changes. GitHub Actions are allowed to remain advisory
only for Sentrux metrics; the repository-layout job must fail on violations.
Never bypass or soften the layout gate merely to make CI green.
DebateAI_Generated/ is normally a disposable build/dependency/cache workspace.
EXCEPTION: archive/installed-release-2026-11-19/ preserves the prior native
Windows bundle, including _internal, and must NOT be deleted automatically.
Git history and agent state are separately preserved in the sibling Coding audit;
never treat those unique records as downloadable dependencies.
Credentials, source code, and private user data remain outside Generated.
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
make the reorganization look clean.

## GitHub working contract

The public repository is `ErpeUser/DebateAI-final-public` and its standard
branch is `main`. Agents must work directly on a checked-out `main`, commit
the requested change there, and push `main` to `origin`. Agents must not create
feature branches, worktrees for routine changes, or pull requests. A pull
request found on GitHub is an incoming candidate to review, not a workflow for
the agent to create.

Before any GitHub pull or push, run:

```powershell
python app/scripts/github_sync.py --pull --strict
```

The command fetches and prunes remote refs, checks the GitHub default branch,
lists every other remote branch and every open pull request,
then performs an ff-only pull when the checkout is clean. After a successful
pull it classifies changed paths. Backend, frontend, desktop, AI or launcher
changes trigger the Windows bundle rebuild and smoke test. Launcher changes
also run the installed-bundle check. A recognized browser-extension change
must have a package build entry and is rebuilt. The command returns non-zero
while candidates remain so the agent must inspect them before the update is
considered complete.

For each listed branch or pull request, inspect its commits, changed files,
tests and freshness against `main`. Apply a standalone fix with a reviewed
cherry-pick, combine complementary changes in one local commit, or keep the
newer compatible implementation when it supersedes an older one. Resolve
conflicts on `main`, run the affected tests, and record the disposition in the
commit message or task notes. Never blindly merge every candidate, close or
delete someone else's branch, or force-push to resolve divergence.

After the review, run the layout and targeted tests, commit directly to `main`,
and push with `git push origin main`. If the working tree was dirty before the
pull, preserve those changes and stop before pulling.

Before cleanup or publication run backend/frontend/desktop/docs-site and
release tests as applicable. Current Windows bundle smoke passes; a fresh
Windows release build of modified source has not yet been completed.
Historical documentation and the independent pre-migration fallback remain
outside this active project in the existing 2026-11-18 snapshot. The public
repository contains source and safe documentation only. Local evidence,
recovery bundles, credentials, transcripts and other private material remain
outside Git.
