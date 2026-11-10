# Contributing

Before opening a pull request:

1. Run the backend unit and integration tests.
2. Run `npm ci`, `npm run build`, and `npm test` in `source/frontend`.
3. Run the security and dependency checks.
4. Do not add credentials, recordings, transcripts, generated secrets, or unpinned runtime downloads.
5. Keep new network clients behind bounded timeouts, response limits, and explicit allowlists.

Changes affecting authentication, PII handling, provider routing, uploads, release workflows, or dependencies require a security-focused review.
