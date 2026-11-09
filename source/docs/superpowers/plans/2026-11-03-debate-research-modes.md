# Debate Research and Rhetoric Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable live-debate modes, mandatory analogy guidance, and adjustable background research while supporting an optional localhost OAuth subscription bridge.

**Architecture:** A focused debate-settings service persists validated JSON and is exposed through one router. New calls receive an immutable settings snapshot; the existing Debate Copilot and research scheduler consume it. The frontend renders one settings card, while the existing Connections endpoint mechanism handles a local OpenAI-compatible bridge.

**Tech Stack:** FastAPI, SQLAlchemy app settings, Pydantic, React/TypeScript, stdlib unittest, Node behavior tests.

**Spec:** `docs/superpowers/specs/2026-11-03-debate-research-modes-design.md`

## Global Constraints

- Do not store or copy provider OAuth tokens in Backchannel.
- Public research stays disabled under Privacy First.
- Immediate guidance must never wait for research.
- `Brutal-sachlich` attacks claims, never people.
- Preserve existing editable agent prompts and endpoint configuration.
- Desktop defaults are research enabled with frequency `often`; the bridge process lives only as long as Backchannel.

## Review Focus

- Invalid persisted settings fall back to safe defaults.
- Privacy First suppresses research even when enabled.
- A newer transcript revision cannot be overwritten by older research.
- Missing analogy triggers the same one-shot correction as other missing guidance.
- Frequency presets map to deterministic cooldowns and reject unknown values.

---

### Task 1: Persisted debate settings and API

**Files:**
- Create: `backend/app/services/debate_settings.py`
- Create: `backend/app/routers/debate_settings.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_debate_settings.py`

**Interfaces:**
- Produces: `DebateSettings`, `get_debate_settings(db)`, `set_debate_settings(db, value)`, `GET/PATCH /api/debate-settings`.

- [ ] Write failing validation, fallback, persistence, and router tests.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement the minimal service and router.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Runtime rhetoric modes, analogy, and frequency

**Files:**
- Modify: `backend/app/services/agents/objection_handler.py`
- Modify: `backend/app/services/agents/orchestrator.py`
- Modify: `backend/app/ws/audio_handler.py`
- Modify: `backend/app/services/agents/prompts.py`
- Test: `backend/tests/test_objection_handler.py`
- Test: `backend/tests/test_agent_orchestrator.py`

**Interfaces:**
- Consumes: `DebateSettings` snapshot.
- Produces: `DebateRecommendation.analogy` and style-specific prompt composition.

- [ ] Write failing tests for analogy, both mode instructions, and cooldown mapping.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement runtime wiring and stronger prompt contract.
- [ ] Run focused tests and confirm they pass.

### Task 3: Administration settings card

**Files:**
- Create: `frontend/src/components/DebateSettingsCard.tsx`
- Create: `frontend/src/components/DebateSettingsCard.test.mjs`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/components/AdminPanel.tsx`
- Modify: `frontend/src/components/ActiveCall/DebateCoachPanel.tsx`

**Interfaces:**
- Consumes: `/api/debate-settings`.
- Produces: mode/frequency/research controls and an analogy card.

- [ ] Write failing behavior tests for controls, API payloads, and analogy rendering.
- [ ] Run frontend tests and confirm expected failures.
- [ ] Implement the minimal UI and API client.
- [ ] Run behavior tests and `npm run build`.

### Task 4: Local subscription bridge setup and configuration

**Files:**
- Reuse: `frontend/src/components/EndpointsCard.tsx`
- Reuse: `backend/app/services/custom_endpoints.py`

**Interfaces:**
- Consumes: loopback OpenAI-compatible endpoint exposed by the separately authenticated bridge.
- Produces: endpoint model entries assignable to the Debate Copilot.

- [ ] Download a checksum-published Windows x64 bridge release only after explicit approval.
- [ ] Bind it to `127.0.0.1`, create a local client key, run it as a Backchannel child process, and open its interactive OAuth login.
- [ ] Register the endpoint through Backchannel's existing Connections API.
- [ ] Select a fast subscription-backed model for Debate Copilot after login exposes the catalog.

### Task 5: Verification and installation

**Files:**
- Modify: installed desktop bundle only through the existing release build workflow.

- [ ] Run backend focused suites and the full backend suite.
- [ ] Run desktop tests, frontend behavior tests, and frontend build.
- [ ] Build and smoke-test the Windows bundle.
- [ ] Update the local installation without replacing user data and verify the app health endpoint.
