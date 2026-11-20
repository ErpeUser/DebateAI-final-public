# DebateAI – Produktvision

**Stand:** 19.11.2026 · **Status:** vom Projekteigentümer anhand von 50 Entscheidungsfragen und Freitext-Ergänzungen präzisiertes **Produktziel**, nicht Aussage über den aktuellen Fertigstellungsgrad.

**Leseregel:** Festgelegte Ziele haben Vorrang vor älteren Konzepten. Noch nicht entschiedene Alternativen stehen jeweils unmittelbar unter dem betroffenen Thema oder gesammelt am Ende; frühere Produktlinien sind ausdrücklich als historisch/optional gekennzeichnet. Implementiert, getestet, veröffentlicht und abgenommen sind unterschiedliche Zustände.

## 1. Leitbild und Zielgruppe

**DebateAI soll der beste persönliche Echtzeit-Debatten-Copilot werden.** Die Anwendung hört einer laufenden, insbesondere kontroversen Diskussion zu, versteht die argumentative Situation und liefert genau dann die rhetorisch stärksten, sofort aussprechbaren Reaktionen, wenn der Nutzer sie braucht. Sie soll ihm helfen, Widersprüche aufzudecken, Behauptungen zu hinterfragen, eigene Positionen zu verteidigen und überzeugender zu argumentieren. **Der Mensch entscheidet selbst, was er sagt; DebateAI spricht nicht autonom an seiner Stelle.**

Erste Kernzielgruppen sind **Privatpersonen sowie Debattierer, Studierende und Rhetorik-Interessierte**. Das wichtigste V1-Szenario ist ein **kontroverser Videocall**; persönliche Gespräche und nachträgliche Analysen sind nachgeordnet. Das Produkt ist zunächst bewusst **für eine einzelne Person**, nicht für Team-Workspaces, optimiert.

Der entscheidende Aha-Moment ist eine **brillante, sofort nutzbare Erwiderung**. Erfolg bedeutet nicht möglichst viel KI-Text, sondern dass Vorschläge **nachweislich häufiger helfen**: Sie sind rechtzeitig, sprechbar, situativ treffend, überzeugend und sachlich vertretbar.

Langfristig bleibt DebateAI eine **modulare Plattform für Rhetorik, Gesprächsanalyse und KI-Forschung** – aber alle Erweiterungen müssen den Echtzeit-Debattenkern unterstützen, nicht verdrängen.

## 2. Das Live-Erlebnis als Hauptprodukt

Nach einem geführten Starttest für Audio, Hardware, lokale Modelle und Datenflüsse startet der Nutzer eine Sitzung. Mikrofon und Systemaudio laufen als getrennte Quellen. Die Anwendung ordnet Sprecher in Echtzeit zu, führt das Gesprächsprotokoll fort und erstellt ununterbrochen Vorschläge.

**Zwei logisch getrennte, durchgehend aktive Agentenrollen** arbeiten zusammen:

1. **Argument-Agent:** Er bewertet die gerade gesprochene Aussage, ihre Prämissen, Schlussfolgerungen, möglichen Fehler, Beweislast und unmittelbar passenden Gegenreaktionen.
2. **Strategie-Agent:** Er verfolgt die bisherige Sitzung, Positionen, bereits gegebene Antworten, wiederkehrende Argumentationsmuster, Widersprüche, Doppelstandards, Dilemmata und den nächsten taktisch sinnvollen Gesprächsschritt.

Beide Rollen dürfen parallel arbeiten, müssen aber auf denselben aktuellen Sprecher-/Kontextstand bezogen sein und dürfen einander nicht mit widersprüchlichen oder überholten Ergebnissen überschreiben. **Zwei Rollen sind eine fachliche Anforderung, keine zwingende Vorgabe für zwei getrennte Modelle oder Prozesse.** Die konkrete Orchestrierung muss den Latenz- und Qualitätszielen standhalten.

