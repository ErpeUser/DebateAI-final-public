# DebateAI - Ziel-Ordnerbaum und Verbesserungsanalyse

**Umsetzungsstand:** Signierter Release-Download mit Ed25519/SHA-256-Prüfung,
Rollback-Installation, einheitliche lokale Release-Build-Ausgaben unter
DebateAI_Generated, Fachmodul-Fassaden und Windows-CI-Gates wurden implementiert.
Ausstehend bleiben ein echter Test des produktiven Download-Endpunkts sowie
die schrittweise Verlagerung der Backend-Implementierungen (bisher nur stabile
Fachmodul-Interfaces). npm-Modulordner bleiben aus Kompatibilitätsgründen lokal.

Stand: 18.11.2026. Diese Datei ist ein Architekturvorschlag, KEINE ausgefuehrte Migration.
Die automatisch erhobene IST-Struktur steht in ORDNERBAUM_AKTUELL.md.

## Ziel: mit oder ohne Generated startfaehig

```text
Coding/
|-- DebateAI/
|   |-- .git/                      (internes Git-Metadatenverzeichnis)
|   |-- .github/workflows/         (versionierte CI, bleibt an dieser Stelle)
|   |-- .gitignore
|   |-- .gitattributes
|   |-- README.md
|   |-- AGENTS.md
|   |-- Start-DebateAI.cmd
|   |-- Start-DebateAI.ps1         (starten / bei Bedarf wiederherstellen)
|   |
|   |-- app/                        (kanonischer, versionierter Quellcode)
|   |   |-- backend/
|   |   |   |-- app/
|   |   |   |   |-- main.py
|   |   |   |   |-- routers/
|   |   |   |   |-- ws/
|   |   |   |   `-- services/       (VORSCHLAG: in Fachmodule aufteilen)
|   |   |   |       |-- audio/
|   |   |   |       |-- transcription/
|   |   |   |       |-- speakers/
|   |   |   |       |-- agents/
|   |   |   |       |-- knowledge/
|   |   |   |       |-- privacy/
|   |   |   |       |-- updates/
|   |   |   |       `-- shared/
|   |   |   |-- alembic/
|   |   |   |-- fixtures/
|   |   |   `-- tests/
|   |   |-- frontend/
|   |   |   |-- src/
|   |   |   |   |-- components/{PreCall,ActiveCall,PostCall,shared}/
|   |   |   |   |-- hooks/
|   |   |   |   `-- services/
|   |   |   |-- public/
|   |   |   `-- package.json + package-lock.json
|   |   |-- desktop/                (Launcher, Updater, PyInstaller-Spezifikation)
|   |   |-- ai/                     (Prompts und versionierte Defaults)
|   |   |-- site/                   (statische Startseite/Marketing - QUELLE)
|   |   |-- docs-site/              (Astro + Assembly - NICHT mit site/ vermischen)
|   |   |-- release-signing-worker/
|   |   |-- .ai/                    (bestehende Projektunterlagen)
|   |   |-- .github/release-notes/  (bestehende Versionshistorie)
|   |   |-- .sentrux/               (versionierte Strukturregeln)
|   |   |-- docs/                   (Kanonische Doku, API, Kontrakte, Audit)
|   |   |-- scripts/                (bestehende Build-/Pruefpfade beibehalten)
|   |   `-- tools/                  (versionierte Migrationstools)
|   |
|   |-- runtime/
|   |   `-- DebateAI/
|   |       |-- DebateAI.exe
|   |       |-- DebateAIUpdater.exe
|   |       `-- _internal/          (vollstaendiges, unveraendertes onedir-Bundle)
|   |
|   `-- DebateAI_Generated/        (OPTIONAL, vom Build automatisch anlegbar)
|       |-- dependencies/          (Python-venv, spaeter optional npm-Cache)
|       |-- build/                 (Artefakte, Stage und PyInstaller-Work)
|       |-- downloads/             (verifizierte temporaere Downloads)
|       |-- cache/
|       |-- logs/
|       |-- reports/
|       `-- tmp/
|

Benutzerdaten bleiben EXTERN: %LOCALAPPDATA%/DebateAI/ (niemals Generated).
```

## Analyse: direkt am Rechner bestaetigt

