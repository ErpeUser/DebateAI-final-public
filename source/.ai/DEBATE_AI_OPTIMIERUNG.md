# Debate AI - fuehrender Optimierungsstand

## DESKTOP_FINAL-Paket 3/3 - Windows-Build und native Smokes (2026-11-11)

- Der echte Checkout bleibt `C:\Users\User\Datein\Coding\DebateAI`, Branch
  `master`, ohne Daten-/AppData-Loeschung. Die Identitaets-, Update-, Provider-
  und Buildvertraege bevorzugen DebateAI und behalten kontrollierte Backchannel-
  Aliase.
- Behoben: gepinnter Gemini-Web-Bridge-Patch an v1.3.4, Windows-Go-Modulformatierung,
  Smoke-Test-Instanzheader, tokengebundene Updater-Health-Anfrage und Windows-
  Master-Key-Kompatibilitaet unter DPAPI; keine Fremdprozesse beendet.
- Exakter finaler Build mit Python 3.12, Node 24 und Oracle/Node-Runtime:
  `source/dist/DebateAI/DebateAI.exe` und `DebateAIUpdater.exe`.
- Bundle-Smoke: gesund, lokale ASR-Probe nutzbar, sauberer Shutdown. Archiv-Smoke:
  native Windows-Update und erzwungener Rollback bestanden.
- ZIP: `source/dist/DebateAI-windows-x64.zip`, SHA-256
  `09CC1C199A98602C780B393F550B1D7B845174117501647011011ECA4BB464D8`.
- Tests: Desktop-Identitaet 11, Updater 12 (1 Windows-Symlink-Skip), Desktop-
  Smoke/Bridge 13, Backend fokussiert 58 (1 Skip), Frontend npm 323, PWA 5,
  Kalibrierung 26; Frontend-Build erfolgreich. Ein vorheriger `npm test`
  Zusatzparameter war Node-ungültig und wurde ohne ihn erneut erfolgreich ausgefuehrt.
- Offen bleiben echte manuelle/hardwaregebundene Gates A06/A18/A21/A22, die
  15 Runtime-Gates, lokale Ollama-Modellpaar-Messung, Provider-Logins, reale
  Authenticode-/Update-Signatur und Repository-Admin-Rename. Diese werden nicht
  als bestanden behauptet.
- Volltree-Backend-Scan: 1855 Tests, 5 Failures/11 Errors/4 Skips. Die Fehler
  sind getrennt dokumentiert: fehlendes pytest im isolierten Release-Venv,
  umgebungs-/modellabhängige Tests sowie historische Branding-/Orchestrator-
  Erwartungen, die dem kanonischen DebateAI-Vertrag widersprechen. Der
  fokussierte produktrelevante Satz und alle nativen Release-Smokes bleiben grün.

Stand: 2026-11-08

## V3-Wiederaufnahme 2026-11-08 - rekonstruierter Stand und Abnahmematrix

### Belegbare Rekonstruktion

- Das native Codex-Goal ist aktiv: Alle Anforderungen des vollstaendigen
  V3-Vertrags implementieren, integrieren, testen und belegen, ohne bestehende
  Funktionalitaet oder fremde Aenderungen zu beschaedigen.
- Vollstaendig gelesen: `ANALYSE_V3.txt`, `START_HIER_V3.txt`,
  `UMSETZUNGSAUFTRAG_V3.txt`, diese fuehrende Datei, `AGENTS.md`,
  `docs/agents.md` und `ABNAHMEFAELLE_V3.json` direkt aus
  `Debate_AI_Review_Umsetzungsauftrag_V3.zip`.
- Die Codex-App listet den urspruenglichen 17:36-Minuten-Work-Task nicht als
  eigenen lesbaren Task. Der danach gespeicherte Chat `Master Auftrag V3
  Umsetzung` enthaelt jedoch das vollstaendige sichtbare Verlaufsprotokoll.
  Es wurde nicht behauptet, der unzugreifbare Originalchat sei erinnert worden.
- Die am 8. November zwischen 05:31 und 05:43 geaenderten Dateien bestaetigen
  die uebergebenen Pakete A04, A07, A11, A12 und A14 im Arbeitsbaum. Nichts
  wurde zurueckgesetzt, gestasht, committed, bereinigt oder geloescht.
- Ruling: Im bestehenden Checkout auf Branch
  `codex/debate-ai-master-optimization` weiterarbeiten. Ein neuer Worktree
  wuerde den umfangreichen uncommitteten V3-/Vorarbeitsstand nicht enthalten;
  die Repository-Anweisung verlangt ausdruecklich dessen Erhalt. Risiko bei
  Fehlentscheidung: groessere Diff-Komplexitaet; Gegenmassnahme sind kleinste
  Pakete, gezielte Tests und diese persistente Matrix.

### Aktueller Nachweis der wiedergefundenen Pakete

- Backend, projektgebundenes Python 3.12.10 und repository-internes TEMP:
  `python -m unittest tests.test_windows_audio_capture
  tests.test_ws_event_stream tests.test_transcript_refiner
  tests.test_debate_review tests.test_debate_copilot` -> 104/104 gruen.
- Frontend ohne Sandbox-Kindprozess:
  `node --test --test-isolation=none src/hooks/useWebSocket.test.mjs
  src/lib/wsEventStream.test.mjs` -> 18/18 gruen.
- Erweiterter Audio-/Retentionpfad ausserhalb der Windows-Sandbox:
  `python -m unittest tests.test_audio_handler
  tests.test_windows_audio_capture tests.test_pii_shield` -> 101/101 gruen.
  Der identische Sandboxlauf hatte 99 fachlich gruene Tests und zwei reine
  `TemporaryDirectory`-ACL-Fehler. Der Lauf mit dem versehentlich aufgerufenen
  systemweiten Python 3.14 war mangels Projektabhaengigkeiten nicht verwertbar.

### V3-Abnahmematrix A01-A24

Status ist nur `BESTANDEN`, wenn ein aktueller konkreter Nachweis vorliegt.
`IMPLEMENTIERT` bedeutet vorhandener Code/Test, dessen vollstaendiger
V3-Vertrag noch zusammengezogen oder erneut ausgefuehrt werden muss.

| ID | Genaue Anforderung | Stand / Dateien und Tests | Nachweis / verbleibende Luecke | Status |
| --- | --- | --- | --- | --- |
| A01 | Dauerhafte Audioannahme vor ACK; Crashfenster Datei/Index/ACK rekonstruierbar | `backend/app/services/audio_store.py`, `backend/app/ws/audio_persistence.py`, `backend/app/main.py`; `test_audio_store.py`, `test_main_schema.py` | Aktiviertes Archiv synchronisiert Append/Close per `flush`/`fsync`; ein crashoffener WAV wird anhand der stabilen Session-/Segmentidentitaet repariert, verknuepft und als beendet indiziert, bevor Orphan-Cleanup laeuft. 28/28 kombinierte Tests gruen. Begrenzung: kein Schutz gegen kompletten Datentraegerverlust | BESTANDEN |
| A02 | Commit vor WebSocket-Sendefehler; Reconnect zeigt committed Text genau einmal | `backend/app/services/provisional_transcripts.py`, `backend/app/services/pii/ws.py`, `backend/app/services/ws_event_stream.py`; `test_pii_shield.py`, `test_ws_event_stream.py`, `test_provisional_transcripts.py` | Commit-vor-Send ist getestet; bei deterministischem Senderfehler bleibt der committe Interimtext im Journal und ein neuer Socket erhaelt ihn genau einmal im Snapshot. 58/58 fokussierte Tests gruen | BESTANDEN |
| A03 | Technischen Replay, echte Wiederholung und Capture-Neustart unterscheiden | `frontend/src/hooks/useWebSocket.ts`, `backend/app/ws/audio_handler.py`, `backend/app/ws/audio_pipeline.py`, `backend/app/services/agents/orchestrator.py`, `provisional_transcripts.py`; `test_audio_handler.py`, `test_provisional_transcripts.py`, Frontend-WebSockettests | Logische `capture_id` bleibt bei automatischem Reconnect stabil und wird beim expliziten Disconnect verworfen; Gateway-/Interim-Segment-IDs tragen diese Identitaet. Technischer Replay bleibt revisions-idempotent, ein neuer Capture bekommt eine neue ID. Backend 13/13 (davon 1 erwartungsgemaess ohne PostgreSQL uebersprungen), Frontend 26/26 gruen | BESTANDEN |
| A04 / N1 | 128000-Byte-RAM-Grenze bei Retention-off; kein stiller PCM-Drop, sichtbarer Stop, keine Diskkopie | `native_audio_bridge.py`, `audio_pipeline.py`; `test_windows_audio_capture.py`, `test_audio_handler.py`, `test_pii_shield.py`, `test_ws_event_stream.py` | 101/101 Audio-/Retentiontests und 18/18 Clienttests gruen; bereits akzeptierte native Frames bleiben erhalten, Overflow stoppt sichtbar | BESTANDEN |
| A05 | Raten, Restbuffer, Tail, Clock-/Geraetewechsel und getrennte Resampler | `windows_audio_capture.py`, `track_mixer.py`, `test_windows_audio_capture.py`, `test_track_mixer.py` | 44.1/48-kHz-Resampling ueber mehrere Rest-/Tailbloecke, getrennte Converter-Zustaende, Spurmischung und erkannter Geraete-/Ratenwechsel sind belegt; 18/18 Tests gruen | BESTANDEN |
| A06 | Kurze deutsche Rede und Diarisierungsoverload ohne Textverlust | `speaker_diarizer.py`, `ordered_transcription.py`, `audio_runtime.py`, `audio_messages.py`, `audio_pipeline.py`, `capacity_planner.py`, `scripts/replay_call.py`, `scripts/validate_v3_acceptance_evidence.py`; `test_diarization_backlog.py`, `test_audio_handler.py`, `test_capacity_planner.py`, `test_replay_call.py`, `test_v3_acceptance_evidence.py` | Technischer P0-Fix bestanden: der Backlog-Guard entfernt keine akzeptierten Frames; ein neuer Frame oberhalb 30 s wird vor Persistenz/Queue abgewiesen, sichtbarer `diarization_overflow`-Stop und Full-Drain; Kapazitaets- und Replaypfad verwenden denselben Annahmestopp-/Statusvertrag. Das Evidenz-Gate erzwingt deutsche Referenz, alle Szenarien, Transcript-Vollstaendigkeit und sauberen Abschluss. Shutdown-Timeout meldet `audio_gap`. Reales deutsches Referenzaudio/Overlap bleibt BLOCKED | BLOCKED |
| A07 | Snapshot/Delta, umgekehrte Commitreihenfolge, Restart-Epoche und alter Cursor | `ws_event_stream.py`, `session_manager.py`, `useWebSocket.ts`; `test_ws_event_stream.py`, `test_pii_shield.py`, Frontend-Epochtests | Zwei asynchrone Writer werden mit umgekehrter Fertigstellungsreihenfolge simuliert; Delta-Cursor und spaeter Writer bleiben replaybar. Alte Serverepoche erzwingt Full-Snapshot; Client setzt Cursor/History zurueck. Backend 75/75 (17 Journal + 58 PII) und Frontend 18/18 gruen | BESTANDEN |
| A08 | Cancellation ist nicht physisches Workerende; Lane bleibt reserviert | `native_inference.py`; `test_native_inference.py`, `test_debate_copilot.py` | Abgebrochene/timeoutte native Threads bleiben supervised; die Lane wird quarantiniert und nimmt keine zweite Arbeit an. 66/66 fokussierte Tests gruen | BESTANDEN |
| A09 | Manuelle Revision gewinnt gegen spaete Automatik und entwertet Empfehlungen | `transcript_revisions.py`, `transcript_refiner.py`, `orchestrator.py`; `test_transcript_revisions.py`, `test_transcript_refiner.py`, `test_debate_copilot.py` | Manuelle Korrekturen erhoehen die Transcriptrevision, invalidieren passende Live-Empfehlungen und stale spaete Automatik wird verworfen; Originale bleiben bei Refinerfehler erhalten. 77/77 fokussierte Tests gruen | BESTANDEN |
| A10 | Leeres/kuerzeres Final und Split/Merge duerfen Nachbartext nicht loeschen | `provisional_transcripts.py`, `ordered_transcription.py`, `audio_handler.py`; `test_provisional_transcripts.py`, `test_ordered_transcription.py`, `test_audio_handler.py` | Leere Finals bleiben sichtbar, kuerzere exakt zugeordnete Finals duerfen ersetzen, Nachbarjobs werden geordnet weiterverarbeitet und Split-Track-Topologie bleibt erhalten. 27/27 fokussierte Tests gruen | BESTANDEN |
| A11 / N2 | Refiner bewahrt Wortreihenfolge, Rollen, Negationen, Namen/Zahlen und Rawtext | `transcript_refiner.py`, `ai/transcript_refiner_system.txt`, `test_transcript_refiner.py` | Red-Green aus verlorenem Task rekonstruiert; aktueller 104/104-Lauf gruen | BESTANDEN |
| A12 / N3 | Reviewzitat nur aus exakter Claim-/Utterance-Herkunft, nicht Wortaehnlichkeit | `debate_review.py`, `test_debate_review.py` | Gegensaetzliche fast identische Saetze aktuell in 104/104 gruen; ohne exakte ID bleiben Sprecher/Zeit unbestaetigt | BESTANDEN |
| A13 | Sprecherkorrektur waehrend laufender Nachanalyse entwertet nur Abhaengiges | `speaker_context_enhancer.py`, `speaker_revalidation.py`, `speaker_name_rewriter.py`; `test_speaker_context_enhancer.py`, `test_speaker_revalidation.py` | Batchabfrage begrenzt Mutationen auf zugewiesene Insight-IDs; Finalisierung loescht `speaker_context_dirty` nur bei identischer Mapping-Version. Der Stale-Race-Test bestaetigt, dass eine spaetere Sprecherrevision die laufende alte Revision nicht als aktuell markiert | BESTANDEN |
| A14 | Aktuelle Retention-/Learning-Policy unmittelbar vor spaetem Commit erneut pruefen | `orchestrator.py`, `debate_settings.py`; `test_debate_copilot.py` | Lern- und Transkriptaufbewahrung-aus verhindern Commit; aktueller 104/104-Lauf gruen | BESTANDEN |
| A15 | Opt-in, Ablauf, Widerruf und Neustart fuer Lernbeispiele; Feedback ist kein Faktenlabel | `debate_learning.py`, `semantic_argument_memory.py`, `tests/test_debate_learning.py` | Ablauf wird beim Laden ausgeschlossen, Widerruf bleibt restartfest gespeichert, Korrektur wird separat protokolliert; gespeicherte Beispiele bleiben `feedback_kind=usefulness`, `factual_status=unverified`, `export_allowed=false`; Duplikat ersetzt den alten Eintrag | BESTANDEN |
| A16 | Effektiver Default/Override/Reset-Prompt und genau ein Hauptbeitrag in beiden Modi | `ai_config.py`, `prompt_resources.py`, `debate_settings.py`, `objection_handler.py`; `test_ai_config.py`, `test_prompt_ordering.py`, `test_debate_copilot.py` | Gespeicherter Override gewinnt, Reset/Versionierung stellt den Default wieder her, Modus-/Style-Ressourcen werden effektiv geladen und das Schema erlaubt genau einen sprechbaren Hauptzug ohne Pflicht-Bundle. 100/100 fokussierte Tests gruen | BESTANDEN |
| A17 | Gueltige Beleg-ID ist kein Wahrheitsbeweis; Passage/Zeitraum/Population/Einheit/Negation muessen stuetzen | `debate_research.py`, `argument_graph.py`, `orchestrator.py`; `test_debate_research.py`, `test_argument_graph.py`, `test_debate_copilot.py` | Quellen-ID allein reicht nicht: strukturierte Einheit/Zeitraum/Population muessen im Zielkontext stuetzen; Gegenpassagen bleiben unverified. 88/88 fokussierte Research-/Graph-/Copilot-Tests gruen | BESTANDEN |
| A18 | Zustimmung/Eingrenzung/Rueckfrage/Nichtausgabe bei Wahrheitsbindung und beiden Modi | Promptressourcen, Copilottests, `scripts/validate_v3_acceptance_evidence.py`, `tests/test_v3_acceptance_evidence.py` | Automatisierbare Schema-/Promptteile und ein konservatives Gate fuer beide Modi, mindestens zehn Faelle, verblindete anonymisierte Ratings und Fallabdeckung vorhanden; menschliche deutsche Sprechbarkeits-/Rhetorikabnahme nicht ersetzbar | BLOCKED |
| A19 / N4 | Strict-local darf Loopbackproxy/LAN/Browser-ASR nicht allein nach Label freigeben | `privacy.py`, `llm.py`, `custom_endpoints.py`, `useSpeechRecognition.ts`; `test_privacy.py`, `test_privacy_agent_admission.py`, `test_custom_endpoints.py`, `test_llm_endpoint.py`, `test_llm_self_hosted_limits.py` | Zielhost wird geprueft, oeffentliche URLs werden verworfen, und die beiden app-eigenen Loopback-Bridges (`subscription-ai`, `gemini-web`) bleiben trotz on-prem URL gesperrt. Browser-ASR wird im Produktpfad nicht gestartet; der Backend-Audiopfad bleibt massgeblich. 137/137 isolierte Privacy-/Endpoint-/LLM-Tests gruen. Restgrenze: unbekannte Drittanbieter-Proxies koennen nur durch Betreiberangabe/Ende-zu-Ende-Netztest bewertet werden | BESTANDEN |
| A20 | Fehlende Gewichte: ehrlicher Offline-/Readinessfehler, kein Cloudfallback/Download | `transcription_readiness.py`, `transcription_runtime.py`, `audio_handler.py`, `retranscribe.py`; `test_transcription_readiness.py`, `test_local_asr_readiness.py`, `test_transcription_runtime.py`, `test_audio_handler.py`, `test_transcription_jobs.py`, `test_retranscribe.py` | Lokale Runtime prueft Import und `fbanks.npz`; fehlende Gewichte/Data melden einen sichtbaren Readinessfehler, der Start-Gate verweigert den Call, und Retranscribe faellt nicht ungeprueft auf Cloud zurueck. 45/45 fokussierte Tests gruen | BESTANDEN |
| A21 | ASR A/B unter gleicher deutscher Referenz und Gesamtlast | ASR-Adapter, Benchmarks, historische reale Clips, `scripts/validate_v3_acceptance_evidence.py`, `tests/test_v3_acceptance_evidence.py` | Historische Clips belegen Whisper-vs-Parakeet-Entscheidung; das Gate erzwingt jetzt zwei gleich benannte Laeufe, dieselbe Referenz/Hardware/Last, keine manuelle Korrektur und endliche Metriken. Eine aktuelle gleiche Referenz-/Hardware-Gesamtlastkampagne fehlt | BLOCKED |
| A22 | Kausaler Mehrturn-/Latenzbenchmark ohne Zukunftsdaten, Fehler im Nenner | `benchmark_debate_copilot.py`, `test_debate_benchmark.py`, `scripts/validate_v3_acceptance_evidence.py`, `tests/test_v3_acceptance_evidence.py`, historische Qwen-Messung | Echter Produktionspfad wurde gemessen; deterministische Rubrik-Vorpruefung und ein konservatives Evidenz-Gate fuer Zukunftsdaten, Nenner, gleiche Last, Latenz-/Fehlergrenzen und verblindete Ratings sind integriert; unabhaengiger Referenzdatensatz/Cluster und menschliche Qualitaet fehlen | BLOCKED |
| A23 | Sichere Legacy-Adoption/Cleanup nur mit Eigentums-, Referenz- und Packagingnachweis | `main.py`, Migrationen 028-031, `test_main_schema.py`, `desktop/tests/test_release_contract.py`, `test_release_manifest.py`, `test_platform_release_manifest.py`, `test_smoke_test.py`, `docs-site/*.test.js` | Legacy-Adoption, Audio-Recovery/Cleanup, Migrationen 028-031, Plattform-Signaturen, Release-Manifest, Archiv-Smoke und die private/public Docs-Releaseoberflaeche sind geprueft. Backend 20/20, Desktop 43/43 und Docs aggregiert 206/206 gruen; Produktionsaudit 0 High/Critical; keine unreferenzierte Loeschung belegt | BESTANDEN |
| A24 | Installierter Windows-Kandidat muss aktuellem Quell-/Prompt-/Assetstand entsprechen | `scripts/build_debate_assistant.ps1`, `frontend/dist`, `desktop/backchannel.spec`, `dist/Backchannel-DebateAI-windows-x64.zip`, Desktop-Smokes | Nach dem 96-Zeichen-Capture-ID-Fix neu gebaut; Frontend 2139 Module, Bundle-Smoke mit Health/ASR/Shutdown und kanonischer Archiv-Smoke mit Update/Rollback sind gruen. GUI/DPI/Discord bleibt manuell | BESTANDEN |

Gesamtstand dieser konservativen Matrix: 20 BESTANDEN, 0 IMPLEMENTIERT,
0 OFFEN, 0 IN ARBEIT, 4 BLOCKED. Die Statussumme ist kein Qualitaetsscore.

### V3-Zusatzmatrix P0-P3 und sonstige verbindliche Vertraege

Die A01-A24-Zeilen sind die atomaren Abnahmepunkte. Diese zweite Matrix fuehrt
die uebergeordneten P0/P1/P2/P3-Vertraege und ihre belastbare Ableitung
explizit, damit ein gruener Einzeltest nicht versehentlich als Vollabnahme
eines groesseren Vertrages gelesen wird.

| ID | Vertrag / genaue Abgrenzung | Artefakte und Nachweis | Status |
| --- | --- | --- | --- |
| P0-A | Audioannahme: aufgenommen -> RAM -> dauerhaft angenommen -> erkannt -> angezeigt; Crashfenster sichtbar | A01-A04, Audio-Store-/Journaltests, 101/101 Audio-/Retentionpfad | BESTANDEN |
| P0-B | Samples/Uhren/Luecken, thread-sichere native Bruecke, Hardware-Discontinuity | A03-A06, Windows-Audio-/Mixer-/Overflowtests; reale Hardware bleibt in A06 separat | BESTANDEN (technisch) |
| P0-C | Einfachste korrekte Wiederanbindung mit Snapshot/Epoche statt erzwungenem Outbox-Rewrite | A01/A02/A07, Backend 75/75 und Frontend 18/18 | BESTANDEN |
| P0-D | ASR-Final ist nicht automatisch wahrer; Revision, Konflikt und leeres Final | A09-A11, Refiner-/Provisional-/Orderingtests 104/104 | BESTANDEN |
| P1-B | Sprecher-/Quellenrevision entwertet nur konkret Abhaengiges | A12/A13/A17, Review-/Revalidation-/Graph-Suite | BESTANDEN |
| P1-C | GoodDebateExample als eigener Opt-in-/Widerrufs-/Retentionbestand | A14/A15, Learning-/Consent-Race-Tests | BESTANDEN |
| P1-D | Effektiver Prompt in realem Request, Default/Override/Reset, beide Modi und sinnvolle Nichtausgabe | A16 und technischer Anteil A18; deutsche Human-Rhetorik bleibt A18 BLOCKED | BLOCKED (Human-Gate) |
| P2-A | Strict-local umfasst Start, Warmup, Downloads/Updates, Browser-ASR, Hintergrund und Nachanalyse; kein stiller Cloudfallback | A19/A20; pinned model downloader, `docs/model-manifest.json`, Privacy-/Readiness-Suite; Drittanbieter-Proxy und vollstaendige Netzsperre nur Betreiberabnahme | BESTANDEN (automatisierbarer Anteil) |
| P2-B | Modellwahl erst nach wirksamem Prompt-/Thinking-Fix; kein zweiter Dauer-ASR ohne Netto-Nutzen | A21/A22 und Qwen-/ASR-Benchmarks; gleiche Hardware-/Referenzkampagne fehlt | BLOCKED |
| P2-C | Vorhandene Adapter/Libraries ausschoepfen; Versionsaudit und Python-3.13/audioop-Vertrag ohne pauschales Upgrade | `backend/scripts/audit_dependencies.py`, `docs/dependency-audit-v3.json`, `docs/dependency-audit-v3.md`, A05/A21/A24; installiert/constraint/native/license metadata erfasst, Security-Advisory-Review und Python-3.13-Migration bleiben getrennte Releaseentscheidungen | IMPLEMENTIERT |
| P2-D | UI-Zustaende, Verlauf, Pegel, Stop/Festhalten/Recherchepause; keine Fokus-/Autoscrollschleife; Loopback separat | Frontend-Regression/Build und A24; echte GUI/DPI-/Loopbackabnahme fehlt | BLOCKED (Hardware) |
| P3-A | Vor Entfernung Eigentum, Aufrufer, Entry Points, Registry, Packaging, Hash/Groesse, Ersatz und Rueckweg belegen | A23/A24, Release-/Manifest-/Smoke-Suites 206/206 Docs und 43/43 Desktop | BESTANDEN (gepruefte Pfade) |
| P3-B | Abgeloeste Timer/Writer/Refiner/Wrapper/Imports/Settings/Routen tatsaechlich entfernen, Migrationen erhalten | A23 Cleanup-/Migrationstests; kein unreferenzierter Loeschpfad belegt | BESTANDEN (gepruefte Pfade) |
| P3-C | App-eigene Gewichte/Tokenizer/Downloads und Buildreste nur nach Eigentums-/Rueckwegpruefung physisch entfernen | Kein unautorisierter Cleanup ausgefuehrt; shared caches/unklare ACL-Ordner geschuetzt | BLOCKED (Eigentums-/Rollbackabnahme) |
| P3-D | Schemaadoption/Legacy-/unterbrochene Migration in Kopien, Asset-/Prompt-/Buildfingerprint verknuepfen | A23 Migration-/Schema-Tests und Releasefingerprints; unterbrochene Migration auf realer Bestandskopie nicht ausgefuehrt | BLOCKED (Bestandskopie) |
| P3-E | Debate-AI-Identitaet und alte Daten-/EXE-Pfade nur mit gepruefter Uebernahme/Rueckweg | A23/A24 Release-/Installationspfade; reale Nutzerinstallation nicht zurueckgesetzt | BLOCKED (manuelle Installation) |
| P3-F | Nach Cleanup Tests, Imports, Start/Health, Snapshot/Export, Modell-/DLL-/Assetfindung und Offlinebetrieb erneut pruefen | Voll-Backend 1719/1719, Frontend Build 2139 Module; nur die in P3-C bis P3-E genannten Realpfade offen | BESTANDEN (technischer Anteil) |
| P3-G | Frischer lesender Review ausserhalb des Diffs, max. fuenf Hauptbefunde, keine erfundene Unabhaengigkeit | Dieser Wiederaufnahme-Audit plus persistente Matrix; externe Human-/Hardware-Gates explizit markiert | BESTANDEN |

P2-C ist damit als reproduzierbarer Inventar-/Auditpunkt `IMPLEMENTIERT`.
Das Artefakt behauptet weder einen nicht ausgefuehrten Security-Scan noch eine
Python-3.13-Kompatibilitaet; beides bleibt als explizite Releaseentscheidung
sichtbar. Das ist kein Anlass fuer ein pauschales Upgrade.

### Atomare Coverage-Matrix der verbindlichen Unteranforderungen

