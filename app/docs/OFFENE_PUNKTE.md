# DebateAI – Offene Punkte

Stand: 2026-11-19. Priorisierung nach P0–P3. Ein Punkt bleibt offen, wenn der aktuelle Tree, ein Acceptance-Bericht oder ein erreichbarer GitHub-Nachweis ihn nicht abschließend belegt. Historische Erledigung wird nicht als aktuelle Abnahme ausgegeben.

## P0 – vor einer belastbaren Produkt- oder Releasefreigabe

### P0.1 GitHub Actions tatsächlich ausführen

- **Problem:** Viele PR- und Master-Läufe endeten mit fehlenden Runner-Schritten, steps:null, 404-Logs oder Account-/Billing-Limit. Das ist kein grüner Test.
- **Status:** offen/blockiert; PR #24 nennt Billing-/Spending-Limit und Regeln-403 ausdrücklich.
- **Nächste Handlung:** Runner/Billing klären, Workflow-Trigger und Permissions prüfen, vollständige Jobs auf dem aktuellen Master oder einem exakt reproduzierbaren Branch starten.
- **Fertigstellungsnachweis:** sichtbare erfolgreiche Jobs für Backend, Frontend, Desktop, Docs/Worker, Security und Release-Contracts inklusive Logs und Commit-SHA.
- **Quelle:** PRs #3, #6, #8, #18, #24; app/docs/FINAL_STATUS_AND_OPEN_ITEMS.md; app/docs/EVIDENCE.md.

### P0.2 Signiertes produktives Windows-Release

- **Problem:** Authenticode ist im aktuellen Beleg NotSigned. Der Release-/R2-/Download-/DNS-/Access-Pfad und ein echter Hold-Commit sind nicht produktiv nachgewiesen.
- **Status:** Bundle-/Hash-/Rollback-Smokes vorhanden; Signatur, Operatorfreigabe und produktiver Download offen.
- **Nächste Handlung:** Zertifikat/Remote-Signing, Hold-Commit, Release-Manifest, R2/Access/DNS und Signaturprüfung auf sauberem Windows durchführen; keine Testfreigabe mit unsignierter EXE.
- **Fertigstellungsnachweis:** signierte EXE und ZIP, Zertifikatskette/Thumbprint, reproduzierbare Hashes, veröffentlichter Download, Update und erzwungener Rollback von einem frischen Client.
- **Quelle:** app/docs/EVIDENCE.md; app/docs/releasing.md; GitHub-Release v0.6.6 mit ausdrücklich offenen Signatur-/Hardware-Gates.

### P0.3 Reale Windows-/Audio-/GUI-/Provider-Abnahme

- **Problem:** Headless-Health, lokale ASR und Testlabor wurden nachgewiesen; echter 120+-Sekunden-Mikrofon-/WASAPI-/System-Audiolauf, GUI/WebView2/DPI, Gerätewechsel, Langzeitsitzung und reale Provider-Logins fehlen.
- **Status:** offen; Release v0.6.6 nennt A06, Hardware/DPI und externe Rollback ausdrücklich als Grenzen.
- **Nächste Handlung:** frisches Windows-Gerät mit realem Mikrofon und Loopback, Login-/Kosten-/Privacy-Szenarien und Update/Restart/Rollback prüfen; Audio- und UI-Evidenz speichern.
- **Fertigstellungsnachweis:** unveränderte Testfixtures, Rohmetriken für ASR/Latency/CPU/RAM, Bildschirm-/Event-Evidenz, Wiederholung nach Neustart und klarer PASS/FAIL/NOT_APPLICABLE je Gate.
- **Quelle:** app/docs/DEBATE_AI_VISION_FINAL.md; app/docs/DESKTOP_FINAL.md; app/docs/windows-final-recovery.md; app/docs/EVIDENCE.md; Release Notes v0.6.6.

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
- **Quelle:** app/docs/EVIDENCE.md; app/docs/FINAL_STATUS_AND_OPEN_ITEMS.md; PR #24.

### P1.2 276-Punkte-Ledger abschließen

