# DebateAI – Historie und Provenienz

Stand: 2026-11-20. Diese Datei bündelt frühere Visionen, Forschungsentscheidungen, Abgleichsmatrizen und datierte Nachweise. Sie beschreibt historische Herkunft und Entscheidungen, keine aktuelle Freigabe. Aktuelle Ziele stehen in [VISION.md](VISION.md), aktuelle Lücken in [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md).

## Leseregel

Ein historischer Status wird nicht durch seine Aufnahme in dieses Dokument zu einem aktuellen Testergebnis. Alte Pfade, Branch-Namen, Commitstände und Releaseaussagen bleiben Provenienzangaben. Für den heutigen Zustand gelten der aktuelle Quellbaum, frische Tests und die aktuelle Vision.

## Aktueller Implementierungsnachweis – 2026-11-22

Der frische GitHub-Readback für `main` war
`0024b0c930390916a07bc00c869b92b77d56f599`. Darauf aufbauend wurden im
lokalen Checkout zwei Gate-Korrekturen nachgewiesen: `6faabf734c9ee6c4adefdf01175dd58c6185250a`
beschränkt die Docs-Asset-Prüfung auf echte `.css`-Quellen (HTML-Codebeispiele
mit `url(...)` sind kein Asset), und `18b3574` prüft PWA-Metadaten semantisch
statt von einer einzeiligen HTML-Serialisierung abzuhängen. Lokal bestanden die
Docs-Asset-Regression **3/3**, `npm test` im Docs-Site-Projekt, der Clean-Build
und der Snapshot-Audit; der PWA-Lauf bestand mit **6/6**.

Diese Nachweise gelten für die lokalen Commits auf Basis des genannten SHA.
Eine aktuelle GitHub-CI-Abnahme für einen nachfolgenden Ziel-SHA stand zum
Zeitpunkt dieses Eintrags noch aus; die historischen roten Runs
`44967192464`, `44967192422` und `44967192373` bleiben deshalb offen und
werden nicht rückwirkend als grün interpretiert.

## Historische V6-Vision – 2026-11-10

Die folgende Fassung ist der frühere verbindliche V6-Zielstand. Die noch gültigen Zielbestandteile sind in [VISION.md](VISION.md) zusammengeführt.

<details>
<summary>Historischer V6-Text</summary>

# Debate AI V6 – verbindliche Produktvision
Stand: 2026-11-10. Diese Datei dokumentiert das Produktziel, nicht den Nachweis fertig getesteter Funktionen.

## Leitbild
Debate AI ist ein deutschsprachiger, datenschutzbewusster Echtzeit-Debattenassistent für Windows: Er hört Mikrofon und – sofern freigegeben – Systemaudio, erkennt argumentative Züge und liefert **vor dem Verpassen des Gesprächsmoments** eine kurze, sofort sprechbare Antwort oder eine strategisch stärkere Gegenfrage. Die Oberfläche unterstützt einen Menschen beim Denken und Sprechen; sie spricht nicht autonom für ihn und behauptet keine erfundenen Fakten.

## Nicht verhandelbare Qualitätskriterien
1. **Echtzeit zuerst:** lokale Sofortantwort unabhängig von langsamer Recherche/Tiefenanalyse; Revisionen und neue Aussagen verdrängen alte Ergebnisse; keine parallelen, sich gegenseitig überholenden Generierungen; zuerst verständlicher Sprechtext.
2. **Deutsch und natürliche Rhetorik:** keine abstrakten Romanantworten; klare Position, ehrliche Prämissenprüfung, Beweislast, gezielte Rückfrage, gut merkbare Formulierung. Debattenmodi 'Überzeugen' und 'Hart' bleiben; Stimme und persönliche Perspektive des Nutzers bewahren.
3. **Local-first und Wahlfreiheit:** Ollama/Qwen als schneller lokaler Standardweg, lokale Whisper-/Parakeet-/weitere wirklich kompatible ASR-Backends; ChatGPT, Gemini und die bestehenden Bridges für optionale Tiefe. Provider nur dann einsetzen, wenn installiert, angemeldet, freigegeben und tatsächlich geprüft. Niemals Cloudkosten/Übertragung durch einen stillen Test auslösen.
4. **Audiotreue:** getrennte Mikrofon- und Systemaudiospuren, 16-kHz-PCM-Verarbeitung, Ausfall- und Gerätewechselbehandlung; Erkennen von Sprache, Sprecherwechsel und Transkriptkorrekturen.
5. **Belegqualität:** gelesene Quellen von Annahmen trennen; keine halluzinierten Nachweise, verdeckten Modellwechsel oder Scheinsicherheit. Argumentgedächtnis darf veraltete Claims nicht als aktuell verkaufen.
6. **Windows als Hauptprodukt:** existierender lokaler Checkout, tatsächliche EXE, WebView2, PostgreSQL, ffmpeg, Ollama, Bridges, Tray und Overlay müssen über einen reproduzierbaren, sicheren Updatepfad dieselbe Releaseversion verwenden.
7. **Nutzerdaten behalten:** Datenbanken, lokale Modelle, Profile, persönliche Prompts, Playbooks, Credentials, Browser-Sessions und DPAPI-Schlüssel nie durch Code-/EXE-Updates überschreiben. Code darf veraltete lokale Versionen ersetzen; echte einzigartige Verbesserungen werden kompatibel integriert.
8. **Messbarkeit statt Bauchgefühl:** objektive ASR-Fehlerrate, Wort-/Satzvergleich, Erstreaktionslatenz, finale Antwortlatenz, Antwortqualität, Sprechbarkeit, Ressourcenlast, Stabilität, Offline-/Privacy-Verhalten, Fehlerfälle, reproduzierbare Fixtures. Keine universelle 'beste' Einstellung behaupten, wenn Hardware/Testmaterial nicht geprüft sind.

## Sprachlabor: einmal sprechen, fair vergleichen
In Admin / Einstellungen ein benutzbares, responsives **Sprachlabor** bereitstellen. Ein vorformulierter deutscher Satz wird angezeigt; der Benutzer spricht ihn ein oder lädt eine vorhandene Audiodatei hoch. Dieselbe unveränderte Aufnahme wird an die ausgewählten verfügbaren ASR-Modelle geschickt, nicht jedes Modell mit neuer Sprache gefüttert. Unterstützte Messwerte: erkannter Wortlaut je Modell, Wortfehlerrate (WER) gegen editierbaren Referenzsatz, Laufzeit, Real-Time-Factor (RTF), Fehlerstatus und lokale/Cloud-Herkunft. Eine Aufnahme mit Stille, falscher Sprache, Hintergrundgeräusch, Eigennamen, Zahlen und aufeinanderfolgenden Korrekturen sind relevante Fälle. Verfügbarkeit muss vor der Ausführung geprüft werden; API-/Cloudkosten nur mit expliziter Opt-in-Bestätigung. Aufnahme und erkannte Texte bleiben lokal und werden nicht ungefragt dauerhaft gespeichert. Fehler und Modellgrenzen sichtbar machen.

Empfohlene deutschsprachige Beispielsätze (editierbar, keine echten Personendaten):
- 'Sie behaupten, erneuerbare Energien seien unzuverlässig, weil nachts keine Sonne scheint.'
- 'Das klingt plausibel, aber welche belastbaren Daten stützen Ihre Schlussfolgerung?'
- 'Wenn die Kosten um 15 Prozent sinken, warum steigt dann der Gesamtpreis?'
- 'Ich unterscheide zwischen einer unbelegten Behauptung und einer nachprüfbaren Quelle.'
- 'Moment, ich korrigiere mich: Nicht 2023, sondern 2024 ist der Vergleichszeitraum.'
- 'Überprüfen wir die Voraussetzung, bevor wir über die Folgen sprechen.'

## Antwortlabor: echter fairer Blindvergleich
Ein zweiter Abschnitt, **Antwortlabor**, lässt eine gegnerische These, eigene Position und Stil/Modus eingeben, optional den Sprachlabor-Transkripttext übernehmen. Zwei ausgewählte tatsächlich verfügbare Modelle/Promptvarianten erhalten dieselbe Eingabe und dieselben erlaubten Kontextquellen. Vor Wahl eines Siegers stehen **Antwort A / Antwort B ohne Modellnamen** nebeneinander (Reihenfolge deterministisch randomisiert pro Test); Bewertung nach sofortiger Nutzbarkeit, Natürlichkeit, Präzision, argumentative Stärke, Gegenfrage, Quellenredlichkeit und Latenz. Nach der Bewertung Identitäten, Modellversionen, Prompt-Hash, technische Laufzeit und Kostenhinweis aufdecken. Ungeprüfte Cloud-Modelle nicht als live-vorhanden darstellen. Keine automatische Übernahme des Siegers in Produktion. Der Mensch kann Testergebnisse exportieren und **erst nach bewusster Bestätigung** eine getestete Empfehlung übernehmen; Rückgängig-/Wiederherstellungsweg bereitstellen.

## Selbsttests und Abnahmekriterien
- Deterministische Unit-/Contract-Tests für Routing, Streaming, JSON, Revisionen, falsche/fehlende Daten, Timeout, Parallelität, Tokenlimits, Eingabevalidierung, Recorder-Lebensdauer und sichere Konfigurationsübernahme.
- Integrationstest für Windows-Audio, On-device-ASR und WebSocket-End-to-End (nur auf realer Hardware als bestanden kennzeichnen).
- Offline/Privacy-First ohne unerwartete Cloudanfragen; externe Logins/Keys niemals extrahieren, übertragen oder in Reports zeigen.
- Belastungstest während einer laufenden Debatte; Labor darf keine Audio- oder Qwen-Echtzeitkapazität rauben. Livegespräch soll Labor-Benchmarks blockieren oder bis danach zurückstellen.
- Nutzeroberfläche: Desktop, schmale Fenster/Mobilbreite, Tastaturbedienung, Screenreader-Labels, Fehlerfälle, kein stilles Verschwinden einer Aufnahme.
- Windows: frischer Start und Update mit Datenmigration, Wiederstart, Update- und Rollback-Smoketest, Prüfsumme, Nachweis des tatsächlich ausgeführten EXE-Pfads.

## Bewusste Nicht-Ziele
Keine unkontrollierte Neuarchitektur; kein ungefragtes Löschen von Nutzerprofilen oder lokalen Verbesserungen; kein Auto-Apply des A/B-Siegers; kein erfundener Windows-Hardwaretest; keine automatische Veröffentlichung eines signierten Releases ohne Zertifikat/Freigabe.

## Vorrang und Bezug
Zusammen lesen: `/AGENTS.md`, `/app/AGENTS.md`, `HANDBUCH.md` und
`OFFENE_PUNKTE.md`. Dieses Dokument beschreibt die Herkunft und die
Entscheidungen; Handbuch und offene Punkte regeln Ausführung und aktuellen
Nachweis.

</details>

## Forschungs- und Abgleichentscheidungen – 2026-11-11

Die früher getrennten Forschungs- und Reconciliation-Dateien werden hier als historische Entscheidungsgrundlage erhalten. Ihre Aussagen waren Mess- und Architekturhinweise, keine pauschalen Qualitätsbeweise.

### Recherchierte Entscheidungen

<details>
<summary>Historischer Forschungsbericht</summary>

# DebateAI - recherchierte Entscheidungen, 2026-11-11

Keine universell beste Architektur oder Windows-Modellrangliste wird behauptet. Drei Firecrawl-Agenten recherchierten ausschliesslich oeffentliche Primaerquellen fuer ASR, Bewertung/Agentenarchitektur und Zuverlaessigkeit. ASR endete abgeschlossen; die anderen beiden erreichten das Limit mit Teilresultaten. Sie haben keinen privaten Code begutachtet. Context7 lieferte zusaetzlich die zur Zielversion passende Python3.12-asyncio-Dokumentation.

## Einzelprompt versus weitere Agenten

