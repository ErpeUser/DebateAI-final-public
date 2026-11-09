# DebateAI / Backchannel – Implementierungs- und Pipeline-Audit

> Fuehrender Optimierungs- und Entscheidungsstand seit 7. November 2026:
> `.ai/DEBATE_AI_OPTIMIERUNG.md`. Dieses Audit bleibt als historischer Detailbeleg.

Stand: 2026-11-06, 19:35 Europe/Vienna  
Grundlage: aktueller Arbeitsbaum `codex/debate-ai-master-optimization` bei Basis-Commit `da2c530`, laufendes Paket auf Port 8474 und direkte Statusabfragen.  
Wichtig: Der Arbeitsbaum enthält 326 gemeldete Änderungen/neue Dateien. Dieser Audit beschreibt deshalb den **aktuellen Quellstand und die laufende Installation getrennt**. Nichts in diesem Dokument behauptet, dass jede Quelländerung bereits in der veröffentlichten EXE steckt.

## 1. Kurzurteil

Backchannel besitzt derzeit drei miteinander verbundene KI-Ebenen:

1. **Lokale Echtzeitspur:** native Windows-Audioaufnahme → lokales Parakeet für sofortige Teiltexte → Silero/ECAPA für Sprachaktivität und Sprechertrennung → lokales Whisper Base für gespeicherte finale deutsche Transkripte.
2. **Lokaler Debatten-Copilot:** Qwen 3:4B über einen lokalen Ollama-kompatiblen Endpunkt erzeugt ereignisgesteuert die sofort sprechbare Antwort, Gegenfrage, Stütze, Analogie und Rechercheentscheidung.
3. **Vertiefende Analyse:** normales ChatGPT-Webkonto ist als erste externe Analysequelle konfiguriert, danach Gemini-Web, anschließend CLIProxy/Codex und Gemini CLI. Diese Ebene speist Gesamtanalyse, Hauptanalyse, strategische Signale, Quellenabgleich und Abschlussredaktion.

Die lokale Kernkette kann ohne ChatGPT/Gemini transkribieren und Qwen-Empfehlungen erzeugen. Externe Vertiefungen sind optional und fallen kontrolliert aus. Im laufenden Paket ist ChatGPT Web als bereit bestätigt; Gemini Web ist vorhanden, aber die Sitzung ist aktuell nicht bereit und verlangt eine erneute interaktive Anmeldung.

## 2. Einfache Ablaufkette

```text
Windows-Mikrofon ─┐
                  ├─ native PCM16/16 kHz ─ WebSocket /ws/{session_id}
Windows-Wiedergabe┘                              │
                                                ├─ Pegelereignisse → zwei UI-Meter
                                                ├─ Parakeet V3 Live → flüchtiger Teiltext
                                                └─ Silero VAD + ECAPA → Sprechersegmente
                                                                  │
                                                                  └─ Whisper Base (Deutsch)
                                                                     → finaler Text
                                                                     → PostgreSQL transcript_entries
                                                                     → WebSocket transcript
                                                                     → TurnAssembler
                                                                          │
                                                                          ├─ Qwen Debate Copilot
                                                                          │  → Sofortsatz
                                                                          │  → Gegenfrage
                                                                          │  → Gegenargument
                                                                          │  → Analogie
                                                                          │  → Recherchebedarf
                                                                          │
                                                                          ├─ Claims/Argumentgedächtnis
                                                                          ├─ DuckDuckGo/Wikipedia-Recherche
                                                                          └─ externe Analyse-Routen
                                                                             1 ChatGPT Web
                                                                             2 Gemini Web
                                                                             3 CLIProxy/Codex
                                                                             4 Gemini CLI
                                                                                  │
                                                                                  ├─ Gesamtanalyse
                                                                                  ├─ Hauptanalyse
                                                                                  ├─ Chancen-/Quellenabgleich
                                                                                  ├─ strategische Signale
                                                                                  └─ Abschlussanalyse
```

