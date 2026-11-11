# DebateAI integration plan

Goal: integrate the tested calibration laboratory and standalone identity into the private repository.
Architecture: retain the existing FastAPI, React/Vite, ONNX/Ollama, desktop lifecycle and updater validation. No replacement inference engine.
Spec: user-authorized DebateAI rebrand and GitHub push, 2026-11-11.

Global constraints: preserve runtime data and credentials; no force push; no manufactured production signing keys or domains; do not claim Windows verification in Linux; preserve licenses.

- [x] Integrate recovery source and tests into production paths, including an in-app lab dialog.
- [x] Establish canonical DebateAI identity and migration-safe desktop path resolution.
- [x] Disable legacy update service by default; require explicit independent channel and trust configuration.
- [x] Add safe GitHub repository rename helper and migration/audit instructions.
- [x] Run focused regression tests, syntax and UI checks; review diffs.
- [x] Push real source and tests without force; verify remote tree. Documentation/script publication is the final commit of this work package.

Review focus: retained credentials; legacy data directories; invalid update URLs; unfinished native workers; active call preservation when opening or closing the laboratory.

Ruling: this environment cannot launch independent coding agents. Reviews are separate author passes, not multiple-agent verification.
Ruling: native Windows build/install and a repository-administration rename are not established by a source push.

Remaining whole-product work is explicitly tracked in DESKTOP_FINAL.md and debateai-verification-2026-11-11.md; these completed package checkboxes do not mean a completed standalone Windows release.
