# Release Hardening Design

## Intent

Prepare the current DebateAI/Backchannel source tree for a fresh Windows x64 one-dir release while preserving user data, settings, secrets, and the already working release until the new candidate passes its smokes.

## Goals

- Keep corrected claim text and revisions attached to cached research, topic knowledge, and visible live answers.
- Run real Alembic migrations for an empty database, but safely adopt an existing unversioned database without replaying destructive historical migrations.
- Avoid reconnect churn when a healthy socket merely becomes visible again.
- Guarantee that opening the desktop app produces a visible surface even when the embedded WebView2 child starts without creating a window.
- Open the official OpenAI/Codex OAuth page from the original user click so browser popup blocking cannot turn login into an apparently inert action.
- Prove the changes with focused tests, then build and smoke a fresh staged EXE and ZIP before atomically publishing them to `dist`.

## Non-goals and constraints

- No privacy-first/privacy redesign, RL tests, broad refactor, provider/model download beyond existing build assets, or full-suite run.
- No destructive database reset and no change to user configuration or secrets.
- Preserve the current dirty working tree; do not isolate from it because the requested build must contain that exact source state.

## Approaches

1. Broad rewrite of orchestration, migration startup, and socket delivery: rejected as high-risk and contrary to the requested scope.
2. Build the current source unchanged: rejected because inspection found concrete revision and empty-database gaps.
3. Selected: add narrow revision guards/cache rebinding, distinguish empty from adopted databases, and suppress only redundant visibility reconnects. This yields measurable benefit with small, testable changes.

## Design

- Rebind a cached `ResearchResult` to the current target claim before creating `DebateSource` objects. Store topic knowledge only when its claim revision is not older than the stored revision. Reject a server-side debate update whose explicit claim/transcript revision is already stale.
- Classify schema startup as `upgrade` for empty or already versioned databases and `adopt` only for databases with application tables but no `alembic_version`. Adoption keeps `create_all` plus compatibility column patches followed by `stamp head`.
- Reconnect on visibility only when the session still wants a connection and the socket is neither OPEN nor CONNECTING.
- Treat an embedded GUI child as successful only after Windows reports a visible top-level window. If the child exits or remains invisible for a short bounded interval, stop it and open the same local URL in the system browser; retain the tray process and log the fallback.
- Reserve an OAuth browser window synchronously from the OpenAI login button, navigate it after the local bridge returns the authorization URL, and close the placeholder on failure. Keep the existing visible link as a fallback when popups are disabled.
- Use the existing staged build script, which retains the current `dist` artifacts until both staged bundle and archive smokes pass, then swaps the candidate into place.
