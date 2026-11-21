# Workspace audit and target structure

Stand 21. November 2026. The complete file-level inventory is generated on
the local machine at
`DebateAI_Generated/reports/provenance/workspace-tree-full.md`. It includes
every file below the checkout, including the installed bundle and disposable
dependencies. Private user data under `%LOCALAPPDATA%/DebateAI` is outside the
inventory by design.

## Current boundaries

```text
DebateAI/
├── app/                         maintained source, tests, prompts and contracts
├── runtime/DebateAI/            one complete installed bundle, kept together
├── DebateAI_Generated/          disposable builds, caches, dependencies, logs and reports
├── .github/                     repository workflows and ownership metadata
├── .git/                        Git metadata, never moved into Generated
├── AGENTS.md, README.md, LICENSE
├── Start-DebateAI.cmd/.ps1      recovery and launch entry points
├── pyproject.toml, ruff.toml    repository tooling configuration
└── .gitignore, .gitattributes
```

The measured local inventory is 30,750 files in `app/`, 32,862 files in the
installed bundle and 101,297 files in `DebateAI_Generated/` at audit time. The
generated dependency virtual environment accounts for most of that size.

## Disposition

- The root `.ruff_cache` was moved to `DebateAI_Generated/cache/ruff` and Ruff
  now writes there through `ruff.toml`.
- `runtime/DebateAI/` stays outside Generated because the launcher expects this
  canonical path and its `_internal/` directory is an inseparable bundle.
- `app/desktop/pgsql`, `app/desktop/ffmpeg`, the Oracle Node runtime and similar
  downloaded desktop inputs stay at their toolchain-compatible paths. Their
  source scripts and `.gitignore` entries already treat them as disposable.
- Source documentation, manifests, lockfiles, prompts, tests and migration
  tools stay in `app/`. They are versioned inputs or explicit compatibility
  evidence, not generated cache.
- No source file met the evidence threshold for deletion or combination. The
  legacy importer is explicitly invoked and covered by a regression test. The
  release manifests and historical records are referenced by audits and tests.

## Target generated workspace

```text
DebateAI_Generated/
├── build/                       staged releases, recovery and native smoke data
├── cache/
│   ├── npm/                     npm download cache
│   ├── pip/                     pip download cache
│   └── ruff/                    Ruff analysis cache
├── dependencies/python/         disposable release virtual environment
├── downloads/                   verified build downloads
├── logs/                        disposable command logs
├── reports/
│   ├── acceptance/
│   ├── benchmarks/
│   ├── provenance/              reference maps and full workspace tree
│   └── screenshots/
└── tmp/                         short-lived staging
```

Regenerate the complete inventory with
`python app/scripts/export_project_tree.py --full --depth 99 --limit 1000000
--output DebateAI_Generated/reports/provenance/workspace-tree-full.md`.

## VS Code entry points

The local `.vscode/` profile now contains repository-relative tasks for layout,
workspace-reference, tree and focused Python checks. It recommends Python,
Pylance, Ruff, ESLint, Prettier, Docker, YAML, GitLens and Path IntelliSense,
with automatic Python and TypeScript import suggestions. The profile remains
ignored local editor state and does not become part of the public source tree.