Die folgende Tabelle fuehrt jede Unteranforderung aus dem Umsetzungsauftrag
einzeln. Ein zusammengesetztes Paket gilt dadurch nicht automatisch als
vollstaendig: `BLOCKED` bezeichnet eine echte externe Voraussetzung,
`IMPLEMENTIERT` einen belegten technischen Anteil mit bewusst dokumentierter
Restentscheidung.

| ID | Genaue Anforderung (Kurzform des Vertrags) | Beleg / verbleibende Luecke | Status |
| --- | --- | --- | --- |
| P0.1 | Dirty-Stand, echte EXE/Build-ID, Quelldiff, Prompt-/Config-/Gewichts-/Treiber-/OS-/Hardware-/Lock-Inventar | Arbeitsbaum, Build-/Prompt-/Modellevidenz und Dependency-Audit vorhanden; laufende reale EXE-/Hardwareinventur fehlt | BLOCKED |
| P0.2 | Einen konkreten Verlustfall Capture -> Transport -> ASR -> Revision -> Commit -> UI -> Export reproduzieren und Ursachen trennen | A01-A04, Audio-/Journal-/UI-/Exporttests; reale deutsche Aufnahme fehlt | BESTANDEN (technisch) |
| P0.3 | Native Queue, PCM, Thread-/Eventloop-Uebergang und Overflow ohne kaschierten Verlust pruefen | A04, 101/101 Audio-/Retentiontests, kein accepted-frame drop | BESTANDEN |
| P0.4 | Herkunft, Capture-Generation, Track, Sequenz/Samplebereich, Rate und getrennte Zustaende | A03/A05, Capture-ID-/Resampler-/Geratewechseltests | BESTANDEN |
| P0.5 | Empfangen vs. dauerhaft angenommen; ein begrenzter idempotenter Durabilitaetspfad | A01/A02/A04, Archiv-/Recovery-/Quota-/ACK-Tests | BESTANDEN |
| P0.6 | Kanonische Segment-IDs, append-only Revisionen, Split/Merge/Retranscribe/Manuell ohne Zerstoerung | A09/A10, Provisional-/Ordering-/Revisionstests | BESTANDEN |
| P0.7 | Snapshotwasserzeichen, committed Cursor, Restart-Epoche, Paging und konkurrierende DB-Tasks | A07, Backend-Journal-/PII- und Frontend-Epochtests | BESTANDEN |
| P0.8 | PCM-/Kanal-/Rate-/Antialias-/Resampler-/Clock-/Stop-/VAD-/Leisefilter pruefen | A05/A06, Audio-/Mixer-/Filtertests; akustische Hardwareabnahme fehlt | BESTANDEN (technisch) |
| P0.9 | Getrennte Quellen gegen Vollzeitdiarisierung, Echo/Systemloopback und unbekannte Sprecher korrekt behandeln | Track-/Diarisierungslogik und Tests; echte Discord-/Echoquelle fehlt | BLOCKED |
| P0.10 | Retention-off fuer Rohdaten, Revisionen, Spool, Claims, Insights, Embeddings, PII, Logs und Exporte | A14/A15, PII-/Retention-/Learning-Suite; reale Nutzerdaten-/Backupabnahme fehlt | BESTANDEN (technisch) |
| P1.1 | Realer Aufruf-/Ressourcenplan mit Trigger, Revision, Modell, Budget, Prioritaet, Timeout, Cancellation, Schreibrecht, Ausgabe | `docs/agents.md`, Orchestrator-/Budget-/Cancellationtests | BESTANDEN |
| P1.2 | Bestehende Funktionen statt neuer Agenten; fachliche Trigger und Cooldowns statt Dauerloops | Agenten-/Trigger-/Dedup-/Researchtests; keine neue Dauer-ASR eingefuehrt | BESTANDEN |
| P1.3 | Alle Promptressourcen sowie Loader, Overrides, Seeds, Reset, Migration, Version und Hash pruefen | Prompt-Resource-/Ordering-/AI-Config-Tests und `seed_agents.py` Hash-/Versiongate | BESTANDEN |
| P1.4 | Ein gemeinsamer kleiner JSON/Pydantic-Vertrag, technische IDs, Revision, Belege, Grenzen, Reparaturversuch | Copilot-/Schema-/Benchmark-/Evidenztests | BESTANDEN |
| P1.5 | Coach trifft den tatsaechlichen Punkt, trennt Behauptung/Beleg, stimmt ein, grenzt ein, fragt nach oder korrigiert | Prompt-/Claim-/Research-Gates; deutsche Sprechbarkeit und rhetorische Qualitaet menschlich offen | BLOCKED |
| P1.6 | Kontextbudget, Themen-/Cache-Versionen und unabhaengige Belege ohne `latest only` fuer Wahrheit | Context-/Revision-/Cache-/Reconnecttests | BESTANDEN |
| P1.7 | Refiner konservativ: Reihenfolge, Zahlen, Namen, Negation und Rawtext bewahren | A11/N2, Red-Green-Refiner-Suite | BESTANDEN |
| P1.8 | Nachanalyse aus gesichertem Transkript mit Herkunft, Revision, Quellenwiderruf und Zustimmung | A12-A15/A17, Review-/Graph-/Learning-Tests; Human-Review bleibt separat | BESTANDEN (technisch) |
| P2.1 | Strict-local ueber Capture, ASR, Refiner, LLM, Embeddings, Start, Downloads, Browser-ASR, Hintergrund und Nachanalyse | A19/A20, Privacy-/Readinesstests, gepinnte Downloads; Vollnetz-/Drittanbieterproxy nur Betreiberabnahme | BESTANDEN (automatisierbarer Anteil) |
| P2.2 | Modellwahl nicht nach Label; Ein-Erkennerpfad gegen Interim/Final und Challenger nur bei gemessenem Restproblem | Vier vorhandene WAVs wurden mit Whisper/Parakeet unter identischem lokalem Lauf verglichen; Whisper bleibt wegen des realen deutschen Restfehlers Final-Standard. Gleiche aktuelle Hardware-/Gesamtlastkampagne fuer A21 fehlt | IMPLEMENTIERT (Modellentscheidung; A21-Kampagne offen) |
| P2.3 | Qwen3:4b zuerst korrekt mit Thinking-/Template-/Kontext-/JSON-/Deutsch-/Lastmessung konfigurieren | Qwen-Prompt-/Benchmark-/Copilottests; kein unnoetiger Challengerwechsel | BESTANDEN (technisch) |
| P2.4 | Einmal laden, Warmup/Wechsel sichtbar, globale CPU-/Thread-/RAM-/VRAM-/Queue-/Lag-Budgets | Local-fit-/Inference-/Agent-Activity-/Capacitytests | BESTANDEN (technisch) |
| P2.5 | Recherche als konkrete offene Fakten mit Passage, Originalquelle, Zeitraum, Population, Einheit, Abrufzeit und Gegenbeleg | A17, Research-/Graph-/Provenance-Suite | BESTANDEN |
| P2.6 | Egress-/Renderer-/Download-/Secret-Schutz; Modellquelle, Revision, Hash, Lizenz, sichere Formate | Privacy-/Request-/Downloadtests, `docs/model-manifest.json`, atomare Hashpruefung | BESTANDEN (technisch) |
| P2.7 | Vorhandene Libraries/Adapter gezielt ausschoepfen, keine neue Bibliothek ohne reproduzierten Bedarf | Onnx-/Pydantic-/AsyncSession-/HTTP-/Adaptertests; keine unbelegte Zusatzbibliothek | BESTANDEN |
| P2.8 | Direkte produktive Abhaengigkeiten und native Komponenten mit Version, Constraint, Nutzen, Lizenz, Plattform, Security-/Ablosestatus auditieren | `audit_dependencies.py`, `dependency-audit-v3.json`; Security-Scan und Python-3.13-Migration bewusst nicht behauptet | IMPLEMENTIERT |
| P2.9 | Ruhige UI mit Jetzt-sagen-Karte, Verlauf, zwei Pegeln, Zustanden, Stop/Festhalten/Recherchepause, Quellen/Korrekturen | Frontend 269/269 und Build 2139 Module; echte GUI/DPI-/Loopbackabnahme fehlt | BLOCKED |
| P3.1 | Vor Entfernen Eigentum, Aufrufer, Entry Points, Registry, Overrides, Packaging, Hash/Groesse, Ersatz/Rueckweg belegen | A23/A24 Release-/Manifest-/Smoke-Nachweise fuer gepruefte Pfade | BESTANDEN (gepruefte Pfade) |
| P3.2 | Abgeloeste Timer/Writer/Refiner/Wrapper/Imports/Settings/Routen komplett entfernen und Migrationen erhalten | Cleanup-/Migrationstests, statischer Review, keine unreferenzierte Loeschung belegt | BESTANDEN (gepruefte Pfade) |
| P3.3 | App-eigene unbenutzte Gewichte/Tokenizer/Downloads/Buildreste nur mit Eigentum/Rueckweg physisch loeschen; Manifest fuehren | Keine destruktive Bereinigung ohne Eigentumsnachweis; shared/unklare ACL-Pfade geschuetzt | BLOCKED |
| P3.4 | Leere, versionierte, Legacy- und unterbrochene Migration in Kopien abnehmen; ausgelieferte Migrationen nicht umschreiben | Schema-/Migrationstests vorhanden; echte unterbrochene Bestandskopie fehlt | BLOCKED |
| P3.5 | Debate-AI-Identitaet und alte Daten-/EXE-Pfade mit Uebernahme und Rueckweg | Release-/Installationsvertraege vorhanden; reale Nutzerinstallation nicht zurueckgesetzt | BLOCKED |
| P3.6 | Nach Cleanup, Install/Health/Readiness, Snapshot/Export, Asset-/DLL-Findung und Offlinebetrieb erneut pruefen | Backend 1719/1719 (historischer Gesamtbeleg; aktueller Vollaufgruf Zeitlimit), Frontend 269/269, Desktop 193/193, Docs 206/206, Build 2139 Module; Realpfade P3.3-P3.5 offen | BESTANDEN (technischer Anteil) |
| P3.7 | Frischer lesender Review ausserhalb des Diffs, max. fuenf Hauptbefunde, kritische Zusatzbefunde nicht unterschlagen | Dieser Audit, Matrix, Fortschrittsdatei und explizite Blocker | BESTANDEN |

### Paket 2026-11-08 - A03 Capture-Identitaet bei Reconnect

- Der Vertrag fuehrte bisher nur Cursor-/Revisionstests, aber keine explizite
  Capture-Identitaet. `useWebSocket` sendet jetzt eine zufaellige `capture_id`
  je logischem Capture; automatische Reconnects verwenden sie weiter, ein
  expliziter Disconnect leert sie fuer den naechsten Start.
- Der Backend-Orchestrator und der lokale Streaming-Pfad binden ihre
  Interim-Segment-IDs an diese ID. Damit ist derselbe technische Replay unter
  gleicher Capture-Identitaet idempotent, waehrend ein neuer Capture trotz
  wortgleichem Text eine neue Identitaet besitzt.
- Nachweis: Backend `tests.test_audio_handler.AudioFrameDecodingTests
  tests.test_provisional_transcripts tests.test_provisional_transcripts_postgres`
  -> 13 Tests, 12 bestanden und 1 erwartungsgemaess uebersprungen, weil kein
  `BACKCHANNEL_TEST_POSTGRES_URL` gesetzt ist; Frontend
  `useWebSocket.test.mjs`, `wsEventStream.test.mjs`, `useAudioCapture.test.mjs`
  -> 26/26. Die Regression aus Audio-/Replay-/PII-Suite danach -> 131/131.

Status: BESTANDEN.

### Paket 2026-11-08 - Abschlussregression und Capture-ID-Randfall

- Die A03-Identitaet wird jetzt auf 96 Zeichen begrenzt, damit der Gateway- /
  Track-Suffix innerhalb des `VARCHAR(128)`-Vertrags bleibt. Der Grenzfall ist
  mit 200 Zeichen Eingabe getestet; die A03-Kurzsuite ist 12/12 gruen.
- `git diff --check` und `python -m compileall -q backend/app backend/tests`
  sind gruen.
- Die erste vollstaendige Backend-Discovery lief 1705 Tests: 1697 bestanden,
  3 uebersprungen, 6 Fehlschlaege und 2 Fehler. Die acht Abweichungen waren
  die danach behobenen privaten-IP-Hostregeln, die Prompt-Laenge und ein
  veralteter Test-Fake; die fokussierte Nachpruefung dieser Aenderungen ist
  30/30 gruen. Eine Wiederholung der kompletten Discovery wurde von der
  Ausfuehrungsfreigabe wegen abgelaufener Anmeldung abgewiesen und daher nicht
  umgangen.
- Frontend-Einzeltests: 113/134 fachlich gruen; 21 Dateien scheiterten nur an
  `esbuild`-`spawn EPERM` der eingeschraenkten Umgebung. Der Produktionsbuild
  nach A03 bleibt mit 2139 Modulen gruen.

Status: technische Regressionen behoben; Gesamt-Discovery und A24-Rebuild
bleiben wegen Umgebungsfreigaben nachzuholen.

Naechster exakter Schritt: Ausfuehrungsfreigabe erneuern, dann A24 neu bauen,
kanonischen Bundle-/Archiv-Smoke wiederholen und die vollstaendige Backend-
Discovery abschliessend ausfuehren.

Naechster exakter Schritt: den Windows-Kandidaten nach der A03-Aenderung erneut
  bauen, danach Gesamtregression, Statusmatrix und verbleibende manuelle
  Abnahmen abschliessend synchronisieren.

### Paket 2026-11-08 - A24 quellidentischer Windows-Kandidat

- `scripts/build_debate_assistant.ps1 -Python .release-venv\\Scripts\\python.exe
  -SkipDownloads` hat das Frontend mit 2139 transformierten Modulen gebaut,
  den aktuellen Backend-/Promptstand in PyInstaller eingebettet und den
  Kandidaten unter `dist/Backchannel-DebateAI-windows-x64.zip` veroeffentlicht.
- Der Bundle-Smoke pruefte Readiness, lokale ASR-Runtime und sauberen Shutdown:
  `OK: healthy on port 8474`, `OK: bundled local ASR runtime usable`,
  `OK: clean shutdown`.
- Der Archiv-Smoke mit dem vom Checker geforderten kanonischen Namen pruefte
  Update und erzwungenen Rollback: `OK: native windows-x64 update and forced
  rollback`.
- Nach dem A03-Capture-ID-Fix wurde der Kandidat erneut gebaut; der zweite
  Frontend-/PyInstaller-Lauf blieb bei 2139 Modulen gruen. Bundle-Smoke und
  kanonischer Archiv-Smoke wurden am 08.11. erneut ausgefuehrt und blieben
  gruen.
- Die anschliessende sichtbare GUI-/DPI-/Discord-Abnahme bleibt manuell und
  wird nicht aus dem Smoke abgeleitet.

Status: BESTANDEN.

Naechster exakter Schritt: die abschliessende V3-Gesamtregression ausfuehren,
die Matrix gegen den aktuellen Arbeitsbaum zaehlen und die verbleibenden
manuellen Blocker mit einem reproduzierbaren Abnahme-Playbook dokumentieren.

### Paket 2026-11-08 - A24-Rebuild und vollstaendige Backend-Discovery

- Der Kandidat wurde nach der finalen 96-Zeichen-Capture-ID-Grenze erneut mit
  `scripts/build_debate_assistant.ps1 -Python .release-venv\\Scripts\\python.exe
  -SkipDownloads` gebaut. Das Frontend transformierte 2139 Module; der
  aktuelle Backend-/Prompt-/Assetstand ist im Windows-ZIP enthalten.
- Der separate Bundle-Smoke meldete `OK: healthy on port 8474`,
  `OK: bundled local ASR runtime usable` und `OK: clean shutdown`.
- Der separate kanonische Archiv-Smoke meldete
  `OK: native windows-x64 update and forced rollback`.
- Die vollständige Backend-Discovery lief mit repository-internem TEMP:
  `Ran 1705 tests in 138.465s`, `OK (skipped=3)`. Es gab keine Fehler.

Status: BESTANDEN.

Naechster exakter Schritt: ausschliesslich die dokumentierten manuellen
Abnahmen A06, A18, A21 und A22 vorbereiten bzw. durchfuehren.

### Paket 2026-11-08 - Vollstaendige Frontend-Regression

- Die komplette im Frontend-Paket definierte Testsuite wurde mit erlaubtem
  `esbuild`-Prozessstart ausgefuehrt: `npm test` meldet 268 Tests, 268 Pass,
  0 Fail, 0 Cancelled, 0 Skipped.
- Damit sind die vorherigen 21 `spawn EPERM`-Fehler als reine Sandboxgrenze
  bestaetigt und mit der freigegebenen Ausfuehrung ausgeraeumt.

Status: BESTANDEN.

Naechster exakter Schritt: nur noch die realen manuellen Abnahmen und die
separate Betreiberfreigabe fuer einen sauberen synchronisierten Release-Branch.

### Paket 2026-11-08 - PWA-Maskable-Assetvertrag und finaler A24-Rebuild

- `npm run test:pwa` fand zunaechst einen echten Fehler: Die beiden
  maskable PNGs waren schwarze Vollflaechen mit einem Mark ausserhalb der
  40%-Safe-Zone und nicht im manifestierten Theme-Hintergrund.
- `frontend/scripts/make_pwa_icons.py` leitet die maskable Varianten jetzt
  reproduzierbar aus `desktop/assets/icon.png` ab, entfernt nur den
  randverbundenen Quellhintergrund, setzt `#0f172a` als opaque Hintergrund und
  skaliert das Mark in die Safe-Zone. `npm run test:pwa` ist danach 5/5 gruen.
- Der Frontend-Produktionsbuild blieb bei 2139 Modulen gruen. Der Windows-
  Kandidat wurde danach erneut gebaut; der Bundle-Smoke meldete Health,
  lokales ASR und sauberen Shutdown, der kanonische Archiv-Smoke meldete
  `OK: native windows-x64 update and forced rollback`.

Status: BESTANDEN.

Naechster exakter Schritt: keine weitere automatisierbare V3-Luecke bekannt;
offen bleiben nur die dokumentierten manuellen Abnahmen und Betreiberbedingungen.

### Paket 2026-11-08 - Docs-site Release-Regression

- Die sechs fokussierten Docs-Suites sind nach `npm ci` gruen:
  Release-Access 27/27, Migration 8/8, Worker 83/83, Admin 19/19,
  Download 13/13 und Site 17/17.
- Der aggregierte Lauf `node --test *.test.js` ist mit 206/206 Tests,
  0 Fehlern, 0 Abbruechen und 0 Skips gruen.
- `npm run build` ist gruen: 14 Seiten gebaut, Pagefind-Index und
  `dist-site` erzeugt. Die bestehende Vite-Warnung fuer die Newsreader-Schrift
  bleibt eine Laufzeitreferenz und kein Buildfehler.
- `npm ci` meldet 14 transitive Audit-Hinweise (2 moderate, 11 high,
  1 critical); es wurde kein automatischer Audit-Fix ausgefuehrt, weil dieser
  den bestehenden freigegebenen Arbeitsstand ausserhalb des V3-Vertrags
  veraendern wuerde.

Status: BESTANDEN fuer die V3-/Release-Vertragspruefung.

Naechster exakter Schritt: nur noch die dokumentierten manuellen V3-Abnahmen
und die Betreiberentscheidung fuer den sauberen Release-Checkout.

### Paket 2026-11-08 - Docs-Produktionsabhaengigkeiten sicher aktualisiert

- Der rein lesende Produktions-Audit hatte zunaechst 11 Befunde, darunter
  einen kritischen Astro-RCE-Fix und mehrere hohe Befunde in Sharp, devalue,
  js-yaml, SVGO, Vite und Zod. Das war eine echte Release-Sicherheitsluecke.
- `docs-site/package.json` wurde gezielt auf `@astrojs/starlight` 0.42.10,
  `astro` 7.4.7 und `sharp` 0.35.5 angehoben; `npm update` aktualisierte die
  transitiven Patchstaende bis `postcss-selector-parser` 7.1.7.
- `npm audit --omit=dev --audit-level=high` meldet danach `found 0
  vulnerabilities`.
- Die sechs fokussierten Suites nach dem Update bleiben gruen:
  27/27, 8/8, 83/83, 19/19, 13/13 und 17/17. Der Aggregatlauf bleibt
  206/206; `npm run build` erzeugt weiterhin 14 Seiten und `dist-site`.

Status: BESTANDEN.

Naechster exakter Schritt: nur noch die dokumentierten manuellen V3-Abnahmen
und die Betreiberentscheidung fuer den sauberen Release-Checkout.

### Paket 2026-11-08 - A23 sichere Adoption und Release-Vertraege

- Backend-Schema-/Adoptionssuite: `tests.test_main_schema` -> 20/20. Die
  Tests decken Legacy-Adoption, Migrationen 028-031, stabile Referenzen,
  Audio-Recovery vor Orphan-Cleanup und die aktuelle Datenform ab.
- Desktop-/Release-Suite mit `PYTHONPATH=backend`: Manifest, Plattform-
  Signatur, Cleanup-Vertrag und nativer Archiv-Smoke -> 43/43.
- Die Release-Vertraege verlangen weiterhin einen sauberen synchronisierten
  `master`; der aktuelle gemischte Arbeitsbaum wurde nicht bereinigt,
  committed oder veroeffentlicht.

Status: BESTANDEN.

Naechster exakter Schritt: A24 Quell-/Prompt-/Assetidentitaet des aktuellen
Windows-Kandidaten gegen einen reproduzierbaren Build-Nachweis pruefen.

### Paket 2026-11-08 - A20 ehrliche Transcription-Readiness

- Der fokussierte Gesamtfall prueft lokale Modellbereitschaft, fehlende
  Runtime/Data-Datei, fehlende oder fehlerhafte Cloud-Credentials,
  ungueltige Auswahl, den WebSocket-Start-Gate sowie lokale Retranscription.
- Die lokale Probe importiert `onnx_asr` und prueft die zur Laufzeit benoetigte
  `fbanks.npz`-Ressource. Ein Fehler wird als `transcription_unready` mit
  konkreter Ursache gemeldet; es gibt weder stillen Download noch impliziten
  Cloud-Fallback.
- Nachweis mit projektgebundenem Python 3.12.10 und isoliertem TEMP:
  `python -m unittest tests.test_transcription_readiness
  tests.test_local_asr_readiness tests.test_transcription_runtime
  tests.test_audio_handler.TranscriptionReadinessGateTests
  tests.test_transcription_jobs tests.test_retranscribe` -> 45/45.

Status: BESTANDEN.

Naechster exakter Schritt: A23 Migrations-/Legacy-Adoption und Packaging-
Nachweis mit der fokussierten Schema-/Release-Suite pruefen.

### Paket 2026-11-08 - A19/N4 Strict-local-Transportgrenzen

- Der neue Regressionstest prueft beide app-eigenen Loopback-Transporte mit
  einem als on-prem markierten Ziel. `allows_local_only()` verweigert sie
  trotzdem; die Zulassung darf nicht aus Loopback-URL oder Anzeigename allein
  abgeleitet werden.
- Oeffentliche Endpoints und fehlende/ungueltige Endpoints bleiben fail-closed.
  LAN-/Loopback-Inference wird nur fuer den expliziten OpenAI-kompatiblen
  Endpointpfad zugelassen. Der Browser-Web-Speech-Hook wird im aktuellen
  Produktpfad nicht gestartet; die Desktop-/Web-Aufnahme laeuft ueber den
  Backend-Audiopfad, sodass Browser-ASR nicht stillschweigend Strict-local
  ersetzt.
- Nachweis mit projektgebundenem Python 3.12.10 und isoliertem Repository-TEMP:
  `python -m unittest tests.test_privacy tests.test_privacy_agent_admission
  tests.test_custom_endpoints tests.test_llm_endpoint
  tests.test_llm_self_hosted_limits` -> 137/137. Der erste nicht isolierte
  Lauf war wegen Windows-TEMP-ACL nicht verwertbar; der isolierte Lauf ist
  vollstaendig gruen.

Status: BESTANDEN.

Naechster exakter Schritt: A20 Readiness-/Offline-Gesamtfall (Start, Warmup,
Postcall) ausfuehren und verbleibende offene Downloads/Fallbacks schliessen.

### Paket 2026-11-08 - A17 Quellen-Scope gegen Wahrheitsuebernahme

- Red-Test reproduzierte, dass eine formal gueltige Quellen-ID mit
  widersprechender Einheit oder Population bisher trotzdem eine numerische
  Empfehlung stuetzen konnte.
- `backend/app/services/agents/orchestrator.py` bindet strukturierte
  Quellenmetadaten jetzt an den Ziel-/Sprechkontext. Einheit, Zeitraum und
  Population muessen jeweils in diesem Kontext vorkommen; Einheiten werden
  mit Prozent-/Prozent-Aliasen und vorsichtiger Flexionspraefixlogik verglichen.
  Bei fehlender Bindung wird die numerische Aussage nicht als belegt
  uebernommen.
- Nachweis: `python -m unittest tests.test_debate_copilot.DebateRecommendationTests`
  -> 26/26; `python -m unittest tests.test_debate_research tests.test_argument_graph tests.test_debate_copilot`
  -> 88/88. Der Lauf enthaelt nur den bekannten harmlosen Pending-Research-
  Logeintrag.

Status: BESTANDEN.

Naechster exakter Schritt: A19/N4 Strict-local- und Browser-ASR-Umgehungen als
End-to-End-Vertrag pruefen und bei einer Luecke mit Red-Test schliessen.

### Paket 2026-11-08 - A06/P0 Diarization-Backlog ohne PCM-Verlust

- Red-Test `backend/tests/test_diarization_backlog.py` reproduzierte, dass
  `_shed_diarization_backlog` bereits angenommene Queue-Frames entfernte und
  die Pending-Zeitstempel verschob.
- Der Guard ist jetzt eine reine Ueberlaufpruefung. Die Audioannahme in
  `backend/app/ws/audio_messages.py` prueft den prospektiven Bytebestand vor
  Samplezaehler, Writer, Gateway und Queue. Bei Ueberschreitung wird der neue
  Frame abgewiesen, `state.stopped` gesetzt, `diarization_overflow` mit
  `rejected_bytes`/`frames_dropped: 0` gesendet und der vorhandene Backlog im
  Full-Drain weiterverarbeitet.
- `backend/app/ws/audio_pipeline.py` beendet die Empfangsschleife unmittelbar
  nach diesem kontrollierten Stop. Ein Drain-Timeout meldet jetzt explizit
  `audio_gap` mit der Zahl der nicht mehr transkribierbaren akzeptierten Frames;
  es gibt keinen stillen Drop mehr.
- Neu/angepasst: `backend/tests/test_audio_handler.py` prueft die Ablehnung
  vor Mixer/Queue sowie den sichtbaren Gap; der Backlog-Test prueft Queue,
  Sentinel und Pending-Ledger auf unveraenderten Inhalt.

Nachweis:

- Red: `python -m unittest tests.test_diarization_backlog` schlug vor der
  Korrektur in 3 Overflowfaellen fehl.
- Green: `python -m unittest tests.test_audio_handler.DiarizationWorkerShutdownTests tests.test_audio_handler.AudioPipelineOrderingTests tests.test_diarization_backlog` -> 12/12.
- Regression ausserhalb der Windows-TEMP-ACL-Sandbox mit projektgebundenem
  Python 3.12.10: `python -m unittest tests.test_audio_handler tests.test_diarization_backlog tests.test_windows_audio_capture tests.test_pii_shield` -> 107/107.

