# GitHub Repository: Ordnerstruktur, Automatisierung und Sicherheit

Stand: 18.11.2026. Dieses Dokument unterscheidet **auf GitHub aktivierte**
Einstellungen von **vorbereiteten** Checks, die erst nach einer erfolgreichen
Veröffentlichung auf einem Branch laufen.

## Kanonische Projektstruktur

- `/.github/workflows/`: GitHub Actions für Tests, Struktur, Sicherheit,
  Website und manuell ausgelöste Desktop-Releases. Der Unterordner
  `app/.github/release-notes/` ist **versionierte Produktinformation**,
  kein GitHub-Workflow-Ort.
- `/app/`: sämtliche Programmquellen und Build-Eingaben; insbesondere
  `backend/`, `frontend/`, `desktop/`, `site/`, `docs-site/`,
  `scripts/`, `ai/`, `docs/` und `release-signing-worker/`.
- `/Start-DebateAI.*`: versionierter Windows-Start-/Recovery-Einstieg.
- `/runtime/`: lauffähige, lokal installierte PyInstaller-`onedir`-Runtime
  inklusive `_internal`. In Git **ignoriert**, niemals als Quelle behandeln.
- `/DebateAI_Generated/`: beliebig neu erzeugbare Build-/Dependency-Caches,
  Downloads und Reports. In Git **ignoriert**, niemals zwingende Quelle.
- `/.git/`: internes Git-Verzeichnis des Checkouts. Ein alter Pointer-Checkout
  kann während der Migration gelesen werden, gehört aber nicht zum finalen
  öffentlichen Baum.
- `%LOCALAPPDATA%/DebateAI`: private lokale Datenbanken, Sessions und
  Einstellungen; vollständig außerhalb von Git.

Eine automatische Pfadprüfung liegt unter
`app/scripts/verify_repository_layout.py`. Sie prüft die aktuelle Git-Index-
und Arbeitskopie auf verpflichtende Quelldateien, gültige Root-Verzeichnisse,
Groß-/Kleinschreibungskollisionen, irrtümlich versionierte Laufzeitdateien,
Geheimnisse und Datenbanken. Fehlende versionierte Dateien und unerwartete
Root-Verzeichnisse sind Fehler, keine Warnungen. Die Prüfung lädt nichts
herunter und fasst die Runtime nicht an.

## GitHub Actions / Repository-Regeln

- **Structure → repository-layout:** regulärer, blockierender Job für
  Pull Requests und Pushes auf `master` und `main`. Führt die Pfadprüfung, den
  `--source-only`-Checkouttest und Regressionstests aus.
- **Structure → sentrux:** zusätzlicher, weiterhin **beratender** Job
  (`continue-on-error`), weil die historische Metrik-Baseline Altlasten
  enthält. Er ist kein Ersatz für die blockierende Pfadprüfung.
- **tests:** getrennte Backend-, Frontend-, Browser- und Windows-
  Starter-/Buildvertragstests.
- **security:** Python/Pip-, npm- und weitere festgelegte Audits.
- **docs-site-build:** validiert `app/site` plus `app/docs-site`;
  kein unkontrolliertes Live-Deployment.
- **Desktop release:** weiterhin `workflow_dispatch` mit explizitem Tag,
  Commit und Plattformen. Keine automatische Veröffentlichung bei Push.
- `/.github/CODEOWNERS`: echte Pfade im `app/`-Monorepo sowie Root-
  Guardrails; beantragt Owner-Review für relevante Änderungen.
- `/.github/PULL_REQUEST_TEMPLATE.md`: Checkliste für Struktur, Schutz
  privater Daten, Signaturen, Tests und offene E2E-Grenzen.
- `/.github/dependabot.yml`: dokumentierte Update-Ziele für Actions, Python-
  Anforderungen und die getrennten npm-Lockfile-Verzeichnisse. Automatische
  Version-Update-PRs bleiben im öffentlichen Mirror deaktiviert, damit keine
  Dependabot-Branchflut entsteht. Sicherheitsmeldungen bleiben bei GitHub.

