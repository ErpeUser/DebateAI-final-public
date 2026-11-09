# Discord Live Two-Move Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show exactly two concise, ranked, speakable German moves during a live Discord debate while preserving the existing two modes, one-call local inference, research, revision, privacy, and desktop paths.

**Architecture:** Extend the existing `DebateRecommendation` schema and `ObjectionHandlerAgent` prompt with compact conversation state, ranking, and at most two conditional follow-ups. Reuse the existing orchestrator and reducer safeguards, then reduce the live panel to two ranked cards with optional compact context below them.

**Tech Stack:** Python 3, Pydantic, FastAPI service layer, stdlib `unittest`, React, TypeScript, Node test runner, Vite.

**Spec:** `docs/superpowers/specs/2026-11-03-discord-live-two-moves-design.md`

## Global Constraints

- Preserve exactly the two existing rhetoric modes: `persuasive` and `forceful`.
- Do not add an agent, model, framework, background service, dashboard, question tree, or ASR path.
- Keep one compact structured model call per relevant transcript revision; the existing empty-output retry is the only recovery call.
- Option A is one directly speakable German sentence, normally at most 25 words.
- Option B is a precise German counter-question, normally 6-14 words.
- Track only `none`, `open`, `partial`, `answered`, `unclear`, or `evaded`, plus at most two conditional follow-ups.
- Preserve the previous recommendation while a newer revision or research refinement is running.
- Do not alter cloud credentials, subscription bridge, budget controls, Privacy First, user data, or Windows security in this plan.
- Do not commit the existing dirty worktree unless the user explicitly requests a commit.

## Review Focus

- An external speaker asks a question: both moves remain present and the stronger one is first.
- The team speaker makes a claim: the model anticipates likely pushback without misattributing the speaker.
- A response is partial or ambiguous: status stays conservative and does not invent evasion.
- A newer transcript arrives before an older analysis/research result: only the newest revision remains visible.
- The local model or research is slow/unavailable: the last usable recommendation remains on screen.

---

### Task 1: Structured recommendation and compact conversation state

**Files:**
- Modify: `backend/app/services/agents/objection_handler.py`
- Modify: `backend/app/services/agents/prompts.py`
- Test: `backend/tests/test_objection_handler.py`

**Interfaces:**
- Consumes: existing `run_cycle(transcript_window, directives, speakers)` and `generate_json(...)` path.
- Produces: `ConditionalFollowUp`, `DebateRecommendation.primary_move`, `question_status`, `open_question`, and `follow_ups`; preserves all existing fields.

- [ ] **Step 1: Write failing schema and prompt tests**

Add tests named `test_recommendation_accepts_ranked_two_move_state`, `test_follow_ups_are_limited_to_two`, `test_prompt_requests_word_limits_ranking_and_conservative_question_state`, and `test_previous_question_state_is_included_in_next_cycle`. Assert the exact status values, `primary_move` values, the two-follow-up cap, 25-word/6-14-word instructions, team/external distinction, and prior state in the second request.

- [ ] **Step 2: Run the focused tests and verify the new assertions fail**

Run: `cd backend; python -m unittest tests.test_objection_handler`

Expected: FAIL because the new schema fields/state prompt do not exist.

- [ ] **Step 3: Implement the minimal schema and state path**

Add `ConditionalFollowUp(condition: str, question: str)`, the exact recommendation fields above, `Field(max_length=2)` for follow-ups, and a private compact state updated only after a usable current response. Append that state to the next prompt. Require only the two speakable moves (plus analogy when configured) for usability; keep `counterargument` compatible but non-mandatory.

- [ ] **Step 4: Tighten the existing prompt without adding another model call**

Require one-sentence option A, 25 words normally; option B, 6-14 words; joint ranking by relevance, logic, factual confidence, brevity, and context; conservative question status; no invented evasion; zero to two conditional follow-ups; and explicit team/external speaker handling.

- [ ] **Step 5: Run the focused tests and verify they pass**

Run: `cd backend; python -m unittest tests.test_objection_handler`

Expected: PASS.

### Task 2: Preserve state through source refinement and revisions

**Files:**
- Modify: `backend/app/services/agents/objection_handler.py`
- Test: `backend/tests/test_debate_copilot.py`
- Test: `backend/tests/test_objection_handler.py`

