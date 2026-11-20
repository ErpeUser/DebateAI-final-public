# DebateAI – Offene Punkte

Stand: 2026-11-20. Diese Datei enthält ausschließlich aktuell offene Entscheidungen, Nachweise und Freigabegates. Historische Evidenz und frühere Zielstände stehen gesammelt in [HISTORIE.md](HISTORIE.md). Ein Punkt bleibt offen, wenn der aktuelle Tree, ein Acceptance-Bericht oder ein erreichbarer GitHub-Nachweis ihn nicht abschließend belegt.

## P0 – vor einer belastbaren Produkt- oder Releasefreigabe

### P0.1 GitHub Actions tatsächlich ausführen

- **Problem:** Viele PR- und Master-Läufe endeten mit fehlenden Runner-Schritten, steps:null, 404-Logs oder Account-/Billing-Limit. Das ist kein grüner Test.
- **Status:** offen/blockiert; PR #24 nennt Billing-/Spending-Limit und Regeln-403 ausdrücklich.
- **Nächste Handlung:** Runner/Billing klären, Workflow-Trigger und Permissions prüfen, vollständige Jobs auf dem aktuellen Master oder einem exakt reproduzierbaren Branch starten.
- **Fertigstellungsnachweis:** sichtbare erfolgreiche Jobs für Backend, Frontend, Desktop, Docs/Worker, Security und Release-Contracts inklusive Logs und Commit-SHA.
- **Quelle:** PRs #3, #6, #8, #18, #24; [historischer Status vom 19.11.2026](HISTORIE.md#historischer-status-2026-11-19); [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18).

### P0.2 Signiertes produktives Windows-Release

- **Problem:** Authenticode ist im aktuellen Beleg NotSigned. Der Release-/R2-/Download-/DNS-/Access-Pfad und ein echter Hold-Commit sind nicht produktiv nachgewiesen.
- **Status:** Bundle-/Hash-/Rollback-Smokes vorhanden; Signatur, Operatorfreigabe und produktiver Download offen.
- **Nächste Handlung:** Zertifikat/Remote-Signing, Hold-Commit, Release-Manifest, R2/Access/DNS und Signaturprüfung auf sauberem Windows durchführen; keine Testfreigabe mit unsignierter EXE.
- **Fertigstellungsnachweis:** signierte EXE und ZIP, Zertifikatskette/Thumbprint, reproduzierbare Hashes, veröffentlichter Download, Update und erzwungener Rollback von einem frischen Client.
- **Quelle:** [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18); app/docs/releasing.md; GitHub-Release v0.6.6 mit ausdrücklich offenen Signatur-/Hardware-Gates.

### P0.3 Reale Windows-/Audio-/GUI-/Provider-Abnahme

- **Problem:** Headless-Health, lokale ASR und Testlabor wurden nachgewiesen; echter 120+-Sekunden-Mikrofon-/WASAPI-/System-Audiolauf, GUI/WebView2/DPI, Gerätewechsel, Langzeitsitzung und reale Provider-Logins fehlen.
- **Status:** offen; Release v0.6.6 nennt A06, Hardware/DPI und externe Rollback ausdrücklich als Grenzen.
- **Nächste Handlung:** frisches Windows-Gerät mit realem Mikrofon und Loopback, Login-/Kosten-/Privacy-Szenarien und Update/Restart/Rollback prüfen; Audio- und UI-Evidenz speichern.
- **Fertigstellungsnachweis:** unveränderte Testfixtures, Rohmetriken für ASR/Latency/CPU/RAM, Bildschirm-/Event-Evidenz, Wiederholung nach Neustart und klarer PASS/FAIL/NOT_APPLICABLE je Gate.
- **Quelle:** app/docs/VISION.md; app/docs/DESKTOP_FINAL.md; app/docs/windows-final-recovery.md; [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18); Release Notes v0.6.6.

### P0.4 Öffentliche Quellenstrategie entscheiden

- **Problem:** DebateAI-Source ist ausdrücklich code-only und kann seine eigenen vollständigen Layout-/Build-Gates wegen fehlender AGENTS, Workflows, Spec, Signing-Keys, docs-site worker, acceptance catalog und credential-naher Module nicht erfüllen. final-public ist vollständiger, aber public-only nach dem privaten Master.
- **Status:** bewusst unvollständiger Export; öffentliche Build-/Release-Freigabe offen.
- **Nächste Handlung:** Variante festlegen: code-only Forschungsquelle beibehalten und Grenzen im README schärfen oder einen reproduzierbaren, secretsfreien Public-Release mit allen erforderlichen Contracts erzeugen.
- **Fertigstellungsnachweis:** dokumentierte Datei-/Build-Matrix, erfolgreicher Source-only-Build oder explizite Nicht-Produktionsfreigabe, keine fehlenden Pflichtpfade im gewählten Vertrag.
- **Quelle:** README des DebateAI-Source; app/scripts/verify_repository_layout.py; öffentliche Snapshot-Inventur; final-public 8396409/5d10e41.

### P0.5 Offener Governance-PR #24

- **Problem:** Draft PR #24 enthält app-Layout, Workflows, CODEOWNERS, Dependabot und Struktur-/Secret-Gates, ist aber vor Billing/CI, Ruleset-Prüfung, neuem Windows-Build, signiertem Download und Dependabot-Risikobewertung nicht mergebereit.
- **Status:** offen, Draft, Basis 79c095c, Head 468559d5.
- **Nächste Handlung:** die P0.1–P0.2-Nachweise liefern, Diff/Workflow-Trigger prüfen, Dependency-Risiken bewerten und erst danach Review/Merge entscheiden.
- **Fertigstellungsnachweis:** PR-Checks grün, unabhängiger Review, dokumentierte Ruleset-/Billing-Situation und bewusstes Merge- oder Close-Entscheid.
- **Quelle:** PR #24.

## P1 – vor einer vollständigen Funktions- und Qualitätsaussage

### P1.1 Dependency-Audit reparieren oder begründen