Der Live-Modus zeigt **drei kurze, unterschiedliche und möglichst direkt aussprechbare Alternativen**. Mindestens eine soll eine konkrete verwendbare Formulierung bieten; passende Alternativen können Gegenfrage, Einwand, Beispiel oder strategische Gesprächsbewegung sein. Empfehlungen werden **laufend** aktualisiert und auch während der eigenen Rede angezeigt, wenn ein wichtiger Fehler oder eine neue Chance erkannt wird. Der Nutzer muss dabei ohne Umwege selbst entscheiden können, ob er die Hilfe aufgreift.

**Frühe, revidierbare Vorschläge sind gewollt:** Die KI darf auf unvollständige Transkripte reagieren, kennzeichnet Unsicherheit aber passend. Korrigiert die ASR ihren Wortlaut, muss die sichtbare Empfehlung ebenfalls überarbeitet werden. Durch neue Aussagen überholte Karten dürfen nicht als aktuell weitergelten; sie werden sichtbar als **„veraltet“** markiert. Neue Ergebnisse tragen erkennbaren Sitzungs-/Turn-Bezug.

**Ambitionierte Zielzeit:** Eine erste brauchbare Reaktion soll auf der definierten Windows-Zielhardware nach Möglichkeit innerhalb von **1 bis 2,5 Sekunden** erscheinen. Das ist ein zu messendes Ziel, kein bereits belegter SLA. Rechenintensive Nebenaufgaben dürfen die erste Reaktion nicht blockieren.

Bei Modell- oder Provider-Ausfall zeigt DebateAI **einen klaren Fehlerstatus und keine neue, vermeintlich intelligente Ersatzantwort**. Bereits angezeigte Vorschläge behalten ihren zeitlichen/inhaltlichen Status.

## 3. Rhetorik: zwei zentrale Modi

Die Rhetorik ist kein generischer Chatbot-Stil, sondern eine strategische Entscheidung anhand von Diskussion, Gegenüber, eigener Position und Modus.

### Modus „Knallhart“

Ziel ist **maximale argumentative Konfrontation**: unhaltbare Aussagen bloßstellen, Doppelstandards aufdecken, Widersprüche zuspitzen, gegnerische Prämissen umdrehen und durch präzise Rückfragen argumentative Auswege verengen. Pointierte, sehr scharfe, auch provokante Formulierungen sind ausdrücklich erwünscht. Das System soll nicht unnötig weichzeichnen.

Dazu gehören **konkrete, an den Gesprächsverlauf angepasste Szenarien**: etwa dieselbe moralische Regel auf vertauschte politische oder soziale Rollen anwenden und fragen, ob das Gegenüber den Maßstab dann weiterhin akzeptieren würde. Solche Rollentausche sind klar **hypothetische Fragen**, keine erfundenen Tatsachen. „Hart wie möglich“ bezieht sich auf argumentative Wirksamkeit, nicht auf Drohungen, Aufrufe zu Gewalt oder frei erfundene Vorwürfe.

### Modus „Überzeugend“

Ziel ist **maximale tatsächliche Überzeugungswirkung**. DebateAI soll verständliche Beispiele, relevante gemeinsame Ausgangspunkte, präzise Sprache, Einwände des Gegenübers und psychologisch nachvollziehbare Gesprächsführung verbinden. Der Modus kann eine harte Gegenposition ruhig formulieren, eine taktisch hilfreiche Frage stellen oder den besten Zeitpunkt für einen Perspektivwechsel erkennen.

### Umgang mit eigener Schwäche im Gespräch

Wenn die KI merkt, dass **der Nutzer selbst** einen Denkfehler gemacht hat, soll sie nicht einfach seine Position aufgeben. Sie versucht zunächst, den **vertretbaren Kern** der Position zu retten: durch eine engere Definition, ein korrektes Beispiel, eine legitime Differenzierung, einen Wechsel zur überprüfbaren Grundfrage oder eine taktische Gegenfrage. Sie darf den Nutzer auch auf einen substanziellen Fehler hinweisen. **Ein falscher Fakt wird dabei nicht als wahr verteidigt; eine Ausweichstrategie wird nicht als Beleg ausgegeben.**

