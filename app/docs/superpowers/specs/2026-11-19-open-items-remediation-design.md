# Open-items remediation design

Stand: 2026-11-19

## Intent and scope

Move the open-items register to a reproducible acceptance state. Fix issues that
are reproducible in the public checkout and keep external release gates explicit.

Goals:

- The backend suite must not require private evidence in the public checkout.
- The Playwright lab must use a supported, pinned GitHub runner.
- The Windows startup contract must return exit code 0 after successful checks.
- Documentation must point to the canonical status file and fresh evidence.

External gates remain blocked until a real Windows device, provider accounts,
publisher identity, and production R2 credentials are supplied. No test key or
invented release URL is acceptable.

## Approaches

Re-adding the private matrix would violate the repository privacy contract;
removing its tests would lose local coverage. The selected approach keeps the
matrix checks active when an authorized evidence file exists and skips them with
a clear reason in the public checkout. The browser job is pinned to
ubuntu-24.04 because the current Playwright version rejects ubuntu-26.04.

## Acceptance criteria

- AC-01 public checkout skips the private matrix checks without FileNotFoundError.
- AC-02 an authorized matrix file still runs both checks.
- AC-03 calibration-browser uses ubuntu-24.04.
- AC-04 startup test exits 0 after success.
- AC-05 docs and Oracle npm audits report zero high/critical findings.
- AC-06 status and README use the canonical open-items path.
- AC-07 hardware, signature, and R2 gates are marked BLOCKED, not passed.
- AC-08 layout and source-only guards remain green.
- AC-09 targeted tests and builds are reproducible.
- AC-10 the delivered commit is verified on main with no feature branch or PR.

## Six phases

1. Discovery and capability preflight.
2. Research and reuse of existing tests, guards, and lockfiles.
3. Specification, measurable acceptance criteria, and atomic plan.
4. Minimal implementation on main.
5. Adversarial functional, security, and layout verification.
6. Delivery with exact commit and fresh GitHub evidence.
