# Debate AI – gezielte Optimierung (2026-11)

## Maßstab

Die Änderung priorisiert die erste brauchbare, natürlich sprechbare Debattenhilfe innerhalb weniger Sekunden. Bestehende Debattenmodi, die lokale Echtzeitspur, externe Hintergrundanalyse, Recherche, Argumentgedächtnis und die Windows-Overlay-Nutzung bleiben erhalten.

## Nachgewiesene Engpässe

- `AgentOrchestrator._schedule_debate_revision()` brach eine laufende Antwort bei jedem neuen Zwischen-Transkript ab. Bei kontinuierlicher Sprache konnte dadurch kein vollständiges Ergebnis entstehen.
- `SemanticArgumentMemory.search_targets()` führt ONNX-Embedding-Berechnungen synchron aus. Der Aufruf lag im Live-Pfad und konnte den asyncio-Event-Loop blockieren.
- Das getrennte Overlay fragte den Backend-Endpunkt alle 600 ms ab und zeigte immer `answer_now`, auch wenn das Modell `primary_move=question` gesetzt hatte.
- Die Browser-Aufnahme vertraute darauf, dass `AudioContext({sampleRate: 16000})` in jedem Browser tatsächlich 16 kHz liefert. Bei abweichender nativer Rate wurde das PCM-Signal zeitlich falsch interpretiert.
- Die UI verwendete für die beiden verbindlichen Modi uneinheitliche Bezeichnungen und erlaubte `NaN` als Argumentgedächtnis-Schwellenwert.

## Umgesetzte Änderungen

1. **Bedingtes Live-Coalescing**
   - Vor dem ersten sichtbaren Modell-Teilstück wird eine veraltete Revision weiterhin abgebrochen.
   - Sobald eine sprechbare Teilantwort sichtbar ist, bleibt der Worker aktiv, setzt nur eine ausstehende neueste Revision und veröffentlicht die laufende Antwort fertig. Danach wird genau der neueste Stand analysiert.
   - Finale Transkriptänderungen bleiben geschützt: eine alte Antwort darf bei einem abgeschlossenen neuen Segment nicht die sichtbare Karte überschreiben.

2. **Nicht-blockierendes Argument-Retrieval**
   - Support-Kontext, semantische Suche und Hintergrund-Recherche laufen über `asyncio.to_thread` außerhalb des WebSocket-Event-Loops.
   - Die gefundenen Claim-IDs werden nur übernommen, wenn Claim und Transkript-Snapshot nach dem Thread-Aufruf noch übereinstimmen; ein abgebrochener älterer Aufruf kann dadurch keine neue Revision umleiten.
   - Die synchrone Hilfsfunktion bleibt für Tests und nicht-async Aufrufer erhalten.

3. **Strategische Overlay-Auswahl**
   - `primary_move=question` zeigt zuerst die Gegenfrage und stellt die Sofortantwort sekundär dar.
   - Das Overlay pausiert im unsichtbaren Zustand und reduziert die Fallback-Abfrage auf 1,2 Sekunden.

4. **Stabile 16-kHz-Audioverarbeitung**
   - AudioWorklet- und ScriptProcessor-Fallback resampeln explizit aus der tatsächlichen `AudioContext.sampleRate` auf 16 kHz.
   - Wenn ein Browser die angeforderte Rate ablehnt, wird ein normaler Kontext geöffnet und derselbe Resampling-Pfad verwendet.

5. **Deutsche Produktoberfläche**
   - Die Modi heißen einheitlich **Hart** und **Überzeugen**.
   - Der Ähnlichkeitswert wird endlich geprüft und auf 0,10–0,95 begrenzt; leere oder nicht-finite Eingaben werden verworfen.

6. **Live-Prompt und lokales Routing**
   - Der aktive Live-Prompt verlangt jetzt immer eine streambare `answer_now`-Antwort und zusätzlich nach Möglichkeit eine Gegenfrage. `primary_move` bestimmt weiterhin die Reihenfolge.
   - Der native Qwen/Ollama-Debattenpfad hängt nicht mehr am Standardport 11434. Eigene Ports und lokale Proxy-Endpunkte behalten dadurch `think=false`, Kontext- und Ausgabebegrenzung.

## Verifikation

- Python-Syntaxprüfung des geänderten Orchestrators: erfolgreich.
- Die vorhandene Testlogik für Abbruch vor dem ersten Teilstück bleibt unverändert.
- Die vorhandene Testlogik für sichtbare gestreamte Antworten wird durch das neue Coalescing unterstützt.
- Die bestehende Claim-/Revision-Sperre bleibt für finale Transkripte aktiv.

## Grenzen und nächste Messung

Die Umgebung enthält kein laufendes Windows-Audiogerät, kein Ollama-Modell und keine Provider-Sitzung. Deshalb wurden keine realen TTFT-Messungen und keine End-to-End-Diarisierung ausgeführt. Vor einem Release sollten die vorhandenen Benchmark-Skripte mit mindestens 20 deutschen Debattenfällen laufen und TTFT, finale Antwortzeit, Abbruchrate, sichtbare Antwortquote, Audio-Drops sowie Nutzerbestätigungen messen. Die Änderungen ersetzen keine Qualitätsbewertung der lokalen Qwen-Konfiguration und keine Prüfung der Provider-Anmeldungen auf einem realen Windows-System.
