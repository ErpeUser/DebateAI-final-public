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
