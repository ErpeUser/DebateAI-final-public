# DebateAI - verbindlicher Desktop-Abschlussauftrag und Windows-Runbook

Stand: 2026-11-11, konsolidiert nach Source-Merge #4. Produktname DebateAI; Zielrepository ErpeUser/DebateAI, stabile Repository-ID 1450951492, **privat**, Zielbranch master. Bis zur bestaetigten echten Umbenennung lautet der Name ErpeUser/backchannel-v6-private. Kein zweites Repository, keine umgeschriebene Historie und kein Force-Push.

**Prioritaet bei Widerspruechen:** Neueste explizite Nutzervorgaben und verbindliche Datenschutz-, Sicherheits- und Datenbewahrungsregeln der Root-/source-AGENTS haben Vorrang. Fuer die zwei hier konsolidierten Dokumente gilt die neuere, konkretere und pruefbare Vorgabe (besonders die Ergaenzungen vom 2026-11-11); sichere Ablaufdetails des Windows-Runbooks bleiben erhalten. Vor jeder Ausfuehrung den neuesten `origin/master` pruefen. Diese Datei ist ein Arbeitsauftrag, keine Behauptung einer Windows-Freigabe.

## Bereits umgesetzt, nicht doppelt bauen

Kalibrierungslabor/Navigation/Tests, begrenzte Uploads vor Multipart, asynchroner Decoder, Workerbesitz nach Abbruch, Modellcache-Erhalt, eingebetteter Sync-Kollisionsschutz, kompatible DebateAI-Datenidentitaet und expliziter eigener API-Updatekanal bleiben erhalten. Der Produktions-Paarbenchmark backend/scripts/benchmark_blind_pair.py ist jetzt integriert: vorhandener benchmark_debate_copilot.py in isolierten sequentiellen Prozessen, beide Modi, kausale deutsche Fixture, Herkunftshashes/Fehlernenner. Labor prueft Hash/Zaehler und erfindet keine Defaultbewertungen. Kein zweiter Promptstack. Die automatische Erzeugung ist ein Source-CLI, kein in die EXE eingebauter Button.

Gemeinsam vollstaendig lesen: Root/source AGENTS, windows-final-recovery.md, releasing.md, RECONCILIATION_MATRIX_DE.md, FINAL_VERIFICATION_2026-11-11.md und letzte relevante Eintraege von .ai/DEBATE_AI_OPTIMIERUNG.md plus .ai/FINAL_INTEGRATION_2026-11-11.md. Alte 100/141 Tests sind historische Nachweise; aktuelle 94 fokussierte Linuxpruefungen sind keine Full-Tree-/Windowsfreigabe.

## 1. Bestehenden Windows-Checkout wirklich integrieren

Root/Branch/HEAD/origin/uncommittete Aenderungen/lokale Commits bestimmen. Neueste Remote-Fixes als Grundlage, ueberholten Source verwerfen, einzigartige kompatible Verbesserungen testen/erhalten. Vor Stash/Merge/Rebase aktuellen single-file sync_final_workspace.py gemaess Root-AGENTS bootstrappen; seine Kollisionsmeldungen nicht umgehen. Keine blind stash-apply, git clean -fdx oder Datenloeschung.

Der sichere Bootstrap stammt aus dem neuesten Remote-Stand; Kollisionsschutz vor Stash/Merge/Rebase nicht umgehen. Zuerst vorhandene lokale Aenderungen und Commits pruefen.

```powershell
$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repo) { throw 'Existing local checkout not found' }
Set-Location $repo
$remote = (git remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $remote -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)ErpeUser/(DebateAI|backchannel-v6-private)(\.git)?/?$') { throw 'Unexpected origin' }
git fetch origin '+refs/heads/master:refs/remotes/origin/master'
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
$scriptText = git show origin/master:source/scripts/sync_final_workspace.py
if ($LASTEXITCODE -ne 0) { throw 'Newest sync script missing' }
$tempScript = Join-Path $env:TEMP ('debateai-sync-' + [guid]::NewGuid().ToString('N') + '.py')
try {
    [IO.File]::WriteAllText($tempScript, ($scriptText -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
    py -3.12 $tempScript --repo $repo
    if ($LASTEXITCODE -ne 0) { throw 'Inspect the reported collision/conflict and resolve safely' }
} finally { Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue }
```

