# German Debate Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a local-first German debate copilot that continuously replaces its immediate answer, counterargument, and counter-question while existing analysis agents and optional keyless research improve later revisions in the background.

**Architecture:** Extend the current Objection Handler structured call into an event-driven fast lane, protect it with revision cancellation and local-inference priority, and broadcast an ephemeral `debate_update` contract. Keep research in a separately scheduled keyless service and render the latest state in a dedicated active-call panel.

**Tech Stack:** Python 3.12, asyncio, FastAPI, Pydantic, httpx, React 18, TypeScript, Vite, Node test runner, stdlib `unittest`, PowerShell, Docker Compose, Ollama, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-11-02-german-debate-copilot-design.md`

## Global Constraints

- Fast guidance never awaits research, strategic agents, persistence, or UI work.
- Transcript ingestion returns after scheduling; it never awaits a text model.
- Only the newest monotonic revision may publish a recommendation.
- Preserve Objection Handler insight persistence and all existing background agents.
- Use one local `qwen3:4b` text model and existing custom-endpoint routing.
- Default research providers require no API key; Privacy First disables research egress.
- Do not automate ChatGPT Pro or Google AI Pro consumer sessions.
- Add no database migration and no second insight store.
- New source text stays ASCII unless the containing file already requires non-ASCII.

## Review Focus

- Rapid successive transcript segments: earlier inference is cancelled/discarded and only the newest revision is visible (Task 3 tests).
- Local endpoint occupied by deep analysis: the debate request preempts the inner low-priority request without killing the background loop (Task 1 tests).
- Network failure, malformed response, or slow research: guidance remains visible and research reports a bounded non-blocking failure (Task 2 tests).
- A research query containing PII tokens or Privacy First enabled: no external request is made (Task 2 tests).
- Resumed/disconnected calls and absent debate model: normal transcription and insights continue with an actionable empty/blocked state (Tasks 3 and 4 tests).

---

### Task 1: Prioritized local inference boundary

**Files:**
- Create: `backend/app/services/inference_scheduler.py`
- Create: `backend/tests/test_inference_scheduler.py`
- Modify: `backend/app/services/llm.py`
- Modify: `backend/tests/test_llm_router.py`

**Interfaces:**
- Produces: `InferencePriority(str, Enum)`, `InferencePreempted(RuntimeError)`, and `run_local_inference(endpoint_key: str, priority: InferencePriority, operation: Callable[[], Awaitable[T]]) -> T`.
- `llm._openai_json()` chooses `HIGH` only for source `debate_copilot`; other endpoint calls use `NORMAL`.

- [ ] **Step 1: Write failing scheduler tests** for per-endpoint serialization, high-priority preemption of an inner normal operation, no cross-endpoint interference, and scheduler reuse after cancellation.
- [ ] **Step 2: Run `python -m unittest tests.test_inference_scheduler` from `backend/` and verify the missing module failure.**
- [ ] **Step 3: Implement the smallest keyed scheduler** that owns inner operation tasks so cancelling a request does not cancel its caller task.
- [ ] **Step 4: Run the scheduler tests and verify they pass.**
- [ ] **Step 5: Add failing LLM-router tests** proving endpoint JSON calls enter the scheduler with `HIGH` for `debate_copilot` and `NORMAL` for `strategic_signals`.
- [ ] **Step 6: Route self-hosted JSON HTTP operations through the scheduler** while leaving hosted OpenAI/Google behavior unchanged.
- [ ] **Step 7: Run `python -m unittest tests.test_inference_scheduler tests.test_llm_router`.**
- [ ] **Step 8: Commit with `feat: prioritize local debate inference`.**

### Task 2: Keyless, claim-linked research service

**Files:**
- Create: `backend/app/services/debate_research.py`
- Create: `backend/tests/test_debate_research.py`
- Modify: `backend/app/config.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `ResearchSource`, `ResearchResult`, `is_safe_research_query(query: str) -> bool`, and `research_claim(claim: str, query: str, *, client: httpx.AsyncClient | None = None) -> ResearchResult`.
- Queries Wikimedia search/extract and DuckDuckGo Instant Answer concurrently with one shared timeout; output sources contain `title`, `url`, `snippet`, `provider`, and `claim`.

- [ ] **Step 1: Write failing tests** for source normalization, canonical `https` URLs, duplicate removal, result caps, PII-token refusal, empty-query refusal, partial-provider success, total timeout, and no fabricated fallback URLs.
- [ ] **Step 2: Run `python -m unittest tests.test_debate_research` and verify RED.**
- [ ] **Step 3: Add settings** `DEBATE_RESEARCH_ENABLED`, `DEBATE_RESEARCH_TIMEOUT_SECONDS`, `DEBATE_RESEARCH_COOLDOWN_SECONDS`, and `DEBATE_RESEARCH_MAX_SOURCES` with privacy-preserving defaults.
- [ ] **Step 4: Implement both keyless adapters and the normalizer** using existing `httpx`; add no new runtime dependency.
- [ ] **Step 5: Run the focused research tests and verify GREEN.**
- [ ] **Step 6: Commit with `feat: add keyless debate research`.**

