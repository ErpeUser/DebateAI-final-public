# DebateAI – Verbindliche Gesamtvision

**Stand:** 22.11.2026  
**Dokumenttyp:** Vollständiges Produktziel und fachlicher Anforderungskatalog, **kein Nachweis einer fertigen Implementierung**.  
**Geltung:** Zielvision für DebateAI; konsolidiert aus der bisherigen VISION.md vom 19.11.2026 und den Eigentümerentscheidungen aus sechs Grill-Me-Runden bis zum 21.11.2026.

> **Leseregel und Vorrang:** Die jüngsten ausdrücklich getroffenen Produktentscheidungen gelten vor widersprechenden früheren Vorschlägen. Bestätigte ältere Ziele bleiben erhalten. „Soll“, „muss“ und „geplant“ beschreiben Zielverhalten, nicht den aktuellen Softwarestand. **Implementiert, lokal getestet, auf echter Hardware geprüft, freigegeben und veröffentlicht sind unterschiedliche Zustände.** Tatsächliche Nachweise stehen im aktuellen Code, in [HANDBUCH.md](HANDBUCH.md) und [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md); historische Herkunft in [HISTORIE.md](HISTORIE.md).

## 1. Leitbild, Zielgruppe und unverrückbarer Produktkern

**DebateAI soll der bestmögliche persönliche Echtzeit-Debatten-Copilot werden.** Es verfolgt eine laufende, vor allem kontroverse Diskussion, erkennt ihre Argumentstruktur und schlägt im richtigen Moment kurze, natürliche, unmittelbar aussprechbare Reaktionen vor. Es hilft dem Nutzer, Prämissen zu prüfen, Widersprüche und Doppelstandards zu erkennen, relevante Belege zu finden und überzeugender zu argumentieren. **Der Mensch entscheidet selbst, was er sagt. DebateAI spricht nicht autonom an seiner Stelle.**

Die erste Zielgruppe sind Privatpersonen, Debattierer, Studierende und Rhetorik-Interessierte. **V1 konzentriert sich auf eine einzelne Person in einem kontroversen Videocall.** Persönliche Gespräche, nachträgliche Auswertungen und allgemeine Meeting-Analyse sind unterstützende beziehungsweise optionale Szenarien. Team-Workspaces und ein allgemeiner Meeting-Dienst sind nicht die primäre Produktidentität.

Der Aha-Moment ist nicht viel generierter Text, sondern eine **situativ richtige, sachlich vertretbare und rechtzeitig sprechbare Erwiderung**. Erfolg wird an nachweisbarem Nutzen, Genauigkeit, Natürlichkeit, Rhetorik, Zeitverhalten und Stabilität gemessen. DebateAI soll langfristig auch eine modulare Plattform für Rhetik- und Gesprächsanalyse, Evaluierung und KI-Forschung sein; jede Erweiterung muss jedoch dem Live-Debattenkern dienen.

**Leitprinzipien:**
- **Local First im Live-Pfad:** Lokale Spracherkennung und ein lokales Textmodell liefern die erste Reaktion; externe Web-Agenten ergänzen, blockieren diesen Pfad aber nicht.
- **Web First bei externen Agenten:** Neue ChatGPT-/Gemini-Agenten arbeiten über die jeweiligen Weboberflächen, nicht über verpflichtende Modell-APIs.
- **Einfachheit trotz Leistung:** Die bestehende Desktop-UI wird konsequent verbessert und vereinfacht, ohne ihre wertvollen Analysefunktionen zu verlieren.
- **Generative statt deterministische KI-Beispiele:** Modellantworten in Vorschauen und Alternativen stammen aus tatsächlichen Modellgenerationen; keine als echt ausgegebenen Textbausteine.
- **Nutzerentscheidung:** Die KI darf Einstellungen und Strategien empfehlen, aber persönliche Präferenzen nicht stillschweigend übernehmen.
- **Geprüfte Selbstoptimierung:** Nach manuellem Start können Testprofile automatisiert verbessert werden, niemals während der Live-Debatte.
- **Eigenständigkeit:** DebateAI darf sich von Backchannel und anderen Systemen inspirieren lassen, darf aber nicht von ihnen als Produkt abhängen.

## 2. Plattform, Betriebsarchitektur und Modellwege

**Das Hauptprodukt bleibt eine eigenständige Windows-Desktop-Anwendung.** Der kritische Live-Pfad nutzt lokale Audioverarbeitung, lokale ASR und ein lokal ausführbares Textmodell, etwa über Ollama/Qwen oder eine funktional geeignete Alternative. Das ist ein Architekturziel, keine Festlegung auf ein bestimmtes Modell. Der lokale Pfad bleibt auch während langsamer oder ausgefallener Web-Recherchen funktionsfähig.

Daneben arbeitet ein **zusätzlicher Web-Agenten-Pfad** mit ChatGPT Web und Gemini Web. Dieser übernimmt je nach Bedarf Recherche, tiefere Argumentationsanalyse, Kontextanreicherung, Vergleich und spätere Test-/Profiloptimierung. Eine laufende lokale erste Antwort darf von diesen Aufgaben nicht abhängig sein. Die neuen externen Agenten benötigen **keine verpflichtende direkte Modell-API**. Bereits vorhandene API-Integrationen, etwa für ältere Meeting- und Dokumentfunktionen, dürfen als klar gekennzeichnete optionale Legacy-Pfade erhalten bleiben, ohne die Web-Agenten-Strategie zu verwässern.

**Lokal und Cloud sind zwei mögliche Ausführungsumgebungen derselben Anwendung:**
- **Lokal:** reguläre Live-Debattennutzung, Testlabor und vollständige Programmausführung auf dem eigenen Windows-PC.
- **Cloud:** vollständige Testinstanz des Programms einschließlich UI/Teststeuerung, Agenten, Browser-Sitzungen, Audio-/Video-Replay, Messung, Konfigurationsoptimierung und Build-/GitHub-Anbindung.
- **Hybrid:** gemeinsame versionierte Prompts, Profile und Konfigurationsstände, ohne lokale Sitzungsdaten ungefragt in die Cloud zu verschieben.

Die Cloud ist **kein Ersatz für die lokale Nutzung**. Google Cloud wird wegen vorhandener Willkommens-Credits vorrangig auf technische Eignung und Kosten untersucht; andere Lösungen sind zulässig, falls sie objektiv besser geeignet sind. Docker/Self-hosted bleibt ein möglicher Entwicklungs- und Serverweg, Windows-Desktop aber die primäre Nutzung. Linux/macOS und breiterer Plattform-Support sind mögliche spätere Ausbauten.

Vor einer ersten Live-Sitzung prüft eine geeignete Einrichtungshilfe Prozessor, GPU, RAM, Audio-Geräte, lokale ASR-/Textmodelle, Modellkompatibilität und ausgewählte Datenflüsse. Fehlende Modelle oder Voraussetzungen werden verständlich erklärt; Downloads, Provider und mögliche Kosten werden transparent dargestellt. Mindesthardware und verbindliche Modellmatrix sind durch Messungen zu bestimmen, nicht aus Vermutungen abzuleiten.

## 3. Live-Debatte, fachliche Agentenrollen und Kontext

Nach dem Audio-/Hardware-Starttest beginnt die Sitzung mit getrennten Audioquellen, laufenden Transkripten, Sprecherzuordnung und kontinuierlich aktualisierten Antwortvorschlägen. Die Anwendung verarbeitet nicht nur den letzten Satz, sondern **Argumentationsverlauf, eigene Position, Position des Gegenübers, bisherige Reaktionen, Widersprüche und den nächsten sinnvollen rhetorischen Schritt**.