Parallelität:

- Pegel, Live-Teiltext und Segmentierung laufen während der Aufnahme parallel.
- Finale Transkription wird geordnet mit begrenzter Parallelität ausgeführt; Ausgabe und Datenbankreihenfolge bleiben stabil.
- Qwen reagiert ereignisgesteuert auf neue finale bzw. revidierte Gesprächszüge.
- Recherche und externe Vertiefung laufen nach der sofortigen lokalen Antwort im Hintergrund.
- Post-Call-Linsen laufen erst bei normalem Gesprächsende oder ausdrücklich angeforderter Abschlussanalyse.

## 3. Audio, ASR und Persistenz

| Stufe | Tatsächlich aktiv | Aufgabe | Quellort |
| --- | --- | --- | --- |
| Windows Capture | Ja, Desktoppaket | Mikrofon und optional WASAPI-Loopback getrennt erfassen; PCM16/16 kHz und Pegel liefern | `backend/app/services/windows_audio_capture.py`, `native_audio_bridge.py`, `backend/app/routers/native_audio.py` |
| Audio-WebSocket | Ja | Binärdaten, Trackstatus, Replay, Stop und Direktiven transportieren | `backend/app/ws/audio_pipeline.py`, `audio_messages.py`, `audio_handler.py` |
| Silero VAD | Ja, wenn Modell vorhanden | Sprache/Silence segmentieren | `backend/app/services/speaker_diarizer.py` |
| ECAPA-TDNN | Ja, wenn Modell vorhanden | Sprecher-Embeddings und automatische Sprecherzuordnung | `speaker_diarizer.py`, `speaker_assignment.py` |
| Parakeet V3 Live | Ja; Laufzeitmodell `local-parakeet-v3-live` | Schnelle, flüchtige Teiltranskripte; **nicht** die persistierte Wahrheit | `local_live_captioner.py`, `local_transcriber.py` |
| Whisper Base lokal | Ja; Laufzeitmodell `local-whisper-base` | Deutsche finale Segmenttranskripte | `local_transcriber.py`, `ordered_transcription.py` |
| TurnAssembler | Ja | Kurze Finalsegmente zu einem semantischen Gesprächszug mit Revision zusammenführen | `turn_assembler.py`, `audio_handler.py` |
| PostgreSQL | Ja | Finale Zeilen als `transcript_entries`, Sprecher, Claims, Insights, Sitzungen und Einstellungen speichern | `backend/app/models.py`, `audio_handler.py` |
| Transcript Refiner | Vorhanden, derzeit deaktiviert | Optional Zeichensetzung/offensichtliche Verhörer korrigieren, ohne Inhalt zu ändern | `transcript_refiner.py`; Agent `transcript_refiner` |

Vertrag zwischen Teiltext und Finaltext:

```python
# audio_handler.py, sinngemäß gekürzt
entry = TranscriptEntry(session_id=session_id, text=text, sequence=seq, speaker_id=...)
db.add(entry)
await db.commit()
await websocket.send_json({"type": "transcript", "data": transcript_payload})
await orchestrator.feed_transcript(turn.text, ...)
```

- `interim_transcript` ist eine Vorschau und darf ersetzt oder entfernt werden.
- `transcript` ist final, wird bei aktivierter Speicherung zuerst committed und danach an UI/Agenten verteilt.
- Die globale Laufzeiteinstellung `transcript_retention_enabled` ist aktuell `true`.
- Neu im Quellstand: kurze Whisper-Puffer werden spätestens nach 1,5 Sekunden geleert; die veröffentlichte EXE enthält diese letzte Änderung noch nicht.

## 4. KI-Modelle und Provider

### 4.1 Laufzeitmodelle

