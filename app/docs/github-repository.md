# GitHub repository and local output contract

The public source repository is `ErpeUser/DebateAI-final-public` with
`main` as its default branch. The Windows checkout remains the canonical
private working copy. Public Git contains source, safe documentation, tests,
and build inputs. Runtime bundles, Generated output, acceptance evidence,
internal `.ai` status material, credentials, transcripts, databases, browser
sessions and user data stay out
of Git.

## Generated output

Build products, dependency caches, release staging, screenshots, provenance
reports and acceptance runs belong below `DebateAI_Generated/`. The canonical
subfolders are defined in `app/scripts/generated_paths.py`:

- `build/` for build and release staging
- `dependencies/` for local release environments
- `cache/` for package and tool caches
- `reports/acceptance/` for local acceptance runs
- `reports/benchmarks/` for benchmark exports
- `reports/provenance/` for workspace and folder-tree reports
- `reports/screenshots/` for local captures
- `tmp/` for disposable intermediate files

The layout guard fails when private acceptance evidence is tracked under
`app/docs/acceptance/` or when generated files appear in the public source
tree. `.gitignore` is a second line of defence and never replaces the guard.

## Direct-main agent workflow

Agents work directly on a checked-out `main`, commit the requested change,
and push `main` to `origin`. They do not create feature branches, routine
worktrees or pull requests.

Before a GitHub pull or push, run:

```powershell
python app/scripts/github_sync.py --pull --strict
```

This fetches and prunes remote refs, verifies the GitHub default branch, lists
all other branches and open pull requests, and then performs
an ff-only pull when the checkout is clean. A non-zero result means candidates
still need review.

For each candidate, inspect commits, changed files, tests and freshness. Apply
a standalone fix with a reviewed cherry-pick, combine complementary changes
in one local commit, or keep the newest compatible implementation when it
supersedes an older one. Resolve conflicts on `main`, test the result, and
record the disposition. Never blindly merge every candidate, close or delete
someone else's branch, or force-push.

GitHub Actions still validate pushes and can validate community pull requests.
They do not create commits, approve reviews, or publish local private data.
