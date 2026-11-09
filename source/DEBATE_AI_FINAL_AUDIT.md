# Debate AI - finaler lokaler Kandidaten-Audit

## Wiederaufnahme- und Release-Checkpoint (7. November 2026)

Die fuehrende, aktuellere Fortschritts- und Entscheidungsquelle ist
`.ai/DEBATE_AI_OPTIMIERUNG.md`; dieser Bericht fasst den gebauten Kandidaten
zusammen.

- **Erledigt:** Optimierungspunkte 01-16, A1/A2/A3, B1-B5, Windows-Paketkorrekturen, Plugin-gestuetzter Designreview, gezielte UX-Korrekturen und finaler Windows-x64-One-Dir-Neubau.
- **Buildstatus:** Erfolgreich. Bundle-Smoke und Archiv-Smoke starteten die echte EXE, prueften lokale ASR-Grundfunktion, Unicode-/Leerzeichen-Installationspfad, Update-Swap, erzwungenen Rollback und kontrolliertes Beenden.
- **Laufende Prozesse:** Keine Build- oder Backchannel-Prozesse. Der letzte isolierte EXE-Review wurde kontrolliert beendet.
- **Offen:** Sichtbare Windows-/DPI-/Mikrofonabnahme, Sentrux und ein sauberer synchronisierter `master` fuer einen autorisierten Release.
- **Naechster konkreter Schritt bei Wiederaufnahme:** Den vorhandenen Kandidaten sichtbar mit einer realen deutschen Mikrofonsitzung abnehmen; erst danach den gemischten Arbeitsstand verlustfrei in einen sauberen Releasezustand ueberfuehren.
- **Auslieferung:** `dist/Backchannel/`, `dist/Backchannel-DebateAI-windows-x64.zip` und diese Datei.

## 1. Umfang und Vorgehen

Der bestehende, umfangreich uncommittete Arbeitsbaum wurde erhalten. Nutzerdaten, Konfiguration, lokale Providerdaten und Secrets wurden weder geloescht noch in das Paket aufgenommen. Es wurde kein Commit erzeugt und kein globaler Ollama-Zustand veraendert.

Geprueft und abgeschlossen wurden:

- die urspruenglichen Optimierungspunkte 01-16;
- persistentes Streaming-ASR, adaptives Sprecherbudget und hybrides Wissensretrieval;
- Ereignisreplay, Ressourcenprofile, Packaging, Fresh-DB-Start und Windows-Pfadfaelle;
- ein kurzer Design-/UX-, Effizienz-, Vereinfachungs-, Bereinigungs-, Library- und Update-Review;
- der reale Windows-x64-One-Dir-Build mit EXE- und Archiv-Smokes.

## 2. Status 01-16

### 01 | Zweigleisiges Argumentretrieval - UMGESETZT

Sofortantworten bleiben vom langsamen Recherchepfad getrennt. Lokale und externe Vertiefung ergaenzen spaeter Belege, ohne die erste sprechbare Reaktion zu blockieren.

### 02 | WebSocket-Zustellung vom Audio- und Schreibpfad entkoppeln - UMGESETZT

Ereignisse besitzen geordnete Sequenzen, Replay und begrenzte Queues. Der Frontend-Cursor wird erst nach tatsaechlichem Rendern fortgeschrieben; Hidden-Window-Replay bleibt konsistent.

### 03 | Spaete Analysen als Themenwissen statt veraltete Antwort - UMGESETZT

Verspaetete Ergebnisse werden kontextbezogen bewertet, als Hintergrundwissen markiert oder verworfen, statt eine ueberholte Live-Antwort zu ersetzen.

### 04 | Ressourcenplaetze bis zum realen Ende nativer Arbeit halten - UMGESETZT

Native ASR-, Embedding- und Analysearbeit behaelt ihre Ressourcenplaetze bis zum tatsaechlichen Abschluss. Abbruch- und Fehlerpfade geben Slots kontrolliert frei.

### 05 | Ollama-/Qwen-Livepfad optimieren - UMGESETZT

Das Economy-Profil nutzt 4096 Kontexttoken, Balanced 8192. Explizite Einstellungen bleiben erhalten; `think=false` wird nur fuer bekannte Qwen-3-Familien gesetzt.