| Modell/Route | Status | Tatsächliche Rolle | Kosten-/Loginpfad |
| --- | --- | --- | --- |
| `local-parakeet-v3-live` | Aktiv | Schneller deutscher Live-Teiltext | lokal, kein Login |
| `local-whisper-base` | Aktiv und diagnostisch nutzbar | Persistierte finale Transkription | lokal, kein Login |
| `endpoint:german-debate-ollama:qwen3:4b` | Aktiv | Sofortiger Debate Copilot | lokal, kein Login |
| `chatgpt-web:gpt-6` | Aktiv und Laufzeitstatus `ready=true`, `xhigh` | Externe Tiefenanalyse/Meta-/Post-Call-Agenten | persönliches normales ChatGPT-Webkonto über Oracle-Browserprofil |
| `endpoint:gemini-web:gemini-3.1-pro` | Konfiguriert, aktuell `ready=false` | Zweite Web-Analyseroute | Google-Websitzung; aktuell Re-Login nötig |
| `endpoint:subscription-ai:gpt-6-sol` | Aktivierter Fallback | CLIProxy/Codex-Subscription-Fallback | bestehender OAuth-/Proxyweg |
| `endpoint:subscription-ai:gemini-3.1-pro-preview` | Aktivierter Fallback | Gemini-CLI-OAuth-Fallback | bestehender OAuth-/Proxyweg |
| `gemini-3.1-pro-preview` offizielle API | Deaktiviert | Letzter optionaler API-Weg | würde API-Schlüssel/Kosten erfordern; Standard aus |

### 4.2 Priorität und Auswahl

Quelle: `ai/providers.default.json`; Benutzerkopie: `%LOCALAPPDATA%\Backchannel\ai\providers.json`.

```json
[
  "chatgpt-web:gpt-6 (xhigh)",
  "endpoint:gemini-web:gemini-3.1-pro (high)",
  "endpoint:subscription-ai:gpt-6-sol (xhigh)",
  "endpoint:subscription-ai:gemini-3.1-pro-preview (high)",
  "gemini-3.1-pro-preview (disabled)"
]
```

Routingregeln:

- Die auf einem Agenten direkt gespeicherte Modell-ID ist dessen primäre Zuweisung.
- `external_reasoning.py`, `subscription_bridge.py`, `provider_capabilities.py` und `llm.py` lösen die konkrete Route, Fähigkeiten, strukturierte Ausgabe, Limits und Fehlerklassen auf.
- `ai_config.py` verwaltet Reihenfolge, Cooldown, adaptive Reasoning-Stufe, Parallelitätslimit und die einmalig kopierte Benutzerkonfiguration.
- Fallback ist global aktiv; externe Hintergrundanalyse ist auf eine parallele Ausführung begrenzt.
- Eine deaktivierte offizielle API-Route wird nicht still aktiviert.
- Der lokale Qwen-Copilot hängt nicht von dieser externen Reihenfolge ab.

## 5. Alle konfigurierten Agenten

Laufzeitquelle: `GET /api/agents`; Seed/Reset: `backend/app/services/seed_agents.py`.