**Zwei dauerhaft verfügbare fachliche Kernrollen bleiben verbindlich:**

1. **Argument-Agent:** Prüft aktuelle Aussagen, Prämissen, Schlussfolgerungen, Beweislast, Denkfehler und direkte Gegenreaktionen.
2. **Strategie-Agent:** Verfolgt den Sitzungsverlauf, Muster, bereits verwendete Antworten, Doppelstandards, Widersprüche, Dilemmata und taktische Optionen.

Diese Rollen müssen auf demselben gültigen Gesprächs-/Sprecherkontext arbeiten. **Zwei Rollen sind keine Pflicht zu zwei getrennten Modellen oder Prozessen.** Ein zentraler Koordinator kann sie lokal oder durch zusätzliche Web-Aufgaben unterstützen und achtet darauf, dass neue, alte und widersprüchliche Agentenergebnisse nicht ungeprüft vermischt werden.

Zusätzliche Rollen wie Recherche, Belegprüfung, Kontextanalyse und Evaluierung können bedarfsorientiert und dynamisch aktiviert werden. Bestehende Funktionen für Lead-/Shout-Verhalten, das Erkennen günstiger Argumentationsmomente und strategische Hinweise sollen so weit wie sinnvoll automatisiert und verbessert werden, statt zusätzliche Benutzerentscheidungen zu erzwingen. Live-KI-Unterstützung bleibt sichtbar und kontrollierbar; der Nutzer spricht selbst.

## 4. Antwortausgabe: eine beste Antwort, höchstens zwei Alternativen

Die frühere gleichrangige Darstellung von drei Antwortkarten wird durch eine klare Hierarchie ersetzt:

- **Eine beste aktuelle Antwort** steht visuell im Vordergrund: kurz, natürlich, sprechbar und zum letzten relevanten Gesprächszug passend.
- **Bis zu zwei sinnvolle Alternativen** stehen nachgeordnet bereit, beispielsweise eine Analogie, eine präzise Gegenfrage, ein Einwand, ein hypothetischer Perspektivwechsel oder eine zweite starke Argumentation.
- Die Alternativen müssen sich in ihrer tatsächlichen Strategie unterscheiden; ein bloßes Umformulieren desselben Inhalts zählt nicht.
- Die besten Antworten und Alternativen werden **dynamisch von den KI-Systemen generiert**, nicht aus statischen rhetorischen Textbausteinen zusammengesetzt.
- Überholte Ergebnisse werden als **veraltet** markiert und nicht als aktuell angeboten. Antworten tragen einen eindeutigen Sitzungs-, Sprecher- und Gesprächszugbezug.

**Frühe, revidierbare Vorschläge sind ausdrücklich erwünscht.** Das lokale Modell darf auf unvollständige Transkripte reagieren, muss aber Unsicherheit angemessen kennzeichnen. Korrigiert die ASR eine Aussage oder liefert eine Recherche belastbare neue Informationen, wird die bestehende Antwort nach Möglichkeit **verbessert, korrigiert oder erneuert**, statt ungefragt eine separate Folgeantwort zu erzeugen. Historische Versionen dürfen bei Bedarf nachvollziehbar bleiben. Auch während der Rede des Nutzers darf die Oberfläche relevante Fehler, Chancen und Korrekturen zeigen.

**Ambitioniertes, noch zu validierendes Latenzziel:** Auf definierter Windows-Zielhardware soll nach Möglichkeit eine erste brauchbare Antwort innerhalb von **1 bis 2,5 Sekunden** sichtbar sein. Dies ist kein bereits belegter SLA. Qualität, besonders die sachliche Richtigkeit, darf nicht für eine reine Geschwindigkeitszahl geopfert werden. Aufwendige Arbeiten dürfen den lokalen Erstpfad nicht spürbar blockieren.

Bei einem **Web-Agenten-Ausfall** arbeitet der tatsächlich verfügbare lokale Pfad weiter und zeigt den Ausfall transparent. Bei einem **Ausfall des lokalen Modells** wird ein ehrlicher Fehlerstatus angezeigt; es dürfen keine fingierten Ersatzantworten als aktuelle KI-Leistung ausgegeben werden.

## 5. Rhetorik: genau zwei zentrale Modi

Der Nutzer wählt **vor jeder neuen Sitzung** zwischen **„Hart“** und **„Überzeugend“**. Der zuletzt verwendete Modus ist vorausgewählt, kann aber vor Sitzungsbeginn jederzeit geändert werden. Kein zusätzlicher Pflichtdialog bei jedem Agentenaufruf und keine Vielzahl konkurrierender Rhetorikmodi.

### Hart

Der bisherige Modus „Knallhart“ heißt in der UI künftig **„Hart“**. Inhaltlich bleibt er bewusst direkt, pointiert und argumentativ konfrontativ: Widersprüche aufzeigen, Doppelstandards prüfen, unhaltbare Prämissen angreifen, Maßstäbe hypothetisch umkehren und präzise Gegenfragen formulieren. Sehr scharfe, provokante und rhetorisch zugespitzte Formulierungen sind möglich, soweit sie sachlich vertretbar sind. **Hart** bedeutet nicht, Tatsachen zu erfinden, Gewalt anzudrohen oder unbelegte persönliche Vorwürfe als Fakten auszugeben.

### Überzeugend

Der Modus **„Überzeugend“** verfolgt eine möglichst hohe tatsächliche Überzeugungswirkung: verständliche Beispiele, Gemeinsamkeiten, faire Einordnung gegnerischer Einwände, präzise Formulierungen und situativ passende Gesprächsführung. Eine starke Gegenposition darf ruhig formuliert werden; kluge Gegenfragen und der richtige Zeitpunkt für einen Perspektivwechsel können wirksamer sein als reine Konfrontation.

### Eigene Fehler, Wahrheit und rhetorische Redlichkeit

Wenn der Nutzer selbst einen Fehler macht, soll DebateAI helfen, den **vertretbaren Kern** seiner Position zu retten – beispielsweise durch korrekte Präzisierung, einen engeren Begriff, ein zulässiges Gegenbeispiel oder eine Klärungsfrage. Es darf den Fehler auch benennen. **Falsche Tatsachen werden nicht als wahr verteidigt; eine Ausweichstrategie wird nicht als Beleg ausgegeben.**

Nur überprüfte Tatsachen werden als gesichert dargestellt. Ungeprüfte Zahlen, Studien, Zitate und Quellen dürfen nicht als verifiziert ausgegeben werden. Hypothetische Rollentausche sind als hypothetisch erkennbar. Bei einer fragwürdigen Zahl kann zunächst die Logik des daraus gezogenen Schlusses geprüft und erst danach die Zahl selbst recherchiert werden. Rhetorik wird stets gegen Korrektheit, Gesprächskontext und Quellenredlichkeit bewertet.

## 6. Deutsch, Live-Audio, ASR und Sprecherverständnis

**Deutsch bleibt die einzige offiziell unterstützte V1-Sprache.** Natürliches gesprochenes Deutsch, Zahlen, Eigennamen, Korrekturen, Gesprächsdynamik und Streitgespräche haben Vorrang vor einer breiten Sprachliste. Mehrsprachigkeit und Auto-Detect bleiben spätere Optionen; ältere Release-Notes zu Mehrsprachigkeit sind kein neuer V1-Produktvertrag.

