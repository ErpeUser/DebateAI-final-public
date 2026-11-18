# Incremental domain boundaries

These packages are stable **import facades**, not copied implementations.
The existing `app.services.*` modules remain canonical and preserve current
imports, monkeypatch targets, and test fixtures. This is the first safe phase
towards replacing the 103-file flat service directory; implementations are
moved only after their callers and patching contracts are mapped and tested.

`updates/` owns signature and update interfaces, `transcription/` exposes
language and diarizer selection, and `privacy/` exposes local-only policy.

Do not sweep-move files or use implicit wildcard imports.
