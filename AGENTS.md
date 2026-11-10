# Codex instructions: FINAL WINDOWS WORKSPACE (mandatory)

## User intent — no ambiguity

The user explicitly requires the **EXISTING LOCAL Windows project checkout** to be updated to the
**LATEST FIXED REMOTE** `origin/master`, then the local desktop application rebuilt from
that same source. Do **not** treat a temporary clone/worktree as completion. A temporary
clone is allowed for investigation only; the user's actual existing checkout must end up
synchronized. Do not substitute an old GitHub release ZIP, old build or historical snapshot.

**Codex must decide automatically**, not repeatedly ask the user whether to pull,
overwrite or merge:

1. **Remote wins for superseded code.** If a local change is an older version of
   an already fixed or replaced feature in `origin/master`, discard that change from
   the active code. Do not reintroduce old code, dependencies, prompts, models, provider
   routing or UI through blind stash-apply/cherry-pick.
2. **Integrate genuinely unique improvements.** Compare local-only changes and commits
   semantically to the current remote. Bring forward only nonredundant, working
   improvements that complement the latest behavior and maintain compatibility.
   Test them and commit them to the existing checkout. Do not just keep both
   implementations side-by-side if they conflict.
3. **Newest fixed remote is the floor.** The current known fixed ancestor is
   `b7d48730bed175d4e4e7e5b2a6a6acf309f6dfb4`. Prefer `origin/master` if it
   has newer fixes. Never downgrade or pin to an older SHA when a newer checked
   `origin/master` is available.
4. **Preserve machine-specific data.** Never delete
   `%LOCALAPPDATA%\Backchannel`, `%USERPROFILE%\.ollama`,
   any existing browser profiles/cookies, OAuth sessions, API credentials,
   `.env`, `node_modules`, databases, volume data, local model caches,
   audio/transcripts or user configuration. Never run `git clean -fdx`.
   Do not commit secrets or local runtime state.
5. **Final means actual installed/runtime code.** Once merged, use the existing
   release scripts to rebuild, execute the included bundle/archive smokes,
   install or update the existing Windows application through its safe update
   path and start it. Verify that the source HEAD, packaged version and running
   executable match. Do not claim this succeeded unless the machine tests
   actually completed. Codesigning requires a real signing certificate.

## Mandatory workflow on Windows

Run these commands **in the existing checkout root** (the directory containing
`source/`, not `source/` itself). Discover it with `git rev-parse --show-toplevel`.
If not in a Git checkout, locate the actual existing worktree by inspection
first rather than silently creating a different checkout.

~~~powershell
$ErrorActionPreference = "Stop"
$repo = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repo) { throw "Existing local Git checkout not found" }
Set-Location $repo

$remote = (git remote get-url origin).Trim()
if ($remote -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)ErpeUser/backchannel-v6-private(\.git)?/?$') {
    throw "Unexpected origin; refusing to replace unrelated local code."
}
git fetch origin '+refs/heads/master:refs/remotes/origin/master'
if ($LASTEXITCODE -ne 0) { throw "GitHub fetch failed; check private repo access." }

# Bootstrap the updater from THE FRESHLY FETCHED REMOTE, even when the old
# local checkout does not yet have the new updater file.
$scriptText = git show origin/master:source/scripts/sync_final_workspace.py
if ($LASTEXITCODE -ne 0) { throw "Final-sync script missing from newest remote." }
$tempScript = Join-Path $env:TEMP ("debate-ai-sync-" + [guid]::NewGuid().ToString("N") + ".py")
try {
    [IO.File]::WriteAllText($tempScript, ($scriptText -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
    py -3.12 $tempScript --repo $repo
    if ($LASTEXITCODE -ne 0) {
        throw "Automatic sync requires semantic conflict resolution; inspect output and complete it."
    }
} finally {
    Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
}
~~~

`sync_final_workspace.py` fast-forwards the existing working tree to the
new remote, moves tracked working-tree edits into a recoverable named stash,
and preserves divergent local commits in a named backup branch while
rebasing them on `origin/master` when possible. It never resets ignored or
untracked runtime files. This preparatory script **does not make the semantic
merge decision for Codex**. Codex must review every recorded stash/backup,
compare behavior against new source, discard outdated pieces, cherry-pick/
restore only unique compatible improvements, and resolve conflicts. If an
automatic rebase conflicts, inspect both sides, preserve the corrected remote
behavior and the unique local functionality where possible, then
`git rebase --continue`. Never use `git push --force`.

Any meaningful combined improvements must pass the project tests and be
committed/pushed to `master` where authorized. If `origin/master` advanced
again, repeat fetch/integration before publishing. Finally prove:

~~~powershell
git fetch origin master
git status --short
git rev-parse HEAD
git rev-parse origin/master
# HEAD and origin/master MUST be identical for final synchronization.
~~~

A tracked clean checkout is expected; untracked/ignored user data may
remain and MUST NOT be forcibly removed. If the remote is inaccessible,
authentication is unavailable or critical conflicts cannot be resolved
correctly, report that precise blocker and do **not** falsely claim
the local Windows copy was updated.

## Build, install and verify

Use `source/docs/windows-final-runbook.md` for installation and testing and
`source/docs/releasing.md` for the release-specific build chain. In the
actual synchronized local checkout:

~~~powershell
Set-Location (Join-Path $repo "source")
$python312 = py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 required" }
.\scripts\build_debate_assistant.ps1 -Python $python312 -IncludeOracle
if ($LASTEXITCODE -ne 0) { throw "Windows build failed" }
~~~

The local build generates `source/dist/Backchannel-DebateAI-windows-x64.zip`.
After native smoke acceptance, safely replace only the **installed application
binaries** using verified archive/rollback rules, not user data. The
installation must not be overwritten while running and must not be deleted
before the new bundle is verified. Verify Ollama/Qwen, audio, ChatGPT Web,
Gemini Web and encrypted API-key reuse against the **new running version**
where available. An external account sign-in must be performed by the user
in the supported browser UI, never by importing cookies from their default
profile.

Do not finish after merely editing these instructions, fetching, making a
temporary clone, running Ollama tests, or generating an old build ZIP. The
deliverable is the **actual updated Windows machine checkout + current
application**; distinguish every step you demonstrably completed from
anything that machine still needs to do.