Status: technischer Teil BESTANDEN; A06 insgesamt BLOCKED wegen nicht
ausfuehrbarer realer deutscher Mikrofon-/Discord- und Overlap-Abnahme.

### Paket 2026-11-08 - A15 Lernbeispiele explizit und widerrufbar

- `backend/tests/test_debate_learning.py` deckt die bisher unbelegten
  Grenzen direkt ab: Ablauf filtert abgelaufene Beispiele, ein neuer DB-Reader
  sieht gueltige Beispiele nach einem Neustart, Widerruf bleibt mit Korrektur
  persistent und Duplikate werden deterministisch ersetzt.
- Der Test verifiziert ausserdem, dass ein bestaetigtes hilfreiches Beispiel
  kein Faktenlabel erhaelt (`feedback_kind=usefulness`,
  `factual_status=unverified`) und nicht exportiert wird.

Nachweis: `python -m unittest tests.test_debate_learning` -> 3/3 gruen.
Status: BESTANDEN.

### Paket 2026-11-08 - A13 Sprecher-Revalidierung gegen Stale-Race

- Die vorhandenen Vertragspruefungen wurden erneut ausgefuehrt. Die
  Enhancement-Abfrage selektiert nur die der Batch zugewiesenen Insight-IDs;
  die Caller-Transaktion stempelt auch nur diese Eintraege mit der laufenden
  Mapping-Revision.
- `finalize_run_state` markiert eine erfolgreiche alte Revalidierung bei
  zwischenzeitlich erhoehter `speaker_context_version` wieder als dirty und
  setzt keinen falschen Abschlusszeitpunkt fuer die neue Sprecherrevision.
- Der Test `test_finalization_clears_only_the_mapping_version_that_ran` prueft
  die Race-Reihenfolge (Revision 1 laeuft, Revision 2 wird gespeichert),
  `test_batch_applies_and_stamps_only_assigned_insights_in_caller_transaction`
  prueft die Abhaengigkeitsbegrenzung.

Nachweis: `python -m unittest tests.test_speaker_revalidation tests.test_speaker_context_enhancer` -> 46/46 gruen.
Status: BESTANDEN.

### Paket 2026-11-08 - A01 dauerhafte Audioannahme und Crash-Recovery

- `SegmentAudioWriter.append` und `close` synchronisieren den aktiv erlaubten
  Audioarchiv-Track mit `flush` plus `os.fsync`, bevor der jeweilige Aufruf als
  erfolgreich weiterlaufen kann. Ohne aktiviertes Audioarchiv bleibt der
  bestehende Retention-Vertrag unveraendert; es wird keine heimliche Datei
  erzeugt.
- `backend/tests/test_audio_store.py` prueft die neue Barriere mit einer
  isolierten Writer-Instanz und bestaetigt weiterhin WAV-Roundtrip,
  Tracktrennung und Orphan-Cleanup.
- `repair_wav_file` repariert beim Start die RIFF-/data-Groessen eines
  fsynced, aber vor `close` abgebrochenen WAVs. `_recover_interrupted_audio`
  verknuepft diese Dateien ueber Session-/Segmentnummer, markiert das Segment
  beendet und fuehrt die Aux-Orphan-Bereinigung erst danach aus.

Nachweis: `python -m unittest tests.test_audio_store tests.test_main_schema` -> 28/28 gruen (projektgebundenes Python, isolierter TEMP ausserhalb der ACL-Sandbox). Der Recovery-Test simuliert den Crash exakt am offenen WAV-Header und prueft die anschliessende Startup-Verknuepfung.
Status: BESTANDEN fuer das zugesagte lokale Crashfenster; kompletter Datentraegerverlust bleibt ausserhalb des Vertrags.

### Paket 2026-11-08 - A02 Commit vor WebSocket-Sendefehler

- Der bestehende Commit-vor-Senden-Schutz wurde mit einem echten
  deterministischen Senderfehler verbunden: der alte Socket kann nach dem
  Persistenzcommit scheitern, ohne dass der Interimtext aus dem Journal
  verschwindet.
- Ein neu geoeffneter Socket fordert den Snapshot an und erhaelt den
  persistierten Text genau einmal. Das trennt DB-Commit, Journal-Replay und
  Transportfehler; ein erfolgreiches `send_json` wird nicht als DB-Beleg
  missverstanden.

Nachweis: `python -m unittest tests.test_pii_shield tests.test_ws_event_stream tests.test_provisional_transcripts` -> 58/58 gruen.
Status: BESTANDEN.

### Paket 2026-11-08 - A03 Replay-Identitaet und Audiobereich

- Die aktuellen Revision-/Replaypruefungen wurden zusammen mit den
  Transcript-Revisionen und der lokalen Live-Captioner-Spur ausgefuehrt.
  Technische Duplikate werden ueber `(session_id, segment_id, revision)`
  entwertet; wortgleiche echte Wiederholungen mit neuer Segmentidentitaet
  bleiben getrennt. Append-Revisionsmaterialisierung und Audioanfang/-ende
  bleiben adressierbar.
- Neustart-/Capture-Generation ist im Laufzeitpfad ueber neue Segment-IDs und
  Samplebereiche getrennt, aber noch nicht als eigener persistierter
  End-to-End-Reconnect-Test belegt. Deshalb bleibt A03 konservativ
  `IMPLEMENTIERT`.

Nachweis: `python -m unittest tests.test_provisional_transcripts tests.test_transcript_revisions tests.test_local_live_captioner tests.test_audio_handler.AudioFrameDecodingTests` -> 24/24 gruen.
Status: IMPLEMENTIERT (Replay-/Audiobereich bestanden; Generationstest offen).

### Paket 2026-11-08 - A05 Raten, Tail und Geraetewechsel

- Die native Converter-Pruefungen decken jetzt 44,1-kHz- und 48-kHz-Eingang,
  mehrteilige Callback-Bloecke mit Restbuffer, PCM16-Mono-Ausgabe und getrennte
  Zustandsobjekte je Spur ab.
- Der Capture-Monitor erkennt eine geaenderte Default-Geraeterate als
  kontrollierten Neustart; die vorhandenen TrackMixer-Tests pruefen Alignment,
  Solo-Tail und Clamping weiter.

Nachweis: `python -m unittest tests.test_windows_audio_capture tests.test_track_mixer` -> 18/18 gruen.
Status: BESTANDEN fuer den synthetischen Rate-/Tail-/Device-Vertrag; reale
Windows-Hardwareumschaltung bleibt Teil der manuellen Abnahme.

### Paket 2026-11-08 - A08 Native Cancellation und Lane-Quarantaene

- Die Native-Inference-Vertragspruefungen wurden erneut ausgefuehrt. Eine
  abgebrochene Coroutine wird sofort freigegeben, aber der laufende Thread
  bleibt bis zum physischen Ende supervised; die gemeinsame Lane bleibt bis
  dahin unbenutzbar.
- Der unowned Helper haelt denselben Worker nach Cancellation referenziert,
  ohne das Shutdown-Warten des Aufrufers zu blockieren.

Nachweis: `python -m unittest tests.test_native_inference tests.test_debate_copilot` -> 66/66 gruen.
Status: BESTANDEN.

### Paket 2026-11-08 - A09 Manuelle Revision vor spaeter Automatik

- Manuelle Transcriptkorrekturen gewinnen gegen spaete Modellantworten:
  Revision und abhaengige Empfehlung werden erhoeht/entwertet, waehrend die
  alte sprachliche Grundlage nachvollziehbar bleibt.
- Stale Debatten-/Research-Revisionen werden nicht erneut sichtbar gemacht;
  Refinerfehler behalten die Originaltexte statt eine leere oder spekulative
  Fassung zu speichern.

Nachweis: `python -m unittest tests.test_transcript_revisions tests.test_transcript_refiner tests.test_debate_copilot` -> 77/77 gruen.
Status: BESTANDEN.

### Paket 2026-11-08 - A10 Leere Finals und Nachbargrenzen

- Die Revision- und Ordered-Transcription-Pruefungen wurden gemeinsam
  ausgefuehrt. Ein leeres Final loescht keinen sichtbaren Text; ein kuerzeres
  Final ersetzt nur den exakt identifizierten Segmentbereich. Spaetere
  Nachbarjobs bleiben geordnet und Split-Track-Topologie wird nicht durch das
  Ende einer Spur zurueckgesetzt.

Nachweis: `python -m unittest tests.test_provisional_transcripts tests.test_ordered_transcription tests.test_audio_handler.AudioPipelineOrderingTests tests.test_audio_handler.AudioFrameDecodingTests` -> 27/27 gruen.
Status: BESTANDEN.

### Paket 2026-11-08 - A07 Snapshot-Delta und Restart-Epoche

- Ein neuer Journal-Test modelliert zwei asynchrone Writer mit umgekehrter
  Commit-/Fertigstellungsreihenfolge. Der Snapshot nach Writer B setzt den
  Cursor genau hinter B; Writer A bleibt danach als Delta replaybar und wird
  nicht wegen eines zu grossen oder alten Cursors uebersprungen.
- Die vorhandene Serverepoche erzwingt bei Neustart einen Vollsnapshot; die
  Frontend-Tests pruefen den kontrollierten Cursor-/History-Reset und die
  anschliessende Sequenzverarbeitung.

Nachweis: Backend `python -m unittest tests.test_ws_event_stream tests.test_pii_shield` -> 75/75 gruen; Frontend `node --test --test-isolation=none src/hooks/useWebSocket.test.mjs src/lib/wsEventStream.test.mjs` -> 18/18 gruen.
Status: BESTANDEN fuer den synthetischen Snapshot-/Cursor-Vertrag.

### Paket 2026-11-08 - A16 Prompt-Defaults, Overrides und Hauptzug

- Die Prompt-/Konfigurationssuite wurde vollstaendig erneut ausgefuehrt.
  Gespeicherte Prompts bleiben benutzergefuhrt, Overrides werden sofort aktiv,
  Versionen koennen gezielt restauriert werden und Reset laedt den gebuendelten
  Default statt eines versteckten Hardcodes.
- Der Copilotvertrag validiert einen einzigen sprechbaren Hauptzug; Frage,
  Antwort oder Eingrenzung duerfen ohne kuenstliches Pflicht-Bundle gewaehlt
  werden. Persuasive/forceful und Style-Fokus werden als getrennte Ressourcen
  in den effektiven Prompt eingebunden.

Nachweis: `python -m unittest tests.test_ai_config tests.test_prompt_ordering tests.test_debate_copilot` -> 100/100 gruen (isolierter TEMP ausserhalb der ACL-Sandbox).
Status: BESTANDEN fuer den technischen Prompt-/Settings-Vertrag; menschliche Rhetorikabnahme bleibt A18.

### Naechste exakt ausfuehrbare Aktion

A17 direkt pruefen: Quellen-ID, Passage, Zeitraum, Population, Einheit und
Negation als Wahrheitsbindung gegen Gegenpassagen testen.

## Paket 2026-11-07 - dauerhafte vorlaeufige Transkriptrevisionen

Erledigt und geprueft:

- `provisional_transcript_revisions` speichert Live-ASR-Hypothesen append-only
  mit Session, Segment-ID, Revision, Track und vorhandener Originalaudio-
  Samplebasis. `UNIQUE(session_id, segment_id, revision)` macht technische
  Replays idempotent; verschiedene Segment-IDs erhalten wortgleiche echte
  Wiederholungen.
- Der Retention-Aus-Schalter laesst Interims weiterhin live erscheinen, legt
  aber keine Revisionszeile an. Bei aktivierter Speicherung wird zuerst
  committed und erst danach gesendet. Ein Commitfehler erscheint daher nicht
  als gespeichert.
- Leere und stale Revisionen werden ignoriert. Append-Deltas werden vor der
  Speicherung materialisiert. Ein nichtleeres Final mit exakt derselben
  Segment-/Audiozuordnung markiert seine Entwurfsrevisionen unabhaengig von der
  Textlaenge atomar als finalisiert; ein leeres oder unzugeordnetes Final ist
  keine Loeschanweisung. Die append-only Entwurfszeilen bleiben als Historie
  erhalten.
- REST/Session-Laden projiziert nur die neueste nicht finalisierte Revision je
  Segment. Reconnect-Status laedt diesen Stand neu; ein zugleich replaytes
  Live-Interim wird in der UI nicht doppelt dargestellt. Die UI kennzeichnet
  ihn ehrlich als `Gespeicherter Entwurf`.
- Migration `030_provisional_transcript_revisions` ist fuer normale Upgrades
  und fuer die bestehende Legacy-Adoption idempotent.

Geaenderte Pfade dieses Pakets:

- `AGENTS.md`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/routers/transcripts.py`
- `backend/app/services/provisional_transcripts.py`
- `backend/app/services/pii/ws.py`
- `backend/app/ws/audio_handler.py`
- `backend/alembic/versions/030_provisional_transcript_revisions.py`
- `backend/tests/test_provisional_transcripts.py`
- `backend/tests/test_pii_shield.py`
- `backend/tests/test_audio_handler.py`
- `backend/tests/test_main_schema.py`
- `frontend/src/App.tsx`
- `frontend/src/types/index.ts`
- `frontend/src/lib/sessionRefresh.ts`
- `frontend/src/lib/sessionRefresh.test.mjs`
- `frontend/src/components/ActiveCall/TranscriptPanel.tsx`
- `frontend/src/components/ActiveCall/TranscriptPanel.test.mjs`

Belege:

- 36 fokussierte Backendchecks fuer Persistenz, Commit-vor-Senden,
  Retention, Finalisierung, Migration, Replay und Sequenz: gruen.
- 20 fokussierte Frontendchecks fuer gespeicherten Status, Reconnect,
  Deduplizierung und WebSocket-Replay: gruen.
- Python-Kompilierung: gruen; Alembic-Head:
  `030_provisional_transcript_revisions`.
- Frontend-Produktionsbuild: gruen, 2139 Module; bestehende Chunkwarnung bleibt.

Echter PostgreSQL-Beleg:

- Aus dem gebuendelten PostgreSQL wurde ein isolierter Wegwerfcluster auf Port
  55432 erstellt. Zwei echte parallele `asyncpg`-Transaktionen schrieben
  dieselbe Segment-/Revisions-ID. Ergebnis: genau ein Writer `created=True`,
  genau eine Datenbankzeile, kein Unique-Fehler. Der Cluster wurde danach
  gestoppt und sein verifizierter Temp-Pfad entfernt; Nutzerdaten waren nicht
  beteiligt. Test: `tests.test_provisional_transcripts_postgres`, 1/1 gruen.

## Paket 2026-11-07 - Deutsch-ASR A/B und Lastbeleg

- Vorhandenes reales 16-kHz-Mono-Audio wurde verwendet; keine neue Aufnahme
  oder synthetische Behauptung erfunden. Die Modelle lagen bereits lokal vor.
- Kontrollsatz `artifacts/real-smoke/german-asr.wav` (6,575 s): Whisper Base
  lieferte `Der Ausbau erneuerbare Energien ...`, Parakeet v3 den grammatisch
  richtigen Text `Der Ausbau erneuerbarer Energien ...`. Warm-RTF Whisper
  0,066-0,068, Parakeet 0,044-0,046; beide schneller als Echtzeit.
- Reale Nutzeraufnahme `a903.../segment_1_mic.wav`, 15-s-Fenster: Whisper blieb
  deutsch und erkannte den Kern `Feminismus`; Parakeet wechselte in einem
  schwierigen Fenster faelschlich auf `Definitely for that.`. Eine zweite
  reale Aufnahme (`bb4...`) bestaetigte denselben Sprachstabilitaetsvorteil:
  Whisper `Hallo Test Test Test`, Parakeet begann mit `Yes`.
- Vier gleichzeitig angeforderte Whisper-Transkriptionen desselben 6,575-s-
  Audios wurden ueber die native Inferenzlane vollstaendig verarbeitet:
  2,647 s Wandzeit fuer 26,3 s Audio, aggregiertes RTF 0,101, 4/4 nicht leer.

Entscheidung: `local-whisper-base` bleibt als deutscher Final-Standard. Der
einzelne saubere Kontrollsatz reicht nicht fuer einen Wechsel zu Parakeet, weil
die reale schwierige Aufnahme dessen englischen Fehlwechsel reproduziert.
Parakeet bleibt die schnelle Live-Spur; das bestehende Whisper-Kontextbatching
bleibt die verlustsicherere finale Loesung.

## Paket 2026-11-07 - lokale Sofortantwort und Rhetorikvertrag

- Der aktive Desktoppfad bleibt
  `endpoint:german-debate-ollama:qwen3:4b`. Die Live-Lane verwendet Ollamas
  native `/api/chat`-Route, `think=false`, den exakten Pydantic-JSON-Vertrag,
  begrenzten Kontext/Output und einen abschliessenden `/no_think`-Schalter.
- `debate_live_v2` verlangt einen sofort sprechbaren deutschen Satz mit
  hoechstens 25 Woertern sowie Gegenargument, Gegenfrage, Analogie,
  Zielbehauptung, Argumentpunkte, Unsicherheit und Recherchebedarf. Der Prompt
  behandelt ASR als fallibel und verbietet erfundene Fakten und erfundene
  persoenliche Erlebnisse.
- Beide aktiven Modi sind getrennt und quellgeprueft: `persuasive` nutzt
  Steelman/gemeinsame Basis; `forceful` greift die konkrete Behauptung hart in
  der Sache, nie die Person, an. Der Moduswechsel erzwingt einen neuen Scan.
- 62 fokussierte Kernpruefungen fuer Objection Handler und lokale
  Self-hosted-Limits sind gruen. Sie decken beide Modi, Analogievertrag,
  kurze Sprechfelder, `/no_think`, native Ollama-Steuerung und begrenzte
  Ausgabe ab.
- Ein echter erneuter Produktionspfad-Lauf mit Ollama 0.40.14 und dem lokalen
  `qwen3:4b` (4,0B, Q4_K_M) ist jetzt belegt. Kaltstart: erste sichtbare
  Modellantwort 4106,760 ms, vollstaendige strukturierte Empfehlung
  7419,898 ms. Warm: erste sichtbare Modellantwort 1414,327 ms,
  vollstaendige Empfehlung 4145,994 ms. Der Warmwert fuer die erste nutzbare
  Anzeige liegt damit unter 2,5 s; der vollstaendige Kaltstart liegt nicht im
  Ziel und wird nicht als bestanden ausgegeben. Der historische paketierte
  Beleg von etwa 0,8-1,1 s bleibt ein separater Altbeleg, nicht das Ergebnis
  dieser Messung.
- Der Benchmark lief durch `AgentOrchestrator`, `ObjectionHandlerAgent`, den
  strukturierten lokalen LLM-Router und die echte `debate_update`-Ausgabe. Sein
  Replay wurde an den aktuellen `DebateSettings`-Vertrag angepasst.
- Der Kontrolllauf deckte eine echte Luecke auf: explizite Playbook-
  Sprachbefehle vom eigenen Mikrofon wurden trotz aktiviertem Sprachbefehl-
  Schalter als Transkript behandelt. Die kleine Allowlist akzeptiert jetzt die
  vorhandenen Playbooks nur nach Wake-Phrase, nur vom lokalen Mikrofon und nur
  fuer den Teamsprecher. Fremd-/Gegneraudio bleibt ausgeschlossen. `Zeile fuer
  Zeile` wurde im warmen Echtlauf verbraucht, veraenderte das Transkript nicht
  und zeigte nach 1428,067 ms eine neue Modellantwort.
- 76 direkte Tests fuer Benchmark und Debate-Copilot sind gruen. Der eigens
  gestartete Ollama-Prozess wurde nach der Messung anhand PID und Programmpfad
  beendet; die ausschliesslich dafuer erzeugten Messdateien wurden entfernt.

Geaenderte Pfade und direkte Belege dieses Teilpakets:

- `backend/app/services/agents/orchestrator.py`
- `backend/scripts/benchmark_debate_copilot.py`
- `backend/tests/test_debate_copilot.py`
- `backend/tests/test_debate_benchmark.py`
- `python -m unittest tests.test_debate_benchmark tests.test_debate_copilot`:
  76/76 gruen.
- `scripts/build_debate_assistant.ps1 -Python ./.venv/Scripts/python.exe
  -SkipDownloads`: Exit 0; `npm ci` meldete 0 Schwachstellen, Frontendbuild,
  Bundle-Smoke und Archiv-Smoke waren gruen. Der erste Sandboxversuch konnte
  nur den npm-Unterprozess nicht starten (`EPERM`); derselbe Build lief danach
  mit der erforderlichen Prozessberechtigung erfolgreich.

## Paket 2026-11-07 - Hintergrundanalyse und Provider-Vertraege

- Der aktive Standard priorisiert nur aktivierte Routen in gespeicherter
  Reihenfolge: normales ChatGPT-Webkonto, Gemini-Web, ChatGPT/Codex-OAuth und
  Gemini-CLI-OAuth. Die offizielle kostenpflichtige Gemini-API ist im
  gebuendelten Standard deaktiviert und wurde nicht aufgerufen.
- `Privacy First` verhindert externe Recherche und laesst Agenten nur zu, wenn
  das konkrete Ziel lokal/on-prem eingestuft wurde. Ein unbekannter oder
  entfernter Endpoint wird nicht irrtuemlich als lokal zugelassen.
- Sofortantwort und Hintergrundanalyse bleiben getrennt: Logikpruefung kann
  ohne Websuche laufen; Recherche ist eng, spaeter und darf die Sofortantwort
  nicht blockieren. Veraltete Ergebnisse duerfen nur in den Claim-Speicher,
  nicht auf die aktuelle Karte.
- Automatische Analysen sind gebremst und werden bei blossen Paraphrasen nicht
  neu gestartet. Manuelle Jobs haben Scheduler-Prioritaet, koennen
  sitzungsbezogen abgebrochen werden und stoppen keine gemeinsam genutzte
  Provider-Bridge. Deadline umfasst Warteschlange, Recherche, Retry und
  Fallback; Providerfehler setzen einen begrenzten Cooldown.
- 72 lokale Tests fuer Scheduler, Recherche-Sharing/Abbruch, Privacy-Zulassung,
  LLM-Routing und die relevanten Orchestratorvertraege sind gruen. Weitere 5
  direkte Tests fuer gespeicherte Providerreihenfolge, Hintergrundanalyse ohne
  Websuche, Claim-Verdichtung, Paraphrasenbremse und manuellen Abbruch sind
  gruen. Es wurde kein Web-, Login- oder kostenpflichtiger Modellcall erzeugt.

## Paket 2026-11-07 - UI/Settings und ehrliche Privacy-Zustaende

- Unter `Privacy First` sind automatische und manuelle Live-Rechercheaktionen
  jetzt wirklich deaktiviert. Die Oberflaeche sagt ausdruecklich, dass
  oeffentliche Recherche blockiert ist und die lokale Sofortantwort weiterlaeuft.
- Beide Debattenmodi, Retention und aktive Einstellungen bleiben an die
  vorhandenen Laufzeitvertraege gebunden; es wurde kein Scheinzustand fuer
  blockierte Provider eingefuehrt.
- 16 Coach-, 20 Active-Call- und 2 Settings-Vertragstests sind gruen. Der
  Produktionsbuild ist gruen; nur die bereits bekannte Chunkwarnung bleibt.

## Paket 2026-11-07 - unabhaengiger Review: Finalisierung und Korrekturhistorie

Erledigt und geprueft:

- Der lokale Live-Captioner fuehrt seine tatsaechliche Segment-ID bis zum
  finalen Datenbankcommit. Ein Final markiert damit nicht mehr nur die generische
  Gateway-ID; Sampleposition `0` bleibt eine gueltige Audiozeit und wird nicht
  durch einen Fallback ersetzt.
- Dauerhafte Finalzeilen speichern `utterance_id` und Produzentenrevision. Die
  Aeusserungs-ID ist zugleich der stabile UI-/Analysebezug; der Datenbankzeilen-
  Primaerschluessel bleibt die unverwechselbare Identitaet jedes gespeicherten
  Evidenzfragments.
- Migration `031_transcript_entry_revisions` ergaenzt die stabilen Bezuege, den
  manuellen Korrekturmarker und die append-only Tabelle
  `transcript_entry_revisions`. Original, Text, Sprecher, Quelle, Grund und
  Zeitpunkt bleiben nachvollziehbar.
- Manuelle Text- und Sprecherkorrekturen laufen unter einer Zeilensperre. Die
  erste Korrektur sichert den vorherigen Stand; jede weitere erhaelt eine
  monotone Revision. Leere und wirkungslose Aenderungen erzeugen keine Historie.
- Eine manuell korrigierte Zeile ist fuer den asynchronen Transcript Refiner
  gesperrt. Auch ein bereits laufender Refiner laedt die Zeile vor dem Schreiben
  erneut unter Sperre und darf eine inzwischen manuelle Korrektur nicht
  ueberschreiben.
- Haengt die sichtbare Live-Empfehlung von derselben Aeusserung ab, wird sie nach
  dem dauerhaften Korrekturcommit sofort sichtbar entwertet, alte Argumente und
  Quellen werden entfernt, die Transkriptrevision erhoeht und eine neue lokale
  Bewertung gestartet. Verspaetete alte Ergebnisse scheitern an der vorhandenen
  Claim-/Revisionssperre.
- Die Post-Call-Ansicht erlaubt die Korrektur nur fuer dauerhafte Finalzeilen,
  zeigt `Manuell korrigiert`, erfasst einen optionalen Grund und verwendet
  stabile Identitaeten statt Arrayindex als Listenschluessel. Gespeicherte
  Entwuerfe bleiben bis zum Final absichtlich schreibgeschuetzt.

Geaenderte Pfade dieses Pakets:

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/routers/transcripts.py`
- `backend/app/services/transcript_revisions.py`
- `backend/app/services/transcript_refiner.py`
- `backend/app/services/agents/orchestrator.py`
- `backend/app/ws/audio_handler.py`
- `backend/alembic/versions/031_transcript_entry_revisions.py`
- `backend/tests/test_transcript_revisions.py`
- `backend/tests/test_transcript_refiner.py`
- `backend/tests/test_debate_copilot.py`
- `backend/tests/test_audio_handler.py`
- `backend/tests/test_main_schema.py`
- `frontend/src/types/index.ts`
- `frontend/src/services/api.ts`
- `frontend/src/components/PostCall/TranscriptReview.tsx`
- `frontend/src/components/PostCall/PostCallView.tsx`
- `frontend/src/components/PostCall/TranscriptReview.test.mjs`

Belege:

- 24 direkt relevante Backendtests fuer Revisionen, Refiner-Rennbedingung,
  Migration, Entwurfspersistenz, atomare Finalisierung und Live-Entwertung:
  gruen.
- Der breitere Audio-/Persistenzlauf pruefte 75 Faelle: 74 liefen in der Sandbox
  gruen; der einzige Windows-Temp-ACL-Fall lief anschliessend einzeln ausserhalb
  der Sandbox gruen. Es bleibt daraus kein Produktfehler offen.
- 22 Post-Call-, Korrektur- und API-Vertragstests: gruen.
- Python-Kompilierung und zielbezogenes `git diff --check`: gruen; lediglich die
  bestehende LF/CRLF-Hinweiswarnung erscheint. Alembic-Head ist
  `031_transcript_entry_revisions`.
- Frontend-Produktionsbuild: gruen, 2139 Module; bekannte Warnung fuer den
  Hauptchunk groesser als 500 kB bleibt.

## Paket 2026-11-07 - Sprechervertrag, Supply Chain und lokaler Releasekandidat

