 # Plan: Open-items remediation

## Goal

Make the public checkout pass every reproducible open-item gate while keeping
private evidence and production release credentials outside the repository.

## Architecture and tech stack

The changes touch Python unittest contracts, PowerShell release checks, GitHub
Actions YAML, Markdown status records, and existing npm workspaces. No runtime
dependency or product API is introduced.

## Global constraints

- Work directly on `main` as required by `AGENTS.md`.
- Preserve `.ai` privacy, generated/runtime boundaries, and existing lockfiles.
- Do not create a PR, force-push, publish a release, or invent signing/R2 data.
- Every changed behavior gets a targeted regression check before delivery.

## Tasks

- [ ] Keep the V3 matrix test active for authorized private evidence and skip it
   with an explicit reason in the public checkout.
- [ ] Pin the calibration browser job to ubuntu-24.04.
- [ ] Make the startup PowerShell contract end with explicit exit 0 after success.
- [ ] Fix stale documentation links and refresh the status register.
- [ ] Run targeted tests, builds, layout guards, and source-only checks.
- [ ] Commit to main, push, and fetch workflow status for the exact new SHA.

## Spec and TDD steps

1. Run the V3 matrix test before the change and capture the missing-private-file
   failure.
2. Add the optional-path skip, then run the same test and an authorized matrix
   fixture check.
3. Pin the browser runner and make the PowerShell success exit explicit.
4. Run layout, source-only, docs, frontend, Oracle, and audit checks.
5. Update status documentation only from the resulting evidence.

## Review focus

- A missing private file must never become a false pass for an authorized file.
- The browser runner pin must match the Playwright version in the workflow.
- PowerShell failure paths must remain nonzero; only the completed path exits 0.
- Status wording must distinguish local evidence from GitHub and operator gates.

## Test ledger

- Backend V3 matrix unit test (public and optional private path).
- PowerShell startup/build contract tests where Windows is available.
- Docs-site `npm test`, `npm run build`, and high-severity npm audit.
- Oracle high-severity npm audit and frontend test/build/PWA checks.
- `verify_repository_layout.py` and `workspace_refs.py --source-only --strict`.
- GitHub workflow runs/statuses for the delivered commit.

## Exact commands

```text
python -m unittest app.backend.tests.test_v3_matrix_coverage -v
python app/scripts/verify_repository_layout.py
python app/scripts/workspace_refs.py --source-only --strict
cd app/docs-site && npm test && npm run build && npm audit --audit-level=high
cd app/frontend && npm test && npm run build && npm run test:pwa -- --dist
cd app/desktop/chatgpt_oracle && npm audit --audit-level=high
```
