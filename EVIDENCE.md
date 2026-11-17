# Evidence register

The repository keeps source, reproducible tests and provenance. Machine state, credentials, recordings, databases, model caches and generated release packages stay outside Git.

## Current cleanup evidence

- Baseline at `946144b4e58dd354db76bdb80c23d2fa4ed67a95`: 1,196 tracked files, 136 directories, 21,788,705 tracked bytes, 203,814 lines across code/config files.
- Final cleanup commit `a9012b3a67a9d9a327c0eea503d4ea7a8aa4f87e`: 1,195 tracked files, 136 tracked directories, 21,756,054 tracked bytes, 203,648 code/config lines.
- Static checks: Knip 6.45.1 (unused files/exports reviewed; public calibration entry points intentionally retained), Vulture 2.x with 100% confidence (two dead-code findings removed).
- Recovery: a complete Git bundle and tracked-file manifest were written outside the repository before edits.

## Retained provenance

`PRIVACY_AUDIT.md`, `SOURCE_PROVENANCE.md`, the release and snapshot manifests, dated acceptance records, original research, and the historical plans/specs remain because they document non-reconstructable decisions or external evidence. They are not runtime inputs.

A gate is complete only when a fresh command, artifact or manually recorded hardware result proves it. CI provisioning failures, real-model audio acceptance, Windows signing and external publication remain separate gates.
