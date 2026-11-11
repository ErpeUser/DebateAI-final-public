# DebateAI - Wiederherstellungs- und Migrationsvertrag

Stand 2026-11-11. Der fruehere ZIP-Overlay-Weg wird durch direkte Git-Integration ersetzt. Kein apply_package.py und keine alte final_sync_safety.py ueber den neueren integrierten Source kopieren. Der aktuelle single-file sync_final_workspace.py enthaelt seinen Kollisionsschutz bereits vor Stash/Merge/Rebase.

## Sichere Programmaktualisierung

Die alte funktionierende Installation bleibt erhalten, bis neues Archiv und Staging vollstaendig verifiziert sind. Staging auf demselben Dateisystem wie das Installationsziel anlegen, vorhandene validierende Archive-/Updaterfunktion nutzen, nur Programmdateien tauschen. Aktive Aufnahme/Verarbeitung abwarten und eigene Prozesse sauber beenden. Keine pauschalen Remove-Item- oder git-clean-Befehle. Bei Fehler vor Tausch bleibt alte Version unangetastet; bei Startfehler nach Tausch alte Binaerdateien zuruecksetzen. Den Health-Nachweis an die neue Instanz binden, nicht irgendein bereits laufendes Backend als Erfolg akzeptieren.

## Daten sind ein eigener Rueckweg

%LOCALAPPDATA%\Backchannel und %LOCALAPPDATA%\DebateAI, PostgreSQL, master.key/DPAPI, AI-Prompts/Playbooks, Browserprofile, API-/OAuth-Sessions, Transkripte und Modelle niemals loeschen. Eine laufende DB-Dateikopie ist kein konsistenter Backup. Vor Schemaaenderung den vorhandenen kontrollierten Backupweg oder gestoppte DB nutzen und Wiederherstellbarkeit pruefen. Binaerrollback ist kein Schemarollback. Zwei verschiedene Programmversionen duerfen nicht parallel denselben Datenbestand benutzen. Kein automatisches Verschmelzen zweier nichtleerer Datenordner.

## Konfiguration und Produktidentitaet

Neue Defaults, bisherige Baseline und aktive Benutzerkopie semantisch zusammenfuehren. Ein EXE-Update ersetzt absichtlich keine angepassten Prompts. Aktiven Pfad/Generation/Profile/Trigger via Anwendung pruefen. Exe-/Updater-/Archivnamen erst als zusammenhaengenden Vertrag migrieren; historische Lizenz-/Herkunftshinweise bleiben.

## Testlabor und Grenzen

Laborassets und Navigation sind integriert. Der Produktions-Paarbenchmark benchmark_blind_pair.py ist implementiert, benoetigt aber die Source-Projektumgebung und ein bewusst beendetes Desktopprogramm. Er ist kein neuer Installer oder in die EXE eingebauter Generierungsbutton. Fehler, Timeouts und unbewertete Skalen bleiben ehrlich. Ein synthetischer Browsertest oder Headless-Replay ist keine deutsche Hardware-/Sprachabnahme.

Exakte nativen Schritte stehen in DESKTOP_FINAL.md. Signierter Release nur mit realem Zertifikat, unabhaengigem Kanal und erfolgreichem Protokoll; keine erfundene Freigabe.