### Wahrheit und Belege

**Nur überprüfte Tatsachen werden als gesichert dargestellt.** Bei einer unbelegten, aber rhetorisch starken Erwiderung wird die Behauptung entweder als ungeprüft markiert, durch eine ehrliche hypothetische Annahme ersetzt oder in eine kritische Frage umgewandelt. Erfundene Studien, Zitate und Quellen sind ausgeschlossen.

Trägt das Gegenüber eine fragwürdige Zahl vor, darf DebateAI zuerst die **Logik des Schlusses unabhängig von der Zahl** angreifen: Was folgt daraus überhaupt? Welche Prämisse fehlt? Wird ein anderer Maßstab angelegt? Ein Faktencheck ergänzt diese Analyse später.

**Noch offen:** Welcher Modus nach Installation startet (Knallhart oder explizite Wahl), welche Abstufungen die maximale Schärfe erhalten und wie stark sehr persönliche Angriffe in der UI begrenzt werden. Diese Details sind nicht durch die Antwort „hart wie möglich“ abschließend spezifiziert.

## 4. Recherche, Belegfluss und Reaktionsgeschwindigkeit

Die **erste nutzbare Erwiderung gewinnt zeitlich vor der vollständigen Quellenprüfung**. Sie kann eine klar erkennbare ungeprüfte Argumentationslinie enthalten, darf aber keine ungeprüften Angaben als feststehende Fakten verkaufen.

Sobald der Nutzer **externe Recherche aktiviert** hat, darf sie **kontinuierlich im Hintergrund** laufen, ohne für jede Suche erneut zu fragen. Treffer werden bewertet und – sobald belastbar – als **kurze, direkt verwendbare Aussage mit Quelllink** in die laufende Sitzung eingebracht. Später eintreffende Belege dürfen Vorschläge verbessern, korrigieren oder widerlegen; bereits veraltete Vorschläge müssen entsprechend gekennzeichnet bleiben.

Das System denkt **strategisch über den Gesprächsverlauf**: Es soll nicht nur den letzten Satz beantworten, sondern anhand der aktuellen Argumente und der in dieser Sitzung erkannten Argumentationsmuster entscheiden, ob direkte Widerlegung, Gegenfrage, hypothetischer Rollentausch, Dilemma, Klärung der Definition oder Abwarten die beste nächste Bewegung ist.

Tiefenanalyse, Webrecherche, Quellenextraktion und experimentelle Mehrschrittverfahren laufen in getrennten, begrenzten Ressourcenbudgets. Sie dürfen die lokale ASR und die schnelle Antwortgenerierung nicht spürbar verdrängen.

## 5. Sprache, Audio und Sprecherverständnis

**Deutsch ist die einzige offiziell unterstützte V1-Sprache.** Hohe Qualität für natürlich gesprochenes Deutsch, Zahlen, Eigennamen, Korrekturen und kontroverse Gesprächsdynamik hat Vorrang vor einer breiten, aber unausgereiften Sprachliste.

**Mikrofon und Systemaudio als getrennte Spuren** sind unverzichtbar. Audio-Capture, Zeitstempel, Gerätauswahl/-wechsel, Ausfälle und Wiederanlauf müssen stabil funktionieren. 16-kHz-PCM-kompatible Verarbeitung und lokal verfügbare Whisper-/Parakeet- oder gleichwertige ASR-Wege bleiben technische Optionen, keine pauschalen Genauigkeitsversprechen.

**Live-Sprecherzuordnung ist eine V1-Pflichtanforderung.** Die KI muss unterscheiden können, welche Aussage vom Nutzer und welche vom Gegenüber stammt; Fehler und Unsicherheit dürfen die strategische Einordnung nicht unsichtbar verfälschen. ASR-Revisionen und Diarisierungskorrekturen propagieren in Argumentgedächtnis und Antwortkarten.

