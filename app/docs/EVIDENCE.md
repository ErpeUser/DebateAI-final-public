# DebateAI — Evidenz- und Freigaberegister

Dieses Dokument unterscheidet reale lokale Prüfungen von nicht ausgeführten Release-, Hardware- und CI-Gates. Detaillierte historische Git-Commits und unabhängige Original-Sicherungen bleiben erhalten; generierte Testprotokolle sind keine Quellcodeabhängigkeit.

## 18. November 2026 — bereinigter Quellbaum

Basis vor der Umstellung: Git-HEAD `e86b799817ea8e64ff54c948ed483636802a75fd` auf `master`. Der aktive Quellcode wurde physisch von `source/` nach `app/` verlegt und vollständig zum Commit vorgemerkt. Das separate Git-Verzeichnis liegt außerhalb des Projektordners; `git fsck --full` bestanden, Refs, Stash und Index beim Umzug abgeglichen.

- Quelle: 1.034 versionierbare Dateien unter `app/`, ohne Node-Installationen, Cache oder Desktop-Runtime; die gesetzlich erforderliche Node-24.21.0-Lizenz wurde aus dem alten Git-Stand wiederhergestellt und mit der offiziellen Quelle abgeglichen.
- Tatsächlich gelöscht: der gesamte alte Report-/Staging-Bereich unter `DebateAI_Generated/reports/` — **15.434 Dateien / 460.449.956 logische Bytes** (15.362 Staging-Dateien und 72 übrige Reportdateien). Vorher wurden 46 abweichende Dateien und alle übrigen Reports in unabhängigen, SHA-256-geprüften ZIPs außerhalb des Repositorys gesichert. Dies ist **keine** Aussage über physisch freigegebene Speicherblöcke.
- Die bislang aktive Native-Runtime mit 9.082 Dateien und unverändertem EXE-Hash wurde während des Build-/Update-Smokes nicht überschrieben. Vor einer lokalen Aktivierung wird sie vollständig außerhalb des Repositories gesichert und ein erneuter Smoke-Test durchgeführt.
- Unabhängiges Quell-ZIP inklusive root/.github-Konfiguration: 1.044 Dateien, pro Datei SHA-256 geprüft. Ältere externe Rückfall-Snapshots und die komplette Git-Historie bleiben unverändert.
- Die Git-Index-Migration erfasst jetzt alle 1.034 `app/`-Dateien. Eine unabhängige Sicht auf den vorbereiteten Git-Tree ergab 1.045 Dateien insgesamt, keine Generated-/Daten-/Secretdateien und vier ausschließlich synthetische Test-Keymuster. `git diff --cached --check` bestand. Die `.gitattributes`-Regeln wurden von `source/` auf `app/` korrigiert, damit der Gemini-Sicherheitspatch und die Node-Lizenz in frischen Checkouts unverändert bleiben. Ein Commit/Push ersetzt nicht die Funktionsprüfung.

## Isolierter Test aus exakt vorgemerkten Git-Quellen

Die Git-Index-Dateien wurden ohne `source/` und ohne `DebateAI_Generated/` als eigenständiger Quellbaum exportiert. Dort wurden `npm ci` für Frontend und Docs-Site erfolgreich ausgeführt. Python-Tests verwendeten eine separate, bereits vorhandene Python-3.12-Testumgebung; zwei lokale ONNX-Modelldateien wurden **nur in die Testkopie** aus der überprüften Windows-Runtime kopiert und per SHA-256 abgeglichen. Das ist **noch kein Nachweis**, dass alle Python-/Native-Abhängigkeiten allein durch externe Downloads frisch installiert wurden.

| Gate | Ergebnis |
|---|---|
| Backend: `python -m pytest -q -p no:cacheprovider tests` | **2.149 bestanden, 18 übersprungen, 376 Untertests bestanden**, 3 Warnungen, nach Fix des Audio-Shutdown-Imports |
| Desktop-Python: `python -m pytest -q -p no:cacheprovider tests` | **265 bestanden, 1 übersprungen, 210 Untertests bestanden**, inklusive Lizenz- und Zeilenenden-Verträge |
| Frontend: `npm test` | **364 bestanden** |
| Frontend: `npm run build` | **Exit 0**, TypeScript/Vite; große Bundle-Chunks bleiben eine Warnung |
| Docs/Worker: `node --test *.test.js` | **212 bestanden** |
| Skript-/Acceptance-Tests: `python -m pytest -q -p no:cacheprovider app/scripts/tests` | **70 bestanden, 2 übersprungen, 20 Untertests bestanden** |
| Signing-Worker: frisches `npm ci`, `npm test` | **29 bestanden** |
| Docs-Site: `npm run build` | **Exit 0**, 24 HTML-Seiten, 23 Docs |
| Git: `git diff --cached --check`, `git fsck --full` | **Exit 0** vor Commit und nach Git-Auslagerung |
| Vulture (Konfidenz ≥90 %) | **0 sichere Treffer** |
| jscpd (Python/JS/TS, 8 Zeilen, 75 Tokens) | **67 Duplikatstellen**, unverändert gegenüber letztem Refactoring |
| Ruff (F-Regeln) | **0 Befunde** nach Behebung des fehlenden `_append_audio_frames`-Imports im Audio-Shutdown. Erweiterter E4/E7/E9/F-Scan: zunächst **221 Befunde**, danach verbleiben 220 stilistische Warnungen (E402/E701/E702/E741); dieser breite Gate wird **nicht** als grün gemeldet. |

