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

## Zugriffslücken und ausdrücklich nicht geprüfte Inhalte

- Kein vollständiger lokaler privater Checkout, keine private Library-Materialisierung und keine nicht gemounteten Container-Overlay-/Home-Verzeichnisse.
- Remote-Desktop-Recovery-Verzeichnisse wurden inventarisiert, aber Schlüssel, Credentials, Audio, persönliche Datenbanken, Transkripte und private Inhalte nicht gelesen oder in die Dokumente übernommen.
- Private GitHub-Tags/Projects/Rulesets und PR-/Issue-Details, die der Connector nicht auslieferte, sind als ungeklärt markiert.
- Es wurde kein öffentlicher Repository-Write, kein History-Rewrite, kein Merge und kein Release ausgelöst.
