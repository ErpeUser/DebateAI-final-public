# Debate AI V6 release notes

## Included

- Windows x64 PyInstaller onedir package with bundled PostgreSQL, local ASR,
  ffmpeg and the existing desktop runtime.
- External editable prompts and provider configuration beside the executable.
- Safe frozen-runtime path resolution that keeps external configuration out of
  `_internal` and rejects traversal into the immutable bundle.
- Invalid external provider JSON is reported as an explicit configuration
  error instead of being silently treated as an empty configuration.
- Invalid user prompt files use the safe fallback without overwriting the
  user's file.
- Release manifest, full file inventory and SHA-256 checksums.
- Sanitized source snapshot under `source/` with per-file hashes and explicit
  exclusions for generated artifacts, user data, binaries and environment
  secrets.

## Verification

- 242 release-critical backend tests: passed (2 expected skips).
- 94 desktop launcher/PostgreSQL/update tests: passed (1 expected skip).
- 30 prompt/configuration tests: passed.
- 39 V3/manifest/dependency tests: passed.
- 30 manifest/release-contract tests in an isolated Windows temp directory:
  passed.
- Frontend production build: passed, 2,139 modules.
- EXE smoke: health, local ASR readiness and clean shutdown passed.
- External prompt/configuration smoke: prompt hash changed after editing,
  malformed `providers.json` returned HTTP 500, executable hash stayed stable.
- Native Windows update and forced rollback archive smoke: passed.
- Package secret scan: 1,652 readable text files, zero key/token/private-key
  pattern hits; bundled provider configuration equals its default.

## Known limits

The following are intentionally not marked as automated passes:

- A06: real 120+ second German microphone plus Discord/system-audio capture.
- A18: blinded human rhetorical-quality review.
- A21: formal German ASR campaign with reference labels.
- A22: causal independent dataset and human review.
- Real hardware/DPI/install ownership and external rollback acceptance.

These require human or external evidence and must be performed separately.
