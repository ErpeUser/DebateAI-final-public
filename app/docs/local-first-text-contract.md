# Local-First-Textvertrag

Stand: 2026-11-20.

DebateAI hat zwei getrennte lokale Verträge:

- **Lokale Transkription:** Der Desktop-Default ist local-whisper-base (oder ein lokal gemessenes, kompatibles ASR-Modell). Das Audio verlässt den Rechner nur, wenn der Nutzer ausdrücklich einen Cloud-/Live-Gateway-Pfad wählt und der Privacy-Vertrag dies erlaubt.
- **Lokale Textanalyse:** Ein lokaler Textpfad ist über einen aktivierten OpenAI-kompatiblen Custom Endpoint möglich (zum Beispiel LM Studio, Ollama, vLLM oder LiteLLM). Er ist erst produktiv aktiv, wenn base_url, Modell-ID und ein optionaler API-Key im Endpoint-Dialog geprüft wurden; ohne Endpoint bleibt der konfigurierte Provider-Default aktiv.
- **Hybrid-Default:** Provider-Empfehlungen wie Gemini oder GPT beschreiben den aktuell verfügbaren Text-Provider, nicht eine lokale Verarbeitung. Die UI muss deshalb „lokal“, „Cloud“ und „experimentell“ getrennt kennzeichnen und darf aus einer lokalen ASR-Auswahl keine lokale Textverarbeitung ableiten.

## Konfigurationsmatrix

| Pfad | Standard | Aktivierung | Privacy-/Betriebsnachweis |
| --- | --- | --- | --- |
| Lokale ASR | local-whisper-base | Modell lokal installiert und Fit-Test bestanden | Audio bleibt lokal; CPU/GPU- und Latenzwerte aus dem Calibration-Lauf |
| Lokaler Text | kein automatischer Provider | geprüfter Custom Endpoint + lokales Modell | Endpoint-Probe, Modell-ID und Fehlerstatus werden gespeichert |
| Cloud-Text | Provider-Routing laut Modellkatalog | Provider-Key/Account vorhanden | Provider- und Kostenhinweis im Modellkatalog |
| Lokale Live-Caption | experimentell | explizite Parakeet-/Live-Caption-Auswahl | CPU-lastig; Hardwareabnahme separat erforderlich |

Konfiguration und UI müssen diese Matrix bei neuen Modellen oder Pipelines fortschreiben. Ein Wechsel auf „lokal“ darf nie stillschweigend einen Cloud-Fallback aktivieren; ein fehlender lokaler Endpoint muss als nicht verfügbar erscheinen.
