# V3 dependency audit

`backend/scripts/audit_dependencies.py` is the reproducible inventory command
for direct production requirements. It reads the checked-in constraints,
resolves the installed distribution from the release virtual environment, and
records marker, native-component hint, purpose, platform and package-reported license in
[`dependency-audit-v3.json`](dependency-audit-v3.json).

Run it from `backend/` with:

```text
..\.release-venv\Scripts\python.exe scripts\audit_dependencies.py requirements.txt --output ..\docs\dependency-audit-v3.json
```

The current audit is deliberately non-destructive. It makes no upgrade
decision and marks compatibility/security review as required rather than
claiming that package metadata is a security proof. The generated
`security_status: not_scanned` and `deprecation_status: manual_review` fields
make those limits machine-readable. The installed runtime is
Python 3.12; `windows_audio_capture.py` still uses `audioop`, so a future
Python 3.13 move requires a separately tested backport or converter change.
The native paths are explicitly flagged (`onnxruntime`, `kaldi-native-fbank`,
`numpy`, `PyAudioWPatch`, `soundfile`, `pywebview`, and `pyinstaller`).

This closes the reproducible inventory part of P2.8 without a blanket upgrade.
Remaining security-advisory review and any Python-version migration are
release-time decisions and must not be inferred from this file alone.
