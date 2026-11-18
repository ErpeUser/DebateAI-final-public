# Debate AI Konfiguration

Dieser Ordner ist die zentrale, direkt editierbare KI-Konfiguration.

- `debate_live_v2.txt`: kurzer Qwen-Live-Prompt
- `debate_deep_v1.txt`: kompakter Auftrag fuer die externe Argumentanalyse
- `providers.json`: Reihenfolge der Hintergrundmodelle und Denkstufen
- `playbooks.json`: kurze Sprachbefehle und RhetoricIQ-Steuerungen

Im Windows-Paket werden diese Dateien beim ersten Start nach
`%LOCALAPPDATA%\DebateAI\ai` kopiert. Dort koennen sie ohne neuen EXE-Build
bearbeitet werden. Vorhandene Dateien werden bei Updates nicht ueberschrieben.

Fuer eine portable, beschreibbare Kopie kann vor dem Start
`DEBATEAI_PORTABLE=1` gesetzt werden. Dann wird der Ordner `ai` neben der
tatsaechlich gestarteten EXE (ermittelt ueber `sys.executable`) verwendet; die
gebuendelten `_internal`-/`_MEIPASS`-Dateien bleiben unveraenderliche Defaults.
Die aktive Quelle ist immer die externe Datei. Ein Neustart oder der vorhandene
AI-Konfigurations-Reload liest Aenderungen erneut ein; die laufende EXE muss
nicht neu gebaut werden. Ungueltige JSON-/Promptinhalte werden sicher als
Fallback behandelt und ueberschreiben die Nutzerdatei nicht.