### 06 | Austauschbarer ASR-Backendvertrag und Streamingoption - UMGESETZT, EXTERN BEGRENZT

Der NeMo-Speech.cpp-Vertrag v0.3.0 ist als austauschbarer Adapter implementiert. Mikrofon- und Systemspur besitzen persistente Streams, stabile Segment-IDs, monotone Revisionen, Append-Partials, Boundary-Flush und sauberen Session-Close.

### 07 | VAD-Pause von inhaltlichem Sprecherzugende unterscheiden - UMGESETZT

Audio-Chunks koennen vor der Diarisierungsgrenze in den Streamingpfad gelangen. VAD-Pausen schliessen nicht mehr automatisch den inhaltlichen Sprecherzug ab.

### 08 | Einfacher 1:1-Audiomodus - UMGESETZT

Mikrofon und Systemaudio koennen vorlaeufig getrennten Sprecherrollen zugeordnet werden. Das adaptive Minutenbudget gilt in allen Zustaenden; nach Erschoepfung entsteht `auto_unknown` statt unbegrenzter Neuprofilierung.

### 09 | Recherchecaches, Redirectschutz und Wiederverwendung - UMGESETZT

Rechercheergebnisse werden kontrolliert wiederverwendet. Redirects, Zieladressen, Laufzeitbudgets und Cache-Grenzen werden geprueft.

### 10 | Providerweg und exakte Modellvorgaben - UMGESETZT

Providerfaehigkeiten, lokale OpenAI-kompatible Endpunkte und Modellvorgaben werden zentral bewertet. Cloudwege bleiben unter Privacy First gesperrt; lokale/private Ziele bleiben nutzbar.

### 11 | Normalisierte Claimdaten als fachliche Wahrheit - UMGESETZT

Claims besitzen normalisierte Identitaeten und Metadaten fuer Quellen, Widersprueche, Lernsignale und spaetere Analyse.

### 12 | Stabile und vollstaendig abgedeckte atomare Claims - UMGESETZT

Atomare Claims werden stabil abgeleitet und mit Zahlen-, Negations-, Zeit- und Bedingungsmarkern semantisch unterschieden.

### 13 | Gemeinsamer Dossier-/Quellenkontext und Rangfusion - UMGESETZT

PostgreSQL-FTS und FastEmbed werden per Reciprocal Rank Fusion verbunden. ACL, Zeit-/Trefferbudgets und persistierte Embedding-Metadaten sind integriert.

### 14 | Stabile Windows-Audio-Endpunktidentitaeten - UMGESETZT

Windows-Audioendpunkte behalten stabile Identitaeten; Capture- und Diagnosepfade verwenden dieselben Zuordnungen.

### 15 | Gebuendelte React-Updates und kontextbezogene Verspaetungswertung - UMGESETZT

Live-Ereignisse werden begrenzt gesammelt und sichtbarkeitsabhaengig synchronisiert. Wiederanzeige, Replay und Analysealter werden konsistent behandelt.

### 16 | Vereinfachung ohne Systemwechsel - UMGESETZT

Die bestehende Architektur blieb erhalten. Gemeinsame Adapter, Standardbibliotheken und vorhandene Frameworkpfade wurden bevorzugt; kein riskanter Systemwechsel oder Grossrefactor wurde vorgenommen.

## 3. Echte Aenderungen und Verbesserungen

### Audio, Analyse und Wissen

- Persistenter Streaming-ASR-Pfad je physischer Spur mit revisionssicheren Partials.
- Festes adaptives Sprecherbudget mit sicherem Unknown-Fallback.
- Hybrides FTS-/Embedding-Retrieval mit ACL, Budget und RRF.
- Robuste Orchestrator-Initialisierung auch ohne laufenden Event-Loop.
- Semantische Claim-Marker fuer Zahl, Negation, Zeit und Bedingung.

### Frontend und UX