Für einen neuen Windows-Releasekandidaten wurden **PyInstaller 6.22.3 und die gepinnten Python-Abhängigkeiten** frisch installiert, PostgreSQL 16.4.0, FFmpeg, CLIProxyAPI/Gemini-Plugin und Node/Oracle anhand fester Versionen bzw. SHA-Werte bezogen und die Gemini-Bridge aus hashgeprüften Go- und Quellarchiven gebaut. Der native **PyInstaller-Build bestand (Exit 0)**, mit dokumentierten Warnungen zu optionalen PostgreSQL-Perl-/Python-Extensions und versteckten Imports.

Der unabhängig gebaute, **nicht signierte** Windows-Releasekandidat wurde tatsächlich getestet:

- `DebateAI.exe`: SHA-256 `95ab3d2d3976817d5fa2ce018e85a8118464c43633ff0db02a68dc6c388292ba` (26.845.643 Bytes). Der komplette Bundlebaum umfasst **16.122 Dateien / 963.270.554 logische Bytes**. Der native Headless-Smoke bestand mit HTTP-Health, lokaler ASR-Readiness, Kalibrierungs-Assets/-Katalog und sauberem Shutdown (Exit 0).
- Frisch gebündeltes Node 24.21.0 und Oracle-CLI 0.22.2: `--help` gegen die tatsächlich gebündelte CLI erfolgreich (Exit 0).
- `DebateAI-windows-x64.zip`: **448.063.405 Bytes**; SHA-256 `c4b457a7a4150de9f962ce0ae92d7d6e7735815223a1d2d7d86c2474f2528595`. Für alle **16.122** Archivdateien wurden Namen, Größe und CRC geprüft.
- `desktop/scripts/smoke_update_archive.py --platform windows-x64 --archive …`: **„OK: native windows-x64 update and forced rollback“**; positiver gestufter Austausch und absichtlich ausgelöster Rückfall in isolierter Umgebung. Es wurde **keine** aktuelle Benutzerinstallation überschrieben.
- **Authenticode-Status:** `NotSigned` (alte und neue EXE). Reale Audiohardware, Provider-Logins, öffentliche Update-Veröffentlichung, grafische GUI-/DPI-Abnahme und Produktionsfreigabe sind nicht bestätigt.

**Security-Paket-Audit:** Bei `npm audit --omit=dev --audit-level=high` im frisch installierten Quellbaum wurden **0 hohe Befunde** für Frontend und Signing-Worker, jedoch **11 hohe Befunde** für Docs-Site und **4 hohe Befunde** für die optionale ChatGPT-Oracle-Runtime gemeldet (u. a. transitive Astro-/Glob-Abhängigkeiten). Die Zahl bezeichnet betroffene Abhängigkeitspakete aus `npm audit`, nicht bestätigte Ausnutzungen. Die Lockfiles werden nicht blind auf potenziell inkompatible Major-Versionen geändert. Diese Security-Gates **bleiben offen**; `.github/workflows/security.yml` enthält explizite Audit-Jobs, die bei weiterhin vorhandenen Befunden rot werden. Kein Sicherheits- oder Release-Pass ohne deren Behebung.

## GitHub und CI

Am 18. November 2026 stimmte der öffentliche Remote-Ref-Abruf des **privaten** Repositorys `ErpeUser/DebateAI` für `origin/master` mit `e86b7998` überein. Es gab nur den Branch `master` und keine offenen PRs. Die aktuellsten GitHub-Actions-Runs vom 17. November 2026 meldeten `failure` für Tests und Security; für die geprüften Jobs kamen **keine ausführbaren Steps** zurück. Ein angezeigtes Workflow-`success` ist daher kein Beleg für durchgeführte Strukturtests. Lokale Tests sind unabhängig von GitHub-CI.

## Historie und Provenienz

Ältere Aufräumschritte sind durch die Git-Commits `946144b4` (historische Baseline) und `a9012b3a` (früherer Cleanup) dokumentiert. Bisherige Forschung, Quell-Provenienz, Privacy-Audits und ältere Release-/Snapshot-Manifeste sind historische Belege und keine aktuelle Build-Freigabe. Nur gezielt identifizierte, eindeutig reproduzierbare Dateien dürfen endgültig entfernt werden. API-Schlüssel, lokale Sessions, PostgreSQL- und Anwendungsdaten unter `%LOCALAPPDATA%/DebateAI` sind keine generierbaren Caches.
