# DebateAI: mandatory final Windows workspace contract

Product identity: **DebateAI**. Canonical target repository `ErpeUser/DebateAI`, stable repository ID **1450951492**, always **private**. No second repository, history rewriting, force-push, fake signing keys or domains. Required copyright/license/provenance notices remain.

Read together: source/AGENTS.md; source/docs/DEBATEAI_CANONICAL_INDEX.md; source/docs/DESKTOP_FINAL.md; source/docs/windows-final-recovery.md; source/docs/releasing.md; relevant latest entries of source/.ai/DEBATE_AI_OPTIMIERUNG.md and source/.ai/FINAL_INTEGRATION_2026-11-11.md. The reconciliation matrix resolves both earlier deliveries. New explicit user instructions supersede obsolete branch/branding guidance, not privacy, data protection or test requirements.

## The actual existing checkout is mandatory

Find the Windows worktree actually used by the user; record absolute root, branch, HEAD, origin, uncommitted changes and local-only commits. A temporary inspection copy or old release ZIP is not completion. Latest corrected remote is the baseline. Discard superseded local source, prompts, model routes and build logic; retain genuinely unique compatible improvements only after semantic comparison and tests. Review every stash/backup rather than blindly applying it. Resolve overlapping edits by behavior, not timestamps. Never blindly push ahead commits or reset divergent work.

Known fixed ancestor b7d48730bed175d4e4e7e5b2a6a6acf309f6dfb4 is a floor, not a pin. After the consolidation merge, master must contain 9d88baae677083770c2c81943687713d6fc393a6 and subsequent finalization fixes. Do not require an old feature branch that may have been safely deleted after merge.

Migrate %LOCALAPPDATA%\Backchannel into %LOCALAPPDATA%\DebateAI without deleting the legacy source until the canonical copy is validated. Preserve %USERPROFILE%\.ollama, master.key/DPAPI, API/OAuth sessions, browser profiles/cookies, .env, node_modules, databases/volumes, model caches, recordings/transcripts, settings and customized AI files. Never git clean -fdx. Never commit secrets or machine runtime state. A named stash/backup is recovery, not the semantic merge decision.

## Bootstrap from the newest fetched source

Run in the actual root containing source/, not a temporary checkout. If on another branch or in an unfinished merge/rebase, first inspect and safely reconcile that state.

```powershell
$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repo) { throw 'Existing local checkout not found' }
Set-Location $repo
$remote = (git remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $remote -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)ErpeUser/DebateAI(\.git)?/?$') { throw 'Unexpected origin' }
git fetch origin '+refs/heads/master:refs/remotes/origin/master'
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
$scriptText = git show origin/master:source/scripts/sync_final_workspace.py
if ($LASTEXITCODE -ne 0) { throw 'Newest sync script missing' }
$tempScript = Join-Path $env:TEMP ('debateai-sync-' + [guid]::NewGuid().ToString('N') + '.py')
try {
    [IO.File]::WriteAllText($tempScript, ($scriptText -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
    py -3.12 $tempScript --repo $repo
    if ($LASTEXITCODE -ne 0) { throw 'Inspect the reported collision/conflict and resolve safely' }
} finally { Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue }
```

The single-file updater checks ignored/untracked collisions before stashing and preserves divergent commits for review. Never weaken those guards to appear synchronized. Inspect named stash/backup; restore only unique tested improvements, resolve conflicts before rebase --continue. Verify repository ID/private status before administrative rename. User authorizes normal non-force source publication, merge and deletion only of branches proven fully included in master, never protection bypass or deletion of unique work/default branch.

## Playbooks remain product functionality

Keep all valid current strategies (presently 15) in source/ai/playbooks.json and source/ai/defaults/playbooks.json. Preserve genuinely new local strategies/triggers, not obsolete duplicate or contradictory directives. Keep current short answer_now, optional counter_question, primary_move and current deep analysis prompts in source/ai/debate_live_v2.txt, source/ai/defaults/prompts/debate_live_v2.txt and corresponding deep versions.

source/backend/app/services/ai_config.py playbook_controls() and _merge_bundled_defaults() intentionally preserve customized runtime copies. A new EXE does not prove an old user playbook was migrated. Compare active user copy, last bundled baseline and new defaults. Secure an external rollback copy before reconciliation; keep unique valid strategies and version history. Never blindly overwrite user customization.

Check PROFILE_DEFINITIONS/playbook_term in debate_settings.py, saved profiles/per-session directives and orchestrator trigger normalization as one chain. The PyInstaller spec must still bundle ai after renaming. Verify both playbook JSON files and live/deep prompts in the actual archive, then /api/ai-config active directory, prompt generation and effective strategy. Exercise Gegenfrage, Beweislast and Widerlegung, both modes and focused config/profile tests.

## Build/install/verification

Use Python3.12/Node24, existing constraints/lockfiles and current release scripts in the synchronized real checkout:

```powershell
Set-Location (Join-Path $repo 'source')
$python312 = py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 required' }
.\scripts\build_debate_assistant.ps1 -Python $python312 -IncludeOracle
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
```

The active wrapper output is the DebateAI archive and executable contract; historical Backchannel filenames are migration evidence only. Renaming one file is not completed decoupling. Include frontend/laboratory, backend, ONNX resources, PostgreSQL, ffmpeg, Ollama, CLIProxyAPI/Gemini, Web bridge, Oracle/Node24, PyInstaller, bundle and native archive/rollback smokes.

Never delete old installation before the new archive/staging passes validation. Use existing updater, same-filesystem staging, preserve old binaries, stop own processes after work drains, then verify exact new EXE and token-bound health. Never call a live PostgreSQL file copy a consistent backup. Schema migration needs a separate tested data recovery path; binary rollback is not DB rollback. Never delete AppData or kill unrelated processes.

Use existing credentials only through supported application interfaces. A fresh interactive login belongs to the user; never import private standard-profile cookies. Check Privacy First against real destinations, not localhost labels. A signed production release needs real Authenticode certificate, independent update trust and successful publication logs; no fictitious success.

Run full native/project/release gates and all 15 handoff runtime checks. Separate focused Linux/mocked evidence, true model measurements, real hardware, account steps and publication. A CI runner executing no steps is not a pass. Do independent work despite external blockers; never disguise internal missing work as only account issues.

The production pair CLI is already integrated: existing headless replay in sequential isolated processes, both modes and retained failure denominators. Stop the desktop for that source experiment. It is not a frozen-UI generation button or screen-paint/hardware measurement. Do not rebuild confirmed work or add speculative agent frameworks. Research recommendations require measured benefit.

After further useful source changes: test, commit, integrate latest remote, push without force, then build that exact finalized code. Finally git fetch origin master; git status --short; git rev-parse HEAD and origin/master must agree. Retained user files are not source garbage. Report absolute real project path, SHAs, semantic merge decisions, ZIP path/SHA256, running EXE/build origin, automated and hardware results, Ollama/ChatGPT/Gemini/key status, actual repository/branch state and exact blockers. A source merge alone is not a final installed Windows version.
