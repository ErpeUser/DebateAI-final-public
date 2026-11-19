# DebateAI – aktuelle offene Punkte

Stand: **19. November 2026**. Der [Evidenznachweis](EVIDENCE.md) unterscheidet lokal bestandene Tests, neu gebaute Artefakte und noch offene externe Freigaben. Frühere Statusstände und die damaligen `source/`-Pfade sind ausschließlich historische Belege im gesicherten Git-Verlauf, **keine aktuelle Handlungsanleitung**.

## Bereits lokal nachgewiesen

- Kanonischer Quellbaum unter `app/`; bisherige historische `source/`-Pfade im Git-Index entfernt. Git-Metadaten extern ausgelagert, vollständige Integritätsprüfung bestanden.
- Unnötige generierte Report- und Stagingkopien gelöscht, Modelle und Benutzer-/DB-Daten geschützt.
- Neuer, gepinnter Windows-Quellaufbau mit PyInstaller, PostgreSQL, FFmpeg, CLIProxyAPI, Node/Oracle und aus verifizierten Quellen gebauter Gemini-Bridge durchgeführt; native EXE ist erfolgreich gestartet und wurde mit Health, ASR, Lab-Assets und sauberem Shutdown geprüft.
- Vollständige automatische Tests: Backend **2.149 bestanden / 18 übersprungen**, Desktop **265 / 1 übersprungen**, Frontend **364 bestanden**, Docs/Worker **212 bestanden**, Skripte **70 / 2 übersprungen**, Signing-Worker **29 bestanden**; Frontend- und Docs-Build erfolgreich.
- Windows-Releasekandidat: neuer Headless-EXE-Smoke, Oracle-CLI und isolierter Update-/Forced-Rollback-Smoke bestanden; 16.122 ZIP-Mitglieder geprüft, SHA-256 im [Evidenzregister](EVIDENCE.md). Die 16.122 Dateien wurden erneut hashverifiziert in den aktiven Programmordner übernommen; **erneuter Headless-Smoke direkt aus der aktiven Runtime bestanden**. Der alte Programmordner bleibt außerhalb des Repositories als vollständiger Rückfall erhalten. Authenticode weiterhin `NotSigned`.
- Die zuletzt gefundenen F821-/F401-Fehler wurden behoben; die breiteren Stilwarnungen und Duplikatstellen sind nicht vollständig beseitigt.
- Die lokalen Workflow-/Testregressionen sind behoben: Die private V3-Matrix wird bei fehlender autorisierter Evidence sauber übersprungen (im veröffentlichten Remediation-Commit), der Calibration-Browser nutzt einen Playwright-kompatiblen Ubuntu-Runner und der Windows-Startvertrag beendet erfolgreiche Prüfungen mit Exit 0. Die GitHub-CI bleibt für den neuen HEAD unbestätigt, solange der Run-/Statusdienst keinen frischen Lauf liefert.
- Frische lokale `npm audit --audit-level=high`-Prüfungen für Docs-Site, Oracle und Frontend melden **0 High/Critical Findings**; die früheren 11/4-Befunde sind für den aktuellen Lockfile-Stand nicht reproduzierbar.
- Layout- und Source-only-Gates sind im öffentlichen Checkout erfolgreich: `verify_repository_layout.py` und `workspace_refs.py --source-only --strict`.

## Noch nachzuweisen oder abzuschließen

1. **GitHub Actions:** Die Workflows enthalten jetzt ausführbare Schritte und die bekannten öffentlichen Regressionen sind korrigiert. Für den neuen Commit bleibt ein frischer grüner GitHub-Run ausstehend, weil der aktuelle Connector für den neuen SHA noch keine Workflow-Evidenz liefert. Ein leerer Run-/Statusdatensatz wird nicht als bestanden gewertet.
2. **Produktrealität (BLOCKED/external):** Windows-GUI mit Fokus/DPI, echtes Mikrofon/WASAPI/Systemaudio, lange parallele Live-Sessions und echte Provider-Logins inklusive Privacy-First und nutzerautorisierter Kosten separat abnehmen. Automatische Lab- und Unit-Tests ersetzen diese Prüfungen nicht.
3. **Releasefreigabe (BLOCKED/external):** Authenticode-Signatur mit gültiger Herausgeberidentität, Produkt-/R2-Updateveröffentlichung und Freigabe fehlen. Nicht heimlich mit Testschlüsseln publizieren.
4. **Security-Abhängigkeiten:** Der aktuelle Lockfile-Stand ist lokal sauber: Docs-Site, Oracle und Frontend melden bei `npm audit --audit-level=high` jeweils **0 High/Critical Findings**. Nach dem nächsten aktivierten CI-Run erneut gegen denselben Commit prüfen.
5. **Weitere Codequalität:** 67 jscpd-Duplikatstellen (großteils Tests), 220 breite Ruff-Stilwarnungen sowie große LLM-/Audio-/Orchestrator-Funktionen gezielt und regressionsgesichert behandeln. Keine riskante Massentransformation bei laufender Releaseabnahme.

## Verbindlicher Ablauf für zukünftige Arbeit

Quellcode, Tests, Lockfiles und gesetzlich erforderliche Lizenzen bleiben in `app/`; installierte Laufzeiten und regenerierbare Artefakte gehören nach `DebateAI_Generated/` oder in einen isolierten Buildbereich. Vor jeder Löschung tatsächliche Referenzen und Wiederherstellbarkeit prüfen. Keine privaten Benutzerdaten, externen Secrets, Git-Historie oder optionalen Modellpfade blind entfernen.

Aktuelle Kommandos und Releasebedingungen stehen in [releasing.md](releasing.md); dieser Status ersetzt die älteren Windows-/Codex-Aufträge ausdrücklich.
