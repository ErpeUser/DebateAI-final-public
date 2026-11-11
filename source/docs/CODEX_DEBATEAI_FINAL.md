# Verbindlicher Abschlussauftrag: DebateAI als eigenstaendiges Programm

## Auftrag, Identitaet und vorhandener Stand

Produktname: **DebateAI**, ohne Leerzeichen. Ziel-Repository: `ErpeUser/DebateAI`.
Die Repository-ID bleibt **1450951492**, die Sichtbarkeit bleibt **private**.
Bis zur tatsaechlich verifizierten Umbenennung heisst es
`ErpeUser/backchannel-v6-private`. Kein zweites Repository erzeugen, keine
Historie umschreiben, kein Force-Push. Urheber-/Lizenzhinweise bleiben erhalten.

Die Implementierung liegt zunaechst auf `hardening/debateai-standalone`.
Der bereits gepushte Integrationscommit ist
`da030fafd5c1a76c103e6a07a824c915635e005a`; weitere getestete Commits dieses Branchs
sind einzubeziehen. Nicht blind nur `master` holen und dadurch die neue Arbeit
uebergehen. Einen neueren Stand anhand von Code und Tests sinnvoll integrieren.

Lies `AGENTS.md`, `source/AGENTS.md`, Windows-Final-Runbook, Releasing-Dokumentation,
die relevanten letzten Eintraege in `.ai/DEBATE_AI_OPTIMIERUNG.md` sowie diesen
Auftrag vollstaendig. Dieser neue Rebranding-Auftrag hat fuer Produktidentitaet
Vorrang, nicht fuer Datensicherheit oder vorgeschriebene Release-Pruefungen.

Bereits im Produktcode: lokaler ASR-Vergleich, deutsche Referenzsaetze,
Blindauswertung mehrerer Antwortpaare, In-App-Labordialog, Uploadbegrenzung,
Worker-/Abbruchschutz, Cache-Erhalt, frische DebateAI-Datenpfade und ein explizit
konfigurierter eigener Updatekanal. Nicht erneut als zweite Architektur bauen.
Die Labor-HTML-/JS-/CSS-Dateien liegen in `frontend/public/calibration*` und werden
vom bestehenden Vite-Build uebernommen. Der Dialog laesst den React-Baum gemountet.

## 1. Tatsächlichen vorhandenen Windows-Arbeitsordner erhalten und aktualisieren

Ermittle absoluten Root, Branch, HEAD, origin, lokale uncommittete Aenderungen
und lokale-only Commits. Keine neue temporaere Kopie als Endergebnis ausgeben.
Vor jedem Checkout/Stash/Merge/Rebase moegliche Kollisionen ignorierter Dateien
pruefen. Das aktualisierte `scripts/sync_final_workspace.py` enthaelt den Schutz
selbst, damit der bestehende Bootstrap aus einer einzelnen TEMP-Datei funktioniert.

Git-Befehl aus dem ermittelten existierenden Root:

```powershell
$ErrorActionPreference = 'Stop'
$repo = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repo) { throw 'Existing checkout not found.' }
git fetch origin '+refs/heads/master:refs/remotes/origin/master' '+refs/heads/hardening/debateai-standalone:refs/remotes/origin/hardening/debateai-standalone'
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed; inspect branch state and access.' }
git status --short
git log --left-right --oneline HEAD...origin/master
git diff --stat origin/master...origin/hardening/debateai-standalone
```

Falls der Integrationsbranch bereits gemergt/entfernt wurde, dessen enthaltene
Commits in `origin/master` nachweisen, statt einen fehlenden Ref zu ignorieren.
Beim Lesen mit `git show` die neueste Branch-Version des Sync-Skripts verwenden.
Bei Bedarf das Skript als UTF-8 ohne BOM nach TEMP schreiben und mit `--repo`
starten, wie im Root-AGENTS-Bootstrap. Das Skript synchronisiert master; es
entscheidet nicht selbst ueber die Integration des Feature-Branchs. Diese zuerst
semantisch pruefen und zusammenfuehren, ohne ungepruefte historische Commits
wiederherzustellen. Jede gesicherte lokale Aenderung einordnen: ueberholt,
bereits enthalten oder echte getestete Verbesserung. Keine blinde stash-apply-
oder cherry-pick-Serie. Lokale Commits und Stashes bleiben wiederherstellbar.

