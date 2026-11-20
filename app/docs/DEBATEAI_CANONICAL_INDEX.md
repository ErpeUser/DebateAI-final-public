# DebateAI canonical index

This is the entry point for the maintained product contract. It separates the
active DebateAI implementation from dated evidence and historical release
records so a future change does not treat an old snapshot as a runtime
requirement.

## Maintained contract

- [Product vision](VISION.md) — owner-approved current goal and consolidated target extensions.
- [Open items](OFFENE_PUNKTE.md) — maintained P0–P3 backlog and current verification limits.
- [History and provenance](HISTORIE.md) — earlier visions, research decisions, reconciliation and dated evidence; not current release acceptance.
- [Quickstart](quickstart.md) — supported desktop, Docker and local setup.
- [Architecture](architecture.md) — current frontend, backend and WebSocket boundaries.
- [Configuration](configuration.md) — canonical `DEBATEAI_*` variables and explicitly configured update endpoints.
- [Desktop release and recovery](releasing.md) — current build, signing, update and recovery procedures.
- [Identity decoupling design](identity-decoupling-design.md) — canonical runtime and safe legacy-data migration.

## Historical and migration-only records

- [Windows recovery notes (11 November 2026)](windows-final-recovery.md) — dated recovery guidance retained for provenance, **not** current build commands.
- The 12 November 2026 Codex acceptance audit is retained in the historical evidence ledger.


Legacy directory names, archive names, environment variables and request
identifiers occur only in explicit migration code, negative regression tests,
historical provenance or release evidence. The historical SEO route
`/gong-and-backchannel/` is also retained as a redirect/content slug; it is
not a runtime identifier. They must not be reintroduced as runtime aliases.
Migration copies data without deleting the source and refuses to overwrite a
non-empty canonical destination. Migration-only PII key purposes are used only
by the startup rewrite and never by active reads or writes.

`SOURCE_SNAPSHOT_MANIFEST.json`, `release-manifest.json`, dated release notes,
the large technical disclosure and historical audit files are integrity or
evidence artifacts. Regenerate them from a fresh release rather than editing
hashes by hand.

## Verification rule

A gate is complete only when a fresh command, test, release artifact or
manually recorded hardware result proves it. CI provisioning failures,
real-model audio acceptance, human rhetorical review, Windows signing and
external DNS or update publication remain separate gates until evidence is
attached.
