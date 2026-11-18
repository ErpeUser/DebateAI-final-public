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