| Agent | Aktiv | Trigger | Modell aktuell | Ergebnis/Zusammenarbeit | Einstellbar |
| --- | --- | --- | --- | --- | --- |
| Live-Transkription (`audio_gateway`) | Ja | kontinuierlich | Parakeet V3 Live | Nur Teiltext; keine Empfehlung | Einstellungen → Assistenten/Transkription; je Sitzung Override möglich |
| Gesamtanalyse (`consolidated_analyst`) | Ja | ca. 40 s + final | ChatGPT Web | Ein Aufruf über vier Linsen: Fragen, Beobachtungen, Chancen, Aufgaben | Modell, Prompt, Intervall, Linsen global; Aktivierung je Sitzung |
| Debate Copilot (`objection_handler`) | Ja | neues relevantes Ereignis, Zielintervall 10 s | lokales Qwen 3:4B | Sofortsatz, Gegenfrage, Gegenargument, Analogie, Claims und Rechercheentscheidung | Debattenmodus/Stil/Recherche global; Agent je Sitzung |
| Hauptanalyse (`synthesizer`) | Ja | neue Insights, ca. 75 s Cooldown | ChatGPT Web | Qualitätskontrolle, Merge, Antworterkennung, Typanhebung, neues Gesamtbild | Modell/Prompt/Intervall global; Aktivierung je Sitzung |
| Chancen-Abgleich (`opportunity_specialist`) | Ja | neue Opportunity, ca. 55 s | ChatGPT Web | Verknüpft erkannte Chancen ausschließlich mit ausgewählten Wissensquellen | Wissensquellen und Agent global/je Sitzung |
| Strategische Signale (`strategic_signals`) | Ja | ca. 45 s | ChatGPT Web | Priorisierte Live-Karten: Signal, Risiko, nächste Frage, Chance, Aktion | Modell/Prompt/Intervall global; Aktivierung je Sitzung |
| Sitzungsprotokoll (`brief_meeting_lens`) | Ja | Gesprächsende/auf Abruf | ChatGPT Web | Faktisches Protokoll, Entscheidungen, Zusagen, nächste Schritte | global und je Sitzung |
| Erkenntnisanalyse (`brief_discovery_lens`) | Ja | Gesprächsende/auf Abruf | ChatGPT Web | Ziele, Probleme, Wissenslücken, Chancen, Risiken, offene Fragen | global und je Sitzung |
| Abschlussredaktion (`brief_arbiter`) | Ja | nach beiden Post-Call-Linsen | ChatGPT Web | Führt beide Entwürfe widerspruchsarm zusammen | global und je Sitzung |
| Transkript-Korrektur (`transcript_refiner`) | Nein | optional, ca. 45 s | nicht gesetzt | Nur Form-/Verhörerkorrektur; keine Inhaltsanalyse | global und je Sitzung |

Entscheidungslogik:

- `AgentOrchestrator` lädt globale `agent_configs` und überschreibt nur `enabled` mit `session_agent_overrides`.
- TranscriptBuffer, TurnAssembler, Claim-/Argumentgedächtnis und Board-Stubs liefern Kontext.
- Revisionen und Topic-/Turn-IDs verhindern, dass ältere Ergebnisse neuere Karten überschreiben.
- Der Copilot publiziert nur echte Modellfelder. Modellfehler werden als Status behandelt, nicht durch einen sichtbaren deterministischen Antwortsatz ersetzt.
- Synthesizer und Chancen-Abgleich arbeiten nur auf bereits erkannten Items; sie ersetzen den schnellen Copiloten nicht.

## 6. Prompts – Quelle, Empfänger und Wirkung

