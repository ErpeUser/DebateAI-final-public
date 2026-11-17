# F11 bounded persistence acknowledgement verification

Worktree: `C:/Temp/DebateAI-agent-20261116-native/f11-retry-worktree`
Branch: `codex/f11-retry-20261116`
Base: `a24c87421fd06da65feed7e4fad03a54383c763a` (initial status clean).
Origin: `https://github.com/ErpeUser/DebateAI.git`; no fetch, push, reset or stash.

## Finding and semantic decision

The requested production fix already exists in ancestor
`ce745c1dab2212ac574fc83b921952fe90817611` ("fix: retry synthesizer after
failed persistence"). The supplied read-only report also identifies this as
already correct. At this base the fingerprint is assigned only after the real
`_apply_operations` returns, which is after its awaited `db.commit()`.
Production code was deliberately preserved; this delivery adds regression
coverage at the real applier/commit boundary instead of duplicating that fix.
There is no demonstrated unmodified-base RED and no new production fix claim.

The new tests run actual cycle serialization, structured operation dispatch,
adjustment and payload creation. Only the provider and storage I/O are doubled.
The synthetic transaction copies pending objects and publishes them only on a
successful commit, so the failed attempt cannot dirty the next input snapshot.

Policy verified: an empty model operation list or valid adjustment with no
changed fields is successfully completed after commit and consumes the input
fingerprint. A failed empty commit remains retryable. No eligible rows returns
without generating, committing or consuming a fingerprint. Model failure,
commit failure and cancellation leave inputs retryable; a previous successful
fingerprint survives a later failed cycle. Asked/strategic ownership filters,
dismissed exclusion, deterministic ordering and existing working-set/cooldown
tests are preserved.

## Evidence

Exact PowerShell command and Python runner: `run.md`. The installed interpreter
is Python 3.12.10 at the explicitly requested release-venv path. Each run uses
this worktree's backend as PYTHONPATH, a unique temporary DATA_DIR and working
directory, offline flags, blank provider keys and the synthetic port-1 DB URL.
The prompt loader is replaced with the bundled fallback in the new tests, so
they never inspect or seed user AI configuration. No real DB/provider/model,
user data, auth change, download, installation or background job is used.

- `F11_PHASE=red`: **1 test, 1 assertion failure, 0 errors, exit 1**.
  An in-memory mutation moves fingerprint assignment before the real applier.
  The first synthetic commit fails; the identical retry is suppressed and
  returns zero applied operations where one is required. The on-disk production
  file is never modified. `red.json` and `red.md` retain hashes and the failure.
- `F11_PHASE=green`: **37 tests passed, 0 failures/errors/skips, exit 0**.
  Includes 10 new tests plus existing guards, working-set and structured-agent
  suites. Expected error-path diagnostics from existing tests are not live
  provider failures. `green.json` and `green.md` retain hashes and results.

Initial harness attempts produced no test verdict: a stdin invocation was
interrupted (exit 1), an unbounded standard-loop attempt was interrupted
(exit 1), two runner-extraction errors exited 1, and a bounded standard-loop
attempt exited 1 after 45 seconds. Its traceback was in Python's Windows
`socket._fallback_socketpair -> accept`, called by ProactorEventLoop before
test setup. A separate import probe exited 0 and confirmed the isolated module.
The final recorded runs use a timer-only SelectorEventLoop with real asyncio
tasks/timers and no self-pipe. Its selector rejects I/O registration and the
loop rejects cross-thread wakeups. This is mocked-I/O evidence, not a native
Windows socket/proactor pass. The tests themselves keep the standard unittest
base class so the controller can run them with the normal Windows event loop.

Serena initial instructions loaded with this worktree active. Symbol-tool
documentation lookup was denied by the never-approval policy; targeted file
reads and rg were used. No onboarding or configuration files were written.

## Remaining limits

Controller owns independent review, integration and full regression as
requested. No real PostgreSQL, model, EXE, hardware, release or provider-login
acceptance is claimed. The existing per-operation error handling, concurrent
snapshot races, restart durability and broader F11 journal/F12 work remain
outside this ticket. A successful return from the existing applier is the
cycle's success boundary; this ticket does not redesign operation outcomes.
Only the named test file and this evidence directory are delivered.

## Commit blocker

After the focused green run and hash verification, an explicit-path `git add`
failed with exit 1: Git could not create
`C:/Users/User/Datein/Coding/DebateAI/.git/worktrees/f11-retry-worktree/index.lock`
(`Permission denied`). That common Git metadata directory is outside the
sandbox writable roots. No commit was attempted after failed staging; no
alternative index, metadata relocation or permission bypass was used. HEAD
remains the requested base. The controller must stage and commit the listed
files from an environment authorized to write that Git metadata directory.
