# Gemini Web provider provenance

- Project: `ntthanh2603/gemini-web-to-api`
- Upstream release: `v1.3.4`
- Upstream commit: `10368dfc5cd21312cd5514d7b07c862b7b500492`
- Source archive SHA-256: `a2533adcb6ce3c5715598077ebc6460140d2af1274394a77040bdf6bbbdc0f81`
- Build tool: Go `1.27.3` Windows amd64 archive
- Go archive SHA-256: `f26081f438319757f8a1b46d7d0b2c5ec7583d4038e485e0aa725cfde7885fff`
- Local patch: `backchannel-loopback.patch`
- License: MIT; see `LICENSE`

The local patch makes the listener loopback-only by default and protects every
non-health route with the app-generated bearer key. It does not change model
selection, model discovery, cookie validation, fallback detection, or response
identity reporting.

The checked-in Windows binary was built with `build.ps1` and has SHA-256:

`102b4cef8afa40a939c62988123ef92cb2c3539f0574f2da4c3a255f5783fc75`

