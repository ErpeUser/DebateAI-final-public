# Final Source Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the 16 requested source-only optimizations without producing, packaging, publishing, or overwriting any release artifact.

**Architecture:** Extend the existing bounded in-process services and normalized PostgreSQL records instead of adding infrastructure. Keep audio, provider, privacy, replay, prompt, and model contracts stable; expose optional runtimes only when locally available.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Pydantic/asyncio, React/TypeScript, ONNX/FastEmbed/Ollama, stdlib `unittest`.

**Spec:** `C:/Users/User/.codex/attachments/85cf12c9-bd96-46ae-8802-f2c7dd8d29c9/pasted-text.txt`

## Global Constraints

- Do not generate an EXE, installer, release ZIP, PyInstaller build, signature, publication, or model download.
- Preserve PCM16 16 kHz mono, separate mic/system tracks, sessions, prompts, providers, OAuth accounts, and `qwen3:4b` fallback.
- Add no broker, agent framework, vector database, mandatory model server, or heavyweight ASR dependency.
- Work P0, then P1, then P2; preserve user changes in the already dirty worktree.

## Review Focus

- Negation and numeric disagreement must remain retrievable as candidates without being labelled proven contradictions.
- Slow clients must never backpressure audio or final transcript persistence; their state must recover from a snapshot.
- Cancelling an asyncio waiter must not release native inference capacity while its worker thread still runs.
- Fixed audio-device choices must fail visibly when absent; only explicit default-device mode may follow a new default.
- Optional ASR/model capabilities must never be advertised unless the runtime and model are actually usable.

---

### Task 1: Dual-purpose argument and knowledge retrieval (01, 03, 13)

**Files:** Modify `backend/app/services/semantic_argument_memory.py`, `backend/app/services/agents/orchestrator.py`, `backend/app/services/session_manager.py`; create focused tests in `backend/tests/test_semantic_argument_memory.py` and `backend/tests/test_knowledge_context.py`.

**Interfaces:** `SemanticArgumentMemory.search_targets(...) -> SemanticSearchResult`; common context items retain origin, privacy, claim ID, original reference, and rank.

- [ ] Write failing tests for topical matches plus negation/number conflict candidates and privacy-filtered combined context.
- [ ] Run focused tests and confirm the intended failures.
- [ ] Implement dual scoring, structured conflict features, candidate labels, and bounded rank fusion without declaring a contradiction.
- [ ] Feed claim IDs/original references to the coach and retain reusable source/fact knowledge independently from a stale speaking line.
- [ ] Run focused tests to green.

### Task 2: Non-blocking WebSocket delivery and durable recovery (02)

**Files:** Modify `backend/app/services/ws_event_stream.py`, `backend/app/services/pii/ws.py`, `backend/tests/test_ws_event_stream.py`.

**Interfaces:** `ClientSendBuffer.put(...) -> bool` is non-blocking; overflow sets a resync marker and the sender replaces queued delivery with a journal snapshot.

- [ ] Replace the old backpressure test with failing tests proving final overflow returns immediately and snapshot recovery retains final state.
- [ ] Run tests red.
- [ ] Implement per-client overflow/resync behavior while continuing to coalesce interim events.
- [ ] Run WebSocket and audio-handler tests green.

### Task 3: Native resource lifetime, ASR contract, turn assembly, and 1:1 audio mode (04, 06, 07, 08)

**Files:** Create `backend/app/services/native_inference.py`, `backend/app/services/asr_backend.py`, `backend/app/services/turn_assembler.py`; modify `local_transcriber.py`, `ordered_transcription.py`, `audio_runtime.py`, `audio_handler.py`; add focused tests.

**Interfaces:** `run_native_until_complete(...)`; `ASRBackend` protocol with honest capabilities; `TurnAssembler.add(...)` returns revision-safe combined utterances.

- [ ] Write failing cancellation/capacity, backend capability, short-pause continuation, partial-claim, and track fast-path tests.
- [ ] Run them red.
- [ ] Implement shielded native completion, replace stale waiting work only, keep Parakeet default, expose unavailable Nemotron honestly, and reuse loaded model/context objects.
- [ ] Implement conservative same-speaker continuation plus opt-in track-based 1:1 segmentation while retaining the multi-speaker diarizer.
- [ ] Run focused audio/transcription tests green.

### Task 4: Local coach, research reuse, and provider order (05, 09, 10)

**Files:** Modify `backend/app/services/llm.py`, `seed_agents.py`, `debate_research.py`, provider-routing tests.

**Interfaces:** Ollama payload uses supported no-thinking/context/output controls and JSON schema; research caches search documents/passages separately and coalesces identical in-flight work.

- [ ] Write failing payload, redirect-validation, cache separation, single-flight, and provider-priority tests.
- [ ] Run tests red.
- [ ] Implement Ollama-native controls with negotiated fallback, runtime-discovered Qwen alternatives only, bounded redirect traversal, persistent HTTP reuse, and layered caches.
- [ ] Preserve exact Gemini 3.1 Pro High verification and existing account state.
- [ ] Run focused LLM/research/subscription tests green.

### Task 5: Normalized claims and complete atomic coverage (11, 12, 16)

**Files:** Modify `objection_handler.py`, `argument_graph.py`, relevant claim/graph tests.

**Interfaces:** atomic IDs derive from normalized text/span identity rather than list order; uncovered original spans become grouped claims; graph remains a derived cached view reconciled from durable claim rows.

- [ ] Write failing reorder-stability, uncovered-span, quote/condition preservation, and stale-view reconciliation tests.
- [ ] Run tests red.
- [ ] Implement conservative coverage and stable IDs; write normalized records before refreshing the graph view in one transaction.
- [ ] Remove duplicated context/view calculations encountered on this path only.
- [ ] Run focused claim/graph tests green.

### Task 6: Stable devices, batched UI updates, and useful-latency review (14, 15)

**Files:** Modify `windows_audio_capture.py`, `routers/native_audio.py`, `DeviceSetupAssistant.tsx`, `api.ts`, `types/index.ts`, `useWebSocket.ts`, `debate_review.py`, and tests.

**Interfaces:** device selection uses stable endpoint keys plus explicit `default` mode; socket events publish once per animation frame; late-review classification considers work type, topic continuity, user reaction, and usefulness.

- [ ] Write failing backend/device, frontend batching, and review-classification tests.
- [ ] Run tests red.
- [ ] Implement stable resolution without silent fallback, frame-batched socket state publication, and contextual late-recommendation rules.
- [ ] Run focused tests and frontend behavior tests green.

### Task 7: Verification and status matrix

**Files:** No product changes unless a failing verification exposes a regression.

- [ ] Run `python -m unittest discover -s tests` from `backend/`.
- [ ] Run `python -m unittest discover -s tests` from `desktop/`.
- [ ] Run frontend tests and `npm run build` without packaging.
- [ ] Run `sentrux check .`, `sentrux gate .`, and `git diff --check`; do not save a new baseline.
- [ ] Re-read requirements 01-16 and report implemented/already present/partial/blocked with concrete limits.
