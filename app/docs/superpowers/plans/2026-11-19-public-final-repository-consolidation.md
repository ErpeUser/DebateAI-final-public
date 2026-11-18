# Public Final Repository Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one public, complete DebateAI repository with internal Git metadata, automatic workspace references, one tested dependency update, and no private or generated data.

**Architecture:** Preserve the private checkout as the source of truth while converting its external Git metadata pointer into a normal internal `.git/` directory. Keep product source under `app/`, ignored runtime and Generated artifacts outside Git, and make `workspace_refs.py` the single path/reference auditor. Create and verify a temporary public repository before retiring the two existing repositories.

**Tech Stack:** Git, Python 3.12-compatible scripts and unittest, PowerShell contract tests, Node.js 24, npm lockfiles, GitHub Actions, GitHub repository APIs.

**Spec:** `app/docs/superpowers/specs/2026-11-19-public-final-repository-consolidation-design.md`

## Global Constraints

- Preserve all private-tree functions, AI prompts, tests, release scripts and workflows unless the public-safety audit proves a file contains private data or a non-redistributable asset.
- Keep `%LOCALAPPDATA%/DebateAI`, `runtime/DebateAI/_internal`, existing backups, and generated artifacts out of destructive cleanup.
- Use the conventional internal `.git/` directory in the final checkout and preserve refs, objects, reflogs and remotes during relocation.
- Keep `runtime/`, `DebateAI_Generated/`, local configuration, caches, credentials, databases, recordings and transcripts ignored.
- Publish only after secret, personal-data, generated-file and license audits pass.
- Keep `.github/workflows/` and the repository-layout gate. Do not add private secrets or automatic release publication.
- Consolidate the duplicate Dependabot updates into one reviewed `wrangler` `4.165.0` dependency state only after tests pass.
- Do not delete either existing GitHub repository before a fresh public clone has been checked against the approved candidate.

## Review Focus

- Git metadata relocation must preserve `HEAD`, refs, reflogs and the working tree. Test with a before/after ref and blob manifest.
- A clean source clone must work without Generated or runtime. Test `workspace_refs.py --source-only --strict` in a temporary clone.
- Public release must reject secrets, local databases, runtime binaries and generated reports. Test the public audit against positive and negative fixtures.
- Dependency consolidation must keep the release worker functional. Test `npm ci` and the worker test suite with `wrangler` `4.165.0`.
- Final publication must contain the complete approved private-only source set. Test path and blob equality between the candidate and the fresh public clone.

---

### Task 1: Freeze and inventory the current source tree

**Files:**
- Create: `work/repository-inventory-2026-11-19.json` outside the repository
- Read: `C:/Users/User/Datein/Coding/DebateAI-GIT-METADATA/`
- Read: `C:/Users/User/Datein/Coding/DebateAI/`

**Interfaces:**
- Produces a path, blob, ref and ignored-artifact inventory used by all later tasks.

- [ ] **Step 1: Record the current Git state**

Capture `HEAD`, all local and remote refs, remotes, reflogs, stashes, tracked paths, non-ignored untracked paths, and ignored runtime/Generated paths without modifying the checkout.

- [ ] **Step 2: Record the working-tree blob manifest**

Hash every tracked and non-ignored untracked file with `git hash-object` and store the path-to-blob mapping in the temporary inventory.

- [ ] **Step 3: Run the baseline checks**

Run `git diff --check`, `python app/scripts/verify_repository_layout.py`, `python -m unittest app/scripts/tests/test_repository_layout.py -q`, and `python app/scripts/workspace_refs.py --source-only --strict`. Record exit codes and short summaries.

- [ ] **Step 4: Review the inventory**

Confirm that the only active source changes are the PR #24 file set plus the new consolidation spec and plan, and that no personal data or runtime bundle is included.

### Task 2: Move Git metadata into the repository root

**Files:**
- Modify: `C:/Users/User/Datein/Coding/DebateAI/.git`
- Create: `C:/Users/User/Datein/Coding/DebateAI/.git/`
- Preserve: `C:/Users/User/Datein/Coding/DebateAI-GIT-METADATA/`

