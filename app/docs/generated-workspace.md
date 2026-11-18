# Disposable workspace, signed recovery and source builds

## Permanent vs. disposable

Permanent assets:
- `app/` contains the versioned product source, pinned dependency contracts, prompts, update keys, CI tests and build scripts.
- `runtime/DebateAI/` is the complete Windows PyInstaller onedir release. `_internal/` is **inseparable** from the EXEs, including bundled Python libraries, PostgreSQL, FFmpeg, models, frontend and optional web bridges.
- `.git/` is the internal Git history and reference database at the repository root. Legacy checkouts with a pointer file remain readable during migration, but new checkouts use this ordinary `.git/` directory.
- `%LOCALAPPDATA%/DebateAI/` is **private user data** (databases, sessions, preferences). Never move or clean it automatically.

`DebateAI_Generated/` contains disposable build products, release staging, npm/pip caches, temporary downloads and reports only. It can be deleted **after closing all build/test processes**, without preventing an existing installed EXE from starting.

## Normal startup

Double-click `Start-DebateAI.cmd` or launch `runtime/DebateAI/DebateAI.exe` directly. When the release is complete, the application starts **without** Python, Node, Git, network access or Generated. Check without starting:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-DebateAI.ps1 -Check
```

## When the Windows release is missing

`Start-DebateAI.ps1` attempts one of two recovery routes.

**1. Signed release channel (preferred).** An operator explicitly configures two HTTPS URL templates. They must have the same origin and these precise placeholders:

```powershell
$env:DEBATEAI_UPDATE_DESCRIPTOR_URL = 'https://<operator-host>/api/update/latest/{platform_id}'
$env:DEBATEAI_UPDATE_ASSET_URL = 'https://<operator-host>/api/update/assets/{version}/{platform_id}'
.\Start-DebateAI.ps1 -NoLaunch
```

`<operator-host>` is an **example placeholder, not a working endpoint**. This project intentionally does not inherit vendor-specific or private URLs. The existing update service uses the same deployment-owned route. The downloader:
1. Reads the versioned trusted public keys from `app/desktop/release_signing_keys.json`; it never downloads keys or trusts keys from the server.
2. Validates the signed Windows update descriptor with the existing Ed25519 contract.
3. Downloads the exact declared asset with HTTPS same-origin redirects only and verifies SHA-256 and size.
4. Rejects unsafe archive paths, symlinks, casefold collisions and incomplete bundles. Extracts only into a temporary stage under `DebateAI_Generated/build/recovery/`.
5. Passes the verified staged release to the existing installer. The installer backs up the old runtime, smoke-tests the new installation, and restores the old runtime if the smoke test fails.

**Current limitation:** This recovery route requires an existing Python 3.12 environment with the required pinned `cryptography`/backend libraries. It is **not yet a standalone native bootstrap executable** for a completely empty Windows machine. A real configured production endpoint has not been exercised end-to-end in this workspace.

**2. Development source-build fallback.** When *neither* update URL is configured, the starter can use `app/scripts/build_debate_assistant.ps1`, which needs Python 3.12, Node 24, network access and the pinned build toolchain. Passing `-Rebuild` intentionally chooses this path even if an installed runtime exists. The build runs the frontend, pinned dependency and model downloaders, PyInstaller, bundle smoke and archive smoke before publishing the output. It then stages/smokes the candidate under the runtime installer.

The source build publishes into `DebateAI_Generated/build/releases/DebateAI/` and `DebateAI_Generated/build/releases/DebateAI-windows-x64.zip`. Its Python release virtualenv lives under `dependencies/python/release-venv`, npm and pip download caches under `cache/npm` and `cache/pip` **within Generated**. Package-local `node_modules`, frontend `dist` and downloaded build assets remain at their existing toolchain-compatible (Git-ignored) paths in `app/` until those tools support an independently verified relocation.

`-Offline` forbids recovery if the installed release is missing. A partially configured channel (only one URL) always fails explicitly. Bad signatures, hashes or unsafe archives never trigger an unsigned installation fallback.

## Audit and CI

```powershell
py -3.12 app/scripts/workspace_refs.py --strict
py -3.12 app/scripts/workspace_refs.py --source-only --strict
py -3.12 app/scripts/workspace_refs.py --initialize --write-report
powershell -NoProfile -ExecutionPolicy Bypass -File app/scripts/tests/test_start_debateai.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File app/scripts/tests/test_build_debate_assistant.ps1
```

The default audit checks source + native runtime. `--source-only` checks a fresh CI checkout **without** requiring the untracked runtime or Generated. `--initialize` recreates only scratch directories, `--write-report` explicitly stores an optional report.

**Do not delete** `runtime/`, the external Git metadata, `app/`, or `%LOCALAPPDATA%/DebateAI/`. No cleanup script should follow junctions, delete backups while installation is active, or replace a signed-release verification with a URL-only check.