Nach Konsolidierung muss origin/master 9d88baae677083770c2c81943687713d6fc393a6 und die nachfolgenden Finalisierungsfixes enthalten. Feature-Branch nicht als zwingend existent voraussetzen: nach verifiziertem Merge darf er geloescht sein. PR #2, #3 und #4 sind bereits gemergt; vor weiteren Integrationen neu verifizieren, keine alten ZIP-Overlays. Original-ZIP nicht ueber integrierten Source kopieren; apply_package.py ist historisch ersetzt.

Erhalte beide AppData-Ordner, alle DBs, DPAPI/master.key, Keys/OAuth/Cookies/Browserprofile, Ollama-Modelle, Audio/Transkripte/Sitzungen, .env und Benutzerkonfiguration. Backup ist kein Ersatz fuer semantische Entscheidung.

## 2. Reale Repository-Administration

```powershell
py -3.12 .\source\scripts\rename_debateai_repository.py --repo $repo
if ($LASTEXITCODE -ne 0) { throw 'Rename preflight failed.' }
py -3.12 .\source\scripts\rename_debateai_repository.py --repo $repo --apply
if ($LASTEXITCODE -ne 0) { throw 'Inspect remote/local rename state.' }
```

Bestehende sichere gh-Anmeldung verwenden, keine Tokens aus Profilen extrahieren. ID/Privatstatus vor/nachher verifizieren, Zielkonflikt nicht ueberschreiben. Ursprung aktualisieren nur nach bestaetigtem Rename. Helferexistenz ist kein erledigter Rename.

Alte Branches nur bei bewiesener Integration loeschen. Falls hardening/debateai-standalone noch existiert: fetch dieses Ref; git merge-base --is-ancestor origin/hardening/debateai-standalone origin/master muss0 liefern; erst dann git push origin --delete hardening/debateai-standalone. Bei fehlendem Ref nicht als Fehler neu erzeugen. Andere Branches separat auf einzigartige Arbeit pruefen, Default/aktive oder ungesicherte lokale Arbeit nicht loeschen. Kein Branchschutz-Bypass. Wenn die Chat-Schnittstelle keine Admin-/Deleteaktion bietet, ist dies ein echter verbleibender nativer CLI-Schritt.

## 3. Noch offene interne Entkopplung abschliessen

Diese Teile sind NICHT fertig migriert und muessen zusammen getestet werden, kein blindes Suchen/Ersetzen:

| Bereich | Dateien / Zielvertrag |
|---|---|
| Desktop | desktop/launcher.py, desktop/backchannel.spec, desktop/updater.py, desktop/bcdesktop/ und Imports/Ressourcen. Ziel DebateAI.exe, DebateAIUpdater.exe, Bundle DebateAI. |
| Archive/Build | scripts/build_debate_assistant.ps1, release_desktop.ps1, Publisher/Manifeste, desktop/scripts/smoke_bundle.py und smoke_update_archive.py; Ziel DebateAI-windows-x64.zip. |
| Update | backend/app/services/update_service.py ROOT_NAMES/LAUNCHERS, update_signing.py TRUSTED_ASSETS, Helper-/Health-/Signaturtests gemeinsam. Eigener Kanal ohne echte Konfiguration deaktiviert. |
| UI/Packages | Verbliebene React/Tray/About/Fenster/Exportnamen; package.json und Lockfile gemeinsam. PWA-Metadaten/Gate sind bereits DebateAI. Kein blosses CSS-Verstecken. |
| Kompatibilitaet | DEBATEAI_* und X-DebateAI-Instance bevorzugen, alte Namen kontrollierte Migrationsalias; niemals zwei Prozesse auf dieselbe DB. |
| Infrastruktur | Root/source workflows, docs-site/Worker/R2/Signer inventarisieren. Root deploy-site.yml wurde gelesen und baut nur, nicht blind wegen Dateinamen deaktivieren. Keine geerbten fremden Domains/Keys als eigenen Produktionskanal ausgeben. |
| Herkunft | Lizenzen, Credits, historische Pruefsummen/Manifeste erhalten, nicht als neue Releasebelege verwenden. |

