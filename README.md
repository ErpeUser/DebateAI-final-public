# DebateAI

Private, local-first German live debate assistant. Canonical product name: **DebateAI**. The integrated calibration laboratory, safety fixes and production comparison tools are versioned here, not only in a separate recovery ZIP.

**Status:** source integration and focused regression evidence. This is not a newly built/signed/installed Windows release. Full-project CI, the coupled native binary/archive identity migration and real Windows acceptance remain required. A source merge is not a production release.

## Integrated laboratory

Open **Testlabor** inside the app. Its same-origin dialog leaves the main application mounted. Compare the same short German recording across cached local ASR adapters; inspect WER/CER, critical words and runtime separately. Explicit recording, no silent model download or active-setting changes. Heavy diagnostics retain worker ownership until real completion, even after browser cancellation.

Blind pair/suite imports support A/B, ties and both-unsuitable feedback; identities appear after voting. Generated experiments retain failed pairs in their denominators and verify declared context hashes. Optional ratings are not prefilled. Usefulness is not factual truth. Persistence/export is explicit and excludes audio and credentials.

## Actual production-path pairs

Stop the desktop first. In the complete backend source environment select two already installed genuinely local Ollama models:

```sh
cd source/backend
python scripts/benchmark_blind_pair.py --model-a qwen3:4b --model-b SECOND_INSTALLED_LOCAL_MODEL --output comparison.json
```

Replace the second-model placeholder. The existing production replay runs in separate sequential child processes for both modes; causal output pairs and failure counts are exported for laboratory import. Missing models/remote aliases/timeouts/empty answers are not fabricated successes. No second prompt engine, synchronous judge or automatic winner settings. This is a source CLI, not a one-click frozen-EXE feature.

## Identity and data preservation

Fresh installs select DebateAI data paths; existing nonempty legacy data remains accessible. Never blindly remove keys, profiles, databases, transcripts, models or customized strategies. Independent API update channel requires explicit HTTPS endpoints and public trust keys; archive/signature/rollback checks stay mandatory.

Target repository ErpeUser/DebateAI, stable ID1450951492, private. The authenticated rename helper previews before --apply; its existence does not prove an actual rename. Legacy binary/archive names remain until their coupled contracts are tested together. License/provenance notices and historical manifests remain; old checksums are not new release evidence.

## Evidence and native completion

- [Reconciliation of both deliveries](source/docs/RECONCILIATION_MATRIX_DE.md)
- [Fresh focused tests and limitations](source/docs/FINAL_VERIFICATION_2026-11-11.md)
- [Unified Desktop completion and Windows runbook](source/docs/DESKTOP_FINAL.md)
- [Research-informed decisions](source/docs/RESEARCH_DE.md)
- [Ready-to-use Deep Research brief](source/docs/DEEP_RESEARCH_AUFTRAG_DE.md)

Read root/source AGENTS and current handoff together. After verified consolidation use newest master; do not require an obsolete feature branch or overlay the old ZIP onto newer source. Never install an old executable and present it as the current revision.