**Historische Alternative – Mehrsprachigkeit:** Release-Notes v0.6.6 beschrieben Auto-Detect/mehrsprachige Spracherkennung; Teile der aktuellen Konfiguration bevorzugen dagegen „de“. Mehrsprachigkeit bleibt ein späterer möglicher Ausbau, **nicht** der erklärte V1-Produktvertrag. Die tatsächliche Windows-Mikrofon-/WASAPI-/Loopback-Qualität ist vor einer Freigabe zu messen.

## 6. Modelle und Ausführung: lokaler Live-Kern, optionale Cloud-Tiefe

Der gewünschte Standard ist **Hybrid mit klarem Local-First-Vorrang**:

- **Latenzkritischer Pfad:** lokale Spracherkennung und ein lokal laufendes Textmodell (etwa Ollama/Qwen oder ein geeigneter kompatibler Endpunkt) erzeugen die unmittelbare Hilfe.
- **Zusatzpfad:** nach Aktivierung dürfen Cloudmodelle, spezialisierte Provider und Webrecherche zusätzliche Kontext- und Beleganalyse liefern. Sie ersetzen nicht stillschweigend den lokalen Live-Pfad und blockieren seine erste Antwort nicht.
- **Einrichtung:** Ein Assistent prüft vor der ersten echten Sitzung Prozessor/GPU/RAM, Audio-Geräte, vorhandene ASR-/Textmodelle, Modellkompatibilität und die gewählten Datenflüsse. Fehlende oder ungeeignete lokale Modelle werden verständlich erklärt; Downloads und Provider-Nutzung sollen sichtbar konfigurierbar sein.

**Einmalige bewusste Aktivierung statt Popup-Flut:** Ist eine externe Verarbeitung mit Anbieter, Umfang und Kostenrahmen eingerichtet, soll sie ohne weitere Einzelbestätigung für jeden Aufruf funktionieren. Ohne Aktivierung keine überraschende Cloud-Übertragung. Der Wunsch nach reibungslosem Betrieb setzt keine Rechts- oder Aufnahmeregel außer Kraft.

**Historische/optionale Alternativen:** Ein vollständig lokaler bzw. LAN-basierter Betrieb bleibt wichtig; ein frei kombinierbarer Mehrproviderbetrieb für die ältere Meeting-Analyse bleibt möglich. Weder die Website noch die Vision dürfen behaupten, jede vorhandene Funktion – insbesondere Dokument-Summarization oder experimentelle Live-Captions – arbeite schon nachweisbar vollständig lokal. Bei einzelnen Dokumentpfaden existieren Gemini-Files-API-Abhängigkeiten.

**Noch offen:** verbindliche V1-Provider-/Modellmatrix, konkrete Hardware-Mindestwerte, Freigabeumfang externer Transkriptausschnitte und die Wahl zwischen lokaler Schutzoption und automatischer Bereinigung vor externen Aufrufen. PII Shield ist im privaten lokalen Standardbetrieb auf Eigentümerwunsch **aus**, nicht pauschal für jeden denkbaren Einsatz abgeschafft.

## 7. Hauptoberfläche und Einrichtung

Das Hauptprodukt ist eine **eigenständige, umfangreiche Windows-Desktop-Oberfläche**, deren **Analyse-Dashboard im Vordergrund** stehen darf. Eine reine Text-Minimalanzeige oder ein schmales Overlay ist höchstens eine **optionale** Ansicht, nicht das zentrale Produktversprechen. Empfehlungen werden **als Text** ausgegeben; automatische KI-Stimme oder autonomes Mitsprechen gehören nicht zum Zielbetrieb.