```powershell
git grep -n -i -E 'backchannel|bcdesktop|call.helper' -- source .github AGENTS.md README.md
```

Treffer fachlich klassifizieren. Vor jedem Programm-/Datenordnerwechsel alte Version und konsistente DB sichern. Kein Live-DB-Copy als Backup. Datenstaging getrennt, Hashes/DPAPI unter gleichem Benutzer pruefen, Originale behalten. Binaerrollback ist kein Schemarollback. Vollstaendige Migration erst nach nativer Pruefung behaupten.

## 4. Playbooks/Prompts und echte Modellkalibrierung

Alle15 gueltigen Strategien und einzigartige lokale Ergaenzungen erhalten: ai/playbooks.json, ai/defaults/playbooks.json, Live-/Deep-Prompts, services/ai_config.py, debate_settings.py/Profile und Orchestrator-Trigger zusammen vergleichen. Benutzerkopie/alte Baseline/neue Defaults sichern und semantisch abgleichen. Nach Update /api/ai-config aktiven Pfad/Generation, Gegenfrage/Beweislast/Widerlegung und beide Modi nachweisen.

Desktop sauber beenden, zwei bereits installierte rein lokale Modelle bestimmen. In source/backend mit Projekt-Python:

```powershell
python scripts\benchmark_blind_pair.py --model-a qwen3:4b --model-b '<zweites-installiertes-lokales-Modell>' --output '<neue-Ergebnisdatei.json>'
```

Platzhalter ersetzen. Default20Turns liefern40geplantePaare in2Modi; Fehler/Timeout bleiben im Nenner. Kein Download/Cloudalias, keine Keyextraktion. Nur eigene Benchmarkkinder beenden, nicht Ollama. Vertrauenswuerdigen nativen Server statt beliebigem weiterleitenden Localhostproxy verwenden. Bei Benutzerprompts vorhandenen DEBATE_AI_CONFIG_DIR bewusst auf denselben aktiven AI-Ordner setzen. Hash ist nicht gesamter dynamischer Prompt und keine Wahrheit. Kalt/Warm/Hardware/Last gesondert protokollieren. JSON im Labor importieren, Nutzwert getrennt von Fakten; keine automatische Modellumstellung.

