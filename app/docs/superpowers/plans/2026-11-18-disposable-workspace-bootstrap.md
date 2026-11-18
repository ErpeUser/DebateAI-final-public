# Disposable Workspace and Signed Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) and TDD.

**Goal:** Recover missing releases securely while keeping `DebateAI_Generated` disposable and improving code/build organization.

**Architecture:** Reuse Ed25519 verification and pinned keys in a separate Python downloader; wire it into existing install/smoke/rollback; consolidate local build products under Generated, add compatibility domain facades, and CI deletion tests.

**Tech Stack:** PowerShell, Python 3.12/cryptography/urllib, Node 24, GitHub Actions.

**Spec:** app/docs/superpowers/specs/2026-11-18-disposable-workspace-bootstrap-design.md

## Umsetzung und Nachweise (18. November 2026)

- **Abgeschlossen:** Ed25519/SHA-256-validierter Release-Download, ZIP-Sicherheit,
  explizit versionierte Schluessel, Download-Staging, Starter-Integration,
  native Smoke-/Rollback-Installation und Testerwartungen.
- **Abgeschlossen:** lokale Build-/Release-Artefakte sowie npm-/pip-Caches
  in DebateAI_Generated; versionierte Pfadreferenzen und CI-Source-only-Pruefung.
- **Abgeschlossen:** kompatible Backend-Fachmodul-Fassaden fuer Updates,
  Transkription und Datenschutz; bestehende Implementierungen bleiben am Ort.
- **Verifiziert lokal:** 92 Skripttests (2 uebersprungen), 32 Update-Service-Tests
  (1 uebersprungen, in isoliertem Test-venv), 25 Desktop-Release-Tests,
  6 Desktop-Pfadtests, 3 Fachmodul-Tests, PowerShell-Build-/Starter-/Rollback-
  Vertragstests und echter Headless-Windows-Smoke. Git diff --check sauber.
- **Offene Grenzen:** Kein produktiver Release-Endpunkt ist auf dem Rechner
  konfiguriert. Ein echter Remote-Download samt Neuinstallation und ein
  komplett toolchainfreier nativer Bootstrap sind NICHT E2E-verifiziert.
  Keine pauschale Migration der 103 Service-Implementierungen oder
  npm-Installationsverzeichnisse (Kompatibilitaets- und Sicherheitsgruende).
  Git blieb auf dem bestehenden Arbeitszweig, ohne Commit oder Push.

Die folgenden Checklisten sind die urspruenglichen Arbeitsanweisungen,
keine Behauptung, dass ausstehende E2E-Schritte abgeschlossen waeren.

## Global Constraints
No source or data destruction, no Git reset/push, no guessed URL, no unsigned trust fallback. Keep active onedir, package lock and existing runtime imports unchanged.

## Review Focus
1. Untrusted descriptor/hash: refuse promotion.
2. Malicious archive path/symlink/duplicate: refuse extraction.
3. Redirect or partial download: refuse promotion and clean temp.
4. Generated absent with valid bundle: start offline.
5. Local worktree/release contract: correct generated paths without data loss.

---

### Task 1: Verified ZIP staging
**Files:** Create `app/scripts/recover_release.py`, `app/scripts/tests/test_recover_release.py`.
**Interfaces:** `recover(descriptor_url, asset_url, keys_path, output_dir)` returns a verified bundle folder.
- [ ] RED: tests for valid Ed25519 descriptor, invalid signature/hash, HTTPS origin, ZIP traversal/symlinks/collisions.
- [ ] GREEN: use existing verification and fail-closed I/O; tests green.

### Task 2: Launcher recovery
**Files:** Modify `Start-DebateAI.ps1`, test `app/scripts/tests/test_start_debateai.ps1`.
- [ ] RED: tests for offline/no Generated, channel options, trusted downloader invocation.
- [ ] GREEN: signed-recovery then verified transactional install, source-build fallback only with toolchain.

### Task 3: Build/cache layout
**Files:** Modify `app/scripts/build_debate_assistant.ps1`, `app/scripts/tests/test_build_debate_assistant.ps1`, `app/scripts/acceptance/run_all.ps1`, `app/dev.ps1`.
- [ ] RED: build contract test expects Generated build paths and npm cache.
- [ ] GREEN: safe generated outputs and preserved package-local node_modules.

### Task 4: Backend domain facades
**Files:** Add `app/backend/app/services/domains/` subpackages and import tests.
- [ ] RED: tests for stable domain APIs alongside old imports.
- [ ] GREEN: explicit reexports without moving modules abruptly.

### Task 5: CI, documentation and verification
**Files:** `.github/workflows/tests.yml`, `app/scripts/tests/test_workspace_disposability.py`, docs and README.
- [ ] Add CI checks for Generated absent, path contracts, launcher.
- [ ] Run scripts/release/backend/desktop tests, bundle smoke, Git diff check.
- [ ] Document residual limitations; do not claim unrun full remote release installation.