- Der veraltete Retranscribe-Testvertrag wurde an den bereits aktiven
  Sicherheitsvertrag angeglichen: Eine Mikrofonspur ist eine Audioquelle und
  identifiziert ohne exakt passendes registriertes Stimmprofil nicht
  automatisch den einzigen Nutzer. Die Produktionslogik wurde dafuer nicht
  aufgeweicht. 11/11 Sprecherzuordnungs- und 17/17 Retranscribe-Tests sind
  gruen; die Windows-Tempdateitests liefen ausserhalb der Sandbox.
- Die Desktop-Release-Vertraege fuer Manifest, Updater, Launcher, PostgreSQL
  und Smokes wurden gezielt geprueft: 120 Tests gruen, ein bewusst
  uebersprungener Test. Das Manifestmodul musste wegen seines Paketimports vom
  Repository-Stamm gestartet werden; dies ist kein Produktfehler.
- `npm ci` deckte drei behebbare Build-/Dev-Abhaengigkeitswarnungen auf.
  `frontend/package-lock.json` verwendet jetzt Vite 6.4.5,
  `source-map-js` 1.2.2 und `postcss-selector-parser` 6.1.5; zwei nicht mehr in
  `package.json` enthaltene direkte DnD-Lockeintraege wurden dabei bereinigt.
  Reproduzierbares `npm ci`, `npm audit --audit-level=moderate`, UI-Test und
  Produktionsbuild sind gruen; der Audit meldet 0 Schwachstellen.
- Mit Python 3.12.10 und den acht bereits vorhandenen geprueften Offlineassets
  wurde der credential-freie lokale Windows-Kandidat erneut gebaut, zuletzt
  nach dem Abschlussaudit mit Einzelbeitrag, Retention, Audioarchiv und aktiver
  Debate-AI-Produktidentitaet. Der Build fuehrte Bundle- und
  Archiv-Smoke aus und endete mit Exit 0. Die PyInstaller-Hinweise betreffen
  nicht gebuendelte optionale PostgreSQL-Perl/Python-Erweiterungen; die
  tatsaechlich gebuendelte Datenbank-/ASR-Laufzeit bestand den Smoke.
- Der direkte Bundle-Smoke bestaetigte Health-Port, nutzbare lokale ASR-
  Laufzeit und sauberen Shutdown. Der direkte Archiv-Smoke bestaetigte nativen
  `windows-x64`-Updatepfad und erzwungenen Rollback.

Lokaler, nicht veroeffentlichter Kandidat:

- Pfad: `dist/Backchannel-DebateAI-windows-x64.zip`
- Groesse: 340119456 Byte
- Zeitstempel: `2026-11-07T22:37:32.0562780+01:00`
- SHA-256: `8EF57261907867828B57CC97AA1ADEF97020736E6AE86F965E38D1B57360037D`
- EXE-SHA-256: `8D6E9E68F6531A9D73FEBE4D2A775BD1DEB92965629B562A639DCF5404ECD3FE`
- Windows-Dateieigenschaften: Produkt `Debate AI`, Beschreibung `Debate AI`;
  der Updater traegt Produkt `Debate AI` und Beschreibung `Debate AI Updater`.
- Keine Release-Credentials gelesen, kein Tag erzeugt, nichts hochgeladen oder
  veroeffentlicht.

Diese Datei ist ab jetzt der fuehrende Arbeitsstand fuer den Auftrag in
`Debate_AI_Codex_Masterprompt_final.txt`. Die vorhandenen Dateien
`QUALITY_PLAN.md`, `PROGRESS.md` und `IMPLEMENTATION_AUDIT.md` bleiben als
historische Detailbelege erhalten und verweisen fuer neue Entscheidungen hierher.

## Ist-Stand und Schutzgrenzen

- Branch: `codex/debate-ai-master-optimization`.
- Der Arbeitsbaum enthielt vor diesem Paket bereits sehr viele geaenderte und
  neue Dateien. Es wurde nichts zurueckgesetzt, gestasht, bereinigt, committed
  oder geloescht, ausser der nachweislich abgeloesten app-eigenen
  Textaehnlichkeits-Deduplizierung.
- Ein zum aktuellen produktiven Laufzeitcode gehoerender lokaler
  Python-3.12-Desktopkandidat wurde nach dem Abschlussaudit neu gebaut
  und durch Bundle- sowie Archiv-Smoke gestartet. Er wurde nicht visuell oder
  mit einer neuen realen Sitzung abgenommen und ist kein veroeffentlichter
  Release.
- Es liegt kein neues Originalaudio fuer diesen Auftrag vor. Akustische
  Verbesserungen werden daher nicht neu behauptet. Die vorhandenen historischen
  Audio-/Deutschbelege bleiben in `PROGRESS.md` und `IMPLEMENTATION_AUDIT.md`.

## Paket 2026-11-07 - Abschlussaudit: Einzelbeitrag, Retention, Audio und Identitaet

- Der Live-Copilot waehlt jetzt genau einen primaeren sprechbaren Beitrag:
  Antwort, Rueckfrage, Einwand oder Analogie. Nicht gewaehlte Felder sind
  optional; maximal drei Argumentpunkte bleiben zulaessig. Die Liveansicht
  zeigt genau eine grosse `Jetzt sagen`-Karte und eine Alternative nur auf
  Nachfrage. Der ausdrueckliche Nutzerwert `immer Analogie` bleibt wirksam,
  ist bei neuen Installationen aber nicht mehr erzwungen.
- Dauerhafte Audioarchivierung ist eine eigene Einstellung und startet bei
  neuen Installationen ausgeschaltet. Ohne diese Einwilligung werden keine
  Segment-Audiodateien angelegt. Eine vorhandene ausdrueckliche Wahl bleibt
  erhalten.
- Bei ausgeschalteter Transkriptaufbewahrung bleiben Livezeilen fluechtig;
  auch ein Resume schreibt keinen versteckten dauerhaften Sitzungsmarker. Die
  laufende Sitzung behaelt ihren fluechtigen Kontext.
- Die aktive Produktidentitaet lautet `Debate AI`: API-Titel, sichtbare
  Desktop-/Tray-/Fehlertexte, Updatefenster, ChatGPT-/Endpoint-Hinweise,
  Briefing-Exporte und Windows-Dateieigenschaften sind angeglichen. Die
  ausgelieferten Dateinamen `Backchannel.exe`, Updatearchiv, Appdatenpfad,
  HTTP-Header, lokale Storage-Keys und Datenbankkennung bleiben absichtlich
  kompatibel, weil eine kosmetische Umbenennung ohne versionierte
  Daten-/Updatermigration bestehende Installationen, Anmeldungen und Rollback
  gefaehrden wuerde.
- Die gebuendelte PostgreSQL-16-Laufzeit wurde in einer ausschliesslich unter
  `build/.pg-durability-audit` erzeugten Wegwerf-Instanz geprueft:
  `fsync=on`, `synchronous_commit=on`. Der Ordner wurde danach entfernt; keine
  Nutzerdatenbank wurde geoeffnet oder veraendert.

Direkt geaenderte Kernpfade:

- `backend/app/services/agents/objection_handler.py`
- `backend/app/services/agents/prompts.py`
- `ai/debate_live_v2.txt`
- `backend/app/services/debate_settings.py`
- `backend/app/routers/debate_settings.py`
- `backend/app/ws/audio_handler.py`
- `backend/app/services/seed_agents.py`
- `frontend/src/components/ActiveCall/DebateCoachPanel.tsx`
- `frontend/src/components/DebateSettingsCard.tsx`
- `backend/app/main.py`
- `backend/app/services/briefing_document.py`
- `frontend/src/hooks/useDesktopUpdate.ts`
- `desktop/launcher.py`
- `desktop/scripts/version_resource.py`
- `desktop/backchannel.spec`

Pruefbelege:

- Rot-gruen fuer optionales Einzelbeitragsschema, eine primaere Karte,
  Audioarchiv-Standard aus und Resume ohne dauerhaften Retention-Marker.
- 186 fokussierte Backendtests fuer Audiohandler, Einstellungen, Seeds,
  Live-Copilot, Benchmark, Promptressourcen und Branding: gruen.
- 31 fokussierte Frontendtests fuer Livekarte, Settings und Updatefenster:
  gruen. 8 Desktop-Branding-/Ressourcentests: gruen.
- Produktionsbuild: 2139 Module, gruen; bekannte Hauptchunkwarnung bleibt.
- `scripts/build_debate_assistant.ps1 -Python ./.venv/Scripts/python.exe
  -SkipDownloads`: Exit 0 nach 402,4 s. `npm ci` meldete 0 Schwachstellen;
  Bundle- und Archiv-Smoke waren gruen.
- Kein Tag, Commit, Push, Upload, Login oder kostenpflichtiger Provideraufruf.

## Priorisierte bestaetigte Befunde

### P0 - echte Wiederholung wurde per Textaehnlichkeit geloescht - behoben

Der aktive Livepfad unterdrueckte innerhalb von zehn Sekunden jede ausreichend
aehnliche Fuenfwort-Aeusserung vor Persistenz, UI und Agentenanalyse. Text,
Wortmenge und Zeitfenster koennen einen technischen Replay nicht von einer
menschlichen Wiederholung unterscheiden.

Entscheidung: Die globale/semantische Transkript-Deduplizierung wurde komplett
aus dem Livepfad, der Konfiguration und den Tests entfernt. Technische
Idempotenz muss kuenftig an Ereignis-/Audioidentitaet gebunden sein; bis diese
Identitaet vorhanden ist, wird Sprache lieber doppelt erhalten als still
geloescht.

### P0 - kurze erste Aeusserung eines neuen Sprechers verschwand - behoben

Die sogenannte Defer-Logik beendete Live- und Importverarbeitung ohne
Transkriptzeile, wenn eine neue Sprecherzuordnung bei weniger als vier Sekunden
Audio oder weniger als zehn Woertern noetig gewesen waere.

Entscheidung: Nur die dauerhafte Sprecherzuordnung wird aufgeschoben. Der Text
wird mit `speaker_id = null` als `Unknown` gespeichert, gesendet und analysiert.

### P0 - Interim-Anhaenge konnten beim Coalescing Woerter verlieren - behoben

Mehrere `mode=append`-Ereignisse desselben Segments ersetzten einander im
Serverjournal und im Clientpuffer. Das Journal haelt nun getrennt einen
selbsttragenden, kompakten Replay-Stand, waehrend live weiterhin nur kleine
Append-Deltas gesendet werden. Der Client faltet noch nicht gerenderte Deltas
defensiv zusammen. Ein dauerhaftes Final rotiert die Gateway-Segmentidentitaet,
damit der Replay-Stand nicht ueber den ganzen Call waechst.

### P0 - Reconnect-Snapshot konnte nur eine Korrektur ohne Basiszeile liefern - behoben

`transcript` und `transcript_updated` teilten denselben Snapshot-Schluessel.
Eine Korrektur verdraengte daher die Erstellung. Beide Ereignistypen bleiben
nun getrennt im Snapshot; die UI laedt bei einer Korrektur ausserdem den
autoritativen REST-Stand gebuendelt nach. Spaete Antworten einer zuvor
angezeigten Sitzung duerfen den Zustand der neu ausgewaehlten Sitzung nicht
mehr ueberschreiben.

### P0 - alter Finalizer konnte eine fortgesetzte Sitzung terminal markieren - behoben

Ein alter, nach Disconnect auslaufender Call-Segment-Finalizer setzte die
Datenbank bei vorhandenem neuerem Segment zwar nicht auf abgeschlossen, sendete
und journalisierte aber dennoch `completed`. Die neue Generation wird jetzt vor
dem Reconnect-Snapshot dauerhaft als Call-Segment etabliert; der neue
`connecting`-Stand ersetzt einen eventuell schon gelandeten Terminalstatus und
inkrementelles Replay liefert nur den neuesten Status. Terminale Fertigmeldung
wird ausserdem nur nach dem tatsaechlichen Commit des aktuellen Abschlusses
gesendet.

### P1 - spaete Drain-Transkripte und Resume-Stand blieben unsichtbar - behoben

Der Hintergrundpoll lud nach Abschluss keine Transkripte, Segmente oder Sprecher
neu. Resume lud nur Fragen. Beide Pfade synchronisieren jetzt den vollstaendigen
durablen Gespraechsstand, bevor beziehungsweise sobald weitergearbeitet wird.

### P0 - konkurrierende Writer konnten dieselbe Sequenz vergeben - behoben

Jeder Writer berechnete bisher unabhaengig `MAX(sequence) + 1`. Ein alter
auslaufender Socket und ein neuer Reconnect konnten deshalb denselben Wert
committen. Die Vergabe sperrt jetzt zuerst die zugehoerige Sessionzeile; alle
falliblen PII-Schritte passieren davor. Eine neue Migration resequenziert nur
betroffene Alt-Sitzungen in ihrer bisherigen Reihenfolge und erzwingt danach
`UNIQUE(session_id, sequence)`. Unversionierte Legacy-Datenbanken werden bei
Revision 028 adoptiert und fuehren 029 wirklich aus, statt an der neuen
Constraint vorbeigestempelt zu werden.

## Geaenderte Vertraege

- Keine gesprochenen Zeilen anhand globaler String-, Set-, Hash- oder
  semantischer Aehnlichkeit loeschen.
- Kurze/unklare Sprecherzuordnung beeinflusst Attribution, nicht die Existenz
  des Transkripts.
- Der Replay-Stand eines coalescierten Interim-Segments enthaelt die
  vollstaendige Hypothese; live gesendete Append-Ereignisse bleiben Deltas.
- Ein Vollsnapshot enthaelt fuer eine vorhandene korrigierte Zeile sowohl eine
  einsetzbare Basis als auch ihre neueste Korrektur.
- `completed` bedeutet, dass genau dieser Finalizer die Sitzung dauerhaft
  abgeschlossen hat.
- Hintergrundabschluss und Resume lesen den dauerhaften Transkriptstand neu.
- Resume verarbeitet bereits bestaetigte Nachrichten desselben Socket-Puffers
  nicht erneut.
- Sequenzvergabe ist pro Sitzung serialisiert und zusaetzlich durch die
  Datenbankeindeutigkeit abgesichert.

## Pruefbelege dieses Pakets

- Rot-gruen reproduziert: zwei identische spaetere menschliche Aeusserungen
  erzeugten vorher nur eine Nachricht; jetzt zwei.
- Rot-gruen reproduziert: kurze erste Aeusserung eines neuen Sprechers ergab
  vorher null Importzeilen; jetzt eine Zeile ohne erzwungene Sprecher-ID.
- 10 fokussierte Backend-Vertragschecks fuer Wiederholung, Kurzsegment,
  Append-Replay, Snapshot-Erstellung/Korrektur und veralteten Finalizer: gruen.
- 12 fokussierte Frontend-WebSocket-/Session-Checks: gruen.
- 3 fokussierte Sequenzvertragschecks: gruen; Alembic meldet genau den neuen
  Stand `029_unique_transcript_sequence` als Head, Python-Kompilierung ist gruen.
- Frontend-Produktionsbuild: gruen, 2138 Module; bekannte Warnung fuer den
  Hauptchunk groesser als 500 kB bleibt. Der erneute Build nach den finalen
  Session-/Resume-Korrekturen ist ebenfalls gruen.
- 69 fokussierte Backendchecks fuer Audiohandler, Replay und Sequenz: 68 gruen;
  ein Dateitest scheitert ausschliesslich an der bekannten Windows-Temp-ACL.
- 42 abschliessende, temp-dateifreie Backendchecks fuer Replay, Sequenz,
  Wiederholung, Kurzsegmente und geordnete Transkription: gruen. Der separate
  Socket-Generationscheck gegen verspaetetes `completed` ist ebenfalls gruen.
- Der fruehere erweiterte Lauf ueber 102 Backendtests war zunaechst wegen
  Windows-Temp-ACL und drei veralteten Retranscribe-Sprechererwartungen nicht
  insgesamt gruen. Die Dateitests liefen danach ausserhalb der Sandbox; der
  Sprechervertrag wurde vereinheitlicht und die vollstaendigen fokussierten
  Suiten sind nun 11/11 plus 17/17 gruen.
- Sentrux konnte nicht ausgefuehrt werden: weder der in `AGENTS.md` dokumentierte
  Installationspfad noch ein `sentrux`-Befehl ist in dieser Umgebung vorhanden.

## Migration und Bereinigung

Entfernt:

- `backend/app/services/transcript_dedup.py`
- zugehoerige `TRANSCRIPT_DEDUP_*`-Konfiguration
- `backend/tests/test_transcript_dedup.py`

Erhalten:

- Nutzer-, Sitzungs-, Prompt-, Provider- und Audiodaten.
- Sprecher-Ghost-Praedikat als reine Entscheidung ueber Attribution; es darf
  keine Transkriptzeile mehr verwerfen.

## Aktuelle Freigabeblocker und Restarbeit

1. **A06/A18/A21/A22: reale bzw. menschliche Abnahmen:** Deutsche
   Mikrofon-/Discord-Aufnahme mit Overlap, GUI-/DPI-Lesbarkeit, gleiche deutsche
   ASR-A/B-Referenz unter Gesamtlast sowie menschliche rhetorische
   Mehrturnbewertung sind in dieser Umgebung nicht belastbar ausführbar. Sie
   bleiben BLOCKED und werden nicht aus Tests oder Smokes abgeleitet.
2. **Sauberer Releasezustand:** Der Arbeitsbaum enthaelt umfangreiche
   vorbestehende Aenderungen und neue Dateien. Laut `docs/releasing.md` darf die
   Plattformveroeffentlichung nur von sauberem, synchronisiertem `master`
   erfolgen. Es wurde deshalb weder committed, gepusht noch veroeffentlicht.
3. **Sentrux:** Der in `AGENTS.md` dokumentierte Installationspfad ist in dieser
   Umgebung nicht vorhanden; `sentrux check/gate` ist offen.

### Manuelles Abnahme-Playbook fuer die verbleibenden Blocker

- **A06 / Audio und Diarisierung:** Auf einem Windows-Rechner mit echtem
  Mikrofon und Discord-Systemaudio eine mindestens zweiminuetige deutsche
  Zweipersonenaufnahme mit kurzen Einwuerfen, Ueberlappung, Geraetewechsel und
  absichtlichem Backlog durchführen. Danach müssen alle gesprochenen
  Passagen im Transcript vorhanden sein, `audio_gap`/`diarization_overflow`
  nur bei tatsächlich ausgelöstem Grenzfall erscheinen, und die Session muss
  sauber enden. Rohaufnahme, Hardware-/Treiberangaben und Export vergleichen.
- **A18 / Rhetorik:** Mit mindestens zehn deutschsprachigen Mehrturn-Fällen
  beide Modi ausführen. Eine menschliche Prüferin bewertet pro Antwort
  Zustimmung/Eingrenzung/Rückfrage/Nichtausgabe, Wahrheitsbindung,
  Sprechbarkeit und genau einen primären Hauptzug; jede Abweichung mit
  Session-ID, Transcript und Modellantwort protokollieren.
- **A21 / ASR-A-B:** Dieselbe unveränderte deutsche Referenzaufnahme auf
  derselben Hardware und unter identischer Gesamtlast mit beiden freigegebenen
  ASR-Pfaden verarbeiten. Wort-/Zahlen-/Negationsfehler, Latenz, Aussetzer und
  CPU/RAM getrennt messen; kein Ergebnis aus unterschiedlichen Clips oder
  nachträglicher manueller Korrektur werten.
- **A22 / Benchmark:** Einen vorab fixierten, unabhängigen Mehrturn-Datensatz
  ohne Zukunftsdaten verwenden, Produktions- und Referenzpfad unter gleicher
  Last messen und den Nenner vorab festlegen. Latenz, Fehlerquote und eine
  blinde menschliche Qualitätsbewertung getrennt ausweisen; Rohdaten und
  Commit-/Modell-/Hardwarestand archivieren.

Der PostgreSQL-Konkurrenzbeleg, dauerhafte vorlaeufige Revisionen, Retention-
Vertrag, exakte Finalzuordnung, manuelle Korrekturhistorie, gezielte
Empfehlungsentwertung, Retranscribe-Sprechervertrag, Supply-Chain-Audit und der
quellidentische lokale Windows-Kandidat sind nicht mehr offen.

## Naechster exakter Schritt

Die automatisierbaren V3-Pruefungen sind mit dem aktuellen Arbeitsbaum
abgeschlossen. Als naechster exakter Schritt bleibt die manuelle Abnahme von
A06, A18, A21 und A22 mit echter deutscher Referenzaufnahme, Hardware-/DPI-
Pruefung und menschlicher Rhetorikbewertung. Danach sind Matrix und
Freigabestatus erneut zu aktualisieren; Sentrux und ein sauberer,
  synchronisierter Release-Checkout bleiben separate Betreiber- bzw.
  Umgebungsbedingungen.

## Goal-Blocker-Audit

Die automatisierbaren Nachweise sind abgeschlossen und mehrfach wiederholt.
Die vier verbleibenden Blocker A06, A18, A21 und A22 benoetigen unverfuegbare
externe Bedingungen: echte deutsche Mikrofon-/Discord-Hardware, eine
unveraenderte Referenzaufnahme unter gleicher ASR-Last sowie menschliche
Rhetorikbewertung. Diese Bedingungen bestanden ueber mehrere aufeinanderfolgende
Goal-Fortsetzungen unveraendert. Ohne neue Hardware-/Referenzdaten oder eine
menschliche Abnahme ist kein weiterer belastbarer Fortschritt moeglich.

Status: BLOCKED (externe Abnahme erforderlich; kein technischer Fehler).

Naechste konkrete Aktion nach Bereitstellung der Bedingungen: das Playbook
fuer A06/A18/A21/A22 ausfuehren, Rohbelege archivieren und die Matrix nur bei
tatsaechlichem Ergebnis auf BESTANDEN setzen.

## Wiederaufnahme 2026-11-08: wissenschaftliche technische Vorpruefung

Die Aufgabe wurde nach dem vorherigen Goal-Blocker-Audit mit der ausdruecklichen
Anweisung fortgesetzt, trotz fehlender Hardware und menschlicher Abnahme noch
selbststaendig belastbare technische Verbesserungen zu suchen. Eine aktuelle
Primaerquellen-Recherche wurde durchgefuehrt. Die relevanten Ergebnisse sind:

- Die CHiME-7/8-DASR-Auswertung beschreibt Overlap- und Diarisierungsfehler als
  eigenstaendige Messgroessen und stuetzt deshalb getrennte technische
  Audio-/Diarisierungsnachweise statt einer einzigen ASR-Zahl:
  https://arxiv.org/html/2507.18161v2
- LongJudgeBench und WebDevJudge strukturieren offene Qualitaetsurteile in
  explizite Rubriken und vergleichen sie mit Referenzurteilen; die Arbeiten
  zeigen zugleich, dass ein automatischer Judge menschliche Bewertung nicht
  ersetzt:
  https://arxiv.org/html/2606.01629v4 und
  https://arxiv.org/html/2510.18560v3
- LLM-rubric beschreibt eine feingranulare, kalibrierte Rubrik als
  reproduzierbarere Alternative zu einem unstrukturierten Gesamturteil:
  https://doi.org/10.18653/v1/2024.acl-long.745

### Technische A22-Vorpruefung: deterministische Debattenrubrik

Um die Forschungsergebnisse in den bestehenden Produktionsbenchmark zu
ueberfuehren, wurde `backend/scripts/benchmark_debate_copilot.py` um
`evaluate_recommendation_contract()` erweitert. Der Benchmark prueft nun pro
angenommener Empfehlung reproduzierbar:

- Schema-Validitaet und einen sprechbaren primaeren Zug,
- Wortgrenzen fuer Antwort und Rueckfrage,
- vorhandene Zielbehauptung,
- Evidence-Guard gegen unbelegte Zahlen/Attributionen.

Jeder Datensatz enthaelt `quality_preflight` sowie die Summen
`technical_quality_pass_count`, `technical_quality_failure_count` und
`human_review_required_count`. Der Status ist ausdruecklich nur ein
technischer Vertragsstatus; `human_review_required` bleibt immer wahr. Die
Rubrik wird daher nicht als menschliche rhetorische Abnahme und nicht als
Aufhebung von A18/A22 verwendet.

Nachweis:

- Rot-gruen: drei neue Vertragsfaelle in
  `backend/tests/test_debate_benchmark.py` (sprechbare Antwort, unbelegte
  Zahl, fehlende primaere Rueckfrage).
- Vollstaendige fokussierte Benchmark-Suite: 18/18 gruen mit
  `..\\.release-venv\\Scripts\\python.exe -m unittest tests.test_debate_benchmark`.
- Fokussierte Agenten-/Orchestrator-/Review-/Learning-Regression: 105/105
  gruen.
- Vollstaendige Backend-Discovery ausserhalb der Sandbox: 1708 Tests, `OK`
  mit 3 erwarteten Skips in 134.771 s. Der normale Sandboxlauf bleibt wegen
  der Windows-TEMP-ACL nicht aussagekraeftig (203 Cleanup-/Dateifehler); der
  erweiterte Lauf beseitigt genau diese Umgebungsstoerung.
- `py_compile` fuer Benchmark und Test sowie `git diff --check` sind gruen;
  `git diff --check` meldet nur die bestehende LF/CRLF-Normalisierung.
- Die vorhandenen technischen Blocker A06/A18/A21/A22 bleiben unveraendert
  BLOCKED; nur die automatisierbare Vorpruefung ist erweitert.

### Dokumentationsabgleich und Folgepruefung

- `docs/debate-copilot.md` dokumentiert die neue `quality_preflight`-Struktur,
  ihre technischen Zaehler und die bewusste Pflicht zur menschlichen Pruefung.
- `docs/debate-ai-optimization-report.md` fuehrt dieselbe Abgrenzung als Teil
  des Optimierungsberichts; kein automatischer Judge wird als Rhetorikabnahme
  ausgegeben.
- Erneute fokussierte Regression nach dem Dokumentationsabgleich: 93/93 Tests
  gruen (`test_debate_benchmark`, `test_debate_copilot`, `test_debate_review`,
  `test_debate_learning`), Python-Kompilierung und `git diff --check` gruen.

### Evidenz-Vorpruefung fuer A06/A18/A21/A22

Die spaetere manuelle Abnahme wird jetzt durch
`backend/scripts/validate_v3_acceptance_evidence.py` gegen unvollstaendige
oder widerspruechliche Metadaten geschuetzt. Die reine Python-Funktion
`validate_evidence_package()` und die CLI pruefen:

- A06: deutsche Referenz von mindestens 120 Sekunden, Mikrofon/Systemaudio,
  Overlap, Geraetewechsel, absichtlicher Backlog, Transcript-Vollstaendigkeit
  und sauberen Terminalzustand;
- A18: beide Debattenmodi, mindestens zehn Mehrturn-Faelle und anonymisierte
  menschliche Ratings;
- A21: genau zwei ASR-Laeufe mit identischem Referenz-SHA, Hardware- und
  Lastprofil, ohne manuelle Korrektur, inklusive Wort-/Zahlen-/Negations-
  fehlern, Latenz, Aussetzern und CPU-Spitzenwert;
- A22: gehashter unabhaengiger Datensatz, Ausschluss von Zukunftsdaten,
  vorab fixierter positiver Nenner, gleiche Last fuer Produktions-/Referenz-
  pfad und getrennte Human-Ratings.

