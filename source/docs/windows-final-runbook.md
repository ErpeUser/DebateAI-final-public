# Debate AI – finaler Windows-Ablauf

Dieses Runbook beschreibt den tatsächlich unterstützten End-to-End-Ablauf der
Windows-Version. Es gilt für das gebaute Verzeichnis
Backchannel-windows-x64.zip und für einen lokalen Build aus dem Repository.

## 0. Codex: lokalen Stand und Playbooks final synchronisieren

**Vor dem Build im vorhandenen Windows-Checkout** den neuesten `origin/master`
holen und die Anweisungen in `AGENTS.md` aus dem Repository-Stamm
ausfuehren. Ein neuer temporaerer Checkout allein ist kein Endergebnis.
Codex entscheidet eigenstaendig: ueberholten lokalen Source-Code ersetzen,
kompatible einzigartige Verbesserungen aus lokalen Commits/Arbeitskopien
uebernehmen, Konflikte aufloesen und dann den tatsaechlich verwendeten
Windows-Ordner auf den aktuellen Commit bringen.

**Das rhetorische Playbook gehoert zur Finalversion:** `ai/playbooks.json`
und `ai/defaults/playbooks.json` liefern die Strategien; Profile und
Ausloeser werden in `backend/app/services/debate_settings.py` und
`backend/app/services/agents/orchestrator.py` verarbeitet.
Benutzeranpassungen koennen im Laufzeitverzeichnis
`%LOCALAPPDATA%\Backchannel\ai\playbooks.json` liegen.
Codex vergleicht bei Bedarf die ausgelieferte Version mit dem bisher aktiven
Playbook und dessen Basisversion, sichert Benutzeranpassungen und fuehrt
echte neue Strategien sinnvoll zusammen. Veraltete Widersprueche werden nicht
zurueckkopiert; persoenliche Strategien und gespeicherte Versionen werden
nicht geloescht. Die Anwendung besitzt bereits ein Drei-Wege-Verfahren,
das geaenderte Benutzerdateien standardmaessig beibehält – deshalb reicht
ein neuer Git-Checkout alleine **nicht** als Playbook-Migration.

Nach dem Windows-Build kontrollieren, dass das ZIP die aktuellen Playbooks
und Prompts enthaelt und dass `/api/ai-config` den beabsichtigten aktiven
Konfigurationspfad, die Promptversion und die Konfigurationsgeneration zeigt.
Debattenprofile und zumindest die Playbook-Ausloeser Gegenfrage,
Beweislast und Widerlegung pruefen. Wenn ein Schritt mangels Windows-Rechten
oder laufender Anmeldung nicht moeglich ist, das konkret melden – keinen
fertigen Windows-Betrieb behaupten.

## 1. Voraussetzungen

- Windows 10 oder 11, 64 Bit.
- Microsoft Edge WebView2 Runtime. Sie ist auf aktuellen Windows-Installationen
  normalerweise vorhanden. Fehlt sie, muss sie vor dem Start installiert werden.
- Ein Mikrofon und eine zulässige Windows-Systemaudioquelle für die Gegenseite.
  Windows muss für Desktop-Apps den Mikrofonzugriff und die verwendete
  Loopback-/Systemaudioquelle erlauben.
- Für den schnellsten lokalen Sofortpfad: Ollama und das Modell qwen3:4b.
  Cloud-Provider sind dafür nicht erforderlich.
- Für ChatGPT Web: ein installierter Chrome- oder Edge-Browser und ein gültiges
  ChatGPT-Konto.
- Für Gemini Web: ein gültiges Google-Konto. Die Anmeldung läuft in einem
  isolierten WebView2-Fenster.
- Für externe API-Modelle: der jeweilige API-Key. Keys werden in der Anwendung
  unter **Admin → Verbindungen** gespeichert, verschlüsselt auf dem Gerät
  abgelegt und nach einem Neustart wieder verwendet.

