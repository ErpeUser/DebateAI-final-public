# Debate AI V6 – verbindliche Produktvision
Stand: 2026-11-10. Diese Datei dokumentiert das Produktziel, nicht den Nachweis fertig getesteter Funktionen.

## Leitbild
Debate AI ist ein deutschsprachiger, datenschutzbewusster Echtzeit-Debattenassistent für Windows: Er hört Mikrofon und – sofern freigegeben – Systemaudio, erkennt argumentative Züge und liefert **vor dem Verpassen des Gesprächsmoments** eine kurze, sofort sprechbare Antwort oder eine strategisch stärkere Gegenfrage. Die Oberfläche unterstützt einen Menschen beim Denken und Sprechen; sie spricht nicht autonom für ihn und behauptet keine erfundenen Fakten.

## Nicht verhandelbare Qualitätskriterien
1. **Echtzeit zuerst:** lokale Sofortantwort unabhängig von langsamer Recherche/Tiefenanalyse; Revisionen und neue Aussagen verdrängen alte Ergebnisse; keine parallelen, sich gegenseitig überholenden Generierungen; zuerst verständlicher Sprechtext.
2. **Deutsch und natürliche Rhetorik:** keine abstrakten Romanantworten; klare Position, ehrliche Prämissenprüfung, Beweislast, gezielte Rückfrage, gut merkbare Formulierung. Debattenmodi 'Überzeugen' und 'Hart' bleiben; Stimme und persönliche Perspektive des Nutzers bewahren.
3. **Local-first und Wahlfreiheit:** Ollama/Qwen als schneller lokaler Standardweg, lokale Whisper-/Parakeet-/weitere wirklich kompatible ASR-Backends; ChatGPT, Gemini und die bestehenden Bridges für optionale Tiefe. Provider nur dann einsetzen, wenn installiert, angemeldet, freigegeben und tatsächlich geprüft. Niemals Cloudkosten/Übertragung durch einen stillen Test auslösen.
4. **Audiotreue:** getrennte Mikrofon- und Systemaudiospuren, 16-kHz-PCM-Verarbeitung, Ausfall- und Gerätewechselbehandlung; Erkennen von Sprache, Sprecherwechsel und Transkriptkorrekturen.
5. **Belegqualität:** gelesene Quellen von Annahmen trennen; keine halluzinierten Nachweise, verdeckten Modellwechsel oder Scheinsicherheit. Argumentgedächtnis darf veraltete Claims nicht als aktuell verkaufen.
6. **Windows als Hauptprodukt:** existierender lokaler Checkout, tatsächliche EXE, WebView2, PostgreSQL, ffmpeg, Ollama, Bridges, Tray und Overlay müssen über einen reproduzierbaren, sicheren Updatepfad dieselbe Releaseversion verwenden.
7. **Nutzerdaten behalten:** Datenbanken, lokale Modelle, Profile, persönliche Prompts, Playbooks, Credentials, Browser-Sessions und DPAPI-Schlüssel nie durch Code-/EXE-Updates überschreiben. Code darf veraltete lokale Versionen ersetzen; echte einzigartige Verbesserungen werden kompatibel integriert.
8. **Messbarkeit statt Bauchgefühl:** objektive ASR-Fehlerrate, Wort-/Satzvergleich, Erstreaktionslatenz, finale Antwortlatenz, Antwortqualität, Sprechbarkeit, Ressourcenlast, Stabilität, Offline-/Privacy-Verhalten, Fehlerfälle, reproduzierbare Fixtures. Keine universelle 'beste' Einstellung behaupten, wenn Hardware/Testmaterial nicht geprüft sind.

## Sprachlabor: einmal sprechen, fair vergleichen
In Admin / Einstellungen ein benutzbares, responsives **Sprachlabor** bereitstellen. Ein vorformulierter deutscher Satz wird angezeigt; der Benutzer spricht ihn ein oder lädt eine vorhandene Audiodatei hoch. Dieselbe unveränderte Aufnahme wird an die ausgewählten verfügbaren ASR-Modelle geschickt, nicht jedes Modell mit neuer Sprache gefüttert. Unterstützte Messwerte: erkannter Wortlaut je Modell, Wortfehlerrate (WER) gegen editierbaren Referenzsatz, Laufzeit, Real-Time-Factor (RTF), Fehlerstatus und lokale/Cloud-Herkunft. Eine Aufnahme mit Stille, falscher Sprache, Hintergrundgeräusch, Eigennamen, Zahlen und aufeinanderfolgenden Korrekturen sind relevante Fälle. Verfügbarkeit muss vor der Ausführung geprüft werden; API-/Cloudkosten nur mit expliziter Opt-in-Bestätigung. Aufnahme und erkannte Texte bleiben lokal und werden nicht ungefragt dauerhaft gespeichert. Fehler und Modellgrenzen sichtbar machen.