**Interfaces:**
- Consumes: extended `DebateRecommendation` from Task 1 and current orchestrator revision checks.
- Produces: source-refined recommendations that keep `primary_move`, question state, open question, and follow-ups unless verified evidence materially changes the actual moves.

- [ ] **Step 1: Write failing refinement and stale-result tests**

Add `test_source_refinement_preserves_rank_and_conversation_state`, `test_new_revision_keeps_previous_recommendation_until_ready`, and `test_stale_research_cannot_replace_newer_two_move_result`. Assert exact revision, ranking, status, and follow-up values.

- [ ] **Step 2: Run the focused tests and verify the new assertions fail**

Run: `cd backend; python -m unittest tests.test_objection_handler tests.test_debate_copilot`

Expected: at least the refinement preservation assertion FAILS.

- [ ] **Step 3: Preserve compact state during source refinement**

Tell the refinement prompt to retain ranking/state/follow-ups and deterministically restore the original values when a refinement omits them. Do not change the orchestrator scheduling, cancellation, cache, Privacy First, or broadcast order unless a failing regression test proves it necessary.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `cd backend; python -m unittest tests.test_objection_handler tests.test_debate_copilot`

Expected: PASS.

### Task 3: Render exactly two ranked live cards

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/components/ActiveCall/DebateCoachPanel.tsx`
- Modify: `frontend/src/components/ActiveCall/DebateCoachPanel.test.mjs`

**Interfaces:**
- Consumes: the extended WebSocket `DebateRecommendation` object.
- Produces: exactly two main cards ordered by `primary_move`, with compact optional analogy, open-question status, one next follow-up, and existing sources.

- [ ] **Step 1: Replace the four-card test with failing two-card tests**

Add `renders exactly two ranked moves`, `question-first reverses the card order`, `compact context does not become a third card`, and `keeps prior guidance visible while activity is running`. Assert labels `Antwort / Gegenargument` and `Gegenfrage`, absence of the old four labels, and exactly two `<article>` elements.

- [ ] **Step 2: Run the component test and verify it fails**

Run: `cd frontend; node --test src/components/ActiveCall/DebateCoachPanel.test.mjs`

Expected: FAIL because four cards are still rendered and new fields are untyped.

- [ ] **Step 3: Extend the frontend type and render two ranked cards**

Add the matching field unions and follow-up shape. Build a two-item array from `answer_now` and `counter_question`, order it from `primary_move`, keep the existing recommendation during `running`, and move analogy/status/follow-up into compact non-card details. Correct corrupted German text in this touched component.

- [ ] **Step 4: Run the component test and frontend build**

Run: `cd frontend; node --test src/components/ActiveCall/DebateCoachPanel.test.mjs`

Run: `cd frontend; npm run build`

Expected: PASS; build may retain the existing chunk-size warning.

### Task 4: Regression, latency, and Windows bundle verification

**Files:**
- Modify only if a focused failure proves necessary: `backend/scripts/benchmark_debate_copilot.py`
- Update: `.superpowers/sdd/2026-11-03-discord-live-two-moves/progress.md`

**Interfaces:**
- Consumes: completed backend and frontend changes.
- Produces: test evidence and a refreshed Windows desktop bundle; no new runtime interface.

- [ ] **Step 1: Run debate latency and focused regression checks**

Run: `cd backend; python -m unittest tests.test_debate_benchmark tests.test_debate_settings tests.test_subscription_bridge`

Expected: PASS with the existing measured latency/cancellation assertions.

- [ ] **Step 2: Run full backend, frontend, and desktop suites**

Run: `cd backend; python -m unittest discover -s tests`

Run: `cd frontend; npm test`

Run: `cd desktop; python -m unittest discover -s tests`

Expected: PASS except only previously documented environment-specific skips.

- [ ] **Step 3: Run structural and diff checks**

Run: `sentrux check .`

Run: `sentrux gate .`

Run: `git diff --check`

Expected: only the two approved generated-lockfile structural exceptions; no new gate regression or whitespace error.

- [ ] **Step 4: Rebuild and smoke-test the Windows desktop bundle**

Use the repository's existing desktop build command and smoke checks. Verify `dist/Backchannel/Backchannel.exe` starts, owns the local bridge only while running, and does not clear the last recommendation during a slow revision.

- [ ] **Step 5: Record exact results and stop**

Update the progress ledger with commands, pass/fail counts, measured latency, changed files, and remaining limits. Do not add unrelated cleanup after the smallest verified patch passes.
