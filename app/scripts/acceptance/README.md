# DebateAI acceptance entry

Run from the existing repository root:

```powershell
powershell -NoProfile -File .\source\scripts\acceptance\run_all.ps1 -Profile Full
```

`-Python` selects an existing Python environment. The wrapper first uses the
checkout's `DebateAI_Generated/.release-venv/Scripts/python.exe`, then Python 3.12. Worktrees
without their own environment can explicitly use the original checkout's venv.
Python entry: `python app/scripts/acceptance/run.py --profile Full`.

Profiles: Fast, Full, Audio, ASR, Prompts, Security, Desktop, Release, Report.
Report gathers inventory without running suites. No model download, login,
installation, release publication, user-data migration or update is initiated.
Existing locked dependencies and approved model fixtures must already exist.
Only `-AllowNetwork` enables the dependency advisory query; ordinary trusted
repository tests are not network-sandboxed by this runner.

Each finished job prints `TASK-END <id> <status>`. Independent work continues
after a failed job. A dependent check runs only after its prerequisite passed.
All results remain in the denominator. Zero discovered tests, missing summaries,
skips, timeouts and unavailable tools cannot silently turn green. The Full
backend check uses pytest so free functions and fixtures are not omitted.

## Process and data safety

Tests receive isolated DATA_DIR, HOME, AppData, cache and temporary directories,
blank provider credentials and a deliberately unavailable database URL. User
`.env` files block affected Python suites. This is not permission/network
sandboxing; only trusted project tests may run. Do not use real data as fixtures.
The Windows launcher waits for assignment to a kill-on-close Job Object before
executing a command. POSIX uses a new session. Owned descendants are stopped on
success as well as timeout; unrelated processes are not terminated.

Output has a hard memory limit. Known credential values are redacted; overflow
output is omitted because truncation can expose a partial credential. Evidence
stays under Git-ignored `DebateAI_Generated/reports/acceptance/`; it is not uploaded automatically.
Existing reports are never overwritten. Symlink/junction output paths and
concurrent runner locks are rejected. A crashed lock requires inspection of its
owner; do not delete a lock while another run is active.

## Honest results

Exit 0 means the selected automated scope passed, not product acceptance.
Exit 1 means an executed check failed; exit 2 means incomplete evidence or a
blocked check. Full and Release do not currently approve a product: original
requirement review and actual hardware, model, human and release evidence remain
separate. `project_status` stays `IN_ARBEIT`. A successful subprocess duration is
not speech-to-painted-card latency. Missing measurements say `NOT_MEASURED`.

The inventory imports all 65 namespaced A/F/R gates plus the separate 276
historical identities. Historical statuses never become fresh approvals. An
unresolved original definition is reported explicitly, never invented from a
hash. The historical ledger is not modified by this command.

## Resume

```powershell
powershell -NoProfile -File .\source\scripts\automation\resume_debateai.ps1 -State .\evidence\acceptance\RUN\resume.json
```

Resume only revalidates a fixed profile on the recorded clean commit; it never
executes shell commands supplied in JSON and does not restart a coding agent.
Changed source requires a fresh run. No invisible background implementation is
promised by this script.

## Runner verification

```powershell
python -m unittest discover -s app/scripts/tests -p "test_acceptance*.py" -v
```

The 2026-11-16 native Windows/Python 3.12 verification ran 47 contract tests with
no skips or failures. That proves these runner contracts, not all product gates.

## Prepared verification tools

If present, DebateAI_Generated/.acceptance-venv supplies only Bandit, pip-audit and browser
fixtures; backend/desktop continue using the selected project interpreter.
Pinned direct tool versions are in requirements-tools.txt. The runner never
installs them. An explicit absolute PLAYWRIGHT_CHROMIUM_EXECUTABLE pointing
to an existing approved binary is forwarded; browser profiles and cookies are
not copied. All browser cases use fresh fixture contexts, not user tabs.
The 29 native Chromium fixture tests passed after repairing setup-failure
cleanup; they do not count as microphone or Windows WebView acceptance.
