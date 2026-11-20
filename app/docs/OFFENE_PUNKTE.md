# DebateAI – Offene Punkte

Stand: 2026-11-20. Diese Datei enthält nur Punkte, für die der aktuelle Tree oder ein erreichbarer Nachweis noch keinen vollständigen Abschluss belegt. Erledigte und veraltete Einträge wurden in dieser Fortschreibung entfernt; historische Belege und alte Zielstände bleiben in [HISTORIE.md](HISTORIE.md).

**Aktueller geprüfter Code-/CI-Stand:** Der getestete Codezielstand ist `9c384608de5da7b452161fa77419a8dfec3ddaed`; dafür sind `tests` (Run `44683868162`) und `security` (Run `44683868692`) erfolgreich. Der anschließende docs-only Stand `cf71d7c0973e0cb8c0064d07b6b719d081c570ae` ist lokal und remote synchron; sein Testlauf `44684946317` ist mit Backend (`136116931378`), Frontend (`136116931129`), PostgreSQL-Grenzen (`136116931485`), Windows-Workspace (`136116931500`) und Browser-Kalibrierung (`136116931518`) grün. Der Security-Lauf `44684946366` bestätigt Python (`136116931581`), Frontend (`136116931624`), Docs-Production (`136116931788`) und Oracle-Production (`136116931447`); der Docs-Site-Build `44684946393` ist ebenfalls grün. Der Structure-Gesamtlauf `44684946526` bleibt wegen geerbter absoluter Sentrux-Verstöße rot (`136116931684`), während der Layout-Job (`136116932033`) und der relative Vergleich `No degradation detected` erfolgreich sind. Lokal auf dem autorisierten Windows-Gerät bestehen die Frontend-Tests mit 371/371 und der Produktionsbuild. Die öffentliche Quellenstrategie ist entschieden: Dieses Repository bleibt ein reproduzierbarer, secretsfreier Source-/Test-Stand; Produktfreigabe, Signierung und Hardwareabnahme bleiben getrennte externe Gates. Die stale-cycle-Regression (`test_stale_strategic_cycle_is_discarded_before_persisting`) ist im Backend-Job `136116931378` enthalten; der Overlay-Snapshot-Test und der Frontend-Build sind im Frontend-Job `136116931129` sowie lokal mit 371/371 Tests nachgewiesen.

## P0 – vor einer belastbaren Produkt- oder Releasefreigabe

### P0.1 GitHub-Actions-Gesamtgate

- **Status:** teilweise nachgewiesen; für `9c384608` sind Tests und Security grün, der Structure-Gesamtlauf bleibt wegen absoluter, geerbter Sentrux-Schulden rot.
- **Offen:** Die verbleibenden absoluten Findings entweder im Code abbauen oder als bewusst akzeptierte Qualitätsverschuldung mit Owner und Termin entscheiden.
- **Fertigstellungsnachweis:** grüner Structure-Gesamtlauf ohne absolute Findings oder eine datierte, verantwortete Ausnahmeentscheidung; Tests/Security müssen weiterhin auf exakt demselben SHA grün sein.
- **Quelle:** Runs `44683868125`, `44683868162`, `44683868692`; Sentrux-Job `136113438257`.

### P0.2 Signiertes produktives Windows-Release

- **Status:** extern offen. Bundle-, Hash- und Rollback-Smokes sind vorhanden; Authenticode, Zertifikatskette, Operatorfreigabe, R2/Access/DNS und produktiver Download sind nicht belegt.
- **Benötigt:** Zertifikat oder autorisierter Remote-Signing-Prozess, Hold-Commit, Release-Manifest und ein frischer Windows-Client mit Update/Restart/Rollback-Nachweis.
- **Blocker/Owner:** Operator-/Release-Owner; im aktuellen Chat sind weder Zertifikat noch Produktionszugriff autorisiert.

### P0.3 Reale Windows-/Audio-/GUI-/Provider-Abnahme

- **Status:** extern offen. CI und Laborverträge decken DOM, Mock-Audio und API-Verhalten ab; ein echter 120+-Sekunden-Mikrofon-/WASAPI-/Loopback-Lauf, Gerätewechsel, WebView2/DPI, Provider-Login/Kosten/Privacy und Neustart fehlen.
- **Benötigt:** frisches Windows-Gerät, reale Audiohardware, autorisierte Providerkonten und Rohmetriken für ASR, Latenz, CPU/RAM sowie Bildschirm-/Event-Evidenz.
- **Blocker/Owner:** Operator-/Hardware-Owner; keine ungeprüften Logins oder Kostenaktionen auslösen.

## P1 – vor einer vollständigen Funktions- und Qualitätsaussage

### P1.4 Release-/Update-Cutover

- **Status:** extern offen. Runbook und isolierte Smokes sind versioniert; ein produktiver Hold-Commit mit Manifest, Signatur, Download, Update und getrenntem Binary-/Daten-Rollback fehlt.
- **Benötigt:** Operator-kontrollierte Probeveröffentlichung auf einem frischen Client; Nachweise müssen auf denselben Release-SHA und dieselben Artefakt-Hashes zeigen.

### P1.5 Distributable-Site-/Asset-Gate

- **Status:** Claim-Matrix, Privacy-/Locality-Texte und die aktive Linkprüfung sind im Code abgeglichen. Offen bleibt nur der distributable Snapshot: jeder aktive Link und jedes Asset muss im veröffentlichten Paket vorhanden sein oder aus den Seiten entfernt werden.
- **Benötigt:** frischer Site-Asset-Scan, Docs-Site-Test/Build und ein veröffentlichter oder ausdrücklich als nicht-produktiv markierter Snapshot.

