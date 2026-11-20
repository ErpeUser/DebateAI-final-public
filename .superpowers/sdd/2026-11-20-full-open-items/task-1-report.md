# Task 1 report

## Result

Docs-site and active repository references now use the checked-in `app/docs`
contract, `ErpeUser/DebateAI-final-public`, and `main`. The docs root is the
maintained canonical index. Sync, Astro navigation, LLM assembly, README,
quickstart, deployment/release runbooks, and static site/release links no
longer point at absent docs or the historical `source`/`master` layout.

The focused implementation commit is `c7e94fe` (`docs: synchronize site links
and canonical repository layout`). It changes `app/docs-site/{site.test.js,
sync-docs.mjs,assemble.mjs,astro.config.mjs}`, the active README and docs
references, and the 50 static site/release pages that carried the old source,
branch, or missing docs links.

## Verification

- `cd app/docs-site && npm test` passed, 171 tests across all suites.
- `cd app/docs-site && npm run build` passed and assembled `dist-site` with 20
  docs pages.
- `python -m unittest app/scripts/tests/test_repository_layout.py` passed, 11
  tests.
- `git diff --cached --check` passed before commit.
- The regression was red before implementation because `site.test.js` loaded
  the absent `app/docs/README.md` and asserted the old repository/branch
  contract. It passes after the contract fix and checks every checked-in docs
  markdown link.

## External-only items

No external release gate was claimed. Windows Authenticode signing, real
hardware/audio acceptance, provider credentials, Cloudflare DNS/R2/D1
production cutover, and customer catalog publication still require operator
evidence outside this repository.
