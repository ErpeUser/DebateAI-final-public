# Discord Live Two-Move Design

## Intent

Make the existing live Debate Copilot useful in short Discord debates by keeping exactly two speakable choices visible: a concise answer or counterargument and a concise counter-question. Preserve the existing two rhetoric modes and reuse the current local-model, scheduler, research, revision, privacy, and UI paths.

## Goals

- Produce option A as one directly speakable German sentence, normally no more than 25 words.
- Produce option B as a precise German counter-question, normally 6-14 words.
- Rank the stronger move first using relevance, logical strength, factual confidence, brevity, and recent conversation state.
- Track only the small state needed to distinguish open, partial, answered, unclear, or evaded questions and prepare at most two conditional follow-ups.
- Keep a usable prior or provisional recommendation visible during silence, partial speech, slow local inference, or failed research.
- Preserve immediate local guidance before optional web research and replace it only with relevant, current evidence.
- Keep one compact structured Qwen call per relevant transcript revision.

## Non-goals and anti-goals

- No third rhetoric mode, new agent, new model, new framework, new background service, large argument tree, score dashboard, or ASR replacement.
- No separate LLM call for scoring or follow-up generation.
- No invented contradiction, premise, evasion, evidence, quotation, or factual certainty.
- No forced joke or analogy; the existing `always_analogy` setting remains authoritative.
- No changes to cloud credentials, the subscription bridge, budget controls, Privacy First, user data handling, or Windows security behavior.

## Existing system reused

- `ObjectionHandlerAgent` already performs one structured low-latency call and returns immediate guidance.
- `AgentOrchestrator.feed_transcript()` already cancels superseded work, revision-stamps updates, broadcasts guidance before persistence, and refines current revisions after research.
- `TranscriptBuffer` already carries speaker identity and team/external speaker type.
- `DebateCoachPanel` already receives revision-safe live recommendations and source status.
- Existing Parakeet, Qwen/Ollama endpoint routing, inference scheduler, research frequency, source cache, and Privacy First gates stay in place.

## Approaches considered

1. Extend the existing structured recommendation and render two ranked moves. Selected: it preserves one model call, all revision safeguards, and the current UI shell.
2. Rank the existing fields only in React. Rejected: the UI cannot reliably judge logic, conversation state, or whether a question was answered.
3. Add a separate state/scoring agent. Rejected: it adds latency, calls, synchronization, and architecture the request explicitly excludes.

## Design

Extend `DebateRecommendation` with a compact primary-move discriminator, question status, optional open-question text, and zero to two conditional follow-ups. Keep the existing fields for compatibility: `answer_now` becomes option A, `counter_question` becomes option B, `counterargument` remains structured support for option A, and `analogy` remains optional presentation support controlled by settings.

The prompt receives the existing recent transcript and participant legend. It must distinguish the user's/team speaker from external speakers, classify the latest relevant question state conservatively, and generate answer, question, ranking, and follow-ups in the same response. Hard word limits are validated and normalized without a second scoring call.

The panel renders only two main cards. The selected primary move appears first and the other second. Analogy, open-question status, follow-up, and verified sources appear as compact optional details. A new running revision does not clear the current recommendation; stale revisions and stale research remain blocked by the current reducer and orchestrator checks.

Research continues to run after the first local recommendation. A source refinement must preserve both choices, ranking, state, and follow-ups unless the evidence materially changes them. Privacy First continues to block public research.

## Verification

Test questions, claims by both sides, complete and partial answers, conservative evasion handling, silence/partial transcript retention, rapid speaker changes, source refinement, Privacy First, stale/slow model results, the two existing modes, word limits, and measured local-response latency. Run the focused suites first, then the full backend, frontend, desktop, build, and Windows bundle smoke tests.
