# DebateAI – Browser-KI-Übergabe und Fehlerchronik

Diese Datei ist eine sachliche Übergabe für eine zweite KI, die den Windows-Desktopstand von DebateAI prüft oder weiter behebt. Sie beschreibt die wiederkehrenden Fehler aus dem Arbeitsverlauf, die nachgewiesenen Ursachen, die eingebauten Korrekturen und die Reihenfolge, in der ein neuer Fehler untersucht werden muss.

## Verbindlicher Projektstand

- Repository: `ErpeUser/DebateAI` (privat)
- Checkout: `C:\Users\User\Datein\Coding\DebateAI`
- Zielbranch: `master`
- Letzter veröffentlichter Quellstand: `c74eab0d728502f2740030a9965e85fcb81a4d3d`
- `HEAD` und `origin/master` müssen vor jeder Aussage über „online“ verglichen werden.
- Maßgeblich ist der echte Windows-Checkout und die daraus gestartete EXE, nicht ein temporärer Klon, ein alter ZIP-Stand oder ein verschachtelter Build-Ordner.

## Was im Verlauf wiederholt schiefging

### 1. Falscher oder veralteter Build wurde geprüft

Mehrfach war die sichtbare Anwendung nicht der gerade geprüfte Quellstand: alte EXE, verschachteltes `dist\DebateAI\DebateAI`, laufende Vorgängerprozesse und gesperrte Dateien führten zu widersprüchlichen Bildern. Ein erfolgreicher Quelltest beweist deshalb nicht, dass die laufende GUI diesen Quellstand verwendet.

**Regel:** Vor einem GUI-Test immer absolute EXE, PID, Startzeit und Build-Hash ausgeben. Nur einen eigenen Vorgängerprozess über den normalen Tray-/Quit-Weg beenden. Nie `git clean -fdx` oder pauschales Löschen von AppData verwenden.

### 2. Testlabor war in der GUI nicht erreichbar

Der lokale RequestGuard erlaubte zunächst nur `/`, `/assets/*` und das Favicon. `/calibration.html`, die Labor-Assets, Icons und das Manifest wurden deshalb mit `403` blockiert. Das Labor war im Frontend vorhanden, aber der Desktop-Webview konnte die Einstiegsseite nicht laden.

**Fix:** Desktop-Bootstrap-Allowlist um `/calibration.html`, `/calibration/`, `/icons/` und `/manifest.webmanifest` erweitert; Regressionstest ergänzt. Commit: `c04335b4`.

### 3. Testlabor lud, meldete aber „Backend nicht verbunden“

Das Labor rief `/api/calibration/catalog` und weitere APIs aus dem eingebetteten Webview auf. Der Desktop-Backend-Schutz verlangt eine instanzgebundene Berechtigung. `/api/meta` lieferte zwar den Header `X-DebateAI-Instance`, aber konkurrierende Webview-Requests verloren den Header bzw. waren schneller als der Bootstrap. Dadurch erschienen `403` bei Catalog, Sessions, Models und Privacy, obwohl ein manueller Request mit demselben Token funktionierte.

**Fix:** Gemeinsamer Session-Bootstrap in `source/frontend/public/calibration/session.mjs` und `source/frontend/src/services/api.ts`, konkurrierende Requests werden geteilt, fehlgeschlagener Bootstrap kann erneut versucht werden. Zusätzlich stellt `/api/meta` nun einen same-origin-HttpOnly-Cookie bereit; der RequestGuard akzeptiert Header oder Cookie. Tests prüfen Parallelität, Retry und Cookie-Autorisierung. Commit: `acd53c88` (Session-Client) und `c74eab0d` (Cookie-Fallback).

**Diagnose zuerst:** Status von `/api/meta`, `Set-Cookie` und `X-DebateAI-Instance` prüfen; danach Catalog einmal mit Header und einmal mit Cookie testen. Nicht aus einem sichtbaren „Backend nicht verbunden“ sofort auf einen fehlenden Backend-Prozess schließen.

### 4. Tray-Symbol fehlte trotz laufender Anwendung

Der eigene `pystray`-Setup-Callback ersetzte die Standard-Sichtbarkeitslogik. Das Fenster lief, aber das Symbol wurde nicht sichtbar registriert.

**Fix:** Nach dem Initial-Window-Setup wird `_icon.visible = True` explizit gesetzt; Desktop-Regressionstest ergänzt. Commit: `acd53c88`.

### 5. PostgreSQL-Port war offen, Datenbank aber noch nicht bereit

Der Startcode akzeptierte einen offenen Port zu früh. Während der Recovery meldete PostgreSQL noch `database system is not yet accepting connections`; wenige Millisekunden später war der Dienst bereit. Das erzeugte scheinbar zufällige Alembic-/Backend-Startfehler.

