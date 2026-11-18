# GitHub repository hygiene and structure enforcement

> **For agentic workers:** Use superpowers:executing-plans / TDD. User explicitly requested direct implementation.

**Goal:** Make the private GitHub repository enforce the versioned DebateAI structure, ignore only disposable/secret files, and provide operational CI and maintainable repository governance.

**Architecture:** A dependency-free Python script checks version-controlled paths, key structure contracts and ignore rules. Root GitHub Actions runs that script as a required failing step independent of the existing advisory Sentrux metrics. Repository CODEOWNERS, PR checklist, Dependabot and GitHub settings align with the true app/ source tree.

**Stack:** Git, Python 3.12, GitHub Actions, GitHub REST / gh.

**Spec:** app/docs/ORDNERSTRUKTUR_ZIELBILD.md; app/docs/generated-workspace.md; root AGENTS.md.

## Global constraints
- Keep private GitHub repository private; never force push, rewrite master, remove live files or touch %LOCALAPPDATA%/DebateAI, runtime/ or external Git metadata.
- Preserve original local master and uncommitted changes. Any GitHub publication goes to a new branch and PR, not directly to master.
- Keep app/site and app/docs-site separate; app/.github/release-notes is versioned source data, not an executable Actions workflow folder.
- Verify .env.example and all source lockfiles remain tracked; ignore only runtime/cache/state/secret artifacts.
- Existing CI runner failures are Billing & plans pre-job errors, not code-test failures. Do not claim hosted green checks until GitHub has lifted the account block.
- Branch protection / rulesets currently return 403 for this private repo on the account plan; never make the repo public to enable them.

## Review focus
1. Generator or runtime files accidentally added to Git: check rejects.
2. Secret environment variants or private keys: remain ignored, examples versioned.
3. Source folder moved or root .github workflows nested under app: check rejects.
4. Windows/Linux filesystem collisions and illegal paths: check rejects.
5. CI yaml still valid and truly fatal on structural violations; advisory Sentrux stays separate.

---

### Task 1 — Gitignore and versioned structure guard
**Files:** .gitignore, app/scripts/verify_repository_layout.py, app/scripts/tests/test_repository_layout.py.
**Interfaces:** validate_paths(paths: Iterable[str]) -> list[str]; command line --repo-root.
- [ ] RED: regression tests for protected roots, secrets, binaries, missing key files and normal checkout.
- [ ] GREEN: implement path checks and precise Git ignore exclusions.
- [ ] Verify tracked files and ignore behavior.

### Task 2 — CI and team governance
**Files:** .github/workflows/structure.yml, .github/CODEOWNERS, .github/PULL_REQUEST_TEMPLATE.md, .github/dependabot.yml, docs/github-repository.md, root README.md.
- [ ] RED: tests checking blocking structure step, CODEOWNERS and versioned root workflow path.
- [ ] GREEN: root-only Actions guard, code review guidance and dependency update policies.
- [ ] Verify syntax and local test suite.

### Task 3 — GitHub remote settings and integration
**Files:** GitHub repository configuration; optionally new remote branch and PR.
- [ ] Inspect settings and GitHub Actions failure reasons.
- [ ] Enable security alerts and enforce safe action permissions where supported; verify via read-back.
- [ ] Preserve local master changes; stage a separate isolated publication branch after tests.
- [ ] Verify remote PR/check status and record GitHub plan/billing blockers instead of claiming success.

## Results (local verification)

- 102/102 script tests completed successfully (2 skipped), including 10 new layout regressions; ran both in original working copy and an isolated clean Git checkout without runtime/ or Generated/.
- Native Windows headless bundle smoke passed (health, local ASR, testlab and clean shutdown).
- Independent PowerShell starter/signed-recovery rollback and build-contract tests passed in the isolated checkout.
- Six root workflow/Dependabot YAML files parsed; `git diff --check` passed.
- `verify_repository_layout.py` and `workspace_refs.py --source-only --strict` passed with Generated absent in the clean clone.
- GitHub private repo settings verified: required Actions SHA pinning, vulnerability alerts, Dependabot security updates, automatic merged-branch deletion and updateable PR branches enabled; default workflow permissions remain read-only, auto-merge disabled.
- GitHub Branch Protection/Rulesets: HTTP 403 (private repo plan limit). Account Billing & plans prevents all hosted jobs from starting. Do not claim hosted CI green or a branch lock.
- No forced push, no runtime modifications, no deletions or changes to the original master checkout. Publish through an independent PR after final checks.
