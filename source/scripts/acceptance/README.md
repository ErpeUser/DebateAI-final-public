# Acceptance command adapter

Use the existing installed project Python; this command never installs dependencies:

```powershell
source\.release-venv\Scripts\python.exe source\scripts\run_acceptance.py --profile fast --output C:\Temp\debateai-acceptance-unique
source\.release-venv\Scripts\python.exe source\scripts\run_acceptance.py --profile full-software --output C:\Temp\debateai-full-unique
```

The output directory must be new, private and outside active user data. `fast`
runs the focused safety and adapter tests. `full-software` wraps the existing
backend pytest, desktop unittest, frontend Node and docs-site Node suites;
it does not replace them. Output includes JSON, HTML, bounded logs, exact
commands/exits/counts/hashes, source commit and actual source-content identity.
One task-finished JSON event is emitted after each completed command.

Missing/empty test evidence is never PASS. All-skipped suites are NOT_RUN.
Inconsistent JUnit counts are rejected; passing pytest subtests omitted as case
nodes are counted separately only when the same child's terminal summary and
suite total reconcile. Existing JUnit/log files are never reused. Source-byte
changes during a campaign fail its stability gate. Source symlinks/junctions
are refused instead of silently hashing unrelated content.

Child commands inherit only selected non-secret environment variables and use
isolated synthetic profile/data directories. Existing `.env` files at command
or import roots and their ancestors block execution without being read/deleted.
This is for reviewed project commands, not a privilege or network sandbox.

A Windows Job Object (or POSIX process group) owns launched descendants from
before execution. Cleanup runs on success and timeout. Output is capped at
4 MiB; overflow and uncertain cleanup fail. Failed commands, timeouts, skips,
and earlier failed campaign reports remain evidence, not silently excluded.

`windows-native`, `hardware`, and `production-release` never substitute software
results for their real external protocols. `release_decision` remains
BLOCKED_EXTERNAL. No EXE, microphone, human rating, signature, installation or
publication is performed by this adapter. Independent review is a separate gate.

The 2026-11-16 full-software campaign exposed four docs-site failures (two
credential-link assertions and missing local `@noble/hashes`/`jose` dependencies).
Those are separate repair/setup tasks, not runner successes or hidden skips.

Process helpers were reused from the existing isolated acceptance draft; this
file documents the single current command, not a second test framework.
