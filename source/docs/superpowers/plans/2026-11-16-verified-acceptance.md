# DebateAI verified implementation plan

Spec: user-supplied implementation masterprompt V2 (65 A/F/R gates and separate historical 276 inventory).
Goal: deliver tested fixes and the requested reusable acceptance entry point without treating software checks as hardware or release approval.
Base: ac51b3730a58b143715b49e63d707654d948ed59. Audio fix: 1f2de5adaa77d585c806d5d55bfff6035b87632f.
Actual checkout: C:/Users/User/Datein/Coding/DebateAI. Isolated linked worktree: evidence/implementation-20261116.

## Global constraints
Preserve stashes, untracked user files, AppData, keys, browser state and models. No force push, production publication, model download or billable provider requests. Python 3.12 / Node 24. Read actual sources; historical results are not current evidence.

## Tasks
1. Audio archive fix: validate exact PCM format before repair; exclusive creation; terminal close; descriptor cleanup. Native scope run: 19 tests, 18 passed, 1 symlink permission skip. Full backend/hardware not accepted.
2. Reproduce full backend baseline; investigate each failure before patching. Correct stale test assumptions without undoing safe key preservation or durable transcript reload. Add behavioral regression assertions.
3. Implement acceptance executor with tests first: bounded output, no shell evaluation, owned-process-tree cleanup including successful parents, continue independent tasks, retain failed prerequisites.
4. Implement inventory, profiles, Python/PowerShell entry, reports and safe resume: zero-test or skipped runs cannot imply complete acceptance; separate 65 and 276 identities; no commands from saved JSON; no overwritten evidence.
5. Run native runner tests, full affected suites, review changes, commit and push the existing hardening branch. Inspect current remote and CI before integration.
6. Continue remaining masterprompt packages from verified state; resolve original historical definitions and retain all unmet gates explicitly. Implement real capabilities rather than claim implementation from an inventory file.

## Review focus
Process descendants surviving parent exit; credential fragments at log boundaries; empty/skip-only tests; untrusted report HTML; .env/real database leakage; Windows argument quoting; loss of source changes; conflicting parallel branches.

## Evidence ledger
2026-11-16: Native device available, root clean except user .agents/ and Reviews/. Two existing stashes left unchanged. Linked worktree starts from published audio fix. Native Python 3.12.10 audio tests pass except symlink privilege skip; evidence outside Git in evidence/implementation-run-20261116/audio-native-4f32c0c3. Full backend baseline launched separately, pending.
Ruling: use author self-review because no independent subagent tool is available; do not claim independent review.
Ruling: previous Linux acceptance drafts were not persisted in this checkout. Their reported tests do not prove the delivered implementation; implement and test here before publication.