Das Ergebnis ist immer entweder `incomplete` oder
`ready_for_manual_review`; `human_review_required` bleibt immer wahr. Damit
werden keine externen Bedingungen simuliert und kein Blocker hochgestuft.

Nachweis: `backend/tests/test_v3_acceptance_evidence.py` 4/4 gruen; die
kombinierte fokussierte Suite mit Evidenz-, Benchmark-, Copilot-, Review- und
Learningtests ist 97/97 gruen. Die CLI verweigert das vorhandene reine
Debattenfixture erwartungsgemaess mit `incomplete` und Exit-Code 2. Python-
Kompilierung und `git diff --check` bleiben gruen.

### Naechste konkrete Aktion

Bei Bereitstellung eines echten Evidenzpakets zuerst die neue Vollstaendigkeits-
pruefung ausfuehren, danach nur die fehlenden manuellen A06/A18/A21/A22-
Schritte abarbeiten und Rohbelege unveraendert archivieren. Bis dahin keine
weitere Architekturveraenderung ohne reproduzierbaren Befund.

### A06: No-drop-Backlog und Dokumentationsabgleich

Der vorhandene technische Schutzpfad wurde erneut gegen den aktuellen Code
geprueft. `backend/app/ws/audio_runtime.py` verwirft bei Ueberschreitung des
30-Sekunden-/Bytebudgets keinen bereits angenommenen Frame; der neue Frame wird
vor der Zaehlung abgelehnt, der Aufruf kontrolliert beendet und die akzeptierte
Warteschlange vollstaendig ausgedraint. `backend/app/ws/audio_messages.py`
meldet dabei `diarization_overflow` mit `frames_dropped: 0`. Die zuvor veraltete
Beschreibung in `docs/audio-pipeline.md` wurde auf diesen Vertrag berichtigt.

Nachweis:

- `tests.test_diarization_backlog`: 6/6 gruen.
- Die kombinierten Worker-/Shutdown-/Overflow-/Native-Buffer-Tests plus
  Backlogtests: 28/28 gruen.
- Der breitere Audio-Handler-Lauf bleibt wegen eines bekannten Windows-TEMP-
  ACL-Fehlers in einem nicht relevanten `TemporaryDirectory`-Cleanup-Test
  unvollstaendig; der isolierte technische Overflow-Satz ist davon nicht
  betroffen.

Damit ist der technische A06-No-drop-Vertrag BESTANDEN; reale deutsche
Mikrofon-/Discord-Aufnahme, echte Overlap-Erkennung und Hardwarewechsel bleiben
als externe A06-Abnahme BLOCKED. Eine synthetische Abnahme wird daraus nicht
abgeleitet.

Naechste konkrete Aktion: Bei Bereitstellung der realen Aufnahme das
Evidenzpaket mit `validate_v3_acceptance_evidence.py` pruefen; bis dahin keine
weitere A06-Architekturveraenderung ohne neuen reproduzierbaren Befund.

### A06: Kapazitaetsplaner an den No-drop-Vertrag angeglichen

Bei einem Abgleich aller Overload-Texte wurde eine echte Inkonsistenz im
Admission-Planer gefunden: `backend/app/services/capacity_planner.py` empfahl
noch "Shed oldest diarization audio", obwohl der aktive Audio-Pfad akzeptierte
PCM-Frames niemals entfernen darf. Die Empfehlung wurde auf
"Stop before accepting new diarization audio" geaendert. Damit beschreibt auch
der Kapazitaetsplan nur noch den sichtbaren Annahmestopp vor dem Queue-Ueberlauf;
der geschuetzte Batch-Transkriptpfad bleibt unangetastet.

Nachweis: zunaechst bewusst roter Test nach Umstellung der Erwartungen (2
Fehlschlaege), danach minimale Codeaenderung und `tests.test_capacity_planner`
mit 16/16 gruen. Historische Design-Spezifikationen behalten ihre damalige
Entscheidungsdokumentation; sie sind keine aktive Laufzeitbeschreibung.

Naechste konkrete Aktion: keine weitere A06-Aenderung ohne neuen reproduzierbaren
Befund; bei realen Hardware-/Referenzdaten das Evidenzpaket ausfuehren.

### A06: Replay-Warnpfad auf den aktuellen Statusnamen gebracht

Der aktive Replay-Client `backend/scripts/replay_call.py` erkannte zunaechst
nur den historischen Status `diarization_overloaded`. Der aktuelle WebSocket-
Vertrag sendet `diarization_overflow`; dadurch waere ein realer Backlog-Stopp
beim Offline-Replay nicht als Warnung sichtbar gewesen. Ein kleiner
Red-Green-Test in `backend/tests/test_replay_call.py` erzwingt nun die
Warnmeldung fuer den aktuellen Status, waehrend der alte Name aus
Rueckwaertskompatibilitaet weiter akzeptiert wird.

Nachweis: der neue Test fiel vor der Aenderung erwartungsgemaess fehl und ist
danach zusammen mit Kapazitaets-, Backlog- und Audio-Overflowtests mit 27/27
gruen gelaufen.

Naechste konkrete Aktion: aktive Statusnamen weiter nur gegen den WebSocket-
Vertrag pruefen; keine weitere A06-Architekturveraenderung ohne neuen Befund.

### A06: Aktivitaetsanzeige und Protokolldoku semantisch synchronisiert

Die letzte aktive Altlast lag in den sichtbaren Gesundheitsdaten: WebSocket-
Dokumentation, Agenten-Dokumentation und UI bezeichneten `shed` als
"uebersprungen" bzw. "shed audio", obwohl der aktuelle Vertrag einen Frame vor
der Annahme zurueckweist und akzeptierte PCM-Daten nie entfernt. Der Wire-Key
`shed` bleibt fuer alte Clients erhalten, wird aber als abgewiesener Framezaehler
dokumentiert; die deutsche Anzeige sagt jetzt "abgewiesen". Die Hinweise auf
einen sichtbaren Overload-Stopp sind damit fuer Operatoren nachvollziehbar.

Nachweis: Der Frontend-Red-Test fuer die Anzeige schlug vor der UI-Aenderung
fehl und lief danach mit 20/20 Tests gruen (erweiterte Ausfuehrung wegen
Sandbox-EPERM fuer esbuild). Die aktualisierten Dokumente sind ohne
`git diff --check`-Inhaltsfehler.

Naechste konkrete Aktion: keine weitere A06-Aenderung ohne neuen
reproduzierbaren Befund; reale deutsche Aufnahme und Hardwareabnahme bleiben
im Evidenz-Playbook BLOCKED.

Die Health-Dokumentation wurde anschliessend noch auf die tatsaechliche
Rueckwaertskompatibilitaet geschaerft: Der Wire-Key `shed` bleibt ein alter
Zaehler und wird nicht als Beweis eines PCM-Verlusts interpretiert; der aktuelle
`diarization_overflow`-Status liefert `rejected_bytes` separat. So wird weder
ein nicht vorhandener Health-Zaehler behauptet noch der sichtbare Stop verharmlost.

### A07: Reconnect-Epochen im WebSocket-Vertrag dokumentiert

Der implementierte A07-Fix war im Code und in den Tests vollstaendig, aber die
oeffentliche Protokolldokumentation erklaerte die entscheidenden Felder noch
nicht. `docs/websocket-protocol.md` beschreibt jetzt `after_sequence`,
`after_epoch`, die stabile `capture_id` sowie `session_snapshot` mit
`server_epoch`, `through_sequence`, `full` und geordneten Ereignissen. Ein
veralteter Serverepoch-Cursor wird ausdruecklich als Full-Snapshot behandelt;
der Client setzt Cursor und Historie vor der Anwendung zurueck.

Nachweis: reine Vertragsdokumentation, ohne Laufzeitveraenderung; die bereits
vorhandenen Backend- und Frontend-Epochtests bleiben die ausfuehrbare Quelle
des Nachweises. `git diff --check` bleibt ohne Inhaltsfehler.

Naechste konkrete Aktion: keine A07-Implementierung wiederholen; nur bei einem
neuen Protokollbefund gezielt nachbessern.

Gemeinsame Nachpruefung der neuen A06-/A07-Randpfade: Replay-Warnung,
Kapazitaetsplaner, Backlog-/Worker-/Shutdown-/Overflow-, Native-Buffer- und
WebSocket-Journaltests liefen zusammen mit 62/62 gruen. Die Abnahmematrix
bleibt unveraendert bei 20 BESTANDEN und den vier externen BLOCKED-Punkten.

### Aktueller technischer Zwischenstand

Die selbststaendig pruefbaren Nacharbeiten dieses Wiederaufnahmeabschnitts
sind abgeschlossen: A06-No-drop, Kapazitaetsplan, Replay-Warnung,
Aktivitaetsanzeige und A07-Reconnect-Dokumentation sind synchronisiert und
regressionsgeprueft. Es wurden keine Daten geloescht, kein fremder Arbeitsstand
zurueckgesetzt und keine manuelle Abnahme simuliert.

Letzter Sammelnachweis: Backend 62/62 fuer die betroffenen A06/A07-Pfade,
Frontend 19/19 fuer Reconnect/Epochen und 20/20 fuer die Aktivitaetsanzeige;
`git diff --check` ohne Inhaltsfehler. Die vier externen Bedingungen bleiben
unveraendert BLOCKED: reale deutsche Mikrofon-/Discord-Aufnahme und Overlap
(A06), menschliche deutsche Rhetorik (A18), gleiche Referenz-/Hardware-ASR-
Kampagne (A21) und unabhaengiger kausaler Produktionsbenchmark mit Human-Gate
(A22).

Naechste konkrete Aktion: sobald ein echtes Evidenzpaket vorliegt,
`backend/scripts/validate_v3_acceptance_evidence.py` ausfuehren und nur danach
die jeweils noch fehlenden manuellen Abnahmeschritte protokollieren.

### Evidenz-Gate: wissenschaftliche Mindestkonsistenz verschaerft

Die erste Evidenzvorpruefung kontrollierte vor allem das Vorhandensein von
Feldern. Ein Audit zeigte, dass damit z. B. eine String-Dauer, unendliche oder
negative ASR-Metriken, nicht anonymisierte Rater-Namen, unverblindete Ratings
oder weniger Ratings als A18-Faelle durchrutschen konnten. Das widerspricht der
geforderten Messdisziplin, auch wenn der Status danach weiterhin niemals
`passed` wird.

Die CLI prueft nun zusaetzlich:

- endliche positive Referenzdauer und endliche nichtnegative A21-Metriken;
- exakt benannte A21-Laeufe (`asr_a`, `asr_b`);
- anonymisierte Rater-IDs, explizite Verblindung, eindeutige Fall-IDs und fuer
  A18 mindestens eine Bewertung je Fall;
- A22-Fehlerquoten im Intervall 0..1.

Nachweis: Drei neue Red-Faelle schlugen vor der Implementierung fehl; danach
`tests.test_v3_acceptance_evidence` 7/7 und die kombinierte Evidenz-/Benchmark-
/Copilot-/Review-/Learning-Suite 100/100 gruen. `py_compile` und
`git diff --check` sind gruen. Die Statuswerte bleiben konservativ
`incomplete` oder `ready_for_manual_review`, immer mit
`human_review_required: true`.

Naechste konkrete Aktion: den verschaerften Validator beim Eintreffen realer
Evidenzpakete ausfuehren; bis dahin bleiben A06/A18/A21/A22 BLOCKED.

### CLI-Grenzpruefung des Evidenz-Gates

Das vorhandene reine Debattenfixture wurde erneut absichtlich als falscher
Evidenztyp an die CLI uebergeben. Die Ausgabe blieb konservativ
`status: incomplete`, `human_review_required: true`, und der Prozess endete
mit Exit-Code 2. Zusammen mit den 7/7 Validator-Unit-Tests ist damit sowohl
die Funktions- als auch die CLI-Grenze belegt; ein unpassendes Paket kann nicht
als manuell bereit markiert werden.

Naechste konkrete Aktion: bei echter Hardware-/Human-Evidenz denselben CLI-
Aufruf auf das unveraenderte Rohpaket anwenden und nur `ready_for_manual_review`
als Eingang in die manuelle Abnahme verwenden.

### P2.6 - Reproduzierbare Modell-Downloads und Supply-Chain-Gate

Ein frischer P2/P3-Audit zeigte eine konkrete technische Luecke: Der
ONNX-Downloader verwendete mutable `master`/`main`-Pfade und akzeptierte
vorhandene oder neu geladene Bytes ohne Integritaetspruefung. Das ist fuer
Strict-local-Wartung und Auslieferung kein belastbarer Nachweis.

Behoben: `backend/scripts/download_models.py` fuehrt jetzt fuer alle Runtime-
und optionalen Modelle eine gepruefte Spec mit upstream Revision, SHA-256,
Groesse und Lizenz. URLs sind auf die nachgewiesenen Commit-Revisionen
fixiert. Bestehende Dateien werden vor dem Ueberspringen gehasht; neue
Downloads landen zunaechst in einer `.download`-Datei, werden geprueft und
erst danach atomar installiert. Hashfehler brechen hart ab und koennen keinen
Cloud-Fallback ausloesen. Die lesbare Inventarquelle ist
`docs/model-manifest.json`; `docs/audio-pipeline.md` verlinkt sie.

Nachweis: Red-Green mit drei neuen Tests in
`backend/tests/test_download_models_script.py`; anschliessend die fokussierte
Strict-local-/Adapter-Suite inklusive Downloader `106/106` gruen, der reale
Downloader-Lauf verifizierte beide vorhandenen Runtime-Modelle, und
`py_compile` war gruen. Die Quellen-/Lizenzangaben wurden gegen die
offiziellen Silero- und WeSpeaker/Hugging-Face-Seiten abgeglichen.

Statusmatrix bleibt 20/24 BESTANDEN, 0 offen, 4 BLOCKED (A06, A18, A21,
A22). P2.1/P2.6 sind technisch fuer die abgedeckten Pfade nachgebessert;
gemeinsam genutzte externe Dienste wurden nicht global umkonfiguriert.

Naechste konkrete Aktion: weitere P2/P3-Pfade nur bei einem reproduzierbaren
Vertragsbruch aendern; ansonsten Gesamtregression und anschliessend die
manuellen A06/A18/A21/A22-Abnahmen mit echten Evidenzpaketen vorbereiten.

### Gesamtregression nach P2.6

Der vollstaendige Backend-Testbestand wurde nach der Downloader-Aenderung
ausserhalb der Windows-TEMP-ACL-Sandbox ausgefuehrt: `1719` Tests, `OK`,
`3` bewusst uebersprungen. Der Frontend-Produktionsbuild lief nach einer
isolierten Sandbox-EPERM-Wiederholung ebenfalls gruen: Vite transformierte
`2139` Module. Die einzige Buildwarnung betrifft die bereits bekannte grosse
Hauptbundle-Groesse, nicht einen Fehler.

Nachweis: `backend: python -m unittest discover -s tests -q` mit Exit-Code 0;
`frontend: npm run build` mit Exit-Code 0. Der erste Frontend-Lauf in der
Sandbox scheiterte reproduzierbar an `spawn EPERM` und wurde nicht als
Produktfehler gewertet. Es wurden keine Daten- oder Fremdarbeitsbaum-
Aenderungen bereinigt.

Naechste konkrete Aktion: Statusmatrix und Blockerhinweise gegen die drei
V3-Quellen frisch abgleichen; keine weitere technische Aenderung ohne neuen
reproduzierbaren Befund.

### P2-C - Reproduzierbares Dependency-/Native-Inventar

Der Matrixabgleich zeigte, dass der Versionsaudit bisher nur implizit in
`requirements.txt` und Einzeltests steckte. `backend/scripts/audit_dependencies.py`
liest jetzt die direkten Anforderungen, erkennt Extras/Marker, ermittelt die
installierte Version und Package-Lizenz, markiert bekannte native Komponenten
und schreibt ein deterministisches JSON-Artefakt. Die begleitende
`docs/dependency-audit-v3.md` hält fest, dass dies kein pauschales Upgrade und
kein erfundener Security-Scan ist; Python 3.12/audioop bleibt bewusst der
getestete Ausgangspfad.

Nachweis: `tests.test_dependency_audit` und die Downloader-/Integritaetssuite
zusammen `5/5` gruen; beide Audit-/Downloader-Skripte kompilieren; der
verifizierende Modell-Downloader bestaetigte beide vorhandenen Runtime-
Gewichte. Das Artefakt ist `docs/dependency-audit-v3.json`.

P2-C wechselt damit von `OFFEN` auf `IMPLEMENTIERT`. Offen bleiben nur die
ausdruecklich benannten Releaseentscheidungen (separater Advisory-Review und
eine moegliche Python-3.13-Portierung), fuer die kein pauschales Upgrade
belegt oder autorisiert ist.

Der Audit wurde anschliessend um maschinenlesbare Zweck-, Plattform-,
`security_status: not_scanned`- und `deprecation_status: manual_review`-
Felder ergaenzt. Damit sind die Grenzen des Nachweises sichtbar und es wird
keine Sicherheitspruefung behauptet, die nicht ausgefuehrt wurde.

### Frontend-Gesamtregression und Abschlussaudit des technischen Anteils

Die vollstaendige Frontend-Testliste lief nach dem P2-C-Paket mit `268/268`
Tests gruen. Damit sind neben dem Produktionsbuild mit 2139 transformierten
Modulen auch die sichtbaren Reconnect-, Capture-, Privacy-, Research-,
Recommendation-, Review- und Update-Vertraege aktuell ausgefuehrt.

Der anschliessende Quellenabgleich bestaetigt: selbststaendig bearbeitbare
technische Punkte sind in der Matrix belegt. Verbleibend sind ausschliesslich
die bereits benannten echten externen Gates: deutsche Mikrofon-/Discord-
Referenzaufnahme und Overlap, menschliche deutsche Rhetorikbewertung, gleiche
ASR-Referenz-/Hardwarekampagne, kausaler Human-Benchmark sowie reale GUI/DPI-,
Rollback- und Bestandsinstallationsabnahmen. Diese werden nicht simuliert.

Naechste konkrete Aktion: bei Eintreffen eines Evidenzpakets den konservativen
Validator ausfuehren; bis dahin den technischen Stand nicht als vollstaendig
manuell abgenommen ausgeben.

### Atomare Coverage-Matrix und Regression

Der erneute Quellenabgleich fand eine Dokumentationsluecke: Die bisherige
Zusatzmatrix deckte P0-A bis P3-G ab, fuehrte aber die verbindlichen
Unteranforderungen P0.1-P3.7 nicht jeweils als eigene Zeile. Diese Zeilen sind
jetzt mit Kurzanforderung, Artefakt/Nachweis, Restluecke und Status einzeln in
dieser Datei erfasst. Die vier A-/N-Punkte bleiben unveraendert und werden
nicht durch die groessere Tabelle doppelt als bestanden behauptet.

Dafuer wurde `backend/tests/test_v3_matrix_coverage.py` hinzugefuegt. Der Test
stellt sicher, dass A01-A24, N1-N4 sowie alle P0.1-P3.7-IDs vorhanden sind und
jede Zeile einen zulassigen Status und Evidenzspalte fuehrt.

Nachweis: kombinierte Matrix-/Dependency-/Downloader-/Evidenz-Suite `14/14`
gruen; `git diff --check` bleibt ohne Inhaltsfehler. Externe Hardware-,
Referenz-, Human- und Bestandsinstallations-Gates sind in den atomaren Zeilen
weiterhin als `BLOCKED` markiert und nicht kuenstlich hochgestuft.

Naechste konkrete Aktion: nur bei einem neuen Quellen- oder Laufzeitbefund
weitere Matrix-/Codeaenderungen vornehmen; ansonsten auf echte
Evidenzpakete fuer die markierten Gates warten.

### P3.3/P0.1 - Asset-, Eigentums- und Rollback-Inventar

Fuer den noch offenen Cleanup-/Environment-Vertrag wurde ein lesendes,
maschinenlesbares Inventar unter `docs/v3-asset-inventory.json` angelegt.
Es trennt benoetigte Runtime-Artefakte, generierte Release-Staging-Dateien,
Rollback-Kandidaten und ungeklaerte ACL-geschuetzte Testpfade. Fuer die
vorhandenen grossen Runtime-/Release-Dateien sind SHA-256, Groesse,
Verantwortungsbereich, Zweck und Rueckweg dokumentiert. Der Eintrag fuer
fruehere `.previous`-Pakete bleibt bis zur Release-Owner-Bestaetigung
erhalten; die unbekannten `backend/tmp*`-Pfade wurden nicht angefasst.

Es wurde bewusst nichts geloescht, ueberschrieben, umbenannt oder gemerged.
Damit ist der technische Inventarteil reproduzierbar, ohne aus fehlenden
Referenzen eine unzulaessige Eigentums- oder Loeschannahme abzuleiten.

Nachweis: `backend/tests/test_v3_asset_manifest.py` und die Coverage-Matrix
zusammen `4/4` gruen. `git diff --check` bleibt ohne Inhaltsfehler. Ein
echter installierter EXE-/Hardware-Snapshot sowie die externe Bestaetigung
des Rollback-Aufbewahrungsfensters bleiben P0.1/P3.3/P3.5-Gates und werden
nicht simuliert.

Status: P3.3 bleibt `BLOCKED` (Inventar implementiert; physische Bereinigung
und Eigentums-/Rollbackabnahme extern offen); P0.1 bleibt `BLOCKED` fuer
reale Bestands-/Hardwareabnahme.

Naechste konkrete Aktion: die verbleibenden technisch geschlossenen
V3-Anforderungen gegen einen letzten fokussierten Regressionstest spiegeln;
danach nur noch echte Evidenzpakete fuer A06/A18/A21/A22 und die
Bestandsinstallations-/Rollback-Gates verarbeiten.

### Fokussierte V3-Abschlussregression

Die fokussierte technische Suite fuer Asset-Manifest, atomare Matrix,
Evidenzvalidator, Dependency-Audit, gepinnten Modelldownloader und
Modell-Downloadvertraege lief ausserhalb der Windows-TEMP-ACL-Sandbox mit
`37/37` Tests gruen. Der identische Lauf innerhalb der Sandbox reproduzierte
die bekannte Berechtigungsstoerung beim Erzeugen/Aufraeumen von
`TemporaryDirectory`; der Produktcode war dabei nicht abweichend.

Nachweis: `python -m unittest tests.test_v3_asset_manifest
tests.test_v3_matrix_coverage tests.test_v3_acceptance_evidence
tests.test_dependency_audit tests.test_download_models_script
tests.test_model_downloads` mit Exit-Code 0 ausserhalb der Sandbox.

Statusmatrix bleibt 20/24 BESTANDEN, 0 offen, 4 BLOCKED. Die technischen
Selbsttests sind damit abgeschlossen; offen sind nur echte deutsche
Audio-/Discord-/ASR-Kampagnen, menschliche Rhetorik-/Qualitaetsbewertung,
unabhaengige Produktionsreferenz sowie reale GUI-/DPI-, Installations- und
Rollbackabnahmen.

Naechste konkrete Aktion: keine weitere technische Aenderung ohne neuen
reproduzierbaren Vertragsbruch; bei einem echten Evidenzpaket den Validator
ausfuehren und die jeweilige BLOCKED-Zeile erst dann neu bewerten.

### Wiederaufnahme 2026-11-09 - aktueller Regression- und Evidenzabgleich

Der aktuelle Arbeitsbaum enthaelt neben dem technischen Quellstand bereits
vorhandene reale Audioartefakte: `artifacts/real-smoke/german-asr.wav`
(6,575 s) sowie die drei Ausschnitte unter `backend/.tmp/asr-real/`
(55 s, 18 s und 24 s). Sie wurden nicht veraendert und als
`evidence-candidate` in `docs/v3-asset-inventory.json` mit SHA-256 und Zweck
vermerkt. Sie sind wertvolle Vorbelege fuer deutsches ASR, erfuellen aber
allein weder die A06-Mindestdauer-/Szenarien noch die A21-Anforderung von zwei
identischen Laeufen unter gleicher Gesamtlast. Keine Anforderung wurde daraus
kuenstlich hochgestuft.

Die aktuelle aufgeteilte Backend-Kernregression lief ausserhalb der
Windows-TEMP-ACL-Sandbox mit `789` Tests, `OK`, `2` bewussten Skips in
`87,476 s`. Ein unaufgeteilter Discovery-Lauf wurde nach 124 s ohne
Abschlussmeldung beendet; er wird deshalb nicht als Gesamtgruen gewertet.
Die aktuelle Frontend-Suite lief ausserhalb der Sandbox mit `268/268` Tests
gruen. Der Produktionsbuild transformierte `2139` Module erfolgreich; die
bekannte Warnung zum 602-kB-Hauptchunk bleibt nicht-blockierend. Der
Sandboxlauf scheiterte ausschliesslich an `spawn EPERM`.

Fuer die praktische Restabnahme wurde
`docs/v3-manual-acceptance-runbook.md` hinzugefuegt. Es beschreibt den
kuerzesten reproduzierbaren Ablauf fuer A06, A18, A21, A22 und die
Bestands-/Rollbackpruefung sowie die unveraenderte Nutzung des konservativen
Evidence-Validators. Der Validator kann nur `incomplete` oder
`ready_for_manual_review` liefern; `BESTANDEN` bleibt an die echte
Hardware-/Humanpruefung gebunden.

Nachweis: Manifest-/Matrix-/Evidenzsuite `12/12` gruen; Backend-Kernpaket
`789/789` gruen; Frontend `268/268` gruen; Build gruen. Statusmatrix bleibt
`20/24 BESTANDEN`, `0 offen`, `4 BLOCKED` (A06, A18, A21, A22). P0.1/P3.3/P3.5
bleiben wegen realer Bestands-, Eigentums- und Rollbackabnahme BLOCKED.

Naechste konkrete Aktion: auf einer echten Windows-Abnahmemaschine den
Runbook-Ablauf ausfuehren, die Rohbelege unveraendert archivieren und erst nach
Validator plus menschlicher Prüfung die jeweilige Matrixzeile aktualisieren.

### Schneller ASR-Entscheidungsbeleg aus vorhandenen WAVs

Auf ausdruecklichen Wunsch wurden die vier bereits vorhandenen WAV-Dateien
direkt mit den lokal vorhandenen Modellen `local-whisper-base` und
`local-parakeet-tdt-0.6b-v3` verarbeitet. Es wurde keine neue Aufnahme,
kein Netzwerk und kein kostenpflichtiger Provider verwendet.

Ergebnis:

- Im 55-Sekunden-Clip liefert Whisper einen zusammenhaengenden deutschen
  Satz mit dem Schluesselwort `Abtreibung`; Parakeet kollabiert zu `Up
  tremble.`.
- Im 18-Sekunden-Fenster erkennt Whisper `Abtreibung`; Parakeet macht daraus
  `Abschlagen`.
- Im 24-Sekunden-Fenster sind beide fehlerhaft, Whisper bleibt aber naeher
  am deutschen Inhalt.
- Nur beim 6,575-Sekunden-Kontrollsatz formuliert Parakeet
  `erneuerbarer` grammatisch besser als Whisper `erneuerbare`.

Die Entscheidung fuer den produktiven deutschen Finalpfad lautet deshalb
`local-whisper-base`. Parakeet v3 kann als schnelle vorlaeufige Live-Spur
beibehalten werden, aber nicht als finaler deutscher Transcriber. Laufzeiten,
RTF, SHA-256 und alle Rohtexte sind in
`docs/evidence/asr-local-wav-decision-2026-11-09.json` gespeichert.

