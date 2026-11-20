# DebateAI Arbeitsstrang B – Prompt-Matrix

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

## Doppelte oder veraltete Ressourcen

- `background.oracle`, `background.gemini` und `background.gpt6` sind byte-identisch; sie bleiben vorerst als modellabhängige Routingnamen erhalten.
- `app/ai/playbooks.json` und `app/ai/defaults/playbooks.json` sind identisch und bleiben wegen Update-/Benutzerkonfigurationsschutz getrennt.
- `app/ai/debate_deep_v1.txt` und `app/ai/defaults/prompts/debate_deep_v1.txt` sind identisch.
- `experimental_integrator_v1.txt` wird nicht geladen; die Datei bleibt als historische Referenz erhalten.
- Die aktive und Defaultfassung von `debate_live_v2` wurden in B vereinheitlicht; die neue Hash-Version ist `b836b11580ae`.
