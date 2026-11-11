# DebateAI: Integrationsnachweis, 11. November 2026

## Tatsaechlich ausgefuehrt

Aktueller Linux-Fokuslauf auf den integrierten Dateien:

| Bereich | Tests | Ergebnis |
|---|---:|---|
| Backend: Kalibrierung, Uploadgrenzen, Abbruch-/Workerbesitz, Cache-Erhalt, eigener Updatekanal | 62 | OK |
| Desktop-Identitaet und datenerhaltende Pfadauswahl | 10 | OK |
| Git-Dateikollisionsschutz und Repository-Rename-Vertrag | 25 | OK |
| JavaScript: Recorder, Blindauswertung und Fallpakete | 20 | OK |
| Chromium: Labor und In-App-Launcher mit expliziten Testfixtures | 24 | OK |
| **Gesamt, keine doppelt gezaehlten Wiederholungen** | **141** | **0 fehlgeschlagen** |

Ausgefuehrte Befehle (jeweils angegebenes Arbeitsverzeichnis):

```text
source/backend: PYTHONPATH=. python -m unittest discover -s tests -v
source/desktop: python -m unittest discover -s tests -v
source: python -m unittest discover -s scripts/tests -v
source/frontend: node --test calibration-tests/core.test.mjs calibration-tests/suite.test.mjs
source/frontend: python -m unittest discover -s calibration-tests -p 'test_*.py' -v
```

**Wichtig:** Die lokale Entwicklungsumgebung enthielt eine nach Git-Blob-Hashes
rekonstruierte TEILKOPIE des Repositorys. Die obigen Discover-Aufrufe erfassten
die darin vorhandenen neuen/fokussierten Tests, nicht die gesamte bestehende
Projekt-Testsuite. Auf einem vollstaendigen Checkout sind die Befehle daher eine
umfangreichere Pruefung. Kein gruener Gesamtprojekt-Build wird behauptet.

Umgebung: Linux, Python 3.13.5, Node 22.16.0, Playwright 1.57.0 und Chromium.
Die eigentliche Windows-Buildkette verlangt weiterhin Python 3.12 und Node 24.
Python-Dateien wurden zusaetzlich syntaktisch geprueft; Workflow-YAML wurde geparst.
Ein YAML-Parse ist kein Nachweis eines ausgefuehrten GitHub-Workflows.

## Was die Tests belegen und was nicht

Die Git-Schutztests verwenden echte temporaere Repositories. Ein Test reproduziert
bewusst, dass Git ignorierte lokale Dateien ohne den Schutz ueberschreiben kann;
der aktualisierte echte Sync-Aufruf stoppt davor und laesst Stash, HEAD und
Nutzdateien unangetastet. Die Repo-Rename-Tests verwenden einen Fake-Command-Runner;
sie benennen kein echtes Repository um und sind kein Nachweis fuer Adminzugriff.

Backend-Routentests nutzen die echten neuen FastAPI-Routen mit kontrollierten
Modell-/DB-/Decoderabhaengigkeiten. Cache- und Legacy-Diagnosetests fuehren die
exakten ausgewaehlten Produktionsfunktionen mit Fakes aus. Kein echtes ONNX-Modell
wurde vermessen. Die UI importiert reale Labor-HTML/CSS/JS-Dateien in einen
Browser-DOM mit expliziten API-, Speicher- und Audiofixtures. Die normale Navigation
und Hardwareaufnahme waren durch die Browserumgebung gesperrt; diese Sperre wurde
nicht umgangen. Eine synthetische Audioquelle ist kein Mikrofon- oder Loopbacktest.

Neue Fehlerregressionen wurden erst rot, dann gruen geprueft, unter anderem:
leeres neues Datenverzeichnis uebergeht gespeicherte Alt-Daten; fehlerhafte eigene
Trust-Konfiguration darf den Appstart nicht abbrechen; unpassende Fallpakete;
Launcher-Lifecycle; Git-Kollision vor Stash; falsche Repository-ID/Privatstatus.

Review: getrennte Selbstpruefungen durch denselben Autor. Es wurden keine mehreren
unabhaengigen Agents gestartet. Dieser Befund darf nicht als Multi-Agent-Review
oder unabhaengiges Sicherheitsaudit ausgegeben werden.

## GitHub und Artefakte

Ausgangs-master: `d07a6581f91944434f691bd1295b39a002b938b5`.
Identitaet/Update-Isolation: `4f72fa0a5a336057ebe7a6a7b6cc8bd8b88bdb7f`.
Integriertes Labor/Testquellen: `da030fafd5c1a76c103e6a07a824c915635e005a`.
Arbeitsbranch: `hardening/debateai-standalone`. Weiterfuehrende getestete Skripte,
CI-Einbindung und dieser Nachweis folgen auf demselben Branch.

Die drei gepatchten Kernquellen wurden am Integrationscommit direkt gegen GitHub
abgeglichen: main.py `67449eb10af3f0689ce926f0b239080948ed2f14`, diagnostics.py
`f483fe90dd5a35950295c658ae363080a0a0c515`, local_transcriber.py
`f279172f5bdc7ec68a08f2019774b2b27de805f9`. Korrekte Labor-JS-Blob-ID:
`90620740f6472c94f1bfff4f9c1ffd2dde949f4b`.

Ein temporaerer privater Source-Snapshot-Workflow konnte keinen Runner starten;
sein Job endete ohne ausgefuehrte Schritte. Er wurde wieder entfernt. Daraus
folgt kein gruener CI-Test und auch kein nachgewiesener Produktfehler.
Den aktuellen PR-Checkstatus vor Merge erneut lesen. Es wurde kein neuer Windows-
Build, kein signiertes Release, kein Installer und kein vorhandener Windows-PC
aktualisiert. Historische Release-Manifeste sind keine neuen Buildnachweise.

## Konkrete offene Arbeit

Repository-Rename tatsaechlich ausfuehren; EXE/Updater/Bundle/Archivvertrag und
restliche sichtbare Namen samt Imports geschlossen migrieren; alte automatisierte
Deployment-/Publikationspfade abtrennen; produktive Antwortpaar-Erzeugung an das
Labor anbinden; vollstaendige Projektgates und native Windows-Build-/Update-/
Rollback-Abnahme. Diese sind teilweise noch INTERNE Entwicklungsarbeiten, nicht
nur externe Kontologin- oder Zertifikatsblocker. Exakte Schritte und alle 15
Runtime-Gates stehen in `DESKTOP_FINAL.md`.