### P1.10 A/B- und Sprachlabor als zugängliches Produktfeature

- **Status:** offen/strukturell nicht nachweisbar im Hauptprodukt.
- **Benötigt:** zugänglicher, blinder A/B-Vergleich mit Reveal und Export, unabhängige Datensätze, WER/CER/RTF sowie Rater-Übereinstimmung; das Calibration-Labor allein erfüllt diesen Produktvertrag nicht.

### P1.14 Löschpfad für externe, lokale und Browser-Artefakte

- **Status:** lokaler, Browser- und Prozess-Cleanup sowie idempotente Retry-Outbox sind implementiert. Offen bleibt die echte Provider-/Operator-Abnahme.
- **Benötigt:** autorisierter Provider-Test mit absichtlich fehlschlagender Löschung, Retry-/Backoff-Logs, bestätigtem finalem Delete und Prüfung, dass kein zulässiges Reconnect-Replay verloren geht.

### P1.15 Live-State und WebSocket-Journale für Multiworker-Betrieb

- **Status:** offizielle Startpfade erzwingen einen Worker; Journale und Stale-Guards sind begrenzt. Ein gemeinsamer Redis-/DB-State-Adapter und ein Zwei-Worker-Produktionsnachweis fehlen.
- **Benötigt:** autorisierte Multiworker-Umgebung mit gemeinsamem State, Reconnect-/Replay-Test und Nachweis ohne doppelte Persistierung.

### P1.16 LAN-Origin-Vertrauen und Bind-Defaults

- **Status:** Loopback-/Reload-Defaults, Origin-/Host-Allowlist und Instance-Token sind durch Request-Guard-Tests abgesichert. Offen bleibt die vollständige Bedrohungsprüfung auf einem realen LAN mit Reverse Proxy und DNS-Rebinding-Szenarien.
- **Benötigt:** autorisierter LAN-/Proxy-Test mit aufgezeichneten erlaubten und blockierten Origin-, Host-, WebSocket- und Mutation-Fällen.

## P2 – technische Schulden und belastbare Messung

### P2.1 Ruff-/Duplikat-Schulden

- **Status:** F-Fehler und vulture sind bereinigt; breite Style-/jscpd-Last bleibt.
- **Benötigt:** priorisierte, produktionskritische Triage mit begründeten Ausnahmen, ohne ungezielte Massenformatierung während Releasearbeit.

### P2.2 Reproduzierbarkeit des vollständigen Builds

- **Status:** private historische Evidenz ist vorhanden; eine unabhängige Wiederholung aus sauberem Checkout mit Toolchain-, Lockfile-, Lizenz- und Artefakt-Hashes fehlt.
- **Benötigt:** sauberer Linux-/Windows-Checkout und eine versionierte Build-Matrix. Der aktuelle Windows-Desktop-Clone ist für Code-/CI-Tests vorhanden, aber noch kein frischer Release-Build.

### P2.3 ASR-/Latenz-/Rhetorikmessung auf Zielhardware

- **Status:** Labor-/synthetische Messungen sind vorhanden; reale Streaming-, Dual-Track-, Sprecherfehler-, Tail-Latency- und Langzeitsitzungsdaten fehlen.
- **Benötigt:** referenzierte deutsche Audiofälle, WASAPI-Mikrofon/Loopback, WER/CER, first-speakable/final latency, RTF, CPU/RAM, Modell-/Prompt-Hashes und Wiederholungsangaben.

### P2.10 Listen-, Transcript- und Knowledge-APIs

- **Status:** kompatible Array-Limits, stabile Tie-Breaker und Composite-Indizes sind vorhanden. Echte Cursor-Fortsetzung, UI-Seitenabruf und vollständige SQL-seitige Chat-Priorisierung bleiben offen.
- **Benötigt:** versionskompatibler Cursorvertrag für alle betroffenen Endpunkte, UI-Weiterblättern, Cursor-Regressionen und ein begrenzter Lastnachweis.

### P2.11 Parallele Migrationsstarts

- **Status:** PostgreSQL-Advisory-Lock und ein isolierter Paralleltest sind vorhanden. Fehler-/Retry-Matrix eines absichtlich scheiternden Runners und die vollständige Legacy-Datenbankmatrix fehlen.
- **Benötigt:** reproduzierbarer Failure-/Retry-Test, frische und Legacy-Schemata, exakt ein Alembic-Head und sichtbarer Fehlerstatus ohne halb angewendetes Schema.

### P2.12 Prozessweite Journale und PII-Scrub-Indizes

- **Status:** TTL/LRU, Byte-/Registry-Limits, sessionweises Cleanup und terminale Job-TTL sind implementiert und regressionsgetestet. Ein 10.000-Session-Langzeittest und produktiver Multiworker-Replay-Nachweis fehlen.
- **Benötigt:** definierte RAM-/Indexbudgets, synthetischer 10.000-Session-Lauf, Reconnect-Replay-Prüfung und ein autorisierter Multiworker-Nachweis.

## P3 – Inventar und externe Zuständigkeiten

### P3.2 Repository-/Projekt-Inventar

- **Status:** öffentliche Refs, Open-PRs, Issues, Releases und Actions sind für den aktuellen Connectorzugriff geprüft; Open-PRs/Issues/Releases sind leer. Branch-Protection/Rulesets und private Projects/Tags sind über die aktuelle Integration nicht vollständig lesbar (403 bzw. nicht unterstützte API).
- **Benötigt:** authentifizierter Export der fehlenden privaten Inventare mit Zeitpunkt, Cursor/Seitenzahl und Abgleich gegen lokale Refs.
