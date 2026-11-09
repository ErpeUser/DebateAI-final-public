# Debate Research and Rhetoric Modes Design

## Intent

Make Backchannel useful for live German debates: immediate speakable guidance, optional source-backed research, and two selectable rhetorical styles. Reuse a user's own subscription through a local OAuth bridge where permitted; never copy browser cookies or OAuth token files into Backchannel.

## Goals

- Add `Ueberzeugend` and `Brutal-sachlich` modes.
- Always return a short, defensible analogy alongside answer, counterargument, and counter-question.
- Add `Wenig`, `Normal`, and `Oft` research frequency presets; desktop defaults to enabled + `Oft`.
- Persist these controls in Administration and apply them to new live calls.
- Keep immediate guidance independent of slow research.
- Allow a localhost OpenAI-compatible subscription bridge through the existing Connections endpoint mechanism.

## Non-goals and anti-goals

- No automated browser UI, copied cookies, scraped consumer sessions, multi-account rotation, or account farming.
- No personal attacks, humiliation, fabricated certainty, fake citations, or manipulative dark patterns in the forceful mode.
- Backchannel does not own provider OAuth tokens; a separately installed bridge owns and refreshes them.

## Constraints

- Privacy First blocks public research.
- Research sends only a narrow fact query without participant names or private details.
- The third-party bridge is optional and bound to loopback; the app remains functional without it.
- Existing user-edited agent prompts remain editable.
- Any bundled subscription bridge is a child process of Backchannel and stops when Backchannel exits.

## Approaches considered

1. Automate ChatGPT/Gemini websites through a logged-in browser. Rejected: fragile UI coupling and unnecessary cookie/session exposure.
2. Call Codex/Gemini CLIs for every fact check. Safe login path but high process startup latency for live speech.
3. Use a local OAuth-to-OpenAI bridge and Backchannel's existing custom-endpoint support. Selected: one login, stable localhost protocol, model reuse across agents, and no provider token inside Backchannel.

## Design

Store debate settings as one validated `app_settings` JSON record. Pass a snapshot into each new `AgentOrchestrator`. The Debate Copilot appends the selected style playbook to its system instruction and returns an `analogy` field. Research scheduling reads the frequency preset for cooldown and triggers on material claims or a changed main topic while retaining caching, revision protection, and immediate-first response.

Administration gets a dedicated Debate Copilot card above the generic agent editor. Connections remains the place to register the localhost subscription bridge and choose its model for the Debate Copilot.