- **Problem:** Der historische MASTER_276_STATUS-Ledger enthält überwiegend offene/teilweise Punkte; Acceptance reporting setzt product_accepted=false. A006/A010 sind blockiert, A086 ist IMPLEMENTIERT_ABNAHME_OFFEN; der öffentliche Snapshot enthält den Ledger nicht.
- **Status:** offen; einzelne A-Items sind nachgewiesen, die Gesamtfreigabe fehlt.
- **Nächste Handlung:** jeden Punkt auf aktuellen app-Pfad abbilden, Status nur mit frischem Beleg ändern, alte source-Pfade als Historie markieren.
- **Fertigstellungsnachweis:** versionierter Ledger mit Status, Quelle, Test/Manuell-Nachweis, Rest-Risiko und Verantwortungsentscheidung; keine Default-Ratings.
- **Quelle:** app/.ai/MASTER_276_STATUS.json im privaten Master; app/scripts/acceptance/reporting.py; app/docs/EVIDENCE.md.

### P1.3 A22/Human-Rating unabhängig abnehmen

- **Problem:** PR #19 korrigierte den unvollständigen Denominator-Validator, wurde aber nicht gemergt. Menschliche rhetorische Qualität, unabhängige Datensätze und Rater-Übereinstimmung sind offen.
- **Status:** Validator-Korrektur historisch getestet (10/10 in temporärer Rekonstruktion), keine aktuelle Master-/Windows-/Human-Abnahme.
- **Nächste Handlung:** aktuelle app-Version prüfen, Validator in CI ausführen, vollständige eindeutige Ratings und unabhängige Fälle erfassen.
- **Fertigstellungsnachweis:** RED/GREEN-Regression im aktuellen Tree, Denominator- und Boolean-Gates, anonymisierte Human-Ratings mit Fehlerfällen und Reproduktionsreport.
- **Quelle:** PR #19; app/docs/DEBATE_AI_VISION_FINAL.md; app/scripts/acceptance/*.

### P1.4 Release-/Update-Cutover nachweisen

- **Problem:** Release-Runbook fordert realen Hold-Commit, Manifest, Signing, R2/Access und getrennten Binary-/Daten-Rollback; der produktive Cutover ist nicht belegt.
- **Status:** Runbook und isolierte Smokes vorhanden; externe Veröffentlichung offen.
- **Nächste Handlung:** eine versionierte Probeveröffentlichung unter Operator-Kontrolle mit frischem Client und Abbruch-/Rollback-Fall durchführen.
- **Fertigstellungsnachweis:** Hold-Commit-SHA, Signatur-/Manifest-Bericht, Download-/Update-/Rollback-Logs, Datenintegritätsprüfung und Freigabeentscheidung.
- **Quelle:** app/docs/releasing.md; app/docs/windows-final-recovery.md; app/docs/EVIDENCE.md.

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
- **Quelle:** app/docs/EVIDENCE.md; app/docs/FINAL_STATUS_AND_OPEN_ITEMS.md.

### P2.2 Reproduzierbarkeit des vollständigen privaten Builds

- **Problem:** Historische Testzahlen stammen teilweise aus isolierten oder materialisierten Checkouts; öffentliche Snapshots fehlen absichtlich Module/Specs/Runtime.
- **Status:** private Evidenz vorhanden, unabhängige Wiederholung auf sauberem Commit erforderlich.
- **Nächste Handlung:** app-Quellstand, Lockfiles, Lizenzen und regenerierbare Runtime getrennt archivieren; Build in sauberem Windows-/Linux-Checkout wiederholen.
- **Fertigstellungsnachweis:** Build-Matrix mit Commit, Toolchain, Dependencies, Artifact-Hashes und reproduzierbarem Testlauf.
- **Quelle:** app/docs/EVIDENCE.md; app/docs/releasing.md; DebateAI-Source README; final-public HEAD.

### P2.3 ASR-/Latenz-/Rhetorikmessung auf Zielhardware

