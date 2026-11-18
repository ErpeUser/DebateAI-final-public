## Ziel und Änderungen

Beschreibe kurz die Änderung und die betroffenen Teile (Backend, Frontend,
Desktop, Website, Release-Pipeline).

## Struktur und Sicherheit

- [ ] Versionierter Code und Eingabedaten liegen unter `app/`; GitHub-Actions nur in `.github/workflows/` im Repository-Root.
- [ ] `runtime/` und `DebateAI_Generated/` bleiben außerhalb von Git.
- [ ] Keine Geheimnisse, `.env`-Varianten, Datenbanken, Transkripte, ausführbaren Builds oder Benutzerdateien committed.
- [ ] `app/site/` und `app/docs-site/` bleiben eigenständige Quellordner.
- [ ] Öffentliche Release-Signaturschlüssel, Build-Skripte und Lockfiles bleiben versioniert.
- [ ] Bei Release-/Updater-Änderungen: SHA-256, Ed25519 und Rollback überprüft.

## Testnachweise

- [ ] `python app/scripts/verify_repository_layout.py`
- [ ] `python app/scripts/workspace_refs.py --source-only --strict`
- [ ] Passende Backend-, Frontend-, Desktop- und Docs-Tests ausgeführt.
- [ ] `git diff --check` erfolgreich.

## Nicht verifizierte Punkte

Nenne ausstehende E2E-Tests, Plattformen und externe Voraussetzungen.
Eine grüne CI-Anzeige ersetzt keinen echten nativen Release-Smoke-Test.

**Hinweis:** Bei GitHub Actions mit Billing-/Runner-Sperre sind fehlgeschlagene
Jobs kein Beleg für ausgeführte Tests. Erst die Kontosperre beheben.