Dieser Nachweis ist ein klarer technischer Modellentscheid, aber bewusst kein
vollstaendiger A21-Pass: Es fehlt ein unabhaengiger Wortreferenztext, eine
120-Sekunden-Referenz und die gleiche vollstaendige Gesamtlast in zwei Laeufen.
Die Matrix bleibt daher bei A21 `BLOCKED`, waehrend die Modellwahl fuer die
Umsetzung entschieden ist.

Nachweis: vier WAVs x zwei lokale Modelle, acht erfolgreiche Transkriptionen;
Manifestpruefung `4/4` gruen.

### V6-Hard-Gate: eingefrorene Ausgangsbasis (2026-11-09)

Der V6-Auftrag wurde im realen Checkout gelesen und als ausfuehrbarer
Abschlussauftrag uebernommen. Ausgangsfingerprint: Git-HEAD
`da2c5301f272142ae5d7bbb2ab10a7b5402ae20c`; der Arbeitsbaum hatte 389
Statuszeilen und enthielt bereits umfangreiche fremde/laufende Aenderungen.
Es wurde nichts zurueckgesetzt, bereinigt, geloescht oder gestasht. Die
vorhandenen ACL-geschuetzten Test-/Temporaerpfade bleiben unangetastet.

Toolchain-Baseline: Host-Python `3.14.7`, Node `v24.21.0`, npm `12.1.0`;
PyInstaller ist im Host-Python nicht installiert. Der bestehende Buildvertrag
verlangt Python 3.12 und die vorhandene `.release-venv`, bevor ein Windows-
x64-onedir-Build ueberhaupt gestartet werden darf. Historische EXEs gelten
nicht als aktueller Buildnachweis.

V6-Freigaberegeln: erst interne Sitzungen 1 und 2, Integration, danach Sitzung
3 mit Cleanup-/Rueckrollmanifest, dann Root-Review und ein ausdruecklicher
`BUILD_READY`-Eintrag. Vorher kein finaler EXE-Build. Die festen Entscheidungen
bleiben: `local-whisper-base` ist der deutsche Finalpfad; Parakeet v3 bleibt
optional interim; A06/A18/A21/A22 sowie reale Installations-/Hardware- und
Rollbackabnahmen werden nicht simuliert.

Bekannte Stopkriterien: kritischer Audio-/Transkriptverlust, aktive Promptquelle
unter `_internal`/`sys._MEIPASS`, ungesicherte Nutzerdatei-Ueberschreibung,
stiller Cloudfallback bei fehlenden lokalen Ressourcen, fehlende Python-3.12-
Buildumgebung oder ein Cleanup ohne Eigentums-/Referenz-/Rollbacknachweis.

Naechster konkreter Schritt: interne Sitzung 1 (releasekritische Restfehler)
auf dem eingefrorenen Stand; Sitzung 2 und der EXE-Build bleiben bis dahin
gesperrt.

### V6 interne Prüfsitzung 1 — Release-Sicherheit (2026-11-09)

Die erste interne Fachsitzung wurde auf den unveraenderten Baseline-Stand
begrenzt. Geprueft wurden Audio-/Transkriptverlust und kontrolliertes
Fehlerverhalten (`test_audio_handler`, Audio-/Transkript-/Ordered-Pipelines,
Ghost-Transkripte), Privacy-/Strict-local- und Secret-Schutz, Update-Service
sowie Desktop-Start/Stop, eingebettetes PostgreSQL, Pfadauflösung und Update-
Akzeptanz.

Nachweis: Backend-Subset `242` Tests gruen (`OK`, `2` erwartete Skips,
25.739 s); Desktop-Subset `94` Tests gruen (`OK`, `1` erwarteter Skip,
9.932 s). Die protokollierten Fehlermeldungen stammen aus absichtlich
simulierten Fehlerpfaden der Tests (Provider down, DB down, Diarizer failure,
unklarer Endpoint) und sind keine Testfehler. Der Host-Python-3.14-Lauf wurde
wegen fehlender Projektabhaengigkeiten nicht als Nachweis verwendet; der
vorhandene Python-3.12-Release-Interpreter wurde genutzt.

Entscheidung Agent 1: kein neuer releasekritischer Defekt mit belastbarem
Reproduktionsbeleg gefunden; keine Codeaenderung und kein Architekturwechsel.
Der Whisper-Finalpfad bleibt unveraendert. Sitzung 1 ist damit bestanden;
die externen A06/A18/A21/A22- und Hardwareabnahmen bleiben unveraendert
BLOCKED und werden nicht umetikettiert.

Naechster konkreter Schritt: interne Sitzung 2 implementiert die noch zu
haertende V6-Semantik fuer externe Konfigurations-/Promptpfade in der
gefrorenen Runtime und prueft einen einzigen kurzen Wirksamkeitsnachweis.

### V6 interne Prüfsitzung 2 — externe Konfiguration/Prompts (2026-11-09)

Die bestehende `ai`-Quelle wurde nicht ersetzt, sondern an der konkreten
Frozen-Runtime-Grenze gehaertet. `backend/app/services/ai_config.py` nutzt im
expliziten Portable-Modus `sys.executable` fuer `ai` neben der gestarteten EXE;
`sys._MEIPASS` bleibt ausschliesslich Defaultquelle. Explizite externe Pfade
werden gegen Bundlepfade und vorhandene Symlink-Traversierung abgesichert.
Installierte Builds behalten den bestehenden beschreibbaren Userpfad
`%LOCALAPPDATA%\\Backchannel\\ai`; Nutzerdateien werden bei Updates nicht
ueberschrieben.

Ungueltige Promptdateien werden validiert und erhalten den sicheren Fallback,
ohne die fehlerhafte Nutzerdatei beim Start zu ueberschreiben. Die AI-
Konfigurationsantwort weist nun effektiven Providerpfad,
content-basierte `configuration_generation` und vollstaendigen Prompt-Hash
neben Version, Quelle und Pfad aus. Reload bleibt deterministisch: jeder
Promptzugriff liest die externe Datei erneut, waehrend laufende Snapshots
konsistent bleiben.

Nachweis: `tests.test_ai_config`, `tests.test_prompt_resources` und
`tests.test_prompt_system_instruction`: `30/30` Tests gruen. Die Tests pruefen
Portable-Pfad ausserhalb `_internal`, Ablehnung eines `_MEIPASS`-Overrides,
ungestoerte Nutzerreihenfolge, Versionswechsel, Traversal-Schutz und
invaliden Prompt-Fallback ohne Ueberschreiben.

Geaenderte Dateien: `backend/app/services/ai_config.py`,
`backend/app/services/agents/prompt_resources.py`,
`backend/app/routers/ai_config.py`, die beiden genannten Testdateien und
`ai/README.md`. Sitzung 2 ist bestanden.

Naechster konkreter Schritt: Sitzung 3 prueft den gesamten aktuellen Ordner
auf eindeutig tote app-eigene Artefakte. Ohne Eigentums-, statische,
dynamische, Packaging-, Migrations- und Rollbackbelege wird nichts geloescht;
unklare und gemeinsam genutzte Pfade bleiben erhalten.

### V6 interne Prüfsitzung 3 — Cleanup und Rueckrollmanifest (2026-11-09)

Der echte Projektordner wurde gegen aktuelle Imports, Packaging-Spec,
Migrationspfade, Fallbacks, Tests und die bereits dirty vorhandenen Dateien
geprueft. Die drei vorgefundenen Loeschungen
(`backend/app/services/transcript_dedup.py`, der zugehoerige Test und
`frontend/public/favicon.svg`) waren bereits vor V6 im Arbeitsbaum und wurden
nicht angefasst. Fuer jede Datei stehen HEAD-SHA/Größe, Referenzstatus,
Ersatzpfad und Rueckrollbefehl im
`docs/v6-cleanup-manifest.json`.

Es gab keinen neuen eindeutig app-eigenen, unreferenzierten und zugleich
rollback-sicheren Kandidaten. Daher wurde bewusst nichts physisch geloescht:
unklare Dateien, Nutzer-/Promptdaten, Migrationen, Lizenzen, Modelle,
gemeinsame Caches und fremde Aenderungen bleiben erhalten. Das ist ein
positiver Cleanup-Befund, keine fehlende Ausfuehrung.

Nachweis: Manifest-JSON parsebar; gezielte statische Referenzsuche ohne
aktive Treffer fuer die drei Baseline-Loeschungen; Python-3.12-V3-/Manifest-/
Dependency-/Downloader-Suite `39/39` gruen. Sitzung 3 ist bestanden, mit
`BEIBEHALTEN/OFFEN` fuer die drei vorbestehenden Loeschungen.

Naechster konkreter Schritt: Integration abschliessen, Root-Review und die
gezielte Prompt-/Start-/Packaging-Pruefung ausfuehren; erst danach darf
`BUILD_READY` gesetzt und die Windows-EXE gebaut werden.

### V6 Root-Review und BUILD_READY (2026-11-09)

Der Integrationsstand ist konfliktfrei geprueft. Die drei internen Sitzungen
sind abgeschlossen; die einzigen V6-Codeaenderungen betreffen die externe
AI-Konfigurationsquelle, deren sichere Fallbacksemantik und deren Diagnose-
Metadaten. `git diff --check` meldet keine Inhaltsfehler (nur erwartete
Windows-LF/CRLF-Hinweise). Die vorhandene Python-3.12-Releaseumgebung meldet
`PyInstaller 6.22.3`; alle fuer den bestehenden Spec benoetigten Modelle,
PostgreSQL-Binaries, ffmpeg, CLIProxyAPI-DLL und Frontend-dist sind vorhanden.
Der Frontend-Produktionsbuild ist mit 2.139 Modulen und Exit-Code 0 gruen.

Gezielte technische Nachweise: releasekritische Backend-Regression `242/242`
gruen, Desktop-Start/Stop/Update `94/94` gruen, externe Prompt-/Config-
Regression `30/30` gruen, V3-/Manifest-/Dependency-Suite `39/39` gruen.
Die Promptquelle ist ausserhalb `_internal`/`sys._MEIPASS` wirksam,
`sys.executable`-Portablepfad und `_MEIPASS`-Schutz sind getestet, und
`docs/v6-cleanup-manifest.json` dokumentiert den konservativen Cleanup.

`BUILD_READY` = **freigegeben** am `2026-11-09T03:59:56.9284618Z`.
Arbeitsbaum-Fingerprint: `c17882b765571c2e27ab2d9c06b3eb7594e57ed73a421bdae03ffe4b401214ca`;
Git-HEAD bleibt `da2c5301f272142ae5d7bbb2ab10a7b5402ae20c`. Relevante Quell-
und Asset-SHA-256 stehen im Build-Gate-Manifest
`docs/v6-build-gate.json`. Der Build darf nur in einem neuen Stagingordner
ausgefuehrt werden; vorhandene `dist/`-/Rollbackstaende bleiben recoverable.

Ehrliche Restgrenzen: A06/A18/A21/A22, echte Hardware-/DPI-Abnahme,
installierte EXE-Abnahme und externe Rollback-/Eigentumsbestaetigung bleiben
`BLOCKED_EXTERNAL`; sie blockieren den lokalen Kandidaten nicht. GitHub-
Veröffentlichung ist erst nach realem EXE-Smoke und Privacy-/Repository-
Sichtbarkeitspruefung zulaessig.

Naechster konkreter Schritt: die bestehende Python-3.12-PyInstaller-Toolchain
auf dem freigegebenen Stagingpfad ausfuehren und danach den minimalen
Windows-EXE-/externen-Prompt-Smokecheck dokumentieren.

### V6 Gate-Nachschärfung — ungültige Providerdatei (2026-11-09)

Der erste EXE-Smoke gegen `build/v6-release-stage-20261109` zeigte einen
echten, aber erst nach dem Build eingefuehrten Restfehler: Der Kandidat
enthielt noch die alte `load_ai_json`-Fallbacklogik und meldete eine
absichtlich kaputte `providers.json` mit HTTP 200 und leerer Konfiguration.
Das war kein bestandener Nachweis und wird nicht schoengerechnet.

Korrektur in `backend/app/services/ai_config.py`: Die Providerdatei wird fuer
den wirksamen Pfad direkt als JSON gelesen; ungueltiges JSON fuehrt nun zu
einem sicheren, sichtbaren Fehler, waehrend ein bereits validierter
In-Process-Stand weiterhin als last-known-good erhalten bleibt. Ein neuer
Red-Test prueft, dass kaputtes Provider-JSON nicht still als leere Liste gilt.
Die betroffene Regression steht mit `26/26` Tests gruen.

Der vorherige `BUILD_READY`-Eintrag ist damit fuer die alte EXE aufgehoben.
Der naechste freizugebende Gate-Fingerprint und der neue Buildpfad werden erst
nach erneuter gezielter Gate-Pruefung und einem Neubau eingetragen.

Aktueller Status: `IN_PROGRESS`; die alte EXE bleibt nur als nicht
freigegebene Diagnose, nicht als Releasekandidat. Naechster konkreter Schritt:
neuer Python-3.12-onedir-Build aus dem korrigierten Quellstand, dann derselbe
Hash-/Prompt-/Invalid-Config-Smoke.

### V6 korrigierter Build, Archiv-Smoke und lokales BUILD_READY (2026-11-09)

Der korrigierte Quellstand wurde in einem neuen Stagingordner mit Python
`3.12.10`, PyInstaller `6.22.3` und dem bestehenden Windows-x64-onedir-Spec
gebaut. Der alte Kandidat bleibt verworfen; verwendet wird ausschliesslich
`build/v6-release-stage-20261109b/Backchannel/Backchannel.exe` mit
`26.895.770` Bytes und SHA-256
`b56a60a1a1e529398ebab0f60128e00ad09982990d9843777a02cc14f9888fc9`.

Nachweis: Der normale EXE-Smoke meldet Health auf Port 8474, nutzbare lokale
ASR-Runtime und sauberes Herunterfahren. Der externe Prompt-/Config-Smoke
belegt, dass die externe Promptdatei ausserhalb `_internal` wirksam ist und
deren Hash nach Bearbeitung wechselt; absichtlich ungueltiges
`providers.json` ergibt HTTP 500; der EXE-Hash bleibt unveraendert. Die
gezielten Regressionen stehen nach der Korrektur mit `26/26` Tests gruen.

Das portable Paket liegt unter
`build/v6-release-output-20261109/Backchannel-windows-x64.zip`, enthaelt
`Backchannel/` als sicheren Archivroot, `4.084` Eintraege, `340.229.282`
Bytes und SHA-256
`a7aff2c633ac5e7c6996b8f05cf76ea9a917a65dfe8a51f00308c647ded98e8a`.
`desktop/scripts/smoke_update_archive.py` bestaetigt den nativen Windows-
Update- und erzwungenen Rollbackpfad mit `OK`.

Der lokale Gate-Status ist damit wieder `BUILD_READY`. Der aktuelle
Arbeitsbaum-Fingerprint ist
`afcd45972fc713db360e5d7f5cbc4271eac4829f6dea494b001e3636cbbc248a`;
Details und Checksums stehen in `docs/v6-build-gate.json` und im
Releaseausgabeordner. Die Buildartefakte sind nachweislich aus dem korrigierten
Quellstand erzeugt; kein alter Kandidat darf veroeffentlicht werden.

Verbleibende externe Blocker bleiben unveraendert: A06/A18/A21/A22 sowie reale
Hardware-/DPI-/Installations-/Rollbackabnahmen. Vor einer Veroeffentlichung
ist zusaetzlich die private GitHub-Sichtbarkeit und die authentifizierte
Schreibberechtigung zu pruefen; ohne diese Belege erfolgt kein Upload.

Naechster konkreter Schritt: Paket auf Secrets/Private-Daten scannen,
GitHub-Remote und private Berechtigung read-only verifizieren und nur bei
positivem Nachweis ein privates Release mit ZIP, Manifest und Checksums
erzeugen; andernfalls den externen Blocker mit reproduzierbarem Befund
dokumentieren.

## RESUME POINT

Status: `DONE` fuer alle technisch erreichbaren V6-Zielbedingungen; privates
GitHub Release veroeffentlicht. Externe manuelle Abnahmen bleiben separat
`BLOCKED_EXTERNAL`.

Abschlussnachweis: privates Repository und Release read-only verifizieren;
Asset-Hashes gegen lokale Dateien vergleichen. Keine Git-Resets, kein Clean,
kein Sammel-Commit fremder dirty Aenderungen. Fuer die spaetere manuelle
Abnahme nur A06/A18/A21/A22 und echte Hardware-/DPI-/Installations-/Rollback-
Nachweise bearbeiten.

### V6 Release-Gate: lokaler Privacy-Scan bestanden, GitHub-Pruefung extern blockiert (2026-11-09)

Der abschliessende lokale Paket-Scan ist bestanden: `1.652` lesbare
Textdateien im ZIP wurden gegen API-Key-, Token- und Private-Key-Muster
geprueft; es gab `0` Treffer. `ai/providers.json` ist bytegleich mit
`ai/providers.default.json` (SHA-256
`18b48afe70c5bdd6bac55c88775aa2277488d7885f6fa945c73ba55160ab1804`), und
es gibt keine `ai/history*`-Dateien. Das Paket enthaelt damit keinen
erkennbaren persoenlichen Providerzustand oder Geheimnisnachweis.

Read-only lokal nachgewiesen: Remote ist
`https://github.com/talberthoule/backchannel.git`; `gh` ist installiert
(`2.101.0`) und der lokale Account ist authentifiziert. Die anschliessende
verbindliche Abfrage von `nameWithOwner`, `isPrivate` und URL wurde jedoch
wegen des ausgeschoepften externen Kontingents von der Ausfuehrungsumgebung
abgewiesen. Damit sind Repository-Privatsichtbarkeit und effektive
Release-Schreibberechtigung nicht nachgewiesen. Es wurde deshalb kein Push,
kein Tag und kein GitHub-Upload ausgefuehrt.

Status dieses Gates: `BLOCKED_EXTERNAL` (nicht als technischer Produktfehler
gewertet). Lokale Artefakte bleiben gueltig und liegen unter
`build/v6-release-output-20261109/`: ZIP SHA-256
`a7aff2c633ac5e7c6996b8f05cf76ea9a917a65dfe8a51f00308c647ded98e8a`,
Manifest SHA-256
`454a38a73b51e0a7e0a1b61d0bcf2945a6ce2b00564957a96af8e2d0ca88fd4c` und
EXE SHA-256
`b56a60a1a1e529398ebab0f60128e00ad09982990d9843777a02cc14f9888fc9`.

Fortsetzung nach Kontingentfreigabe: `gh repo view talberthoule/backchannel
--json nameWithOwner,isPrivate,url,defaultBranchRef` ausfuehren. Nur bei
`isPrivate=true` und nachgewiesener Schreibberechtigung ein Release mit
genau `Backchannel-windows-x64.zip`, `release-manifest.json` und
`SHA256SUMS.txt` erzeugen; danach Release-URL, Tag und Checksums hier
ergaenzen. Bei `isPrivate=false` oder fehlender Berechtigung keinen Upload
versuchen und den Blocker beibehalten.

Nachtrag: Die gezielte Desktop-Manifest-/Release-Contract-Suite wurde in
einem isolierten Repository-Tempordner mit den benoetigten Windows-Rechten
erneut ausgefuehrt: `30/30` Tests gruen. Die vorherigen WinError-5-Laeufe im
geschuetzten System-TEMP sind damit als Umgebungsbesonderheit und nicht als
Produktfehler eingeordnet.

### V6 GitHub-Sichtbarkeit abschliessend verifiziert (2026-11-09)

Die read-only GitHub-Abfrage konnte nach Kontingentfreigabe erfolgreich
ausgefuehrt werden. Verbindlicher Befund:
`talberthoule/backchannel`, Default-Branch `master`, URL
`https://github.com/talberthoule/backchannel`, `isPrivate=false`.

Damit ist das Zielkriterium fuer ein **privates** GitHub-Release nicht
erfuellt. Es wurde folgerichtig kein Tag, kein Push und kein Release-Upload
ausgefuehrt. Eine Umstellung der Repository-Sichtbarkeit oder die Anlage
eines neuen privaten Repositories waere eine externe, nicht automatisch zu
unterstellende Eigentums-/Freigabeentscheidung und wurde nicht vorgenommen.

Status: `BLOCKED_EXTERNAL` fuer den GitHub-Release-Schritt. Die technische
V6-Umsetzung und das lokale BUILD_READY bleiben gueltig; die lokalen Artefakte
und ihre Checksums sind unveraendert. Fuer eine spaetere Veroeffentlichung muss
der Eigentuemerkreis entweder dieses Repository nachweislich privat schalten
oder einen privaten Remote mit bestaetigter Schreibberechtigung bereitstellen;
danach ist die Sichtbarkeit erneut read-only zu pruefen, bevor exakt die drei
geprueften Releaseartefakte hochgeladen werden.

### V6 privates GitHub Release erfolgreich veroeffentlicht (2026-11-09)

Da der bestehende Upstream `talberthoule/backchannel` oeffentlich ist, wurde
gemaess dem autorisierten Auftrag ein separates privates Repository angelegt:
`https://github.com/ErpeUser/backchannel-v6-private`. Read-only verifiziert:
`isPrivate=true`, Default-Branch `master`. Der Release-Metadatenstand wurde
als Commit `bd433f8` gepusht; persoenliche, fremde und ungepruefte
Arbeitsbaumdateien wurden nicht in dieses Repository kopiert.

Das echte GitHub Release `v0.6.6` ist nicht Draft und nicht Prerelease:
`https://github.com/ErpeUser/backchannel-v6-private/releases/tag/v0.6.6`.
Hochgeladen und serverseitig als `uploaded` bestaetigt wurden:

- `Backchannel-windows-x64.zip`, 340.229.282 Bytes,
  SHA-256 `a7aff2c633ac5e7c6996b8f05cf76ea9a917a65dfe8a51f00308c647ded98e8a`;
- `release-manifest.json`, SHA-256
  `454a38a73b51e0a7e0a1b61d0bcf2945a6ce2b00564957a96af8e2d0ca88fd4c`;
- `SHA256SUMS.txt`, SHA-256
  `62085e170a8789b43793aad008362941dfc4a5eb3b69c98083e5c05ed6310de1`;
- `START_HIER.md`, SHA-256
  `0376541f0b116ed2125242f3c7ad64db15da504766513bce7db44df016c69eb4`.

Die drei kleinen Assets wurden anschliessend aus GitHub heruntergeladen und
bytegenau gegen die lokalen Dateien verglichen. Die GitHub-API meldet fuer
das ZIP denselben SHA-256 wie der lokale Build. Damit ist die technische
Release- und Private-Repository-Bedingung erfuellt.

Weiterhin nicht automatisch erfuellt und ehrlich dokumentiert bleiben A06,
A18, A21, A22 sowie reale Hardware-/DPI-/Installations-/Rollbackabnahmen.

### Nachlauf: vollstaendiger bereinigter Quellcode im privaten Repository (2026-11-09)

Auf ausdruecklichen Wunsch wurde der Source-Code zusaetzlich in das private
Release-Repository geladen. Der Snapshot liegt unter `source/` im privaten
Remote `https://github.com/ErpeUser/backchannel-v6-private` und umfasst `1.004`
versionierte Dateien mit `18.965.329` Bytes. Enthalten sind Backend,
Desktop, Frontend, docs-site, Tests, Skripte, AI-Prompts, Konfiguration und
Dokumentation.

Nicht uebernommen wurden Git-Metadaten, virtuelle Umgebungen, node_modules,
Build-/Dist-/`.astro`-/`dist-site`-Ausgaben, Modelle, native Runtime-Binaries,
Audio, Datenbanken, Session-/Tempdaten und `.env`-Dateien. Die generierte
Kopie `docs-site/src/content/docs/` wurde nicht hochgeladen, weil sie gemaess
Projektregeln aus `source/docs/` erzeugt wird. `SOURCE_SNAPSHOT_MANIFEST.json`
listet jede tatsaechlich versionierte Datei mit Groesse und SHA-256.

Der Secretscan meldete nur die fuenf absichtlich synthetischen Test-Fixtures
aus den Redaction-/Credential-Tests; kein Live-Token und kein privater Schluessel
wurde gefunden. Remote-Nachweis: Master-Commit `6f0be66`, `1.004` Source-Blobs,
`0` verbotene Pfade (`.env`, `node_modules`, `build`, `dist`, `.git`),
Repository weiterhin `isPrivate=true`.

Die Korrektur des Snapshot-Manifests wurde als eigener Commit ausgefuehrt,
damit das Inventar keine lokal vorhandenen, aber von `.gitignore` verworfenen
generierten Dateien behauptet. Der bestehende Release-Tag und die vier
Releaseartefakte bleiben unveraendert; der vollstaendige Code liegt auf dem
privaten `master`-Branch.

### Privacy-Nachlauf: Login-/Verlaufsdaten ausgeschlossen (2026-11-09)

Der private Source-Snapshot wurde gezielt auf lokale GPT-/Gemini-/Google-
Anmeldedaten und Nutzungsverlaeufe geprueft. In der aktuellen Baumstruktur
und in allen erreichbaren Git-History-Objekten wurden keine Cookies,
Browserprofile, `Login Data`, OAuth-/Access-/Refresh-Token-Dateien,
Provider-/Account-Overrides, lokale Storage-State-Dateien, Chat-/Conversation-
Verlaeufe, Transkripte, Datenbanken oder Logs gefunden. Die einzige `.env`
Datei ist die neutrale `.env.example`; `ai/providers.json` ist bytegleich mit
`ai/providers.default.json` und enthaelt keine persoenlichen Endpunkte oder
Geheimnisse. Die Quellcode-Handler fuer Login/Cookies bleiben als Code
enthalten, die per-Maschine-Zustaende jedoch nicht.

Der Nachweis wurde in `build/v6-github-private-repo/PRIVACY_AUDIT.md`,
`SOURCE_PROVENANCE.md` und `SOURCE_SNAPSHOT_MANIFEST.json` festgehalten. Der
aktuelle Snapshot umfasst `1.004` Dateien und `18.966.942` Bytes; der
Secretscan enthaelt weiterhin nur fuenf absichtlich synthetische Test-Fixtures.
Naechster Schritt: den aktualisierten privaten Snapshot pushen und Remote-
Baum sowie Historie erneut auf verbotene lokale Datenpfade pruefen.

### Deep-Audit-Nachlauf: Egress, Reihenfolge, Prompts und deutsche Oberflaeche (2026-11-09)

Umgesetzt:

- `backend/app/services/agents/orchestrator.py`: Vor dem Retrieval des
  Vorbereitungsdossiers wird die konfigurierte Route technisch gegen die
  lokale-Ziel-Pruefung abgesichert. Cloud-/Web-Routen erhalten keinen lokalen
  Dossiertext; bei unklarer Pruefung wird aus Sicherheitsgruenden nichts
  uebertragen. Das reine Lesen fuehrt keinen Commit mehr aus.
- `backend/app/services/ordered_transcription.py`: Langsame Transcript-Emits
  halten den Annahme-Lock nicht mehr. Die Reihenfolge bleibt erhalten, spaetere
  Ergebnisse koennen jedoch angenommen werden.
- `backend/app/services/agents/event_bus.py`: Ereignisse, die waehrend eines
  Cooldown-Handlers eintreffen, werden nach dessen Ende erneut eingeplant und
  gehen nicht durch Starvation verloren.
- `backend/app/services/ai_config.py`: Prompt-Platzhalter werden gegen eine
  explizite Allowlist geprueft; unbekannte Namen werden abgewiesen.
