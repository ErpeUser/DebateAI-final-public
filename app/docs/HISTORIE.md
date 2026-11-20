# DebateAI – Historie und Provenienz

Stand: 2026-11-20. Diese Datei bündelt frühere Visionen, Forschungsentscheidungen, Abgleichsmatrizen und datierte Nachweise. Sie beschreibt historische Herkunft und Entscheidungen, keine aktuelle Freigabe. Aktuelle Ziele stehen in [VISION.md](VISION.md), aktuelle Lücken in [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md).

## Leseregel

Ein historischer Status wird nicht durch seine Aufnahme in dieses Dokument zu einem aktuellen Testergebnis. Alte Pfade, Branch-Namen, Commitstände und Releaseaussagen bleiben Provenienzangaben. Für den heutigen Zustand gelten der aktuelle Quellbaum, frische Tests und die aktuelle Vision.

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
Zusammen lesen: `/AGENTS.md`, `/source/AGENTS.md`, `source/docs/windows-final-runbook.md`, `source/docs/releasing.md` und `source/docs/FINAL_STATUS_AND_OPEN_ITEMS.md`. Dieses Dokument beschreibt **was** das Produkt leisten soll; die anderen Dateien regeln Arbeitsweise, Ausführung und aktuellen Nachweis.

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

Aktuelle Kommandos und Releasebedingungen stehen in [releasing.md](releasing.md); dieser Status ersetzt die älteren Windows-/Codex-Aufträge ausdrücklich.

## Herkunft und geschützte Nachweise

- Die historische V6-Vision stammt aus `d07a658:source/docs/DEBATE_AI_VISION_FINAL.md`.
- Die privaten technischen Fortschritts- und Acceptance-Protokolle unter `app/.ai/` bleiben außerhalb des öffentlichen Dokumentvertrags. Ihre geprüften, nicht personenbezogenen Entscheidungen sind in den Abschnitten oben zusammengefasst.
- Lokale Providerprofile, Transkripte, Audiodaten, Credentials, Runtime-Dateien und private Evidence bleiben außerhalb dieser drei redaktionellen Quellen.
- `RESEARCH_DE.md` und `RECONCILIATION_MATRIX_DE.md` sind in diese Historie eingearbeitet und werden nicht mehr als eigenständige Quellen gepflegt.
