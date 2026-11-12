# DebateAI source provenance

## Current source

- Canonical repository: `https://github.com/ErpeUser/DebateAI`
- Repository ID: `1450951492` (private)
- Canonical product/runtime identity: `DebateAI`
- Identity-decoupling work is prepared on
  `codex/debateai-identity-decoupling`; the integrated commit is recorded by
  GitHub when the branch is merged.

The active source tree, desktop package, update contract, environment names,
request headers and WebSocket token protocol use DebateAI. Existing user data is
migrated once from legacy locations without deleting the source or overwriting
a non-empty canonical destination.

## Historical release provenance

The v0.6.6 Windows release was built from the 2026-11-09 audited snapshot:

- Historical upstream project: `https://github.com/talberthoule/backchannel.git`
- Historical private release repository: `https://github.com/ErpeUser/backchannel-v6-private`
- Historical build HEAD: `da2c5301f272142ae5d7bbb2ab10a7b5402ae20c`
- Historical worktree fingerprint: `afcd45972fc713db360e5d7f5cbc4271eac4829f6dea494b001e3636cbbc248a`
- Build format: Windows x64 PyInstaller onedir
- Python: 3.12.10
- PyInstaller: 6.22.3
- Release version/tag: `v0.6.6`

The historical snapshot and its manifests remain integrity records. They are not
active runtime inputs and are not rewritten as if they described the new build.