- `backend/app/services/agents/orchestrator.py`: Unicode-Worttokenisierung
  fuer deutsche Zahlwoerter ist ohne fehleranfaellige Encoding-Klassen
  abgesichert.
- Sichtbare Frontend-Texte in den Hinweisen, Filtern, Nachbearbeitung,
  Sprecher-/Audio-Dialogen, Chat-Verlauf und Typbezeichnungen sind deutsch;
  `frontend/index.html` verwendet `lang="de"`. Die Produktbezeichnung ist
  sichtbar `Debate AI`; technische Kompatibilitaetsnamen bleiben unveraendert.
- Veraltete Frontend-Erwartungen wurden auf den verbindlichen deutschen
  Vertrag aktualisiert; es wurden keine Tests abgeschwaecht.

Nachweise:

- Backend: `tests.test_debate_copilot` und
  `tests.test_dossier_hybrid_integration`: 73 Tests bestanden.
- Backend: Ordered-Transcript plus EventBus: 14 Tests bestanden.
- Backend: Unicode-/Prompt-Fokus: 3 Tests bestanden; alle 38 direkt
  ausgelieferten Root-Prompts wurden zusaetzlich mit der neuen Validierung
  eingelesen.
- Frontend: `npm run build`: 2.139 Module erfolgreich gebaut.
- Frontend: `npm test`: 268 Tests bestanden.
- Die sechs temporaeren Prompt-Ressourcentests bleiben in dieser Windows-
  Umgebung blockiert, weil `tempfile.TemporaryDirectory` unter dem vorhandenen
  System-TEMP mit `PermissionError/WinError 5` endet. Das ist ein
  Umgebungsblocker, kein bestandener Test.

Status: Diese Pakete sind IMPLEMENTIERT/BESTANDEN. Noch offen bleiben die
weiteren Audit-Punkte zu Audio-Backpressure, Analyse-Cancellation/Retry,
Mehrprozess-Betrieb, Deployment/Auth, mobilem Layout, grossen Kontexten und
manuellen Hardware-/Audio-/Rhetorikabnahmen.

Naechster konkreter Schritt: die Server-/Browser-Audio-Backpressure anhand
von F1-F3 pruefen und zuerst einen reproduzierbaren Verlusttest ausfuehren.

### Deep-Audit-Nachlauf: Audio-Backpressure F1-F3 (2026-11-09)

Umgesetzt:

- `frontend/src/hooks/useWebSocket.ts`: Browser-`bufferedAmount` wird mit
  High-/Low-Water-Hysterese begrenzt. Bei Ueberlast wird nur der aktuelle
  Interimframe verworfen; `chunksDropped` bleibt im sichtbaren Audio-Status.
- `backend/app/ws/audio_pipeline.py`: Diarization verwendet neben dem
  Bytebudget nun eine echte begrenzte Queue (`MAX_DIARIZATION_QUEUE_FRAMES`).
  Eine volle Queue lehnt den neuen Frame ab, ohne bereits akzeptiertes PCM zu
  entfernen, und meldet den kontrollierten Overflow.
- `backend/app/ws/audio_messages.py` und `audio_pipeline.py`: Der Live-
  Gatewayversand laeuft ueber eine eigene kleine Queue und einen Sender-Task.
  Der WebSocket-Ingress wartet nicht mehr auf Provider-I/O. Bei Gateway-
  Ueberlast wird ein `audio_gateway_overflow`-Status gemeldet; die dauerhafte
  Batch-Spur bleibt unabhaengig.

Nachweise:

- Backend Audio-Handler/Backlog: 67 ausgefuehrte Tests bestanden; ein
  zusaetzlicher Test bestaetigt Queue-Ueberlast ohne PCM-Drop. Ein separates
  Sammelkommando enthielt ausserdem einen nicht vorhandenen Testmodulnamen und
  einen Windows-TEMP-ACL-Fehler; beide sind Umgebungs-/Aufrufprobleme, keine
  Codefehler.
- Frontend: `npm test` ohne Fehler; der neue Hook-Test prueft die Hysterese.
  Der Produktionsbuild wird nach dem Backend-Paket erneut ausgefuehrt.

Status: F1-F3 IMPLEMENTIERT; technisch fokussiert BESTANDEN. Reale
Mikrofon-/Discord- und Hardware-Lastabnahmen bleiben manuell.

Naechster konkreter Schritt: F6-F7 pruefen — Live-Analyse-Retries und stale
Revision-Cancellation mit Red-Tests gegen unnoetige Zweitaufrufe absichern.

### Deep-Audit-Nachlauf: Live-Retry und stale Revisionen F6-F7 (2026-11-09)

Umgesetzt:

- `backend/app/services/agents/objection_handler.py`: Eine syntaktisch
  gueltige, semantisch leere Empfehlung wird lokal als `no_guidance`
  behandelt. Sie verursacht keinen zweiten Live-Provideraufruf und verwirft
  dabei keine gleichzeitig gelieferten Einwaende. Ein unvollstaendiger
  Pflichtvertrag, etwa eine fehlende erzwungene Analogie, darf weiterhin genau
  einmal korrigiert werden.
- `backend/app/services/agents/orchestrator.py`: Trifft neuere Sprache ein,
  wird die laufende Debattenrevision aktiv abgebrochen und eine neue Revision
  fuer den aktuellsten Stand gestartet. Die bestehenden Revisions-/Snapshot-
  Pruefungen bleiben als Schutz fuer Provider erhalten, die Abbruch ignorieren.
- `backend/tests/test_debate_copilot.py`: Tests pruefen keinen Retry bei
  echter Leere sowie Cancellation und Ausfuehrung der neuesten Revision;
  Negations-/Stale-Tests wurden auf den neuen Vertrag angepasst.

Nachweise:

- `backend\\.venv\\Scripts\\python.exe -m unittest tests.test_debate_copilot tests.test_objection_handler -v`
  -> 93 Tests bestanden.
- Fokussierte Cancellation-/Negationspruefung -> 2 Tests bestanden.

Status: F6-F7 IMPLEMENTIERT und BESTANDEN. Noch offen bleiben die breite
Englisch-/Legacy-Branding-Restpruefung, Gesamtregression, privater Snapshot-
Push sowie nicht technisch ausfuehrbare Hardware-/Audio-/Rhetorikabnahmen.

Naechster konkreter Schritt: sichtbare Frontend-/Dokumenttexte und verbliebene
`Backchannel`-Produktbezeichnungen systematisch inventarisieren und sichere
deutsche Debate-AI-Ersetzungen umsetzen.

### CHAT-HANDOFF: belastbarer Zwischenstand fuer die naechste Sitzung (2026-11-09)

Zweck dieses Abschnitts: Der naechste Chat darf den verlorenen Verlauf nicht
voraussetzen. Der Repository-Zustand und diese Datei sind die massgebliche
Uebergabequelle.

#### Bereits umgesetzt und nachgewiesen

1. Datenschutz-/Dossier-Egress: Cloud- oder Web-Routen erhalten keinen lokalen
   Vorbereitungsdossiertext; unklare Zielpruefung faellt geschlossen aus.
2. Transcript-Reihenfolge: langsame Emits blockieren die Annahme nicht; die
   Ausgabereihenfolge bleibt stabil.
3. EventBus: Ereignisse waehrend eines Cooldowns werden danach erneut geplant.
4. Prompt-/Unicode-Vertrag: unbekannte Platzhalter werden abgewiesen;
   deutsche Unicode-Zahlwoerter sind abgesichert.
5. Audio-Backpressure F1-F3: begrenzte Queues, kein stilles Entfernen bereits
   angenommener PCM-Frames, sichtbare Overflow-Zustaende sowie Browser-
   High-/Low-Water-Hysterese.
6. Live-Analyse F6-F7: semantisch leere, schema-gueltige Antworten loesen
   keinen unnoetigen Retry aus; eine neuere Revision bricht eine alte aktive
   Revision ab und startet den aktuellen Stand.
7. Sichtbare UI: zentrale Frontend-Bereiche sind deutsch, `lang="de"`, und die
   sichtbare Produktbezeichnung lautet `Debate AI`. Technische Legacy-Namen
   (API-Header, Storage-Schluessel, Modul-/Paketpfade) wurden absichtlich nicht
   blind umbenannt, um Kompatibilitaet nicht zu brechen.
8. Private-Snapshot-Pruefung: keine Cookies, Browserprofile, Login-Daten,
   OAuth-/Refresh-Tokens, Provider-Overrides, lokale Chatverlaeufe,
   Transkripte, Datenbanken oder Logs im Snapshot; nur neutrale
   `.env.example` und synthetische Test-Fixtures.

#### Verifizierte Nachweise

- Backend fokussiert: `tests.test_debate_copilot` plus
  `tests.test_dossier_hybrid_integration`: 73 bestanden.
- Ordered-Transcript/EventBus: 14 bestanden.
- F6-F7: `tests.test_debate_copilot` plus `tests.test_objection_handler`:
  93 bestanden.
- Frontend vor dem letzten Mini-Lokalisierungspatch: `npm test` 269/269
  bestanden; `npm run build` 2.139 Module, Build erfolgreich.
- Der Build zeigt nur die bekannte Chunk-Groessen-Warnung, keinen Fehler.
- Sechs Prompt-Ressourcentests bleiben unter Windows wegen
  `TemporaryDirectory`/System-TEMP-ACL (`PermissionError/WinError 5`)
  blockiert; dies ist kein gruener Nachweis.

#### Direkt vor der Fortsetzung noch zu verifizieren

Der letzte Arbeitsabschnitt hat zusaetzlich sichtbare Begriffe in
`TranscriptReview.tsx`, `DesktopUpdate.tsx` und `LocalModelFitCard.tsx`
eingedeutscht. Diese drei kleinen Aenderungen muessen im naechsten Chat mit
`cd frontend; npm test` und `npm run build` erneut verifiziert werden.

#### Noch offen / nicht kuenstlich als bestanden markieren

- komplette Restinventur sichtbarer englischer Texte und sichtbarer
  `Backchannel`-Markenstellen (technische Kompatibilitaetsnamen ausnehmen und
  jede Ausnahme begruenden);
- aktualisierten privaten Snapshot sicher pushen und den Remote-Baum sowie
  die erreichbare Historie erneut auf verbotene lokale Daten pruefen;
- Gesamtregression Backend/Desktop/Docs und ggf. Sentrux-Pruefung;
- Mehrprozess-/Deployment-/Auth- und grosse-Kontext-Auditpunkte aus dem
  Masterauftrag;
- manuelle Abnahmen: echte deutsche Mikrofon-/Discord-Aufnahme, echte
  Audioqualitaet/Referenzaudio, GUI-/DPI-Verhalten auf Hardware sowie
  menschliche rhetorische Qualitaetsbewertung. Diese bleiben `BLOCKED`, bis
  sie mit realen Eingaben ausgefuehrt wurden.

#### Exakte Fortsetzungsanweisung

1. `git status --short` und nur die letzten Aenderungen pruefen; nichts
   zuruecksetzen oder bereinigen.
2. Die drei kleinen Frontend-Lokalisierungen testen/builden.
3. Mit gezielten Suchmustern sichtbare englische JSX-Texte und
   `Backchannel`-Produkttexte inventarisieren; Kommentare, interne IDs,
   Header, Storage-Keys und Dateipfade nicht als sichtbare Marke zaehlen.
4. Nur echte sichtbare Treffer minimal auf Deutsch bzw. `Debate AI` aendern,
   zu jedem Paket Tests ausfuehren und diese Datei erneut aktualisieren.
5. Danach die fokussierte Backend-Suite, Frontend-Suite und Builds ausfuehren,
   Snapshot/Remote-Pruefung nachholen und erst dann den Gesamtstatus melden.

Aktueller Status: automatisierbare Pakete weitgehend IMPLEMENTIERT/BESTANDEN;
Gesamtziel noch NICHT abgeschlossen. Der Goal-Loop bleibt aktiv. Eine
Abschlussmeldung darf nur lauten: `Automatisierbare V3-Umsetzung abgeschlossen
-- verbleibende manuelle Abnahmen und Blocker dokumentiert`, wenn alle
technisch selbststaendig pruefbaren Punkte belegt sind.

### Deep-Audit-Abgleich: Resttexte, Matrix und aktueller Nachweis (2026-11-09)

Der V3-Auftrag wurde erneut gegen die drei lokalen V3-Dateien, die
Abnahmematrix A01-A24, die P0-P3-Zusatzmatrix sowie den Implementierungsplan
abgeglichen. Es wurde kein A-/N-/P0-/P1-/P2-/P3-Punkt aus der Matrix entfernt
oder stillschweigend uebersprungen. Die verbindlichen A-Punkte sind weiterhin:

- `BESTANDEN`: A01-A05, A07-A17, A19-A20, A23-A24 (20 Punkte).
- `BLOCKED`: A06 (echte deutsche Mikrofon-/Discord-/Overlapaufnahme), A18
  (menschliche deutsche Rhetorikabnahme), A21 (gleiche aktuelle deutsche
  Referenz auf identischer Hardware und Gesamtlast), A22 (unabhaengiger
  kausaler Mehrturnbenchmark mit Human-Gate).
- `NOT_RUN`/`OFFEN`: keine A01-A24-Zeile; die vier externen Punkte sind
  bewusst `BLOCKED` und nicht kuenstlich zu `BESTANDEN` hochgestuft.

Zusaetzlich bleiben die in der Matrix getrennt ausgewiesenen externen bzw.
realen Grenzen P0.1, P0.9, P1.5, P2.9 und P3.3-P3.5 offen/blockiert. Die
technischen Anteile dieser Punkte sind geprueft; reale Installation,
Hardware, Eigentum/Rollback und Human-Rating wurden nicht simuliert.

#### In diesem Nachlauf tatsaechlich geaendert

- Weitere sichtbare Frontend-Englischreste wurden auf Deutsch umgestellt:
  Update-Neuigkeiten, erneute Transkription, strategische Signalhistorie,
  Live-Transkript-Aria-Labels, Verwerfen-Schaltflaeche, Download-/Leistungs-
  test-Fehlertexte sowie lokale Modellhinweise.
- Sichtbare Produkt-/UI-Bezeichnungen bleiben `Debate AI`. Die noch
  gefundenen `Backchannel`-Vorkommen wurden klassifiziert: API-Header,
  Umgebungsvariablen, Local-Storage-Schluessel, Installations-/EXE-/Archiv-
  namen, Datenbankrollen und historische externe Domains sind technische
  Kompatibilitaetsidentitaeten. Sie wurden nicht kosmetisch umbenannt, weil
  das ohne Migration Datenverlust oder kaputte Updates verursachen wuerde.
- Die drei lokalen V3-Dateien wurden vorhanden und vollstaendig lesbar
  bestaetigt; der auf dem Desktop referenzierte V6-Auftrag ist in dieser
  Umgebung nicht vorhanden und wurde nicht erfunden.

#### Aktueller Nachweis dieses Nachlaufs

- Frontend `npm test`: **269/269 bestanden**.
- Frontend `npm run build`: **2.139 Module**, Build erfolgreich; nur die
  bekannte Chunk-Groessen-Warnung.
- Backend-Fokus mit Root-`.venv`: Branding, Copilot und Objection-Handler
  **95 Tests bestanden**.
- Ein erneuter Backend-Gesamtlauf wurde nach 122 Sekunden von der lokalen
  Zeitgrenze beendet und ist deshalb **kein** aktueller Vollsuite-Nachweis.
  Der letzte belastbare Gesamt-Nachweis in der Matrix bleibt 1.719/1.719;
  betroffene fokussierte Suiten wurden in diesem Nachlauf erneut gruen
  ausgefuehrt.
- Das Evidenz-Gate `validate_v3_acceptance_evidence.py` wurde ohne Paket nur
  mit dem erwarteten CLI-Fehler beendet; es existiert aktuell kein
  manuelles A06/A18/A21/A22-Evidenzpaket. Daher bleiben diese Punkte BLOCKED.

#### Noch nicht abgeschlossen, aber explizit identifiziert

1. Historische Release-Notes in `backend/app/release_notes.py` und die
   separate englische Marketing-/Docs-Site enthalten weiterhin englische
   historische Inhalte und alte Markennamen. Diese sind nicht technische
   Kompatibilitaetskeys, wurden in diesem Nachlauf noch nicht vollstaendig
   uebersetzt und bleiben als separater Content-Arbeitspunkt offen.
2. Der aktualisierte private Snapshot muss nach den letzten UI-Aenderungen
   erneut erzeugt, auf Geheimnisse/Verlaeufe geprueft und sicher gepusht
   werden; ein Push wurde in diesem Nachlauf nicht behauptet.
3. Ein vollstaendiger aktueller Backend-/Desktop-/Docs-Lauf steht wegen der
   lokalen Zeitgrenze noch aus; fokussierte Nachweise sind vorhanden.

Naechster konkreter Schritt: zuerst den sichtbaren historischen Content
(`release_notes.py` sowie die aktuellen, nicht URL-/Dateinamenbezogenen
Produkttexte) in einem eigenen Paket uebersetzen und mit einem gezielten
Branding-/Content-Test absichern; danach Snapshot und die passenden Suites
erneut synchronisieren.

### Deep-Audit-Nachlauf: Desktop-Fehler bei fehlender Providerdiagnose (2026-11-09)

Befund: Der Desktop-Loginpfad fuer ChatGPT Web behandelte einen
`subprocess.run`-Fehler mit einem Test-Doppel ohne String-`stdout`/`stderr` nicht
robust. Die Diagnosezeile konnte dadurch selbst mit `TypeError: argument of
type 'Mock' is not iterable` scheitern, statt den Providerfehler sauber als
Fehlerstatus zu speichern.

Korrektur: `desktop/bcdesktop/chatgpt_web_login.py` akzeptiert fuer die
Fehlerdiagnose nur echte Stringausgaben und faellt sonst auf eine leere
Diagnose zurueck. Der urspruengliche Exit-Code und der fail-closed Marker-
Vertrag bleiben unveraendert; kein Provider wird bei einem Fehlschlag
aktiviert.

Nachweis:

- Desktop mit korrektem `PYTHONPATH` (Repository, `desktop`, `backend`):
  **193 Tests bestanden, 1 plattformbedingt uebersprungen**.
- Backend `tests.test_meta`, `tests.test_debate_branding`,
  `tests.test_debate_copilot`, `tests.test_objection_handler`: **101 Tests
  bestanden**.
- Docs-Sammelsuite: **206/206 bestanden**.
- Frontend bleibt **269/269** und Build **2.139 Module** gruen.

Status: Desktop-Befund IMPLEMENTIERT und BESTANDEN. Der zuvor gestartete
Backend-Gesamtlauf mit Standardzeitlimit bleibt als `TIMEOUT` dokumentiert;
er wird nicht als Vollsuite-Erfolg ausgegeben. Die Abnahmematrix wurde auf die
aktuellen Frontend/Desktop/Docs-Zahlen aktualisiert.

Naechster konkreter Schritt: die noch offene historische Release-/Marketing-
Contentfrage bewusst entscheiden bzw. als separaten Contentblocker
verifizieren; danach den privaten Snapshot gegen diesen aktuellen Quellstand
neu synchronisieren, ohne lokale Login-/Cookie-/Verlaufsdaten zu uebernehmen.

### Deep-Audit-Kreuztabelle F1-F26: kein Befund stillschweigend uebersprungen (2026-11-09)

Der statische Deep-Audit-Anhang fuehrt neben der V3-Abnahmematrix 26 eigene
Optimierungsbefunde. Diese sind keine zusaetzlichen A01-A24-Zeilen, werden hier
aber einzeln gegen den aktuellen Quellstand abgeglichen. `BESTANDEN` bedeutet
hier nur: der konkret beschriebene technische Befund ist behoben und fokussiert
belegt; `TEILWEISE` bedeutet, dass nur ein Teil der Empfehlung umgesetzt ist;
`OFFEN` bedeutet, dass der Punkt bewusst noch nicht umgesetzt ist.

| Befund | Aktueller Stand | Nachweis bzw. verbleibende Luecke |
|---|---|---|
| F1 | BESTANDEN | Browser-High-/Low-Water und sichtbare Interim-Drops; `useWebSocket`-Tests. |
| F2 | BESTANDEN | Eigene Gateway-Queue und Sender-Task; Audio-Handler-Overflowtests. |
| F3 | BESTANDEN | Begrenzte Diarization-Queue, kein Entfernen angenommener PCM-Frames, sichtbarer Overflow. |
| F4 | BESTANDEN | Ordered-Transcript-Emit ausserhalb des Annahme-Locks; fokussierte Ordering-Suite. |
| F5 | TEILWEISE | Technisches Dossier-Egress-Gate und read-only Retrieval sind vorhanden; immutable Dossier-Cache pro Config-/Session-Generation fehlt noch. |
| F6 | BESTANDEN | Semantisch leere, schema-gueltige Antwort loest keinen zweiten Live-Aufruf aus. |
| F7 | BESTANDEN | Neuere Revision bricht aktive alte Revision ab; Stale-Guards bleiben als Fallback. |
| F8 | BESTANDEN | Pending-Events werden nach laufendem Cooldown-Handler erneut terminiert. |
| F9 | OFFEN | Lokale Streaming-Partials werden angezeigt, triggern den Debate-Coach aber noch nicht ueber einen gemeinsamen debounced Provisional-Kanal. |
| F10 | OFFEN | Consolidated Analyst wartet weiterhin auf das konfigurierte Intervall, bevor der erste Zyklus laeuft. |
| F11 | OFFEN | Synthesis serialisiert weiterhin geaenderte Fenster; inkrementelles Aenderungsjournal fehlt. |
| F12 | OFFEN | Zustaendigkeit und semantische IDs sind nicht vollstaendig anstelle von Text-/Zeitfenster-Dedup umgesetzt. |
| F13 | BESTANDEN | Unicode-Zahlworttokenisierung zentralisiert; Regressionstest fuer deutsche Zahlwoerter. |
| F14 | BESTANDEN | Prompt-Platzhalter-Allowlist weist unbekannte Namen vor Runtime-Formatierung ab. |
| F15 | OFFEN | Alembic ist noch nicht die einzige autoritative Startup-Schemageschichte; Legacy-Adoption bleibt bewusst im Runtime-Patch. |
| F16 | OFFEN | Prozesslokaler Orchestrator ohne Redis/PubSub bzw. Worker-Affinität; Mehrworkerbetrieb ist nicht freigegeben. |
| F17 | OFFEN | Produktionsprofil/Auth-/CORS-/WS-Token-Haertung ist nicht als neuer Deployment-Vertrag umgesetzt. |
| F18 | TEILWEISE | Dependency-Inventar und Constraints sind dokumentiert; ein voll gehashtes Lockfile fuer alle Backend-Abhaengigkeiten fehlt. |
| F19 | OFFEN | Transcript-UI nutzt fuer einige dynamische Bereiche noch Index-Keys und Tail-Scroll ohne Windowing. |
| F20 | BESTANDEN | `frontend/index.html` liefert `lang="de"`; Frontend-Build und UI-Tests gruen. |
| F21 | OFFEN | Dialog-Focus-Trap/-Restore und vollstaendiger Switch-/Inert-Vertrag sind noch nicht als gemeinsame Primitive eingefuehrt. |
| F22 | OFFEN | Systemaudio-Fallback wird technisch geloggt und als Status behandelt, aber beim Browser-Fallback noch nicht als eigene sichtbare Warnkarte ausgegeben. |
| F23 | OFFEN | Empfehlungskarte ist weiterhin atomar live; dedizierte kurze Statuszeile und Progressbar-Vertrag fehlen. |
| F24 | OFFEN | Agentenaktivitaet bleibt auf kleinen Ansichten tabellarisch breit; mobile Reflow-Variante fehlt. |
| F25 | OFFEN | Produktionsstart-/Runtime-Installationsprofil ist nicht als separater harter Deploy-Gate umgesetzt. |
| F26 | TEILWEISE | Einige Research-/Adapterpfade teilen HTTP-Clients; zentrale LLM-Pfade erzeugen weiterhin pro Request eigene Clients. |

Damit ist nachvollziehbar dokumentiert, dass F9-F12, F15-F19 und F21-F26 nicht
vergessen wurden. Sie sind Empfehlungen ausserhalb der bereits belegten
V3-Abnahme und bleiben offen bzw. teilweise, solange keine kleine, getestete
Umsetzung mit vertretbarem Regressionsrisiko vorliegt. Die vier realen V3-
Abnahmen A06/A18/A21/A22 bleiben unabhaengig davon BLOCKED.

Naechster konkreter Schritt: den sichtbaren historischen Release-/Marketing-
Content separat bewerten und danach den privaten Snapshot aus dem aktuellen,
geprueften Quellstand ohne lokale Zugangsdaten neu synchronisieren.

### Aktueller Resume-Override nach erneutem Chat-/Deep-Audit-Abgleich (2026-11-09)

Der fruehere Abschnitt `RESUME POINT` mit `DONE` beschreibt den damaligen
Release-Checkpoint und ist keine aktuelle Gesamtfreigabe. Fuer die Fortsetzung
ist dieser Abschnitt massgeblich:

- `GOAL_STATUS = IN_PROGRESS`.
- Das private GitHub-Repository und das Release `v0.6.6` existieren und wurden
  read-only als privat verifiziert; der dortige `source/`-Snapshot stammt aber
  aus einem frueheren Stand und enthaelt die letzten Frontend-/Desktop-
  Nachlaeufe noch nicht.
- Die lokale Windows-x64-onedir-EXE und der externe Prompt-/Config-Smoke sind
  weiterhin als lokaler `BUILD_READY`-Nachweis belegt. Ein neuer Build nach den
  letzten UI-Aenderungen ist vor einem Snapshot-/Release-Update erforderlich.
- Die aktuelle Frontend-Suite ist 269/269 gruen, Build 2.139 Module; Desktop
  193/193 mit einem Plattform-Skip; Docs 206/206; Backend-Fokus 101/101.
  Der aktuelle Backend-Gesamtlauf bleibt wegen Zeitlimit ohne neuen
  Vollsuite-Nachweis.
- A01-A05, A07-A17, A19-A20, A23-A24 sind BESTANDEN; A06, A18, A21, A22
  bleiben wegen echter Audio-/Hardware-/Human-Gates BLOCKED. Keine A-/N-/P-
  Zeile wurde uebersprungen; die Deep-Audit-Zusatzbefunde F1-F26 stehen in der
  Kreuztabelle unmittelbar davor.

Naechste verbindliche Reihenfolge: (1) sichtbaren historischen Content und
Branding-Reststellen entscheiden/klein korrigieren, (2) aktuellen Frontend-,
Backend-Fokus-, Desktop- und Docs-Nachweis erneut in der Matrix festhalten,
(3) den privaten Source-Snapshot aus genau diesem Stand neu erzeugen und auf
Cookies, Login-Daten, OAuth-/Provider-Zustaende, lokale Verlaeufe,
Transkripte, Datenbanken und Logs scannen, (4) nur bei positivem Privacy- und
Remote-Nachweis den privaten Branch/Release aktualisieren. Keine lokale
Login-/Cookie-Datei und kein Chatverlauf darf in den Snapshot gelangen.

#### V6-Zielbedingungen gegen den aktuellen Stand