**Verbindliche Audioanforderungen:**
- Mikrofon und Systemaudio bleiben technisch und in den Daten **getrennte Spuren**.
- Stabiler Windows-Capture inklusive WASAPI/Loopback, Gerätauswahl/-wechsel, Zeitstempeln, Ausfall- und Wiederanlaufbehandlung.
- Geeignete PCM-Verarbeitung, unter anderem 16-kHz-kompatible Wege; Whisper, Parakeet und vergleichbare lokale ASR-Systeme sind zu vermessende Alternativen.
- **Live-Sprecherzuordnung ist Pflicht:** Nutzer und Gegenüber dürfen nicht unbemerkt vertauscht werden.
- Unsicherheiten, ASR-Revisionen und Diarisierungskorrekturen müssen in Kontextgedächtnis, Argumentanalyse und sichtbare Antworten propagiert werden.
- Für die Qualitätsbewertung sind deutsche Referenzaufnahmen, reale Zielhardware, Sprecherwechsel, Überlappungen, Gerätegeräusche, lange Sitzungen und Wiederaufnahmen erforderlich.

Keine pauschalen Qualitätsversprechen für ASR oder GPU-Verfahren, solange ihre Leistung auf repräsentativem Material und echter Hardware nicht ausreichend belegt ist.

## 7. Recherche, Belegfluss und adaptive Denkzeit

Die erste brauchbare Erwiderung hat zeitlich Vorrang vor einer vollständigen externen Quellenprüfung. **Unverifizierte Fakten dürfen dadurch aber nicht zu angeblich sicheren Tatsachen werden.** Recherche ergänzt, korrigiert und verbessert Antworten, sobald belastbare Informationen vorliegen.

**Automatisierte Recherche:**
- Nach bewusst eingerichteter Freigabe darf Recherche bedarfsorientiert und fortlaufend im Hintergrund laufen, ohne einzelne Popups für jeden Suchvorgang.
- Ein Agent entscheidet möglichst selbst, wann neue Informationen wirklich nötig sind und wann vorhandenes Wissen oder bereits gefundene Belege ausreichen.
- **„Jetzt recherchieren“** ist während jeder laufenden Debatte verfügbar und erzwingt eine Recherche zum aktuellen Kontext.
- Dieser Befehl darf laufende **Recherche-Agenten** stoppen, ersetzen oder neu priorisieren und bisherige nützliche Ergebnisse weiterverwenden.
- **Der lokale Echtzeit-Agent darf dadurch nicht unterbrochen werden.**
- Belastbare Quellen werden in knappen, unmittelbar verwendbaren Aussagen mit nachvollziehbarem Link eingebracht. Später eintreffende Recherche soll vorhandene Antwortvorschläge verbessern oder gegebenenfalls widerlegen.

**Adaptive Denkintensität:** Je nach Schwierigkeit, Zeitdruck, Erreichbarkeit und Antwortdauer soll DebateAI verfügbare Reasoning-Stufen und Web-Modelle intelligent wählen. Bei langen Wartezeiten darf an sicheren Aufgabengrenzen die Denkintensität reduziert oder der Provider gewechselt werden. Bereits laufende Generationen werden nicht chaotisch abgebrochen. Arbeitsabläufe wie **recherchieren → bewerten → argumentieren → verständlich formulieren** sollen aufgabengerecht optimiert und nicht unnötig mehrfach ausgeführt werden.

Die konkrete technische Möglichkeit, Reasoning-Stufen über ChatGPT Web/Gemini Web zuverlässig zu steuern, ist **vor Implementierungszusagen zu prüfen**. Die Vision verlangt gewünschtes Verhalten, behauptet aber keine heute gesicherte externe Steuerbarkeit.

## 8. Sitzungsstart, Sitzungsende und Aufbewahrung

### Start

Vor **jeder neuen Sitzung** ist die Wahl zwischen Hart und Überzeugend möglich. **Der zuletzt gewählte Modus ist vorausgewählt.** Technische Einrichtung und Hardwarechecks werden angeboten, wenn sie nötig sind; kein unnötiges wiederholtes Voll-Onboarding.

### Normales Sitzungsende

**Bei normalem Beenden wird ein vollständiges zeitgestempeltes Transkript erzeugt und lokal behalten.** Es erhält nachvollziehbare Sprecherzuordnung, soweit sicher erkannt, und kann für spätere Auswertung, Argumentgedächtnis und vom Nutzer ausgelöste Tests verwendet werden. Extrahierte Argumente und sonstige ausdrücklich beibehaltene Sitzungsdaten dürfen ebenfalls lokal erhalten bleiben, bis der Nutzer sie löscht.

Die bestehende Ende-der-Sitzung-Oberfläche soll **zwei klar beschriftete, aufklappbare Reiter/Optionen** erhalten und verbessern – derzeit existiert nach Eigentümerangabe nur einer:

1. **„Aufnahme speichern“:** Audio-/Sitzungsaufnahme bewusst dauerhaft sichern, ergänzend zum zeitgestempelten Transkript, und bei Bedarf später analysieren oder in Tests verwenden.
2. **„Komplett ohne Speicherung/Verbesserung fortfahren“:** Die aktuelle Sitzung beenden beziehungsweise fortfahren, **ohne** Transkript, Aufnahme, Argumentextrakte oder Profilverbesserungsdaten dieser Sitzung dauerhaft aufzubewahren oder in Trainings-/Optimierungsläufe zu übernehmen. Bereits temporär angefallene Sitzungsartefakte werden nach Maßgabe des technisch möglichen Löschpfads bereinigt.

**Vorrangregel:** Die bewusste Wahl von „ohne Speicherung/Verbesserung“ überschreibt für **diese Sitzung** die normale Transkript-Aufbewahrung. Die Optionen dürfen nicht widersprüchlich gleichzeitig aktiv sein. Die beiden Reiter sollen intuitiv, klar und ohne unnötige Dialoge funktionieren. Die UI darf daneben den normalen Abschluss mit Transkripterhalt zulassen.

### Rohdaten und Bestandsschutz

Nicht ausdrücklich gespeicherte Rohaufnahmen werden nach notwendiger Verarbeitung beziehungsweise einem ausdrücklich gestarteten Test-/Trainingslauf bereinigt. **Bewusst gespeicherte Test-Videos, Referenz-Audios und Testdatensätze** bleiben dagegen für reproduzierbare Vergleiche erhalten, bis sie manuell gelöscht werden. **Kein stilles allgemeines Modelltraining** aus normalen Sitzungen.

App-Updates und Rollbacks dürfen Datenbanken, gespeicherte Transkripte, Argumentgedächtnis, Profile, Playbooks, Modelle oder Konfigurationen nicht versehentlich löschen oder überschreiben. Bewusst gelöschte Aufnahmen sollen durch Backups oder Updates nicht ungewollt wieder auftauchen. Externe Provider-Speicherungen sind gesondert transparent zu machen; eine lokale Löschaktion darf nicht eine unbelegte globale Provider-Löschung vortäuschen.

## 9. Bestehende Windows-Oberfläche gezielt perfektionieren

**Die vorhandene UI wird analysiert, verbessert und perfektioniert – kein pauschaler Neubau oder Ersatz der Anwendung.** Funktionierende Komponenten und bewährte Abläufe sollen weiterverwendet werden. Unnötige Komplexität wird reduziert, das Design vereinheitlicht und alle zentralen Interaktionen erhalten eine nachvollziehbare Benutzerführung.

Das Hauptprodukt bleibt ein **vollwertiges Windows-Dashboard** mit sichtbarer Gesprächslage, bester Antwort, bis zu zwei Alternativen, Sprecherinformationen, Argumentationsmustern, strategischen Hinweisen, Recherche-/Quellenstatus und klaren Fehlermeldungen. Eine reine Text-Minimalanzeige oder ein schmales Overlay ist **optional**, nicht das alleinige Produktversprechen. Für Videocalls sollen sinnvolle Fenstergrößen, andockbare Panels, gegebenenfalls ein zweiter Monitor und ein optionaler Kompaktmodus anhand tatsächlicher Nutzung geprüft werden.