### Lokalen Ollama-Server und echte Antwort pruefen

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
    throw 'qwen3:4b fehlt: Download nur nach bewusster Freigabe ausfuehren, nicht still im Test.'
}
$info = Invoke-RestMethod "$ollamaBase/api/show" -Method Post -ContentType 'application/json' -Body '{"model":"qwen3:4b"}' -TimeoutSec 10
$request = @{model='qwen3:4b'; stream=$false; think=$false; messages=@(@{role='user';content='Antworte in einem kurzen deutschen Satz: Warum braucht eine Behauptung einen Beleg?'})}
$response = Invoke-RestMethod "$ollamaBase/api/chat" -Method Post -ContentType 'application/json' -Body ($request | ConvertTo-Json -Depth 6) -TimeoutSec 120
if ([string]::IsNullOrWhiteSpace($response.message.content)) { throw 'No actual visible model answer.' }
```

Thinking-Parameter sind Anforderungen, keine Beweise. Unterstuetzung, sichtbare Antwort und wirkliche Zeit getrennt messen. Localhost kann Cloudaliases bedienen; remote_host/remote_model und echten Datenfluss pruefen. Vergleichsskripte laden bewusst keine Modelle nach. Niemals fremd gestartetes Ollama beenden.

Das Beispiel gilt nur fuer den tatsaechlich konfigurierten nativen Ollama-Server. Keine fremden Prozesse oder Nutzerports ueberschreiben, keine Cloudaliases als lokal deklarieren. Sichtbare Antwort, Modellherkunft und Latenz getrennt nachweisen.

### Testlabor und Produktionspaar-Import

Testlabor im Hauptfenster: 13 deutsche Testtypen, eigener Satz, Mikrofon/Import, gleicher Clip, WER/CER, Zahlen/Negation, Fehler im Nenner. Kein Beweis fuer Windows-Doppelspur, Streaming oder Diarisierung.

Echte Antwortpaare sind bereits implementiert. Desktop vorher kontrolliert beenden, zwei bereits installierte lokale Modelle waehlen und aus source/backend mit der Projektumgebung ausfuehren:

```powershell
python scripts\benchmark_blind_pair.py --model-a qwen3:4b --model-b NAME_DES_ZWEITEN_INSTALLIERTEN_MODELLS --output vergleich.json
```

Platzhalter durch vorhandenes Modell ersetzen. Exit0: alle Paare technisch nutzbar; Exit1: Fehler im exportierten Nenner; Exit2: Eingabe/Umgebung/Export abgelehnt. JSON im Labor importieren. Beide Modi, kausaler Kontext, vorhandener Orchestratorpfad, separate sequentielle Prozesse. Kein in die EXE eingebauter Generierungsbutton. Bei Benutzerprompts den vorhandenen DEBATE_AI_CONFIG_DIR bewusst auf den durch die App ausgewiesenen AI-Ordner setzen; keine Keys kopieren. Kleine Stichprobe und Hashes sind kein Fakten-/Qualitaetsbeweis. Kalt/Warm und Hardware/Gesamtlast gesondert erfassen.

Die oben beschriebene Produktions-CLI ist die autoritative Generierung; keinen zweiten Prompt-Stack bauen. Exit 0 bedeutet alle Paare technisch nutzbar, Exit 1 Fehler im Nenner, Exit 2 Eingabe-/Umgebungs-/Exportfehler. Keine automatischen Modell-Downloads oder Modellumstellungen.

## 5. Vollstaendige Gates und nativer Build

Windows x64, Python 3.12, Node 24, npm, WebView2 und bestehende Constraints/Lockfiles. Kein externes Docker-/PostgreSQL-Setup fuer das normale Desktop-Bundle. Keine pauschalen Dependency-Upgrades. Vollstaendigen Checkout pruefen, nicht nur die neuen fokussierten Tests. Backend/desktop jeweils python -m unittest discover -s tests; scripts/tests; frontend npm ci, npm run build, npm test, npm run test:pwa -- --dist, node --test calibration-tests/*.test.mjs; vorhandene Playwright-/Security-/Releasegates. Jede Exitnummer pruefen. Nicht gestartete CI-Runner sind weder gruen noch automatisch ein Produktfehler; Ursache nachweisen und keine Sperren umgehen.

```powershell
Set-Location (Join-Path $repo 'source')
$python312 = py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 unavailable.' }
.\scripts\build_debate_assistant.ps1 -Python $python312 -IncludeOracle
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
$zip = Join-Path $repo 'source\dist\Backchannel-DebateAI-windows-x64.zip'
if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) { throw 'Archivname nur nach vollstaendig getesteter Umstellung ersetzen.' }
Get-FileHash -LiteralPath $zip -Algorithm SHA256
```

Vor vollstaendiger Namensmigration lautet der vorhandene Output weiterhin dist/Backchannel-DebateAI-windows-x64.zip. Nie einfach umbenennen. Erforderliche Frontend/Labor/Backend/ONNX/PostgreSQL/ffmpeg/Ollama/CLIProxy/Gemini/Oracle-Node24-Komponenten, Bundle-Smoke und nativen Archiv-/Rollback-Smoke nachweisen. Nur fehlerbetroffene Schritte wiederholen.

### Native Installation und Rollback ohne Datenverlust

**Niemals die vorhandene Programmversion vor Entpacken und Pruefung der neuen Version loeschen.** Auch bei Erstinstallation nicht in ein bereits benutztes Ziel entpacken. Die vorhandenen validierenden Updater-/Archivfunktionen verwenden; keinen zweiten ad-hoc Installer bauen.

Ablauf: neue ZIP/Hash/Smokes pruefen; vorhandene Installation eindeutig ermitteln; Aufnahme und Verarbeitung abschliessen; ueber Tray sauber beenden; nur eigene Prozesse/Dateisperren pruefen; konsistenten Datenbackup sichern; Staging als Geschwisterverzeichnis der Installation auf demselben Dateisystem anlegen; Archiv validieren und dort entpacken; Vollstaendigkeit/Vertrauensvertrag pruefen; alte funktionierende Programmversion als Rollback behalten; nur Programmdateien tauschen; exakte neue EXE starten; zur neuen Instanz passende tokengebundene Health-/DB-Pruefung ausfuehren. Bei Startfehler alte Programmdateien wiederherstellen.

Niemals AppData loeschen. Eine Kopie offener PostgreSQL-Dateien ist kein konsistenter Backup: kontrolliert stoppen oder den vorgesehenen konsistenten Backupweg benutzen. Binaerrollback macht Schemaaenderungen nicht rueckgaengig; vor dem ersten Start Migrationskompatibilitaet und Daten-Rueckweg sichern. Alte/neue EXE nicht gleichzeitig auf dieselbe DB loslassen. Alte Verknuepfungen und laufenden Prozesspfad pruefen. Backups bis nach Abnahme erhalten. Details: windows-final-recovery.md.

## 6. Alle15 Runtime-Gates verbindlich

1. Neue EXE startet; echter Prozesspfad/Buildursprung stimmen.
2. Backend und eingebettete DB bereit.
3. Tray, Hauptfenster und Testlabor bedienbar.
4. Vorhandene Daten/Einstellungen/Sitzungen erhalten.
5. Ollama qwen3:4b liefert echte native sichtbare Antwort.
6. Mikrofon und Systemaudio getrennt real funktionsfaehig.
7. Deutsche ASR, Sprecherzuordnung und Live-Debatte.
8. Overlay mit kurzer sprechbarer Hilfe und optionaler Gegenfrage.
9. Hart/Ueberzeugen sowie Profile/Strategien korrekt.
10. Spaete Revisionen ueberschreiben keine neueren Claims/Transkripte.
11. Hintergrund/Recherche/Diagnose beeintraechtigen lokalen Sofortpfad nicht.
12. Bestehende verschluesselte Keys unter gleichem Windows-Benutzer nutzbar.
13. ChatGPT-Web/Gemini-Web/CLIProxyAPI-Loginpfade funktionieren.
14. Sauber beenden/neustarten, keine fremden Prozesse beendet.
15. Native Update-/Startfehler-/Rollbackpruefung bestanden.

### Provider und Datenschutz

API-Keys nur ueber Admin > Verbindungen testen/speichern; DPAPI-Wiederverwendung unter gleichem Windows-Benutzer pruefen. ChatGPT-Web mit vorgesehenem eigenen Chrome-/Edge-Profil, Gemini-Web im isolierten WebView2-Login. CLIProxyAPI/Gemini-CLI und konfigurierte APIs erhalten. Bei noetiger neuer Anmeldung nur den sicheren Login-Schritt dem Benutzer ueberlassen. Keine privaten Cookies/Passwoerter extrahieren, keine Secrets oder Transkripte in Logs/Releases kopieren.

Privacy First nach echter Datenroute pruefen. Recherche/externe Hintergrundanalyse bleiben bewusst aktiviert und blockieren die lokale Sofortantwort nicht. Ausgelaufene Sessions duerfen keinen ungewollten Cloudfallback erzeugen. Authenticode und Update-Signatur unterscheiden: reale Zertifikate/Kanal/Trust statt erfundener Werte, vorhandenen Releaseweg nur mit gepruefter eigener Infrastruktur nutzen.

### Signatur und eigenstaendiger Update-Trust

Ein unsignierter Testbuild ist keine signierte Veroeffentlichung. Authenticode braucht ein echtes Zertifikat, Update-Metadaten einen unabhaengigen signierten Kanal. Keine erfundenen Signaturen/Trust-Keys/Domains. releasing.md mit gepruefter eigener Infrastruktur verwenden, keine geerbte fremde Produktionsverbindung als eigenen Kanal ausgeben.

## 7. Ein Ergebnisbericht, keine erneute Grundsatzplanung

Konkrete Fehler beheben, relevante Tests, commit/push ohne force, neuesten master integrieren, dann aus genau diesem Source bauen. Spaeterer Sourcefix erfordert neuen Buildnachweis. git fetch origin master; git status --short; git rev-parse HEAD und origin/master muessen uebereinstimmen. Retained user files nicht als Sourcegarbage entfernen.

Bericht: echter Projektpfad, finalerSHA/Gleichheit, verworfene/integrerte lokale Aenderungen, ZIP-Pfad/SHA256, gestarteteEXE/Buildursprung, automatische Tests getrennt von Hardware, alle15Gates, Provider/Keys/Login, echter Repositoryname und Branchstand, exakte Restblocker. Signierter Release erst nach erfolgreichem Protokoll; Source-Merge ist keine fertige Windows-Installation. Unabhaengige Aufgaben trotz externerBlocker fertigstellen.


## 8. Ergaenzungen fuer die Umsetzung vom 2026-11-11

Die additive Contract-Schicht `source/backend/app/services/response_contract.py`
validiert Replay- und Laborereignisse, ohne den Live-Orchestrator oder die
Datenbank zu ersetzen. Verwende sie zuerst am Export-/Benchmark-Rand. Pflicht-
pruefungen sind schema_version, case_id/turn_id, Claim-Lineage, endliche nicht-
negative Latenzen, monotone first_update/final_update-Zeitpunkte sowie der
vollstaendige Status-/Failure-Satz ok, timeout, empty, stale, error und abstent.
Unbekannte Felder bleiben fuer Vorwaertskompatibilitaet erhalten. Semantische
Wahrheit, Entailment und Quellenqualitaet niemals aus Hashes ableiten.

Der Produktions-Replay muss fuer jede Variante alle gestarteten Faelle im
Nenner behalten. Fehlende Ausgabe, Timeout, leere Antwort, stale Ergebnis,
Providerfehler und Parsingfehler werden nicht herausgefiltert. Ersthilfe,
spaetere Revision, correct-to-wrong und wrong-to-correct getrennt protokollieren.

Fuer die GitHub-Actions-Diagnose sind `workflow_dispatch`-Einstiege in
`.github/workflows/tests.yml` und `.github/workflows/security.yml` vorhanden.
Manuell ausfuehren und die Joblogs pruefen. Ein Lauf mit `steps: []` oder `steps: null` ist ein
Runner-/Dispatchfehler und kein gruenes Gate. Testkommandos nicht blind aendern.

Markdown-Cleanup ist referenzbewusst: historische Audit-, Release-, Provenance-
und Superpowers-Dokumente bleiben erhalten. Vor dem Loeschen eines Dokuments
muss eine statische Referenzsuche, eine Manifestpruefung und ein Testlauf zeigen,
dass es kein Build-, Release-, Prompt- oder Recoveryvertrag ist. `backchannel.spec`,
Backchannel.exe, `BACKCHANNEL_*` und `%LOCALAPPDATA%\\Backchannel` bleiben bis
zur vollstaendig getesteten Migration kontrollierte Legacy-Aliase.

Die vier externen Evidenzgates A06, A18, A21 und A22 bleiben echte manuelle
Windows-/Human-Review-Gates. Source-Tests, Linux-CI oder Mock-Audio duerfen sie
nicht als bestanden markieren. Eine Produktionspromotion eines ASR-Modells,
einer neuen Antwortpolicy oder der Repository-/EXE-Namensmigration ist erst
nach diesen Nachweisen erlaubt.

Vor dem finalen Merge immer: Branch-Head und erwartete SHA pruefen, relevante
Tests mit Exitcode ausfuehren, Arbeitsbaum/Remote vergleichen, PR gegen master
mit vollstaendigem Ergebnisbericht anlegen und nur bei sauberer Review-/Gate-
Lage ohne Force-Merge integrieren. Der Merge eines Source-PRs bestaetigt keine
Windows-Installation oder Signatur.

## Verbindliches Endergebnis

Diese Datei ersetzt die zwei bisherigen Anleitungen. Zuerst den echten Windows-Checkout synchronisieren und finalen Code testen, dann genau diesen Code bauen und ohne Datenverlust installieren. Alle 15 Runtime-Gates und A06/A18/A21/A22 getrennt nachweisen. Modell-, Account-, Hardware- und Signaturblocker nicht als bestanden erfinden. Aktuellen GitHub-Head und ZIP-/EXE-Ursprung nachweisbar abgleichen. Ein Quellcode-Merge allein ist keine Windows-Installation.
