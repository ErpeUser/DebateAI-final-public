# Private source snapshot privacy audit

Audit date: 2026-11-09

The private repository contains source and release metadata only. The audit
covered both the current `master` tree and all objects reachable from its Git
history.

## Excluded data classes

- `.env` and machine-local configuration files (the documented `.env.example`
  is a template, not a credential file)
- provider/account overrides containing personal endpoints or API keys
- ChatGPT/Gemini/OpenAI/Google browser profiles, cookies, `Login Data`, web
  storage, OAuth state, refresh/access tokens and credential caches
- local ChatGPT/Gemini conversation history, prompt history, transcripts,
  exports and chat/session databases
- application databases, SQLite files, logs, recordings, audio and temporary
  test/runtime directories
- generated bundles, virtual environments, `node_modules`, build output and
  model/native runtime artifacts

Source code that implements login or cookie handling remains included; only
the per-machine state handled by that code is excluded.

## Evidence

- Current source snapshot: 1,004 files; no tracked `.db`, `.sqlite*`,
  `.jsonl`, `.log`, cookie/profile/history/storage-state or token/credential
  data files.
- Complete repository history: no matching local-data path objects; the only
  `.env` path is the safe `.env.example` template.
- Credential scan: no live API key, GitHub token, bearer token or private-key
  material. The only matches are five intentionally synthetic redaction-test
  fixtures, listed in `SOURCE_SNAPSHOT_MANIFEST.json`.
- `ai/providers.json` is byte-identical to `ai/providers.default.json` and
  contains no endpoint URL, account identifier or secret.

This audit does not remove or alter the working tree's local runtime data. It
only verifies the already-sanitized copy that is published in the private
repository.