**Gestaltungsprinzipien:**
- Reduzierte, elegante Hauptansicht; umfassende Analysebereiche bei Bedarf aufklappen.
- Klare visuelle Priorität für die **beste aktuelle Antwort**; Alternativen nachgeordnet.
- Benutzerfreundliche Statusanzeigen, Agentenaktivität, Quellen und Sitzungsverlauf ohne Informationsüberladung.
- Das bisherige umfangreiche Analyse-Dashboard wird **verbessert**, nicht einfach entfernt.
- Benachrichtigungen und Hinweise erhalten sinnvolle Standards; kein Wildwuchs neuer Konfigurationsschalter.
- Neue visuelle Elemente nur, wenn sie Orientierung, Verständlichkeit, Kontrolle oder Geschwindigkeit verbessern.
- Einstellungen finden **außerhalb der laufenden Debatte** statt.
- Vorschläge werden **als Text** gezeigt; autonome KI-Sprachausgabe oder selbstständiges Mitsprechen sind nicht vorgesehen.

## 10. Interaktives Onboarding und intelligentes Einstellungsstudio

**Ein besonders wichtiges Produktmerkmal ist ein neu gedachtes, schönes, spielerisches und sofort verständliches Einstellungsstudio.** Es soll Spaß machen, Einstellungen auszuprobieren, ihre tatsächliche Wirkung zu verstehen und die passende Konfiguration zu finden – ohne eine Wand aus Dropdowns, technischen Parametern und Testfenstern.

Das Studio hat **zwei Zugänge**:
1. **Geführtes, freiwilliges Onboarding** beim Einstieg, später jederzeit erneut aufrufbar.
2. **Frei erkundbares Einstellungsstudio** für die tägliche Nutzung und spätere Profilanpassungen.

**Interaktivität als Hauptfunktion, nicht als Nebentest:**
- Wichtige Parameter besitzen direkt integrierte, echte KI-generierte Vorschauen und Vergleichsmöglichkeiten.
- Bei einer Änderung wird die Vorschau **nach einer kurzen Ruhezeit** automatisch neu generiert; unnötige parallele Web-Anfragen werden gebündelt.
- Die Vorschau macht nachvollziehbar, **wie** sich eine Konfiguration auf Stil, Antwort, Argumentation oder Modellverhalten auswirkt.
- Ausführliche manuelle Sondertests und technische Informationen erscheinen **erst nach bewusstem Aufklappen**.
- KI darf verständliche Empfehlungen und mehrere begründete Alternativen vorschlagen. **Nur der Nutzer wählt seine persönlichen Einstellungen.**
- Einstellungen werden **in einem separaten Testprofil** ausprobiert; laufende Debatten werden nie unbeabsichtigt verändert.
- Profile und Präferenzen lassen sich speichern, vergleichen, versionieren und rückgängig machen.
- Beispiele und Animationen dienen der Erklärung; als echte KI-Antwort präsentierte Inhalte sind **niemals bloß deterministische Mustertexte**.

Die Bereiche orientieren sich sowohl an Nutzerzielen als auch an **sinnvollen technischen Kategorien**: Debattenstil, **Transkription**, Antwortgenerierung, Recherche, Agenten und Aufgabenverteilung, Hinweise/Ausgabe sowie nötige erweiterte Funktionen. Die tatsächliche Informationsarchitektur soll aus einer Untersuchung der vorhandenen UI entstehen und eher **weniger, aber klarere Optionen** bieten.

Die übliche Bedienung soll **keinen separaten komplizierten Testbereich erzwingen**: Das Testen ist ein nahtloser Teil des Einstellens. Nur fachlich tiefe Experten- und Messtests werden zusätzlich aufklappbar.

## 11. Sichtbarer Modell-, Prompt-, Sprach- und Strategievergleich

Das A/B- und Sprachlabor ist **ein zugängliches Kernfeature für Nutzer**, kein verstecktes reines Entwicklerwerkzeug. Die aktuelle Produktentscheidung lautet ausdrücklich **sichtbarer Modellvergleich**, **nicht ein verpflichtender Blindvergleich mit verborgenem Modellnamen**.

- ChatGPT Web, Gemini Web und verfügbare Modell-/Prompt-/Stilvarianten werden **direkt nebeneinander** gezeigt.
- Vergleiche verwenden möglichst **denselben Input, dieselbe These, die eigene Position, denselben Gesprächskontext und dieselbe Stilvorgabe**.
- Echte, aktuell generierte Antworten sind als solche sichtbar; Modell, Promptversion, Latenz, Kontext und mögliche Kosten bleiben nachvollziehbar.
- Der Nutzer kann unmittelbar sehen, **welche KI bei welcher Einstellung welche Antwort formuliert**.
- Bewertet werden mindestens Sprechbarkeit, Natürlichkeit, argumentative Stärke, situativer Nutzen, Gegenfragen, Quellenredlichkeit, Fehler und Antwortgeschwindigkeit.
- Gespeicherte frühere KI-Antworten sind nur bei **hoher Qualität** beziehungsweise ausdrücklicher Auswahl wiederverwendbar und **als gespeichert** erkennbar; niemals als frisches Live-Resultat ausgeben.
- Die KI kann begründete Empfehlungen liefern. **Kein automatisch erzwungener Modellgewinner oder stiller Wechsel des persönlichen Liveprofils.**
- Kein synchroner schwerer KI-Richter auf dem latenzkritischen Live-Pfad.

Das **Transkriptions-/Sprachlabor** vergleicht ASR-Modelle an derselben Aufnahme mit editierbarer deutscher Referenz, WER/CER, RTF, Laufzeit und konkreten Fehlerfällen. Der Nutzer kann Transkription und Antwortgenerierung auch separat prüfen. Labortests dürfen eine aktive Live-Sitzung nicht lahmlegen.

Unabhängige menschliche Bewertungen, wiederholbare Datensätze und die saubere Trennung von Test- und Optimierungsfällen bleiben für belastbare öffentliche Qualitätsbehauptungen erforderlich. Bewertungsverfahren dürfen wissenschaftlich fundiert sein, aber die **sichtbare** Produktdarstellung der Modellvergleiche nicht durch das früher vorgeschriebene Blind-A/B-Verfahren ersetzen.

## 12. Web-Agenten, Koordination, Browser-Sitzungen und Ausfälle

**Neue externe KI-Agenten werden primär über ChatGPT Web und Gemini Web betrieben.** Die Zahl parallel laufender Chats und ihre Aufgaben werden intelligent nach Geschwindigkeit, Stabilität, Ergebnisqualität und aktueller Verfügbarkeit verteilt. Ein Beispiel sind zeitweise zwei ChatGPT- und zwei Gemini-Chats statt vier Chats desselben Anbieters; **diese Zahlen sind keine starren Vorgaben**. Dynamische Limits und bei Bedarf manuelle Obergrenzen verhindern unnötige Überlastung.

Ein zentraler Koordinator:
- verwaltet fachliche Rollen, Aufgaben, gemeinsamen Kontext, Quelle und Aktualität;
- vermeidet widersprüchliche oder redundante parallele Recherche;
- weist Aufgaben anhand der verfügbaren Web-Modelle zu;
- darf bei Latenz, Providerfehlern und Überlastung die Aufgaben **unter den Web-Agenten** neu verteilen;
- erhält die lokale Erstreaktion als unabhängigen, nicht unterbrechbaren Kern;
- macht Agentenzuordnung und Status bei Bedarf transparent und manuell beeinflussbar.