**Fix:** `_wait_for_postgres` akzeptiert den Dienst erst, wenn PID-Datei und Statuszeile den Zustand `ready` zeigen und die PID zum Prozess passt. Commit: `1a7375b9`.

### 6. Eingebettete PostgreSQL- und Legacy-Backchannel-Zustände

Die lokale Installation enthielt alte Backchannel-Pfade, fehlende Zeitzonendateien, fehlende `psql`-Hilfsprogramme, alte Rollenmarker und Schema-Zwischenstände. Zusätzlich war eine Alembic-Spalte für den Rollenmarker zu kurz.

**Regel:** Legacy-Daten nach `%LOCALAPPDATA%\DebateAI` migrieren, Quelle behalten, DPAPI/master.key, Sessions, Browserprofile, Cookies, Modelle, Transkripte, `.env` und Playbooks bewahren. Binär-Rollback ist kein Datenbank-Rollback; laufende PostgreSQL-Dateien niemals als konsistentes Backup kopieren.

### 7. Launcher-Logging scheiterte in restriktiven Temp-Verzeichnissen

PyInstaller/Windows konnte den automatisch gewählten Temp-Logpfad mit `PermissionError: [Errno 13]` nicht öffnen. Das verdeckte den eigentlichen Startfehler durch einen zweiten Fehler.

**Fix:** Launcher-Logging hat einen kontrollierten, beschreibbaren Fallback und meldet den Pfad nachvollziehbar. Commit: `73314051`.

### 8. Build-/Archiv- und Dateisperren

`Compress-Archive` konnte bei großen oder gesperrten Bundles hängen. Ein laufender Desktopprozess hielt Programmdateien offen. Die verwendete Lösung ist Geschwister-Staging auf demselben Dateisystem, kontrolliertes Beenden des eigenen Prozesses, Archivierung mit vorhandenem nativen Tar-Weg und anschließende ZIP-/Entpack-Prüfung.

**Regel:** Erst neues Staging und Smoke-Tests validieren, dann alte funktionierende Programmdateien als Rollback behalten und nur Programmdateien austauschen. Keine erzwungene Löschung und kein Force-Push.

### 9. „Grüne“ Tests wurden falsch interpretiert

Ein Mock-, Headless- oder Linux-Lauf beweist weder Windows-WebView2, echtes Tray, Mikrofon, Systemaudio, PostgreSQL-Recovery noch echte Provider-Logins. Ebenso beweist ein Quelltest nicht, dass die gestartete EXE neu gebaut wurde.

**Regel:** Automatisierte Tests, Paket-Smoke, echte Windows-GUI, Hardware und Account-/Provider-Gates getrennt ausweisen. Unbewertete Nenner und Timeouts ehrlich behalten.

### 10. Runtime-Artefakte wurden mit Quellcode verwechselt

Builds, Modelle, Bridge-EXEs, Node-Runtime, Logs, Testdaten und lokale Datenbanken erscheinen als untracked/runtime state. Sie gehören nicht in Git und dürfen nicht als „fehlende Änderungen“ blind hinzugefügt oder gelöscht werden.

## Nachgewiesene Korrekturen und Prüfungen

- Frontend-Build und Frontend-Suite: `327` Tests bestanden.
- Desktop-Suite nach PostgreSQL-Recovery-Fix: `211` Tests, `OK (skipped=1)`.
- RequestGuard-Suite inklusive Cookie-/Allowlist-Regressions: `32` Tests bestanden.
- Session-Client-Fokustests: `2/2` bestanden.
- Vorherige Paket-Smokes: lokaler ASR, Labor-Assets/authentifizierter Catalog und sauberer Shutdown bestanden.
- Native Windows-Archiv-/Rollback-Smoke bestanden.
- `git diff --check` war für den veröffentlichten Stand sauber.

Diese Zahlen sind Testevidenz für die jeweiligen Schichten; sie ersetzen nicht den abschließenden Test mit der exakt gebauten und gestarteten EXE.

## Diagnose-Reihenfolge für die Browser-KI