- **Problem:** npm audit meldet im Docs-Site-Teil 11 High und im optionalen Oracle-/ChatGPT-Pfad 4 High; Frontend und Signing Worker waren im Bericht sauber.
- **Status:** offen; nicht pauschal durch Upgrade lösen.
- **Nächste Handlung:** Advisories einzeln bewerten, kompatible Updates/Overrides testen, optionalen Pfad isolieren oder bewusst begründen.
- **Fertigstellungsnachweis:** frischer Audit-Report mit Null unakzeptierten Findings und Regressionstests oder genehmigte Risikoentscheidung mit Ablaufdatum.
- **Quelle:** [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18); [historischer Status vom 19.11.2026](HISTORIE.md#historischer-status-2026-11-19); PR #24.

### P1.2 276-Punkte-Ledger abschließen

- **Problem:** Der historische MASTER_276_STATUS-Ledger enthält überwiegend offene/teilweise Punkte; Acceptance reporting setzt product_accepted=false. A006/A010 sind blockiert, A086 ist IMPLEMENTIERT_ABNAHME_OFFEN; der öffentliche Snapshot enthält den Ledger nicht.
- **Status:** offen; einzelne A-Items sind nachgewiesen, die Gesamtfreigabe fehlt.
- **Nächste Handlung:** jeden Punkt auf aktuellen app-Pfad abbilden, Status nur mit frischem Beleg ändern, alte source-Pfade als Historie markieren.
- **Fertigstellungsnachweis:** versionierter Ledger mit Status, Quelle, Test/Manuell-Nachweis, Rest-Risiko und Verantwortungsentscheidung; keine Default-Ratings.
- **Quelle:** [HISTORIE.md](HISTORIE.md#historischer-status-2026-11-19); app/scripts/acceptance/reporting.py; der private Ledger ist im geschützten Audit archiviert.

### P1.3 A22/Human-Rating unabhängig abnehmen

- **Problem:** PR #19 korrigierte den unvollständigen Denominator-Validator, wurde aber nicht gemergt. Menschliche rhetorische Qualität, unabhängige Datensätze und Rater-Übereinstimmung sind offen.
- **Status:** Validator-Korrektur historisch getestet (10/10 in temporärer Rekonstruktion), keine aktuelle Master-/Windows-/Human-Abnahme.
- **Nächste Handlung:** aktuelle app-Version prüfen, Validator in CI ausführen, vollständige eindeutige Ratings und unabhängige Fälle erfassen.
- **Fertigstellungsnachweis:** RED/GREEN-Regression im aktuellen Tree, Denominator- und Boolean-Gates, anonymisierte Human-Ratings mit Fehlerfällen und Reproduktionsreport.
- **Quelle:** PR #19; app/docs/VISION.md; app/scripts/acceptance/*.

### P1.4 Release-/Update-Cutover nachweisen

- **Problem:** Release-Runbook fordert realen Hold-Commit, Manifest, Signing, R2/Access und getrennten Binary-/Daten-Rollback; der produktive Cutover ist nicht belegt.
- **Status:** Runbook und isolierte Smokes vorhanden; externe Veröffentlichung offen.
- **Nächste Handlung:** eine versionierte Probeveröffentlichung unter Operator-Kontrolle mit frischem Client und Abbruch-/Rollback-Fall durchführen.
- **Fertigstellungsnachweis:** Hold-Commit-SHA, Signatur-/Manifest-Bericht, Download-/Update-/Rollback-Logs, Datenintegritätsprüfung und Freigabeentscheidung.
- **Quelle:** app/docs/releasing.md; app/docs/windows-final-recovery.md; [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18).

### P1.5 Aktive Website-Versprechen mit Code abgleichen

- **Problem:** Website behauptet unter anderem ganze Pipeline ohne Key und lokale Dokumentverarbeitung; der Code unterscheidet jedoch zwischen Privacy First ohne Shield (vollständige Dokument-Summarization teilweise Gemini-Files-API) und aktiviertem PII Shield (lokale begrenzte Extraktion), während lokale Live-Captions experimentell/CPU-lastig sind. Zusätzlich sind im final-public-Snapshot viele Site-Asset-/Docs-Ziele relativ nicht vorhanden.
- **Status:** Widerspruch und Distributable-Site-Lücke offen.
- **Nächste Handlung:** Claims pro Feature als lokal, cloud-gebunden, experimentell oder ungeprüft markieren; fehlende Assets/Docs erzeugen oder Links entfernen.
- **Fertigstellungsnachweis:** automatischer Link-/Asset-Scan ohne fehlende Ziele, Claim-Matrix mit Codepfad und Test, aktualisierte Privacy-/Locality-Texte.
- **Quelle:** app/site/index.html; backend privacy.py; local_live_captioner.py; docs-site sync/build scripts; öffentliche Site-Referenzscan.

## P2 – technische Schulden und belastbare Messung

### P2.1 Ruff-/Duplikat-Schulden reduzieren

- **Problem:** Der Evidenzbericht nennt rund 220 breite Ruff-Style-Warnungen und 67 jscpd-Duplikatstellen, überwiegend Tests.
- **Status:** F-Fehler und vulture waren bereinigt; Stil-/Duplikatlast bleibt.
- **Nächste Handlung:** produktionskritische Duplikate und sicherheitsrelevante Warnungen priorisieren; keine ungezielte Massenformatierung während Releasearbeit.
- **Fertigstellungsnachweis:** frischer Ruff-/jscpd-Report mit begründeten Ausnahmen und unveränderten Verhaltenstests.
- **Quelle:** [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18); [historischer Status vom 19.11.2026](HISTORIE.md#historischer-status-2026-11-19).

### P2.2 Reproduzierbarkeit des vollständigen privaten Builds

- **Problem:** Historische Testzahlen stammen teilweise aus isolierten oder materialisierten Checkouts; öffentliche Snapshots fehlen absichtlich Module/Specs/Runtime.
- **Status:** private Evidenz vorhanden, unabhängige Wiederholung auf sauberem Commit erforderlich.
- **Nächste Handlung:** app-Quellstand, Lockfiles, Lizenzen und regenerierbare Runtime getrennt archivieren; Build in sauberem Windows-/Linux-Checkout wiederholen.
- **Fertigstellungsnachweis:** Build-Matrix mit Commit, Toolchain, Dependencies, Artifact-Hashes und reproduzierbarem Testlauf.
- **Quelle:** [historische Evidenz vom 18.11.2026](HISTORIE.md#historische-evidenz-2026-11-18); app/docs/releasing.md; DebateAI-Source README; final-public HEAD.

### P2.3 ASR-/Latenz-/Rhetorikmessung auf Zielhardware

- **Problem:** Das Labor misst lokal synthetische/gespeicherte Fälle; Streaming, Dual-Track, Sprecherfehler, Tail-Latency und reale lange Sitzungen sind nicht ausreichend belegt.
- **Status:** calibration_runner.py nennt diese Einschränkungen ausdrücklich; reporting markiert relevante Vergleiche NOT_MEASURED.
- **Nächste Handlung:** referenzierte deutsche Audiofälle, WASAPI-Mikrofon/Loopback, WER/CER, first-speakable/final latency, RTF, CPU/RAM und Revisionen messen.
- **Fertigstellungsnachweis:** Rohdaten, Hardware-/Modell-/Prompt-Hashes, Fehlerklassen, Konfidenz-/Wiederholungsangaben und kein universeller Siegerclaim.
- **Quelle:** app/backend/app/services/calibration_runner.py; transcription_readiness.py; app/docs/HISTORIE.md; app/docs/VISION.md.

### P2.4 Sprach- und UI-Vertrag bereinigen

- **Problem:** Release-Notes nennen automatische Spracherkennung/Parakeet-v3, Seed-/Runtime-Code erzwingt de; Frontend copy behauptet teilweise keine lokale Live-Option, während Backend sie experimentell anbietet.
- **Status:** dokumentierter Code-/Text-Widerspruch.
- **Nächste Handlung:** Entscheidung aus VISION.md treffen und Seed, Runtime, Release Notes, Frontend und Tests synchronisieren.
- **Fertigstellungsnachweis:** eine konsistente Sprachmatrix plus Tests für de/auto/Mehrsprachigkeit und aktualisierte Hilfetexte.
- **Quelle:** backend/app/release_notes.py; seed_agents.py; transcription_runtime.py; LocalModelFitCard.tsx; BatchTranscriptionCard.tsx.

### P2.5 Historische Pfade und Quellenverweise trennen

- **Problem:** Einige Dokumente verweisen noch auf source-Pfade, während aktive Quelle app ist. Das ist für historische Provenienz zulässig, für aktuelle Buildanweisungen aber missverständlich.
- **Status:** Kanonischer Index wurde umgestellt, nicht alle historischen/operativen Texte sind bereinigt.
- **Nächste Handlung:** aktive Befehle/Links auf app aktualisieren, historische Pfade mit Datum/Commit kennzeichnen.
- **Fertigstellungsnachweis:** Link-/Pfadscan ohne aktive falsche source-Referenz, historische Quellenliste erhalten.
- **Quelle:** 9db4446; app/docs/DEBATEAI_CANONICAL_INDEX.md; app/docs/README.md.

## P3 – nachgelagerte Ordnung und Entscheidungen

### P3.1 Öffentliche Dependabot-PRs entscheiden

- **Problem:** DebateAI-Source PR #1 und #2 sind offen und betreffen release-signing-worker (undici/wrangler bzw. sharp/wrangler); keine Reviews oder verwertbaren CI-Statuswerte.
- **Status:** offen.
- **Nächste Handlung:** Advisories/Lockfile-Diffs prüfen, CI auf öffentlichem main ermöglichen, bewusst mergen oder schließen.
- **Fertigstellungsnachweis:** Review, grüner Build und Merge-Commit oder dokumentierte Ablehnung.
- **Quelle:** DebateAI-Source PR #1/#2; Branches 0721ff0 und e3eadfd.

### P3.2 Repository-/Projekt-Inventar laufend aktualisieren

- **Problem:** Private Tags/Projects/Rulesets waren über die zugängliche Connector-API nicht vollständig auslesbar; PR-Suche lieferte keine #22/#23. Das sind Zugriffslücken, keine Negativbeweise.
- **Status:** ungeklärt.
- **Nächste Handlung:** mit authentifiziertem GitHub-Read-Zugriff Tags, Releases, Projects, Rulesets, PR #22/#23, alle Reviewthreads und Actions-Artefakte erneut exportieren.
- **Fertigstellungsnachweis:** vollständige API-Listen mit Zeitpunkt, Cursor/Seitenzahl und Abgleich gegen lokale Refs.
- **Quelle:** Audit-Protokoll 2026-11-19; Connector-Fehler für direkte private tags/projects; PR-/Issue-Suche.

### P3.3 Diese Konsolidierungsdokumente als laufende Quelle pflegen

- **Problem:** Historie, Vision und Restarbeiten waren über viele Einzeldateien verteilt; neue Belege können den Stand ändern.
- **Status:** offen; die frühere Angabe eines separaten Prüf-Branches und unveränderten Masters ist historische Provenienz und beschreibt nicht den aktuellen Public-Stand. `main` enthält die Remediation und die Backlog-Pflege; die frühere Code-Evidenz bezog sich auf `b7e1b7d692034937139b23921a784c6c4e19cc98`. Die aktuelle Branch-SHA muss bei jeder Fortschreibung frisch geprüft werden.
- **Nächste Handlung:** Nach jeder Review nur mit Commit-/Test-/Releasebeleg aktualisieren, erledigte Punkte nicht als offen weiterführen und ungeklärte Alternativen erhalten.
- **Fertigstellungsnachweis:** Jede Änderung verweist auf Commit, PR, Pfad oder frischen Prüflauf; der aktuelle Branch-/HEAD-Stand ist im Dokument datiert und der Diff bleibt auf zulässige Dokumentdateien beschränkt.
- **Quelle:** Nutzerauftrag; historischer Branch `docs/project-consolidation-2026-11-19`; belegter Codecommit `b7e1b7d692034937139b23921a784c6c4e19cc98`.
### P1.6 Aktive Dokumentations-, Link- und Branchreferenzen konsolidieren

- **Kategorie:** **Docs-Drift**
- **Istzustand (historischer Ausgangsbefund am Audit-HEAD `791f864de8025aed4cfe5848f0e9e5b4d7402865`):** `app/docs-site/site.test.js:7-11,50-51` las `app/docs/README.md`, die Datei fehlte; der damalige Docs-Site-Lauf `44640619661`, Job `135970434379`, brach mit `ENOENT` ab und übersprang den Build. `app/docs-site/sync-docs.mjs:10` und `app/docs-site/astro.config.mjs:34` verwiesen auf das alte Repository `ErpeUser/DebateAI`; `sync-docs.mjs:72` erwartete zusätzlich `app/docs/architecture.svg`, während nur `app/docs/architecture/backchannel-architecture.svg` vorhanden war. `assemble.mjs:15-22` und der Testvertrag erwarteten mehrere nicht vorhandene Dokumente (unter anderem `api-keys.md`, `agents.md`, `audio-pipeline.md`, `DESKTOP_FINAL.md`, `CODEX_ACCEPTANCE_2026-11-12.md`, `HISTORIE.md` und `DEBATE_AI_VISION_FINAL.md`). Der Test enthielt nach dem ersten Fehler weitere alte Erwartungen (`site.test.js:196-201`, altes `/blob/master/LICENSE`). Aktive Anleitungen verwendeten `DebateAI.git`, `cd source` und `master`/`origin/master` (`app/README.md:167-179,251-253`; `app/docs/releasing.md:12-18,56-61`; `app/docs/deployment.md:216-220,373-381`), obwohl `AGENTS.md:48-49` den Public-Stand auf `ErpeUser/DebateAI-final-public`/`main` festlegte; die Quickstart-Kommandos setzten fälschlich den Clone-Root statt `app/` voraus (`app/docs/quickstart.md:60-64,122-178,201-210`) und nannten Python 3.11+, während README/Buildpfade 3.12 verlangten. `app/site/index.html:260` behauptete lokale Dokumentverarbeitung, obwohl `app/backend/app/routers/documents.py:79-100` im normalen Pfad Gemini Files nutzte. Zusätzlich widersprachen `AGENTS.md:36-38` und `README.md:18`/`app/docs/generated-workspace.md:10` beim `.git`-Recovery-Vertrag.
- **Aktueller Nachweis:** Die genannten Driftpfade wurden in `c7e94fe` auf vorhandene Dokumente, `ErpeUser/DebateAI-final-public`, `main` und den `app/`-Layoutvertrag umgestellt. Der frühere interne Orchestrierungsbericht wurde vor dem aktuellen Layout-Gate aus dem Tree entfernt; der Commit und die ausgeführten Tests sind die maßgebliche Evidenz.
- **Status:** weitgehend umgesetzt (Commit `c7e94fe`); die CI-Fehlfunktion wurde durch einen konsistenten vorhandenen Dokumentvertrag behoben. `npm test` (171 Tests), `npm run build` (20 Dokumentseiten) und der Repository-Layout-Test (11 Tests) liefen erfolgreich. Externe Veröffentlichungs-/Provider-Gates bleiben separat offen.
- **Sollzustand:** Aktive Dokumentation, Site-Tests und Sync-/Build-Skripte beziehen sich ausschließlich auf vorhandene Ziele und den kanonischen `app/`-/`main`-Stand. Historische Pfade und Produktbeschreibungen sind datiert bzw. korrekt eingegrenzt.
- **Minimalste Lösung:** Einen kanonischen Dokumentationsindex festlegen: erwartete Dateien wiederherstellen oder Sync, Assemble, Tests und Inhaltslinks auf die tatsächlich vorhandenen Dokumente umstellen; Asset-Pfad und Repository-URL gemeinsam korrigieren. Clone-/Branch-/Python-Anweisungen und lokale-vs.-Cloud-Dokumentverarbeitung synchronisieren; alte Quellen nur als historische Provenienz markieren.
- **Nutzen:** Docs-Site-Builds werden wieder ausführbar, Onboarding und Releaseanweisungen führen nicht in falsche Pfade, und Datenschutz-/Produktversprechen stimmen mit dem Laufzeitpfad überein.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Historische Provenienz, Starlight-Slugs und veröffentlichte URLs dürfen nicht versehentlich verschwinden; Sync, Assemble, Site-Test und Quickstart müssen gemeinsam angepasst werden.
- **Akzeptanzkriterium:** Erfüllt für den geprüften Stand: Link-/Pfadscan sowie `cd app/docs-site && npm test && npm run build` liefen erfolgreich; aktive Anweisungen verwenden den `app/`-/`main`-Vertrag. Externe Hosting-/Release-Claims bleiben separat offen.
- **Befundvertrauen:** **hoch**
- **Quelle:** Commit `c7e94fe`; `app/docs-site/site.test.js`; `app/docs-site/sync-docs.mjs`; `app/docs-site/assemble.mjs`; `app/docs-site/astro.config.mjs`.
### P1.7 Historische Evidenz und aktuelle CI-Aussagen konsolidieren

- **Kategorie:** **Docs-Drift**
- **Historischer Befund:** Die früher getrennten Register vermischten private `master`-/`source/`-Informationen und Prüfwerte vom 18./19. November mit als aktuell formulierten Aussagen. Die ursprünglichen Prüfdaten, Testzahlen, SHA-256-Werte und Einschränkungen stehen nun vollständig in den datierten Abschnitten [Historische Evidenz](#historische-evidenz-2026-11-18) und [Historischer Status](#historischer-status-2026-11-19) am Ende dieses Dokuments.
- **Aktuell belegte Code-Checks (Stand 20.11.2026):** Für Codecommit `b7e1b7d692034937139b23921a784c6c4e19cc98` bestand der GitHub-`tests`-Lauf `44647807154` (unter anderem 2.158 bestandene und 16 übersprungene Backend-Tests). Der Security-Lauf `44649251041` und der Docs-Site-Build `44649251028` bestanden für den späteren reinen Dokumentationsstand `a6d3ba5`. Der Structure-Lauf `44649251016` bestand beim Repository-Layout, blieb aber wegen geerbter Sentrux-Regelverstöße rot; absolute Strukturgrenzen sind damit **nicht** abgenommen. Diese Angaben sind zeitgebunden, nicht pauschal für zukünftige Commits.
- **Status:** Dokumentationskonsolidierung umgesetzt. Die historisch belegten Fakten bleiben erhalten; externe Release-/Hardware-Gates und der absolute Sentrux-Qualitätsgate bleiben offen.
- **Sollzustand:** Aktive Aussagen nennen echte Commit-SHAs, Run-/Job-IDs und Prüfzeitpunkte; historische private Git- und Hardwarestände bleiben klar vom Public-`main` getrennt.
- **Umsetzung:** Historische Einzelregister in die beiden datierten Abschnitte unten überführen, alte Dateipfade und Links ersetzen, die ursprünglichen Dateien entfernen und Docs-Site/Layout-Gates erneut prüfen.
- **Nutzen:** Ein erreichbarer Pflegeort für offene Punkte, genaue historische Prüfprotokolle und nachvollziehbare aktuelle CI-Grenzen.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Spätere Runs können Status ändern. Ein grün gelaufener Unterjob ersetzt keine separate Signatur-, Windows-GUI-, Audio- oder Produktionsabnahme.
- **Akzeptanzkriterium:** Alle historischen Hashes/Testzahlen bleiben auffindbar; keine aktiven Links auf entfernte Dateien; die Docs-Site baut, und aktuelle CI-Gates werden nach tatsächlichem Ergebnis statt pauschal als bestanden beschrieben.
- **Befundvertrauen:** **hoch**
- **Quelle:** Historische Abschnitte [18.11.](#historische-evidenz-2026-11-18) und [19.11.](#historischer-status-2026-11-19); GitHub Actions `44647807154`, `44649251041`, `44649251028`, `44649251016`.

### P1.8 Zwei Debattenrollen im Live-Modus tatsächlich aktivieren

- **Kategorie:** **VISION-GAP**
- **Istzustand:** `app/backend/app/services/agents/orchestrator.py:283-287` erlaubt im `_DEBATE_LIVE_AGENTS`-Set nur `audio_gateway`, `objection_handler` und `consolidated_analyst`. `_is_enabled` unterdrückt außerhalb dieses Sets liegende Slugs (`:934-935,1045`), obwohl `strategic_signals` separat definiert (`:704`) und als eigener Loop gestartet wird (`:1468-1469,5047+`). Die VISION verlangt in `:21-26` parallel bezogene Argument- und Strategie-Rollen.
- **Status:** teilweise implementiert; eine strategische Rolle ist im Debate-Live-Modus code-seitig ausgeschlossen.
- **Sollzustand:** Argument- und Strategie-Rolle liefern im selben aktuellen Turn-/Revisionskontext verwertbare Ergebnisse, ohne alte Ergebnisse zu überschreiben.
- **Minimalste Lösung:** Die Live-Allowlist und den Strategie-Loop in einen begrenzten, messbaren Debattenpfad integrieren; Turn-/Revision-IDs und Cancellation explizit durchreichen und die Ausgabe bei fehlendem Modell klar kennzeichnen.
- **Nutzen:** Der Kernanspruch „strategisch über den Gesprächsverlauf“ wird im Hauptszenario wirksam statt nur in optionalen Meeting-Pfaden.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Zusätzliche LLM-/CPU-Last und Latenz; die VISION fordert Ressourcenbudgets und darf die erste Antwort nicht blockieren.
- **Akzeptanzkriterium:** Ein Debate-Live-Test weist pro Turn eine Argument- und eine Strategieausgabe mit gleicher Turn-/Revisions-ID nach; veraltete Strategieergebnisse werden sichtbar verworfen.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/docs/VISION.md:21-26`; `app/backend/app/services/agents/orchestrator.py:283-287,704,934-935,1045,1468-1469,5047+`.

### P1.9 Drei aktuelle Alternativen im Standard-Live-Overlay bereitstellen

- **Kategorie:** **VISION-GAP**
- **Istzustand:** `app/frontend/src/components/DebateOverlay.tsx:42-49` leitet im Standardmodus nur `answer` und höchstens `secondary` ab. Drei `strategy_options` werden erst im optionalen `experimental_debateai`-Zweig (`:99-112`) gerendert. `app/backend/app/services/debate_settings.py:64-81` setzt `pipeline_mode` standardmäßig auf `standard`. Die VISION fordert in `:26-31` drei kurze, unterschiedliche und möglichst direkt aussprechbare Alternativen.
- **Status:** teilweise implementiert; der Standardpfad erfüllt die Drei-Karten-Anforderung nicht.
- **Sollzustand:** Der Standard-Live-Modus zeigt drei aktuelle, unterscheidbare Vorschläge, mindestens einen davon direkt sprechbar, mit sichtbarem Turn-/Revisionsbezug und Veraltungshinweis.
- **Minimalste Lösung:** Antwortvertrag und Reducer so erweitern, dass der Standardpfad drei validierte Alternativen erhält; Overlay rendert sie als gleichwertige Karten und behält den bestehenden experimentellen Pfad kompatibel.
- **Nutzen:** Der zentrale Aha-Moment ist im normalen Produktpfad verfügbar und nicht an einen optionalen Modus gebunden.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Mehr Modell-/UI-Arbeit pro Turn kann die Latenz erhöhen; Mindestlänge, Duplikatprüfung und Fallback müssen festgelegt werden.
- **Akzeptanzkriterium:** Frische Standard-Einstellungen rendern in einem Live-Test drei verschiedene Karten, mindestens eine mit sprechbarer Formulierung; UI-/Reducer-Tests prüfen Turn-/Revisionswechsel und „veraltet“.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/docs/VISION.md:26-31`; `app/frontend/src/components/DebateOverlay.tsx:42-49,99-112`; `app/backend/app/services/debate_settings.py:64-81`.

### P1.10 A/B- und Sprachlabor als zugängliches Produktfeature nachweisen

- **Kategorie:** **VISION-GAP**
- **Istzustand:** `app/frontend/src/components/AdminPanel.tsx:72-79` bietet Tabs für `agents`, `transcription`, `privacy`, `keys` und `about`, aber keinen Einstieg in das Modell-/Prompt-A/B- oder Sprachlabor. Eine separate Calibration-API (`app/backend/app/routers/calibration.py:1-15`) ersetzt keinen zugänglichen Blindvergleich im Hauptprodukt. Die VISION fordert in `:108-113` ein A/B-Labor für alle Nutzer und ein reproduzierbares Sprachlabor.
- **Status:** teilweise/strukturell nicht nachweisbar im Hauptprodukt.
- **Sollzustand:** Nutzer können identische Debattenfälle blind A/B bewerten, erst danach Modell-/Promptdaten sehen und Sprachmodelle mit derselben deutschen Referenz messen.
- **Minimalste Lösung:** Einen UI-Einstieg mit identischem Input, zufälliger Reihenfolge, Reveal nach Bewertung, Latenz-/Kostenmetadaten und reproduzierbarer Testfallverwaltung an die vorhandene Calibration-API anbinden.
- **Nutzen:** Qualitätsaussagen werden für Nutzer nachvollziehbar und das Kernfeature ist nicht nur ein Entwickler-/API-Pfad.
- **Aufwand:** **L**
- **Risiken und Abhängigkeiten:** Blindheit, Datensatztrennung und menschliche Auswertung müssen gegen Trainingsdatenleck und Live-Latenz abgesichert werden.
- **Akzeptanzkriterium:** Ein UI-Test führt einen identischen Fall durch A/B-Blinddarstellung, Bewertung, Reveal und Export; ein Sprachtest zeigt WER/CER/RTF mit derselben Referenzaufnahme.
- **Befundvertrauen:** **mittel-hoch**
- **Quelle:** `app/docs/VISION.md:108-113`; `app/frontend/src/components/AdminPanel.tsx:72-79`; `app/backend/app/routers/calibration.py:1-15`.

### P1.11 Local-First-Textpfad und Default-Dokumentation synchronisieren

- **Kategorie:** **VISION-GAP**
- **Istzustand:** Die VISION fordert in `:53-63` lokale ASR plus lokales Textmodell als latency-kritischen Standard. `app/backend/app/config.py:92` setzt zwar `local-whisper-base` für Batch-ASR, `DEFAULT_MODEL_RECOMMENDATION_ROLES` (`:191-215`) empfiehlt für Textrollen ausschließlich Gemini/GPT; die Local-Registry-Einträge (`:452-525`) sind ASR, der lokale Textpfad `openai-compatible` (`:540-550`) erfordert eine separate Endpoint-Konfiguration. `app/docs/configuration.md:358` dokumentiert zusätzlich einen anderen Default (`gemini-3.5-flash-lite`).
- **Status:** teilweise implementiert und dokumentarisch widersprüchlich; ein lokaler Endpoint ist möglich, aber kein nachgewiesener Standardpfad.
- **Sollzustand:** Eine Neuinstallation nutzt für den zeitkritischen Textpfad einen konfigurierten lokalen Endpoint oder blockiert externe Aufrufe transparent, bis der Nutzer sie ausdrücklich aktiviert; Dokumentation und Code nennen denselben Default.
- **Minimalste Lösung:** Setup-Assistent, Seed/Empfehlungen, Konfigurationsdoku und Tests auf eine verbindliche Provider-/Modellmatrix ausrichten; Cloud nur nach sichtbarer Aktivierung einordnen.
- **Nutzen:** Keine unerwartete Cloud-Nutzung und belastbare Übereinstimmung zwischen Vision, Setup und tatsächlichem Laufzeitverhalten.
- **Aufwand:** **L**
- **Risiken und Abhängigkeiten:** Hardware-/Modellverfügbarkeit, Kosten- und Datenschutzdialoge sowie bestehende Nutzerkonfigurationen müssen migrationssicher bleiben.
- **Akzeptanzkriterium:** Frische Installation ohne Cloud-Key führt nach Setup zu einem lokalen Textendpunkt oder einem klaren Blockierungsstatus; Provider-Spy-Tests beweisen, dass kein impliziter Remote-Textaufruf erfolgt.
- **Befundvertrauen:** **mittel-hoch**
- **Quelle:** `app/docs/VISION.md:53-63`; `app/backend/app/config.py:92,191-215,452-525,540-550`; `app/docs/configuration.md:358`.

### P1.12 PII-Schutz auf alle ausgewählten Chat-Sitzungen ausdehnen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/app/routers/chat.py:223-242` akzeptiert bis zu 20 `session_ids`, schützt aber jede Nutzernachricht ausschließlich mit `shield.protect_text(db, body.session_ids[0], ...)`. `shield.session_roster` ist in `app/backend/app/services/pii/shield.py:191-207` strikt sitzungsgebunden. Ein geschützter Name/Term, der nur in Session 2 bekannt ist, kann damit in einer Multi-Session-Frage vor dem Provider-Aufruf ungeschützt bleiben.
- **Aktueller Nachweis:** `9a72a2a` verwendet `protect_text_for_sessions`; Roster-Einträge aller ausgewählten Sitzungen werden in einem primären, deterministischen Vault-Namespace geschützt.
- **Status:** umgesetzt (Commit `9a72a2a`); der Chat-Roster wird über alle ausgewählten Sitzungen vereinigt und Regressionstests decken den zweiten Sitzungswert ab. Der aktuelle CI-Testlauf `44647807154` auf `b7e1b7d` lief mit installierten Backend-Abhängigkeiten erfolgreich durch (2.158 Tests bestanden, 16 übersprungen); der Multi-Session-Test ist darin enthalten.
- **Sollzustand:** Jede ausgewählte Session trägt ihren Vault-/Roster-Schutz zum gemeinsamen Prompt bei, ohne Token-Namensräume oder Reveal-Zuordnung zu vermischen.
- **Minimalste Lösung:** Einen unionsweiten, read-only Roster/Vault-Scope für die User-Nachricht verwenden oder Multi-Session-Chat auf einen gemeinsamen Schutzscope begrenzen; Namespace-/Reveal-Tests ergänzen.
- **Nutzen:** Verhindert, dass ein Klartextwert aus einer zweiten ausgewählten Sitzung an ein externes Modell gelangt.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Token-Kollisionen, Rückauflösung und Transaktionsdauer über bis zu 20 Sitzungen müssen kontrolliert werden.
- **Akzeptanzkriterium:** `test_multi_session_protection_uses_the_union_of_selected_rosters` und `ChatBriefingOwnerTests.test_multi_session_chat_protects_against_all_selected_sessions` bilden den Session-2-Fall ab; der CI-Lauf `44647807154` bestätigt den vollständigen Backend-Testlauf. Ein Provider-E2E-Test mit echten externen Antworten bleibt bewusst außerhalb dieses lokalen Vertrags.
- **Befundvertrauen:** **hoch** für die Code- und Regressionsevidenz, **mittel-hoch** für die weiterhin nicht real-providerbasierte E2E-Abdeckung.
- **Quelle:** `app/backend/app/routers/chat.py:223-242`; `app/backend/app/services/pii/shield.py:191-207,248-268`.

### P1.13 PostgreSQL-Grenztests in CI tatsächlich ausführen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/tests/test_insight_commit_postgres.py` und `test_provisional_transcripts_postgres.py` sind über `skipUnless` an PostgreSQL-Umgebungsvariablen gebunden. `.github/workflows/tests.yml:30-65` startet keinen PostgreSQL-Service und setzt keine `DEBATEAI_TEST_POSTGRES_*`-Variablen. Ein grüner Backend-Job belegt damit die SQLite-/Mock-Abdeckung, nicht die DB-Constraints, Concurrency- und Migrationsgrenzen.
- **Status:** bestätigt; die Tests sind im Standard-CI ohne explizite PostgreSQL-Bereitstellung überspringbar.
- **Sollzustand:** Die produktionsnahe PostgreSQL-Schicht wird in einem isolierten CI-Job oder sichtbar markierten Nightly-Lauf mit Migrationen und den beiden Testdateien geprüft.
- **Minimalste Lösung:** Einen versionierten PostgreSQL-Service/Container mit Testdatenbank und expliziten Variablen ergänzen; Skip-Zählung im Log als Gate sichtbar machen.
- **Nutzen:** Datenintegritäts- und Race-Bedingungen werden vor Release geprüft statt nur simuliert.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Runner-Zeit, DB-Version und Test-Isolation; Zielcluster-/Produktionsdaten dürfen nicht verwendet werden.
- **Akzeptanzkriterium:** CI-Log weist für beide PostgreSQL-Testdateien ausgeführte Tests und Migrationen ohne Skip aus; Fehler blockieren den markierten DB-Gate-Job.
- **Befundvertrauen:** **hoch**
- **Quelle:** `.github/workflows/tests.yml:30-65`; `app/backend/tests/test_insight_commit_postgres.py:18-28`; `app/backend/tests/test_provisional_transcripts_postgres.py:16+`.

### P2.6 Struktur-CI darf absolute Sentrux-Verstöße nicht als grün verschleiern

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand (historischer Ausgangsbefund am Audit-HEAD `faa68958`):** `.github/workflows/structure.yml` markierte den `sentrux`-Job mit `continue-on-error: true`. Im Lauf `44628692440` schlug der `Rules check`-Schritt fehl; die Auswertung meldete neben `max_file_lines` auch `max_cycles`, `max_cc` und `max_fn_lines`. Der Gesamtworkflow blieb trotzdem `success`, weil der separate Repository-Layout-Job erfolgreich war.
- **Aktueller Nachweis:** Seit `9a72a2a` enthält der Job kein `continue-on-error`; die Rules-Check-Allowlist entscheidet damit über den Jobstatus.
- **Status:** umgesetzt im Workflow (Commit `9a72a2a`); `continue-on-error` wurde entfernt. Im aktuellen Remote-Run `44647805682` auf `b7e1b7d` bestand der Repository-Layout-Job, während der Sentrux-Rules-Job wegen geerbter `max_cycles`, `max_cc`, `max_fn_lines` und zusätzlicher großer Dateien blockierte; der Vergleichsschritt meldete zugleich „No degradation detected“.
- **Sollzustand:** Policy und Status unterscheiden klar zwischen blockierendem Layout-Gate und zugelassener struktureller Schuld; ein unerwarteter Verstoß darf nicht wie ein vollständig grüner Qualitätslauf erscheinen.
- **Minimalste Lösung:** Entweder die zugelassenen Regeln als versionierte Allowlist im Run-Summary ausweisen oder Sentrux bei neuen/unerwarteten Befunden blockierend machen; FINAL_STATUS darf nur den differenzierten Status melden.
- **Nutzen:** CI-Signale werden für Review und Release nicht überinterpretiert.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Eine Policy-Änderung kann bestehende Branches blockieren; Baseline- und Lockfile-Ausnahmen müssen reproduzierbar bleiben.
- **Akzeptanzkriterium:** Der Workflow behandelt den Job-Fehler nicht mehr als grünen Gesamtstatus; die vorhandene Rules-Check-Allowlist bleibt der einzige zulässige Ausnahmeweg. Run `44647805682` bestätigt diese Policy mit einem sichtbaren `failure` für den Sentrux-Job und einem erfolgreichen Layout-Job.
- **Befundvertrauen:** **hoch**
- **Quelle:** `.github/workflows/structure.yml` (`sentrux`-Job und Rules-Check); Run `44647805682`, Jobs `135994751160` (Layout, success) und `135994751783` (Sentrux, failure).

### P2.7 Produktionsstart nicht standardmäßig mit Uvicorn-Reload ausführen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** Historisch interpretierte `app/backend/scripts/start_backend.py:25` ein fehlendes `BACKEND_RELOAD` als `true` und fügte dann `--reload` hinzu. Compose überschreibt dies zwar mit `BACKEND_RELOAD:-false`, ein direkter oder vergessener nativer Start aus Runbooks war damit watcher-/restart-anfällig.
- **Aktueller Nachweis:** `fa165c6` setzt den nativen Default auf `127.0.0.1` und `BACKEND_RELOAD=false`; die Compose- und Token-Regressionsprüfungen sind in `test_start_backend.py` enthalten.
- **Status:** umgesetzt (Commit `fa165c6`); native Starts verwenden Loopback und `BACKEND_RELOAD=false` als Default. Compose behält den explizit token-geschützten Container-Bind bei.
- **Sollzustand:** Produktions- und native Starts laufen ohne Reload; Development aktiviert Reload explizit.
- **Minimalste Lösung:** Default auf `false` setzen und die lokalen Entwicklungsbefehle um `BACKEND_RELOAD=true` ergänzen.
- **Nutzen:** Vermeidet unnötige Ressourcenlast und unbeabsichtigte Sessionabbrüche bei Quelldateiänderungen.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Lokale Entwickler erwarten möglicherweise das bisherige Verhalten; Quickstart und Compose müssen synchron bleiben.
- **Akzeptanzkriterium:** Erfüllt durch `python -m unittest app.backend.tests.test_start_backend -v` (6/6). Start ohne Env enthält kein `--reload`; der explizite Reload-Pfad bleibt getestet.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/backend/scripts/start_backend.py:18-25`; `app/docker-compose.yml` (BACKEND_RELOAD-Override).

### P2.8 Große Chat- und PII-Reveal-Antworten begrenzen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/app/routers/chat.py:184-215` lädt für bis zu 20 Sitzungen vollständige Speaker-, TranscriptEntry- und Insight-Mengen in Python, bevor `build_chat_prompt` auf 60.000 Zeichen kürzt. Zusätzlich puffert `app/backend/app/services/pii/reveal_middleware.py:49-79` jede session-scoped JSON-Antwort vollständig in `body_parts`, bevor die Reveal-Verarbeitung beginnt; ein Größenlimit oder Streaming-/Pagination-Schutz ist nicht erkennbar.
- **Status:** teilweise umgesetzt (Commit `9a72a2a`); der Reveal-Pfad weist Antworten über 8 MiB kontrolliert mit HTTP 413 zurück. SQL-Limits/Pagination und ein Lastbudget für den Chat bleiben offen.
- **Sollzustand:** Datenbankabfrage, Promptaufbau und PII-Reveal sind bei großen Sitzungen begrenzt, paginiert oder liefern kontrollierte 413-/Truncation-Signale.
- **Minimalste Lösung:** Brief-first/Latest-Limits bereits in SQL anwenden, Transkriptseiten explizit begrenzen und den Reveal-Pfad mit einer definierten Maximalgröße versehen; große Antworten nicht doppelt vollständig im Worker halten.
- **Nutzen:** Stabilere Antwortzeiten und geringeres OOM-/Worker-Restart-Risiko bei langen Sitzungen oder parallelen Anfragen.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Prompt-Vollständigkeit, Export-/Reveal-Korrektheit und API-Kompatibilität müssen mit den Limits abgestimmt werden.
- **Akzeptanzkriterium:** Lasttest mit 20 langen Sitzungen bleibt unter einem festgelegten RAM-/Latenzbudget oder wird kontrolliert paginiert/abgelehnt; PII-Reveal und Promptpriorität bleiben korrekt.
- **Befundvertrauen:** **hoch** für den Codepfad, **mittel** für die konkrete Betriebswirkung.
- **Quelle:** `app/backend/app/routers/chat.py:184-215`; `app/backend/app/services/pii/reveal_middleware.py:49-79`.

### P2.9 Accessibility-Namen und Dialogfokus vervollständigen

- **Kategorie:** **QUICK-WIN**
- **Istzustand:** Bestätigt: `app/frontend/src/components/PiiShieldCard.tsx:213-221,287-294` rendert Eingabefeld und Test-Textarea ohne sichtbares/programmatisch verknüpftes Label, `id`/`htmlFor` oder `aria-label`; die Kategorieauswahl daneben ist benannt. `app/frontend/src/components/ConfirmProvider.tsx:75-113` setzt `role="dialog"`/`aria-modal`, fokussiert beim Öffnen nur den Bestätigungsbutton und gibt den Fokus beim Schließen nicht an den Trigger zurück; ein Tab-Fokus-Trap fehlt.
- **Status:** umgesetzt im Code (Commit `9a72a2a`); Eingabefelder besitzen jetzt stabile Namen, der Bestätigungsdialog trappt Tab-Fokus und stellt den Auslöserfokus wieder her. Axe-/Browserausführung war wegen fehlender Frontend-Abhängigkeiten lokal nicht möglich.
- **Sollzustand:** Jedes Eingabefeld besitzt einen stabilen zugänglichen Namen; Dialogfokus bleibt innerhalb des Dialogs und kehrt nach Schließen zum Auslöser zurück.
- **Minimalste Lösung:** Deutsche `<label>`-Elemente mit `htmlFor` oder gleichwertige ARIA-Namen ergänzen und einen kleinen Focus-Trap-/Restore-Mechanismus für Confirm/Notice einführen.
- **Nutzen:** Verhindert unbenannte Controls und Fokusverlust in zentralen Datenschutz-/Bestätigungsflüssen.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Bestehende Tastaturkürzel, Escape-/Backdrop-Verhalten und DOM-Tests müssen unverändert deterministisch bleiben.
- **Akzeptanzkriterium:** DOM-Vertrag ist umgesetzt; der vorhandene Frontend-Build-/Axe-Lauf muss mit installierten Dependencies noch bestätigen, dass Tab, Escape und Focus-Restore im Browser unverändert funktionieren.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/frontend/src/components/PiiShieldCard.tsx:213-221,222-231,287-294`; `app/frontend/src/components/ConfirmProvider.tsx:75-113`.


### P1.14 Löschpfad für externe, lokale und Browser-Artefakte vollständig machen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** Bestätigter Codepfad: `app/backend/app/routers/sessions.py:232-248` löscht Session-/Document-Zeilen per Cascade (`app/backend/app/models.py:33`), lokale Session-Audios und den Shield-Zustand, sammelt aber die Gemini-File-URIs nicht und ruft `delete_uploaded_file` nicht auf. Das ist bei Einzel-Dokumentlöschung in `app/backend/app/routers/documents.py:117-126` vorgesehen, beim Session-Löschen jedoch nicht. Zusätzlich legt `app/frontend/src/components/PostCall/MeetingChat.tsx:76-80,136` Chatverläufe in `window.sessionStorage` ab und entfernt sie nur über „Reset“; `app/frontend/src/App.tsx:770-806` löscht beim Session-Delete den Browsercache nicht.
- **Aktueller Nachweis:** `9a72a2a` sammelt vor der Cascade alle Gemini-URIs, ruft nach dem lokalen Commit den Provider-Delete auf und entfernt den Browser-Chatcache sowie WebSocket-/Job-Referenzen.
- **Status:** teilweise umgesetzt (Commit `9a72a2a`): Session-Löschen sammelt Gemini-URIs und ruft nach dem lokalen Commit `delete_uploaded_file` auf, entfernt Browser-Chatcache sowie Prozess-Journal-/Job-Referenzen. Provider-Retry-/Outbox-Status bleibt offen; `delete_uploaded_file` arbeitet weiterhin best effort.
- **Sollzustand:** Session-Löschung entfernt oder queued alle zugehörigen externen Dateien, lokale Artefakte und clientseitige Chatkopien; fehlgeschlagene externe Löschungen bleiben sichtbar und wiederholbar.
- **Minimalste Lösung:** Vor der DB-Cascade URIs und lokale Pfade erfassen, eine idempotente Cleanup-/Outbox-Operation mit Retry und Auditstatus ausführen und den Session-Cache im Frontend beim Löschen leeren oder in einem Privacy-Modus deaktivieren.
- **Nutzen:** Verhindert unbeabsichtigte PII-/Kosten-Retention bei Sitzungsende und macht Löschfehler nachvollziehbar.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Provider-Delete-Limits, Retry-/Idempotenzregeln und Offline-Löschung müssen mit Datenschutz- und Exportverträgen abgestimmt werden.
- **Akzeptanzkriterium:** Codepfad und isolierter Frontend-Storage-Test sind vorhanden; ein Integrationstest mit echtem Provider-Delete und sichtbarem Retry-/Outbox-Status bleibt erforderlich.
- **Befundvertrauen:** **hoch** für den Codepfad, **mittel** für die externe Providerwirkung.
- **Quelle:** `app/backend/app/routers/sessions.py:232-248`; `app/backend/app/routers/documents.py:117-126`; `app/backend/app/models.py:33`; `app/frontend/src/components/PostCall/MeetingChat.tsx:76-80,136`; `app/frontend/src/App.tsx:770-806`.

### P1.15 Live-State und WebSocket-Journale für Multiworker-Betrieb absichern

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** Bestätigter Architekturpfad für mehr als einen Uvicorn-Worker: `app/backend/app/services/agents/orchestrator.py:718-745` hält `_live_orchestrators` im Prozessspeicher, `app/backend/app/services/ws_event_stream.py:268-282` `_journals` ebenfalls. REST-/WebSocket-Pfade (`app/backend/app/routers/sessions.py:78-80,130-136`; `transcripts.py:22,121`; `debate_review.py:28,202`) greifen auf denselben Prozesszustand zu. Ein WS-Worker A kann deshalb den Live-State für REST-Worker B nicht sehen; Overlay-, Context- und Directive-Operationen werden dort zu No-ops oder veralteten Antworten.
- **Status:** bestätigt für einen Multiworker-Start; ob der produktive Deploymentvertrag mehrere Worker zulässt, ist separat zu verifizieren.
- **Sollzustand:** Live-State, Journale und Steuerbefehle funktionieren deterministisch über Workergrenzen oder der Startvertrag erzwingt nachweislich einen Single-Worker-/Sticky-Session-Betrieb.
- **Minimalste Lösung:** Gemeinsamen Redis-/DB-Journal- und State-Adapter mit Session-/Revision-IDs einführen oder Multiworker im produktiven Start explizit blockieren und den Grund dokumentieren.
- **Nutzen:** Verhindert stille Ausfälle von Overlay, Live-Transkript und Steuerung beim Skalieren oder hinter einem Load-Balancer.
- **Aufwand:** **L**
- **Risiken und Abhängigkeiten:** Event-Reihenfolge, Locking, Backpressure und Persistenzkosten; Single-Worker als Zwischenlösung begrenzt Skalierung.
- **Akzeptanzkriterium:** Ein Zwei-Worker-Integrationstest sendet WS-Ereignis und REST-PATCH über unterschiedliche Worker und beobachtet denselben Session-/Revisionsstand sowie korrektes Overlay-Verhalten.
- **Befundvertrauen:** **hoch** für die In-Process-Zustände, **mittel-hoch** für die betriebliche Auswirkung.
- **Quelle:** `app/backend/app/services/agents/orchestrator.py:718-745`; `app/backend/app/services/ws_event_stream.py:268-282`; `app/backend/app/routers/sessions.py:78-80,130-136`; `app/backend/app/routers/transcripts.py:22,121`; `app/backend/app/routers/debate_review.py:28,202`.

### P1.16 LAN-Origin-Vertrauen und Bind-Defaults explizit absichern

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/app/services/request_guard.py:96-114,121-146` akzeptiert private/link-local IP-Originen anhand syntaktischer Prüfung; `app/backend/scripts/start_backend.py:14-30` bindet direkt gestartet standardmäßig auf `0.0.0.0` und aktiviert ohne Gegenvariable `--reload`. Damit kann ein direkter, nicht auf Loopback begrenzter Start im privaten LAN Requests mit fremdem privatem Origin als vertrauenswürdig behandeln, sofern kein Instance-Token greift. Das ist eine konkrete Sicherheitsgrenze; die vorgesehene LAN-Nutzung und der Tokenzwang müssen im Deployment noch verifiziert werden.
- **Aktueller Nachweis:** `fa165c6` bindet native Starts standardmäßig an Loopback, deaktiviert Reload und verlangt bei explizitem Nicht-Loopback-Bind ein Instance-Token. Die bestehende Origin-Allowlist bleibt unverändert.
- **Status:** teilweise umgesetzt (Commit `fa165c6`): Loopback-/Reload-Defaults und Tokenpflicht für explizite Nicht-Loopback-Binds sind im nativen Startvertrag getestet. Die vollständige Origin-Allowlist-/LAN-Bedrohungsprüfung bleibt offen.
- **Sollzustand:** Nicht-Loopback-Zugriffe benötigen einen expliziten Allowlist-/Tokenpfad; Loopback-Desktop- und bewusst freigegebene LAN-Szenarien bleiben möglich. Reload ist nur Development-Opt-in.
- **Minimalste Lösung:** Bind-Adresse und Origin-Allowlist standardmäßig restriktiv setzen, Instance-Token für jeden nicht lokalen Origin erzwingen und `BACKEND_RELOAD` auf ein explizites Development-Opt-in umstellen; Startvertrag und Tests anpassen.
- **Nutzen:** Reduziert das Risiko zustandsändernder Requests aus fremden privaten Netzen und verhindert versehentliche Reload-/Watcher-Starts.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Bestehende Remote-/Overlay-Szenarien, Browser-Origin-Semantik und Nutzerkonfigurationen; LAN-Kompatibilität muss mit expliziter Freigabe getestet werden.
- **Akzeptanzkriterium:** Ein fremder privater Origin erhält ohne gültigen Token 403, Loopback bleibt funktionsfähig, explizite Allowlist funktioniert, und ein Start ohne Env enthält kein `--reload`.
- **Befundvertrauen:** **mittel-hoch**; die Codeentscheidung ist belegt, die reale Angriffsfläche hängt vom Deployment ab.
- **Quelle:** `app/backend/app/services/request_guard.py:96-146`; `app/backend/scripts/start_backend.py:14-30`; bestehender Punkt P2.7.

### P2.10 Listen-, Transcript- und Knowledge-APIs mit Cursor-Pagination und Limits versehen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** Mehrere GET-Endpunkte liefern ungebremste Vollmengen: `app/backend/app/routers/sessions.py:72-75` alle Sessions, `:141-148` alle Segmente, `app/backend/app/routers/transcripts.py:56-72` alle Transcript-Einträge/Revisionsdaten, `questions.py:14-19` alle Fragen und `knowledge.py:59-72,128-136` alle Quellen/Records. `app/frontend/src/hooks/useSession.ts:116-142` startet zusätzlich mehrere Voll-GETs pro ausgewählter Session.
- **Status:** begründete Optimierung; ein Produktionsausfall ist nicht bewiesen, die lineare Payload-/DB-/Renderlast ist im Code sichtbar.
- **Sollzustand:** Listen haben stabile Cursor-/Limit-Parameter, maximale Antwortgrößen und lazy geladene Details; alte Clients bleiben über begrenzte Defaults kompatibel.
- **Minimalste Lösung:** Cursor oder `limit`/`before` mit sicheren Obergrenzen ergänzen, nach Session-/Zeitindex sortieren und Frontend auf erste Seite plus Detailabruf umstellen.
- **Nutzen:** Kontrollierbare Latenz und Speichernutzung bei lang lebenden Workspaces, großen Transkripten und vielen Sessions.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Sortier-/Cursorstabilität, Exportvollständigkeit und API-Kompatibilität; Datenbankindizes müssen geprüft werden.
- **Akzeptanzkriterium:** Eine Fixture mit 10.000 Sessions und 100.000 Transcriptzeilen bleibt mit Seitenabruf unter festgelegtem p95-/Heap-Budget; UI lädt initial nur die erste Seite und kann vollständig weiterblättern.
- **Befundvertrauen:** **hoch** für den API-Pfad, **mittel** für die Betriebswirkung.
- **Quelle:** `app/backend/app/routers/sessions.py:72-75,141-148`; `app/backend/app/routers/transcripts.py:56-72`; `app/backend/app/routers/questions.py:14-19`; `app/backend/app/routers/knowledge.py:59-72,128-136`; `app/frontend/src/hooks/useSession.ts:116-142`.

### P2.11 Parallele Migrationsstarts mit Locking verifizieren

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/app/main.py:411-442` führt `create_all`/rohe `ALTER`-Schritte sowie Alembic-Stamp/Upgrade innerhalb jedes App-Lifespans aus. Ein Datenbank-Advisory-Lock oder ein anderer Single-Runner-Schutz ist im geprüften Pfad nicht nachweisbar; bei parallelem Start mehrerer Worker können doppelte Änderungen oder konkurrierende Stamps entstehen.
- **Aktueller Nachweis:** Der aktuelle Remediation-Stand serialisiert die komplette Schema-Sequenz auf PostgreSQL mit `pg_advisory_lock(hashtext('debateai.schema'))`; SQLite bleibt beim bestehenden lokalen Pfad.
- **Status:** teilweise umgesetzt; der PostgreSQL-Lock ist im Code vorhanden, ein Zwei-Worker-Startup-Test auf einer isolierten Datenbank fehlt weiterhin.
- **Sollzustand:** Genau ein idempotenter Migrationsrunner arbeitet pro Datenbank; parallele App-Starts warten oder erkennen den aktuellen Head ohne Duplicate-/Lock-Fehler.
- **Minimalste Lösung:** Migrationen aus dem Lifespan in einen expliziten Job verschieben oder per DB-Advisory-Lock serialisieren; Startup-/Legacy-Matrix testen.
- **Nutzen:** Verhindert schwer reproduzierbare Startfehler und Schema-Halbzustände beim Skalieren oder bei Recovery.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Deployment-Reihenfolge, SQLite-Kompatibilität und bestehende Legacy-Upgrades.
- **Akzeptanzkriterium:** Zwei parallele Starts auf frischer und Legacy-Datenbank enden ohne Duplicate-/Lock-Fehler, beide sehen exakt denselben Alembic-Head und ein fehlgeschlagener Runner bleibt sichtbar.
- **Befundvertrauen:** **mittel**
- **Quelle:** `app/backend/app/main.py:411-442`; Alembic-Migrationspfad; PostgreSQL-Gate P1.13.

### P2.12 Prozessweite Journale und PII-Scrub-Indizes begrenzen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** Bestätigter Codepfad ohne erkennbaren Lifecycle: `app/backend/app/services/ws_event_stream.py:268-282` hält globale `_journals`; ein `SessionEventJournal` speichert bis zu 512 Events und 512 State-Events (`:64-82,123-128`). `app/backend/app/services/pii/ws.py:120-131` räumt beim WebSocket-Schließen Buffer und Tasks, aber nicht das globale Journal auf. Zusätzlich halten `app/backend/app/services/pii/vault.py:99-117` globale `_plaintext_seen`-Werte und `app/backend/app/services/pii/redaction.py:39-40,73-90` `_known`-Secrets prozessweit; `vault.forget(session_id):293-297` invalidiert nur den DB-Transaktionscache. `app/backend/app/services/transcription_jobs.py:91-130` hält abgeschlossene/fehlgeschlagene Jobobjekte ebenfalls ohne TTL im globalen `_jobs`.
- **Aktueller Nachweis:** `9a72a2a` ergänzt beim Session-Delete `forget_session` für `_journals` und `_jobs`; Vault-/Redaction-Indizes bleiben als separater TTL-/LRU-Restpunkt offen.
- **Status:** teilweise umgesetzt (Commit `9a72a2a`): Session-Löschen entfernt jetzt das globale WebSocket-Journal und den Transcription-Job-Eintrag. Globale Vault-/Redaction-Scrub-Indizes besitzen weiterhin keinen sessionweisen TTL-/LRU-Lifecycle; Langzeitwirkung bleibt zu messen.
- **Sollzustand:** Journale, Scrub-Indizes und Jobstatus haben einen begrenzten, sessionbewussten Lebenszyklus mit TTL/LRU oder persistiertem Replay; Session-Löschung entfernt sensible Indizes, ohne zulässiges Reconnect-Replay zu brechen.
- **Minimalste Lösung:** TTL/LRU- und Session-Cleanup für globale Strukturen ergänzen, Größen-/Alter-Metriken ausgeben und Löschpfade mit Egress-Scrubbing sowie P1.14 koordinieren; bei notwendigem Replay auf DB/Redis ausweichen.
- **Nutzen:** Begrenzt Prozessspeicher und die Lebensdauer sensibler Klartext-/Tokenreferenzen und macht Multi-Session-/Multiworker-Verhalten kontrollierbarer.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Zu frühes Entfernen kann Reconnects, PII-Egress-Scrubbing oder Debuggability beeinträchtigen; TTL, Replay-Fenster und Datenschutzretention müssen gemeinsam festgelegt werden.
- **Akzeptanzkriterium:** Ein Langzeittest mit 10.000 abgeschlossenen Sessions hält RAM und globale Indexgrößen unter einem definierten Budget; Session-Löschung entfernt die zugehörigen PII-Indizes, und ein zulässiger Reconnect erhält den vereinbarten Event-/Statusstand.
- **Befundvertrauen:** **hoch** für die globalen Strukturen, **mittel** für die Betriebswirkung.
- **Quelle:** `app/backend/app/services/ws_event_stream.py:64-82,123-128,268-282`; `app/backend/app/services/pii/ws.py:120-131`; `app/backend/app/services/pii/vault.py:99-117,293-305`; `app/backend/app/services/pii/redaction.py:39-40,73-90`; `app/backend/app/services/transcription_jobs.py:91-130`; P1.14.
### P3.4 Abhängigkeiten und Modulgrenzen mit bewusst begrenzten Static-Analysis-Gates erfassen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** Das Repository enthält mehrere JavaScript-/TypeScript-Projekte (`app/frontend`, `app/docs-site`, `app/desktop/chatgpt_oracle`) und Python-Abhängigkeitsdateien; der Backend-Orchestrator umfasst über 5.000 Zeilen (`app/backend/app/services/agents/orchestrator.py`) und P2.1 erfasst bereits Ruff-/Duplikatlast. Ein reproduzierbarer Baseline-Report für ungenutzte Abhängigkeiten und Modulzyklen ist nicht nachweisbar.
- **Status:** begründete Optimierung, kein bestätigter ungenutzter Dependency-Befund.
- **Sollzustand:** Ein versionierter Baseline-Report trennt echte Produktionsabhängigkeiten von dynamischen/Generator-/Release-Einstiegspunkten und macht neue Zyklen oder ungenutzte Imports im Änderungsumfang sichtbar.
- **Minimalste Lösung:** Read-only-Baseline mit Knip (JS/TS-Dateien/Dependencies), deptry (Python-Missing/Unused/Transitive) und dependency-cruiser (JS/TS-Zyklen/Boundary-Regeln) erstellen; Konfiguration für dynamische Imports und generierte Pfade dokumentieren. Keine Gate-Verschärfung ohne bereinigte Baseline.
- **Nutzen:** Weniger tote Abhängigkeiten, frühere Architekturdrift-Erkennung und kleinere, nachvollziehbare Refactorings.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** False Positives durch dynamische Imports, Calibration-/Release-Einstiegspunkte und zusätzliche CI-Zeit; Lizenz- und Regelwerksprüfung vor produktivem Gate.
- **Akzeptanzkriterium:** Baseline ist im Repository dokumentiert, alle Findings sind triagiert, geänderte Dateien erzeugen keine untriagierten neuen Zyklen/Unused-Dependency-Befunde; ein Report nennt explizite Ausnahmen.
- **Befundvertrauen:** **hoch** als Tool-/Prozesschance, nicht als Defekt.
- **Quelle:** `app/frontend/package.json`; `app/docs-site/package.json`; `app/desktop/chatgpt_oracle/package.json`; `app/backend/requirements*.txt`; `app/backend/app/services/agents/orchestrator.py`; offizielle Dokumentation: https://knip.dev/explanations/how-knip-works, https://deptry.com/rules-violations/, https://github.com/sverweij/dependency-cruiser.