Die Anwendung braucht für das normale Desktop-Bundle kein Docker und keine
separate PostgreSQL-Installation. Das Bundle bringt die benötigten lokalen
Laufzeitkomponenten einschließlich PostgreSQL und ffmpeg mit.

## 2. Fertiges Bundle installieren

PowerShell:

~~~powershell
$ErrorActionPreference = "Stop"

$zip = Join-Path $env:USERPROFILE "Downloads\Backchannel-windows-x64.zip"
$installRoot = Join-Path $env:LOCALAPPDATA "Programs\DebateAI"
$bundleRoot = Join-Path $installRoot "Backchannel"

if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) {
    throw "ZIP-Datei nicht gefunden: $zip"
}

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
if (Test-Path -LiteralPath $bundleRoot) {
    # Vor dem Ersetzen die Anwendung beenden. Daten liegen separat unter
    # %LOCALAPPDATA%\Backchannel und werden hier nicht gelöscht.
    Remove-Item -LiteralPath $bundleRoot -Recurse -Force
}
Expand-Archive -LiteralPath $zip -DestinationPath $installRoot -Force

$exe = Join-Path $bundleRoot "Backchannel.exe"
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Backchannel.exe fehlt im entpackten Bundle: $exe"
}

Start-Process -FilePath $exe -WorkingDirectory $bundleRoot
~~~

Die Anwendung startet Backend, eingebettete Datenbank, Tray und das Desktopfenster
selbst. Der Start wird ohne sichtbare CMD-Fenster ausgeführt. Die persistenten
Daten liegen in:

~~~text
%LOCALAPPDATA%\Backchannel
~~~

Diese Daten enthalten Einstellungen, verschlüsselte Zugangsdaten,
Transkript-/Debattendaten und Updatezustand. Bei einer Neuinstallation darf
dieses Verzeichnis erhalten bleiben.

## 3. Lokalen Sofortpfad aktivieren

Die EXE startet Ollama, wenn es bereits installiert ist, installiert aber keine
Software ohne ausdrückliche Windows-Aktion. Einmalige Einrichtung:

~~~powershell
$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    winget install Ollama.Ollama --exact `
        --accept-package-agreements `
        --accept-source-agreements `
        --silent `
        --disable-interactivity
}

$ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollama) {
    $ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
}
if (-not (Test-Path -LiteralPath $ollama -PathType Leaf)) {
    throw "ollama.exe wurde nach der Installation nicht gefunden."
}

try {
    Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3 | Out-Null
} catch {
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    do {
        Start-Sleep -Seconds 2
        try {
            Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3 | Out-Null
            $ready = $true
        } catch {
            $ready = $false
        }
    } until ($ready)
}

& $ollama pull qwen3:4b
if ($LASTEXITCODE -ne 0) {
    throw "qwen3:4b konnte nicht geladen werden."
}
~~~

Danach in **Admin → KI/Modelle** den lokalen deutschen Debattenpfad
auswählen. Der Desktop-Launcher wärmt qwen3:4b beim Start vor. Wenn Ollama
nicht verfügbar ist, bleibt die Anwendung benutzbar; ein konfigurierter
Cloud- oder OpenAI-kompatibler Fallback kann übernehmen.

## 4. Zugangsdaten und Provider

### API-Keys

1. Anwendung öffnen.
2. **Admin → Verbindungen** öffnen.
3. Provider auswählen und den Key eintragen.
4. Verbindung testen und speichern.
5. Unter **Admin → KI/Modelle** das Modell dem Debattenpfad oder einem
   Hintergrundagenten zuweisen.

Der Key wird nicht in den Projektordner, nicht in das Bundle und nicht in Logs
geschrieben. Unter Windows schützt der Launcher den Daten-Schlüssel mit DPAPI.
Derselbe Windows-Benutzer kann die gespeicherten Keys nach Neustarts direkt
weiterverwenden. Beim Umzug auf einen anderen Rechner oder Benutzer müssen sie
erneut eingegeben werden.