Erhalte insbesondere vorhandene Anwendungsdaten, DPAPI-Schluessel, API-Keys,
Browserprofile/Sessions, `.env`, Ollama-Modelle, eigene Strategien, Datenbanken,
Transkripte und Einstellungen. Niemals `git clean -fdx`. Eine Dateikollision
beheben bedeutet extern sichern und fachlich entscheiden, nicht Schutz umgehen.

## 2. Repository kontrolliert umbenennen

Nach Integration des aktuellen Sync-Schutzes und Tests:

```powershell
py -3.12 .\source\scripts\rename_debateai_repository.py --repo $repo
if ($LASTEXITCODE -ne 0) { throw 'Repository rename preflight failed.' }
py -3.12 .\source\scripts\rename_debateai_repository.py --repo $repo --apply
if ($LASTEXITCODE -ne 0) { throw 'Inspect reported remote/local rename state.' }
```

Das benutzt die vorhandene sichere `gh`-Anmeldung, liest keine Tokens aus und
prueft Repository-ID und Privatstatus vor/nach der Umbenennung. Kein anderes
Repository ersetzen, wenn der Zielname schon belegt ist. Explizite Push-URLs
werden bewusst zur semantischen Pruefung blockiert. Nach erfolgreichem Rename
URLs/Metadaten aktualisieren. Renaming ist keine neue Signatur oder Lizenz.

## 3. Noch offene technische Entkopplung wirklich abschliessen

Kein globales Suchen/Ersetzen ueber Laufzeitdaten. Diese zusammenhaengenden
Quellcode-Vertraege in einem getesteten Paket migrieren:

| Bereich | Exakte Stellen / Verhalten |
|---|---|
| Desktop-Namen | `desktop/launcher.py`, `desktop/backchannel.spec`, `desktop/updater.py`, `desktop/bcdesktop/`, deren Imports und Ressourcen. Ziel EXE `DebateAI.exe`, Updater `DebateAIUpdater.exe`, Bundle-Root `DebateAI`. Nicht nur ZIP umbenennen. |
| Build/Archive | `scripts/build_debate_assistant.ps1`, `scripts/release_desktop.ps1`, Publisher, Plattformmanifest-Erzeugung, `desktop/scripts/smoke_bundle.py` und `smoke_update_archive.py`; vorhandene Dateinamen im Checkout bestaetigen. Ziel Windows-Datei `dist/DebateAI-windows-x64.zip`. |
| Updatevertrag | `backend/app/services/update_service.py` ROOT_NAMES/LAUNCHERS, `update_signing.py` TRUSTED_ASSETS, Updatehelper/Health-Protokoll und Tests synchron aendern. Eigener Kanal bleibt ohne echte Konfiguration deaktiviert. Keine alte Release-Identitaet oder fremde Trust-Keys automatisch uebernehmen. |
| Sichtbare UI | React-Komponenten, Tray/Fenstertitel, App-/PWA-Manifest, HTML-Metadaten, About/Release-Hinweise, Exportnamen, Icons und Paketmetadaten inkl. Lockfile. Kein CSS-Verstecken alter Namen. |
| Interne Identitaet | Neue `DEBATEAI_*`-Variablen und `X-DebateAI-Instance` bevorzugen. Alte Namen nur explizit als dokumentierte Daten-/Protokollmigration tolerieren. Single-instance-Schutz darf niemals zwei Prozesse auf denselben PostgreSQL-Ordner lassen. |
| Infrastruktur | `.github/workflows`, `source/.github/workflows`, `docs-site/`, Worker-/R2-/Deploymentkonfigurationen inventarisieren. Alte automatische Deploy-/Publishpfade vor Promotion sperren oder vom Produktpfad trennen. Keine neuen Domains, Zertifikate oder Signaturen erfinden. |
| Herkunft | Historische Manifeste und rechtlich notwendige Credits nicht als aktive Abhaengigkeit behandeln. Keine alten SHA256-Listen als Nachweis fuer neue Artefakte ausgeben. |

Gezielte Bestandsaufnahme aus dem Repository-Root:

```powershell
git grep -n -i -E 'backchannel|bcdesktop|call.helper' -- source .github AGENTS.md README.md
```

Jeden Treffer als aktive Produktidentitaet, aktive Fremdserver-Abhaengigkeit,
notwendige Migrationsalias-Regel oder historische/rechtliche Herkunft klassifizieren.
Verbleibende Treffer begruenden; Null-Treffer durch Loeschen von Historie oder
Tests ist kein Qualitaetsnachweis. Den vollstaendigen Baum pruefen, nicht nur die
in der vorherigen Sitzung verfuegbare Teilkopie.

