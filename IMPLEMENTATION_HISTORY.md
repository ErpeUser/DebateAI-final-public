# Implementation history

This file is the short, current record of product changes. Detailed plans and dated audits remain in `source/docs/superpowers/` and `source/.ai/` because they contain provenance or verification evidence that cannot be reconstructed from Git alone.

- **2026-11-17 — deep cleanup:** removed two unreferenced frontend components, one unreachable backend statement, one unused artifact streaming helper and its imports, and unused public exports identified by Knip. Consolidated ignore rules at the repository root and removed the duplicate nested `.gitignore`.
- **2026-11-16 — acceptance consolidation:** the verified acceptance runner, native evidence and profile/tool contract tests were integrated into `master`.
- **2026-11-11 — identity and release hardening:** DebateAI naming, data migration safeguards, update origin validation, provider routing, desktop packaging and rollback contracts were consolidated into the canonical source tree.

Use `git log --follow` for the complete line-by-line history. The maintained contract starts at [`source/docs/DEBATEAI_CANONICAL_INDEX.md`](source/docs/DEBATEAI_CANONICAL_INDEX.md).