- Versioniert sind 1.045 Git-Dateien; app/ hat zum Auditzeitpunkt rund 1.064 Dateien und 14,6 MiB.
- Die vorhandene Windows-Runtime hat 16.122 Dateien mit rund 918,6 MiB.
- DebateAI_Generated ist zum Zeitpunkt des Audits nicht vorhanden.
- Root-.git ist ein relativer Verweis auf das externe Schwesterverzeichnis; Git-Befehle funktionieren.
- app/backend/app/services hat 103 direkte Python-Dateien. Diese hohe flache Zahl erschwert Navigation und klare Verantwortlichkeiten.
- app/frontend/src/components umfasst 93 Dateien; PreCall, ActiveCall und PostCall existieren bereits als Domänengruppen.
- app/docs-site/assemble.mjs kopiert app/site/ und die gebauten Astro-Docs gemeinsam nach dist-site/. Das ist ein dokumentierter Buildfluss, keine nachgewiesene Dublette.
- app/scripts/build_debate_assistant.ps1 nutzt bereits ein Generated-Release-venv, aber weitere Outputs liegen nach wie vor in app/build und app/dist.
- npm ci legt node_modules weiterhin in den jeweiligen Paketordnern an; fuer eine Verlagerung in Generated muss der Buildprozess zuerst angepasst und getestet werden.
- Start-DebateAI.ps1 kann bei fehlender Runtime einen Quell-Build versuchen, ist aber KEIN vollstaendig getesteter One-Click-Download-Installer.
- Einige vorangegangene Aenderungen und diese neuen Dokumente sind lokal nicht committed. Kein Push wurde ausgefuehrt.

## Priorisierte Verbesserungsvorschlaege (nicht automatisch umgesetzt)

**P0 - Wiederherstellung der Runtime vereinfachen.** Bei fehlendem Bundle sollte der Starter vorzugsweise
ein veroeffentlichtes, signiertes und per Manifest/Hash verifiziertes Windows-Release atomar laden,
smoke-testen und erst danach aktivieren. Ein kompletter PyInstaller-Neubau sollte ein separater
Entwickler-Fallback sein. So braucht der normale Nutzer fuer eine Neuinstallation kein Python/npm.

**P0 - Build-Ausgaben eindeutig routen.** Ein versioniertes Pfadmodul (z.B. app/scripts/build_paths.py)
soll Build-Artefakte, Caches, temporaere Downloads und Python-venv getrennt zuweisen. Parallel
app/scripts/build_debate_assistant.ps1, app/scripts/release_desktop.ps1 und die CI-Pfade
angleichen, damit keine unerklaerten app/build- oder app/dist-Reste bleiben. Erst nach Tests migrieren.

**P1 - Backend-Services modularisieren.** Die 103 flachen Dateien schrittweise in fachliche Pakete
aufteilen, Imports per Kompatibilitaets-Reexports absichern, dann Backend-/Release-Tests laufen lassen.
Nicht per Dateinamen allein automatisch verschieben.

**P1 - npm-Abhaengigkeiten sauber isolieren.** npm ci und package-lock.json weiter verwenden;
Node-Paketordner erst nach verifiziertem Pfadvertrag oder einer kontrollierten Junction-Strategie
in Generated auslagern. Standard-npm erwartet installierte node_modules im Paketkontext.

**P1 - Loeschbarkeit als CI-Vertrag testen.** In einem isolierten Test Generated entfernen,
Git-Aufloesung, Quellpfade und Runtime-Start pruefen; zusaetzlich corrupt-download, Offline- und
Rollback-Faelle testen. Echten Release-Download und Quell-Neubau separat als E2E-Gates nachweisen.

**P2 - Dokumentation konsolidieren statt verschieben.** app/docs ist kanonischer Dokumentationsinhalt;
app/docs-site baut daraus die Astro-Seite; app/site ist Marketing-/Landingpage-Quellmaterial.
Verweise und Build-Kette dokumentieren, nicht unbedacht zusammenfuehren.

**P2 - Git-Portabilitaet und Cleanup.** Relative .git-Verknuepfung unterstuetzen, aber neue
normale Git-Clones (bei denen .git ein Verzeichnis sein kann) ebenso akzeptieren. Cleanup
nur anhand einer Whitelist und nie in laufende Anwendungen oder private Daten hinein.

## Unbedingt behalten

- runtime/DebateAI/_internal/ als ganzes onedir-Bundle, nicht nach Dateidubletten ausduennen.
- app/ai/ Prompts und app/desktop/ Build-/Update-Spezifikationen.
- .github/workflows/ und das interne `.git/` ausserhalb Generated.
- %LOCALAPPDATA%/DebateAI/ mit Datenbanken, Sitzungen und persoenlichen Einstellungen.

## Nachpruefen

```powershell
py -3.12 app/scripts/export_project_tree.py --depth 4 --limit 12 --output app/docs/ORDNERBAUM_AKTUELL.md
py -3.12 app/scripts/workspace_refs.py --strict
powershell -NoProfile -ExecutionPolicy Bypass -File ./Start-DebateAI.ps1 -Check
git status --short
```

Die echte, vollstaendige Bootstrap-Rebuild-Strecke (ohne bestehende Runtime)
wurde bei dieser Strukturanalyse NICHT ausgefuehrt. Keine Daten wurden geloescht oder verschoben.