1. `git rev-parse HEAD`, `git rev-parse origin/master`, Branch, Remote und absolute Checkout-Wurzel prüfen.
2. Laufende DebateAI-PIDs, absolute EXE-Pfade, Startzeiten und Logpfade erfassen. Keine alte EXE mit einer neuen Source-Messung vermischen.
3. Nur den eigenen Prozess kontrolliert über Tray/Quit beenden; aktive Debatten erst auslaufen lassen.
4. `/api/meta` prüfen: HTTP-Status, `X-DebateAI-Instance` nur als Länge/Existenz protokollieren, niemals den Tokenwert loggen, und `Set-Cookie` auf Vorhandensein prüfen.
5. `/api/calibration/catalog` mit derselben Session als Header und als Cookie prüfen. `403` bedeutet zuerst Session-/Webview-Transportproblem, nicht automatisch Backend-Ausfall.
6. Danach `/api/sessions`, `/api/models`, `/api/privacy` und Health/DB-Recovery prüfen. Bei PostgreSQL auf „Port offen“ gegen „ready“ unterscheiden.
7. Im GUI verifizieren: Hauptfenster, Testlabor, Navigation, Laborstatus ohne Backend-Warnung und Tray-Symbol. Bei einem Fehler Screenshot plus absolute Build-ID und Logzeilen sichern.
8. Exakte Bundle-Inhalte prüfen: `calibration.html`, `calibration/session.mjs`, Icons, Manifest, Backend-Routen, Playbooks und Live-/Deep-Prompts.
9. Geänderten Quellstand testen, committen, mit aktuellem Remote abgleichen, ohne Force pushen, danach exakt diesen Stand bauen und ZIP/Entpack-Smoke ausführen.

## Harte Sicherheits- und Erhaltungsregeln

- Keine Secrets, Cookies, OAuth-Dateien, Browserprofile, DPAPI-Schlüssel, Datenbanken, Logs oder Modellgewichte committen.
- Keine privaten Browser-Cookies extrahieren oder Provider-Logins automatisieren; Login bleibt sichtbare Nutzeraktion.
- Keine Daten in `%LOCALAPPDATA%\Backchannel` oder `%LOCALAPPDATA%\DebateAI` löschen, solange Migration und kontrolliertes Backup nicht validiert sind.
- Kein `git clean -fdx`, kein `reset --hard`, kein Force-Push und keine Schutzumgehung.
- „Online“ darf nur behauptet werden, wenn `HEAD == origin/master` nach dem Push nachweisbar ist. „Behoben“ darf nur behauptet werden, wenn die exakt gestartete EXE den relevanten GUI-/API-Test bestanden hat.

## Offene bzw. manuelle Gates

Echte Windows-WebView2-/DPI-/Tray-/Mikrofon-/Systemaudio-Abnahme, reale deutsche Sprachmessungen, Ollama-/ChatGPT-/Gemini-Verfügbarkeit, Authenticode-Signatur und Release-Publikation bleiben getrennte Betreiber- bzw. Hardware-Gates. Ein fehlender Provider-Schlüssel darf nicht als interner Codefehler und ein Mock-Ergebnis nicht als reale Modellmessung ausgegeben werden.

## Historischer Paket-Smoke-Blocker (13.11.2026, im neuen Stand nicht reproduziert)

Der erneute Smoke gegen `source/dist/DebateAI` wurde in einem kontrollierten Workspace-Temp-Verzeichnis gestartet. Der Testcontainer-TEMP selbst scheiterte separat mit `WinError 5` beim Aufräumen; im Workspace-TEMP kam der Prozess bis zum eingebetteten PostgreSQL-Start. Das PostgreSQL-Log enthält:

`listening on IPv4 address "127.0.0.1"` und `database system is ready to accept connections`

Der Launcher meldete damals trotzdem nach dem Timeout `postgres start failed` und beendete die Instanz. Der inzwischen geholte `31e42382`-Stand enthaelt weitere Windows-PID-/Ready-Fixes. Beim echten Neubau mit Python 3.12.10 sind Bundle-Smoke und nativer Archiv-/Forced-Rollback-Smoke gruen; auch die Bestandsdatenbank startete. Dieser historische Fehler ist daher kein aktuell nachgewiesener Paketblocker mehr. Bei Wiederauftreten die echte PID-Zuordnung des direkt gestarteten `postgres.exe`, `postmaster.pid` und `process.poll()` pruefen, nicht den alten Fehlertext als neue Diagnose uebernehmen.

## Nachtrag: nachgewiesene Webview-Ursache und Fix d8f6482b

Der Cookie-Fallback allein erklaerte den echten Browserfehler nicht vollstaendig. Uvicorn und der RequestGuard senden den Instanzheader beide. Browser-/Node-Fetch fasst identische Werte als `token, token` zusammen; der Session-Client schickte diese Liste statt eines einzelnen Tokens weiter. Der RequestGuard bevorzugt den expliziten Header vor dem Cookie und wies ihn korrekt mit 403 ab. Python-urllib las nur den ersten Headerwert und maskierte damit den Fehler im alten Smoke.