**Browsersteuerung und Sitzungsverwaltung:**
- Die Web-Browser sollen **möglichst unsichtbar und im Hintergrund** laufen; eine sichtbare, unterstützte Alternative ist bei technischen Grenzen zulässig.
- Vor einer technischen Festlegung sind verfügbare CLI-, MCP-, Browserautomations- und Erweiterungsansätze auf Zuverlässigkeit, Nutzbarkeit und Plattformregeln zu prüfen.
- **Persistente geschützte Browserprofile/Sitzungen** bevorzugen statt unverschlüsseltem Cookieexport oder im Quellcode gespeicherten Passwörtern.
- Wenn eine Anmeldung abläuft, **sofort verständlich warnen** und eine schnelle erneute Anmeldung erlauben.
- Nach Ausfällen kann ein Chat anhand gesicherter Zustände und gültiger Kontextzusammenfassungen ersetzt werden, ohne dieselbe Aufgabe mehrfach unkontrolliert auszuführen.
- Temporäre Chats und Browserartefakte dürfen nach sicherer Übernahme der Ergebnisse bereinigt werden.
- Mehrere eigene autorisierte Kontoprofile sind technisch trennbar, aber kein eigenes Hauptfeature.
- Cloud-Testinstanzen können **eigene autorisierte Web-Sitzungen** verwalten, statt zwingend lokale Sitzungen zu kopieren.

**Offene technische Bedingung:** Das verlässliche, regelkonforme Betreiben bestimmter Webfunktionen, Headless-Modi und Reasoning-Umschaltungen muss empirisch verifiziert werden. Aus der Vision folgt keine Behauptung, dass jeder Anbieter jede gewünschte Steuerfunktion heute erlaubt oder unterstützt.

## 13. Vollständige Audio-/Video-Debattensimulation als Testlabor

Die Testumgebung soll das **gesamte DebateAI-Programm** unter realitätsnahen Bedingungen prüfen, nicht nur isolierte Prompttexte. Sie ist sowohl lokal als auch in der Cloud nutzbar und unterstützt **Videos, Audiodateien, zeitgestempelte Transkripte, aufgezeichnete Debatten, editierbare Referenzen und künstlich erzeugte Testszenarien**.

Ein realistischer Lauf spielt die Aufnahme beziehungsweise den Testgesprächsverlauf ab, stoppt an geeigneten Stellen und hält fest:
- **was bis zu diesem Zeitpunkt tatsächlich gesagt und transkribiert wurde**;
- welche Sprecher mit welcher Sicherheit erkannt wurden und welche Korrekturen erfolgten;
- welcher Agent wann eine Aufgabe erhielt und welche Informationen er zu diesem Zeitpunkt kannte;
- **wann** Recherche begann, ob sie zu früh, unnötig, sinnvoll oder zu spät war;
- wie lange Transkription, Recherchen, lokale Erstreaktion und Web-Antworten dauerten;
- **welche Antwort tatsächlich zu diesem Zeitpunkt** erzeugt und angezeigt wurde;
- ob sie verständlich, wahrheitsgemäß, sprechbar, situationsgerecht und rhetorisch wirksam war;
- welche konkrete Prompt-, Profil- oder Agentenkonfigurationsänderung eine Verbesserung verspricht.

Die Oberfläche zeigt eine **gemeinsame Zeitleiste** für Aufnahme/Video, Transkript, Sprecher, Agentenaktivität, Recherche, Antwortversionen, Latenzen und Bewertungen. Testdaten und Agentenprotokolle bleiben für wiederholbare Vergleiche verfügbar, solange der Nutzer sie bewusst als Testmaterial aufbewahrt.

**Testarten:**
- **Echtzeit:** echte End-to-End-Latenzen und Verhalten bei laufender Audio-/Videoeingabe.
- **Schrittweise:** an einem Gesprächspunkt anhalten, prüfen, ändern, exakt diesen Abschnitt wiederholen.
- **Beschleunigt:** Logik- und Regressionstests, ohne beschleunigte Laufzeiten mit realen Antwortlatenzen zu verwechseln.
- **Variations-/Störungstests:** Sprecherüberschneidungen, Hintergrundgeräusche, Transkriptionsfehler, Unterbrechungen, langsame oder ausgefallene Web-Agenten, komplexe Gegenargumente.
- **Funktionsübergreifend:** derselbe Test kann ASR, Sprechertrennung, Kontextgedächtnis, Agentenrouting, Recherche, Antwortgenerierung und UI gleichzeitig prüfen, Ergebnisse aber **getrennt** ausweisen.

Zusätzliche KI-generierte Testfälle sind ausdrücklich erlaubt, **aber nur im Testbetrieb nach beziehungsweise außerhalb echter Live-Debatten**. Manuelle Markierungen besonders guter oder schlechter Gesprächsstellen unterstützen die Evaluations-KI und können hochwertige Referenzbewertungen erzeugen.

## 14. KI bewertet KI: schrittweise und profilgebundene Selbstoptimierung

**Während einer laufenden Debatte werden keine Prompts, Modellgewichte, Programmeinstellungen oder Agentenverteilungen als Selbstoptimierung verändert.** Live-Betrieb darf Daten beobachten und nach den gewählten Sitzungsregeln protokollieren. **Optimiert wird ausschließlich in einem bewusst manuell gestarteten Testlauf.**

**Verbindlicher Optimierungszyklus:**

1. Nutzer wählt **ein konkretes Testprofil** und startet die Optimierung manuell.
2. Die unveränderte Ausgangsversion, relevante Datensätze, Promptversionen und Messbedingungen werden gesichert.
3. Eine Evaluations-KI analysiert den Gesamtfall und **priorisiert die wichtigste Schwachstelle**.
4. Sie identifiziert betroffene Agenten, Prompts, Einstellungen, Anzahl paralleler Agenten oder Routingentscheidungen und formuliert **konkrete testbare Änderungen**.
5. Nur der betroffene Gesprächsabschnitt wird unter möglichst vergleichbaren Bedingungen erneut geprüft; alte Web-Chats dürfen den Test nicht unkontrolliert kontaminieren.
6. Technische Kennzahlen und qualitative Bewertungen werden **getrennt** ermittelt. Korrektheit, Gesprächsverständnis und Timing haben Vorrang vor Stil und Härte.
7. Eine nachweislich bessere Variante bleibt **im Testprofil**; eine Verschlechterung wird zurückgenommen.
8. Erst danach folgt **der nächste problematische Abschnitt** oder die nächste Schwachstelle. Nicht wahllos mehrere Funktionen gleichzeitig verändern.
9. Nach mehreren lokalen Verbesserungen folgt eine **vollständige Debattensimulation/Regression**, um Überoptimierung einzelner Szenen zu verhindern.
10. Bei ausbleibender Verbesserung oder wiederholter Verschlechterung endet der Durchlauf kontrolliert. Beste getestete Version und Vergleichsbericht bleiben erhalten.
11. Der Nutzer prüft und **genehmigt die Gesamtverbesserung am Ende der Serie**; es sind keine Rückfragen nach jedem einzelnen Testschritt erforderlich.
12. Erst nach Freigabe werden die geprüften Prompts und Konfigurationen veröffentlicht beziehungsweise als neue freigegebene Profilversion übernommen.

**Erlaubter autonomer Änderungsumfang:** Prompts, zulässige Programmeinstellungen, Agentenrollen, Agentenzahl, Parallelität, Aufgabenverteilung und Routing-/Arbeitsablaufregeln. **Nicht erlaubt:** selbstständige Änderungen an der Quellcode-Logik der Anwendung durch die Cloud-Test-KI.