Die Live-Ansicht soll den aktuellen Gesprächsstand, **drei schnell lesbare Reaktionsvorschläge**, deren Aktualität, Sprecherzuordnung, Argumentationsmuster, strategische Hinweise und nachgelieferte Belege verständlich zusammenführen. Tiefergehende Analyse darf umfangreich sein, muss aber die unmittelbare Antwort unterscheidbar halten.

Die Einrichtung führt durch **Mikrofon, Systemaudio, Modellverfügbarkeit, Leistung und Daten-/Providerwahl**. Im Alltag ist die Oberfläche einfach; ein **Expertenmodus** erschließt Prompts, Modelle, Agentenrollen, Strategien und feinere Einstellungen.

**Offene UX-Abwägung:** Ein großes Dashboard und ein gleichzeitig sichtbarer Videocall konkurrieren um Bildschirmplatz. Ob andockbare Panels, zweiter Monitor oder ein optionaler Kompaktmodus dieses Problem lösen, wird über reale Nutzungstests entschieden; nicht durch eine ungefragte Umdeutung des gewählten Dashboards zu einem Minimal-Overlay.

## 8. A/B-, Sprach- und Strategielabor als Kernfeature

Das **Modell-/Prompt-A/B-Labor ist für alle Nutzer ein zentrales Produktfeature**, nicht lediglich ein verstecktes Entwicklerwerkzeug. Es vergleicht bei **identischer These, eigener Position, Sitzungssituation und Stilvorgabe** tatsächlich verfügbare Prompt-/Modellvarianten. Antworten A/B werden vor einer Bewertung **blind** und mit wechselnder Reihenfolge gezeigt; anschließend werden Modelle, Promptversion, Latenz, Kontext und mögliche Kosten aufgedeckt.

Bewertet werden mindestens **Sprechbarkeit, Natürlichkeit, Reaktionsgeschwindigkeit, argumentative Stärke, situativer Nutzen, Gegenfrage und Quellenredlichkeit**. Der Nutzer soll sehen, welche Strategie im realen Debattenkontext gewinnt. **Kein automatischer Gewinnerwechsel im Livebetrieb**: getestete Einstellungen werden bewusst übernommen und können rückgängig gemacht werden. Kein synchroner LLM-Judge auf dem zeitkritischen Pfad.

Ein **Sprachlabor** vergleicht Modelle fair anhand derselben Aufnahme und einer editierbaren deutschen Referenz, mit WER/CER, RTF, Laufzeit und Fehlerfällen. Laborläufe dürfen den aktiven Livebetrieb nicht lahmlegen. Unabhängige menschliche Bewertungen, Abgrenzung von Trainings-/Testfällen und Wiederholbarkeit sind erforderlich, bevor Qualitätsvorsprünge öffentlich behauptet werden.

## 9. Sitzungsdaten, Privatsphäre und Einwilligung

Die erste Version ist ein **privat genutztes, lokal priorisiertes Einzelplatzprodukt**. Datenschutzkomfort darf die Live-Funktion nicht unnötig verkomplizieren; gleichzeitig bleiben technische Sicherheit, zulässige Aufnahmen und nachvollziehbare externe Datenflüsse verbindliche Grenzen.

