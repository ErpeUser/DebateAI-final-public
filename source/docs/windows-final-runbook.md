# DebateAI - sicherer finaler Windows-Ablauf

Stand: 2026-11-11. Ausfuehrungsanleitung, kein Nachweis eines bereits gebauten oder installierten Windows-Releases. Gemeinsam mit Root-AGENTS, source/AGENTS, CODEX_DEBATEAI_FINAL.md und releasing.md verwenden. Die neue Produktidentitaet heisst DebateAI; noch nicht gemeinsam migrierte interne Archivnamen niemals isoliert umbenennen.

## 1. Bestehenden Arbeitsordner und Daten erhalten

Den tatsaechlich bisher verwendeten Windows-Checkout feststellen, nicht einen neuen Klon als Fertigstellung ausgeben. Repository-ID 1450951492, ErpeUser, private; alter Name backchannel-v6-private, autorisierter Zielname DebateAI. Branch/HEAD, uncommittete Aenderungen und lokale-only Commits erfassen. Neueste Fixes behalten, alte lokale Implementierungen nicht blind wiederherstellen; echte zusaetzliche Verbesserungen semantisch integrieren und testen.

```powershell
$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repo) { throw 'Existing checkout not found.' }
Set-Location $repo
git fetch origin '+refs/heads/master:refs/remotes/origin/master'
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed.' }
git status --short
git log --left-right --oneline HEAD...origin/master
```

Den aktuellen single-file `source/scripts/sync_final_workspace.py` aus origin/master gemaess Root-AGENTS bootstrappen. Dessen Kollisionsschutz VOR Stash/Merge/Rebase nicht umgehen. Aufgezeichnete Stashes/Backup-Branches fachlich pruefen, nicht blind anwenden. Kein Force-Push und kein git clean -fdx.

Erhalten: beide AppData-Ordner Backchannel und DebateAI, DPAPI/master.key, DBs, Profile/Cookies, API-/OAuth-Sessions, Ollama-Modelle, Transkripte, Sitzungen, eigene Konfigurationen und nichtversionierte Laufzeitdaten. Playbooks und Prompts gegen Benutzerkopie und alte Baseline vergleichen; gueltige neue Strategien erhalten. Nach Update den wirklich aktiven Pfad und die Generation ueber /api/ai-config pruefen.

## 2. Build aus genau diesem finalisierten Source

Windows x64, Python 3.12, Node24, npm und WebView2; bestehende Constraints und Lockfiles verwenden. Keine pauschalen Updates oder Neuinstallationen. Fuer normales Desktop-Bundle kein Docker/separates PostgreSQL erforderlich.

```powershell
Set-Location (Join-Path $repo 'source')
$python312 = py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0 -or -not $python312) { throw 'Python 3.12 required.' }
.\scripts\build_debate_assistant.ps1 -Python $python312 -IncludeOracle
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
$zip = Join-Path $repo 'source\dist\Backchannel-DebateAI-windows-x64.zip'
if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) { throw 'Archive missing.' }
Get-FileHash -LiteralPath $zip -Algorithm SHA256
```

Dieser Name ist der vorhandene Buildvertrag, bis EXE/Updater/Archivpruefung gemeinsam migriert sind. Zielname DebateAI-windows-x64.zip nicht allein durch Dateiumbenennung erzwingen. Erforderlich: Frontend inklusive calibration.html und sechs Laborassets, Backend, ONNX-Daten, PostgreSQL, ffmpeg, Ollama-Anbindung, CLIProxyAPI/Gemini-Plugin, Gemini-Web-Bridge, Oracle/portables Node24, PyInstaller, Bundle-Smoke und nativer Update-Archiv-Smoke. Nicht bestandene Schritte reparieren, nicht ignorieren.

## 3. Installation und Update ohne Datenverlust

**Niemals die vorhandene Programmversion vor Entpacken und Pruefung der neuen Version loeschen.** Auch bei Erstinstallation nicht in ein bereits benutztes Ziel entpacken. Die vorhandenen validierenden Updater-/Archivfunktionen verwenden; keinen zweiten ad-hoc Installer bauen.

