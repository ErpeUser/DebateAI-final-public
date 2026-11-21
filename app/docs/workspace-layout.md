# DebateAI workspace layout

The repository has three operational areas with separate ownership.

```text
DebateAI/
├── app/                         versioned source, tests, prompts and build contracts
│   ├── backend/
│   ├── desktop/
│   ├── frontend/
│   ├── docs/                    maintained product and recovery documentation
│   ├── docs-site/
│   ├── release-signing-worker/
│   └── scripts/                 audits, builds and release tooling
├── runtime/
│   └── DebateAI/                one active installed bundle
├── DebateAI_Generated/
│   ├── build/                   staged releases, recovery and native smoke data
│   ├── cache/                   npm, pip and tool caches
│   ├── dependencies/            disposable Python and Node tool environments
│   ├── downloads/               verified build downloads
│   ├── logs/                    disposable command logs
│   ├── reports/                 quality, provenance and test evidence
│   └── tmp/                     short-lived staging files
├── .github/                     repository workflows and templates
└── .git/                        Git metadata
```

The active runtime bundle is independent of `DebateAI_Generated`. The bundle's
`_internal` directory is an inseparable unit and is never deduplicated or
relocated member by member. Private application data remains under
`%LOCALAPPDATA%/DebateAI`.

Package-local `node_modules`, frontend `dist` output and downloaded desktop
assets remain in their toolchain-compatible source locations until the build
tools support a verified relocation. They are ignored and disposable. Python
bytecode, test caches and editor caches are disposable and are removed during
workspace cleanup.

The canonical reference map is maintained by
`app/scripts/workspace_refs.py`. It records source files, the active runtime,
release outputs and native smoke output paths without copying any files.