`frontend/public/calibration/session.mjs` normalisiert jetzt ausschliesslich identische wiederholte Headerwerte. Widerspruechliche Werte blockieren die geschuetzte Anfrage. Kein Host-/Origin-/Token-Guard wurde abgeschwaecht. Zwei zusaetzliche echte Headers/Response-Regressionsfaelle waren vor dem Fix rot; danach Frontend 329/329 gruen. Derselbe Session-Client liefert gegen die reale Windows-EXE beim ersten Aufruf fuer Catalog, Sessions und Privacy jeweils 200.

Fuer Browserdiagnosen deshalb immer Fetch-Headersemantik pruefen und nicht nur einen Python-Request als Browserbeweis ausgeben. Nur Anzahl und Gleichheit von Headerwerten protokollieren, nie Tokenwerte. Tray-Registrierung ist ebenfalls nativ bestaetigt: genau ein Symbol. Der lokale Shell-Pruefhelfer musste uID=0 verwenden, passend zum Verhalten der installierten pystray-Fassung; ein falscher Pruefhelfer darf keinen neuen Produktfix ausloesen.

Aktuelle automatische Evidenz: Backend 1881 Tests (4 Skips), Desktop 213 (1 Skip), Frontend 329, PWA 5. Workspace-Scripts: 25 Tests mit zwei Windows-Umgebungsfehlern (ungueltiger Newline-Dateiname und fehlendes Symlinkrecht), nicht als vollstaendig bestanden melden. Reale Mikrofon-/Systemaudio-/Provider-/Human-/Signaturabnahme bleibt separat.

Finaler lokaler Kandidat: Runtime `d8f6482baa5d3fa0ee000017c6c8830cd590532f`, installiert unter `C:\Users\User\Datein\Coding\DebateAI\source\dist\DebateAI\DebateAI.exe`. ZIP 434543711 Bytes, SHA256 `E88ADDC4DE38C649C9BFA8335EC3CD86E313B97770DE57777F8596FADA47D5F6`; erneuter Bundle- und nativer Archiv-/Rollback-Smoke gruen. Neuer echter Besitzer PID 38400; Health-Token, Catalog/Sessions/Privacy 200, sechs Sessions, 15 aktive Playbooks und ein Shell-Trayicon nachgewiesen. Vor dem Start kalter Datenbackup mit 1269 hashvalidierten Dateien ausserhalb Git, binaerer Rueckweg separat erhalten. Kein signierter Produktionsrelease (`NotSigned`). Die bestehende Gemini-Web-Sitzung ist nicht ready und verzoegert den Start um rund 85 Sekunden. Ein einzelner Tray-Update-Statusrequest liefert beim Start noch 403; nicht mit den nun erfolgreichen Hauptfenster-/Laborrequests verwechseln. Alle 15 Runtime-Gates samt Grenzen stehen im neuesten Abschnitt von `.ai/DEBATE_AI_OPTIMIERUNG.md`.

## Neuer installierter Startfix `144302d5`

Der vorherige Startfehler ist reproduziert und behoben: Optionale Provider-/Gemini-Katalogerkennung blockierte den Backend-Lifespan vor dem lokalen `yield`. Seit `144302d59f9f737dc4b10214b7562efa676461e5` laeuft sie getrennt im Hintergrund und blockiert weder lokale DB-Bereitschaft noch die Testlabor-APIs.

- Neue EXE PID `32808` aus `source/dist/DebateAI/DebateAI.exe`.
- Tokengebundene `/api/ready`-Antwort nach `20,03 s` gegen das vorhandene Nutzerprofil.
- `/api/sessions` `200` mit 6 Sitzungen; `/api/calibration/catalog` `200` mit 3 Modellen.
- Subscription-Bridge startete mit 22 Modellen; lokaler Qwen-Warmup bereit.
- ZIP: 467187101 Bytes, SHA-256 `2913B484A04799DA6060AAC2C3DB5E43B8485D184838EC67A952497A4D94F0F7`.
- Bundle-Smoke und nativer Update-/Forced-Rollback-Smoke bestanden; ZIP-CRC und Bundlewurzel geprueft.
- Regressionen: Backend 1885 OK (4 Skips), Desktop 213 OK (1 Skip), Startup-/Schema-/Bridge-Fokus 32 OK.

Der fuenfminuetige Referenztext ist noch kein Bestandteil des Produkts. Das Labor akzeptiert aktuell maximal 30 Sekunden pro Clip; Aufnahme am Stueck versus mehrere kurze Abschnitte muss vor einer Erweiterung entschieden werden. Ein separater `/api/updates`-403 bleibt offen und ist nicht mit dem nun funktionierenden Hauptfenster-/Labor-Sessionpfad gleichzusetzen.