## 4. Nutzerdaten und Playbooks

Die Datenpfad-Aufloesung bewegt keine Dateien. Bei noch verwendetem Altpfad eine
Offline-Migration vorbereiten: eigene Prozesse kontrolliert stoppen, DB konsistent
sichern, Verzeichnis in eigenes Staging kopieren, Hashes/Vollstaendigkeit und
DPAPI-Zugriff unter demselben Windows-Benutzer pruefen, erst dann umschalten.
Original bis nach bewiesener Abnahme behalten. Kein Live-PostgreSQL-Verzeichnis
blind kopieren. Ein Programmrollback ist kein automatischer Schemarollback.

Alle 15 vorhandenen gueltigen RhetoricIQ-Strategien sowie echte lokale Erweiterungen
behalten. `ai/playbooks.json`, `ai/defaults/playbooks.json`, Live-/Deep-Prompts,
`services/ai_config.py`, `debate_settings.py` und Orchestrator-Trigger zusammen
pruefen. Benutzerkopien und alte Baseline vergleichen; kundenspezifische Prompts
nicht durch neue Defaults ueberschreiben. Nach Build `/api/ai-config`, aktiven
Pfad, Generation, Profile und Gegenfrage/Beweislast/Widerlegung im Runtimepfad testen.

## 5. Labor vervollstaendigen, keine doppelte Engine

Der Clip- und Blindimportpfad existiert und ist integriert. Noch erforderlich:
Antwortpaare aus dem vorhandenen produktiven Debatten-Replay/Benchmark exportieren
oder dessen Lauf ueber eine geschuetzte lokale Job-API anstossen. Keine vereinfachte
zweite generate_text-Promptpipeline, die am Produkt vorbeimisst. Gleiche kausale
Kontexte, beide Modi, aktive Promptversionen/Modellrouten, Commit, Hardware/Last,
Warm-/Kaltlauf, TTFT und sprechbare Antwortlatenz erfassen. Fehler im Nenner.

Vom Labor schon akzeptiertes Dateiformat:

```json
{
  "schema_version": 1,
  "cases": [{
    "case_id": "de-001",
    "mode": "hart",
    "context": "Die bisherige kausale Debatte bis zu diesem Zeitpunkt.",
    "candidates": [
      {"id": "route-a", "text": "Tatsaechliche Produktionsausgabe A"},
      {"id": "route-b", "text": "Tatsaechliche Produktionsausgabe B"}
    ]
  }]
}
```

Optional `context_sha256` mit 64 echten Hex-Zeichen sowie `prompt_version` liefern;
keine Platzhalter als Messnachweis. Kandidaten-Hashes muessen zum Fall passen.
Hoechstens 100 Faelle und 512 KiB je Import. Nichts sensitives automatisch exportieren.
Mindestens 20 echte deutsche Produktionsfaelle fuer belastbare persoenliche
Abnahme vorbereiten; keine Demoantworten als Modellvergleich ausgeben. Menschliche
Nutzwertbewertungen bleiben `factual_status=unverified`. Keine automatische
Gewinneruebernahme oder ungewollter Cloud-Fallback.

## 6. Tests, Build, Installation und alle Runtime-Gates

Zuerst gezielte Tests, dann gesamte vorhandene Backend-, Desktop- und Frontend-
Release-Gates einmal pro finalem Stand. Die neuen Tests sind in `.github/workflows/tests.yml`
integriert; lokale Fokustests ersetzen die vollstaendige Pipeline nicht.

```powershell
Push-Location (Join-Path $repo 'source')
try {
    py -3.12 -m unittest discover -s scripts/tests -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Repository safety tests failed.' }
    Push-Location backend
    try { py -3.12 -m unittest discover -s tests; if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' } }
    finally { Pop-Location }
    Push-Location desktop
    try { py -3.12 -m unittest discover -s tests; if ($LASTEXITCODE -ne 0) { throw 'Desktop tests failed.' } }
    finally { Pop-Location }
    Push-Location frontend
    try {
        npm ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
        npm run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        npm test; if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }
        node --test calibration-tests/core.test.mjs calibration-tests/suite.test.mjs
        if ($LASTEXITCODE -ne 0) { throw 'Calibration tests failed.' }
    } finally { Pop-Location }
    $python312 = py -3.12 -c "import sys; print(sys.executable)"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 unavailable.' }
    .\scripts\build_debate_assistant.ps1 -Python $python312 -IncludeOracle
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
} finally { Pop-Location }
```

