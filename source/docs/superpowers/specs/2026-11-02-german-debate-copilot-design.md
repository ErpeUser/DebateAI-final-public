# German Debate Copilot Design

## Intent

Turn Backchannel into a local-first German debate copilot that keeps listening
while it continuously replaces its visible recommendation with the best short,
speakable answer, counterargument, and counter-question available at that
moment. Fast guidance must never wait for deeper analysis or web research.

## Success criteria

- A final transcript segment schedules guidance without blocking audio ingest or
  transcription.
- Only the newest transcript revision may update the visible recommendation;
  obsolete local-model work is cancelled or discarded.
- The live view always distinguishes the answer, counterargument,
  counter-question, confidence, research status, and sources.
- Consolidated Analyst, Objection Handler, Synthesizer, and Strategic Signals
  continue to run and enrich the broader conversation model.
- Research is occasional, keyless, non-blocking, claim-linked, transparent, and
  disabled by Privacy First.
- A Windows setup script installs/configures Ollama, pulls one appropriately
  sized model, starts Backchannel, selects German local transcription, registers
  the endpoint, and assigns the local text model without purchasing an API.
- A Windows desktop bundle can be built and smoke-tested with a separate script.

## Non-goals and anti-goals

- Do not automate consumer ChatGPT or Google AI web sessions, scrape logged-in
  pages, or bypass subscription/API boundaries.
- Do not make Codex Desktop or Antigravity a runtime dependency. Neither offers
  a usable unattended CLI in the inspected environment.
- Do not introduce another database-backed insight system or duplicate the
  existing strategic agents.
- Do not persist ephemeral recommendations or add a database migration.
- Do not let research, synthesis, or a slow local inference call stall audio or
  transcription.
- Do not invent sources or present a search snippet as verified fact.

## Constraints and selected local models

- Target: Windows laptop, NVIDIA RTX 4070 Laptop GPU, 8,188 MiB VRAM.
- Text model: `qwen3:4b` through Ollama's OpenAI-compatible endpoint. The
  official Ollama registry reports a 2.5 GB artifact and multilingual support;
  using one 4B model for all text roles avoids keeping competing models in VRAM.
- Transcription: `local-parakeet-tdt-0.6b-v3` for durable German segments and
  `local-parakeet-v3-live` for local interim captions, with the workspace
  language set to `de`. Whisper Base remains the fallback already present in
  Backchannel.
- Use the existing PostgreSQL, WebSocket, model registry, custom endpoint,
  Privacy First, PII Shield, local-fit, audio, and desktop packaging systems.

## Approaches considered

### Selected: extend the existing Objection Handler into the fast debate lane

One structured low-latency call returns both ordinary objection findings and an
ephemeral recommendation. The orchestrator triggers it from transcript events,
cancels superseded work, persists only the existing objection insights, and
broadcasts the recommendation separately. This reuses the current prompt,
model selection, activity state, transcript buffer, deduplication, and insight
pipeline with the fewest additional model calls.

### Rejected: add a separate Debate Agent

This is easier to reason about in isolation but duplicates model configuration,
prompt context, activity reporting, and GPU work. On an 8 GB laptop it also
raises the chance that the supposedly fast path queues behind itself.

### Rejected: repurpose Strategic Signals for the live recommendation

Strategic Signals already has the right big-picture inputs, but its interval,
large context, database reads, and five-section output make it the wrong latency
boundary. It remains a background input rather than the immediate responder.

## Runtime architecture

1. `feed_transcript()` appends the final German segment to the existing ring
   buffer, increments a monotonic debate revision, cancels the prior fast-lane
   task, and schedules a new task without awaiting it.
2. The Objection Handler reads only the fresh debate window and returns a
   compact `DebateRecommendation` plus zero or more existing objection items.
   The prompt requires German, one or two speakable sentences per field,
   `/no_think`, explicit uncertainty, and a narrowly worded research query only
   when a material factual claim is unresolved.
3. The orchestrator discards any result whose revision is not current. Current
   objections enter the existing insight pipeline; the recommendation is sent
   as `debate_update` and replaces the current UI state.
4. A local-endpoint inference scheduler allows one request per endpoint. A
   high-priority debate request preempts the inner HTTP request of a normal
   background agent; the background loop remains alive and retries on its next
   normal trigger.
5. If research is requested, enabled, outside Privacy First, outside the
   cooldown, and contains no raw PII, the orchestrator starts a separate task.
   Wikimedia search/extract and DuckDuckGo Instant Answer are queried with
   timeouts. Results keep title, canonical URL, snippet, provider, and the
   target claim.
6. Research failure only updates research status. Success is cached and may
   refine the recommendation if its revision is still current; otherwise the
   evidence is available to the next fast cycle. Every displayed source is a
   real returned URL associated with the exact claim it supports or challenges.
7. Consolidated Analyst, Synthesizer, and Strategic Signals retain their
   existing schedules and persistence behavior. They never sit on the fast
   lane's awaited path.

## User interface

The active-call screen gains a compact `DebateCoachPanel` above the ordinary
insight list. It has three stable, glanceable cards: "Direkte Antwort",
"Stärkstes Gegenargument", and "Beste Gegenfrage". A narrow metadata row shows
the target claim, confidence, whether the result is updating, and research
state. A source area shows only sources attached to the target claim, opens
canonical URLs in a new tab, labels unverified/model-only guidance clearly, and
never displaces the continuously scrolling transcript or live insights.

## Privacy and external access

Audio, transcription, debate generation, and background agents run locally in
the supplied setup. Automatic research sends only the model-produced factual
query to public Wikimedia and DuckDuckGo endpoints. Privacy First disables this
egress. PII token markers make a query ineligible, and errors never expose
credentials because no research credential exists.

## Installation and operation

`scripts/setup_debate_assistant.ps1` is idempotent. It verifies the NVIDIA GPU
and Docker, installs Ollama with Winget only when absent, pulls `qwen3:4b`,
starts the Compose stack, waits for health, creates or updates a named local
endpoint, assigns its model to live text agents, enables Privacy First only
when automatic research is not requested, and selects the German Parakeet v3
transcription models. It prints the app URL and explicit data-egress setting.

`scripts/build_debate_assistant.ps1` creates an isolated Python 3.12 virtual
environment, installs the checked-in requirements, builds the frontend,
downloads the existing ONNX/PostgreSQL/FFmpeg assets, runs PyInstaller using
the existing spec, runs the existing desktop smoke test, and writes a Windows
zip under `dist/`.

## Verification

- Unit tests cover schema normalization, German brevity, stale-result discard,
  cancellation, scheduler preemption, research gating/deduplication/timeouts,
  source-to-claim mapping, and unchanged audio/transcript flow.
- Frontend tests cover replacement semantics, three primary cards, confidence,
  research states, verified links, and unverified labeling.
- Script tests cover dry-run/idempotent command decisions and endpoint payloads.
- The complete backend suite, frontend tests/build, desktop tests, and desktop
  smoke test remain the release gates.
- A deterministic German debate replay measures time from transcript ingest to
  `debate_update`; hardware benchmarking records real results without claiming
  an unmeasured latency.