Ablauf: neue ZIP/Hash/Smokes pruefen; vorhandene Installation eindeutig ermitteln; Aufnahme und Verarbeitung abschliessen; ueber Tray sauber beenden; nur eigene Prozesse/Dateisperren pruefen; konsistenten Datenbackup sichern; Staging als Geschwisterverzeichnis der Installation auf demselben Dateisystem anlegen; Archiv validieren und dort entpacken; Vollstaendigkeit/Vertrauensvertrag pruefen; alte funktionierende Programmversion als Rollback behalten; nur Programmdateien tauschen; exakte neue EXE starten; zur neuen Instanz passende tokengebundene Health-/DB-Pruefung ausfuehren. Bei Startfehler alte Programmdateien wiederherstellen.

Niemals AppData loeschen. Eine Kopie offener PostgreSQL-Dateien ist kein konsistenter Backup: kontrolliert stoppen oder den vorgesehenen konsistenten Backupweg benutzen. Binaerrollback macht Schemaaenderungen nicht rueckgaengig; vor dem ersten Start Migrationskompatibilitaet und Daten-Rueckweg sichern. Alte/neue EXE nicht gleichzeitig auf dieselbe DB loslassen. Alte Verknuepfungen und laufenden Prozesspfad pruefen. Backups bis nach Abnahme erhalten. Details: windows-final-recovery.md.

## 4. Lokales Ollama wirklich pruefen

Den tatsaechlich konfigurierten nativen Endpunkt verwenden, individuelle Ports nicht ueberschreiben. Beispiel fuer vorhandenes Ollama und Standardendpoint:

```powershell
$ErrorActionPreference = 'Stop'
$ollamaBase = 'http://127.0.0.1:11434'
$command = Get-Command ollama -ErrorAction SilentlyContinue
$ollama = if ($command) { $command.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
if (-not (Test-Path -LiteralPath $ollama -PathType Leaf)) { throw 'Use the approved Ollama setup path first.' }
$ready = $false
try { $tags = Invoke-RestMethod "$ollamaBase/api/tags" -TimeoutSec 3; $ready = $true } catch {}
if (-not $ready) {
    $owned = Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 1
        try { $tags = Invoke-RestMethod "$ollamaBase/api/tags" -TimeoutSec 3; $ready = $true } catch {}
    } until ($ready -or (Get-Date) -ge $deadline -or $owned.HasExited)
    if (-not $ready) { throw 'Ollama did not become ready; no endless retry.' }
}
if (-not ($tags.models | Where-Object { $_.name -eq 'qwen3:4b' })) {
    & $ollama pull qwen3:4b
    if ($LASTEXITCODE -ne 0) { throw 'Required model download failed.' }
}
$info = Invoke-RestMethod "$ollamaBase/api/show" -Method Post -ContentType 'application/json' -Body '{"model":"qwen3:4b"}' -TimeoutSec 10
$request = @{model='qwen3:4b'; stream=$false; think=$false; messages=@(@{role='user';content='Antworte in einem kurzen deutschen Satz: Warum braucht eine Behauptung einen Beleg?'})}
$response = Invoke-RestMethod "$ollamaBase/api/chat" -Method Post -ContentType 'application/json' -Body ($request | ConvertTo-Json -Depth 6) -TimeoutSec 120
if ([string]::IsNullOrWhiteSpace($response.message.content)) { throw 'No actual visible model answer.' }
```

Thinking-Parameter sind Anforderungen, keine Beweise. Unterstuetzung, sichtbare Antwort und wirkliche Zeit getrennt messen. Localhost kann Cloudaliases bedienen; remote_host/remote_model und echten Datenfluss pruefen. Vergleichsskripte laden bewusst keine Modelle nach. Niemals fremd gestartetes Ollama beenden.

## 5. Kalibrierung und Produktionspaare

Testlabor im Hauptfenster: 13 deutsche Testtypen, eigener Satz, Mikrofon/Import, gleicher Clip, WER/CER, Zahlen/Negation, Fehler im Nenner. Kein Beweis fuer Windows-Doppelspur, Streaming oder Diarisierung.

Echte Antwortpaare sind bereits implementiert. Desktop vorher kontrolliert beenden, zwei bereits installierte lokale Modelle waehlen und aus source/backend mit der Projektumgebung ausfuehren:

```powershell
python scripts\benchmark_blind_pair.py --model-a qwen3:4b --model-b NAME_DES_ZWEITEN_INSTALLIERTEN_MODELLS --output vergleich.json
```

Platzhalter durch vorhandenes Modell ersetzen. Exit0: alle Paare technisch nutzbar; Exit1: Fehler im exportierten Nenner; Exit2: Eingabe/Umgebung/Export abgelehnt. JSON im Labor importieren. Beide Modi, kausaler Kontext, vorhandener Orchestratorpfad, separate sequentielle Prozesse. Kein in die EXE eingebauter Generierungsbutton. Bei Benutzerprompts den vorhandenen DEBATE_AI_CONFIG_DIR bewusst auf den durch die App ausgewiesenen AI-Ordner setzen; keine Keys kopieren. Kleine Stichprobe und Hashes sind kein Fakten-/Qualitaetsbeweis. Kalt/Warm und Hardware/Gesamtlast gesondert erfassen.

## 6. Provider, Datenschutz und Zugangsdaten

API-Keys nur ueber Admin > Verbindungen testen/speichern; DPAPI-Wiederverwendung unter gleichem Windows-Benutzer pruefen. ChatGPT-Web mit vorgesehenem eigenen Chrome-/Edge-Profil, Gemini-Web im isolierten WebView2-Login. CLIProxyAPI/Gemini-CLI und konfigurierte APIs erhalten. Bei noetiger neuer Anmeldung nur den sicheren Login-Schritt dem Benutzer ueberlassen. Keine privaten Cookies/Passwoerter extrahieren, keine Secrets oder Transkripte in Logs/Releases kopieren.

Privacy First nach echter Datenroute pruefen. Recherche/externe Hintergrundanalyse bleiben bewusst aktiviert und blockieren die lokale Sofortantwort nicht. Ausgelaufene Sessions duerfen keinen ungewollten Cloudfallback erzeugen.

## 7. Alle 15 nativen Abnahmepunkte

1. Exakte neue EXE startet; Buildursprung/Prozesspfad stimmen.
2. Backend und eingebettete DB bereit.
3. Tray, Hauptfenster und Labor bedienbar.
4. Alte Einstellungen/Sitzungen/Daten erhalten.
5. Native Ollama-Antwort qwen3:4b, nicht bloss HTTP200.
6. Mikrofon und Systemaudio getrennt real funktionsfaehig.
7. Deutsche Transkription/Sprecher/Live-Debatte funktionieren.
8. Overlay zeigt sprechbaren Hauptzug und optionale Gegenfrage.
9. Hart/Ueberzeugen und gespeicherte Profile korrekt.
10. Spaete Revisionen ueberschreiben keine neuen Ergebnisse.
11. Hintergrundanalyse/Recherche stoeren lokalen Sofortpfad nicht.
12. Gespeicherte API-Keys unter demselben Benutzer lesbar.
13. ChatGPT/Gemini/CLI-Login- und Verbindungspfade nutzbar.
14. Sauber beenden/neustarten, keine fremden Prozesse beendet.
15. Sicheres Update, Startfehler und Rollback nachgewiesen.

Automatische Tests, Hardwarepruefung und Konto-/Benutzerinteraktion getrennt protokollieren. Keine ungetestete Funktion als bestanden markieren.

## 8. Signatur und Abschluss

Ein unsignierter Testbuild ist keine signierte Veroeffentlichung. Authenticode braucht ein echtes Zertifikat, Update-Metadaten einen unabhaengigen signierten Kanal. Keine erfundenen Signaturen/Trust-Keys/Domains. releasing.md mit gepruefter eigener Infrastruktur verwenden, keine geerbte fremde Produktionsverbindung als eigenen Kanal ausgeben.

Final git fetch origin master, git status --short, git rev-parse HEAD und origin/master vergleichen. Source, ZIP-Pruefsumme und wirklich gestartete EXE muessen denselben finalisierten Code nachweisen. Bericht mit Projektpfad, SHAs, Mergeentscheidungen, ZIP/Hash, EXE-Pfad, Tests, 15 Runtime-Gates, Providerstatus und exakten Restblockern. Eine lokale Benutzerdatei ist kein zu loeschender Sourcefehler.