- **Offene KI-Nutzung:** DebateAI ist für Situationen vorgesehen, in denen der Einsatz von KI-Unterstützung offen ist. Für Gesprächsaufnahmen gelten je nach Kontext unterschiedliche Regeln; erforderliche Einwilligung wird nicht durch den privaten Nutzungszweck ersetzt.
- **PII Shield:** Im lokalen Privatbetrieb standardmäßig **deaktiviert**. Für Cloudverarbeitung bleibt eine klar erkennbare, bewusst auswählbare Schutzfunktion möglich; sie muss nicht zwangsläufig jeden lokalen Verarbeitungsschritt verlangsamen.
- **Cloudfreigabe:** Eine konfigurierte und aktivierte externe Route darf anschließend ohne wiederkehrende Unterbrechung genutzt werden. Anbieter, übermittelte Datenarten und mögliche Kosten müssen vor der erstmaligen Einrichtung transparent sein.
- **Rohaufnahme:** Audio wird nur so lange vorgehalten, wie es für die jeweilige Verarbeitung erforderlich ist; nach abgeschlossener Verarbeitung und gegebenenfalls einem **vom Nutzer ausdrücklich gestarteten** Trainingslauf wird es gelöscht. Ein stilles, allgemeines Modelltraining wird daraus nicht abgeleitet.
- **Dauerhafte Nutzdaten:** **Transkripte und extrahierte Argumente bleiben lokal erhalten**, bis der Nutzer sie löscht. Sie fallen gerade **nicht** unter eine pauschale kurze automatische Löschfrist. Optional ist ein verschlüsseltes Backup; Standard bleibt die effiziente lokale Speicherung.
- **Updates:** Datenbanken, Argumentgedächtnis, persönliche Prompts/Playbooks, Modelle, Profile, Schlüssel und Sitzungsdaten dürfen durch App-Updates und Rollbacks nicht versehentlich gelöscht oder überschrieben werden. Absichtlich gelöschtes Audio darf durch Backup-/Update-Routinen nicht ungewollt wieder auftauchen.

**Noch offen:** genaue Aufzeichnungsregeln je Einsatzkontext, Aufbewahrung von Zwischenspeichern/Backups, Anbieter- und Datenklassenfreigaben, konkrete PII-Shield-Grenzen und ob überhaupt persönliches Modelltraining als Produktfunktion angeboten wird.

## 10. Funktionsumfang und langfristige Ausbaulinien

Der erste ernsthafte Release soll ein **integriertes Gesamtprodukt** mit einem vollständigen, belastbaren **Echtzeit-Debattenkern** sein – **kein bloßer Textchat-Prototyp**. Dazu gehören die fortlaufenden Agentenrollen, deutschsprachige Live-Audioverarbeitung, Sprechertrennung, drei aktuelle Reaktionskarten, zwei Rhetorikmodi, das Dashboard, Modell-/Hardware-Setup und das zugängliche A/B-Labor. Entscheidend ist, dass diese Kernfunktionen **wirklich verlässlich** sind.

Die bereits entwickelte **allgemeine Meeting-Analyse** bleibt als **eigener optionaler Bereich** bestehen: strukturierte Transkripte, Beobachtungen, Briefings, Fragen, Nachanalysen und Sitzungsabfragen können weiter genutzt und verbessert werden, sind aber **nicht** die primäre Identität oder das Leitszenario.

**Videoanalyse und experimentelle Vier-Move-/Mehragentensysteme** sind eine wichtige **langfristige Differenzierung**. Sie sollen strategische Szenarien, Evidenzpakete und tiefere Rhetorikanalyse ermöglichen, dürfen aber erst nach Messung von Qualität, Latenz und echtem Zusatznutzen als ausgereifte Produktfunktion gelten. Bestehende experimentelle Implementierungen sind kein Releasebeweis.

**Keine vorrangige Integrations-Offensive:** Kalender-, CRM-, Videocall- oder Fremd-API-Integrationen werden erst nach der Perfektionierung des Kerns priorisiert. Kein Team-Workspace-Zwang, kein Kontozwang allein zur lokalen Nutzung.

**Offener Zielkonflikt:** „Integriertes Gesamtprodukt“ bedeutet nicht automatisch, dass jede historische Meeting-, Video- und Forschungsfunktion zum ersten Release vollständig abgenommen sein muss. Die genaue Pflicht-/Optional-/Experimentell-Matrix bleibt vor der Freigabe ausdrücklich zu entscheiden; die Funktionsbreite darf fehlende Zuverlässigkeit nicht verdecken.

## 11. Windows, Distribution und Open Source

