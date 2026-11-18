# Repeatable DebateAI UI capture

Uses [agent-browser](https://github.com/vercel-labs/agent-browser), tested with
0.43.0 and its Chromium, without adding a production dependency or rebuilding the
Windows executable. Node 24 is required. Install once if missing:

```powershell
npm install -g agent-browser@0.43.0
agent-browser install
```

Start DebateAI normally, then from the real checkout:

```powershell
.\app\scripts\capture_gui_surfaces.ps1 -BothThemes
```

The DOM entry point accepts the same options. Supply `-Url` if the desktop uses
another loopback port; do not put credentials or instance tokens in that URL.
`AGENT_BROWSER_BINARY` can point to a differently installed native CLI binary.
Screenshots are saved under `DebateAI_Generated/reports/gui-capture/<timestamp>/<theme>/`, with
`index.html`, `manifest.json` and a ZIP containing both themes. Failed runs keep
their evidence but exit unsuccessfully. Do not publish these local artifacts:
read-only provider/settings views can still contain personal information.

## What is automatic

- Enumerates visible settings and review tabs, without hardcoded agent counts.
- Recursively opens visible content disclosures and nested `details`; excludes
  hidden tabs, sidebar navigation, switches and action menus.
- Handles independent iframe documents, nested scroll containers, textareas and
  horizontal overflow. Records actual scroll positions, dimensions and SHA256.
- Retains original viewport screenshots and overlapping scroll tiles. A separate
  full-content rendering temporarily removes height/overflow constraints.
- Single-open accordions are read one at a time. Their actually rendered bodies
  are retained as inert, capture-only copies for the expanded rendering, recorded
  as `retainedPanels`. This is not the application's simultaneous-open behavior.
- Detects remaining closed disclosures, clipped content, inaccessible frames,
  missing controls and safety limits; these are failures, not successful skips.
- Waits for independent card-loading placeholders to finish, with a bounded
  timeout rather than silently capturing a loading-only page as complete.

## Deliberately bounded workflow

Welcome, new debate dialog and browser-only creation, expanded preparation,
active/pause view in both debate modes, all ten review tabs, material, sources and
source creation form, all five settings tabs, laboratory and its blind demo.
Workflow entry points are explicit safe actions: a generic click-everything
crawler would delete data, start microphones, download models or initiate logins.
Additional conditional workflows need representative fixtures and a coverage
entry; this is not an assertion that every possible data/error state is covered.

Fixtures replace only debate/session data inside an isolated browser profile.
Creation never reaches the database; all other API writes, sockets and microphone
requests are blocked. Settings GETs remain real. No login cookies are imported,
and no credentials/tokens are included in reports. These screenshots prove UI
rendering, **not** live audio, model quality, provider readiness, native tray UI,
installer behavior or Windows release acceptance. Existing native window capture
is still available as `app/scripts/capture_debateai_window.ps1`.

The manifest records checkout HEAD/dirty state, capture-code SHA256, application version, URL, theme,
scope and failures. The running application can be older than checkout HEAD:
capture is not a build/install operation.

## Focused regression checks

```powershell
node --test app/scripts/gui-capture/capture.test.mjs
```

Tests use real Chromium for nested/exclusive disclosures, full-height restoration,
stale scroll identities, horizontal movement, iframe scrolling and delayed card
readiness; separate behavioral checks prove the fixture write guard does not
forward mutations and credential-bearing capture URLs are rejected.