### Task 3: Event-driven debate fast lane

**Files:**
- Modify: `backend/app/services/agents/objection_handler.py`
- Modify: `backend/app/services/agents/prompts.py`
- Modify: `backend/app/services/agents/orchestrator.py`
- Modify: `backend/app/services/seed_agents.py`
- Create: `backend/tests/test_debate_copilot.py`
- Modify: `backend/tests/test_orchestrator.py`
- Modify: `backend/tests/test_seed_agents.py`

**Interfaces:**
- Produces Pydantic `DebateRecommendation` and `DebateSource` plus `ObjectionHandlerAgent.latest_recommendation` while preserving `run_cycle(...) -> list[dict]`.
- `AgentOrchestrator.feed_transcript(...)` schedules `_run_debate_revision(revision: int) -> None` and returns before inference.
- Broadcasts `{"type":"debate_update","data":{revision,status,answer_now,counterargument,counter_question,target_claim,confidence,needs_research,research_status,sources,generated_at}}`.

- [ ] **Step 1: Write failing agent tests** for German speakable fields, empty-safe defaults, objection compatibility, `/no_think`, uncertainty, and a narrow research query.
- [ ] **Step 2: Run `python -m unittest tests.test_debate_copilot` and verify RED.**
- [ ] **Step 3: Extend the prompt/schema** without changing the existing objection list return contract.
- [ ] **Step 4: Add failing orchestrator tests** proving non-blocking feed, event trigger, old-task cancellation, stale-result discard, current result broadcast, ordinary objection persistence, and close-time cleanup.
- [ ] **Step 5: Replace the periodic objection loop with revision tasks** and preserve Activity Registry state/outcome reporting.
- [ ] **Step 6: Add failing research orchestration tests** for disabled/Privacy First gating, cooldown, background execution, current-revision refinement, stale-revision cache-only behavior, and failure status.
- [ ] **Step 7: Wire `research_claim()` as a separate task** and never await it from the fast recommendation path.
- [ ] **Step 8: Update seeded Objection Handler copy** to describe transcript-event triggering and debate outputs; preserve user-modified saved configs.
- [ ] **Step 9: Run focused agent/orchestrator/seed tests and verify GREEN.**
- [ ] **Step 10: Commit with `feat: add continuous debate fast lane`.**

### Task 4: Live debate panel and WebSocket contract

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/ActiveCall/DebateCoachPanel.tsx`
- Create: `frontend/src/components/ActiveCall/DebateCoachPanel.test.mjs`
- Modify: `frontend/src/components/ActiveCall/ActiveCallView.tsx`
- Modify: `frontend/src/components/ActiveCall/ActiveCallView.test.mjs`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces `DebateRecommendation`, `DebateSource`, and the `debate_update` `WSMessage` variant.
- `App` stores the newest revision only and passes `debateRecommendation` to `ActiveCallView`.
- `DebateCoachPanel` renders three primary cards, confidence/freshness, research state, and claim-linked external sources.

- [ ] **Step 1: Write failing source/contract tests** for newest-revision replacement, stale update rejection, and reset on a new WebSocket call.
- [ ] **Step 2: Add the typed WebSocket contract and state reducer; run the focused test.**
- [ ] **Step 3: Write failing panel tests** for the three German headings, loading/blocked/ready/error states, unverified labeling, safe external-link attributes, and source-to-claim copy.
- [ ] **Step 4: Implement the compact panel** above Live Insights without changing transcript scrolling or the existing insight list.
- [ ] **Step 5: Run `npm test` and `npm run build` from `frontend/`.**
- [ ] **Step 6: Commit with `feat: show live debate recommendations`.**

### Task 5: Idempotent Windows setup and local configuration

**Files:**
- Create: `scripts/setup_debate_assistant.ps1`
- Create: `scripts/tests/test_setup_debate_assistant.ps1`
- Create: `docker-compose.debate.yml`
- Modify: `docs/quickstart.md`
- Modify: `README.md`

**Interfaces:**
- `setup_debate_assistant.ps1 [-SkipInstall] [-SkipModelPull] [-Research] [-DryRun]` detects GPU/Docker/Ollama, installs Ollama through Winget when needed, pulls `qwen3:4b`, starts Compose, and idempotently calls existing endpoint/agent/transcription/privacy APIs.
- Docker override exposes host Ollama as `http://host.docker.internal:11434/v1` without publishing credentials.