| V6-Bedingung | Aktueller Status | Beleg bzw. Rest |
|---|---|---|
| Releasekritische Produktimplementierung | DONE fuer den bisher geprueften Code | V3-Matrix und fokussierte Regressionen; neuer Nachweis nach letztem UI-/Desktop-Patch noch erforderlich. |
| Facharbeiten integriert und Cleanup | DONE fuer dokumentierte, nicht-destruktive Pfade | `docs/v6-cleanup-manifest.json`, Migration-/Release-Tests; reale Eigentums-/Rollbackabnahme bleibt extern. |
| Externe Prompt-/Konfigurationsdateien | DONE | Externer Prompt-Hash-/Provider-Fehler-Smoke im lokalen Build-Gate. |
| Reale Windows-x64-onedir-EXE | DONE historisch, aktuell neu zu verifizieren | Vorhandene EXE/Archiv-Smokes sind belegt; nach dem letzten Desktop-Fix kein neuer Build ausgefuehrt. |
| Minimaler EXE-Startcheck | DONE historisch, aktuell neu zu verifizieren | Health/ASR/Shutdown-Smoke im V6-Gate; neuer Kandidat steht aus. |
| Releasepaket und SHA-256 | DONE fuer v0.6.6 | ZIP, Manifest, `SHA256SUMS.txt` und `START_HIER.md` sind im privaten Release verifiziert. |
| Privates Repository | BESTANDEN | `ErpeUser/backchannel-v6-private`, `isPrivate=true`, read-only verifiziert. |
| Privates GitHub Release mit Artefakten | BESTANDEN fuer v0.6.6 | Release ist nicht Draft/Prerelease; letzte Quell-/UI-Nachlaeufe sind noch nicht Bestandteil. |
| Fortschrittsdatei | IN_PROGRESS | Aktueller Resume-Override und F1-F26-Kreuztabelle sind eingetragen; nach jedem naechsten Paket erneut aktualisieren. |

Der V6-Release ist damit nicht vergessen oder uebersprungen, aber der Status
ist wegen des nachtraeglich geaenderten Quellstands bewusst `IN_PROGRESS` und
nicht erneut `DONE`, bis Build/Smoke und Snapshot-Synchronisierung fuer genau
diesen Stand abgeschlossen sind.

#### Nachweis dieses zweiten Abgleichs

- `backend`: `tests.test_v3_matrix_coverage` plus
  `tests.test_v3_acceptance_evidence` -> **9/9 bestanden**. Damit wird erneut
  maschinell bestaetigt, dass alle Matrix-IDs und die konservativen
  Evidenz-Gates vorhanden sind.
- `git diff --check` -> keine Whitespace-Fehler; die Ausgabe enthielt nur die
  bekannte Windows-LF/CRLF-Hinweisserie.
- Der Deep-Audit-Anhang wurde direkt aus der erreichbaren Datei mit 26
  Einzelbefunden gelesen; die F1-F26-Kreuztabelle oben fuehrt jeden Befund
  einzeln auf.
- Der V6-Auftrag wurde direkt aus der erreichbaren Pasted-Text-Datei gelesen;
  der auf dem Desktop genannte Markdown-Pfad existiert in dieser Umgebung
  nicht und wurde nicht ersetzt oder erfunden.
- Der in `AGENTS.md` referenzierte Sentrux-Pfad und auch `sentrux` im PATH sind
  in dieser Umgebung nicht vorhanden; `check`/`gate` konnten daher nicht
  ausgefuehrt werden. Dies ist ein Werkzeug-Blocker, kein bestandener
  Struktur-Nachweis.

### Deep-Audit-Nachlauf: API-Fallbacktexte und erneute Frontend-Verifikation (2026-11-09)

Umgesetzt wurden die letzten sichtbaren englischen Fehler-Fallbacks in
`frontend/src/services/api.ts` und `frontend/src/services/desktopUpdateApi.ts`:
Import-, Upload-, Benchmark- und Desktop-Berechtigungsfehler erscheinen nun
deutsch. Protokollheader wie `X-Backchannel-Instance` blieben absichtlich
unveraendert.

Nachweis:

- `frontend`: `npm test` -> **269/269 bestanden**.
- `frontend`: `npm run build` -> **2.139 Module**, erfolgreich; nur die bekannte
  Chunk-Groessen-Warnung.
- `backend`: Branding-Suite -> **2/2 bestanden**.

Status: dieses Lokalisierungspaket BESTANDEN. Historische Release-Notes und die
separate englische Marketing-/Docs-Site sind weiterhin als eigener Content-
Arbeitspunkt ausgewiesen; sie wurden nicht stillschweigend als vollstaendig
uebersetzt markiert.

Der lokale Snapshot-Abgleich bestaetigt die bekannte Luecke konkret: Die
Arbeitskopie verwendet bereits deutsche Texte in `StrategicSignalCard.tsx` und
den letzten Audio-/Update-Komponenten, waehrend
`build/v6-github-private-repo/source/` dort noch den frueheren englischen
Stand enthaelt. Das ist ein Snapshot-Synchronisierungsproblem, kein neuer
Produktfehler; es bleibt bis zur kontrollierten Aktualisierung offen.

Naechster konkreter Schritt: aktuelle fokussierte Backend-/Desktop-/Docs-
Nachweise im Resume-Override festhalten und danach den privaten Snapshot mit
dem jetzt erneut gebauten Quellstand synchronisieren.

### Deep-Audit-Nachlauf: Live-UI-Restluecken und Dokumentationsmetadaten (2026-11-09)

Zwei kleine, technisch selbststaendig pruefbare Deep-Audit-Reste wurden
geschlossen:

- `frontend/src/components/ActiveCall/TranscriptPanel.tsx` verwendet fuer
  gespeicherte Transkriptzeilen nun stabile IDs statt Array-Index-Schluesseln;
  fuer noch nicht persistierte Live-Zeilen gibt es einen deterministischen
  Zeit-/Sprecher-/Index-Fallback.
- `frontend/src/components/ActiveCall/AgentActivityPanel.tsx` wechselt auf
  kleinen Ansichten von der breiten Scroll-Tabelle zu beschrifteten, vertikal
  lesbaren Zeilen.
- `frontend/src/hooks/useAudioCapture.ts`, `frontend/src/App.tsx` und
  `frontend/src/components/ActiveCall/ActiveCallView.tsx` zeigen bei einem
  abgelehnten oder nicht verfuegbaren Browser-Systemaudio-Fang sichtbar an,
  dass nur das Mikrofon aufgenommen wird. Native Desktop-Aufnahme bleibt
  unveraendert.
- `docs-site/astro.config.mjs` und die JSON-LD-Breadcrumbs verwenden fuer den
  sichtbaren Produktnamen `Debate AI`; technische Domains, Header und
  Kompatibilitaetsnamen bleiben absichtlich unveraendert.

Nachweis:

- `frontend`: `npm test` -> **270/270 bestanden** (einschliesslich stabiler
  Transkript-Schluessel).
- `frontend`: `npm run build` -> **2.139 Module**, erfolgreich; nur die
  bekannte Chunk-Groessen-Warnung.
- `docs-site`: `npm run build` -> **17 Seiten** und `dist-site` erfolgreich;
  nur bekannte Astro-Warnungen fuer fehlende optionale i18n-/Font-Assets.

Status: Dieses UI-/Metadatenpaket BESTANDEN. Die Deep-Audit-Befunde F9-F12,
F15-F18, F21, F23 und F25 bleiben wie in der Kreuztabelle als offene
Architektur-/Betriebsarbeiten ausgewiesen; sie wurden nicht uebersprungen und
werden nicht durch diese kleinen Fixes kuenstlich als erledigt markiert.
Die echten manuellen V3-Gates A06/A18/A21/A22 bleiben BLOCKED.

Naechste konkrete Aktion: den privaten Source-Snapshot aus dem jetzt gebauten
Quellstand kontrolliert neu erzeugen, mit dem Privacy-Audit gegen Cookies,
Login-Daten, OAuth-/Provider-Zustaende, lokale Verlaeufe, Transkripte,
Datenbanken und Logs pruefen und erst danach eine Remote-Aktualisierung
entscheiden.

### Deep-Audit-Nachlauf: Privater Quell-Snapshot synchronisiert (2026-11-09)

Der zuvor veraltete private Quellstand wurde nach dem neuen Frontend-/Docs-
Build kontrolliert neu erzeugt und in
`https://github.com/ErpeUser/backchannel-v6-private` auf `master` aktualisiert.
Die Aktualisierung betrifft den sanitisierten Quell-Snapshot, nicht das alte
Release-Artefakt `v0.6.6`; dieses bleibt unveraendert, bis ein neuer EXE-
Build/Smoke durchgefuehrt wurde.

Snapshot-Nachweis:

- Remote-Commit: `949339d0bbe50b7f2dc7ab89f0fd43dbf178a960` (inklusive finaler Fortschrittsdatei).
- `source/`: **1.027 Dateien**, **19.434.696 Bytes**; per-Datei-SHA-256 in
  `SOURCE_SNAPSHOT_MANIFEST.json`.
- Ausgeschlossen: `.env`, Cookies, Browserprofile, Login-/OAuth-Zustaende,
  Provider-Account-Ueberschreibungen, lokale Verlaeufe/Transkripte, Datenbanken,
  Logs, temporaere Testordner, Modellgewichte, native Binaries und generierte
  Bundles.
- Dateinamen-/Endungsscan: **0** lokale Daten-/Credential-Dateien.
- Secret-Musterscan: nur die drei bekannten synthetischen Redaktions-Test-
  fixtures; keine Live-Schluessel.
- Der private Remote-Branch zeigt nach dem Push denselben Commit.

Status: Snapshot-Synchronisierung BESTANDEN. Eine neue oeffentliche oder
private Release-Datei wurde bewusst nicht behauptet; `v0.6.6` ist als
historisch gebaut und fuer den vorherigen Stand dokumentiert. Die manuelle
Audio-/Hardware-/Human-Abnahme A06/A18/A21/A22 sowie die offenen Deep-Audit-
Architekturpunkte bleiben BLOCKED/OFFEN.

Naechster konkreter Schritt: die verbleibenden automatisierbaren V6-Gates
(Desktop-Neubau/Smoke nach dem aktuellen UI-Patch und ein moeglichst enger
Backend-Gesamtlauf ohne lokale TEMP-Probleme) ausfuehren und danach nur den
tatsaechlich belegten Status im Resume-Override nachziehen.

### Deep-Audit-Nachlauf: aktueller Windows-Build und Smoke (2026-11-09)

Der aktuelle Windows-x64-onedir-Kandidat wurde mit
`scripts/build_debate_assistant.ps1 -Python .\\.release-venv\\Scripts\\python.exe -SkipDownloads`
bis zum Build und dem Staged-Smoke ausgefuehrt. Die Wrapper-Ausfuehrung
ueberschritt das 120-Sekunden-Ausfuehrungslimit waehrend der abschliessenden
Komprimierung; deshalb wird kein neuer Release-Upload behauptet.

Belastbarer Teilnachweis:

- `build/release-stage/Backchannel/Backchannel.exe` wurde neu erzeugt.
- `desktop/scripts/smoke_test.py --bundle build/release-stage/Backchannel`
  -> **OK: healthy on port 8474; bundled local ASR runtime usable; clean
  shutdown; exit 0**.
- Der bestehende `dist/Backchannel-DebateAI-windows-x64.zip` bleibt der
  vorherige, bereits verifizierte Release-Kandidat; er wurde nicht als neuer
  Build ausgegeben.

Status: aktueller Onedir-Build/Smoke **BESTANDEN**, neue ZIP-/Release-
Komprimierung **nicht nachgewiesen wegen Zeitlimit**. Der Remote-Source-
Snapshot bleibt auf `949339d`; `v0.6.6` bleibt historisch. Keine manuelle
Abnahme wurde simuliert.

Nachtrag: Fuer den aktuellen Nutzerbedarf ist keine ZIP erforderlich. Die ZIP
ist nur fuer den optionalen Release-/Updater-Vertrag relevant; der direkte
Windows-Onedir-Build und sein Start-/ASR-/Shutdown-Smoke sind der entscheidende
Nachweis. Ein separater Archiv-Smoke mit dem frei benannten lokalen
`*-current.zip` wurde deshalb nicht als Produktfehler gewertet, da der Test
absichtlich den kanonischen Release-Dateinamen `Backchannel-windows-x64.zip`
verlangt.

### V6-Nachlauf: direkter EXE-Upload (2026-11-09)

Auf Wunsch wurde der aktuelle direkt startbare Windows-Build als separates,
klar gekennzeichnetes Asset in den privaten Release `v0.6.6` hochgeladen. Der
historische ZIP-/Manifest-Satz blieb unveraendert:

- Asset: `Backchannel-DebateAI-windows-x64-current.exe`
- Groesse: 26.899.718 Bytes
- SHA-256: `F7CD836461ECC903AFC91023D14A3FE2030D5F3CE7BEC369BA2B02DB54FC74D5`
- URL: `https://github.com/ErpeUser/backchannel-v6-private/releases/download/v0.6.6/Backchannel-DebateAI-windows-x64-current.exe`
- Begleitend: `SHA256SUMS-current-exe.txt`

Status: direkter EXE-Push **BESTANDEN**. Das Asset ist bewusst als aktueller
Kandidat benannt und nicht nachtraeglich in das alte ZIP-Release-Manifest
eingeschmuggelt. Eine neue Release-Version bleibt bis zu einer vollstaendigen
neuen Release-Metadatenrunde unnoetig.

Naechster konkreter Schritt: falls ein neues Releaseartefakt benoetigt wird,
die bereits erzeugte `build/release-stage/Backchannel`-Kopie in einem laengeren
lokalen Lauf komprimieren, danach Archiv-Smoke und SHA-256 ausfuehren; bis dahin
keine neue Release-Version veroeffentlichen.

### Backend-Gesamtlauf mit Release-Umgebung (2026-11-09)

Der vollstaendige Backend-Testlauf wurde anschliessend mit der installierten
Release-Umgebung (`.release-venv\\Scripts\\python.exe`) wiederholt:

- `python -m unittest discover -s tests` -> **1.740 Tests OK, 3 uebersprungen**
  in 131,5 Sekunden.
- Der vorherige globale Python-3.14-Lauf mit 169 Importfehlern wird als
  Umgebungsfehlversuch verworfen und nicht als Produktstatus gefuehrt.

Damit sind Frontend 270/270, Backend 1.740/1.740, Desktop 193/193 (ein
Plattform-Skip), Docs 206/206 sowie der aktuelle Onedir-Smoke nachgewiesen.
Die offenen manuellen Audio-/Hardware-/Human-Gates und die in der F1-F26-
Kreuztabelle als OFFEN/TEILWEISE markierten Architekturpunkte bleiben davon
unberuehrt.

Naechste konkrete Aktion: Abschlussstatus aus diesen Nachweisen und den
verbleibenden BLOCKED/OFFEN-Punkten konsistent zusammenfassen; keine
Vollfreigabe oder neue Release-Version behaupten.

### Nachweisabgleich abgeschlossen (2026-11-09)

Der erneute Chat-/Deep-Audit-Abgleich ist damit technisch abgeschlossen:

- Keine A-/N-/P0-/P1-/P2-/P3-Zeile fehlt in der V3-Matrix; alle nicht
  automatisierbaren Punkte sind explizit BLOCKED/OFFEN.
- Frontend: 270/270 Tests und 2.139-Modul-Produktionsbuild bestanden.
- Backend: 1.740/1.740 Tests bestanden, 3 uebersprungen, in der Release-
  Python-Umgebung.
- Desktop: 193/193 Tests bestanden, ein Plattform-Skip; aktueller Onedir-
  Kandidat und Health/ASR/Shutdown-Smoke bestanden.
- Docs-Site: 206/206 Tests und 17-Seiten-Build bestanden.
- Privater Source-Snapshot: auf Remote-`master` Commit `949339d` synchron,
  1.027 Dateien / 19.434.696 Bytes, Privacy-Scan ohne lokale Kontodaten.
- Sentrux bleibt ein externer Werkzeug-Blocker, weil das in `AGENTS.md`
  angegebene Programm in dieser Umgebung nicht vorhanden ist.

Nicht als erledigt ausgegeben werden: neue ZIP-Komprimierung nach dem aktuellen
Patch (Zeitlimit), neue Release-Version, echte deutsche Mikrofon-/Discord-
Aufnahme, Hardware-/DPI-Abnahme, menschliche rhetorische Bewertung sowie die
offenen Deep-Audit-Architekturpunkte F9-F12, F15-F19 und F21-F26.

GOAL_STATUS bleibt daher **IN_PROGRESS**. Naechste konkrete Aktion fuer eine
spätere Fortsetzung: nur einen laengeren lokalen ZIP-/Archiv-Smoke-Lauf starten
oder die dokumentierten manuellen Gates mit echter WAV-/Hardware-Abnahme
ausfuehren; keine bereits bestandenen Pakete wiederholen.

### Desktop-Fortsetzung (2026-11-11)

- Checkout auf `ErpeUser/backchannel-v6-private`/`master` synchronisiert:
  `HEAD == origin/master == ddf1b3e05a6b70252b2335e09581140107144227`.
- Der minimale Desktop-/Release-Lauf ist wiederholbar dokumentiert:
  89 Desktop-Kern-/Release-/Updater-/Smoke-Tests bestanden, 1 Symlink-Test
  wegen fehlender Windows-Rechte uebersprungen; zusaetzlich 7
  `test_version_resource`-Tests bestanden. Die PowerShell-Vertraege
  `test_release_desktop.ps1` und `test_build_debate_assistant.ps1` sowie
  Python-`compileall` sind gruen.
- Ein Acceptance-Vertragsfehler in
  `source/backend/app/routers/updates.py` wurde minimal korrigiert:
  `start_background_check()` verwendet nun den vom Test und Vertrag
  erwarteten direkten Singleton-Aufruf. Danach bestanden
  `test_update_acceptance` (2/2) und `test_smoke_test` (5/5).
- `desktop.tests.test_release_contract` bleibt als Snapshot-Blocker sichtbar,
  weil `source/.github/workflows/desktop-release.yml` fehlt; der Workflow liegt
  nur unter dem Repository-Root `.github/workflows/desktop-release.yml`.
- Keine EXE-/ZIP-Neuveroeffentlichung und keine manuellen Audio-/Hardware-/
  Provider-Gates behauptet. Laufende PostgreSQL-Prozesse halten alte
  `dist/`-Dateien offen; diese wurden nicht fremd beendet.

Naechste konkrete Aktion: den fehlenden `source/.github`-Workflowvertrag gegen
  den gewollten Snapshot-Aufbau entscheiden und erst danach den vollstaendigen
  Desktop-Release-Contract ausfuehren; bis dahin keine Windows-Freigabe
  behaupten.

### DESKTOP_FINAL-Gesamtumsetzung gestartet (2026-11-11)

- Neues persistentes Goal fuer die vollstaendige Umsetzung von
  `source/docs/DESKTOP_FINAL.md` angelegt; der Ausfuehrungsplan liegt in
  `source/docs/superpowers/plans/2026-11-11-desktop-final-completion.md`.
- `source/scripts/sync_final_workspace.py --repo <repository-root>` lief mit
  `HEAD == origin/master == ddf1b3e05a6b70252b2335e09581140107144227` durch.
  Der Synchronisierer sicherte die zwei vorherigen tracked Aenderungen in
  Stash `9eab1d37ad0a159f74471f570f7000abae0c6102`; beide wurden nach Review
  kontrolliert wieder angewendet. Keine Nutzer-/Runtime-Datei wurde durch den
  Synchronisierer geloescht.
- Task 1 ist damit verifiziert; als naechstes folgt die vollstaendige
  Identitaets-/Kompatibilitaetsmatrix fuer Desktop, Updater, API, UI und
  Datenpfade. Keine Zwischenfreigabe behaupten.
### DESKTOP_FINAL-Paket 2/3: kanonische Produkt- und Update-Identitaet (2026-11-11)

- Der Remote-Sync wurde erneut mit dem neuesten `sync_final_workspace.py` ausgefuehrt; lokale Aenderungen wurden in Stash `d4fbe9c8591692de86bec3e7db415e0d22270652` gesichert, geprueft und wiederhergestellt. Kein AppData-/DB-/Key-/Cookie-/Modellordner wurde veraendert oder geloescht.
- Desktop-Identitaet verwendet `DebateAI.exe`, `DebateAIUpdater.exe`, `DebateAI`/`DebateAI.app` und `X-DebateAI-Instance`; `Backchannel`-Bundle, Launcher, Updater, Datenordner und Header bleiben kontrollierte Lese-/Fallback-Aliase.
- Build-/Release-/Manifest-/Workflow-/Linux-Container-/Smoke-Pfade erzeugen jetzt `DebateAI-windows-x64.zip`, `DebateAI-linux-x64.tar.gz`, `DebateAI-macos-arm64.zip`; Update-Signierung akzeptiert alte Assets weiterhin nur als Legacy-Eingang.
- `DEBATEAI_*`-Umgebungsvariablen werden fuer Daten-, Update-, FFmpeg-, AI-Konfigurations-, Host-/Origin- und CLIProxy-Pfade bevorzugt; alte `BACKCHANNEL_*`-Namen bleiben kompatibel.
- Nachweise: `compileall` gruen; Desktop Identity/Updater/Smoke/Subscription/Native-Update-Akzeptanz gruen; Release-Contract und Release-Manifest 30/30 gruen; vorhandene Windows-Symlink-Pruefungen bleiben wegen fehlender Symlink-Berechtigung uebersprungen.
- Offen: Restliche Provider-/Bridge-Variablen fachlich durchtesten, Backend-/Frontend-Gesamtsuiten, Root-Administration/Repository-Rename pruefen, Build-Abhaengigkeiten und Assets synchronisieren, nativen `build_debate_assistant.ps1 -IncludeOracle` ausfuehren, ZIP/Hash und die 15 Human-/Hardware-Gates getrennt dokumentieren.
- Naechste Aktion: canonical/legacy env chain in Backend-Provider-Routern abschliessen und danach Frontend-/Backend-/Desktop-Gesamttests mit korrektem `PYTHONPATH` ausfuehren.

### DESKTOP_FINAL-Paket 3/3: Volltest, Vertragsluecken und Wiederaufnahmepunkt (2026-11-11)

- Der Volltest wurde aus dem echten `source`-Arbeitsverzeichnis mit der
  Release-Umgebung ausgefuehrt: **1.854 Backend-Tests OK, 4 uebersprungen**
  (`python -m unittest discover -s backend/tests`, 138,8 Sekunden). Der
  Root-Aufruf wird nicht als Produktfehler gewertet, weil ein Test seinen
  Unterprozess-PYTHONPATH relativ zu `source` aufloest.
- Die Response-Contract-Luecke ist geschlossen: `error` ist jetzt neben
  `ok`, `timeout`, `empty`, `stale` und `abstent` auch als Failure-Klasse
  zulaessig. Die Blind-Benchmark-Exporte bewahren damit Fehler im Nenner,
  ohne Providerdetails oder Geheimnisse zu exportieren.
- Upload- und Analyse-Routen akzeptieren weiterhin echte AsyncSessions und
  sind zugleich gegen synchrone Test-Doubles fehlertolerant; ein fehlendes
  optionales `rollback` kann den eigentlichen Analysefehler nicht mehr
  verdecken. Die beiden Orchestrator-/Prompt-Regressionen und die kanonischen
  DebateAI-Branding-Erwartungen sind ebenfalls behoben.
- Der Fortschritt ist dadurch unterbrechungsfest: vor jedem weiteren Build
  sind `git status`, `git rev-parse HEAD`, `git rev-parse origin/master` und
  der letzte Eintrag dieses Logs zu pruefen. Der naechste erlaubte Schritt ist
  der Frontend-/Desktop-Gesamtlauf und anschliessend ein neuer Build aus exakt
  diesem Source-Stand; keine Human-/Hardware-/Provider- oder
  Authenticode-Abnahme darf automatisiert als bestanden ausgegeben werden.

### Finaler Windows-Kandidat aus Commit 97e4b3e (2026-11-11)

- Frontend: `npm test` **323/323**; Desktop: **207/207**, ein dokumentierter
  Symlink-/Windows-Rechte-Skip; Backend: **1.854/1.854**, vier dokumentierte
  Skips; `compileall` und `git diff --check` gruen.
- Der vorgeschriebene `build_debate_assistant.ps1 -IncludeOracle`-Lauf hat
  Frontend, Bridge, Oracle/Node24, PyInstaller, PostgreSQL, ffmpeg, Ollama-
  Ressourcen und Bundle erfolgreich gebaut. Nur der Windows-
  `Compress-Archive`-Schritt ueberschritt das Ausfuehrungszeitlimit; das
  vollstaendige Staging wurde mit dem validierten nativen TAR-ZIP-Pfad
  archiviert.
- Finaler Pfad: `source/dist/DebateAI-windows-x64.zip`, **432.425.608 Bytes**,
  SHA-256 **`7D1470219C06B6A7E81DAE5C2E07AB1E34794E1C569414B2A16C2E7BA5AF0D27`**.
  `source/dist/DebateAI/DebateAI.exe` und `DebateAIUpdater.exe` stammen aus
  demselben Staging. Bundle-Smoke meldet `healthy`, lokales ASR und sauberen
  Shutdown; der native Update-/erzwungene-Rollback-Smoke ist bestanden.
- Der Runtime-Quellstand des Kandidaten ist `97e4b3e3446de9cd69a4c6d84cff737d6a4b42d7`; die nachgelagerte Evidenz-Dokumentation ist in `d1e68455161535e58110104a22147275df4b3d64` gepusht und aktuell gilt `HEAD == origin/master == d1e68455161535e58110104a22147275df4b3d64`. Die verbleibenden 15
  Human-/Hardware-/Provider-/Authenticode-Gates sind vorbereitet, aber nicht
  als automatisiert bestanden ausgegeben.

### Codex-Abnahme-Fortsetzung (2026-11-12)

- Der echte Windows-Checkout `C:/Users/User/Datein/Coding/DebateAI` wurde mit
  dem aktuellen `origin/master` synchronisiert: `HEAD == origin/master ==
  e632d852b6a0dc4c6c7a8e65372c7f9b087fd4a5`. Untracked Build-, Modell- und
  Runtime-Dateien blieben erhalten; zwei alte Stashes wurden geprueft und
  nicht erneut angewendet, weil ihre Source-Aenderungen bereits integriert sind.
- Drei isolierte Vertragsfehler wurden behoben: der Alembic-Runtime-Override
  bleibt mit Test-Doubles kompatibel und ist als direkter `set_main_option`-
  Aufruf sichtbar; ein 404 beim Update-Asset bewahrt eine resumierbare Partial-
  Datei; der Subscription-Bridge-Export uebergibt den korrekten Wert an
  `set_env`.
- Nachweise: Backend **1.865/1.865** (4 Skips), `compileall` gruen; Frontend-
  Build, **325/325** Node-Tests und **5/5** PWA-Tests gruen; Desktop
  **206/206** (1 Symlink-Rechte-Skip) mit `PYTHONPATH=desktop;backend`.
- Offen bleiben der exakte native Windows-EXE/ZIP-Build samt Hash/Smoke, echte
  Mikrofon-/WASAPI-/WebView2-/Hardware-/Provider-/Login-/Authenticode-Gates,
  reale Debattenvideos sowie ein verifizierter GitHub-Runnerlauf.

Naechste konkrete Aktion: den synchronisierten, getesteten Source-Stand mit
  `build_debate_assistant.ps1 -IncludeOracle` bauen und nur die dabei belegten
  Windows-/Archiv-/Rollback-Ergebnisse dokumentieren.