| Prompt | Empfänger | Codequelle | Wirkung |
| --- | --- | --- | --- |
| `AUDIO_BRIDGE_PROMPT` | Audio Gateway | `services/agents/prompts.py` | Explizit still: nur zuhören/transkribieren, keine Analyse |
| `CONSOLIDATED_ANALYST_BASE_PROMPT` | Gesamtanalyse | `prompts.py` | Kontext, Sprecher, Direktiven, Dokumente, aktive Items und letzte Transkripte; JSON-Items |
| `DEFAULT_ANALYST_LENSES` | Gesamtanalyse | `prompts.py`; DB `agent_configs.lenses` | Vier einzeln aktivierbare Linsen für Frage, Beobachtung, Chance, Aufgabe |
| `OBJECTION_HANDLER_PROMPT` | Qwen Copilot | `prompts.py` + Prompt-Ressourcen | Schnelle deutsche Empfehlung und Einwandserkennung |
| `DEBATE_RECOMMENDATION_PROMPT` | Qwen-Livevertrag | `prompts.py` | Strukturiert `answer_now`, Gegenfrage, Analogie, Claim, Recherchebedarf |
| Analogie-/Modus-/Phasenressourcen | Qwen Copilot | `agents/prompt_resources.py`, `ai/prompts/*`, `ai/playbooks.json` | Überzeugend vs. brutal-sachlich, natürlicher/knapper/belegorientierter Stil, Gesprächsphase |
| `PRINCIPAL_AGENT_PROMPT` | Hauptanalyse | `prompts.py` | Merge, Enrichment, Answer Detection, strategische Synthese |
| `OPPORTUNITY_SPECIALIST_PROMPT` | Chancen-Abgleich | `prompts.py` | Nur vorhandene Knowledge Records zuordnen, nichts erfinden |
| `STRATEGIC_SIGNALS_PROMPT` | Strategische Signale | `prompts.py` | Fünf Live-Sektionen nach Dringlichkeit über alle Sektionen ranken |
| `BRIEF_MEETING_LENS_PROMPT` | Sitzungsprotokoll | `prompts.py` | Faktische Post-Call-Sicht |
| `BRIEF_DISCOVERY_LENS_PROMPT` | Erkenntnisanalyse | `prompts.py` | Discovery-/Sensemaking-Sicht |
| `BRIEF_ARBITER_PROMPT` | Abschlussredaktion | `prompts.py` | Konflikte zwischen beiden Entwürfen auflösen |
| `SYSTEM_PROMPT` | Transcript Refiner | `transcript_refiner.py` | Zeichensetzung/Satzgrenzen/offensichtliche Verhörer, Bedeutung erhalten |
| Review-/Learning-Prompts | Nachanalyse | `debate_review.py`, `debate_learning.py` | Sitzung bewerten, Argumentgraph und übernehmbare Vorschläge erstellen |

Zentraler Qwen-Ausgabevertrag, gekürzt:

```text
answer_now: direkt sprechbarer deutscher Satz
counterargument: kompakte Stütze
counter_question: präzise echte Alternative
analogy: kurze korrekte Analogie oder konkreter Vergleich
target_claim + argument_points: bezogene Behauptung und Teilargumente
confidence + needs_research + research_query: Unsicherheit und Recherche
```

Prompt-Persistenz:

- Seeds/Reset kommen aus `seed_agents.py` und `prompts.py`.
- Benutzeränderungen liegen in PostgreSQL (`agent_configs`) bzw. im lokalen `ai`-Verzeichnis.
- `ai_config.py` versioniert editierbare Prompt-Ressourcen im lokalen `ai/history/prompts`-Ordner.
- Bekannte Defaults werden migrationsartig aktualisiert; individuell geänderte Werte sollen nicht pauschal überschrieben werden.

## 7. Recherche, Quellen und Material

### Aktiv

- `debate_research.py`: keyless Webrecherche über aktivierte Provider.
- Standardprovider: DuckDuckGo und Wikipedia; zwei Schritte, Originalquellen erwünscht, 20 Sekunden Gesamtbudget.
- Claim-/Quellenverträge: `debate_contracts.py` (`AtomicClaim`, `DebateSource`, `LogicalRelation`).
- Quellenstatus unterscheidet gefunden/gelesen/fehlgeschlagen sowie unterstützt/widerspricht/unklar und primär/sekundär/unbekannt.
- `argument_graph.py` und `semantic_argument_memory.py` halten Beziehungen, Themen und frühere Argumente.

### Wissensquellen/Material

- `knowledge_sources` und `knowledge_records` sind generische, vom Nutzer befüllbare Quellen.
- Der bestehende „Angebotskatalog“ ist der historische integrierte Adapter `source_type=offerings` und wird vom Chancen-Abgleich genutzt.
- Er ist deshalb **keine nachweislich tote Altlast** und wird in diesem Durchgang nicht gelöscht. Eine spätere Produktanpassung sollte ihn zu neutralem „Material/Katalog“ umbenennen oder als optionalen Adapter behandeln, ohne Daten zu verlieren.
- Dokumente und lokale Vorbereitungsdossiers werden sitzungsbezogen gespeichert und in erlaubte Promptkontexte aufgenommen.

## 8. Browser-/Desktop-Bridges und Authentifizierung