- **Problem:** Das Labor misst lokal synthetische/gespeicherte Fälle; Streaming, Dual-Track, Sprecherfehler, Tail-Latency und reale lange Sitzungen sind nicht ausreichend belegt.
- **Status:** calibration_runner.py nennt diese Einschränkungen ausdrücklich; reporting markiert relevante Vergleiche NOT_MEASURED.
- **Nächste Handlung:** referenzierte deutsche Audiofälle, WASAPI-Mikrofon/Loopback, WER/CER, first-speakable/final latency, RTF, CPU/RAM und Revisionen messen.
- **Fertigstellungsnachweis:** Rohdaten, Hardware-/Modell-/Prompt-Hashes, Fehlerklassen, Konfidenz-/Wiederholungsangaben und kein universeller Siegerclaim.
- **Quelle:** app/backend/app/services/calibration_runner.py; transcription_readiness.py; app/docs/RESEARCH_DE.md; DEBATE_AI_VISION_FINAL.md.

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
- **Status:** diese drei Dateien wurden auf einem separaten Prüf-Branch angelegt; Master ist unverändert.
- **Nächste Handlung:** nach Review nur mit Commit-/Test-/Releasebeleg aktualisieren, erledigte Punkte entfernen, ungeklärte Alternativen erhalten.
- **Fertigstellungsnachweis:** jede Änderung verweist auf Commit, PR, Pfad oder frischen Prüflauf; Diff bleibt auf HISTORIE.md, VISION.md und OFFENE_PUNKTE.md beschränkt.
- **Quelle:** Nutzerauftrag; Branch docs/project-consolidation-2026-11-19.

## Ergänzende Auditbefunde (priorisiert)

### P1.6 Aktive Dokumentations-, Link- und Branchreferenzen konsolidieren

