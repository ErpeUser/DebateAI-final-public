# Codex-Abnahme – DebateAI – 2026-11-12

## Zweck

Dieser Bericht ist der aktuelle, reviewfähige Übergabepunkt für Codex. Er trennt
belegte Quellcode- und Testarbeit von Nachweisen, die nur auf einem echten
Windows-System, mit realen Modellen/Anmeldungen oder durch Menschen erbracht
werden können.

## Ausgangslage und GitHub

- Repository: `ErpeUser/DebateAI`, privat, Repository-ID `1450951492`.
- Basis vor diesem Audit: `ffde73c2648bacab54388d749375a7083e42c12d`
  (`test: avoid retaining the removed hold literal`).
- Der aktuelle `master` enthält die bereits gemergten Identitäts- und
  Vertrags-Härtungen `fcdfc798...` und `d8cbb535...`.
- Es gibt nur den Default-Branch `master`; PR #1 bis #7 sind geschlossen und
  gemergt. Es ist kein offener PR vorhanden.
- Die letzten Actions-Läufe für `master` (Tests, Security, Docs-Site) endeten
  am 2026-11-12 vor dem ersten Job-Schritt mit `steps: []`/keinen Logs. Das
  ist kein grüner Testnachweis und derzeit als GitHub-Runner-/Provisionierungs-
  blocker zu behandeln.

## In diesem Audit umgesetzt

### Alembic/Datenbankvertrag

Die CLI-Migration nutzte noch einen aktiven Legacy-Default:

- `source/backend/alembic.ini` enthielt
  `callhelper:changeme@.../callhelper`.
- Eingebettete Migrationen überschreiben die URL bereits aus
  `settings.DATABASE_URL`, direkte Alembic-Aufrufe jedoch nicht.

Behoben auf diesem Branch:

1. Canonicaler, nicht geheimer DebateAI-Placeholder in `alembic.ini`.
2. `alembic/env.py` übernimmt für CLI und eingebettete Ausführung immer
   `settings.DATABASE_URL` und schützt Prozentzeichen für ConfigParser.
3. Neue Regressionstests in
   `source/backend/tests/test_alembic_configuration.py` verhindern die
   Rückkehr von `callhelper` oder `changeme` und prüfen den Runtime-Override.

Dadurch wird kein Passwort in Git eingeführt; der echte Wert kommt weiterhin aus
`.env`/Umgebung.

## Bereits im Quellstand vorhanden

Das Sprach- und Antwortlabor ist im aktuellen Source-Tree integriert, einschließlich
bounded Upload/Decode, identischer Aufnahme für mehrere ASR-Modelle, WER/CER-/RTF-
Verträgen, Blind-Pair-Import, Hash-/Nennerprüfung und Same-Origin-Launcher.
Relevante Pfade:

- Backend: `source/backend/app/routers/calibration.py`,
  `diagnostic_audio.py`, `calibration_runner.py`.
- Frontend: `source/frontend/public/calibration.html`,
  `calibration/core.mjs`, `lab.mjs`, `launcher.mjs`.
- Tests: `source/backend/tests/test_calibration_*.py`,
  `source/frontend/calibration-tests/`,
  `source/frontend/public/calibration/*.test.mjs`.

Die produktive Antwortpaar-Erzeugung bleibt bewusst eine explizite Source-CLI
(`source/backend/scripts/benchmark_blind_pair.py`), kein versteckter
Frozen-UI-Button. Kein Testsieger wird automatisch als aktive Konfiguration
übernommen.

## Backchannel-Unabhängigkeit

Aktive Laufzeitpfade, Variablen, Header, Update- und Desktop-Verträge verwenden
DebateAI. Vorkommen von Backchannel bleiben nur in:

- expliziter, nicht destruktiver Legacy-Migration,
- historischen Provenienz-/Release-/Audit-Aufzeichnungen,
- dem bewusst beibehaltenen SEO-/Vergleichspfad
  `/gong-and-backchannel/`,
- negativen Regressionstests.

Diese Vorkommen dürfen nicht pauschal gelöscht werden, weil sie Datenmigration,
Provenienz und Integritätsnachweise schützen. Ein neuer Build muss die aktiven
Paket-/EXE-/AppData-Verträge separat mit einem Windows-Smoketest bestätigen.

