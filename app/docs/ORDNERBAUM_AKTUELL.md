# DebateAI - aktueller Ordnerbaum (automatisch erzeugt)

Stand: 2026-11-19T00:37:59+01:00
Quelle: Repository-Root (relativ zu app/scripts/export_project_tree.py)
app/: 1061 Dateien, 14.5 MiB
runtime/: 16122 Dateien, 918.6 MiB
DebateAI_Generated vorhanden: True

Dieser Baum zeigt echte Verzeichnisse; '...' bezeichnet nur gekuerzte Inhalte.
Private Benutzerdaten ausserhalb des Repositorys werden nicht eingelesen.

```text
DebateAI/
├── .codex/
│   └── config.toml
├── .git/
│   ├── hooks/
│   │   ├── applypatch-msg.sample
│   │   ├── commit-msg.sample
│   │   ├── fsmonitor-watchman.sample
│   │   ├── post-update.sample
│   │   ├── pre-applypatch.sample
│   │   ├── pre-commit.sample
│   │   ├── pre-merge-commit.sample
│   │   ├── pre-push.sample
│   │   ├── pre-rebase.sample
│   │   ├── pre-receive.sample
│   │   ├── prepare-commit-msg.sample
│   │   ├── push-to-checkout.sample
│   │   └── ... (+2 weitere Eintraege)
│   ├── info/
│   │   └── exclude
│   ├── logs/
│   │   ├── refs/
│   │   │   ├── heads/
│   │   │   └── remotes/
│   │   └── HEAD
│   ├── migration-backups/
│   │   └── original-git-pointer-2026-11-18.txt
│   ├── objects/
│   │   ├── info/
│   │   └── pack/
│   │       ├── pack-cc0ccaf983da6ee4c31c49ea2a1b27da4d949981.idx
│   │       ├── pack-cc0ccaf983da6ee4c31c49ea2a1b27da4d949981.pack
│   │       └── pack-cc0ccaf983da6ee4c31c49ea2a1b27da4d949981.rev
│   ├── refs/
│   │   ├── heads/
│   │   │   └── master
│   │   ├── remotes/
│   │   │   └── origin/
│   │   └── tags/
│   ├── config
│   ├── description
│   ├── HEAD
│   ├── index
│   ├── ORIG_HEAD
│   └── packed-refs
├── .github/
│   ├── workflows/
│   │   ├── deploy-site.yml
│   │   ├── desktop-release.yml
│   │   ├── security.yml
│   │   ├── structure.yml
│   │   └── tests.yml
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── SECURITY.md
├── .superpowers/
│   └── sdd/
│       └── public-final-repository-consolidation/
│           ├── plan-path
│           └── progress.md
├── app/
│   ├── .ai/
│   │   ├── DEBATE_AI_OPTIMIERUNG.md
│   │   └── MASTER_276_STATUS.json
│   ├── .github/
│   │   └── release-notes/
│   │       ├── v0.1.1.md
│   │       ├── v0.2.0.md
│   │       ├── v0.2.1.md
│   │       ├── v0.2.2.md
│   │       ├── v0.2.3.md
│   │       ├── v0.2.4.md
│   │       ├── v0.2.5.md
│   │       ├── v0.3.0.md
│   │       ├── v0.3.1.md
│   │       ├── v0.3.2.md
│   │       ├── v0.3.3.md
│   │       ├── v0.3.4.md
│   │       └── ... (+17 weitere Eintraege)
│   ├── .sentrux/
│   │   ├── baseline.json
│   │   └── rules.toml
│   ├── ai/
│   │   ├── defaults/
│   │   │   ├── prompts/
│   │   │   └── playbooks.json
│   │   ├── agent.audio_gateway.txt
│   │   ├── agent.brief_arbiter.txt
│   │   ├── agent.brief_discovery_lens.txt
│   │   ├── agent.brief_meeting_lens.txt
│   │   ├── agent.consolidated_analyst.txt
│   │   ├── agent.objection_handler.txt
│   │   ├── agent.opportunity_specialist.txt
│   │   ├── agent.strategic_signals.txt
│   │   ├── agent.synthesizer.txt
│   │   ├── agent.transcript_refiner.txt
│   │   ├── analogy.optional.txt
│   │   └── ... (+36 weitere Eintraege)
│   ├── backend/
│   │   ├── alembic/
│   │   │   ├── versions/
│   │   │   └── env.py
│   │   ├── app/
│   │   │   ├── routers/
│   │   │   ├── services/
│   │   │   ├── ws/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── release_notes.py
│   │   │   └── schemas.py
│   │   ├── benchmarks/
│   │   │   ├── debate_latency_smoke_de.json
│   │   │   ├── debate_quality_20_de.json
│   │   │   └── debate_quality_de.json
│   │   ├── fixtures/
│   │   │   └── debate_calibration_de.json
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   ├── audit_dependencies.py
│   │   │   ├── benchmark_blind_pair.py
│   │   │   ├── benchmark_debate_copilot.py
│   │   │   ├── benchmark_deep_debate_analyst.py
│   │   │   ├── diarizer_ab.py
│   │   │   ├── download_models.py
│   │   │   ├── install_sortformer.py
│   │   │   ├── README-synthesizer-replay.md
│   │   │   ├── replay_call.py
│   │   │   ├── setup_windows_gpu.ps1
│   │   │   ├── start_backend.py
│   │   │   └── ... (+6 weitere Eintraege)
│   │   ├── tests/
│   │   │   ├── fixtures/
│   │   │   ├── __init__.py
│   │   │   ├── test_active_questions_bound.py
│   │   │   ├── test_adapter_contracts.py
│   │   │   ├── test_adaptive_reasoning.py
│   │   │   ├── test_agent_activity.py
│   │   │   ├── test_ai_config.py
│   │   │   ├── test_ai_prompt_contracts.py
│   │   │   ├── test_alembic_configuration.py
│   │   │   ├── test_alembic_transaction.py
│   │   │   ├── test_argument_graph.py
│   │   │   ├── test_artifacts_insights_export.py
│   │   │   └── ... (+189 weitere Eintraege)
│   │   ├── .dockerignore
│   │   ├── alembic.ini
│   │   ├── Dockerfile
│   │   ├── requirements-sortformer.txt
│   │   ├── requirements-test.txt
│   │   └── requirements.txt
│   ├── build/
│   │   └── native-smoke/
│   ├── desktop/
│   │   ├── assets/
│   │   │   ├── icon.icns
│   │   │   ├── icon.ico
│   │   │   └── icon.png
│   │   ├── chatgpt_oracle/
│   │   │   ├── node/
│   │   │   ├── LICENSE.oracle
│   │   │   ├── package-lock.json
│   │   │   ├── package.json
│   │   │   └── UPSTREAM.md
│   │   ├── debateai_desktop/
│   │   │   ├── __init__.py
│   │   │   ├── chatgpt_web_login.py
│   │   │   ├── gemini_web_bridge.py
│   │   │   ├── gemini_web_login.py
│   │   │   ├── lifecycle_ui.py
│   │   │   ├── ollama_lifecycle.py
│   │   │   ├── paths.py
│   │   │   ├── pg.py
│   │   │   ├── subscription_bridge.py
│   │   │   └── windows_console.py
│   │   ├── gemini_web_to_api/
│   │   │   ├── build.ps1
│   │   │   ├── debateai-loopback.patch
│   │   │   ├── LICENSE
│   │   │   └── UPSTREAM.md
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   ├── build_platform_manifest.py
│   │   │   ├── build_release_manifest.py
│   │   │   ├── download_cliproxyapi.py
│   │   │   ├── download_ffmpeg.py
│   │   │   ├── download_pg.py
│   │   │   ├── make_icons.py
│   │   │   ├── smoke_test.py
│   │   │   ├── smoke_update_archive.py
│   │   │   └── version_resource.py
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_chatgpt_web_login.py
│   │   │   ├── test_debateai_identity.py
│   │   │   ├── test_download_ffmpeg.py
│   │   │   ├── test_download_pg.py
│   │   │   ├── test_explicit_legacy_import.py
│   │   │   ├── test_frozen_streams.py
│   │   │   ├── test_gemini_web_bridge.py
│   │   │   ├── test_gemini_web_login.py
│   │   │   ├── test_launcher.py
│   │   │   ├── test_lifecycle_ui.py
│   │   │   ├── test_ollama_lifecycle.py
│   │   │   └── ... (+12 weitere Eintraege)
│   │   ├── constraints-windows-py312.txt
│   │   ├── debateai.spec
│   │   ├── debateai_identity.py
│   │   ├── Dockerfile.release-linux
│   │   ├── launcher.py
│   │   ├── release_signing_keys.json
│   │   └── ... (+2 weitere Eintraege)
│   ├── docs/
│   │   ├── acceptance/
│   │   │   ├── coordination.json
│   │   │   ├── integration-manifest.json
│   │   │   └── requirements-delta.json
│   │   ├── architecture/
│   │   │   └── backchannel-architecture.svg
│   │   ├── assets/
│   │   │   ├── gemini-create-key-button.png
│   │   │   ├── gemini-create-key-dialog.png
│   │   │   └── wordmark.svg
│   │   ├── evidence/
│   │   │   ├── asr-local-wav-decision-2026-11-09.json
│   │   │   └── debate-vnext-benchmark.json
│   │   ├── superpowers/
│   │   │   ├── plans/
│   │   │   └── specs/
│   │   ├── agents.md
│   │   ├── api-keys.md
│   │   ├── architecture.md
│   │   ├── architecture.svg
│   │   ├── audio-pipeline.md
│   │   ├── CODEX_ACCEPTANCE_2026-11-12.md
│   │   ├── configuration.md
│   │   └── ... (+29 weitere Eintraege)
│   ├── docs-site/
│   │   ├── migrations/
│   │   │   ├── 0001_interest_subscribers.sql
│   │   │   ├── 0002_release_access.sql
│   │   │   ├── 0003_release_access_policies.sql
│   │   │   └── 0004_release_update_grants.sql
│   │   ├── public/
│   │   │   ├── fonts/
│   │   │   └── favicon.svg
│   │   ├── src/
│   │   │   ├── assets/
│   │   │   ├── components/
│   │   │   ├── content/
│   │   │   ├── styles/
│   │   │   └── content.config.ts
│   │   ├── .gitignore
│   │   ├── admin-authorization.test.js
│   │   ├── admin-early-access.test.js
│   │   ├── admin-preview.mjs
│   │   ├── admin-preview.test.js
│   │   ├── admin-test-helpers.js
│   │   ├── admin-users.test.js
│   │   ├── admin.test.js
│   │   ├── assemble.mjs
│   │   └── ... (+15 weitere Eintraege)
│   ├── frontend/
│   │   ├── calibration-tests/
│   │   │   ├── browser_fixture.py
│   │   │   ├── core.test.mjs
│   │   │   ├── import-evidence.test.mjs
│   │   │   ├── session.test.mjs
│   │   │   ├── suite.test.mjs
│   │   │   ├── test_fixture_cleanup.py
│   │   │   ├── test_import_evidence.py
│   │   │   ├── test_lab_browser.py
│   │   │   └── test_launcher.py
│   │   ├── public/
│   │   │   ├── calibration/
│   │   │   ├── icons/
│   │   │   ├── calibration.html
│   │   │   └── manifest.webmanifest
│   │   ├── scripts/
│   │   │   ├── make_pwa_icons.py
│   │   │   └── verify-pwa-assets.mjs
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── i18n/
│   │   │   ├── lib/
│   │   │   ├── services/
│   │   │   ├── types/
│   │   │   ├── utils/
│   │   │   ├── App.tsx
│   │   │   ├── index.css
│   │   │   └── main.tsx
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── index.html
│   │   ├── nginx.conf
│   │   ├── package-lock.json
│   │   ├── package.json
│   │   ├── postcss.config.js
│   │   ├── tailwind.config.js
│   │   └── ... (+2 weitere Eintraege)
│   ├── release-signing-worker/
│   │   ├── scripts/
│   │   │   └── create-signing-key.mjs
│   │   ├── src/
│   │   │   └── index.mjs
│   │   ├── test/
│   │   │   ├── create-signing-key.test.mjs
│   │   │   └── index.test.mjs
│   │   ├── package-lock.json
│   │   ├── package.json
│   │   └── wrangler.jsonc
│   ├── scripts/
│   │   ├── acceptance/
│   │   │   ├── __init__.py
│   │   │   ├── catalog.py
│   │   │   ├── checked_pytest.py
│   │   │   ├── checked_unittest.py
│   │   │   ├── execution.py
│   │   │   ├── inventory.py
│   │   │   ├── owned_process.py
│   │   │   ├── process_launcher.py
│   │   │   ├── README.md
│   │   │   ├── reporting.py
│   │   │   ├── requirements-tools.txt
│   │   │   ├── run.py
│   │   │   └── ... (+2 weitere Eintraege)
│   │   ├── automation/
│   │   │   └── resume_debateai.ps1
│   │   ├── gui-capture/
│   │   │   ├── capture.mjs
│   │   │   ├── capture.test.mjs
│   │   │   ├── fixtures.js
│   │   │   ├── README.md
│   │   │   └── run.mjs
│   │   ├── tests/
│   │   │   ├── r2-object.test.mjs
│   │   │   ├── test_acceptance_evidence.py
│   │   │   ├── test_acceptance_execution.py
│   │   │   ├── test_acceptance_profiles.py
│   │   │   ├── test_acceptance_pytest.py
│   │   │   ├── test_acceptance_tools.py
│   │   │   ├── test_build_debate_assistant.ps1
│   │   │   ├── test_migrate_releases_to_r2.ps1
│   │   │   ├── test_publish_release_platform.ps1
│   │   │   ├── test_recover_release.py
│   │   │   ├── test_release_desktop.ps1
│   │   │   ├── test_rename_debateai_repository.py
│   │   │   └── ... (+5 weitere Eintraege)
│   │   ├── build_debate_assistant.ps1
│   │   ├── capture_debateai_window.ps1
│   │   ├── capture_gui_dom.ps1
│   │   ├── capture_gui_surfaces.ps1
│   │   ├── export_project_tree.py
│   │   ├── migrate_releases_to_r2.ps1
│   │   ├── publish_release_platform.ps1
│   │   ├── r2-object.mjs
│   │   └── ... (+9 weitere Eintraege)
│   └── ... (+13 weitere Eintraege)
├── DebateAI_Generated/
│   └── reports/
│       └── acceptance/
├── runtime/
│   └── DebateAI/
│       ├── _internal/ [16120 Dateien, 885.4 MiB; gekuerzt]
│       ├── DebateAI.exe
│       └── DebateAIUpdater.exe
├── .gitattributes
├── .gitignore
├── AGENTS.md
├── README.md
├── Start-DebateAI.cmd
└── ... (+1 weitere Eintraege)
```