- **Kategorie:** **Docs-Drift**
- **Istzustand:** Bestätigt: `app/docs-site/site.test.js:7-10,50-51` liest `app/docs/README.md`, die Datei fehlt im aktuellen Tree. Der aktuelle Docs-Site-Lauf `44628692090` (HEAD `faa68958fc7c4eb8a6ac2914a81043901046cebd`, Job `135929255875`) bricht deshalb mit `ENOENT` ab; `npm run build` wird übersprungen. `sync-docs.mjs:12-19` und `assemble.mjs:12-27` behandeln `README.md` außerdem als Index. Ein interner Linkscan findet zusätzlich fehlende Ziele für `api-keys.md`, `agents.md`, `audio-pipeline.md`, `DESKTOP_FINAL.md`, `CODEX_ACCEPTANCE_2026-11-12.md`, `HISTORIE.md`, `DEBATE_AI_VISION_FINAL.md` sowie `app/architecture.svg`. Aktive Anleitungen verwenden daneben noch das alte Repository/den Pfad `DebateAI.git`, `cd source` (`app/README.md:248-252`) und mehrfach `master`/`origin/master` (`app/docs/releasing.md:11-18,56-60`), obwohl `AGENTS.md:48-49` `ErpeUser/DebateAI-final-public` auf `main` als Vertrag festlegt. `app/README.md:6-21` positioniert das Produkt weiterhin primär als Meeting-Assistent, während `VISION.md:5-17,148-157` den Debatten-Copilot als V1-Leitszenario festlegt. Auch bestehende Quellenangaben in `app/docs/OFFENE_PUNKTE.md:29,71,113` zeigen noch auf die gelöschten historischen Dateien. Zusätzlich widersprechen `AGENTS.md:36-38` (interner `.git`-Checkout) und `README.md:18`/`app/docs/generated-workspace.md:10` (externer Pointer) beim Recovery-Vertrag.
- **Status:** bestätigt; der fehlende Docs-Site-Test ist reproduziert, die übrigen Ziele und Pfade sind per Tree/API als fehlend oder veraltet nachgewiesen.
- **Sollzustand:** Aktive Dokumentation verweist ausschließlich auf vorhandene Ziele und den kanonischen `app/`-/`main`-Stand. Historische Dokumente und alte Pfade bleiben nur mit expliziter Datierung/Provenienz verlinkt. Produktbeschreibung und aktive UI-/Release-Hinweise geben den Debattenkern als V1-Hauptszenario wieder.
- **Minimalste Lösung:** Einen kanonischen Dokumentationsindex festlegen: entweder die vom Docs-Site-Vertrag erwarteten Dateien wiederherstellen oder Sync-, Assemble-, Test- und Inhaltslinks konsistent auf die vorhandenen Dokumente umstellen. Aktive Clone-/Branchbefehle auf `ErpeUser/DebateAI-final-public`/`app`/`main` korrigieren und historische Verweise markieren; README-Claims gegen die Vision-Matrix prüfen.
- **Nutzen:** Docs-Site-Builds werden wieder ausführbar, Onboarding- und Releaseanweisungen führen nicht in veraltete Pfade, und Soll-/Ist-Erwartungen stimmen überein.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Historische Provenienz und veröffentlichte Docs-URLs dürfen nicht versehentlich entfernt werden; Starlight-Slugs, Site-Sync und Release-Runbook müssen gemeinsam angepasst werden.
- **Akzeptanzkriterium:** Ein interner Markdown-/HTML-Linkscan meldet auf dem aktuellen Commit keine fehlenden Ziele; `cd app/docs-site && npm test && npm run build` endet erfolgreich; aktive Anweisungen enthalten keine unbeabsichtigten `source`-/`master`-Pfade.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/docs-site/site.test.js:7-10,50-51`; `app/docs-site/sync-docs.mjs:12-19`; `app/docs-site/assemble.mjs:12-27`; `app/README.md:6-21,248-252`; `app/docs/releasing.md:11-18,56-60`; `app/docs/VISION.md:5-17,148-157`; Workflow-Run `44628692090`, Job `135929255875`.

### P1.7 Evidenzregister und aktuelle CI-Aussagen auf einen Stand bringen

- **Kategorie:** **Docs-Drift**
- **Istzustand:** Bestätigt widersprüchlich: `app/docs/EVIDENCE.md:44` führt 11 hohe Docs-Site- und 4 hohe Oracle-Befunde als offen, `:52-54` beschreibt noch das private Repository `ErpeUser/DebateAI` auf `origin/master` und alte fehlende CI-Schritte. `app/docs/FINAL_STATUS_AND_OPEN_ITEMS.md:13-14,19-22` behauptet dagegen für einen geprüften Stand 0 High/Critical sowie erfolgreiche Läufe `44527239634/50/16`. Für den aktuellen öffentlichen HEAD `faa68958` sind über die Actions-API `tests` `44628692256` und `security` `44628692311` erfolgreich, `docs-site-build` `44628692090` fehlgeschlagen; `Structure` `44628692440` ist insgesamt erfolgreich, enthält aber einen fehlgeschlagenen Sentrux-Job. Die Zahlen selbst sind damit zeit-/commitabhängig und nicht als einheitlicher aktueller Freigabestand belegt.
- **Status:** bestätigt widersprüchlich; der aktuelle Sicherheits-/CI-Inhalt muss gegen frische Logs erneut verifiziert werden.
- **Sollzustand:** Aktive Statusabschnitte nennen nur Werte mit Commit-SHA, Run-/Job-ID und Zeitpunkt. Ältere Auditwerte sind sichtbar historisch und werden nicht als aktueller Blocker oder Pass dargestellt; der fehlgeschlagene Docs-Site-Run und nicht blockierende Strukturbefunde bleiben sichtbar.
- **Minimalste Lösung:** EVIDENCE und FINAL_STATUS in datierte Abschnitte „historisch“/„aktueller HEAD“ trennen und pro Zahl die zugrunde liegende Run-/Job-ID ergänzen. Nicht über die Connector-Reichweite hinausgehende Aussagen als „nicht nachweisbar“ markieren.
- **Nutzen:** Freigabeentscheidungen beruhen auf nachvollziehbarer, nicht widersprüchlicher Evidenz.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Eine lokale npm-/Sicherheitsprüfung kann von den öffentlichen Actions abweichen; deshalb müssen Lockfile, Commit und Joblog gemeinsam referenziert werden.
- **Akzeptanzkriterium:** Ein Review findet in den aktiven Abschnitten keine widersprüchlichen Repo-/Branch-/Auditstände; jede CI-/Audit-Zahl ist auf genau einen Commit und einen sichtbaren Run/Job zurückführbar.
- **Befundvertrauen:** **hoch** für die Dokumentabweichung, **mittel** für den nicht lokal reproduzierten Security-Inhalt.
- **Quelle:** `app/docs/EVIDENCE.md:44,52-54`; `app/docs/FINAL_STATUS_AND_OPEN_ITEMS.md:13-14,19-22`; GitHub Actions `44628692090`, `44628692256`, `44628692311`, `44628692440`, HEAD `faa68958fc7c4eb8a6ac2914a81043901046cebd`.

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
- **Status:** bestätigter Codepfad; die konkrete Klartext-Reproduktion ist mit einem Term nur in Session 2 und deaktivierter NER zu verifizieren.
- **Sollzustand:** Jede ausgewählte Session trägt ihren Vault-/Roster-Schutz zum gemeinsamen Prompt bei, ohne Token-Namensräume oder Reveal-Zuordnung zu vermischen.
- **Minimalste Lösung:** Einen unionsweiten, read-only Roster/Vault-Scope für die User-Nachricht verwenden oder Multi-Session-Chat auf einen gemeinsamen Schutzscope begrenzen; Namespace-/Reveal-Tests ergänzen.
- **Nutzen:** Verhindert, dass ein Klartextwert aus einer zweiten ausgewählten Sitzung an ein externes Modell gelangt.
- **Aufwand:** **M**
- **Risiken und Abhängigkeiten:** Token-Kollisionen, Rückauflösung und Transaktionsdauer über bis zu 20 Sitzungen müssen kontrolliert werden.
- **Akzeptanzkriterium:** Regressionstest mit geschütztem Wert ausschließlich in Session 2 und `ner=False` zeigt keinen Klartextwert im Provider-Prompt; Antworten bleiben korrekt rückauflösbar.
- **Befundvertrauen:** **hoch** für die Codeabweichung, **mittel** für die noch nicht ausgeführte End-to-End-Reproduktion.
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
- **Istzustand:** `.github/workflows/structure.yml` markiert den `sentrux`-Job mit `continue-on-error: true`. Im Lauf `44628692440` (HEAD `faa68958`) schlug der `Rules check`-Schritt fehl; die Auswertung meldete neben `max_file_lines` auch `max_cycles`, `max_cc` und `max_fn_lines`. Der Gesamtworkflow blieb trotzdem `success`, weil der separate Repository-Layout-Job erfolgreich war.
- **Status:** bestätigt; das Ergebnis ist absichtlich advisory, aber als allgemeiner grüner Struktur-Lauf missverständlich.
- **Sollzustand:** Policy und Status unterscheiden klar zwischen blockierendem Layout-Gate und zugelassener struktureller Schuld; ein unerwarteter Verstoß darf nicht wie ein vollständig grüner Qualitätslauf erscheinen.
- **Minimalste Lösung:** Entweder die zugelassenen Regeln als versionierte Allowlist im Run-Summary ausweisen oder Sentrux bei neuen/unerwarteten Befunden blockierend machen; FINAL_STATUS darf nur den differenzierten Status melden.
- **Nutzen:** CI-Signale werden für Review und Release nicht überinterpretiert.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Eine Policy-Änderung kann bestehende Branches blockieren; Baseline- und Lockfile-Ausnahmen müssen reproduzierbar bleiben.
- **Akzeptanzkriterium:** Ein absichtlicher, nicht erlaubter Strukturverstoß führt zu einem sichtbaren roten Gesamt-Gate oder zu einer maschinenlesbaren Allowlist-Erklärung; Run-Summary nennt die vier aktuellen Befunde.
- **Befundvertrauen:** **hoch**
- **Quelle:** `.github/workflows/structure.yml` (`sentrux`-Job und Rules-Check); Run `44628692440`, Jobstatus `Sentrux structural gate=failure`, Gesamtstatus `success`.

### P2.7 Produktionsstart nicht standardmäßig mit Uvicorn-Reload ausführen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/scripts/start_backend.py:25` interpretiert ein fehlendes `BACKEND_RELOAD` als `true` und fügt dann `--reload` hinzu. Compose überschreibt dies zwar mit `BACKEND_RELOAD:-false`, ein direkter oder vergessener nativer Start aus Runbooks bleibt damit watcher-/restart-anfällig.
- **Status:** bestätigt; das Default-Verhalten ist im Startsymbol sichtbar.
- **Sollzustand:** Produktions- und native Starts laufen ohne Reload; Development aktiviert Reload explizit.
- **Minimalste Lösung:** Default auf `false` setzen und die lokalen Entwicklungsbefehle um `BACKEND_RELOAD=true` ergänzen.
- **Nutzen:** Vermeidet unnötige Ressourcenlast und unbeabsichtigte Sessionabbrüche bei Quelldateiänderungen.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Lokale Entwickler erwarten möglicherweise das bisherige Verhalten; Quickstart und Compose müssen synchron bleiben.
- **Akzeptanzkriterium:** Start ohne Env enthält kein `--reload`; ein expliziter Development-Start enthält es und ein Start-/Smoke-Test prüft beide Pfade.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/backend/scripts/start_backend.py:18-25`; `app/docker-compose.yml` (BACKEND_RELOAD-Override).

### P2.8 Große Chat- und PII-Reveal-Antworten begrenzen

- **Kategorie:** **TECH-IMPROVEMENT**
- **Istzustand:** `app/backend/app/routers/chat.py:184-215` lädt für bis zu 20 Sitzungen vollständige Speaker-, TranscriptEntry- und Insight-Mengen in Python, bevor `build_chat_prompt` auf 60.000 Zeichen kürzt. Zusätzlich puffert `app/backend/app/services/pii/reveal_middleware.py:49-79` jede session-scoped JSON-Antwort vollständig in `body_parts`, bevor die Reveal-Verarbeitung beginnt; ein Größenlimit oder Streaming-/Pagination-Schutz ist nicht erkennbar.
- **Status:** bestätigter Codebefund; konkrete RAM-/Latenzgrenzen sind zu messen.
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
- **Status:** bestätigt; Auswirkung ist für Screenreader-/Tastaturnutzung reproduzierbar zu verifizieren.
- **Sollzustand:** Jedes Eingabefeld besitzt einen stabilen zugänglichen Namen; Dialogfokus bleibt innerhalb des Dialogs und kehrt nach Schließen zum Auslöser zurück.
- **Minimalste Lösung:** Deutsche `<label>`-Elemente mit `htmlFor` oder gleichwertige ARIA-Namen ergänzen und einen kleinen Focus-Trap-/Restore-Mechanismus für Confirm/Notice einführen.
- **Nutzen:** Verhindert unbenannte Controls und Fokusverlust in zentralen Datenschutz-/Bestätigungsflüssen.
- **Aufwand:** **S**
- **Risiken und Abhängigkeiten:** Bestehende Tastaturkürzel, Escape-/Backdrop-Verhalten und DOM-Tests müssen unverändert deterministisch bleiben.
- **Akzeptanzkriterium:** Axe-/DOM-Tests melden keine unbenannten Controls; Tab bleibt im Dialog, Escape schließt deterministisch und der Fokus landet wieder auf dem auslösenden Element.
- **Befundvertrauen:** **hoch**
- **Quelle:** `app/frontend/src/components/PiiShieldCard.tsx:213-221,222-231,287-294`; `app/frontend/src/components/ConfirmProvider.tsx:75-113`.

## Zugriffslücken und ausdrücklich nicht geprüfte Inhalte

- Kein vollständiger lokaler privater Checkout, keine private Library-Materialisierung und keine nicht gemounteten Container-Overlay-/Home-Verzeichnisse.
- Remote-Desktop-Recovery-Verzeichnisse wurden inventarisiert, aber Schlüssel, Credentials, Audio, persönliche Datenbanken, Transkripte und private Inhalte nicht gelesen oder in die Dokumente übernommen.
- Private GitHub-Tags/Projects/Rulesets und PR-/Issue-Details, die der Connector nicht auslieferte, sind als ungeklärt markiert.
- Es wurde kein öffentlicher Repository-Write, kein History-Rewrite, kein Merge und kein Release ausgelöst.