- Replay-Cursor an wirklich gerenderten Zustand gebunden; Queue begrenzt und beim Wiederanzeigen synchronisiert.
- Deutsche, konsistente Navigations- und Hilfetexte statt gemischter englischer Texte.
- Sichtbaren Mojibake-Text im 1:1-Audiomodus korrigiert.
- `Neue Debatte`, `Einstellungen` und `Einstellungen -> Assistenten` als einheitliche Begriffe verwendet.
- Interne Agent-Slugs aus der normalen Oberflaeche entfernt.
- Modellserverstatus, Aktionen und Privacy-First-Erklaerung lokalisiert.
- Schliessen-, Auswahl- und Dialogaktionen im Debattendialog auf mindestens 44 px Zielhoehe gebracht.
- Debattennamen serverseitig auf die Frontendgrenze von 120 Zeichen begrenzt; ueberlange Direktaufrufe liefern Validierung statt Datenbankfehler.

### Windows-Paket und Update

- Build erfolgt in getrenntem Staging; die letzte gueltige Auslieferung bleibt bis nach allen Smokes erhalten.
- Publish-Swap besitzt abgesicherten Rollback und wird durch einen erzwungenen Fehlerfall geprueft.
- Alembic-Konfiguration und Migrationen sind Bestandteil des Pakets.
- Leere/unversionierte Datenbanken werden aus SQLAlchemy-Metadaten erstellt und danach auf Alembic `head` gestempelt.
- Eingebettetes PostgreSQL wird bei einem nicht ASCII-faehigen Installationspfad einmalig in einen isolierten ASCII-Laufzeitpfad kopiert.
- Archiv-Smoke trennt echten Unicode-/Leerzeichen-Installationspfad von isolierten ASCII-Pruefdaten und prueft den realen Update-Swap.
- Provider-Credentials werden fuer Smokes aus der Umgebung entfernt.

## 4. Design-, Effizienz-, Bereinigungs- und Update-Review

Verwendet wurden Designly Visual QA, Awesome Design mit einer Linear-orientierten Desktop-Designreferenz, Better Design First-Visit Walks und Context7 fuer aktuelle React-Effekt-/Polling-Hinweise.

Ergebnis:

- Dunkle Oberflaechenstufen, weisse Primaerschrift und ein einzelner Tuerkis-Akzent liefern klare Hierarchie und ausreichenden Kontrast.
- Desktop bei 1280 x 720 und mobile Reflow-Pruefung bei 375 x 667 zeigten keinen horizontalen Ueberlauf.
- Begriffe, Umlaute, Hilfetexte und Touchziele wurden an den belegten Stellen korrigiert.
- Das Live-Debattenlayout priorisiert die Sprechspur, danach Live-Argumente und das einklappbare Transkript.
- Der 600-ms-Overlay-Poll bleibt lebensdauergebunden und billig; Sichtbarkeitspause/Backoff wurde als nicht blockierende spaetere Verbesserung dokumentiert.
- Grosse Dateien wie `App.tsx`, `DebateCoachPanel.tsx`, `orchestrator.py` und `desktop/launcher.py` wurden vor Release nicht riskant zerlegt.
- Nachweislich ungenutzte Frontendimporte wurden entfernt. Die direkte, nicht verwendete Abhaengigkeit `@dnd-kit/sortable` wurde entfernt; transitive DnD-Hilfen bleiben korrekt erhalten.
- Exakte Windows-Abhaengigkeiten bleiben eingefroren. Keine blinde Major-Aktualisierung und kein `npm audit fix --force` wurde ausgefuehrt.

## 5. Verifikation

Frische oder fuer diesen Release massgebliche Nachweise:

- 163 gezielte Backend-Integrationspruefungen erfolgreich.
- 78 gezielte Audio-/ASR-Pruefungen erfolgreich.
- 57 gezielte A1-/A2-Pruefungen erfolgreich.
- Retrieval: 60 gezielte Pruefungen plus 5 Integrationspruefungen erfolgreich.
- Desktop: 174 Pruefungen erfolgreich, 1 Skip.
- PostgreSQL-/Unicode-Lifecycle: 29 Pruefungen erfolgreich.
- Fresh-DB-/Schema: 12 Pruefungen erfolgreich.
- Debattennamen-Validierung: 2 neue Pruefungen erfolgreich.
- Frontend vor der letzten Politur: 262 Pruefungen erfolgreich und Produktionsbuild erfolgreich.
- Nach der letzten Politur: 12 direkt betroffene Frontendpruefungen erfolgreich; TypeScript und Vite-Produktion erfolgreich, 2138 Module transformiert.
- Finaler PyInstaller-Build erfolgreich.
- Finaler Bundle-Smoke erfolgreich: echte EXE, Health, lokale ASR-Grundfunktion, sauberes Beenden.
- Finaler Archiv-Smoke erfolgreich: Start aus Unicode-/Leerzeichenpfad, Update-Swap, erzwungener Rollback, sauberes Beenden.
- Kein abschliessender sichtbarer EXE-/DPI-/Mikrofoncheck wurde behauptet; DOM-, Build- und Smokepruefungen ersetzen diese menschliche Abnahme nicht.
- Paketinhalt geprueft: Frontend, Alembic, Migrationen, Silero, ResNet152, PostgreSQL und CLIProxy vorhanden; keine offensichtlichen Secret-Dateien gefunden.

## 6. Verbleibende Grenzen und bewusste Rueckstellungen

- NeMo-Speech.cpp v0.3.0 und das Nemotron-Modell sind optional und auf diesem Rechner nicht installiert. Adapter und Protokoll sind getestet; echte externe Modellinferenz wurde nicht behauptet.
- Ein Backend-Gesamtlauf vor den letzten Korrekturen hatte bei 1622 Pruefungen 18 Failures, 38 Errors und 2 Skips. Die groessten Ursachen wurden danach behoben und durch fokussierte Gruppen bestaetigt; ein zweiter kompletter Gesamtlauf wurde zur Vermeidung unnoetiger Doppelarbeit nicht gestartet.
- `npm ci` und `npm audit --audit-level=moderate` melden 0 Schwachstellen.
- Wenn bereits `%LOCALAPPDATA%` selbst keinen ASCII-Pfad und keinen 8.3-Alias besitzt, ist dieser besondere PostgreSQL-Datenpfad nicht extern verifiziert. Der aktuelle Benutzer- und Archiv-Smoke ist erfolgreich.
- Sentrux war in der angegebenen lokalen Installation nicht verfuegbar; es wird kein Sentrux-Pass behauptet.
- Oracle bleibt bewusst ungebuendelt. CLIProxy und der freigegebene Gemini-Pfad sind enthalten.
- Keine Anmeldung, 2FA oder Kontopruefung wurde fuer diesen Abschlusslauf ausgeloest.
- Keine kostenpflichtigen Provideraufrufe wurden fuer Build oder Smoke ausgefuehrt.

## 7. Finale Artefakte

### One-Dir-Anwendung

- Pfad: `C:\Users\User\Datein\Coding\DebateAI\dist\Backchannel`
- Dateien: 3739
- Gesamtgroesse: 703734086 Bytes
- Startdatei: `C:\Users\User\Datein\Coding\DebateAI\dist\Backchannel\Backchannel.exe`
- EXE-Groesse: 26888457 Bytes
- EXE-SHA-256: `8D6E9E68F6531A9D73FEBE4D2A775BD1DEB92965629B562A639DCF5404ECD3FE`
- Windows-Produktname/Beschreibung: `Debate AI` / `Debate AI`

### Vollstaendiges ZIP

- Pfad: `C:\Users\User\Datein\Coding\DebateAI\dist\Backchannel-DebateAI-windows-x64.zip`
- Groesse: 340119456 Bytes
- Archiveintraege: 3804
- Zeitstempel: `2026-11-07T22:37:32.0562780+01:00`
- SHA-256: `8EF57261907867828B57CC97AA1ADEF97020736E6AE86F965E38D1B57360037D`

## 8. Abschlussurteil

Der Windows-x64-Kandidat ist als startfaehige One-Dir-Anwendung und
vollstaendiges ZIP gebaut und gesmokt. Es besteht kein bekannter Paket-, Start-,
Swap- oder Rollback-Defekt. Er ist nicht veroeffentlicht oder menschlich
abgenommen; die sichtbare Windows-/Audioabnahme und der saubere autorisierte
Releasezustand bleiben echte Freigabeblocker.
