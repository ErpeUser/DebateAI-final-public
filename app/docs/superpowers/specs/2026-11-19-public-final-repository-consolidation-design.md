# DebateAI: public final repository consolidation design

## Intent

Create one public final repository from the complete private DebateAI source tree and the verified cleanup work already represented by PR #24. Remove the confusing sibling Git metadata directory, preserve all product behavior and private-only source modules, and publish only files that pass an explicit secret, personal-data, generated-artifact and license review.

## Goals

- Keep the complete local application source, AI prompts, tests, release scripts, workflows and documentation that exist in the private checkout.
- Move Git metadata into a normal internal `.git/` directory under the repository root.
- Make `app/scripts/workspace_refs.py` resolve the internal `.git/` directory and retain compatibility with pointer-style checkouts during migration.
- Keep `runtime/`, `DebateAI_Generated/`, local configuration, caches, credentials and user data out of Git while preserving the existing runtime locally.
- Publish one verified public repository and preserve a recoverable local and remote snapshot until the final repository is independently cloned and checked.
- Retire `ErpeUser/DebateAI` and `ErpeUser/DebateAI-Source` only after the final public repository passes the agreed checks.

## Non-goals

- Reorganizing backend service modules by filename during repository migration.
- Moving or rewriting `%LOCALAPPDATA%/DebateAI` data.
- Modifying the installed `runtime/DebateAI/_internal` bundle in place.
- Inventing update URLs, public keys, CI credentials or deployment configuration.
- Treating the public source snapshot as a replacement for private-only modules or tests.

## Anti-goals

- No force-push, history rewrite or destructive cleanup before a verified final clone exists.
- No publication of secrets, personal recordings, transcripts, databases, runtime binaries, generated reports or local configuration.
- No deletion of either existing GitHub repository before the final repository has the complete approved tree and a successful clean-clone audit.

## Findings that drive the design

- The private working tree contains the exact 37 file blobs from PR #24, while local `master` still points to the older `79c095c` commit.
- The public `DebateAI-Source` snapshot shares 767 of 768 paths with the private tree. 761 common files are byte-identical. Its six differences are `.gitignore`, `README.md` and whitespace-only changes in four files.
- The private tree has 303 additional paths, including private-only configuration, AI prompts, release code and tests. Those files remain part of the product source and require public-safety review before publication.
- `runtime/DebateAI` is an older ignored installed bundle and stays outside the source migration.
- GitHub currently has four open Dependabot PRs across the two repositories. The two PRs in each repository have identical `package.json` and `package-lock.json` blobs, so only one dependency update can be retained in the final repository.
- The newer public-snapshot dependency candidate uses `wrangler` `4.165.0`. Its isolated worker install and 13 worker tests pass. The private-repository candidates use `4.164.0` and remain unmerged.

## Chosen architecture

The final checkout uses the conventional layout below.

```text
DebateAI/
|-- .git/                         internal Git metadata
|-- .github/                      versioned workflows and governance
|-- .codex/                       ignored local tooling state
|-- app/                          versioned source, tests, prompts and docs
|-- runtime/DebateAI/             ignored installed bundle
|-- DebateAI_Generated/           ignored rebuildable outputs and reports
|-- Start-DebateAI.*              versioned recovery entrypoints
`-- README.md, AGENTS.md, .gitignore, .gitattributes
```

The repository root remains the only source root. `workspace_refs.py` resolves the root, source paths, runtime, Generated and Git metadata through one reference map. It reports whether Git and runtime are independent of Generated and refuses missing essential paths in strict mode. A legacy `.git` pointer is still readable for migration and recovery, but new clones use the standard directory.

## Public-release policy

- Start from the private tree plus the PR #24 content, then add the existing MIT license at the repository root without changing its text or copyright notice.
- Compare the public candidate against the current private tree by path and Git blob. Investigate every private-only file, especially release workers, admin routes, configuration modules, prompts, fixtures and tests.
- Run repository layout, source-only workspace, secret, credential, database, binary and license checks against the candidate.
- Keep public source that is required for reproducible understanding and tests. Remove only files proven to contain private data, live credentials, personal information or generated artifacts, and record each removal in the release manifest.
- Keep `.github/workflows/` and the blocking layout workflow. Public Actions must not receive private secrets or publish releases automatically.
- Carry one reviewed Dependabot configuration into the final repository. Close duplicate dependency PRs and regenerate the lockfile once against the final tree instead of copying two parallel Dependabot branches.

## Migration sequence

1. Freeze the current working tree and create a recoverable local snapshot of the external Git metadata, current files and ignored runtime.
2. Audit all paths and contents, including the 303 private-only paths, against the public-release policy.
3. Convert the checkout to an internal `.git/` directory while preserving refs, objects, reflogs, remotes and the working-tree contents.
4. Update `workspace_refs.py`, `README.md`, `AGENTS.md`, repository documentation and tests to describe the internal metadata layout and automatic references.
5. Commit the consolidated candidate on a dedicated migration branch. Run all targeted local checks and the public-safety audit.
6. Create a temporary public final repository, push the verified branch and perform a fresh clone audit with no ignored local artifacts.
7. Compare the fresh clone against the approved candidate, verify the default branch and workflows, and record the final commit hash.
8. Delete the two old GitHub repositories only after the fresh clone and remote checks pass. Rename the temporary final repository to `DebateAI` if the chosen final name is available.

## Verification gates

- Git metadata relocation preserves `HEAD`, `master`, remotes, objects, reflogs and the exact working-tree blobs.
- `python app/scripts/verify_repository_layout.py` passes on the candidate.
- `python app/scripts/workspace_refs.py --source-only --strict` passes without Generated or runtime.
- Targeted backend, frontend, desktop, docs-site, release and repository-layout tests pass where dependencies are available.
- `git diff --check` passes.
- Secret and personal-data scans find no credentials, databases, recordings, transcripts, local configuration or runtime binaries.
- Fresh public clone contains the complete approved source tree, no ignored artifacts, no private metadata and the expected workflows.

## Open decision

The final public repository name must be confirmed before the temporary repository is created and before either existing repository is deleted. The recommended sequence uses a temporary public name, verifies it, then renames it to `DebateAI`.
