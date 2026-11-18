# DebateAI: disposable workspace and secure recovery design

## Goal / accepted brief
Implement the user-approved improvements from `app/docs/ORDNERSTRUKTUR_ZIELBILD.md`: installed release and Git independent of `DebateAI_Generated/`; missing-release recovery with existing signed update contract; unified generated build outputs; incremental domain organization; CI and tests. User requested direct implementation in the current checkout.

## Invariants
- Preserve the complete working `runtime/DebateAI/_internal`, external `../DebateAI-GIT-METADATA` and all preexisting uncommitted source changes. No Git reset/push or remote publication.
- Never touch private data in `%LOCALAPPDATA%/DebateAI`. `DebateAI_Generated/` is disposable.
- Update sources are independent, deployment-owned and *explicitly configured*. This PC does not currently provide one. Never invent a production domain.
- Verify Ed25519 signatures via versioned `app/desktop/release_signing_keys.json` and existing `app.services.update_signing.verify_update_descriptor`; enforce same-origin HTTPS, SHA-256, size, safe archive root and extraction, limits and atomic rollback.
- Installed bundle starts without Python, npm, network or Generated. Signed-release restoration from an absent bundle uses a trusted Python 3.12 environment with pinned cryptography; if unavailable, fail safely or use explicit source build, not a silent unsigned fallback.
- Preserve source `app/site/` and `app/docs-site/` independently; the latter assembles the former. Keep npm install `node_modules` in package directories; route disposable npm caches into Generated without unsafe junctions.
- The 103 backend flat services must migrate incrementally with stable imports, not in a sweeping untested move.

## Approaches
Considered (a) unsigned ZIP download (rejected: trust downgrade), (b) unconditional source build (existing heavy fallback), (c) signed-release recovery with verified staging, smoke and atomic swap (chosen). Authentication/authorization is unchanged; downloadable updates use the documented anonymous update API.

## Failure behavior
Missing channel: report explicitly and allow developer source build only with toolchain. Malformed descriptors, unexpected redirects, hash mismatch or hostile ZIP: fail closed, never overwrite runtime. Failed smoke after install: restore prior runtime. Preserve offline operation for existing installs.

## Verification
Unit tests for signed descriptor/sha256/zip traversal/redirect/missing configuration; PowerShell build-contract tests; domain import tests; Generated-deletion tests; native bundled smoke. Full online recovery requires operator-configured endpoints and is not assumed complete until tested.
