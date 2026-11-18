# DebateAI

DebateAI is a desktop and web application for live debate analysis.

The maintained source is under app/: backend (FastAPI/Python), frontend
(React/TypeScript), desktop (Windows launcher/updater and PyInstaller spec),
AI prompts and playbooks, documentation website and release-signing worker.
Configuration, tests, source documentation and release scripts are kept with
the source that uses them.

## Layout

- app/ - versionable application source, tests, configuration and docs
- DebateAI_Generated/runtime/DebateAI/ - locally verified Windows binary bundle,
  including its required _internal/ directory (not committed to Git)
- DebateAI_Generated/ - unversioned generated outputs: runtime, downloads,
  build products, caches and test reports (ignored by Git); keep the verified
  bundle until a replacement has been smoke-tested
- .github/workflows/ - GitHub automation
- %LOCALAPPDATA%/DebateAI/ - private user sessions, settings and database
  (outside this repository and never considered build cache)

## Build and verification

- Python 3.12, Node.js 24
- Backend: cd app/backend; python -m pip install -r requirements.txt
- Frontend: cd app/frontend; npm ci; npm test; npm run build
- Docs: cd app/docs-site; npm ci; npm test; npm run build
- Windows desktop smoke: python app/desktop/scripts/smoke_test.py
  --bundle DebateAI_Generated/runtime/DebateAI
- Release source and configuration: app/scripts/, app/desktop/debateai.spec,
  .github/workflows/.

The local standalone executable is a previously built release; it is not a
new build of uncommitted source changes. Preserve external backups and never
delete personal data under %LOCALAPPDATA%/DebateAI.
