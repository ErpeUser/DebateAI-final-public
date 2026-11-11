# DebateAI - exakter nativer Abschlussauftrag

Stand 2026-11-11. Produktname DebateAI, Zielrepository ErpeUser/DebateAI, ID1450951492, private, Zielbranch master. Bisher backchannel-v6-private bis echte Umbenennung belegt. Kein zweites Repository, Force-Push oder Historienumschreiben. Keine neue Grundsatzplanung verlangen: der Nutzer autorisiert normale technische Entscheidungen und Fertigstellung.

## Bereits umgesetzt, nicht doppelt bauen

Kalibrierungslabor/Navigation/Tests, begrenzte Uploads vor Multipart, asynchroner Decoder, Workerbesitz nach Abbruch, Modellcache-Erhalt, eingebetteter Sync-Kollisionsschutz, kompatible DebateAI-Datenidentitaet und expliziter eigener API-Updatekanal bleiben erhalten. Der Produktions-Paarbenchmark backend/scripts/benchmark_blind_pair.py ist jetzt integriert: vorhandener benchmark_debate_copilot.py in isolierten sequentiellen Prozessen, beide Modi, kausale deutsche Fixture, Herkunftshashes/Fehlernenner. Labor prueft Hash/Zaehler und erfindet keine Defaultbewertungen. Kein zweiter Promptstack. Die automatische Erzeugung ist ein Source-CLI, kein in die EXE eingebauter Button.

Gemeinsam vollstaendig lesen: Root/source AGENTS, windows-final-runbook.md, windows-final-recovery.md, releasing.md, RECONCILIATION_MATRIX_DE.md, FINAL_VERIFICATION_2026-11-11.md und letzte relevante Eintraege von .ai/DEBATE_AI_OPTIMIERUNG.md plus .ai/FINAL_INTEGRATION_2026-11-11.md. Alte 100/141 Tests sind historische Nachweise; aktuelle 94 fokussierte Linuxpruefungen sind keine Full-Tree-/Windowsfreigabe.

## 1. Bestehenden Windows-Checkout wirklich integrieren

Root/Branch/HEAD/origin/uncommittete Aenderungen/lokale Commits bestimmen. Neueste Remote-Fixes als Grundlage, ueberholten Source verwerfen, einzigartige kompatible Verbesserungen testen/erhalten. Vor Stash/Merge/Rebase aktuellen single-file sync_final_workspace.py gemaess Root-AGENTS bootstrappen; seine Kollisionsmeldungen nicht umgehen. Keine blind stash-apply, git clean -fdx oder Datenloeschung.

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

Nach Konsolidierung muss origin/master 9d88baae677083770c2c81943687713d6fc393a6 und die nachfolgenden Finalisierungsfixes enthalten. Feature-Branch nicht als zwingend existent voraussetzen: nach verifiziertem Merge darf er geloescht sein. Falls PR2 noch offen ist, zuerst den tatsaechlichen Stand pruefen/integrerieren, nicht neue Arbeit durch alten master ersetzen. Original-ZIP nicht ueber integrierten Source kopieren; apply_package.py ist historisch ersetzt.

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

## 5. Vollstaendige Gates und nativer Build

Python3.12, Node24, bestehende Constraints/Lockfiles. Vollstaendigen Checkout pruefen, nicht nur die neuen fokussierten Tests. Backend/desktop jeweils python -m unittest discover -s tests; scripts/tests; frontend npm ci, npm run build, npm test, npm run test:pwa -- --dist, node --test calibration-tests/*.test.mjs; vorhandene Playwright-/Security-/Releasegates. Jede Exitnummer pruefen. Nicht gestartete CI-Runner sind weder gruen noch automatisch ein Produktfehler; Ursache nachweisen und keine Sperren umgehen.

```powershell
Set-Location (Join-Path $repo 'source')
$python312 = py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 unavailable.' }
.\scripts\build_debate_assistant.ps1 -Python $python312 -IncludeOracle
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
```

Vor vollstaendiger Namensmigration lautet der vorhandene Output weiterhin dist/Backchannel-DebateAI-windows-x64.zip. Nie einfach umbenennen. Erforderliche Frontend/Labor/Backend/ONNX/PostgreSQL/ffmpeg/Ollama/CLIProxy/Gemini/Oracle-Node24-Komponenten, Bundle-Smoke und nativen Archiv-/Rollback-Smoke nachweisen. Nur fehlerbetroffene Schritte wiederholen.

Bestehende Installation erst nach geprueftem Build sicher aktualisieren: Aufnahme/Verarbeitung beenden, eigene Prozesse schliessen, konsistenten DB-Rueckweg sichern, validiertes Archiv in gleiches-Dateisystem-Staging, alte funktionierende Programmversion behalten, nur Binaerdateien tauschen, exakte neue EXE und tokengebundenen Health pruefen, bei Fehlschlag Rollback. Kein Loeschen-vor-Entpacken, AppData bleibt.

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

Vorhandene Credentials nur ueber App, interaktiven sicheren Login dem Benutzer ueberlassen, keine Standardprofil-Cookies extrahieren. Privacy First gegen wirkliche Ziele. Authenticode und Update-Signatur unterscheiden: reale Zertifikate/Kanal/Trust statt erfundener Werte, vorhandenen Releaseweg nur mit gepruefter eigener Infrastruktur nutzen.

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
Manuell ausfuehren und die Joblogs pruefen. Ein Lauf mit `steps: []` ist ein
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