| Integration | Implementierung | Verhalten |
| --- | --- | --- |
| ChatGPT Web | `backend/app/services/chatgpt_web.py`, Router `chatgpt_web.py`, Desktop `chatgpt_web_login.py`, Runtime `desktop/chatgpt_oracle/` | Oracle startet einen dedizierten Browserprofil-Job. Status liest verifizierte Modell-/Thinking-Metadaten. Login, Trennen und Konto wechseln sind eigene explizite API-Aktionen. |
| Gemini Web | Router `gemini_web.py`, `subscription_bridge.py`, Desktop `gemini_web_bridge.py`/`gemini_web_login.py`, Runtime `desktop/gemini_web_to_api/` | Lokaler OpenAI-kompatibler Webproxy; gespeicherte Google-Sitzung; Pro-Modellstatus über Bridge. |
| CLIProxy/Codex | `cliproxy_api.py`, `subscription_oauth.py`, Desktop `cliproxyapi/` | OAuth-basierter Fallback für Subscription-Modelle. |
| Gemini CLI | `subscription_bridge.py`, `subscription_oauth.py` | OAuth-Fallback über lokale Bridge. |
| App-Fenster | `desktop/launcher.py` | Long-lived Besitzerprozess, eingebettetes WebView-Fenster, Tray und Systembrowser-Fallback. |

Wichtige Abgrenzung:

- Ein **Provider-Statuscheck** darf keinen Loginbrowser öffnen.
- Ein Browser darf nur durch explizites Login/Kontowechseln oder einen echten ChatGPT-Web-Analysejob entstehen.
- Beim App-Start werden ChatGPT Web und Gemini Web genau einmal per Status-API geprüft. Ist ein installierter Provider nicht bereit, öffnet sich nur Backchannels interne Seite „Verbindungen“; ein externer Login startet erst nach Tastendruck.
- ChatGPT Web ist technisch keine reine HTTP-Text-API: Oracle steuert das normale persönliche Webkonto im dedizierten Profil. Mehrere gleichzeitige Oracle-Jobs werden durch eine Browserreservierung verhindert.
- Erkennt ein realer Oracle-Job, dass die zuvor bestätigte Modellauswahl nicht mehr auffindbar ist, wird eine recoverbare Fehler-Sidecar neben dem Nachweis geschrieben. Folgeagenten öffnen dann keine weiteren Browserjobs, sondern melden „Erneut anmelden“; das dedizierte Sitzungsprofil bleibt erhalten.
- Eine unveränderte abgelehnte Gemini-Sitzung wird genau einmal versucht und danach erst bei einem neuen Login-Handoff erneut gestartet. Ein zuvor erfolgreich gestarteter, später abgestürzter Helper darf weiterhin neu starten.
- Der laufende Prozessbestand zeigt derzeit viele Edge-Unterprozesse; aus Prozessnamen allein lässt sich nicht beweisen, welche davon Oracle, WebView2 oder normale Benutzerfenster sind. Eine pauschale Beendigung wäre daher unsicher.

## 9. Speicherung und Datenbanken

PostgreSQL-Tabellen im aktuellen Modell:

- Sitzungen, Segmente und Transkripte: `sessions`, `call_segments`, `transcript_entries`
- Sprecher/Revisionsdaten: `speakers`, `speaker_mapping_revisions`, Revalidation-Tabellen
- Analyse: `questions` (historischer Sammeltyp für alle Insight-Karten), `debate_claim_records`, `session_syntheses`, `insight_clusters`
- Vorbereitung: `documents`, `directives`
- Quellen/Material: `knowledge_sources`, `knowledge_records`, `offerings`
- KI-Konfiguration: `agent_configs`, `session_agent_overrides`, `custom_endpoints`, `app_settings`
- Nutzungsdaten: `token_usage`

Migration/Kompatibilität:

- Alembic verwaltet versionierte Migrationen.
- Startup unterscheidet leere, alte unversionierte und bereits versionierte Datenbanken und ergänzt kompatibel fehlende Spalten.
- Desktop nutzt das paketierte PostgreSQL und `%LOCALAPPDATA%\Backchannel\pgdata`; Build-/Updatevorgänge dürfen diesen Datenordner nicht ersetzen.

## 10. Oberfläche und Einstellorte

| Bereich | Heute vorhanden | Reichweite |
| --- | --- | --- |
| Neue Debatte | Name, derzeit im UI fälschlich nur „Überzeugen“ sichtbar | neue Sitzung |
| Pre-Call | Geräte, PC-Ton, Kontext, Dokumente, Dossier, Import, Teilnehmer, Sitzungsagenten | je Sitzung |
| Aktive Debatte | beide Pegel, Transkript, Copilot, Recherche an/aus, Antwortausrichtung, Quellenprüfung, Direktiven | live |
| Einstellungen → Assistenten | Modelle, Prompts, Intervalle/Linsen, Debattenmodus, Stil, Recherchehäufigkeit | globaler Standard |
| Einstellungen → Transkription & Audio | Live-/Finalmodell, Deutsch, Geräte-/Diarisierungsoptionen | globaler Standard |
| Einstellungen → Verbindungen | ChatGPT/Gemini/CLIProxy/CLI/API-Status und Loginwege | Installation/Konto |
| Quellen | generische Wissensquellen und Datensätze | global, von Agenten auswählbar |
| Material | historischer Angebots-/Katalogadapter | global, optional für Chancen-Abgleich |

Belegte UI-Lücke:

- Backend und `MeetingContextSetup` kennen `debate_persuasive` und `debate_forceful`.
- `NewSessionModal.tsx` setzt jedoch `meetingType` hart auf `debate_persuasive` und zeigt nur eine statische Karte. Der zweite Modus ist deshalb bei der Erstellung nicht wählbar.
- Debattenmodus und Recherchehäufigkeit sind derzeit globale Einstellungen; die Live-UI kann Recherche nur an/aus schalten. Eine vollständige sitzungsspezifische Frequenz-/Modussteuerung ist im aktuellen Vertrag nicht implementiert.

## 11. Fehlerbehandlung, Revisionen und Ressourcen

- `OrderedTranscriptionQueue` begrenzt Transkriptionsparallelität, hält Eingabereihenfolge, trennt Filterung von echten Fehlern und hat Zeitlimits für ASR und Persistenz.
- WebSocket-Replay verwendet Sequenzen; UI-Hooks coalescen Pegel/Teiltexte und vermeiden unnötige React-Renders.
- Turn-/Claim-Revisionen und Themenzustand verhindern veraltete Copilot-/Rechercheergebnisse.
- Providerfehler werden normalisiert und erhalten Cooldowns; ein externer Fehler darf den lokalen Copiloten nicht überschreiben.
- Externe Analysen sind auf eine parallele Hintergrundausführung begrenzt.
- Launcher besitzt Einzelinstanz-/Guard-, Backend-, PostgreSQL-, Tray-, WebView- und Browser-Fallback-Lebenszyklus.
- Beim Gesprächsende werden Audio, Queue und Agenten geordnet geleert; Post-Call kann vollständig oder ohne Briefing beendet werden.

## 12. Tatsächlich geprüft / nur Code-bestätigt / offen