**Interfaces:**
- Consumes the Task 1 inventory.
- Produces a normal internal `.git/` directory with the same Git database and working-tree state.

- [ ] **Step 1: Make a recoverable metadata copy**

Copy the external Git metadata to a uniquely named local backup outside the source tree. Verify object counts and the `HEAD`/ref manifest before changing the active pointer.

- [ ] **Step 2: Materialize the internal `.git/` directory**

Copy the metadata into `DebateAI/.git/`, remove the external-only `core.worktree` setting from the copied config, and preserve remote and branch configuration. Keep the external sibling untouched until final verification.

- [ ] **Step 3: Repoint Git and validate refs**

Replace the pointer file with the internal directory and verify `git rev-parse`, `git status`, `git branch -a -vv`, `git remote -v`, `git reflog`, and `git fsck --no-reflogs` against the Task 1 inventory.

- [ ] **Step 4: Validate working-tree equality**

Recompute the blob manifest and require exact equality for all existing tracked and non-ignored untracked files.

### Task 3: Make automatic references location-independent

**Files:**
- Modify: `app/scripts/workspace_refs.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `app/docs/generated-workspace.md`
- Modify: `app/docs/github-repository.md`
- Modify: `app/docs/ORDNERSTRUKTUR_ZIELBILD.md`
- Test: `app/scripts/tests/test_workspace_disposability.py`

**Interfaces:**
- `external_git_dir()` becomes a compatibility resolver that returns the internal `.git/` directory for normal clones and follows a pointer only for legacy checkouts.
- `collect()` reports `git_metadata` inside the root for normal clones and fails strict mode when metadata is under Generated.

- [ ] **Step 1: Add failing reference-resolution tests**

Cover an internal `.git/` directory, a legacy relative pointer, an absolute pointer, a missing pointer target, and Generated metadata rejection.

- [ ] **Step 2: Implement the resolver change**

Use the repository root as the anchor for internal `.git/` and preserve the existing pointer parser only as a migration compatibility path.

- [ ] **Step 3: Update documentation**

Describe `.git/` as the standard layout, the legacy sibling as a migration backup, and the automatic resource map as the source of truth for runtime, Generated and source paths.

- [ ] **Step 4: Run the targeted tests**

Run `python -m unittest app/scripts/tests/test_workspace_disposability.py -q` and `python app/scripts/workspace_refs.py --source-only --strict`.

### Task 4: Build the public-release audit

**Files:**
- Create: `app/scripts/public_release_audit.py`
- Create: `app/scripts/tests/test_public_release_audit.py`
- Modify: `app/scripts/verify_repository_layout.py` only if the existing gate lacks a required public check

**Interfaces:**
- `audit(repo_root: Path) -> dict` returns categorized findings with paths and rule identifiers, never secret values.
- `main()` exits nonzero for secret markers, local databases, generated/runtime artifacts, private Git metadata, or unresolved license files.

- [ ] **Step 1: Write failing fixture tests**

Test safe source, a private-key marker, a literal credential assignment, a database file, a runtime executable, a Generated path, a `.git` pointer to an external directory, and a missing root license.

- [ ] **Step 2: Implement bounded path and content checks**

Scan only the candidate tree, skip binary content safely, report paths and rule names, and avoid printing matched values.

- [ ] **Step 3: Add license and public-asset checks**

Require the existing MIT text at the root and identify non-source binary assets for explicit review instead of deleting them automatically.

- [ ] **Step 4: Run the audit against the current candidate**

Classify findings into retained product source, test fixtures, generated files, local data, and unresolved items. Do not publish while unresolved items remain.

### Task 5: Consolidate dependency updates

**Files:**
- Modify: `app/release-signing-worker/package.json`
- Modify: `app/release-signing-worker/package-lock.json`
- Modify: `.github/dependabot.yml`
- Modify: `app/docs/github-repository.md`

**Interfaces:**
- Produces one lockfile state using `wrangler` `4.165.0` and one Dependabot configuration for the final repository.

- [ ] **Step 1: Reproduce the dependency candidate in an isolated copy**

Generate the lockfile from the complete private worker source with `wrangler` `4.165.0`, keeping install outputs outside the repository.

- [ ] **Step 2: Run worker install and tests**

Run `npm ci --ignore-scripts --no-audit --no-fund` and `npm test -- --test-reporter=spec` in the isolated worker copy. Require all worker tests to pass.

- [ ] **Step 3: Apply the verified dependency state**

Update the final candidate package files and retain one grouped Dependabot definition. Do not merge both private PR #22/#23 or both public PR #1/#2.

- [ ] **Step 4: Re-run the worker tests in the candidate**

Repeat install and tests from the candidate tree and record the exact package-lock hash.

### Task 6: Prepare and verify the public candidate

**Files:**
- Create: `LICENSE` copied exactly from `app/LICENSE`
- Modify: `README.md`
- Modify: `.gitignore`
- Modify: `app/docs/github-repository.md`
- Modify: `app/docs/generated-workspace.md`

**Interfaces:**
- Produces a complete candidate tree containing private-only product source and no private or generated material.

- [ ] **Step 1: Add the root license without changing attribution**

Copy the existing MIT license text exactly and verify it matches `app/LICENSE` byte-for-byte.

- [ ] **Step 2: Review all private-only paths**

Inspect the 303 paths absent from the public snapshot, with special attention to the 20 source-like files, AI prompts, admin/release workers, fixtures, images, fonts and local configuration templates.

- [ ] **Step 3: Run public-safety audit and layout gates**

Run `python app/scripts/public_release_audit.py`, `python app/scripts/verify_repository_layout.py`, `python app/scripts/workspace_refs.py --source-only --strict`, and `git diff --check`.

- [ ] **Step 4: Run targeted product checks**

Run the repository-layout tests, workspace disposability tests, recovery/start contract tests, worker tests, and available backend/frontend/desktop/docs-site suites. Record any dependency- or platform-blocked suites separately.

- [ ] **Step 5: Commit the candidate**

Commit the verified candidate on a dedicated migration branch with a message describing the public consolidation and dependency state.

### Task 7: Publish and audit a fresh public clone

**Files:**
- Create: temporary public GitHub repository `ErpeUser/DebateAI-final-public`
- Create: temporary fresh clone under `work/`

**Interfaces:**
- Produces a public repository URL and final commit hash that match the approved candidate.

- [ ] **Step 1: Create the temporary public repository**

Create it without README, license, workflow secrets, or generated files, then push the verified candidate branch.

- [ ] **Step 2: Set the default branch**

Set `main` or `master` according to the final README and workflow configuration, then verify the repository visibility, branch, and workflow paths.

- [ ] **Step 3: Clone without local artifacts**

Clone the public repository into a fresh directory and compare tracked paths and blobs against the approved candidate.

- [ ] **Step 4: Run source-only verification in the clone**

Run the layout gate, public audit and source-only workspace audit without Generated, runtime or local configuration.

- [ ] **Step 5: Record the final remote evidence**

Save the URL, default branch, commit hash, path count and audit summaries before any deletion.

### Task 8: Retire the duplicate repositories

**Files:**
- Remote: `ErpeUser/DebateAI`
- Remote: `ErpeUser/DebateAI-Source`

**Interfaces:**
- Leaves one verified public final repository and no duplicate Dependabot branches.

- [ ] **Step 1: Reconfirm destructive scope**

Display the exact repository names, final clone URL and recorded commit hash before deletion.

- [ ] **Step 2: Delete the two old repositories**

Delete only after the fresh public clone, branch, blob and safety audits pass. Preserve the local metadata backup until the final remote is independently cloned again.

- [ ] **Step 3: Rename the temporary repository if requested**

Rename `DebateAI-final-public` to `DebateAI` only after the old name is released and the final URL is verified.

- [ ] **Step 4: Verify the final public repository**

Check the final URL, default branch, active branches, workflows, Dependabot configuration and clean clone one last time.

## Execution Notes

- Do not use a fresh public snapshot as the source of truth. Use the full private candidate and add only the root license needed for public discovery.
- Do not delete or rewrite the external metadata backup until the final clone has passed all gates.
- If any private-only file fails the public audit, stop publication and report the exact path and rule without exposing its value.