## Verifizierte GitHub-Einstellungen

| Einstellung | Ergebnis |
|---|---|
| Final public mirror | **öffentlich**, Standardbranch `main` |
| Private canonical checkout | **privat**, historischer Standardbranch `master` |
| Workflow-Berechtigungen | `read`; Workflows dürfen PR-Reviews nicht automatisch genehmigen |
| Actions-Quelle | Aktiviert; **vollständige Commit-SHA-Pins für Actions erforderlich** |
| Dependabot-Warnungen | aktiviert |
| Automatische Dependabot-Sicherheitsupdates | aktiviert (PRs, kein Auto-Merge) |
| Nach Merge aufgeräumte PR-Branches | aktiviert |
| PR-Branches aktualisierbar | aktiviert |
| Automatisches Merge | bleibt deaktiviert |
| Branch-Protection/Rulesets | **nicht verfügbar**: API HTTP 403, GitHub Pro oder öffentliches Repository erforderlich |

**GitHub-Plan-Grenze:** Die privaten und öffentlichen Repositorys können mit dem aktuellen
Tarif keine serverseitig erzwungene `master`- oder `main`-Branch-Protection über REST
nutzen. Die CI-Prüfungen **scheitern sichtbar**, wenn Regeln gebrochen
werden, können aber ohne Branch-Protection einen berechtigten direkten Push
nicht grundsätzlich verhindern. Das Repository wird zur Behebung **nicht
öffentlich gestellt**. Bei einem späteren Upgrade sollten die erforderlichen
Statuschecks `Repository layout and tracked-file hygiene`, `backend`,
`frontend` und `security` erst nach nachgewiesenen grünen Runs als
Required Checks konfiguriert werden.

**Aktuelle Konto-/Runner-Sperre (18.11.2026):** GitHub Actions startete die
letzten Jobs gar nicht. GitHub meldet: `The job was not started because
recent account payments have failed or your spending limit needs to be
increased.` Das lässt sich nicht durch YAML beheben. Unter
**GitHub → Settings → Billing & licensing** die Zahlungen und das
Actions-Budget prüfen. Erst danach laufen Hosted CI und Release-Jobs
tatsächlich. Diese Einschränkung berührt nicht den lokalen Windows-Start.

## Gitignore, Quellen und sichere Veröffentlichung

`.gitignore` ignoriert Runtime, Generated, Paketinstallationen,
Python-/Node-Caches, `.env`-Varianten, lokale Datenbankdateien und
Schlüsselcontainer. Die öffentlichen `app/desktop/release_signing_keys.json`,
beide Quell-Websites, `.env.example`, Lockfiles und versionierte Skripte
bleiben im Git-Index. `.gitignore` entfernt **niemals** bereits versionierte
Dateien; existierende Secrets in Git müssen gesondert gesperrt und ihre
Schlüssel ersetzt werden. Im geprüften aktuellen Git-Index fanden sich
keine solchen Dateien.

Vor einem PR oder Merge:

```powershell
py -3.12 app/scripts/verify_repository_layout.py
py -3.12 app/scripts/workspace_refs.py --source-only --strict
py -3.12 -m unittest discover -s app/scripts/tests -p test_repository_layout.py -v
py -3.12 -m unittest discover -s app/scripts/tests -p 'test_*.py' -q
git diff --check
```

Beim Aufnehmen von Änderungen nicht `git add -f` auf ignorierte Ordner
anwenden. GitHub- und lokale Versionen über Pull Requests vergleichen.
Keine Git-Historie, Backups, Datenbank oder laufende EXE bei CI-Reparaturen
löschen. Ein Release erfordert weiterhin die eigene signierte
Multi-Plattform-Release-Abnahme.