[BenchAgent, 2026-06-04](https://arxiv.org/abs/2606.05670) vergleicht Agentenworkflows unter vereinheitlichten Ein-/Ausgaben und Werkzeugen. Die untersuchten Aufgaben liefern keinen direkten Beweis fuer deutsche Windows-Livedebatten oder dass mehr Agenten stets besser sind. [Asynchronous Tool Usage, 2024](https://arxiv.org/abs/2410.21620) ist ein Architekturhinweis, kein projektspezifischer Qualitaetsbeweis.

Entscheidung: vorhandenen lokalen Kurzpfad und getrennte Hintergrundanalyse behalten. Kein synchroner LLM-Judge vor der ersten Antwort, kein zweiter Prompt-/Orchestratorstack. Zusatzaagenten nur nach Ablation unter gleichem kausalem Kontext, Zeit-/Tokenbudget und Gesamtlast. Der neue Paarbenchmark misst den bestehenden Produktions-Replay in isolierten sequentiellen Prozessen, statt andere Prompts als Produktionsqualitaet auszugeben. LangGraph/AutoGen/vLLM nur als begruendetes spaeteres Experiment, nicht als ungemessene Pflichtabhaengigkeit.

## Bewertung: Nutzwert ist nicht Wahrheit

[MT-Bench/Chatbot Arena](https://arxiv.org/abs/2306.05685), [Position Bias](https://arxiv.org/abs/2406.07791), [Cognitive Biases](https://arxiv.org/abs/2402.10669) und [Self-Preference](https://arxiv.org/abs/2410.21819) motivieren getrennte Pruefungen von Reihenfolge, Laenge, Stil und Modellfamilie. Ergebnisse aus ihren Daten sind nicht automatisch deutsche Sprechbarkeits-/Faktenbewertungen. Die neuere [Bias Mitigation-Arbeit](https://arxiv.org/abs/2604.23178) bleibt ein Forschungsinput, kein versprochener projektspezifischer Gewinn.

Umgesetzt: zufaelliges A/B, Identitaeten erst nach Entscheidung, Gleichgut/Beide-ungeeignet, keine erfundenen Default-Ratings, fehlgeschlagene Paare im Nenner, echte Nachrechnung von Kontext-Hashes. Hash beweist Textidentitaet, nicht Wahrheit oder gleiche Hardware. Nutzerfeedback bleibt usefulness/unverified. Keine automatische Gewinnerkonfiguration.

Noch zu messen: Faktentreue mit konkreten Quellen, Sprechbarkeit/Relevanz getrennt, Biasperturbationen, Zweitrater-Uebereinstimmung, statistische Einheit und Konfidenzintervalle. 20 synthetische Turns sind ein Pilot/Funktionsset, keine allgemeine Rangliste. Wiederholungen desselben Falls nicht als unabhaengige Faelle zaehlen.

## Deutsche ASR und Streaming

[Whisper-Streaming](https://arxiv.org/abs/2307.14743) und [MFLA, 2025-06-04](https://arxiv.org/abs/2506.03722) untersuchen Qualitaet/Latenz/Stabilitaet. GPU- oder Offlinewerte sind keine Ziel-PC-Messung. Die offizielle [Parakeet-v3-Modellkarte](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) stuetzt die deutsche multilingual-Auswahl statt des englischen v2-Kandidaten.

Entscheidung: bestehende ONNX-Adapter, getrennte Audioquellen und Revisionen behalten. Keine ungepruefte NeMo-/RNNT-/CTranslate2-Migration. [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), [faster-whisper](https://github.com/SYSTRAN/faster-whisper) und [NeMo-Speech.cpp](https://github.com/NVIDIA/NeMo-Speech.cpp) sind Vergleichskandidaten mit Lizenz-, Checkpoint-, Windows-, Warmup-, Speicher- und Gesamtlastpruefung. Nichts davon wird hier als neu integriert behauptet. [Confucius4-R2T2](https://arxiv.org/abs/2611.06043) bleibt Recherchekandidat, kein getesteter deutscher Produktionsadapter.

Messen: WER/CER getrennt von Negationen, Zahlen/Einheiten, Namen, Korrekturen und Sprecherfehlern. RTF getrennt von stabilem Wort, erster sprechbarer Antwort und echter Anzeige. VAD/Chunkgroesse/LocalAgreement beeinflussen Verzögerung und Revisionen; keine pauschale Ersetzung. WASAPI-Mikrofon/Loopback, Drift/Overlap und konkurrierende ASR/LLM-Last auf Windows messen.

## Ollama und wirklich lokale Routen

[Thinking](https://docs.ollama.com/capabilities/thinking), [Authentication](https://docs.ollama.com/api/authentication) und der offizielle [OpenAPI-Vertrag](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml) sind die Referenz fuer native Faehigkeiten und Remote-Metadaten. Localhost allein beweist keine ausschliesslich lokale Inferenz.

Umgesetzt: begrenztes natives /api/tags vor Benchmark-Substitutionen; fehlende Modelle und remote_host/remote_model/Cloudaliases ablehnen; keine Downloads; ungeeignete URLschemata, Credentials, Queries, Fragmente und gehostete Bridgerouten abweisen. Metadatenzugriff ohne Umgebungsproxy/Redirect. Ein taeuschender Drittanbieterproxy bleibt eine Betreiber-/Netztestfrage. think=false/reasoning_effort=none sind Anforderungen, keine belegte Laufzeitwirkung; sichtbare Antwort und echte Modellfaehigkeiten auf Zielhardware messen. Normale konfigurierte Produktprovider werden nicht entfernt.

## Cancellation, Uploads, Paketierung

[Python3.12 asyncio](https://docs.python.org/3.12/library/asyncio-task.html) erklaert wait_for/shield: Abbruch eines Awaiters bedeutet kein physisches Threadende; wait_for kann auf Cancellation warten. [FastAPI UploadFile](https://fastapi.tiangolo.com/tutorial/request-files/) spoolt nach Parsing, daher ersetzt begrenztes read() kein Vor-Parser-Limit.

Behalten/ergänzt: ASGI-Uploadgrenze, Single-Flight bis echtem Ende, begrenztes Finalwarten nach Teilantwort, Replayquarantaene, sequentielle begrenzte Benchmarkprozesse, kein unbegrenztes stdout-PIPE. Nur eigene Kinder beenden/reapen, keinen Benutzer-Ollama-Prozess. Bestehende unittest/Node/Playwright-, pip-audit/Bandit/npm-audit- und Lockfilewege benutzen statt spekulativer neuer Runtimebibliotheken. Versionen nicht pauschal upgraden.

Windows bleibt separat: PyInstaller-Ressourcen/ONNX-Daten, DPAPI, WebView2, Audio, PostgreSQL-Backup, Signatur und Rollback brauchen echte native Gates. Das Runbook entfernt Loeschen-vor-Entpacken, behauptet jedoch keinen hier ausgefuehrten Installationslauf.

</details>

### Abgleich der Lieferungen

<details>
<summary>Historische Abgleichsmatrix</summary>

# Abgleich beider Lieferungen - 2026-11-11

Basis: Recovery-ZIP SHA256 5e26c00f2615d7712efb1e2c648ba307db6c013ddb20964a672c07a135f63d7b und Featurestand 9d88baae677083770c2c81943687713d6fc393a6. Historische 100/141 Tests sind nicht automatisch heutige Tests. Codeintegration und native Produktabnahme bleiben getrennt.

| Punkt | Entscheidung / integrierter Ort | Grenze |
|---|---|---|
| Git-Kollisionsschutz | Neuere eingebettete Version in scripts/sync_final_workspace.py behalten; kein altes Hilfsskript darueberkopieren. | Echter Windows-Checkout noch synchronisieren. |
| ASR-Modellcaches | Neueren local_transcriber.py-Fix erhalten, Kalibrierung ohne automatische Downloads. | Reale Modellinitialisierung pruefen. |
| Upload/Decoder | Integrierte ASGI-Grenze, diagnostic_audio und asynchroner Decoder erhalten. | Native Bundle-Gates offen. |
| Worker bei Abbruch | Exklusive Diagnosejobs erhalten; Produktions-Replay/Prozess-Timeout und Quarantaene ergaenzt. | Cancellation beweist kein physisches Threadende. |
| apply_package.py | Historischer ZIP-Installationshelfer absichtlich nicht als zweiter Installer eingebaut. Direkte Git-Integration ersetzt seinen Zweck. | Seine neun Tests nicht als neue Produkttests zaehlen. |
| Gefaehrlicher Installer | DESKTOP_FINAL.md wirklich ersetzt; windows-final-recovery.md integriert. Kein Loeschen vor Entpacken/Pruefung. | Native Installation/Rollback noch ausfuehren. |
| 13 deutsche Testtypen | Vorhandenes Labor mit Aufnahme/Import, gleichem Clip, WER/CER, RTF, Zahlen/Negation/Stille behalten. | Kein Dual-Track-/Streaming-/Sprecherbeweis. |
| Blindvergleich | Mehrfall-Import/zufaellige A/B/Identitaet erst nach Wahl behalten; echte Kontext-Hashpruefung und Fehlernenner hinzugefuegt. | Nutzen ist kein Faktenlabel. |
| Bewertungen | Unberuehrte Skalen erzeugen nicht mehr automatische 3/5-Werte. | Historische Exporte mit Defaults nicht als bewusste Ratings interpretieren. |
| Echte Modellausgaben | backend/scripts/benchmark_blind_pair.py ruft bestehenden Produktionsbenchmark in isolierten sequentiellen Prozessen auf, beide Modi, 20 deutsche Turns. | Source-CLI, kein Frozen-UI-Generierungsbutton; reale Modellmessung fehlt. |
| Revision/Modus/Latenz | Mode korrekt propagiert; alte/leere Modellfragmente liefern keinen falschen ersten Zeitpunkt; optionale Gegenfrage und Headless-ACK korrekt behandelt. | Headless-ACK ist keine Bildschirmanzeige. |
| Herkunft/Privacy | Lokale native Modellliste begrenzt pruefen; Cloudaliases/URLcredentials/unerwartete Routen abweisen; keine rohen Fehler/Secrets exportieren. | Manipulativer lokaler Proxy erfordert Betreiber-/Netzpruefung. |
| Settings/Persistenz | Keine aktive Modell-/Profilumstellung. Speicherung bewusst; Versuchszahlen und Herkunft im Export. | Kein automatisch behaupteter Sieger. |
| In-App-Zugang | Neueren Dialog behalten, Haupt-React-Baum bleibt montiert. | WebView2-Mikrofon auf Windows pruefen. |
| PWA-Identitaet | Manifest und vorhandener PWA-Test gemeinsam auf DebateAI abgeglichen. | Keine neue Ikonengrafik behaupten. |
| Forschung/Matrix | RESEARCH_DE.md, diese Matrix und DEEP_RESEARCH_AUFTRAG_DE.md nun versioniert. | Ein Rechercheagent fertig, zwei Teilresultate am Limit. |
| Codex-Auftrag | Aktueller DESKTOP_FINAL.md ersetzt veraltete ZIP-Overlay-/Feature-Branch-Pflicht. | Alle 15 Windows-Gates bleiben verbindlich. |
| Datenidentitaet/Update | Neuere kompatible DebateAI-Datenpfade und eigener expliziter API-Updatekanal behalten. | EXE/Updater/Archiv-/Paketmigration noch nicht vollstaendig. |
| Repository-Rename | Vorhandener gepruefter rename_debateai_repository.py bleibt. | Reale Adminaktion nicht durch Helferexistenz erledigt. |
| NeMo/Overlay/Host-Guard aus abgebrochenen Logs | Keine unbelegten Fertigmeldungen uebernehmen; vorhandene Pfade gezielt testen. | Nicht als in diesem Durchlauf neu implementiert ausgeben. |

Vision bleibt kurze sprechbare lokale Hilfe, korrekte deutsche Sprache und Revisionen, Argumentgedaechtnis, optionale Gegenfrage, Hart/Ueberzeugen, Nutzerkonfiguration und getrennte externe Hintergrundanalyse. Mehr Agenten sind kein eigenstaendiges Qualitaetsziel.

</details>

## Zugriffslücken und ausdrücklich nicht geprüfte Inhalte

- Kein vollständiger lokaler privater Checkout, keine private Library-Materialisierung und keine nicht gemounteten Container-Overlay-/Home-Verzeichnisse.
- Remote-Desktop-Recovery-Verzeichnisse wurden inventarisiert, aber Schlüssel, Credentials, Audio, persönliche Datenbanken, Transkripte und private Inhalte nicht gelesen oder in die Dokumente übernommen.
- Private GitHub-Tags/Projects/Rulesets und PR-/Issue-Details, die der Connector nicht auslieferte, sind als ungeklärt markiert.
- **Historischer Auditstand vor der Remediation vom 20.11.2026:** In diesem Prüfbericht wurde noch kein öffentlicher Repository-Write, History-Rewrite, Merge oder Release ausgelöst; spätere Commits auf Public-`main` sind davon unabhängig dokumentiert.

## Historische Evidenz 2026-11-18

*Übernommen aus dem früheren eigenständigen Evidenz- und Freigaberegister. Die folgenden Zahlen, Dateipfade, Prüfläufe, Hashes, Git- und CI-Aussagen beschreiben den dokumentierten Stand vom 18. November 2026, nicht den aktuellen Public-Branch oder eine Produktfreigabe.*

Dieses Dokument unterscheidet reale lokale Prüfungen von nicht ausgeführten Release-, Hardware- und CI-Gates. Detaillierte historische Git-Commits und unabhängige Original-Sicherungen bleiben erhalten; generierte Testprotokolle sind keine Quellcodeabhängigkeit.

### 18. November 2026 — bereinigter Quellbaum

Basis vor der Umstellung: Git-HEAD `e86b799817ea8e64ff54c948ed483636802a75fd` auf `master`. Der aktive Quellcode wurde physisch von `source/` nach `app/` verlegt und vollständig zum Commit vorgemerkt. Das separate Git-Verzeichnis liegt außerhalb des Projektordners; `git fsck --full` bestanden, Refs, Stash und Index beim Umzug abgeglichen.

- Quelle: 1.034 versionierbare Dateien unter `app/`, ohne Node-Installationen, Cache oder Desktop-Runtime; die gesetzlich erforderliche Node-24.21.0-Lizenz wurde aus dem alten Git-Stand wiederhergestellt und mit der offiziellen Quelle abgeglichen.
- Tatsächlich gelöscht: der gesamte alte Report-/Staging-Bereich unter `DebateAI_Generated/reports/` — **15.434 Dateien / 460.449.956 logische Bytes** (15.362 Staging-Dateien und 72 übrige Reportdateien). Vorher wurden 46 abweichende Dateien und alle übrigen Reports in unabhängigen, SHA-256-geprüften ZIPs außerhalb des Repositorys gesichert. Dies ist **keine** Aussage über physisch freigegebene Speicherblöcke.
- Die bisherige Native-Runtime (9.082 Dateien) blieb während der Build-/Update-Tests unangetastet. Nach bestandenem Release-/Rollback-Test wurde sie vollständig außerhalb des Repositorys gesichert und der verifizierte neue Bundlebaum als aktive Runtime installiert. Für den tatsächlich aktiven Pfad folgte ein eigenständiger erfolgreicher Smoke-Test.
- Unabhängiges Quell-ZIP inklusive root/.github-Konfiguration: 1.044 Dateien, pro Datei SHA-256 geprüft. Ältere externe Rückfall-Snapshots und die komplette Git-Historie bleiben unverändert.
- Die Git-Index-Migration erfasst jetzt alle 1.034 `app/`-Dateien. Eine unabhängige Sicht auf den vorbereiteten Git-Tree ergab 1.045 Dateien insgesamt, keine Generated-/Daten-/Secretdateien und vier ausschließlich synthetische Test-Keymuster. `git diff --cached --check` bestand. Die `.gitattributes`-Regeln wurden von `source/` auf `app/` korrigiert, damit der Gemini-Sicherheitspatch und die Node-Lizenz in frischen Checkouts unverändert bleiben. Ein Commit/Push ersetzt nicht die Funktionsprüfung.

### Isolierter Test aus exakt vorgemerkten Git-Quellen

Die Git-Index-Dateien wurden ohne `source/` und ohne `DebateAI_Generated/` als eigenständiger Quellbaum exportiert. Dort wurden `npm ci` für Frontend und Docs-Site erfolgreich ausgeführt. Python-Tests verwendeten eine separate, bereits vorhandene Python-3.12-Testumgebung; zwei lokale ONNX-Modelldateien wurden **nur in die Testkopie** aus der überprüften Windows-Runtime kopiert und per SHA-256 abgeglichen. Das ist **noch kein Nachweis**, dass alle Python-/Native-Abhängigkeiten allein durch externe Downloads frisch installiert wurden.

| Gate | Ergebnis |
|---|---|
| Backend: `python -m pytest -q -p no:cacheprovider tests` | **2.149 bestanden, 18 übersprungen, 376 Untertests bestanden**, 3 Warnungen, nach Fix des Audio-Shutdown-Imports |
| Desktop-Python: `python -m pytest -q -p no:cacheprovider tests` | **265 bestanden, 1 übersprungen, 210 Untertests bestanden**, inklusive Lizenz- und Zeilenenden-Verträge |
| Frontend: `npm test` | **364 bestanden** |
| Frontend: `npm run build` | **Exit 0**, TypeScript/Vite; große Bundle-Chunks bleiben eine Warnung |
| Docs/Worker: `node --test *.test.js` | **212 bestanden** |
| Skript-/Acceptance-Tests: `python -m pytest -q -p no:cacheprovider app/scripts/tests` | **70 bestanden, 2 übersprungen, 20 Untertests bestanden** |
| Signing-Worker: frisches `npm ci`, `npm test` | **29 bestanden** |
| Docs-Site: `npm run build` | **Exit 0**, 24 HTML-Seiten, 23 Docs |
| Git: `git diff --cached --check`, `git fsck --full` | **Exit 0** vor Commit und nach Git-Auslagerung |
| Vulture (Konfidenz ≥90 %) | **0 sichere Treffer** |
| jscpd (Python/JS/TS, 8 Zeilen, 75 Tokens) | **67 Duplikatstellen**, unverändert gegenüber letztem Refactoring |
| Ruff (F-Regeln) | **0 Befunde** nach Behebung des fehlenden `_append_audio_frames`-Imports im Audio-Shutdown. Erweiterter E4/E7/E9/F-Scan: zunächst **221 Befunde**, danach verbleiben 220 stilistische Warnungen (E402/E701/E702/E741); dieser breite Gate wird **nicht** als grün gemeldet. |

Für einen neuen Windows-Releasekandidaten wurden **PyInstaller 6.22.3 und die gepinnten Python-Abhängigkeiten** frisch installiert, PostgreSQL 16.4.0, FFmpeg, CLIProxyAPI/Gemini-Plugin und Node/Oracle anhand fester Versionen bzw. SHA-Werte bezogen und die Gemini-Bridge aus hashgeprüften Go- und Quellarchiven gebaut. Der native **PyInstaller-Build bestand (Exit 0)**, mit dokumentierten Warnungen zu optionalen PostgreSQL-Perl-/Python-Extensions und versteckten Imports.

Der unabhängig gebaute, **nicht signierte** Windows-Releasekandidat wurde tatsächlich getestet:

- `DebateAI.exe`: SHA-256 `95ab3d2d3976817d5fa2ce018e85a8118464c43633ff0db02a68dc6c388292ba` (26.845.643 Bytes). Der komplette Bundlebaum umfasst **16.122 Dateien / 963.270.554 logische Bytes**. Der native Headless-Smoke bestand mit HTTP-Health, lokaler ASR-Readiness, Kalibrierungs-Assets/-Katalog und sauberem Shutdown (Exit 0).
- Frisch gebündeltes Node 24.21.0 und Oracle-CLI 0.22.2: `--help` gegen die tatsächlich gebündelte CLI erfolgreich (Exit 0).
- `DebateAI-windows-x64.zip`: **448.063.405 Bytes**; SHA-256 `c4b457a7a4150de9f962ce0ae92d7d6e7735815223a1d2d7d86c2474f2528595`. Für alle **16.122** Archivdateien wurden Namen, Größe und CRC geprüft.
- `desktop/scripts/smoke_update_archive.py --platform windows-x64 --archive …`: **„OK: native windows-x64 update and forced rollback“**; positiver gestufter Austausch und absichtlich ausgelöster Rückfall in isolierter Umgebung, noch ohne die damalige aktive Runtime zu verändern.
- **Authenticode-Status:** `NotSigned` (alte und neue EXE). Reale Audiohardware, Provider-Logins, öffentliche Update-Veröffentlichung, grafische GUI-/DPI-Abnahme und Produktionsfreigabe sind nicht bestätigt.

**Security-Paket-Audit:** Bei `npm audit --omit=dev --audit-level=high` im frisch installierten Quellbaum wurden **0 hohe Befunde** für Frontend und Signing-Worker, jedoch **11 hohe Befunde** für Docs-Site und **4 hohe Befunde** für die optionale ChatGPT-Oracle-Runtime gemeldet (u. a. transitive Astro-/Glob-Abhängigkeiten). Die Zahl bezeichnet betroffene Abhängigkeitspakete aus `npm audit`, nicht bestätigte Ausnutzungen. Die Lockfiles werden nicht blind auf potenziell inkompatible Major-Versionen geändert. Diese Security-Gates **bleiben offen**; `.github/workflows/security.yml` enthält explizite Audit-Jobs, die bei weiterhin vorhandenen Befunden rot werden. Kein Sicherheits- oder Release-Pass ohne deren Behebung.

### Lokale native Aktivierung – 18. November 2026

Nach dem geprüften Git-Commit `9db444648fdce2cb76867ab89c563c01905af113` und dem bestandenen Archiv-Smoke wurden alle **16.122** Bundledateien separat in einen neuen Runtime-Kandidaten kopiert und **einzeln per SHA-256 gegen den frisch gebauten Quell-Bundlebaum geprüft**. Erst danach wurden die Ordner umgestellt; die bisherige vollständige Runtime blieb unter `DebateAI-FINALISIERUNG-SICHERUNG-20261118/PREVIOUS_NATIVE_RUNTIME_BEFORE_20261118_REBUILD/` **außerhalb** des Repositorys erhalten. Die alte EXE hat unverändert SHA-256 `d430c5ded6f67f8251eb3f4b928dce6073d9e043593b8d57d907dac61781ad49`.

Der aktive Pfad `DebateAI_Generated/runtime/DebateAI/DebateAI.exe` hat jetzt SHA-256 `95ab3d2d3976817d5fa2ce018e85a8118464c43633ff0db02a68dc6c388292ba`. Der **erneute reale Headless-Smoke direkt aus diesem aktiven Ordner** meldete `OK: healthy`, `OK: bundled local ASR runtime usable`, `OK: testlab assets and authenticated catalog usable`, `OK: clean shutdown` sowie Exit-Code **0**. Der Aktivierungszustand `activated_native_smoke_verified` und die ursprüngliche EXE-Sicherung sind extern protokolliert. `Get-AuthenticodeSignature` ergibt weiterhin **NotSigned**; grafische Bedienung, echte Audiohardware, Provider-Konten und öffentliche Updates sind nicht dadurch freigegeben.

### GitHub und CI

Am 18. November 2026 stimmte der öffentliche Remote-Ref-Abruf des **privaten** Repositorys `ErpeUser/DebateAI` für `origin/master` mit `e86b7998` überein. Es gab nur den Branch `master` und keine offenen PRs. Die aktuellsten GitHub-Actions-Runs vom 17. November 2026 meldeten `failure` für Tests und Security; für die geprüften Jobs kamen **keine ausführbaren Steps** zurück. Ein angezeigtes Workflow-`success` ist daher kein Beleg für durchgeführte Strukturtests. Lokale Tests sind unabhängig von GitHub-CI.

### Historie und Provenienz

Ältere Aufräumschritte sind durch die Git-Commits `946144b4` (historische Baseline) und `a9012b3a` (früherer Cleanup) dokumentiert. Bisherige Forschung, Quell-Provenienz, Privacy-Audits und ältere Release-/Snapshot-Manifeste sind historische Belege und keine aktuelle Build-Freigabe. Nur gezielt identifizierte, eindeutig reproduzierbare Dateien dürfen endgültig entfernt werden. API-Schlüssel, lokale Sessions, PostgreSQL- und Anwendungsdaten unter `%LOCALAPPDATA%/DebateAI` sind keine generierbaren Caches.

## Historischer Status 2026-11-19

Die folgenden Angaben bleiben als datierter Status erhalten. Sie sind keine aktuelle Abnahme.

*Übernommen aus dem früheren eigenständigen Statusbericht vom 19. November 2026. Die damaligen Pass-/Offen-Aussagen gelten nur für die jeweils angegebenen Tests und Commits; verbindlich für offene Gates sind die oben stehenden P0–P3-Einträge.*

Stand: **19. November 2026**. Der [Evidenznachweis](#historische-evidenz-2026-11-18) unterscheidet lokal bestandene Tests, neu gebaute Artefakte und noch offene externe Freigaben. Frühere Statusstände und die damaligen `source/`-Pfade sind ausschließlich historische Belege im gesicherten Git-Verlauf, **keine aktuelle Handlungsanleitung**.

### Bereits lokal nachgewiesen

- Kanonischer Quellbaum unter `app/`; bisherige historische `source/`-Pfade im Git-Index entfernt. Git-Metadaten extern ausgelagert, vollständige Integritätsprüfung bestanden.
- Unnötige generierte Report- und Stagingkopien gelöscht, Modelle und Benutzer-/DB-Daten geschützt.
- Neuer, gepinnter Windows-Quellaufbau mit PyInstaller, PostgreSQL, FFmpeg, CLIProxyAPI, Node/Oracle und aus verifizierten Quellen gebauter Gemini-Bridge durchgeführt; native EXE ist erfolgreich gestartet und wurde mit Health, ASR, Lab-Assets und sauberem Shutdown geprüft.
- Vollständige automatische Tests: Backend **2.149 bestanden / 18 übersprungen**, Desktop **265 / 1 übersprungen**, Frontend **364 bestanden**, Docs/Worker **212 bestanden**, Skripte **70 / 2 übersprungen**, Signing-Worker **29 bestanden**; Frontend- und Docs-Build erfolgreich.
- Windows-Releasekandidat: neuer Headless-EXE-Smoke, Oracle-CLI und isolierter Update-/Forced-Rollback-Smoke bestanden; 16.122 ZIP-Mitglieder geprüft, SHA-256 im [Evidenzregister](#historische-evidenz-2026-11-18). Die 16.122 Dateien wurden erneut hashverifiziert in den aktiven Programmordner übernommen; **erneuter Headless-Smoke direkt aus der aktiven Runtime bestanden**. Der alte Programmordner bleibt außerhalb des Repositories als vollständiger Rückfall erhalten. Authenticode weiterhin `NotSigned`.
- Die zuletzt gefundenen F821-/F401-Fehler wurden behoben; die breiteren Stilwarnungen und Duplikatstellen sind nicht vollständig beseitigt.
- Die lokalen Workflow-/Testregressionen sind behoben: Die private V3-Matrix wird bei fehlender autorisierter Evidence sauber übersprungen, der Calibration-Browser nutzt einen Playwright-kompatiblen Ubuntu-Runner und der Windows-Startvertrag beendet erfolgreiche Prüfungen mit Exit 0. Für den geprüften Code-Stand sind die GitHub-Actions-Läufe `tests` (44527239634), `security` (44527239650) und `Structure` (44527239616) erfolgreich.
- Frische lokale `npm audit --audit-level=high`-Prüfungen für Docs-Site, Oracle und Frontend melden **0 High/Critical Findings**; die früheren 11/4-Befunde sind für den aktuellen Lockfile-Stand nicht reproduzierbar.
- Layout- und Source-only-Gates sind im öffentlichen Checkout erfolgreich: `verify_repository_layout.py` und `workspace_refs.py --source-only --strict`.

### Noch nachzuweisen oder abzuschließen

1. **GitHub Actions:** Die Workflows enthalten ausführbare Schritte, die bekannten öffentlichen Regressionen sind korrigiert und die drei maßgeblichen Läufe (`tests` 44527239634, `security` 44527239650, `Structure` 44527239616) sind erfolgreich abgeschlossen.
2. **Produktrealität (BLOCKED/external):** Windows-GUI mit Fokus/DPI, echtes Mikrofon/WASAPI/Systemaudio, lange parallele Live-Sessions und echte Provider-Logins inklusive Privacy-First und nutzerautorisierter Kosten separat abnehmen. Automatische Lab- und Unit-Tests ersetzen diese Prüfungen nicht.
3. **Releasefreigabe (BLOCKED/external):** Authenticode-Signatur mit gültiger Herausgeberidentität, Produkt-/R2-Updateveröffentlichung und Freigabe fehlen. Nicht heimlich mit Testschlüsseln publizieren.
4. **Security-Abhängigkeiten:** Der aktuelle Lockfile-Stand ist lokal sauber: Docs-Site, Oracle und Frontend melden bei `npm audit --audit-level=high` jeweils **0 High/Critical Findings**. Der Security-Lauf 44527239650 ist ebenfalls erfolgreich.
5. **Weitere Codequalität:** 67 jscpd-Duplikatstellen (großteils Tests), 220 breite Ruff-Stilwarnungen sowie große LLM-/Audio-/Orchestrator-Funktionen gezielt und regressionsgesichert behandeln. Keine riskante Massentransformation bei laufender Releaseabnahme.

### Verbindlicher Ablauf für zukünftige Arbeit

Quellcode, Tests, Lockfiles und gesetzlich erforderliche Lizenzen bleiben in `app/`; installierte Laufzeiten und regenerierbare Artefakte gehören nach `DebateAI_Generated/` oder in einen isolierten Buildbereich. Vor jeder Löschung tatsächliche Referenzen und Wiederherstellbarkeit prüfen. Keine privaten Benutzerdaten, externen Secrets, Git-Historie oder optionalen Modellpfade blind entfernen.

Aktuelle Kommandos und Releasebedingungen stehen im [Handbuch](HANDBUCH.md); dieser Status ersetzt die älteren Windows-/Codex-Aufträge ausdrücklich.

## Herkunft und geschützte Nachweise

- Die historische V6-Vision stammt aus `d07a658:source/docs/DEBATE_AI_VISION_FINAL.md`.
- Die früheren privaten technischen Fortschritts- und Acceptance-Protokolle wurden in die historische Zusammenfassung überführt und aus dem aktiven Projektbaum entfernt. Die unabhängige Audit-Kopie bleibt außerhalb des Projekts geschützt.
- Lokale Providerprofile, Transkripte, Audiodaten, Credentials, Runtime-Dateien und private Evidence bleiben außerhalb dieser drei redaktionellen Quellen.
- `RESEARCH_DE.md` und `RECONCILIATION_MATRIX_DE.md` sind in diese Historie eingearbeitet und werden nicht mehr als eigenständige Quellen gepflegt.

---

## Konsolidiertes Archiv der ausgedünnten Dokumente

Die folgenden Abschnitte bewahren frühere Arbeitsstände, Übergaben und Verträge, deren operative Inhalte in `HANDBUCH.md` oder den drei Kerntexten aufgegangen sind. Sie gelten als Provenienz und ändern den aktuellen Produkt- oder Releasevertrag nicht.

### Archivierte Prompt-Matrix

Quelle: `PROMPT_MATRIX_B.md`.

Basis-SHA: `445ee4a6eb5d1fb271e485aa132a6031e2b26db1`
Branch: `feat/prelive-prompt-quality`

Die Matrix beschreibt die zur Laufzeit verwendeten Promptressourcen und die
zusätzlichen Code-Prompts, die nicht als eigene Datei vorliegen. Hashes sind die
SHA-256-Kurzform des aktuellen Textes (12 Zeichen). Ein Prompt gilt als aktiv,
wenn `load_prompt_resource`, `active_prompt`, ein Agent-Konstruktor oder ein
Router ihn zur Laufzeit lädt. `experimental_integrator_v1` ist als Altlast
markiert: Die Integration geschieht aktuell deterministisch im Python-
Orchestrator und lädt diese Datei nicht.

| Name | Aufgabe | Datei/Codepfad | aktives Modell | Eingaben | Ausgabeformat | Version/Hash | bekannte Schwächen | geplante Tests | Bewertung |
|---|---|---|---|---|---|---|---|---|---|
| `debate_live_v2` | lokale Sofortantwort | `app/ai/debate_live_v2.txt`, `objection_handler.py` | lokales Debattenmodell | Kontext, Sprecher, Direktiven, Transkriptfenster | JSON-Recommendation | `b836b11580ae` | ASR-Fehler und Negationen bleiben modellabhängig | Contract, Benchmark, Live-Replay | aktiv, verbessert |
| `debate_deep_v1` | tiefe Claim-Analyse | `app/ai/debate_deep_v1.txt` | externe Tiefenanalyse/Fallback | Claim, Nutzerposition, Verlauf, Belege | JSON/strukturierte Analyse | `3abb7b59a10f` | langsam; darf Live-Antwort nicht blockieren | Promptvertrag, Deep-Replay | aktiv |
| `agent.objection_handler` | Argument-Agent und lokale Rhetorik | `app/ai/agent.objection_handler.txt`, `objection_handler.py` | konfiguriertes Textmodell | Live-Kontext, Einwände, Sprecher, Direktiven | Recommendation + Items | `d20ab1b79529` | Modell-/Providerqualität schwankt | Promptvertrag, Debattenfälle | aktiv |
| `agent.consolidated_analyst` | Fakten-/Kontextanalyse | `app/ai/agent.consolidated_analyst.txt` | Agentmodell | Meetingkontext, Fenster, Linsen, Sprecher | Insight-JSON | `a172b45b07f4` | Lens-Konfiguration kann überladen | Agent- und Lens-Tests | aktiv |
| `agent.synthesizer` | Zusammenführung und Qualitätskontrolle | `app/ai/agent.synthesizer.txt` | Synthesizer-Modell | Kontext, Insights, Transkript | Synthese-JSON | `d28b0501c9e2` | nachgelagerte Latenz | Synthesizer-Tests | aktiv |
| `agent.opportunity_specialist` | Angebotsabgleich | `app/ai/agent.opportunity_specialist.txt` | DB-/Textmodell | Kontext, Wissensbasis, Chancen | Insight-JSON | `60bce4e376b0` | nur aktiv bei belastbarer Wissensbasis | Opportunity-Tests | aktiv |
| `agent.strategic_signals` | strategische Live-Signale | `app/ai/agent.strategic_signals.txt` | Textmodell | Kontext, Sprecher, Direktiven, Verlauf | Signal-JSON | `ea57ab716420` | Inferenzrisiko bei dünnem Verlauf | Signal-Tests | aktiv |
| `agent.transcript_refiner` | ASR-Text säubern | `app/ai/agent.transcript_refiner.txt` | Refiner-Modell | Transkriptzeilen | JSON/Textvertrag | `ab12d1a64899` | darf keine Wörter verändern | Refiner-/Placeholder-Tests | aktiv |
| `agent.audio_gateway` | stille Audioweiterleitung | `app/ai/agent.audio_gateway.txt` | Audio-Gateway | Audiospur | keine eigene Ausgabe | `0716f8b6cf8f` | keine Analyse erlaubt | Audio-Gateway-Tests | aktiv |
| `agent.brief_meeting_lens` | sachliches Nachdebattenprotokoll | `app/ai/agent.brief_meeting_lens.txt` | Briefing-Modell | Kontext, Sprecher, Transkript | Briefing-JSON | `4feefbeddb30` | nachgelagert | Briefing-Tests | aktiv |
| `agent.brief_discovery_lens` | Sensemaking/Fragen | `app/ai/agent.brief_discovery_lens.txt` | Briefing-Modell | Kontext, Sprecher, Insights, Transkript | Briefing-JSON | `86b1808c1a23` | Sales-Inferenz vermeiden | Briefing-Tests | aktiv |
| `agent.brief_arbiter` | zwei Briefing-Linsen versöhnen | `app/ai/agent.brief_arbiter.txt` | Briefing-Modell | beide Linsenergebnisse, Kontext | Briefing-JSON | `95c4521ee6dc` | Konflikte/Unsicherheit explizit halten | Arbiter-Tests | aktiv |
| `experimental_debate_live_v1` | experimentelle lokale Debatte | `app/ai/experimental_debate_live_v1.txt` | experimentell konfiguriert | Live-Kontext, Sprecher, Einwände | JSON | `d824af734519` | experimentell; kein Live-SLA | Experimental-Tests | aktiv experimentell |
| `experimental_research_v1` | experimentelle Recherchelane | `app/ai/experimental_research_v1.txt` | externe Lane | Claim, Quellenkontext | JSON | `476edf1ccb98` | ChatGPT-Web-Lock kann seriell wirken | Lane-/Lock-Tests | aktiv experimentell |
| `experimental_adversarial_v1` | Gegenprüfung/Double Standards | `app/ai/experimental_adversarial_v1.txt` | externe Lane | vollständiger Verlauf, Claim | JSON | `007bb1d63056` | keine neue Position ohne Claim | Lane-Tests | aktiv experimentell |
| `experimental_strategist_v1` | sprechbare Strategie | `app/ai/experimental_strategist_v1.txt` | externe Lane | Claim, Verlauf | JSON | `e5d5e4fd8bed` | keine persönliche Attacke | Lane-Tests | aktiv experimentell |
| `experimental_integrator_v1` | historische externe Integrationsstufe | `app/ai/experimental_integrator_v1.txt` | keines | — | — | `cfe2173b3711` | ungenutzt; Integration ist Python-Code | Nicht-Lade-Test | veraltet/ungenutzt |
| `background.oracle` / `.gemini` / `.gpt6` | gleiche Hintergrundanalyse | `app/ai/background.*.txt` | jeweiliger Provider | Claim, Position, Verlauf, Belege | strukturierte Analyse | `2744492ae6f6` | byte-identische Duplikate | Hash-/Routing-Test | aktiv, doppelt |
| `research_source_system` | Quellenrecherche-Rolle | `app/ai/research_source_system.txt`, `debate_research.py` | Rechercheprovider | Claim/Query | Quellen-JSON | `cb63d6620e0a` | Snippets sind kein Beleg | Quellen-/Halluzinationstests | aktiv |
| `research_source_refinement` | verifizierte Quellen in Sprechtext | `app/ai/research_source_refinement.txt` | Rechercheprovider | Empfehlung, Target-Claim, Auszüge | Empfehlung-JSON | `1090b896051c` | Zeitraum/Grundgesamtheit prüfen | Quellenbindungstests | aktiv |
| `transcript_refiner_system` | unverändernde Transkriptkorrektur | `app/ai/transcript_refiner_system.txt` | Refiner | ASR-Zeilen | korrigierter Text | `c1e415e9856e` | keine Wortänderung | ASR-Contract-Tests | aktiv |
| `batch_transcription` | Batch-ASR-Anweisung | `app/ai/batch_transcription.txt` | ASR-/Cloudprovider | Audio/Segmente | Transkript | `eacf6b56cc16` | Modellverfügbarkeit | Transkriptions-/ASR-Tests | aktiv |
| `gemini_live_gateway` | Live-Audio-Gateway | `app/ai/gemini_live_gateway.txt` | Gemini Live | Audio, Session | Gateway-Events | `d8ff13573e96` | Cloudzustimmung/Verfügbarkeit | Adapter-Tests | aktiv |
| `analyze_transcript` | importiertes Transkript | `app/ai/analyze_transcript.txt` | Analysemodell | Kontext, Direktiven, Transkript | Insight-JSON | `7c9d68b75a8f` | Batch, nicht Live | Analyzer-Tests | aktiv |
| `live_chat_system` / `postcall_chat_system` | Chatrollen | `app/ai/*.txt`, Router | gewähltes Modell | Kontext/Frage/Verlauf | Chattext/JSON | `868e00b0f4a7` / `b65fba9ada59` | Kontextlänge | Chat-Tests | aktiv |
| `speaker_context_enhancement` | Sprecherkorrektur neu bewerten | `app/ai/speaker_context_enhancement.txt` | Analysemodell | Sprecher, Insights, Transkript | Operations-JSON | `fe2c1ca1e6e2` | keine Änderungen an dismissed items | Speaker-Tests | aktiv |
| `debate_review_system` / `_task` | Nachdebatten-Review | `app/ai/debate_review_*.txt` | Reviewmodell | Debatte, Quellen, Nutzerfreigabe | Review-JSON | `36b1ffb53118` / `0751ec82d890` | nur nach Bestätigung | Review-Tests | aktiv |
| `debate_user_loyalty` | Position bewahren | `app/ai/debate_user_loyalty.txt` | lokales Modell | Nutzerposition/Claim | Zusatzinstruktion | `074e83b05175` | Loyalität darf Fakten nicht verfälschen | Loyalty-Tests | aktiv |
| `mode.forceful` / `.persuasive` | rhetorische Modi | `app/ai/mode.*.txt` | lokales Modell | Modus, Claim, Kontext | Zusatzinstruktion | `3d26eb2d9f03` / `3410fb3e5ca2` | Schärfe sachlich begrenzen | Mode-Tests | aktiv |
| `style.natural` / `.concise` / `.evidence` | Stilregeln | `app/ai/style.*.txt` | lokales Modell | Antwortentwurf | Zusatzinstruktion | `5933e0f0dfa4` / `0dc87d17189e` / `98e3d9144e0d` | Stil kann sich widersprechen | Style-Tests | aktiv |
| `analogy.required` / `.optional` | Analogiepflicht | `app/ai/analogy.*.txt` | lokales Modell | Claim/Antwort | Zusatzinstruktion | `fc8cbc2b7be0` / `16cd9b766dc5` | keine erfundenen Tatsachen | Rhetorik-Tests | aktiv |
| `phase.new_topic` / `_follow_up` / `_deep_reanalysis` | adaptive Denkstufen | `app/ai/phase.*.txt` | Laufzeitroute | Claim-/Kontextstatus | Zusatzinstruktion | `1e6db0e9ed5f` / `99b4541375d1` / `a5f9a58f2e49` | Aufwand bei Themenwechsel | Adaptive-Tests | aktiv |
| `app/backend/app/services/agents/prompts.py` | viele feste Agentensysteme | Python-Konstanten | je Agentroute | je Rolle definierte Felder | JSON-Schemata | Code-Hash im Commit | nicht vollständig dateibasiert | Prompt-/Agenttests | aktiv im Code |
| `objection_handler.py`-Instruktionen | Forschungs-/Modus-/Strategieappendices | Python-Konstanten | lokales/externe Modelle | Claim, Kontext, Einstellungen | JSON | Code-Hash im Commit | dynamische Kombinationen | Objection-/Mode-Tests | aktiv im Code |
| `debate_research.py`-Systemtexte | Quellenprüfung | Python-Code | Rechercheprovider | Query, Quellen | Recherche-JSON | Code-Hash im Commit | externe Quellenlatenz | Research-Tests | aktiv im Code |
| `local_fit.py`-Systemprompt | lokaler Modellvergleich | Python-Code | lokale Textmodelle | Debattenfälle | Fit-/Benchmarkdaten | Code-Hash im Commit | CPU/RAM/GPU abhängig | Local-Fit-Tests | aktiv im Code |

### Doppelte oder veraltete Ressourcen

- `background.oracle`, `background.gemini` und `background.gpt6` sind byte-identisch; sie bleiben vorerst als modellabhängige Routingnamen erhalten.
- `app/ai/playbooks.json` und `app/ai/defaults/playbooks.json` sind identisch. Die Defaultkopie bleibt als Reset-/Migrationsquelle getrennt; der Endpoint `/api/ai-config/prompts/rhetoriciq.playbooks/reset` liest sie explizit.
- `app/ai/debate_deep_v1.txt` und `app/ai/defaults/prompts/debate_deep_v1.txt` sind identisch. Die Defaultkopie bleibt als Resetquelle für benutzerdefinierte Prompts erhalten.
- `experimental_integrator_v1.txt` wird nicht geladen; die Datei bleibt als historische Referenz erhalten.
- Die aktive und Defaultfassung von `debate_live_v2` wurden in B vereinheitlicht; die neue Hash-Version ist `b836b11580ae`.

### Archivierte Arbeitsstrang-B-Übergabe

Quelle: `TRACK_B_HANDOFF.md`.

### Änderungsstand

- Basis-SHA: `445ee4a6eb5d1fb271e485aa132a6031e2b26db1`
- Branch: `feat/prelive-prompt-quality`
- Arbeitsbereich: eigener Worktree `/workspace/scratch/01cefca878b0/worktree-b`
- Ziel: kontrollierte Promptqualität, zugängliches A/B-/Sprachlabor, Videolink-UI und nachvollziehbare Übergabe an Integrationsdurchgang C.

### Gelieferte Funktionen

#### Promptqualität und Optimierung

`app/backend/app/services/prompt_optimization.py` ist ein providerunabhängiger,
kontrollierter Store. Er vergleicht dieselben `fixed`- und `holdout`-Fälle,
aggregiert Natürlichkeit, Faktentreue, argumentative Stärke, Quellenredlichkeit,
Sprechbarkeit/Nutzbarkeit, Latenz und Kosten und verweigert die Aktivierung bei
fehlenden Fällen oder Regressionen. Vorschläge werden mit Inhaltshash,
Baseline-Hash, Grund, Risiken, Quellen und Zeitstempel protokolliert.

Der Standardpfad bleibt Vorschlag beziehungsweise manuelle Freigabe. Auto-Apply
muss sowohl in der Policy als auch durch eine ausdrückliche Aktivierung gesetzt
werden. Das Änderungsbudget ist standardmäßig klein. Aktivierung und Auditdatei
werden atomar geschrieben; bei einem Schreibfehler wird der vorherige Prompt
wiederhergestellt. `rollback()` ist jederzeit möglich. `rollback_if_regressed()`
prüft zusätzlich den aktiven Hash und verhindert, dass ein inzwischen manuell
geänderter Prompt überschrieben wird. Platzhalter laufen vor der Aktivierung
durch die vorhandene Produktionsvalidierung.

`video_eval_autotune.py` bietet jetzt Fixture-Normalisierung,
`compare_evaluations`-Entscheidung, report-only-Ausgabe und explizit gated
`apply_prompt_proposal`/`apply_optimization`-Wrapper. Ohne Freigabe entsteht
keine Mutation. Die bestehende Video-Pipeline und Batch-Verarbeitung bleiben
unverändert.

Die aktive Live-Promptfassung wurde mit der Defaultfassung vereinheitlicht: Das
`counterargument` muss die Antwort mit dem stärksten ehrlichen Grund stützen und
niemals dagegen argumentieren; `analogy` erklärt die entscheidende Logik. Der
Vertragstest prüft außerdem kurze sprechbare Antworten, Claim-Zielgenauigkeit,
Negationen und das Verbot erfundener Fakten.

#### Labor und Desktop

Der neue Admin-Tab `Labor` enthält:

- blindes A/B-/Sprachlabor mit zwei tatsächlich verfügbaren Modellen oder Promptvarianten,
- gleiche Eingabe, Quellen und Datensatz-ID, optional unabhängiger Holdout,
- wechselnde, deterministische A/B-Reihenfolge und Reveal erst nach gespeicherter Bewertung,
- Bewertungen für Natürlichkeit, Stärke, Präzision, Quellenredlichkeit und Nutzbarkeit,
- „beide ungeeignet“, Export, Latenz-/Kosten-/Prompt-Hash-Anzeige,
- kontrollierte Übernahme und Rollback sowie Rater-Übereinstimmung aus dem Backend,
- Videolink-Card gegen den vereinbarten `/api/video-eval/jobs...`-Vertrag mit
  Statusanzeige, Gemini-Fallback-Einwilligung, Abbruch und Artifact-Ansicht.

Die API-Funktionen zeigen Providerfehler sichtbar an und behaupten keinen
Live-Erfolg, wenn das Backend oder ein Cloudmodell nicht verfügbar ist.

### Prompt-Matrix und Forschung

Die vollständige Matrix steht im archivierten Abschnitt dieses Dokuments.
Sie unterscheidet aktive, experimentelle, doppelte und ungenutzte Ressourcen und
führt Eingaben, Ausgabeformate, Modellroute, Hash, Schwächen, Tests und Bewertung
auf.

Verwendete überprüfbare Referenzen:

- OpenAI, *Evaluation best practices*: https://developers.openai.com/api/docs/guides/evaluation-best-practices
- OpenAI, *Agent evals*: https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI, *Graders*: https://developers.openai.com/api/docs/guides/graders
- Shi et al., *Judging the Judges*, IJCNLP-AACL 2025: https://aclanthology.org/2025.ijcnlp-long.18/
- Findings of EMNLP 2025, multi-agent judge bias: https://aclanthology.org/2025.findings-emnlp.941/
- OpenAI, *Whisper*: https://cdn.openai.com/papers/whisper.pdf

Die Entscheidungen daraus sind im Code sichtbar: feste Datensätze, Holdouts,
blinde Reihenfolge, getrennte Qualitätsdimensionen, keine alleinige Bestätigung
durch den vorschlagenden Judge und kontinuierliche Auditdaten.

### Geänderte Dateien

- `app/ai/debate_live_v2.txt`
- `app/ai/defaults/prompts/debate_live_v2.txt`
- `app/backend/app/services/prompt_optimization.py`
- `app/backend/scripts/video_eval_autotune.py`
- `app/backend/tests/test_prompt_optimization.py`
- `app/backend/tests/test_video_eval_autotune_controlled.py`
- `app/backend/tests/test_ai_prompt_contracts.py`
- `app/frontend/src/components/AdminPanel.tsx`
- `app/frontend/src/components/QualityLabCard.tsx`
- `app/frontend/src/components/QualityLabCard.test.mjs`
- `app/frontend/src/components/VideoEvalCard.tsx`
- `app/frontend/src/components/VideoEvalCard.test.mjs`
- `app/frontend/src/lib/qualityLab.ts`
- `app/frontend/src/lib/qualityLab.test.mjs`
- `app/frontend/src/services/api.ts`
- `HISTORIE.md`
- `TRACK_B_HANDOFF.md`

### Verifikation

- `PYTHONPATH=app/backend python -m unittest tests.test_prompt_optimization tests.test_video_eval_autotune_controlled`: **10/10 bestanden**.
- `PYTHONPATH=app/backend python -m unittest tests.test_ai_prompt_contracts`: Promptvertrag und Live-Qualitätsvertrag bestanden.
- Frontend `npm test`: **377/377 bestanden**.
- Frontend `npm run build`: **Exit 0**; Vite meldet weiterhin die bekannten Chunk-Größenwarnungen.
- `python -m py_compile app/backend/app/services/prompt_optimization.py app/backend/scripts/video_eval_autotune.py`: bestanden.
- Breitere Backendtests, die SQLAlchemy/Google-Provider importieren, konnten in der Minimalumgebung nicht geladen werden, weil diese optionalen Testabhängigkeiten dort fehlen. Sie wurden nicht als bestanden gezählt.

### Integrationshinweise für C

1. Die Quality-/Video-Lab-Routen sind im Frontend typisiert, aber absichtlich noch
   nicht in der zentralen Backend-Routerregistrierung enthalten. C soll die
   vorhandenen Verträge implementieren und die Mocks durch echte, fail-closed
   Provider-/Jobdienste ersetzen.
2. Für Promptübernahmen soll C `PromptOptimizationStore(ai_config.ai_directory())`
   verwenden und `approved_by_user` beziehungsweise beide Auto-Apply-Schalter
   explizit setzen. `user_managed=True` schützt persönliche Prompts.
3. `experimental_external_parallelism` beschreibt logische Lanes. Der
   ChatGPT-Webadapter bleibt exklusiv gesperrt; die UI darf daraus keine drei
   parallelen Browserzugriffe ableiten.
4. Die lokale Sofortantwort bleibt zeitkritisch und darf nicht auf einen externen
   Judge, Holdout-Lauf oder Videolink-Job warten.
5. A kann die Videobeweis-Persistenz und Backendjobs an den UI-Vertrag anschließen,
   ohne die in B geschützten Promptdateien, Store-Auditdaten oder Frontendtests
   zu überschreiben.
6. Persönliche Promptdateien und Playbooks bleiben updatefest; keine Seed-/Reset-
   Routine darf sie still ersetzen.

### Nachpr?fung und Korrekturcommit (20.11.2026)

Die urspr?ngliche Lieferung deckt **nicht** alle Punkte des umfangreichen B-Auftrags ab.
Die Lab-Backendrouten, der vollst?ndige ASR-Vergleich (WER/CER/RTF ?ber alle
verf?gbaren Modelle), echte Live-/Holdout-Benchmarkdaten und die End-to-End-
Integration mit A stehen weiterhin aus. Der UI-Vertrag ersetzt keinen
funktionsf?higen Jobdienst. Es wurden keine Cloudmodelle kostenpflichtig aufgerufen.

In der Nachpr?fung wurden konkrete Schutzl?cken behoben:
- Fehlende Qualit?tsdimensionen auf einer Vergleichsseite verhindern eine
  Freigabe, statt als impliziter Nullwert in den Mittelwert einzugehen.
- Eine einzelne Raterbewertung hat keine messbare ?bereinstimmung (null).
- Eine produktive ?bernahme aus dem A/B-Labor ist bei Gleichstand oder
  ungeeigneten Antworten deaktiviert und erfordert eine zus?tzliche Best?tigung.

Gezielte Nachtests: 9 Backend-Optimierungstests und 6 Frontend-Labortests
bestanden. Der Repository-Layout-Guard meldete 1101 zul?ssige Dateien.
Nicht verifizierte gr??ere Test- und Produktionsbuilds werden nicht als
bestanden ausgegeben.

### Archivierter Windows-Recovery-Vertrag

Quelle: `windows-final-recovery.md`.

Stand 2026-11-11. Der fruehere ZIP-Overlay-Weg wird durch direkte Git-Integration ersetzt. Kein apply_package.py und keine alte final_sync_safety.py ueber den neueren integrierten Source kopieren. Der aktuelle single-file sync_final_workspace.py enthaelt seinen Kollisionsschutz bereits vor Stash/Merge/Rebase.

### Sichere Programmaktualisierung

Die alte funktionierende Installation bleibt erhalten, bis neues Archiv und Staging vollstaendig verifiziert sind. Staging auf demselben Dateisystem wie das Installationsziel anlegen, vorhandene validierende Archive-/Updaterfunktion nutzen, nur Programmdateien tauschen. Aktive Aufnahme/Verarbeitung abwarten und eigene Prozesse sauber beenden. Keine pauschalen Remove-Item- oder git-clean-Befehle. Bei Fehler vor Tausch bleibt alte Version unangetastet; bei Startfehler nach Tausch alte Binaerdateien zuruecksetzen. Den Health-Nachweis an die neue Instanz binden, nicht irgendein bereits laufendes Backend als Erfolg akzeptieren.

### Daten sind ein eigener Rueckweg

Migriere %LOCALAPPDATA%\Backchannel einmalig nach %LOCALAPPDATA%\DebateAI; lösche die Quelle nicht und überschreibe keinen nichtleeren Zielordner. PostgreSQL, master.key/DPAPI, AI-Prompts/Playbooks, Browserprofile, API-/OAuth-Sessions, Transkripte und Modelle niemals loeschen. Eine laufende DB-Dateikopie ist kein konsistenter Backup. Vor Schemaaenderung den vorhandenen kontrollierten Backupweg oder gestoppte DB nutzen und Wiederherstellbarkeit pruefen. Binaerrollback ist kein Schemarollback. Zwei verschiedene Programmversionen duerfen nicht parallel denselben Datenbestand benutzen. Kein automatisches Verschmelzen zweier nichtleerer Datenordner.

### Konfiguration und Produktidentitaet

Neue Defaults, bisherige Baseline und aktive Benutzerkopie semantisch zusammenfuehren. Ein EXE-Update ersetzt absichtlich keine angepassten Prompts. Aktiven Pfad/Generation/Profile/Trigger via Anwendung pruefen. Exe-/Updater-/Archivnamen erst als zusammenhaengenden Vertrag migrieren; historische Lizenz-/Herkunftshinweise bleiben.

### Testlabor und Grenzen

Laborassets und Navigation sind integriert. Der Produktions-Paarbenchmark benchmark_blind_pair.py ist implementiert, benoetigt aber die aktuelle App-Projektumgebung und ein bewusst beendetes Desktopprogramm. Er ist kein neuer Installer oder in die EXE eingebauter Generierungsbutton. Fehler, Timeouts und unbewertete Skalen bleiben ehrlich. Ein synthetischer Browsertest oder Headless-Replay ist keine deutsche Hardware-/Sprachabnahme.

Die aktuellen lokalen Build- und Wiederherstellungsschritte stehen in releasing.md. Signierter Release nur mit realem Zertifikat, unabhaengigem Kanal und erfolgreichem Protokoll; keine erfundene Freigabe.

### Zusammengeführte technische und redaktionelle Nebenakten

Die technischen Nebenakten `DEBATEAI_CANONICAL_INDEX.md`, `workspace-audit.md`, `workspace-layout.md`, `github-repository.md`, `identity-decoupling-design.md`, `local-first-text-contract.md`, `static-analysis.md`, `static-analysis-triage.md` und `website-claim-matrix.md` wurden als aktuelle technische Abschnitte in `HANDBUCH.md` konsolidiert. Ihre historischen Entscheidungen und offenen Grenzen bleiben über die datierten Abschnitte in diesem Dokument nachvollziehbar.

## Archivierte Arbeitspläne und Übergaben

Die folgenden Planungs- und Übergabedokumente waren zeitgebundene Arbeitsunterlagen. Ihre Entscheidungen und Ergebnisse sind in den aktuellen Kerntexten oder im Handbuch berücksichtigt. Sie bleiben hier als Provenienz erhalten.

### TRACK_A_HANDOFF.md

Quelle: `HISTORIE.md`.

# DEBATEAI – Arbeitsstrang A Übergabe

Stand: 2026-11-20 (Europe/Vienna)
Basis-SHA: `445ee4a6eb5d1fb271e485aa132a6031e2b26db1`
Branch: `feat/prelive-video-evidence`
Arbeitsverzeichnis: eigener Worktree `worktree-a`

## Ergebnis

Arbeitsstrang A ergänzt den bestehenden Offline-Video-Evaluationspfad um einen
link-first, consent-aware Jobpfad:

1. Öffentliche HTTPS-URL wird validiert (keine Credentials, Sonderports,
   lokale/private DNS-Ziele); yt-dlp wird mit `skip_download`, manuellen und
   automatischen Untertiteln sowie begrenzter Sprachwahl nur zur Metadaten- und
   Track-Ermittlung aufgerufen.
2. Manuelle Untertitel werden vor automatischen Untertiteln ausgewählt und ohne
   Videodownload abgerufen. VTT/SRT/TTML-artige Cue-Texte werden in stabile,
   deutsche, zeitgestempelte Segmente mit Sprecherfeldern normalisiert.
3. Ohne parsebares Transkript entsteht `awaiting_consent` mit dem Hinweis
   „Kein Transkript verfügbar“. Eine Zustimmung für `gemini_api` ist nötig,
   bevor der alternative Gemini-Weg aufgerufen wird. Fehlender Schlüssel,
   nicht unterstützte URL und Providerfehler bleiben verständliche lokale
   Fehlerzustände.
4. A1 (`rhetorical_evidence`) und A2 (`argument_evidence`) entstehen getrennt,
   versioniert und segmentbezogen. A1 liefert Metriken/Testfälle ohne
   Promptänderung. A2 verwendet Claims, Quell-IDs und die Zustände
   `mentioned`, `found`, `retrieved`, `supports`, `contradicts`, `unclear`,
   `unavailable`.
5. JSON-Checkpoints und Artefakte werden atomar unter dem lokalen
   `DATA_DIR/video-eval`-Pfad gespeichert. Job-Token schützen Status, Consent,
   Abbruch und Artefaktzugriff. Doppelte aktive URL-/Sprachanfragen werden
   wiederverwendet; neuere Checkpoints überschreiben keine abgeschlossenen
   Ergebnisse.
6. `video_context.py` segmentiert lange Transkripte token- und zeichenbewusst,
   mit Satz-/Sprechergrenzen, stabilen Chunk-IDs, begrenzter Überlappung,
   Checkpoints, Antwortvalidierung und einem Rollover-Workflow. Nur
   `message-too-large` und `context-full` dürfen einen autorisierten neuen Chat
   auslösen; Rate-Limits, Login, CAPTCHA und belegte Browserprofile werden
   niemals durch Chatwechsel umgangen.

## Geänderte und neue Dateien

- `app/backend/app/services/video_eval_pipeline.py` – rückwärtskompatible
  Artefaktfelder `artifact_schema_version`, `rhetorical_evidence`,
  `argument_evidence`, `provenance`.
- `app/backend/app/services/video_eval_jobs.py` – URL-/DNS-Prüfung, yt-dlp-
  Probe, Untertitelabruf/-normalisierung, Gemini-Fallback, A1/A2-Auswertung,
  lokale Job-/Artefaktpersistenz, Consent und Abbruch.
- `app/backend/app/services/video_context.py` – lange Kontextsegmente,
  Fehlerklassifikation, Checkpoints, Merge/Deduplizierung und kontrollierter
  Kontextwechsel.
- `app/backend/app/routers/video_eval.py` – additive API-Routerdefinition.
- `app/backend/scripts/video_eval_batch.py` – Linkeingänge nutzen zuerst
  Untertitel; bei fehlendem Transkript wird kein stiller Cloud-Upload ausgelöst.
- `app/backend/tests/test_video_eval_jobs.py` – Untertitelreihenfolge,
  Normalisierung, Consent, fehlender Gemini-Key und Artefaktzugriff.
- `app/backend/tests/test_video_eval_router.py` – API-Vertrag und Token-Scope.
- `app/backend/tests/test_video_context.py` – Chunking, Overlap,
  Fehlerklassen, Rollover, Checkpoints und Secret-Scrubbing.
- `HISTORIE.md` – API-/Artefaktspezifikation
  für Arbeitsstrang B.

## API-Vertrag

Die Endpunkte sind im Router implementiert:

- `POST /api/video-eval/jobs` mit `{url, language}`
- `GET /api/video-eval/jobs/{id}`
- `POST /api/video-eval/jobs/{id}/consent` mit
  `{provider: "gemini_api", approved}`
- `POST /api/video-eval/jobs/{id}/cancel`
- `GET /api/video-eval/jobs/{id}/artifact`

Alle Job-Status-/Mutation-/Artefaktabfragen verwenden `X-DebateAI-Job-Token`.
Die vollständigen Beispielantworten, Zustände und Mock-Hinweise stehen in
`HISTORIE.md`.

## Tests und Verifikation

Erfolgreich:

```text
python -m compileall -q app/backend/app app/backend/scripts app/backend/tests
```

Zusätzliche lokale Smoke-Prüfungen decken VTT/SRT-Normalisierung, manuelle
gegen automatische Tracks, `awaiting_consent` → `gemini_key_missing`, lokale
Artefaktspeicherung, A1/A2-Felder und erlaubten Kontext-Rollover ab.

Der Lauf von pytest wurde versucht, ist in der bereitgestellten Runtime aber
nicht möglich, weil `pytest`/`pytest-asyncio` nicht installiert sind:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_video_context.py tests/test_video_eval_jobs.py \
  tests/test_video_eval_router.py tests/test_video_eval_pipeline.py \
  tests/test_video_eval_evaluator.py
# No module named pytest
```

Keine echten Provideraufrufe, Kosten oder Browserlogins wurden ausgelöst.

## Recherchequellen

Zum Implementierungszeitpunkt wurden die offiziellen Primärquellen geprüft:

- yt-dlp README und Python-Embedding:
  <https://github.com/yt-dlp/yt-dlp#usage-and-options> und
  <https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp>
- Gemini Video Understanding:
  <https://ai.google.dev/gemini-api/docs/video-understanding>
- Gemini Audio/Transkription:
  <https://ai.google.dev/gemini-api/docs/audio>
- Gemini Files API:
  <https://ai.google.dev/gemini-api/docs/files>
- Gemini Structured Output:
  <https://ai.google.dev/gemini-api/docs/structured-output>
- Gemini Rate Limits und Preismodelle:
  <https://ai.google.dev/gemini-api/docs/rate-limits> und
  <https://ai.google.dev/gemini-api/docs/pricing>
- YouTube Terms und Developer Policies für öffentliche Inhalte, Zustimmung,
  Löschung und Downloadgrenzen:
  <https://www.youtube.com/t/terms> und
  <https://developers.google.com/youtube/terms/api-services-terms-of-service>

Die Dokumentation weist darauf hin, dass der YouTube-URL-Weg nur öffentliche
Videos verarbeitet, Preview-/Tariflimits sich ändern können und Files-API-
Uploads einen eigenen Processing-/ACTIVE-/FAILED-Lifecycle sowie automatische
Aufbewahrungs- und Löschregeln haben. Die Implementierung hält diese Grenzen
konfigurierbar und überträgt ohne Consent keine Medien.

## Grenzen

- `app/main.py` registriert den neuen Router noch nicht. Das ist absichtlich,
  damit der parallele Integrator C die gemeinsame Routerliste einmalig ändert:
  `from app.routers import video_eval` und
  `app.include_router(video_eval.router)`.
- Der Gemini-Adapter nutzt für öffentliche YouTube-URLs den direkten URI-Weg.
  Files-API-Uploads für andere Plattformen, Status-Polling, vorzeitiges
  `files.delete` und feinere Tarif-/Kostenlimits sind als Erweiterungspunkt
  vorbereitet, aber nicht ohne Providerfreigabe getestet.
- Quellen werden lokal als `mentioned` erfasst. Die vorhandene
  `debate_research`-Verifikation darf C hinter einem expliziten
  Recherche-/Provider-Consent anschließen und danach `retrieved` sowie
  `supports`/`contradicts` setzen.
- Die JSON-Jobpersistenz ist für den bestehenden Single-User-Desktop gedacht.
  Für Multiworker-Serverbetrieb braucht C eine DB-Journal-/Lockschicht oder
  einen dedizierten Worker.
- Der bestehende ChatGPT-Web-Adapter startet pro `generate()` einen eigenen
  Oracle-Prozess und hält einen exklusiven Browserprofil-Lock. Deshalb ist ein
  Chatwechsel im normalen Adapter derzeit nicht nötig; `video_context.py`
  schützt nur tatsächlich wiederverwendete Chats und meldet einen fehlenden
  sicheren Wechsel explizit.

## Integrationsaufgaben für C

1. Router in `main.py` registrieren und die vorhandene Request-/Runtime-
   Middleware prüfen.
2. API-Spezifikation an B übergeben; B kann den Router mit dem dokumentierten
   Mock-Store testen.
3. Bei aktivierter externer Quellenrecherche den bestehenden
   `debate_research.research_claim`-Pfad mit Provider-/Datenklassen-Consent
   verbinden und seine Ergebnisse in A2-Quellzustände mappen.
4. Falls relationale Dauerpersistenz für Jobs/Artefakte erforderlich wird,
   additive Alembic-Migration und Zugriffskontrolle ergänzen; vorhandene
   `VideoEvalArtifact`-JSONs rückwärtskompatibel importieren.
5. Provider-/Browser-Integrationstests mit sicheren Mocks und die fehlende
   Windows-/Desktop-Abnahme getrennt durchführen.

### TRACK_A_VIDEO_EVIDENCE_API.md

Quelle: `HISTORIE.md`.

# Arbeitsstrang A: Video-Evidence-API

Stand: 2026-11-20 · Vertrag für Arbeitsstrang B

Die additive Routerimplementierung liegt in `app/backend/app/routers/video_eval.py`.
Sie wird bewusst nicht automatisch in `app/backend/app/main.py` registriert, weil
`main.py` im parallelen Integrationsdurchgang C gemeinsam gepflegt wird. C kann
den Router mit `app.include_router(video_eval.router)` unter dem bestehenden
`/api`-Präfix aktivieren.

## Zustände und Arbeitsschritte

`status` ist einer von `queued`, `processing`, `awaiting_consent`, `completed`,
`failed` oder `cancelled`. `stage` beschreibt den aktuellen Abschnitt:

`queued` → `validate_url` → `metadata` → `subtitles` → `transcription` →
`ai_analysis` → `source_verification` → `persistence` → `completed`.

Ein öffentlicher Link wird mit yt-dlp-Metadaten geprüft. Die erste Extraktion
setzt `skip_download`, `writesubtitles`, `writeautomaticsub` und eine begrenzte
Sprachliste. Manuelle Untertitel werden vor automatischen Untertiteln verwendet;
ein erfolgreiches Untertitelartefakt setzt `video_downloaded: false`. Fehlt ein
parsebares Transkript, bleibt der Job in `awaiting_consent` und verlangt eine
explizite Zustimmung für `gemini_api`.

## Endpunkte

### `POST /api/video-eval/jobs`

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "language": "de"
}
```

Antwort (`202`):

```json
{
  "id": "vjob_…",
  "status": "queued",
  "stage": "queued",
  "progress": 0.0,
  "artifact_ids": [],
  "access_token": "…",
  "deduplicated": false
}
```

`access_token` ist ein lokales Job-Geheimnis. B sendet es als
`X-DebateAI-Job-Token` bei Consent, Abbruch und Artefaktabruf; es wird nicht in
Logs oder Artefakten gespeichert.

### `GET /api/video-eval/jobs/{id}`

Header: `X-DebateAI-Job-Token: …`

Liefert Status, `stage`, `progress`, `error_code`, `error`, `consent`,
`checkpoints` und verfügbare `artifact_ids`. Der Videolink wird nicht als
zusätzlicher Prompt an einen Provider weitergereicht.

Beispiel für fehlende Untertitel:

```json
{
  "id": "vjob_…",
  "status": "awaiting_consent",
  "stage": "transcription",
  "progress": 0.35,
  "consent": {
    "required": true,
    "provider": "gemini_api",
    "data_class": "video_url",
    "message": "Kein Transkript verfügbar. Gemini-Transkription darf erst nach bewusster Freigabe starten."
  },
  "artifact_ids": []
}
```

### `POST /api/video-eval/jobs/{id}/consent`

Header: `X-DebateAI-Job-Token: …`

```json
{"provider": "gemini_api", "approved": true}
```

Nur `gemini_api` ist für den Fallback zugelassen. Bei Ablehnung endet der Job
mit `consent_denied`; bei fehlendem Schlüssel mit `gemini_key_missing`. Beide
Fehler bewahren Link, Metadaten und Checkpoints lokal.

### `POST /api/video-eval/jobs/{id}/cancel`

Header: `X-DebateAI-Job-Token: …`

Beendet den Job sicher und erhält bereits gespeicherte Checkpoints.

### `GET /api/video-eval/jobs/{id}/artifact`

Header: `X-DebateAI-Job-Token: …`

Liefert nur das lokale strukturierte Artefakt. Ein falsches oder fehlendes Token
führt zu `403`; ein noch nicht abgeschlossenes Artefakt zu `409`.

## Artefaktvertrag

Die bestehenden Felder `video_id`, `source_url`, `transcript_segments`,
`source_candidates`, `verified_sources`, `rhetorical_profile` und `eval_cases`
bleiben erhalten. Link-first Jobs ergänzen:

- `artifact_schema_version: 2` und `provenance` mit URL, Plattform, Abrufzeit,
  Untertitelsprache/-format, Hash und `video_downloaded`.
- `transcript_segments[].segment_id` als stabiler Hash aus Video, Position,
  Zeit und Text.
- `rhetorical_evidence` (A1) mit `analysis_id: rhetoric-v1`, Befunden,
  Segmentbezug und messbaren Testfällen. Es aktiviert keine Promptänderung.
- `argument_evidence` (A2) mit Claim-IDs, Sprecher-/Zeitbezug, Quell-IDs und
  den Zuständen `mentioned`, `found`, `retrieved`, `supports`, `contradicts`,
  `unclear`, `unavailable`.

Transkript- und Untertitelinhalte werden als Daten behandelt. Die lokale Analyse
interpretiert keine Anweisung aus einem Untertitel; Provider-Prompts müssen die
gleiche Datenmarkierung beibehalten.

## Mock-Nutzung in B

B kann den Router in einer kleinen FastAPI-Testanwendung registrieren und den
`video_eval._store` durch einen `VideoJobStore(tmp_path, gemini=FakeGemini())`
ersetzen. Damit bleiben manuelle Untertitel, automatische Untertitel,
Consent-Ablehnung, fehlender Schlüssel, Abbruch und Artefaktzugriff ohne echte
Providerkosten reproduzierbar.

### 2026-11-19-open-items-remediation-plan.md

Quelle: `HISTORIE.md`.

# Open-items Remediation Implementation Plan

> For agentic workers: execute the tasks in order, keep the test ledger current, and do not claim completion without fresh evidence.

## Goal

Make the public checkout pass every reproducible open-item gate while keeping private evidence and production release credentials outside the repository.

## Architecture and tech stack

The changes touch Python unittest contracts, PowerShell release checks, GitHub Actions YAML, Markdown status records, and existing npm workspaces. No runtime dependency or product API is introduced.

## Global constraints

- Work directly on `main` as required by `AGENTS.md`.
- Preserve `.ai` privacy, generated/runtime boundaries, and existing lockfiles.
- Do not create a PR, force-push, publish a release, or invent signing/R2 data.
- Every changed behavior gets a targeted regression check before delivery.

## Tasks

- [x] Keep the V3 matrix test active for authorized private evidence and skip it with an explicit reason in the public checkout.
- [x] Pin the calibration browser job to ubuntu-24.04.
- [x] Make the startup PowerShell contract end with explicit exit 0 after success.
- [x] Fix stale documentation links and refresh the status register.
- [x] Run targeted tests, builds, layout guards, and source-only checks.
- [x] Commit to main and publish the verified tree through the authorized GitHub write path.
- [ ] Obtain a fresh green GitHub run for the delivered SHA; an empty run/status response remains unverified.

## Spec and TDD steps

1. Run the V3 matrix test before the change and capture the missing-private-file failure.
2. Add the optional-path skip, then run the same test and an authorized matrix fixture check.
3. Pin the browser runner and make the PowerShell success exit explicit.
4. Run layout, source-only, docs, frontend, Oracle, and audit checks.
5. Update status documentation only from the resulting evidence.

## Review focus

- A missing private file must never become a false pass for an authorized file.
- The browser runner pin must match the Playwright version in the workflow.
- PowerShell failure paths must remain nonzero; only the completed path exits 0.
- Status wording must distinguish local evidence from GitHub and operator gates.

## Test ledger

- Backend V3 matrix unit test (public and optional private path).
- PowerShell startup/build contract tests where Windows is available.
- Docs-site `npm test`, `npm run build`, and high-severity npm audit.
- Oracle high-severity npm audit and frontend test/build/PWA checks.
- `verify_repository_layout.py` and `workspace_refs.py --source-only --strict`.
- GitHub workflow runs/statuses for the delivered commit.

## Exact commands

```text
python -m unittest app.backend.tests.test_v3_matrix_coverage -v
python app/scripts/verify_repository_layout.py
python app/scripts/workspace_refs.py --source-only --strict
cd app/docs-site && npm test && npm run build && npm audit --audit-level=high
cd app/frontend && npm test && npm run build && npm run test:pwa -- --dist
cd app/desktop/chatgpt_oracle && npm audit --audit-level=high
```

### 2026-11-20-full-open-items-remediation-plan.md

Quelle: `HISTORIE.md`.

# Full Open-Items Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Each task is test-first and ends with fresh verification.

**Goal:** Implement every repository-local, reproducible item in `app/docs/OFFENE_PUNKTE.md`, record external gates that require unavailable credentials/hardware, and leave `main` synchronized locally and remotely.

**Architecture:** Prefer existing contracts and smallest compatible fixes. Group changes by subsystem: docs/site, security/startup, PII/data lifecycle, cross-worker state, API limits/performance, UX/accessibility, CI/release contracts, and evaluation tooling. External operator gates remain explicit blockers rather than fabricated passes.

**Tech Stack:** Python 3.12, FastAPI/SQLAlchemy/Alembic, React/TypeScript, Node test runners/Astro, GitHub Actions, existing PowerShell and repository guard scripts.

**Spec:** `app/docs/OFFENE_PUNKTE.md`, `app/docs/VISION.md`, `AGENTS.md`, and the current repository tests/workflows.

## Global Constraints

- Work directly on `main`; never force-push, rewrite history, or create a PR.
- Preserve `.ai`, `runtime/DebateAI/_internal`, Generated/private-data boundaries, lockfiles, and secrets.
- Do not install new tools or dependencies; use existing packages, scripts, lockfiles, and available CI/remote-device capabilities.
- Every behavior change gets a failing regression test before implementation.
- No claim of signing, hardware, provider, private-ledger, human-rating, or GitHub-billing completion without the required external evidence.
- Update `OFFENE_PUNKTE.md` only after implementation evidence exists; preserve IDs and history.

## Review Focus

- Missing docs paths and stale `master/source` references must fail tests before the docs/site fix.
- Non-loopback API access without an explicit token must remain denied while loopback development remains usable.
- Session deletion must remove remote/local/browser artifacts and PII indexes without breaking retries or reconnect replay.
- Multi-session PII must never use only the first session's roster.
- Cross-worker WS/REST state, pagination limits, migration races, and large reveal bodies must have bounded behavior.
- Standard debate output must preserve turn/revision identity and stale-result handling.

## Tasks

### Task 1: Docs-site and active repository contract

**Files:** `app/docs-site/site.test.js`, `sync-docs.mjs`, `assemble.mjs`, `astro.config.mjs`, active README/docs/site/release references, targeted docs tests.

**Acceptance:** existing docs-site tests and build pass; only existing docs are linked; repository/branch/layout references use `ErpeUser/DebateAI-final-public`, `main`, and `app`; historical examples are labeled.

### Task 2: Startup, LAN-origin, and release branch contracts

**Files:** `app/backend/scripts/start_backend.py`, request guard tests, `app/backend/app/services/request_guard.py` if needed, GPU/quickstart scripts, `app/scripts/release_desktop.ps1`, PowerShell contract tests.

**Acceptance:** default native/GPU start is loopback or token-protected, reload is explicit development-only, foreign private origin without token gets 403, release scripts are branch-aware for `main`.

### Task 3: PII scope and deletion lifecycle

**Files:** chat router/shield/vault/redaction, session/document deletion routers, frontend MeetingChat/App, backend/frontend tests.

**Acceptance:** multi-session protection unions the selected sessions, session deletion is idempotent and queues remote cleanup, local files and sessionStorage are cleared, and global PII indexes have bounded session-aware lifecycle.

### Task 4: Cross-worker state and migration serialization

**Files:** orchestrator/event journal/transcription job registries, migration startup path, integration tests.

**Acceptance:** either shared state or an explicit single-worker/sticky contract is enforced; concurrent startup tests produce one migration head without duplicate/lock errors.

### Task 5: API pagination and bounded chat/reveal processing

**Files:** list routers, schemas, frontend session hook, chat prompt/reveal middleware, API/performance tests.

**Acceptance:** stable limit/cursor defaults protect sessions, transcripts, questions, directives, documents, speakers, and knowledge; prompt/reveal paths have bounded memory and deterministic truncation/413 behavior.

### Task 6: Accessibility and standard debate experience

**Files:** `PiiShieldCard.tsx`, `ConfirmProvider.tsx`, `DebateOverlay.tsx`, live-role orchestration/settings, frontend/backend tests.

**Acceptance:** named controls and focus trap/restore pass DOM/a11y tests; standard mode provides three current alternatives and live strategic signals with revision identity.

### Task 7: CI, dependency baseline, PostgreSQL, and structural gates

**Files:** `.github/workflows/tests.yml`, `structure.yml`, requirements/package manifests only when existing lockfiles support it, CI contract tests/docs.

**Acceptance:** PostgreSQL tests run in a visible job without skip; Sentrux policy distinguishes approved baseline from new violations; reload default and dependency/static-analysis baseline are documented and tested.

### Task 8: Audio race, diagnostics, and evaluation paths

**Files:** audio pipeline, diagnostics/AdminPanel, calibration/A-B UI where existing APIs support it, tests.

**Acceptance:** simultaneous WS/native completions do not drop native data; diagnostics export is redacted; existing calibration API has a documented, reproducible user path or remains explicitly blocked.

### Task 9: External-only gates and final ledger

**Files:** `app/docs/OFFENE_PUNKTE.md` for current gaps and `app/docs/HISTORIE.md` for dated evidence only after evidence.

**Acceptance:** mark only verifiable local items complete; preserve explicit blockers for signing, hardware/provider, private ledger, human ratings, billing, separate repositories, and operator cutover. Run full available test matrix, layout/source guards, review diff, commit to `main`, push through the authorized GitHub write path, and fast-forward the local checkout.

### 2026-11-20-offene-punkte-plan.md

Quelle: `HISTORIE.md`.

# Offene Punkte 2026-11-20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Alle lokal behebbaren Punkte aus `app/docs/OFFENE_PUNKTE.md` auf dem aktuellen `main`-Stand umsetzen, externe Gates mit frischem Evidence/Blocker abgleichen und den Standardbranch verifizieren/synchronisieren.

**Architecture:** Bestehende FastAPI/SQLAlchemy-, React/Vite- und Docs-Site-Verträge bleiben erhalten. Änderungen werden in begrenzten, rückwärtskompatiblen Schichten vorgenommen: query-/memory-budgets im Backend, idempotente Cleanup-/TTL-Lifecycle, reproduzierbare Analyse-/Evidence-Dokumentation und konsistente Produktclaims.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy/Alembic, unittest/pytest, React/Vite, Node test runner, Astro/Starlight, GitHub Actions.

**Spec:** `app/docs/OFFENE_PUNKTE.md` (aktueller Backlog; externe Operator-/Hardware-Gates bleiben als solche ausgewiesen).

## Global Constraints

- Direkte Arbeit auf `main`; kein Force-Push, kein History-Rewrite, kein Feature-Branch.
- Vor Pull/Push `python app/scripts/github_sync.py --pull --strict` ausführen; wenn CLI-Auth fehlt, GitHub-Connector/`git ls-remote` als getrennte Evidence dokumentieren.
- Keine Secrets, echten Providerdaten oder Produktionsartefakte in den Tree schreiben.
- Bestehende API-Kompatibilität und sichere Default-Limits beibehalten.

## Review Focus

- Große Chat-/Reveal-Payloads dürfen weder unkontrolliert im SQL-Query noch doppelt im Worker wachsen.
- Session-Löschung muss lokale, Browser- und externe Artefakte idempotent behandeln und Fehler sichtbar machen.
- Globale Journale/PII-Indizes dürfen nach TTL/LRU-Sweep nicht unbounded wachsen oder zulässiges Reconnect-Replay verlieren.
- Cursor-/Limit-Parameter müssen stabile Tie-Breaker und kompatible Defaults haben.
- Backlog-Status darf nur mit frischen Commit-/Test-/CI-/Device-Belegen aktualisiert werden.

### Task 1: Discovery, ledger und Evidence

**Files:**
- Create: `.superpowers/sdd/2026-11-20-offene-punkte/progress.md`
- Create: `docs/superpowers/plans/2026-11-20-offene-punkte-plan.md`
- Modify: `app/docs/OFFENE_PUNKTE.md`

- [ ] Vollständiges Ledger aller 37 `### P*`-Einträge mit `status_before`, `status_after`, `evidence_or_blocker` erstellen.
- [ ] Aktuellen lokalen SHA, Remote-Head, GitHub-Repo-Metadaten, Actions-Runs und Desktop-Gerät getrennt belegen.
- [ ] Nach jeder Changeset-/Test-/CI-Verifikation die passenden Statuszeilen und Header aktualisieren.

### Task 2: Backend query/memory budgets (P2.8, P2.10)

**Files:**
- Modify: `app/backend/app/routers/chat.py`
- Modify: `app/backend/app/routers/{sessions,transcripts,questions,knowledge,documents,directives,speakers}.py`
- Test: `app/backend/tests/test_chat_prompt.py`, passende Router-/Limit-Tests

- [ ] Failing tests für SQL-seitige Priorisierung, sichere Obergrenzen, stabile Cursor/Tie-Breaker und kontrollierte 413/Truncation schreiben.
- [ ] Implementieren und vollständige Backend-Regression ausführen.

### Task 3: Cleanup outbox/retry and lifecycle bounds (P1.14, P2.12)

**Files:**
- Modify: `app/backend/app/routers/sessions.py`
- Modify: `app/backend/app/services/{pii/vault.py,pii/redaction.py,transcription_jobs.py,ws_event_stream.py}`
- Create/Modify: migrations/models/tests as needed

- [ ] Failing tests für idempotente Provider-Delete-Outbox/Retry, Session-Cleanup, TTL/LRU und zulässiges Replay.
- [ ] Implementieren, ohne externe Provider zu erzwingen; Status/Audit muss sichtbar bleiben.

### Task 4: Migration and single-worker safety (P1.15, P1.16, P2.11)

**Files:**
- Modify: `app/backend/app/main.py`, `app/backend/scripts/start_backend.py`, request-guard tests/docs
- Test: startup/migration/request-guard suites

- [ ] Fehler-/Retry-Matrix für parallele Migrationen und LAN-Origin/Bind-Defaults ergänzen.
- [ ] Bestehende Single-worker-Verträge und Advisory-Lock-Logik explizit verifizieren.

### Task 5: Product claims, language contract, static-analysis baseline (P1.5, P2.4, P3.4)

**Files:**
- Modify: `app/site/index.html`, `app/docs/{HANDBUCH.md,VISION.md}`, runtime/seed/frontend copy as needed
- Create: `app/docs/static-analysis-baseline.md`, config/scripts/tests as needed

- [ ] Claims als lokal/cloud-gebunden/experimentell/ungeprüft markieren und Link-/Asset-Scan grün halten.
- [ ] Ein verbindlicher Sprach-/Provider-Default wird in Code, Seed, UI und Doku synchronisiert.
- [ ] Read-only Knip/deptry/dependency-cruiser Baseline mit expliziten Ausnahmen und Report erzeugen.

### Task 6: Verification and delivery

- [ ] Backend gezielte Tests plus vollständige verfügbare Suiten ausführen.
- [ ] Docs-Site `npm ci`, `npm test`, `npm run build`; Frontend `npm ci`, `npm test`, `npm run build` soweit verfügbar.
- [ ] Remote Actions exakt auf Ziel-SHA prüfen; Windows-Desktop-Smoke/Release-Gates mit echter Ausgabe durchführen, soweit Gerät/Signatur/Provider vorhanden.
- [ ] `github_sync.py --pull --strict` (oder Auth-Blocker) dokumentieren, committen, `git push origin main`, danach lokal/remote/origin-Refs und Clean-Status getrennt verifizieren.

### 2026-11-19-open-items-remediation-design.md

Quelle: `HISTORIE.md`.

# Open-items remediation design

Stand: 2026-11-19

## Intent and scope

Move the open-items register to a reproducible acceptance state. Fix issues that
are reproducible in the public checkout and keep external release gates explicit.

Goals:

- The backend suite must not require private evidence in the public checkout.
- The Playwright lab must use a supported, pinned GitHub runner.
- The Windows startup contract must return exit code 0 after successful checks.
- Documentation must point to the canonical status file and fresh evidence.

External gates remain blocked until a real Windows device, provider accounts,
publisher identity, and production R2 credentials are supplied. No test key or
invented release URL is acceptable.

## Approaches

Re-adding the private matrix would violate the repository privacy contract;
removing its tests would lose local coverage. The selected approach keeps the
matrix checks active when an authorized evidence file exists and skips them with
a clear reason in the public checkout. The browser job is pinned to
ubuntu-24.04 because the current Playwright version rejects ubuntu-26.04.

## Acceptance criteria

- AC-01 public checkout skips the private matrix checks without FileNotFoundError.
- AC-02 an authorized matrix file still runs both checks.
- AC-03 calibration-browser uses ubuntu-24.04.
- AC-04 startup test exits 0 after success.
- AC-05 docs and Oracle npm audits report zero high/critical findings.
- AC-06 status and README use the canonical open-items path.
- AC-07 hardware, signature, and R2 gates are marked BLOCKED, not passed.
- AC-08 layout and source-only guards remain green.
- AC-09 targeted tests and builds are reproducible.
- AC-10 the delivered commit is verified on main with no feature branch or PR.

## Six phases

1. Discovery and capability preflight.
2. Research and reuse of existing tests, guards, and lockfiles.
3. Specification, measurable acceptance criteria, and atomic plan.
4. Minimal implementation on main.
5. Adversarial functional, security, and layout verification.
6. Delivery with exact commit and fresh GitHub evidence.
