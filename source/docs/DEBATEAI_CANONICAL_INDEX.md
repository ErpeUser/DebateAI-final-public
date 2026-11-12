# DebateAI canonical index

This is the entry point for the maintained product contract. It separates the
active DebateAI implementation from dated evidence and historical release
records so a future change does not treat an old snapshot as a runtime
requirement.

## Maintained contract

- [Quickstart](quickstart.md) — supported desktop, Docker and local setup.
- [Architecture](architecture.md) — current frontend, backend and WebSocket boundaries.
- [Configuration](configuration.md) — canonical `DEBATEAI_*` variables and explicitly configured update endpoints.
- [Desktop finalization](DESKTOP_FINAL.md) — build, install and recovery procedure.
- [Identity decoupling design](identity-decoupling-design.md) — canonical runtime and safe legacy-data migration.
- [Identity decoupling plan](superpowers/plans/2026-11-11-debateai-identity-decoupling.md) — implementation and verification gates.
- [Final status and open gates](FINAL_STATUS_AND_OPEN_ITEMS.md) — evidence register with remaining external gates.

## Migration-only records

Legacy directory names, archive names, environment variables and request
identifiers occur only in explicit migration code and historical provenance or
release evidence. They must not be reintroduced as runtime aliases. Migration
copies data without deleting the source and refuses to overwrite a non-empty
canonical destination.

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