Die Selbstoptimierung ist zunächst **Prompt-, Strategie- und Konfigurationsoptimierung**, **nicht automatisch Fine-Tuning der Modellgewichte**. Persönliches Modelltraining kann langfristig als gesonderter ausdrücklich ausgelöster Expertenworkflow untersucht werden. Nicht ausgewählte Profile und persönliche Einstellungen bleiben unverändert.

## 15. Cloud-Testinstanz, GitHub und automatische Bugmeldungen

Die Cloud soll eine **vollständige auswertbare DebateAI-Instanz** bereitstellen. Dazu gehören steuerbare Testoberfläche, Web-Agenten, Audio-/Video-Replays, KI-Auswertung, Konfigurationsoptimierung, Ergebnisprotokolle und Integration mit dem GitHub-Repository. Sie dient ausdrücklich auch dazu, Defekte im vollständigen Zusammenspiel zu entdecken.

**Verbindliche Trennung:**
- **Cloud-Test-KI darf selbst optimieren:** Prompts, Programmeinstellungen, Agentenrollen, Anzahl und Aufteilung der Agenten, Routing sowie Arbeitsabläufe.
- **Cloud-Test-KI darf nicht selbst reparieren:** Quellcodedateien, Laufzeitlogik oder technische Programmfehler. Diese werden **extern durch einen gesonderten Entwicklungsprozess** behoben.
- **Bei erkannten Bugs:** Automatisch einen **GitHub-Issue-Eintrag mit Bug-Kennzeichnung** erzeugen beziehungsweise einen bestehenden passenden Eintrag ergänzen. Ein Bericht umfasst Reproduktionsschritte, relevante Logs, betroffene Bereiche, erwartetes/tatsächliches Verhalten, Umgebung und Teststand. Doppelte Issues möglichst vermeiden; **keine Zugangsdaten, Cookies oder geheimen Sitzungstokens in Issues oder Logs veröffentlichen**.

**GitHub-/Build-Ablauf:**
1. **Nach jedem Push** startet automatisch ein Build mit schnellen technischen Prüfungen, soweit über CI verfügbar.
2. **Umfangreiche KI-Video-, Debatten- und Profiloptimierungstests starten nur manuell.**
3. Ein manuell gestarteter Durchlauf darf autonom mehrere interne Verbesserungsschritte und lokale/Cloud-Regressionen abarbeiten; er bleibt stoppbar.
4. Die geprüfte **Gesamtverbesserung benötigt am Ende eine Nutzerfreigabe**.
5. Nach Freigabe werden nur die erlaubten versionierten Prompt-/Konfigurationsänderungen **direkt auf den Standardbranch** des festgelegten Repositories gepusht; keine dauerhaft unnötigen Nebenbranches.
6. Die freigegebene Konfiguration wird anschließend **automatisch in der Testumgebung aktiviert** und beim nächsten vorgesehenen Synchronisieren lokal verfügbar, ohne unbeteiligte Profile zu überschreiben.
7. Fehlgeschlagene Builds oder nachträglich erkannte Verschlechterungen führen zu einem nachvollziehbaren **Rollback auf die letzte funktionierende Version**, zum Beispiel durch einen gegenläufigen Commit; die Git-Historie darf nicht unkontrolliert überschrieben werden.

**Aktuell für diese Vision festgelegtes Dokument-Repository:** ErpeUser/DebateAI-final-public, Standardbranch **main**, Pfad **app/docs/VISION.md**. Ein historisch genanntes privates Repository mit anderem Standardbranch ist dadurch **nicht** automatisch mit dem öffentlichen Repository identisch. Referenzen und Schreibziele müssen stets konkret überprüft werden.

**Kosten und Betrieb:** Google-Cloud-Credits und möglichst günstiger Betrieb sind zu berücksichtigen. Eine Kostenanzeige und Ressourcentransparenz sind sinnvoll; **kein verpflichtendes Budgetlimit und keine automatische Kostenabschaltung**. Einfache Builds laufen automatisch nach Push; große Testserien nicht. Cloud-Testinstanz und lokaler Betrieb sollen denselben freigegebenen, versionierten Stand nutzen können. Testdaten, Web-Sitzungen und Provider-Berechtigungen dürfen nicht unkontrolliert vermischt werden.

## 16. Sicherheits-, Datenschutz- und Einwilligungspriorität

**Ausdrückliche Entwicklungspriorität: DebateAI wird zunächst privat und überwiegend lokal entwickelt und genutzt. Umfangreiche Datenschutz-, Sicherheits- und Compliance-Komfortfunktionen sind derzeit nachrangig. Sie sollen die Weiterentwicklung, das Einstellungsstudio und die Live-Qualität nicht unnötig verkomplizieren.**

**Diese Priorisierung hebt unverzichtbare Mindestmaßnahmen nicht auf:**
- Browser-Sitzungen und Zugangsdaten müssen angemessen geschützt und dürfen nicht im öffentlichen Repository oder in Bugmeldungen landen.
- Externe Anbieter, mögliche Kosten und Arten übermittelter Daten werden einmalig verständlich eingerichtet; danach sind nicht für jeden Aufruf neue Freigabedialoge nötig.
- Ohne eine bewusst aktivierte externe Route findet keine überraschende Cloud-Übertragung statt.
- **PII Shield ist im privaten lokalen Standardbetrieb deaktiviert**; für externe Wege kann eine bewusst auswählbare Schutzfunktion angeboten werden.
- Rechtlich erforderliche Einwilligungen und zulässige Aufnahmeformen bleiben relevant; private Nutzung beseitigt solche Grenzen nicht.
- Bei „komplett ohne Speicherung/Verbesserung“ werden für diese Sitzung keine dauerhaften lokalen Lern- oder Aufzeichnungsartefakte behalten.
- Absichtliche Löschungen dürfen nicht durch Update-, Retry- oder Backup-Pfade rückgängig gemacht werden.
- Vor öffentlichem Mehrnutzer- oder Produktivbetrieb sind Sicherheits- und Datenschutzmaßnahmen neu zu bewerten.

Die Anwendung ist für offen genutzte KI-Unterstützung gedacht; sie darf kein heimliches Mitsprache- oder Aufnahmeversprechen machen. Die konkreten rechtlichen und Provider-spezifischen Regeln sind vor der jeweiligen Nutzung zu prüfen.

## 17. Testqualität, unabhängige Bewertung und Abnahme

**Absolutes Freigabehindernis bleibt eine unzuverlässige oder faktisch falsche Empfehlung.** Weder eine schöne Oberfläche noch eine schnelle, aber falsche Antwort genügt. Qualitätsaussagen sind durch echte Tests und nachprüfbare Belege zu stützen.

**Kernmetriken und Prüfpfade:**
- **Rhetorik:** unabhängige menschliche Bewertungen deutscher Debatten, Nutzenquote, Natürlichkeit, Sprechbarkeit, argumentative Stärke, Qualität von Gegenfragen, Quellenredlichkeit sowie Bewertung beider Modi.
- **Fakten und Aktualität:** Fehler- und Halluzinationsquote, überholte Antwortkarten, Quellenvalidierung, korrektes Kennzeichnen nicht verifizierter Aussagen.
- **Timing:** Zeit bis zur ersten brauchbaren Antwort, finale Antwort, Tail-Latenz, Recherchebeginn/-ende, lokale und Web-Agentenlast, Reaktionsfähigkeit bei Unterbrechungen.
- **ASR und Sprecher:** WER/CER, RTF, Sprecherfehler, Dual-Track, Overlap, Gerätewechsel, Ausfälle, lange reale Windows-Sitzungen.
- **Agenten:** nachvollziehbare Rollen, kontextkonsistente Ergebnisse, geeignete Parallelität, kontrollierter Providerwechsel, kein unnötiges Doppeln von Arbeit.
- **Selbstoptimierung:** reproduzierbare Vorher-/Nachher-Vergleiche, versionsgebundene Testfälle, getrennte Optimierungs-/Prüfdatensätze, Regression und gegebenenfalls menschliche Referenzurteile.
- **Desktop/Release:** Installations-, WebView2-/GUI-, DPI-, Audio-, Update-, Migration- und Rollback-Tests; eindeutige Artefakt-/Commitbezüge, Hashes und gegebenenfalls Authenticode-Signierung.
- **CI:** Tatsächliche Log- und Testnachweise zählen. Ein Runner- oder Provisionierungsfehler darf nicht als erfolgreiche Codeabnahme umgedeutet werden.