**Windows-Desktop hat Vorrang.** Ziel ist ein stabiler Betrieb auf einem **modernen leistungsfähigen Windows-PC**, inklusive tatsächlichem Mikrofon-/Systemaudio-Capture, WebView2-/Desktop-Integration, lokalen Modellen, sauberem Gerätemanagement und nachvollziehbarem Fehlerverhalten. Frühere Bundles umfassen unter anderem PyInstaller, PostgreSQL, ffmpeg, Tray/Overlay und Updater; diese technische Basis ist auf realer Hardware zu validieren.

**Docker/self-hosted** bleibt als **optionaler Server-, Entwicklungs- und historischer Meeting-Pfad**, nicht als gleichrangiges V1-Leitprodukt. Linux/macOS und breiterer Plattform-Support sind mögliche spätere Ausbauten.

Das Projekt wird **zunächst privat/persönlich bzw. Open Source ohne Monetarisierungsdruck** entwickelt. **Langfristiges Ziel ist vollständige Open-Source-Veröffentlichung von App- und Infrastrukturcode**, mit dokumentierten Abhängigkeiten und soweit möglich reproduzierbaren Build-/Releaseabläufen. Dieses Ziel schließt **keine** Credentials, privaten Profile, Audiodaten, Transkripte oder geheimen Betriebsschlüssel ein.

**Öffentliche Varianten (historischer Ist-Stand):**
- **DebateAI-Source** ist ein code-only Snapshot mit bewusst fehlenden internen Verträgen, Workflow-/Buildbestandteilen und privater Runtime. Ein solcher Export ist **nicht** gleichbedeutend mit dem langfristigen Voll-Open-Source-Ziel.
- **DebateAI-final-public** enthält eine umfassendere konsolidierte öffentliche Historie, beweist aber ebenfalls weder einen signierten noch einen vollständig reproduzierbaren Produktrelease.
- **Privater Master** bleibt die bisherige interne Code-/Abnahmereferenz (Auditbasis 79c095c); diese Visionsfassung entsteht auf dem separaten Review-Branch. Öffentlichkeitsgrad und Reproduzierbarkeit müssen vor einer Vollveröffentlichung bewusst angeglichen werden.

Veröffentlichte Aussagen über vollständige Offlinefähigkeit, Cloudfreiheit, Dokumentpfade, Mehrsprachigkeit oder Reifegrad müssen **dem tatsächlich geprüften Code entsprechen**; Marketing ersetzt keine Messung.

## 12. Qualität, Abnahme und Nicht-Ziele

**Absoluter Release-Stopper ist eine unzuverlässige oder faktisch falsche Empfehlung.** Eine gute Latenzzahl oder ein funktionsreiches Dashboard kompensiert keine schlechte rhetorische oder sachliche Qualität.

Abnahmekriterien für den Debattenkern sind insbesondere:

- **Rhetorik und Hilfe:** unabhängige menschliche Bewertungen mit realistischen deutschen Debattensituationen; Anteil tatsächlich nutzbarer Reaktionen; Fehler-, Halluzinations-, Überholungs- und Gegenbeispielquote; Bewertung beider Modi.
- **Echtzeit und Orchestrierung:** Messung der ersten brauchbaren und der finalen Antwort einschließlich Tail-Latenz, korrektes Verhalten bei Teiltranskripten, laufenden Revisionen, zwei Agentenrollen und Hintergrundrecherche.
- **Audio und Sprecher:** echte Windows-Mikrofon-/WASAPI-/Loopback-Sitzungen, Dual-Track, Sprecherwechsel, WER/CER, RTF, Gerätewechsel, langer Lauf und Wiederaufnahme nach Fehlern.
- **Transparenz und Datenhaltung:** erkennbare lokale/externe Providerwege, verlässliche Quellenlinks, keine als sicher präsentierten ungesicherten Behauptungen, nachvollziehbare Audio-Löschung und Erhalt von Transkript/Argumentgedächtnis.
- **Release und Betrieb:** reproduzierbare Tests, vorhandene CI-Logs statt als grün interpretierter Runner-Ausfälle, echte Windows-Build-/GUI-Abnahme, sichere Installation, Signatur/Hashes, Datenmigration, Update und Rollback. Offene Signatur-/Hardware-/Provider-Gates bleiben sichtbar.

