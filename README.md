# DebateAI

DebateAI is a desktop and web application for live debate analysis.

The maintained source is under app/: backend (FastAPI/Python), frontend
(React/TypeScript), desktop (Windows launcher/updater and PyInstaller spec),
AI prompts and playbooks, documentation website and release-signing worker.
Configuration, tests, source documentation and release scripts are kept with
the source that uses them.

## Layout

- app/ - versionable application source, tests, configuration and docs
- runtime/DebateAI/ - canonical installed Windows bundle path, restored and
  smoke-tested
- DebateAI_Generated/ - disposable generated caches, dependencies, reports and
  build outputs. It may be absent between builds.
- .git - small pointer to the protected Git history in the adjacent Coding audit (do not delete that audit)
- app/scripts/workspace_refs.py - stable path auditor (run with --strict)
- Start-DebateAI.cmd - starts the installed release or verifies and installs a signed update; developer source-build fallback when no update channel is configured
- app/docs/HANDBUCH.md - technical setup, operation and release handbook
- app/docs/VISION.md - owner-approved product vision
- app/docs/OFFENE_PUNKTE.md - maintained current open items and verification gaps
- app/docs/HISTORIE.md - consolidated historical visions, decisions and provenance
- .github/workflows/ - root GitHub Actions (including the blocking repository-layout check)
- .github/CODEOWNERS, .github/dependabot.yml - ownership and dependency-update policy
- app/scripts/github_sync.py - default-branch pull and incoming-branch/PR audit
- app/docs/HANDBUCH.md - repository, CI, structure gate and release contract
- %LOCALAPPDATA%/DebateAI/ - private user sessions, settings and database
  (outside this repository and never considered build cache)

## Start and recover

The normal launcher is `Start-DebateAI.cmd` and its installed-release path is
`runtime/DebateAI/DebateAI.exe`. The complete bundle is installed and the
application runs without disposable caches and needs no
Python, npm or downloads. `Start-DebateAI.ps1 -Check` checks required files
without starting the application or accessing the network. If the verified
runtime is missing and DEBATEAI_UPDATE_DESCRIPTOR_URL / DEBATEAI_UPDATE_ASSET_URL
are configured, the starter downloads only a correctly signed and hashed release.
Otherwise it can rebuild from source (needs Python 3.12, Node.js 24, network and
build toolchain). Both paths install only after a passing smoke test.
`-Offline` forbids network recovery; `-Rebuild` explicitly chooses the source build.

For the removable workspace audit run
`python app/scripts/workspace_refs.py --strict`; add `--initialize
--write-report` only if you want to regenerate optional cache folders.
See `app/docs/HANDBUCH.md` for safeguards and limitations.
Legacy pointer checkouts remain readable during migration, but new checkouts
use the normal internal `.git/` directory.

## Build and verification

- Repository layout: `python app/scripts/verify_repository_layout.py` (read-only)
- CI-compatible source checkout: `python app/scripts/workspace_refs.py --source-only --strict`
- GitHub config: `app/docs/HANDBUCH.md` (public repository and direct-main workflow)
- Python 3.12, Node.js 24
- Backend: cd app/backend; python -m pip install -r requirements.txt
- Frontend: cd app/frontend; npm ci; npm test; npm run build
- Docs: cd app/docs-site; npm ci; npm test; npm run build
- Windows desktop smoke: python app/desktop/scripts/smoke_test.py
  --bundle runtime/DebateAI
- Release source and configuration: app/scripts/, app/desktop/debateai.spec,
  .github/workflows/.

The local standalone executable is a previously built release; it is not a
new build of uncommitted source changes. Preserve external backups and never
delete personal data under %LOCALAPPDATA%/DebateAI.
