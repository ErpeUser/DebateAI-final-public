# DebateAI - Quellcode-Integrationsnachweis 2026-11-11

Basisfeature 9d88baae677083770c2c81943687713d6fc393a6; vorheriger master d07a6581f91944434f691bd1295b39a002b938b5. Finaler Push/Merge wird erst durch den tatsaechlichen GitHub-Commit/PR-Nachweis belegt. Dieser Bericht ist KEINE fertige Windows-Releasefreigabe.

## Frische Tests

| Bereich | Bestanden |
|---|---:|
| Verfuegbare Python-Regressionen fuer Benchmark, Export, Prozessbesitz und bestehende Kalibrierungs-/Upload-/Aktivitaetsvertraege | 69 |
| JavaScript-Kern und neue Import-/Hash-/Fehlernenner-Vertraege | 19 |
| Chromium-Labor mit expliziten API-/Speicherfixtures | 4 |
| PWA-Manifest/HTML-Metadaten | 2 |
| **Gesamt dieses Laufs** | **94** |

Null fehlgeschlagene Tests in diesem Umfang. Zusaetzlich Python compileall und node --check fuer die geaenderten Labor-JavaScriptdateien erfolgreich. Python 3.13.5, Node22.16.0, Linux. Releaseziel bleibt Python3.12/Node24/Windows. Arbeitsumgebung: hashgepruefte TEILKOPIE, kein vollstaendiger Originalcheckout und nicht der Windows-PC. Nicht geaenderte GitHub-Dateien werden durch base_tree beibehalten; niemals die Teilkopie als vollstaendigen Ersatzbaum pushen.

```sh
PYTHONPATH=source/backend python -m unittest discover -s source/backend/tests -p 'test_*.py' -v
node --test source/frontend/calibration-tests/*.test.mjs
python -m unittest discover -s source/frontend/calibration-tests -p 'test_*.py' -v
node --test --test-name-pattern='manifest declares|HTML links' source/frontend/scripts/verify-pwa-assets.mjs
python -m compileall -q source/backend
node --check source/frontend/public/calibration/core.mjs
node --check source/frontend/public/calibration/lab.mjs
```

Im vollstaendigen Checkout entdecken diese Befehle zusaetzliche Tests. 69 ist nicht die Gesamtprojektzahl. Alte 100/141 nicht addieren oder als heute erneut bestanden ausgeben. PWA-PNG-/Maskablechecks wurden hier nicht erneut ausgefuehrt; unveraenderte Checks bleiben im Releasegate. Kein npm-ci/TypeScript/Vite-Gesamtbuild und keine wirkliche Modellausfuehrung behauptet.

Die Kindprozesstests starten/killen/reapen echte eigene Pythonprozesse. Der sprachuebergreifende Test exportiert durch den echten Python-Exporter und importiert mit dem echten JavaScript-Validator samt Hashpruefung. Modell/DB/Ereignisproduzenten sind teilweise Doubles; Playwright rendert echte Labor-Dateien mit kontrollierten APIs/Speicher. Kein Mikrofon-/WebView2-/Hardware-/Faktenqualitaetsnachweis.

## Reproduzierte und behobene Fehler

Optionale Gegenfrage verursachte einen falschen Fehler; null konnte als nichtleerer Text gelten; alte/leer gestreamte Ereignisse verfaelschten erste sprechbare Latenz; fehlgeschlagenes Headless-ACK durfte Erfolg werden; nach Teilantwort fehlte wirksames Finalzeitlimit; Elternabbruch konnte eigene Kindprozesse hinterlassen. Neue Tests decken diese Faelle ab. Quarantaene verhindert Wiederverwendung nach Timeout, behauptet aber kein physisches Threadende.

Native lokale Modellliste wird begrenzt geprueft, fehlende/remote Modelle nicht automatisch geladen. Neue Paare verwenden dieselbe kausale Fixture und beide Modi; Fehler bleiben im Nenner, keine Fakeantwort. Labor prueft Kontexttext-Hashes und konsistente Versuchszaehler; ausschliesslich fehlgeschlagene Experimente bleiben sichtbar, aber nicht votierbar. Unberuehrte Skalen werden nicht als 3/5 erfunden. Runbook-Loeschen-vor-Entpacken entfernt. PWA-Metadaten und Test gemeinsam migriert.

## Review und Recherchegrenzen

Drei Perspektiven als getrennte Selbstpruefung: Sicherheit/Lifecycle, Messqualitaet/UI, Produkt-/Releasevertraege. Kein unabhaengiger Coding-Subagent verfuegbar. Drei echte Firecrawl-Rechercheagenten bearbeiteten nur oeffentliche Quellen: ASR abgeschlossen; Bewertung und Zuverlaessigkeit mit Teilresultaten am Limit. Kein privater Code an diese Agenten. Context7 fuer Python3.12-asyncio benutzt. RESEARCH_DE.md trennt Quellen, Umsetzung und Experimente.

GitHub-CI hatte vor der neuen Publikation Fehler ohne Runner/Schritte. Das ist kein bestandenes Gate und kein belegter Produktfehler; keine Billingursache behaupten, keine Schutzregel umgehen. Nach Push den neuen Checkstatus lesen. Keine Signatur/Releaseveroeffentlichung in diesem Durchlauf.

## Verbleibend

Vollstaendige Projekt-/Security-CI; echter Windows-Build samt Archiv/Update/Rollback; konsistente EXE-/Updater-/Bundle-/Archiv-/Paketmigration; echte Repository-Umbenennung und gegebenenfalls Loeschung eines bereits integrierten Branchs mit passendem Admin/Git-Werkzeug; reale Daten/DPAPI/Playbooks/Provider/Audioabnahme; tatsaechliche deutsche Modell-/Nutzwertmessung; eigene signierte Veroeffentlichung mit realen Zertifikaten/Infrastruktur. DESKTOP_FINAL.md enthaelt die exakte Fortsetzung. Ein erfolgreicher Source-Merge ist kein fertiger Windows-Release.
