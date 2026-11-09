# Debate AI V6 - private Windows release

This repository contains the privately published Windows x64 onedir release
candidate for Debate AI V6. The application is distributed as a release
asset, not as an unreviewed copy of the dirty development worktree.

## Download and start

1. Download `Backchannel-windows-x64.zip` from the GitHub release.
2. Verify it against `SHA256SUMS.txt`.
3. Extract the complete archive without renaming its `Backchannel/` root.
4. Start `Backchannel/Backchannel.exe`.
5. Keep the external `Backchannel/ai/` directory beside the executable when
   changing prompts or provider configuration.

The full runtime and the editable external AI files are described in
`START_HIER.md`. `release-manifest.json` records the build toolchain,
provenance and artifact hashes.

## Scope and evidence

The package was built from Git HEAD
`da2c5301f272142ae5d7bbb2ab10a7b5402ae20c` with the release Python 3.12.10
environment and PyInstaller 6.22.3. The executable, normal startup/health
smoke, external prompt/configuration smoke, archive update/rollback smoke,
and release-manifest tests were run before publication.

The release is private because the public upstream repository must not receive
binary release artifacts. A private repository does not turn the remaining
manual A06/A18/A21/A22 evaluations into automated passes.

## Source code

The `source/` directory contains the sanitized current source snapshot,
including backend, desktop, frontend, docs-site, tests, scripts, prompts and
release configuration. `SOURCE_SNAPSHOT_MANIFEST.json` lists every included
file and hash. It deliberately excludes Git metadata, virtual environments,
node_modules, generated build/dist folders, model/native binaries, audio,
databases, session data and `.env` files. It also excludes provider/account
overrides, browser profiles and cookies, OAuth/API login caches, local
storage, chat/conversation history, transcripts, logs and other per-machine
state. The current snapshot and its complete Git history were checked for
those data classes; the result is zero matching local-data files. Synthetic
credential strings used by redaction tests are retained as test fixtures and
are explicitly listed in the manifest; no live secret was included. See
`PRIVACY_AUDIT.md` for the exact checks and result.
