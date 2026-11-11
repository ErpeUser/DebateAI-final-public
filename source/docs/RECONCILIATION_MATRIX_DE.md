# Abgleich beider Lieferungen - 2026-11-11

Basis: Recovery-ZIP SHA256 5e26c00f2615d7712efb1e2c648ba307db6c013ddb20964a672c07a135f63d7b und Featurestand 9d88baae677083770c2c81943687713d6fc393a6. Historische 100/141 Tests sind nicht automatisch heutige Tests. Codeintegration und native Produktabnahme bleiben getrennt.

| Punkt | Entscheidung / integrierter Ort | Grenze |
|---|---|---|
| Git-Kollisionsschutz | Neuere eingebettete Version in scripts/sync_final_workspace.py behalten; kein altes Hilfsskript darueberkopieren. | Echter Windows-Checkout noch synchronisieren. |
| ASR-Modellcaches | Neueren local_transcriber.py-Fix erhalten, Kalibrierung ohne automatische Downloads. | Reale Modellinitialisierung pruefen. |
| Upload/Decoder | Integrierte ASGI-Grenze, diagnostic_audio und asynchroner Decoder erhalten. | Native Bundle-Gates offen. |
| Worker bei Abbruch | Exklusive Diagnosejobs erhalten; Produktions-Replay/Prozess-Timeout und Quarantaene ergaenzt. | Cancellation beweist kein physisches Threadende. |
| apply_package.py | Historischer ZIP-Installationshelfer absichtlich nicht als zweiter Installer eingebaut. Direkte Git-Integration ersetzt seinen Zweck. | Seine neun Tests nicht als neue Produkttests zaehlen. |
| Gefaehrlicher Installer | DESKTOP_FINAL.md wirklich ersetzt; windows-final-recovery.md integriert. Kein Loeschen vor Entpacken/Pruefung. | Native Installation/Rollback noch ausfuehren. |
| 13 deutsche Testtypen | Vorhandenes Labor mit Aufnahme/Import, gleichem Clip, WER/CER, RTF, Zahlen/Negation/Stille behalten. | Kein Dual-Track-/Streaming-/Sprecherbeweis. |
| Blindvergleich | Mehrfall-Import/zufaellige A/B/Identitaet erst nach Wahl behalten; echte Kontext-Hashpruefung und Fehlernenner hinzugefuegt. | Nutzen ist kein Faktenlabel. |
| Bewertungen | Unberuehrte Skalen erzeugen nicht mehr automatische 3/5-Werte. | Historische Exporte mit Defaults nicht als bewusste Ratings interpretieren. |
| Echte Modellausgaben | backend/scripts/benchmark_blind_pair.py ruft bestehenden Produktionsbenchmark in isolierten sequentiellen Prozessen auf, beide Modi, 20 deutsche Turns. | Source-CLI, kein Frozen-UI-Generierungsbutton; reale Modellmessung fehlt. |
| Revision/Modus/Latenz | Mode korrekt propagiert; alte/leere Modellfragmente liefern keinen falschen ersten Zeitpunkt; optionale Gegenfrage und Headless-ACK korrekt behandelt. | Headless-ACK ist keine Bildschirmanzeige. |
| Herkunft/Privacy | Lokale native Modellliste begrenzt pruefen; Cloudaliases/URLcredentials/unerwartete Routen abweisen; keine rohen Fehler/Secrets exportieren. | Manipulativer lokaler Proxy erfordert Betreiber-/Netzpruefung. |
| Settings/Persistenz | Keine aktive Modell-/Profilumstellung. Speicherung bewusst; Versuchszahlen und Herkunft im Export. | Kein automatisch behaupteter Sieger. |
| In-App-Zugang | Neueren Dialog behalten, Haupt-React-Baum bleibt montiert. | WebView2-Mikrofon auf Windows pruefen. |
| PWA-Identitaet | Manifest und vorhandener PWA-Test gemeinsam auf DebateAI abgeglichen. | Keine neue Ikonengrafik behaupten. |
| Forschung/Matrix | RESEARCH_DE.md, diese Matrix und DEEP_RESEARCH_AUFTRAG_DE.md nun versioniert. | Ein Rechercheagent fertig, zwei Teilresultate am Limit. |
| Codex-Auftrag | Aktueller DESKTOP_FINAL.md ersetzt veraltete ZIP-Overlay-/Feature-Branch-Pflicht. | Alle 15 Windows-Gates bleiben verbindlich. |
| Datenidentitaet/Update | Neuere kompatible DebateAI-Datenpfade und eigener expliziter API-Updatekanal behalten. | EXE/Updater/Archiv-/Paketmigration noch nicht vollstaendig. |
| Repository-Rename | Vorhandener gepruefter rename_debateai_repository.py bleibt. | Reale Adminaktion nicht durch Helferexistenz erledigt. |
| NeMo/Overlay/Host-Guard aus abgebrochenen Logs | Keine unbelegten Fertigmeldungen uebernehmen; vorhandene Pfade gezielt testen. | Nicht als in diesem Durchlauf neu implementiert ausgeben. |

Vision bleibt kurze sprechbare lokale Hilfe, korrekte deutsche Sprache und Revisionen, Argumentgedaechtnis, optionale Gegenfrage, Hart/Ueberzeugen, Nutzerkonfiguration und getrennte externe Hintergrundanalyse. Mehr Agenten sind kein eigenstaendiges Qualitaetsziel.
