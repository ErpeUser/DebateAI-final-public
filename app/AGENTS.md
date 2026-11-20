# DebateAI / app

The repository root [AGENTS.md](../AGENTS.md) is the canonical agent instruction.
Follow it first; do not treat older continuation notes or dated snapshots as
current runtime instructions.

- Versioned source and necessary inputs live in app/; generated outputs
  belong outside it, under DebateAI_Generated/.
- Never delete private user data under %LOCALAPPDATA%/DebateAI, PostgreSQL
  files, secrets, saved sessions or customizable playbooks.
- Retain the live Python/Node/Desktop entry points, APIs, migrations, release
  contracts and source assets. Static scanner results require verification.
- Follow docs/DEBATEAI_CANONICAL_INDEX.md, docs/releasing.md and
  docs/OFFENE_PUNKTE.md for current open gates and docs/HISTORIE.md for dated evidence.
- Run targeted tests and fresh builds. Do not assert a signed release without
  a new binary, verified signature and smoke test.
- Root GitHub workflows may name a checkout folder source/; that alias is
  not the former application source tree.
- Preserve Git history and existing independent recovery copies. Avoid
  duplicate stage directories, worktrees and unreviewed generated files.
- GitHub work uses the public repository `ErpeUser/DebateAI-final-public` on
  its standard `main` branch. Work directly on `main`, commit and push there,
  and do not create feature branches or pull requests for agent changes.
- Before pulling, run `python app/scripts/github_sync.py --pull --strict`.
  Review every listed non-`main` branch and open pull request, then apply,
  combine or supersede candidates on `main` after tests. Never blindly merge,
  close or delete candidates.