Der bestehende Acceptance- und Release-Kontext (unter anderem A22/Human-Rating, Windows-Audio, CI-Provisionierung, Authenticode/Distribution) ist bislang **nicht vollständig abgenommen**. Siehe [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md), den datierten Geschichtsvermerk, den datierten Visionssnapshot und [EVIDENCE.md](EVIDENCE.md).

**Bewusste Nicht-Ziele:** automatische KI-Sprache im Gespräch, ein allgemeiner Team-Meeting-Dienst als Hauptidentität, primär mobile oder macOS-Veröffentlichung, ungeprüfte Vollautomatik von Modellwechseln, ungefragte öffentliche Releases, stille Cloudnutzung und das Ausgeben experimenteller Technik als fertig.

## 13. Noch nicht entschiedene Varianten

Diese Optionen sind **keine aktuellen Produktentscheidungen**. Sie bleiben direkt vergleichbar und können bei einer nächsten Visionsrunde einzeln bestätigt oder gestrichen werden.

1. **Startstil:** **A** Knallhart startet standardmäßig. **B** Der Nutzer wählt vor jeder neuen Sitzung zwischen Knallhart und Überzeugend. **C** Ein letzter Sitzungsstil wird übernommen.
2. **Intensität von Knallhart:** **A** Eine feste, sehr scharfe Stufe. **B** Mehrere Eskalationsstufen. **C** Situative automatische Intensität mit klarer manueller Begrenzung.
3. **Dashboard im Videocall:** **A** Großes separates Fenster auf zweitem Monitor. **B** Andockbare Hauptansicht. **C** Voll-Dashboard mit optionalem Mini-Modus.
4. **Cloud-Freigabeumfang:** **A** Anbieterbezogen einmalig konfigurieren. **B** Pro Sitzung kontrollieren. **C** Pro Datenkategorie konfigurierbar, danach dauerhaft aktiv. Wiederkehrende Freigabedialoge pro Aufruf sind **nicht** gewünscht.
5. **Aufnahme/Einwilligung:** **A** Einheitliche strenge Bestätigung. **B** Kontextabhängige Regeln für lokale Analyse, Speicherung und externe Weitergabe. **C** Bestätigung nur für tatsächlich aufzeichnende Betriebsweisen. Die rechtlich nötigen Grenzen sind gesondert zu prüfen.
6. **Optionales persönliches Modelltraining:** **A** Nicht anbieten. **B** Nur manuell ausgelöste lokale Trainingsläufe. **C** Später als separater Expertenworkflow. Die Audio-Löschregel gilt in jedem Fall.
7. **Erster integrierter Release:** **A** Gesamte Funktionsbreite nur nach voller Einzelabnahme. **B** Voller Live-Kern mit klar markierten optionalen/experimentellen Nebenmodulen. **C** Veröffentlichungsstufen mit vorab festgelegter Feature-Matrix.

**Ältere verworfene oder zurückgestellte Richtung:** Allgemeiner self-hosted Meeting-Assistent als gleichrangiges Hauptprodukt, automatische Mehrsprachigkeit als V1-Versprechen und Docker-first als Standarddistribution sind aufgrund der Eigentümerantworten **nicht mehr gleichrangig**. Sie werden nicht aus der Historie gelöscht, sind aber kein Auftrag, das Leitziel zu verwässern.

---

**Quellen und Vorrang:** Präzisierende Eigentümerantworten auf 50 Visionsfragen vom 19.11.2026 einschließlich der individuellen Ergänzungen; ältere den datierten Visionssnapshot, bisherige VISION.md, den datierten Geschichtsvermerk und [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md). **Die Vision beschreibt, was gewollt ist; der aktuelle Code- und Abnahmestand muss separat belegt werden.**