**Aktueller Status darf nicht aus der Vision abgeleitet werden.** Laut [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md) sind unter anderem vollständige CI-/Structure-Gates, produktive Windows-Signierung und Distribution sowie reale Windows-Audio-/Provider- und quantitative ASR-/Rhetorik-Nachweise noch nicht vollständig abgeschlossen. Bereits vorhandene Test- oder Build-Erfolge müssen auf ihren konkreten Commit und ihren Geltungsbereich bezogen werden.

## 18. Funktionsumfang, Priorisierung und Entwicklung ohne unnötigen Neubau

Der erste ernsthafte Release ist ein **integriertes, belastbares Gesamtprodukt** mit funktionierendem lokalen Live-Kern, deutschsprachiger Audioverarbeitung, Sprechertrennung, zwei fachlichen Agentenrollen, zwei Rhetorikmodi, bester Antwort plus höchstens zwei Alternativen, einem gut nutzbaren Windows-Dashboard und einem **sichtbaren, interaktiven Einstellungs-/Modellvergleich**. **Kein bloßer Textchat-Prototyp.**

**Die vorhandene UI soll jetzt verbessert und perfektioniert werden** – nicht auf einen späteren unbestimmten Release verschoben. UI-Verbesserungen können parallel zur Stabilisierung von Browsern, Agenten und Testarchitektur erfolgen. Es wird **nicht** vorgeschrieben, erst eine komplett neue UI zu bauen oder das Einstellungsstudio bis nach der Cloud-Selbstoptimierung auszusetzen.

**Sinnvolle Arbeitsprioritäten, bei konkreter Evidenz anpassbar:**
1. Bestehende Architektur und Oberfläche vollständig prüfen, Defekte und bereits funktionierende Teile identifizieren.
2. Lokalen Live-Kern, Audio, Kontext, Recherche- und Web-Sitzungsstabilität absichern.
3. **Bestehende UI, Onboarding und Einstellungsstudio fortlaufend gezielt perfektionieren.**
4. Sichtbare Modellvergleiche, reproduzierbare Audio-/Video-Simulation und Qualitätsmessung ausbauen.
5. Autonome profilgebundene Optimierung, Cloud-Testinstanz und GitHub-Berichte kontrolliert integrieren.
6. Verlässlichkeit, Testabnahme, Releases und Qualitätsfortschritt fortlaufend belegen.

**Verfügbare bestehende Module behalten:** Die allgemeine Meeting-Analyse mit strukturierten Transkripten, Beobachtungen, Briefings, Fragen und Nachanalysen bleibt ein **optionaler separater Bereich**. Dokumentfunktionen und ältere Integrationen dürfen weiterbestehen, müssen aber ihren tatsächlichen Provider-/Lokalitätsstatus korrekt ausweisen. Videoanalyse, Vier-Move-/Mehragentensysteme und vertiefte Forschung bleiben wichtige, anhand Qualität und Nutzen zu validierende Erweiterungen. Weder Produktbreite noch experimentelle Prototypen dürfen als Releasebeweis gelten.

**Keine vorrangige Integrations-Offensive:** Kalender, CRM, Fremd-APIs, primär mobile Apps oder ein erzwungener Team-Workspace stehen hinter der Perfektionierung des Debattenkerns zurück. Keine verpflichtende Kontoanmeldung nur für lokale Nutzung. Monetarisierungsdruck ist kein Entwicklungsleitziel.

Die konkrete Feature-Matrix für eine Veröffentlichung darf **unverzichtbar / wichtig / experimentell** unterscheiden und klar ausweisen, was tatsächlich implementiert, getestet und freigegeben ist. Das ist keine Erlaubnis, unzuverlässige Kernfunktionen als fertig auszugeben.

## 19. Windows-Distribution, Open Source und Bestandswahrheit

Windows-Desktop hat Vorrang, einschließlich WebView2-/Desktop-Integration, Mikrofon-/Loopback-Betrieb, GPU-/Modellmanagement, sauberer Fehleranzeige und echter Hardwaretests. Frühere technische Bestandteile wie PyInstaller, PostgreSQL, ffmpeg, Tray/Overlay und Updater dürfen als vorhandene Ansätze geprüft und weitergenutzt werden; die Vision behauptet nicht, dass jedes frühere Bundle heute vollständig abgenommen ist.

DebateAI wird zunächst persönlich beziehungsweise als Open-Source-Projekt ohne Monetarisierungszwang entwickelt. **Langfristiges Ziel ist eine vollständige Open-Source-Veröffentlichung von App- und Infrastrukturcode**, mit dokumentierten Abhängigkeiten und möglichst reproduzierbaren Build-/Releaseabläufen. Dazu gehören ausdrücklich **keine** privaten Anmeldedaten, Sitzungs-Cookies, Profile, Audiomaterialien, Transkripte oder geheimen Schlüssel.

**Historische Quellvarianten und Provenienz:** DebateAI-Source war ein code-only Snapshot mit bewusst fehlenden internen Verträgen/Buildbestandteilen; DebateAI-final-public ist die umfangreichere öffentliche Konsolidierung. Ein früherer privater Master und ältere Audit-Commits sind **historische Vergleichsstände**, keine automatisch aktuelle Freigabereferenz. Öffentliche Repository-Inhalte und Build-Tests belegen nicht automatisch einen signierten, auslieferbaren Windows-Produktrelease. Einzelheiten stehen in [HISTORIE.md](HISTORIE.md).

Öffentliche Aussagen über Offlinefähigkeit, Cloudfreiheit, Mehrsprachigkeit, lokale Dokumentanalyse, unterstützte Provider und Reifegrad müssen **dem überprüften Code und realen Tests entsprechen**. Keine Marketingbehauptung darf vorhandene Abhängigkeiten oder offene Gates verdecken.

## 20. Verbindlicher Forschungs- und Analyseauftrag vor größeren Änderungen

Vor umfangreichen Architektur-, UI- oder Agentenänderungen wird der **tatsächliche Repository-Stand** untersucht. Bestehende Funktionen sollen verstanden, fehlerhafte Komponenten korrigiert und gute Implementierungen erhalten werden.

