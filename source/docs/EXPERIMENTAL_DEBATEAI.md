# Experimentell DebateAI

## Modi

`pipeline_mode: standard` bleibt der Default und erhält den bisherigen Live-Copilot-Ablauf. `pipeline_mode: experimental_debateai` aktiviert nur die neue Debatte-Kette:

1. Das Teiltranskript wird sofort an das lokale Modell gegeben.
2. Das Modell erzeugt Widerspruch, Beispiel/Analogie, Gegenfrage und Widerlegung.
3. Es wählt einen Zug. Nur dieser steht groß als „Jetzt sagen“; die anderen Züge erscheinen als aufklappbare Blobs.
4. Zwischenstände bleiben vorläufig und werden bei jeder neuen Transkript-Revision ersetzt. Ein langer Beitrag muss nicht vollständig beendet sein.
5. Recherche und adversariale Analyse laufen im Hintergrund nur bei Intervall, manueller Anforderung oder einem finalen Checkpoint.
6. Externe Befunde werden in den lokalen Integrationsschritt übernommen. Die UI stellt keine Anbieterantworten gegenüber.
7. Consolidated Analyst beobachtet weiterhin den gesamten Gesprächsverlauf und behält die bestehenden Doppelstandard- und Konsistenzprüfungen.

Die sichtbare Antwort stammt damit immer aus dem lokalen Antwortvertrag. Quellen, externe Gegenargumente und Unsicherheiten bleiben am Claim und an der Revision gespeichert.

## Rechercheanbieter

Wikipedia und DuckDuckGo sind global deaktiviert. Die Runtime filtert beide IDs auch dann heraus, wenn eine alte JSON-Konfiguration sie noch enthält. Recherche verwendet zuerst ChatGPT Web / Oracle und kann auf Gemini Web, Gemini API oder CLIProxy zurückfallen. Die Oracle-Integration behält ihre Single-Flight-Sperre für das dedizierte Browserprofil; der experimentelle Scheduler darf dadurch keine ungetesteten parallelen Browserprofile erzeugen.

## Video- und Sprachprofilpipeline

`source/backend/scripts/video_eval_pipeline.py` verarbeitet einen lokalen Audio-/Videoexport mit Google Cloud Speech-to-Text. `GOOGLE_CLOUD_PROJECT` und gültige Google-Anmeldedaten müssen gesetzt sein.

Das erzeugte JSON-Artefakt enthält:

- vollständige Transkriptsegmente mit Zeitstempeln und optionalen Sprecher-Tags,
- Quellenkandidaten aus URLs, DOIs und Studienverweisen,
- Rhetorikprofil mit Frage-, Widerlegungs- und Analogie-Raten,
- reproduzierbare Evaluationsfälle pro Segment,
- einen Hinweis, dass das Rohtranskript nicht automatisch als Referenzantwort gilt.

Die Quellenkandidaten werden anschließend durch die KI-Webrecherche verifiziert und im Artefakt ergänzt. Prompt-, Modell- oder Stiländerungen werden nicht automatisch in Produktion übernommen. Ein Review-/Eval-Lauf muss zuerst eine Verbesserung nachweisen; erst danach wird eine Änderung bewusst aktiviert.

Beispiel:

```bash
python source/backend/scripts/video_eval_pipeline.py --audio ./debate.wav --video-id debate-001 --out ./artifacts/debate-001.json --speaker-diarization --style-profile ./artifacts/rhetoric-profile.json
```

Lange Audio-/Videodateien werden vor der synchronen Google-Anfrage automatisch in 45-Sekunden-PCM-Abschnitte geteilt und auf die Originalzeitstempel zurückgesetzt. Die Live-Pipeline wartet nicht auf diese Batchauswertung; ffmpeg muss für Videodateien und lange Dateien verfügbar sein.

Für mehrere Videos kann eine JSON-Liste verarbeitet werden:

```json
[
  {"video_id": "debate-001", "audio": "./001.wav", "source_url": "https://example/video"}
]
```

```bash
python source/backend/scripts/video_eval_batch.py --video-list videos.json --out-dir ./artifacts --speaker-diarization
```

Nach dem Erzeugen mehrerer Videoartefakte kann ein leakage-sicherer Evaluationssplit und ein blinder Paarvergleich erzeugt werden:

```bash
python source/backend/scripts/video_eval_evaluate.py \
  --artifacts-dir ./artifacts \
  --out ./artifacts/evaluation-manifest.json
```

Der Evaluator hält ein Video und dieselbe Claim-Familie immer in demselben Split und erzeugt Test-Paare mit den neutralen Labels A/B. Erst nach der Bewertung werden die Baseline-/Kandidatenlabels aufgelöst. Er verändert keine Prompts, Modelle oder Produktionszweige automatisch.

Das lokale Sprachprofil wird mit jeder geprüften Videorunde versioniert. Zusätzlich bewertet ChatGPT Web die beobachteten Muster, Stärken und Verbesserungsmöglichkeiten; diese Bewertung wird im Artefakt als `ai_review` gespeichert. Beides dient als Evaluationsinput für spätere Prompt-/Modellvergleiche; eine Änderung wird erst nach Review übernommen.