### ChatGPT Web

Im finalen Windows-Build werden die gelockte ChatGPT-Web-Runtime, der portable
Node-Runner und das Oracle-Paket in das Bundle aufgenommen.

1. In **Admin → Verbindungen** den Eintrag **ChatGPT Web** öffnen.
2. **Anmelden** wählen.
3. Im sichtbaren Chrome-/Edge-Fenster anmelden.
4. Das Fenster erst schließen, wenn die Anwendung Modell und
   **Extra High** als verifiziert meldet.
5. Unter **Admin → KI/Modelle** den ChatGPT-Web-Pfad nur für die
   Hintergrundanalyse aktivieren. Der lokale Sofortpfad bleibt davon unabhängig.

Wenn die Web-Sitzung abläuft, denselben Anmeldevorgang erneut ausführen. Die
Anwendung verwendet ein eigenes Browserprofil unter
%LOCALAPPDATA%\Backchannel\chatgpt-web; das persönliche Standardprofil wird
nicht übernommen.

### Gemini Web

1. **Admin → Verbindungen → Gemini Web → Anmelden** wählen.
2. Im privaten WebView2-Fenster bei Google anmelden.
3. Warten, bis die Anmeldung abgeschlossen ist.
4. Unter **Admin → KI/Modelle** Gemini Web für Recherche oder
   Hintergrundanalyse aktivieren.

Die Cookies werden nur als einmaliger Übergabewert an die lokale Bridge
übergeben und anschließend aus der Übergabedatei gelöscht. Eine abgelaufene
Sitzung wird durch eine erneute Anmeldung ersetzt. Audio und Live-Transkript
werden dadurch nicht automatisch an Gemini gesendet; nur ausdrücklich
aktivierte externe Analyse- oder Recherchepfade erhalten den dafür
freigegebenen Kontext.

## 5. Debattenbetrieb

- Unter **Debatte** genau einen der beiden Modi wählen:
  **Hart** oder **Überzeugen**.
- Mikrofon und Systemaudio getrennt auswählen.
- Vor dem ersten Gespräch den Pegel beider Spuren prüfen.
- **Debatte starten** drücken.
- Das kompakte Overlay zeigt zuerst die strategisch stärkere Option:
  **Sofortantwort** oder **Gegenfrage**. Die zweite Option bleibt als
  Alternativzug sichtbar.
- Das Overlay kann als Always-on-top-Fenster über Discord, Teams oder dem
  Browser liegen. Die ausführliche Argumentstruktur, Quellen und das vollständige
  Transkript bleiben in den Detailansichten.

Die erste brauchbare Antwort kommt aus dem lokalen Kurzpfad. Externe Modelle,
Recherche und vertiefte Gegenstrategien laufen getrennt weiter und ersetzen eine
bereits sprechbare Antwort nur bei einem erkannten Qualitätsgewinn.

## 6. Sauber beenden, Wiederaufnahme und Updates

- Zum Beenden das Tray-Menü **Beenden** verwenden.
- Dadurch werden WebView-Fenster, Ollama-Prozess (nur wenn vom Launcher
  gestartet), Gemini-Bridge, CLIProxyAPI, PostgreSQL-Watchdog und Backend
  kontrolliert beendet.
- Ein unerwartetes Beenden hinterlässt den nächsten Startzustand unter
  %LOCALAPPDATA%\Backchannel\backchannel.log; die Anwendung bereinigt nur
  eigene temporäre Übergabedateien.
- **Tray → Nach Updates suchen** oder **Admin → Über** startet den signierten
  Updatepfad. Aktive Aufnahmen werden abgewartet. Ein fehlgeschlagener Neustart
  löst den vorhandenen Rollback aus.

Für eine manuelle Sicherung vor einem Update:

~~~powershell
$source = Join-Path $env:LOCALAPPDATA "Backchannel"
$backup = Join-Path $env:USERPROFILE ("Desktop\DebateAI-Backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Copy-Item -LiteralPath $source -Destination $backup -Recurse -Force
~~~

## 7. Lokalen Windows-Build erzeugen

Der Build benötigt Python 3.12, Node 24, npm und Internetzugriff für die
gepinnten Modelle und Laufzeitarchive. Er benötigt keine Release-Credentials.

~~~powershell
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PWD "source")

$python312 = py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 ist nicht installiert." }

.\scripts\build_debate_assistant.ps1 `
    -Python $python312 `
    -IncludeOracle
~~~

Der Build führt Frontend-Build, Python-Abhängigkeiten, ONNX-Modelle,
eingebettetes PostgreSQL, ffmpeg, CLIProxyAPI, Gemini-Web-Bridge und die
ChatGPT-Web-Runtime zusammen. Danach laufen der Bundle-Smoke-Test und der
Update-Archiv-Smoke-Test. Das Ergebnis liegt unter:

~~~text
source\dist\Backchannel-DebateAI-windows-x64.zip
~~~

Für den autoritativen, signierten Mehrplattform-Release verwendet der
Koordinator:

~~~powershell
Set-Location (Join-Path $PWD "source")
.\scripts\release_desktop.ps1 -Version vX.Y.Z
~~~

Dieser Pfad erstellt die Windows-Artefakte mit denselben Vorbereitungen und
übergibt sie anschließend an den vorhandenen signierten Veröffentlichungsweg.

## 8. Authenticode vor Produktionsverteilung

Die Update-Metadaten signieren das ZIP und schützen die Updatekette. Für
Windows SmartScreen und eine vertrauenswürdige EXE muss zusätzlich ein
Authenticode-Zertifikat des Distributors in den Windows-Release-Job injiziert
werden. Das Zertifikat und Passwort gehören nicht in das Repository.

Beispiel im geschützten Windows-Release-Job:

~~~powershell
$ErrorActionPreference = "Stop"

$certPath = Join-Path $env:RUNNER_TEMP "debateai-signing.pfx"
[IO.File]::WriteAllBytes(
    $certPath,
    [Convert]::FromBase64String($env:WINDOWS_CODESIGN_PFX_B64)
)

& signtool sign `
    /fd SHA256 `
    /td SHA256 `
    /tr "http://timestamp.digicert.com" `
    /f $certPath `
    /p $env:WINDOWS_CODESIGN_PFX_PASSWORD `
    "dist\Backchannel\Backchannel.exe"
if ($LASTEXITCODE -ne 0) { throw "Authenticode-Signatur fehlgeschlagen." }

& signtool verify /pa /all /v "dist\Backchannel\Backchannel.exe"
if ($LASTEXITCODE -ne 0) { throw "Authenticode-Prüfung fehlgeschlagen." }

Remove-Item -LiteralPath $certPath -Force
~~~

Dieser Signaturschritt ist absichtlich außerhalb des Quellcodes: Ohne das
private Zertifikat kann keine verantwortbare Signatur erzeugt werden. Ein
unsigniertes lokales ZIP ist für Funktionsprüfung geeignet, aber nicht die
Produktionsfreigabe für Windows.

## 9. Fehlerdiagnose

~~~powershell
$log = Join-Path $env:LOCALAPPDATA "Backchannel\backchannel.log"
Get-Content -LiteralPath $log -Tail 120

Invoke-RestMethod http://127.0.0.1:11434/api/tags
ollama list
~~~

Wenn kein Overlay erscheint, zuerst das Tray-Menü öffnen und **Debatte öffnen**
wählen. Wenn nur eine Audiospur Pegel zeigt, Windows-Datenschutz,
Loopbackquelle und die Auswahl im Audio-Menü prüfen. Wenn ein Provider
fehlschlägt, bleibt der lokale Qwen-Pfad aktiv; den Provider anschließend unter
**Admin → Verbindungen** erneut testen oder anmelden.