Buildscript nach der Namensmigration weiterverwenden/gegebenenfalls atomar mit
seinen Aufrufern umbenennen. Frontend, Backend, ONNX, PostgreSQL, ffmpeg, Ollama,
CLIProxyAPI/Gemini-Plugin, Gemini-Web-Bridge, Oracle/portables Node24, PyInstaller,
Bundle-Smoke und Archiv-/Rollback-Smoke pruefen. Kein Download vorhandener Modelle
nur wegen des Rebrandings. Eigene Providerkonfigurationen nicht zuruecksetzen.

Neue ZIP erst nach erfolgreicher Pruefung in separates Staging entpacken. Vorhandene
Programmversion sichern; nur Programmdateien austauschen, nicht Anwendungsdaten.
Aktive Aufnahmen/Jobs auslaufen lassen. Bei Startfehler kontrolliert zur alten
Programmversion zurueckkehren und Schemakompatibilitaet beachten.

Alle 15 Gates einzeln protokollieren:
1. Neue EXE startet, genauer Prozesspfad stimmt.
2. Backend und eingebettete Datenbank bereit.
3. Tray, Hauptfenster und Labor bedienbar.
4. Alte Einstellungen/Sitzungen/Daten unveraendert verfuegbar.
5. Vorhandenes Ollama antwortet wirklich mit qwen3:4b ueber nativen Endpunkt.
6. Mikrofon und Systemaudio getrennt waehlbar und real funktionsfaehig.
7. Deutsche Transkription, Sprecherzuordnung und Live-Verarbeitung.
8. Overlay liefert kurze sprechbare Sofortantwort und gegebenenfalls Gegenfrage.
9. Hart und Ueberzeugen korrekt, gespeicherte Playbook/Profile wirksam.
10. Spaete Ergebnisse ueberschreiben keine neueren Transkript-/Claimrevisionen.
11. Recherche/Cloud/Diagnostik blockieren den lokalen Sofortpfad nicht.
12. Gespeicherte API-Keys unter demselben Windows-Benutzer verfuegbar.
13. ChatGPT Web, Gemini Web, Gemini-CLI/CLIProxyAPI nutzen vorhandene Loginpfade.
14. Kontrolliertes Beenden/Neustart ohne fremde Prozesse zu beenden.
15. Neues Updatearchiv, tokengebundener Health-Check und erzwungener Rollback.

Privacy First an/aus und reale Netzwerkziele pruefen. Keine Cookies/Passwoerter
extrahieren. Neue Logins ausschliesslich in der vorgesehenen sicheren UI durch
den Nutzer. Externe Kontoprobleme blockieren nicht unabhaengige lokale Arbeit.
Signierte Produktionsveroeffentlichung nur mit realem Authenticode-Zertifikat,
eigenem verifiziertem Update-Trust und erfolgreichen Releaseprotokollen.

## 7. Abschluss, Synchronisation und Nachweis

Normale technische Entscheidungen selbst treffen. Mehrere echte Codex-Agenten
nur bei tatsaechlich vorhandener Agentenfunktion verwenden: Audio/Realtime,
Desktop/Build/Migration, UI/Kalibrierung und unabhaengiger Read-only-Sicherheitsreview.
Keine parallelen Edits derselben Dateien; Integration und gesamte Tests zentral.
Nicht behaupten, mehrere Agents seien gelaufen, wenn nur ein Autor geprueft hat.

Getestete finale Aenderungen integrieren, committen, ohne Force-Push publizieren,
HEAD und neuesten origin/master nach Fetch vergleichen. Die gebaute und gestartete
Version muss genau zu diesem finalen Commit passen. Wenn nach Build Sourceaenderungen
noetig sind, betroffene Tests und Build wiederholen. Keine alten Artefakte umlabeln.

Abschlussbericht: Repository-ID/Name/Privatstatus; tatsaechlicher Windows-Root;
HEAD/origin/master; semantische Mergeentscheidungen; ZIP-/EXE-Pfade und SHA256;
Buildursprung; bestandene Tests; alle 15 Runtime-Gates mit getrennten Status fuer
automatisierte Fixtures, echte Hardware und Login; Provider-/Credential-Status;
noch offene technische Arbeiten und externe Blocker. Interne Restarbeiten nicht
als ausschliesslich externe Blocker umetikettieren. Fortschrittsdatei aktualisieren.
