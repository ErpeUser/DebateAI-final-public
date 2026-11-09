# Debate AI V6 Windows-Paket

Start: `Backchannel.exe` (historischer Dateiname des Debate-AI-Pakets).

Die editierbaren AI-Dateien liegen im Ordner `ai` direkt neben der EXE. Die
Dateien dort sind die wirksame externe Quelle; sie koennen ohne EXE-Neubau
geaendert werden. Nach einer Aenderung Debate AI beenden und neu starten.

Die unveraenderlichen Programm- und DLL-Dateien liegen unter `_internal`.
Dieser Ordner ist keine Promptquelle. Bei fehlenden lokalen Modellen oder
DLLs meldet die Anwendung den Fehler und wechselt nicht still auf eine
Cloudroute.

Fuer eine installierte Kopie ohne Schreibrechte im Programmordner kann der
Benutzerpfad `%LOCALAPPDATA%\Backchannel\ai` verwendet werden. Die Diagnose-
Anzeige `/api/ai-config` weist den tatsaechlich aktiven Ordner,
Konfigurationsgeneration, Promptversion und Prompt-Hash aus.

Dieses Paket ist ein lokaler Releasekandidat. A06/A18/A21/A22 und echte
Hardware-/DPI-/Rollbackabnahmen bleiben externe manuelle Abnahmen.