**Technisch zu untersuchen und anhand realer Tests zu entscheiden:**
- **Backchannel und vergleichbare Agentenarchitekturen:** Aufgabenverteilung, Koordination, Kommunikation, Recovery und übertragbare Gestaltungsideen; keine Kopie oder Produktabhängigkeit.
- **ChatGPT-Web-/Gemini-Web-Automatisierung:** verfügbare CLI-, MCP-, Browser- und Erweiterungswege sowie Funktions- und Plattformgrenzen.
- **Reasoning-Steuerung und dynamisches Agentenrouting:** tatsächlich unterstützte Denkstufen, Latenzen, Providergrenzen und belastbare Fallbacks.
- **Audio-/Video-Testverfahren:** Replay mit Zeitbezug, ASR-/Sprecherreferenzen, Störungstests, Human-Rating und belastbaren Evaluationsmetriken.
- **Profiloptimierung:** gezielte Prompt-/Konfigurationsänderungen, Regression, Kontextisolation, Kosten und Reproduzierbarkeit.
- **Hosting:** kostengünstige, möglichst durch Google-Credits gedeckte vollständige Testinstanz mit Browser-Sitzungen und Windows-/Cloud-Grenzen.
- **Bestehende UI:** aktuelle Navigationslogik, unnötige Optionen, Onboarding, Einstellungszustände und Nutzbarkeit vor jeder größeren Änderung prüfen.

**Faktenrecherche ist Aufgabe des Umsetzungsteams, keine offene Benutzerentscheidung.** Wo Webanbieter eine gewünschte Steuerung nicht zulassen oder technisch nicht zuverlässig ermöglichen, wird dies offen dokumentiert und eine möglichst funktional gleichwertige Alternative geprüft. Keine Abnahmekriterien durch unbewiesene Annahmen ersetzen.

## 21. Dokumentationsvertrag, Änderungen und offene technische Punkte

Diese Datei **VISION.md** ist die **zentrale, ausführliche und verbindliche Gesamtproduktvision**. Sie enthält die vollständigen Ziele und wesentlichen fachlichen Anforderungen. Die anderen Dokumente erfüllen weiterhin getrennte Aufgaben:

| Datei | Inhalt |
| --- | --- |
| [VISION.md](VISION.md) | Verbindliche Gesamtvision, gewünschte Benutzererfahrung, Architekturprinzipien, Prioritäten und Zielverhalten |
| [HANDBUCH.md](HANDBUCH.md) | Tatsächliche Architektur, Setup, APIs, Konfiguration, UI-/Designsystem, Deployment, Release und Betriebsverträge |
| [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md) | Aktuelle Lücken, nicht belegte Funktionen, technische Risiken, Abnahmekriterien und noch offene Gates |
| [HISTORIE.md](HISTORIE.md) | Datiertes Wissen, ersetzte Entscheidungen, historische Visionen, Commits und Evidenz |

**Prioritäts- und Statusregeln:**
- Produktanforderungen können als **unverzichtbar**, **wichtig** oder **experimentell** eingestuft werden.
- **Geplant**, **implementiert**, **getestet** und **freigegeben** sind klar getrennt.
- Neue Eigentümerentscheidungen können ältere Prioritäten und Implementierungsannahmen ersetzen; sie werden konsolidiert statt widersprüchlich nebeneinander weitergeführt.
- Erfolgreiche Tests, Builds und Releases werden anhand konkreter Versionen und Belege dokumentiert, nicht aus Absichtserklärungen abgeleitet.
- Bereits bekannte ältere Zielkonflikte sind hier soweit durch die Eigentümerentscheidungen lösbar **entschieden**: **Hart/Überzeugend** mit Wahl vor jeder neuen Sitzung und letztem Modus als Vorauswahl; **sichtbarer Modellvergleich statt Pflicht-Blindtest**; **beste Antwort plus maximal zwei Alternativen**; **gezielte Perfektionierung der bestehenden UI**; **lokaler Erstpfad mit ergänzenden Web-Agenten**; **manueller Teststart mit autonomer interner Optimierung und abschließender Freigabe**.

**Noch zu verifizieren, aber nicht als neue Grill-Me-Entscheidung offen:** Anbieterfähigkeit und Zulässigkeit von Web-Steuerungen, echte Windows-Zielhardware, konkrete Modell-/Provider-Matrix, Kosten und technische Grenzen der Cloud-Testinstanz, Windows-/Provider-Abnahme, rechtliche Besonderheiten der jeweiligen Aufnahmenutzung sowie noch nicht erfüllte Release-Gates. Diese Aufgaben gehören in die technische Bestandsaufnahme und in [OFFENE_PUNKTE.md](OFFENE_PUNKTE.md).

## 22. Infrastruktur-Abnahme und überprüfbare Betriebsgrenzen

Variante 3 der Abnahme verbindet lokale Produktarbeit mit einer getrennten
externen Betriebsabnahme. Die Anwendung darf einen lokalen Vertrag als
implementiert markieren, wenn Code und reproduzierbare Tests ihn belegen. Eine
vollständige Produkt- oder Releasefreigabe benötigt zusätzlich den passenden
aktuellen Commit, das konkrete Artefakt und die reale Betriebsumgebung.

### Gemeinsamer Zustand

Runs, Ratings, Replay-Journale und Jobs müssen nach ihrer jeweiligen
Schutzklasse ausdrücklich als lokal, prozessweit oder workerübergreifend
gekennzeichnet sein. Ein Prozesscache darf keinen persistenten oder
workerübergreifenden Zustand vortäuschen. Quality-Lab-Runs und Ratings werden
deshalb in einem gemeinsamen Datenbank-Store gehalten; Apply und Rollback
bleiben bis zu einem geprüften Holdout und einer kontrollierten Promptversion
fail-closed.

Für WebSocket-Replay, Transkriptionsjobs und PII-Indizes gilt weiterhin die
stärkere Multiworker-Anforderung. Ein geteilter Adapter muss Cursor-, Epoch-,
TTL- und Löschverträge über Workerwechsel und Neustarts erhalten, ohne
Duplikate oder veraltete Snapshots zu erzeugen. Prozesslokale Bounds bleiben
ein Schutz, ersetzen diesen Nachweis aber nicht.

### CI, Cloud und Release

Jeder Abnahmenachweis bindet sich an Repository, Branch, Commit-SHA,
Workflow-Run, Artefakt-Hash und Zeitpunkt. Ein grüner Testlauf auf einem
anderen Tree bestätigt keinen aktuellen Releasezustand. Cloud-Testinstanzen
dürfen Quellcode, Sitzungsdaten und Credentials nur über ausdrücklich
freigegebene Pfade erhalten. Fehlerberichte werden dedupliziert,
secretbereinigt und reproduzierbar abgelegt.

Ein signiertes Windows-Release benötigt einen frischen Build, eine verifizierte
Authenticode- oder autorisierte Remote-Signatur, ein Manifest mit Hashes und
einen getesteten Update-/Rollbackpfad. Ein vorhandener Runtime-Smoke darf
diesen Nachweis nicht ersetzen. Echte Audio-, Provider-, LAN- und
DNS-Rebinding-Abnahmen bleiben externe Gates mit autorisierter Hardware,
Konten und Netzwerkumgebung.

### Statusregeln

`PARTIAL_VERIFICATION` ist der zulässige Gesamtstatus, solange ein absolutes
Structure-Gate oder ein externer Produktnachweis offen ist. `DONE` darf erst
verwendet werden, wenn Structure, Tests, Security, Docs-Site, Releasepfad und
die für die jeweilige Produktbehauptung erforderlichen Windows-, Audio-,
Provider- und Multiworker-Nachweise auf demselben überprüften Stand grün sind.
Dokumentationsänderungen dürfen keinen offenen Nachweis in einen grünen Status
umbenennen.

---

**Herkunft und Vorrang:** Vollständige VISION.md mit Stand 19.11.2026, aktualisierte Produktentscheidungen aus sechs Grill-Me-Runden (insgesamt Fragen 1–119 mit individuellen Freitextpräzisierungen) bis 21.11.2026, sowie die getrennt dokumentierten technischen und historischen Nachweise. **Dieses Dokument ist ein Zielvertrag, keine Behauptung über die Implementierung.**