## Verifikation

Im aktuellen Linux-Arbeitsraum kann kein vollständiger Checkout und kein
Windows-Paket ausgeführt werden. Im vollständigen Checkout sind mindestens diese
Befehle auszuführen:

```bash
cd source/backend
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q app
cd ../frontend
npm ci
npm run build
npm test
npm run test:pwa -- --dist
cd ../desktop
python -m unittest discover -s tests -p 'test_*.py' -v
```

Zusätzlich für den neuen Fix:

```bash
cd source/backend
python -m unittest tests.test_alembic_configuration -v
```

Ein bestandener Linux-Lauf ersetzt nicht:

- Windows Python 3.12/Node 24 One-Dir-Build und exakte EXE-/ZIP-Identität,
- echtes Mikrofon/WASAPI-Systemaudio, WebView2 und DPI/Tray/Overlay,
- lokale Ollama-/ASR-Modellausführung auf der Zielhardware,
- interaktive ChatGPT-/Gemini-Web-Anmeldung,
- A06/A18/A21/A22 (Langaufnahme, menschliche Rhetorikbewertung, formale
  deutsche ASR- und Kausal-Datensatzmessung),
- Authenticode, öffentliche Update-/DNS-/R2-Publikation,
- ein grüner GitHub-Runnerlauf.

## Debattenvideo-Evaluierung – präziser nächster Auftrag

Ein echtes Video-/Debattenkorpus ist in diesem Repository nicht enthalten. Damit
keine Scheinsicherheit entsteht, führt Codex diesen Schritt nur mit ausdrücklich
freigegebenen, lokal gespeicherten Dateien aus:

1. Lege außerhalb von Git einen Ordner `evidence/video-debates/<case-id>/` an.
2. Speichere pro Fall Video/Audio, Zeitstempel, Sprecherlabels und eine
   anonymisierte Referenztranskription; keine privaten Konten/Cookies.
3. Extrahiere Audio reproduzierbar nach 16-kHz-PCM und markiere Schnitte,
   Überlappungen, Stille, Eigennamen, Zahlen und Selbstkorrekturen.
4. Spiele denselben Clip über das bestehende lokale ASR-/Debate-CLI ab; keine
   neue Prompt-Engine und keine stillen Cloud-Aufrufe.
5. Exportiere pro Modell WER, CER, RTF, Latenz bis zum ersten brauchbaren Zug,
   finale Antwortzeit, Abbruch-/Fehlergrund und Audio-Drops.
6. Für Antwortqualität: anonymisiere zwei echte Provider/Varianten, randomisiere
   A/B reproduzierbar, reveal erst nach menschlicher Bewertung und exportiere
   keine Schlüssel oder Rohtranskripte.
7. Ergänze erst danach Fixtures und Regressionstests. Ein synthetischer Fixture-
   Test darf als Contract-Test zählen, aber nicht als reale Modell- oder
   Hardwareabnahme.

Ein möglicher Codex-Fortsetzungsauftrag lautet:

> Lies `AGENTS.md`, `source/AGENTS.md`, die Vision und diesen Bericht. Prüfe
> zuerst, ob ein freigegebenes lokales Korpus vorhanden ist. Wenn nicht, ändere
> keine Produktpfade und markiere A06/A18/A21/A22 als offen. Wenn vorhanden,
> verwende ausschließlich bestehende `benchmark_blind_pair.py`,
> `diagnostics/local-fit/asr` und die Calibration-Verträge. Implementiere nur
> fehlende, isolierte Fixtures/Tests; belege RED→GREEN, reale Modellnamen,
> Hardware und Datenschutz. Führe nie heimliche Downloads/Logins aus und
> übernimm keinen A/B-Sieger automatisch.

## Merge-/Release-Gate

Vor dem Merge sind Branch-HEAD, Teststatus und Änderungsliste erneut gegen den
aktuellen `master` zu prüfen. Nach dem Push müssen `HEAD` und
`origin/master` auf demselben Commit stehen. Ein historisches v0.6.6-
Backchannel-Archiv oder ein alter Build darf nicht als aktuelle DebateAI-
Windows-Abnahme ausgegeben werden.