| Punkt | Status | Evidenz |
| --- | --- | --- |
| Backend/DB laufend | REAL GETESTET | `GET /api/ready` = `ok`; paketiertes PostgreSQL läuft |
| ChatGPT-Webstatus | REAL GETESTET | `ready=true`, Modell `gpt-6`, Thinking `xhigh`; letzte verifizierte UI-Auswahl gespeichert |
| Gemini-Webstatus | REAL GETESTET, BEREIT | Finales Paket meldet `ready=true`, Pro verfuegbar und Modell `gemini-3.1-pro`; keine neue Modellantwort gesendet |
| Lokale ASR-Verfügbarkeit | REAL GETESTET | `/api/diagnostics/local-asr` = usable |
| ASR-Sprache | REAL GETESTET (Konfiguration) | Batch `local-whisper-base`, Live `local-parakeet-v3-live`, Sprache `de` |
| Qwen-Ausgabevertrag | REAL GETESTET im vorigen Release-Smoke | echte strukturierte deutsche Antwort mit Gegenargument/Gegenfrage/Analogie; kein Template-Fallback |
| Kurze Finaltranskripte | GEZIELT GETESTET UND GEBAUT | neuer 1,5-s-Bound; final 21 fokussierte Backendtests grün; Paket-Smoke grün |
| Zwei Erstellmodi | GEZIELT GETESTET UND GEBAUT | Überzeugen und Brutal-sachlich auswählbar; 2 Modaltests grün |
| Recherchefrequenz je Sitzung/live | OFFEN | global vorhanden, live nur an/aus |
| Wiederholte Browserseiten | URSACHE BEHOBEN, GEBAUT | Nach erstem Oracle-Selektorfehler werden Folgejobs geblockt und Re-Login verlangt; 7 ChatGPT-Tests grün. |
| Unendlicher Gemini-Neustart | URSACHE BEHOBEN, GEBAUT | Unveränderte ungültige Sitzung wird einmal versucht; erfolgreicher Crash-Restart bleibt; 8 Desktoptests grün. |
| Providerprüfung beim Start | GEZIELT GETESTET UND GEBAUT | Ein Statuslauf öffnet nur die interne Verbindungsseite bei Handlungsbedarf; 9 Onboardingtests und Produktionsbuild grün; kein automatischer externer Browser. |
| Beide Pegel im realen Gespräch | OFFEN für erneute Realabnahme | Event- und UI-Pfad vorhanden; Screenshot zeigt aktive Anzeigen, aber niedrige Werte/PC-Ton aus |
| GUI/Tray-Wiederherstellung | REAL GETESTET | echtes `Debate AI`-Fenster sichtbar; versteckte lebende Hauptform wird vom Tray-Waechter restauriert, minimierte oder geschlossene UI nicht |
| Finale EXE entspricht diesem Quellstand | JA | sauberer Python-3.12-Build, Staging-Start/DB/ASR, Archiv-Update und erzwungener Rollback grün |

## 13. Artefakte

- Veröffentlichte EXE: `dist/Backchannel/Backchannel.exe`
  - Groesse: 26,876,512 Bytes
  - SHA-256: `3652AF94E7B2900F2C300C7ED6BA289B6CA34E5E32F3B7ADC9853C3EEA8A26A6`
- Internes updaterfähiges Archiv: `dist/Backchannel-DebateAI-windows-x64.zip`
  - Groesse: 430,128,200 Bytes
  - SHA-256: `AB6156E8E7ECB36ED1FA580382359CECF1A83F3028B7672F0A3B815EA5185F28`

## 14. Für die nächste Pipeline-/Agentenanalyse

Dieser Audit bestätigt die vorhandenen Bausteine, ohne bereits eine Reduktion zu entscheiden. Für eine spätere Optimierung sind die klaren Entscheidungsgrenzen:

1. Sofortspur (Parakeet/Whisper/Qwen) darf nicht von langsamen Webagenten abhängig werden.
2. Gesamtanalyse, Hauptanalyse und strategische Signale haben teilweise überlappende Syntheseaufgaben; eine Reduktion muss ihre unterschiedlichen Trigger und gespeicherten Resultate berücksichtigen.
3. Quellen-/Materialadapter sind echte Datenfunktionen und keine bloßen UI-Altlasten.
4. Post-Call-Trio ist von der Live-Pipeline getrennt und kann unabhängig bewertet werden.
5. Provider-Routing und Agentenanzahl sind getrennte Fragen: weniger Agenten bedeutet nicht automatisch weniger Browserstarts, solange mehrere Aufträge dieselbe Webroute nacheinander verwenden.