Empfohlene deutschsprachige Beispielsätze (editierbar, keine echten Personendaten):
- 'Sie behaupten, erneuerbare Energien seien unzuverlässig, weil nachts keine Sonne scheint.'
- 'Das klingt plausibel, aber welche belastbaren Daten stützen Ihre Schlussfolgerung?'
- 'Wenn die Kosten um 15 Prozent sinken, warum steigt dann der Gesamtpreis?'
- 'Ich unterscheide zwischen einer unbelegten Behauptung und einer nachprüfbaren Quelle.'
- 'Moment, ich korrigiere mich: Nicht 2023, sondern 2024 ist der Vergleichszeitraum.'
- 'Überprüfen wir die Voraussetzung, bevor wir über die Folgen sprechen.'

## Antwortlabor: echter fairer Blindvergleich
Ein zweiter Abschnitt, **Antwortlabor**, lässt eine gegnerische These, eigene Position und Stil/Modus eingeben, optional den Sprachlabor-Transkripttext übernehmen. Zwei ausgewählte tatsächlich verfügbare Modelle/Promptvarianten erhalten dieselbe Eingabe und dieselben erlaubten Kontextquellen. Vor Wahl eines Siegers stehen **Antwort A / Antwort B ohne Modellnamen** nebeneinander (Reihenfolge deterministisch randomisiert pro Test); Bewertung nach sofortiger Nutzbarkeit, Natürlichkeit, Präzision, argumentative Stärke, Gegenfrage, Quellenredlichkeit und Latenz. Nach der Bewertung Identitäten, Modellversionen, Prompt-Hash, technische Laufzeit und Kostenhinweis aufdecken. Ungeprüfte Cloud-Modelle nicht als live-vorhanden darstellen. Keine automatische Übernahme des Siegers in Produktion. Der Mensch kann Testergebnisse exportieren und **erst nach bewusster Bestätigung** eine getestete Empfehlung übernehmen; Rückgängig-/Wiederherstellungsweg bereitstellen.

## Selbsttests und Abnahmekriterien
- Deterministische Unit-/Contract-Tests für Routing, Streaming, JSON, Revisionen, falsche/fehlende Daten, Timeout, Parallelität, Tokenlimits, Eingabevalidierung, Recorder-Lebensdauer und sichere Konfigurationsübernahme.
- Integrationstest für Windows-Audio, On-device-ASR und WebSocket-End-to-End (nur auf realer Hardware als bestanden kennzeichnen).
- Offline/Privacy-First ohne unerwartete Cloudanfragen; externe Logins/Keys niemals extrahieren, übertragen oder in Reports zeigen.
- Belastungstest während einer laufenden Debatte; Labor darf keine Audio- oder Qwen-Echtzeitkapazität rauben. Livegespräch soll Labor-Benchmarks blockieren oder bis danach zurückstellen.
- Nutzeroberfläche: Desktop, schmale Fenster/Mobilbreite, Tastaturbedienung, Screenreader-Labels, Fehlerfälle, kein stilles Verschwinden einer Aufnahme.
- Windows: frischer Start und Update mit Datenmigration, Wiederstart, Update- und Rollback-Smoketest, Prüfsumme, Nachweis des tatsächlich ausgeführten EXE-Pfads.

## Bewusste Nicht-Ziele
Keine unkontrollierte Neuarchitektur; kein ungefragtes Löschen von Nutzerprofilen oder lokalen Verbesserungen; kein Auto-Apply des A/B-Siegers; kein erfundener Windows-Hardwaretest; keine automatische Veröffentlichung eines signierten Releases ohne Zertifikat/Freigabe.

## Vorrang und Bezug
Zusammen lesen: `/AGENTS.md`, `/source/AGENTS.md`, `source/docs/windows-final-runbook.md`, `source/docs/releasing.md` und `source/docs/FINAL_STATUS_AND_OPEN_ITEMS.md`. Dieses Dokument beschreibt **was** das Produkt leisten soll; die anderen Dateien regeln Arbeitsweise, Ausführung und aktuellen Nachweis.
