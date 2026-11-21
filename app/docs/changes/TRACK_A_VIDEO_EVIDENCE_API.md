# Arbeitsstrang A: Video-Evidence-API

Stand: 2026-11-20 · Vertrag für Arbeitsstrang B

Die additive Routerimplementierung liegt in `app/backend/app/routers/video_eval.py`.
Sie wird bewusst nicht automatisch in `app/backend/app/main.py` registriert, weil
`main.py` im parallelen Integrationsdurchgang C gemeinsam gepflegt wird. C kann
den Router mit `app.include_router(video_eval.router)` unter dem bestehenden
`/api`-Präfix aktivieren.

## Zustände und Arbeitsschritte

`status` ist einer von `queued`, `processing`, `awaiting_consent`, `completed`,
`failed` oder `cancelled`. `stage` beschreibt den aktuellen Abschnitt:

`queued` → `validate_url` → `metadata` → `subtitles` → `transcription` →
`ai_analysis` → `source_verification` → `persistence` → `completed`.

Ein öffentlicher Link wird mit yt-dlp-Metadaten geprüft. Die erste Extraktion
setzt `skip_download`, `writesubtitles`, `writeautomaticsub` und eine begrenzte
Sprachliste. Manuelle Untertitel werden vor automatischen Untertiteln verwendet;
ein erfolgreiches Untertitelartefakt setzt `video_downloaded: false`. Fehlt ein
parsebares Transkript, bleibt der Job in `awaiting_consent` und verlangt eine
explizite Zustimmung für `gemini_api`.

## Endpunkte

### `POST /api/video-eval/jobs`

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "language": "de"
}
```

Antwort (`202`):

```json
{
  "id": "vjob_…",
  "status": "queued",
  "stage": "queued",
  "progress": 0.0,
  "artifact_ids": [],
  "access_token": "…",
  "deduplicated": false
}
```

`access_token` ist ein lokales Job-Geheimnis. B sendet es als
`X-DebateAI-Job-Token` bei Consent, Abbruch und Artefaktabruf; es wird nicht in
Logs oder Artefakten gespeichert.

### `GET /api/video-eval/jobs/{id}`

Header: `X-DebateAI-Job-Token: …`

Liefert Status, `stage`, `progress`, `error_code`, `error`, `consent`,
`checkpoints` und verfügbare `artifact_ids`. Der Videolink wird nicht als
zusätzlicher Prompt an einen Provider weitergereicht.

Beispiel für fehlende Untertitel:

```json
{
  "id": "vjob_…",
  "status": "awaiting_consent",
  "stage": "transcription",
  "progress": 0.35,
  "consent": {
    "required": true,
    "provider": "gemini_api",
    "data_class": "video_url",
    "message": "Kein Transkript verfügbar. Gemini-Transkription darf erst nach bewusster Freigabe starten."
  },
  "artifact_ids": []
}
```

### `POST /api/video-eval/jobs/{id}/consent`

Header: `X-DebateAI-Job-Token: …`

```json
{"provider": "gemini_api", "approved": true}
```

Nur `gemini_api` ist für den Fallback zugelassen. Bei Ablehnung endet der Job
mit `consent_denied`; bei fehlendem Schlüssel mit `gemini_key_missing`. Beide
Fehler bewahren Link, Metadaten und Checkpoints lokal.

### `POST /api/video-eval/jobs/{id}/cancel`

Header: `X-DebateAI-Job-Token: …`

Beendet den Job sicher und erhält bereits gespeicherte Checkpoints.

### `GET /api/video-eval/jobs/{id}/artifact`

Header: `X-DebateAI-Job-Token: …`

Liefert nur das lokale strukturierte Artefakt. Ein falsches oder fehlendes Token
führt zu `403`; ein noch nicht abgeschlossenes Artefakt zu `409`.

## Artefaktvertrag

Die bestehenden Felder `video_id`, `source_url`, `transcript_segments`,
`source_candidates`, `verified_sources`, `rhetorical_profile` und `eval_cases`
bleiben erhalten. Link-first Jobs ergänzen:

- `artifact_schema_version: 2` und `provenance` mit URL, Plattform, Abrufzeit,
  Untertitelsprache/-format, Hash und `video_downloaded`.
- `transcript_segments[].segment_id` als stabiler Hash aus Video, Position,
  Zeit und Text.
- `rhetorical_evidence` (A1) mit `analysis_id: rhetoric-v1`, Befunden,
  Segmentbezug und messbaren Testfällen. Es aktiviert keine Promptänderung.
- `argument_evidence` (A2) mit Claim-IDs, Sprecher-/Zeitbezug, Quell-IDs und
  den Zuständen `mentioned`, `found`, `retrieved`, `supports`, `contradicts`,
  `unclear`, `unavailable`.

Transkript- und Untertitelinhalte werden als Daten behandelt. Die lokale Analyse
interpretiert keine Anweisung aus einem Untertitel; Provider-Prompts müssen die
gleiche Datenmarkierung beibehalten.

## Mock-Nutzung in B

B kann den Router in einer kleinen FastAPI-Testanwendung registrieren und den
`video_eval._store` durch einen `VideoJobStore(tmp_path, gemini=FakeGemini())`
ersetzen. Damit bleiben manuelle Untertitel, automatische Untertitel,
Consent-Ablehnung, fehlender Schlüssel, Abbruch und Artefaktzugriff ohne echte
Providerkosten reproduzierbar.