- [ ] **Step 1: Write failing PowerShell tests** for command decisions, idempotent endpoint update/create, the encoded model id, German Parakeet v3 payload, agent patch list, Privacy First behavior, and explicit research-egress output.
- [ ] **Step 2: Run the script test and verify RED.**
- [ ] **Step 3: Implement dry-run-safe setup helpers and the Compose override.**
- [ ] **Step 4: Implement API configuration** for the named Ollama endpoint, all live text agents, German batch/live transcription, and privacy/research choice.
- [ ] **Step 5: Run PowerShell tests and `docker compose config`.**
- [ ] **Step 6: Run the setup on the target machine, recording exact Ollama/model/API readiness results.**
- [ ] **Step 7: Update the quickstart with one-command start, data paths, external-query disclosure, Discord/WhatsApp system-audio selection, and recovery steps.**
- [ ] **Step 8: Commit with `feat: automate local debate setup on Windows`.**

### Task 6: Windows desktop build wrapper

**Files:**
- Create: `scripts/build_debate_assistant.ps1`
- Create: `scripts/tests/test_build_debate_assistant.ps1`
- Modify: `docs/releasing.md`

**Interfaces:**
- `build_debate_assistant.ps1 [-Python <path>] [-SkipDownloads]` reuses the checked-in frontend build, model downloaders, `desktop/backchannel.spec`, `desktop/scripts/smoke_test.py`, and writes `dist/Backchannel-DebateAI-windows-x64.zip`.

- [ ] **Step 1: Write failing script tests** for Python 3.12 enforcement, repository-root resolution, exact existing build helpers, fail-fast behavior, and artifact naming.
- [ ] **Step 2: Run the script test and verify RED.**
- [ ] **Step 3: Implement the wrapper without release credentials, tag checks, publishing, or duplicated downloader logic.**
- [ ] **Step 4: Run script tests, then execute the real build and existing desktop smoke test.**
- [ ] **Step 5: Commit with `build: add Windows debate assistant bundle`.**

### Task 7: German replay, latency evidence, and full verification

**Files:**
- Create: `backend/scripts/benchmark_debate_copilot.py`
- Create: `backend/tests/test_debate_benchmark.py`
- Create: `docs/debate-copilot.md`
- Modify: this plan with measured verification evidence.

**Interfaces:**
- Benchmark accepts an OpenAI-compatible endpoint/model plus deterministic German transcript turns and records per-turn first/current update latency, cancellation count, source/refinement latency, and failures as JSON.

- [x] **Step 1: Write failing benchmark tests** for monotonic timing, deterministic fixture loading, cancellation accounting, and honest failure output.
- [x] **Step 2: Implement the benchmark and run its network-free tests.**
- [x] **Step 3: Replay a fast German debate against local Ollama** while monitoring `nvidia-smi`; record model, quantization, VRAM, median/p95 latency, and observed failures.
- [x] **Step 4: Run the complete backend suite:** `python -m unittest discover -s tests` from `backend/`.
- [x] **Step 5: Run frontend tests and production build:** `npm test` and `npm run build` from `frontend/`.
- [x] **Step 6: Run desktop tests and smoke:** `python -m unittest discover -s tests` from `desktop/`, then the built-bundle smoke test.
- [x] **Step 7: Run structural checks when Sentrux is available; report inherited failures separately from new failures.**
- [x] **Step 8: Review `git diff --check`, `git status`, generated artifacts, and the external-data disclosure.**
- [x] **Step 9: Document operation, model choices, privacy behavior, measured performance, and every verification actually run.**
- [x] **Step 10: Commit with `test: verify German debate copilot end to end`.**

### Measured verification evidence (2026-11-03)

- Local application-path replay: 5/5 successful `debate_update` events, zero
  turn or probe failures, and two superseded revisions cancelled. Median/p95
  transcript-ingest-to-update latency: 3,440.794/4,266.817 ms. With Privacy
  First disabling refinement, first and current update are the same event.
- Model: Ollama `qwen3:4b`, 4.0B, Q4_K_M. GPU after replay: 4,732 of
  8,188 MiB in use on an NVIDIA GeForce RTX 4070 Laptop GPU.
- Privacy First kept source refinement and research egress disabled.
- Focused debate tests: 44 passed. Frontend: 232 passed and production build
  completed. Backend: 1,382 passed, 1 skipped, 1 inherited Windows mode-bit
  assertion failed. Desktop: 124 passed, 1 skipped, 1 inherited Windows
  symlink-privilege test errored; the real built-bundle smoke passed.
- Sentrux was unavailable both on `PATH` and at the legacy location named in
  `AGENTS.md`; no structural baseline was refreshed.
- Artifact: `dist/Backchannel-DebateAI-windows-x64.zip`, 280.8 MiB, SHA-256
  `F25F5CC98E6BF3516242AF9FF24441B6E33260D7EC3BEF7C9F22ECB9DE100845`.
