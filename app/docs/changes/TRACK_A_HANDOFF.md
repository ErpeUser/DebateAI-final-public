# DEBATEAI – Arbeitsstrang A Übergabe

Stand: 2026-11-20 (Europe/Vienna)
Basis-SHA: `445ee4a6eb5d1fb271e485aa132a6031e2b26db1`
Branch: `feat/prelive-video-evidence`
Arbeitsverzeichnis: eigener Worktree `worktree-a`

## Ergebnis

Arbeitsstrang A ergänzt den bestehenden Offline-Video-Evaluationspfad um einen
link-first, consent-aware Jobpfad:

1. Öffentliche HTTPS-URL wird validiert (keine Credentials, Sonderports,
   lokale/private DNS-Ziele); yt-dlp wird mit `skip_download`, manuellen und
   automatischen Untertiteln sowie begrenzter Sprachwahl nur zur Metadaten- und
   Track-Ermittlung aufgerufen.
2. Manuelle Untertitel werden vor automatischen Untertiteln ausgewählt und ohne
   Videodownload abgerufen. VTT/SRT/TTML-artige Cue-Texte werden in stabile,
   deutsche, zeitgestempelte Segmente mit Sprecherfeldern normalisiert.
3. Ohne parsebares Transkript entsteht `awaiting_consent` mit dem Hinweis
   „Kein Transkript verfügbar“. Eine Zustimmung für `gemini_api` ist nötig,
   bevor der alternative Gemini-Weg aufgerufen wird. Fehlender Schlüssel,
   nicht unterstützte URL und Providerfehler bleiben verständliche lokale
   Fehlerzustände.
4. A1 (`rhetorical_evidence`) und A2 (`argument_evidence`) entstehen getrennt,
   versioniert und segmentbezogen. A1 liefert Metriken/Testfälle ohne
   Promptänderung. A2 verwendet Claims, Quell-IDs und die Zustände
   `mentioned`, `found`, `retrieved`, `supports`, `contradicts`, `unclear`,
   `unavailable`.
5. JSON-Checkpoints und Artefakte werden atomar unter dem lokalen
   `DATA_DIR/video-eval`-Pfad gespeichert. Job-Token schützen Status, Consent,
   Abbruch und Artefaktzugriff. Doppelte aktive URL-/Sprachanfragen werden
   wiederverwendet; neuere Checkpoints überschreiben keine abgeschlossenen
   Ergebnisse.
6. `video_context.py` segmentiert lange Transkripte token- und zeichenbewusst,
   mit Satz-/Sprechergrenzen, stabilen Chunk-IDs, begrenzter Überlappung,
   Checkpoints, Antwortvalidierung und einem Rollover-Workflow. Nur
   `message-too-large` und `context-full` dürfen einen autorisierten neuen Chat
   auslösen; Rate-Limits, Login, CAPTCHA und belegte Browserprofile werden
   niemals durch Chatwechsel umgangen.

## Geänderte und neue Dateien

- `app/backend/app/services/video_eval_pipeline.py` – rückwärtskompatible
  Artefaktfelder `artifact_schema_version`, `rhetorical_evidence`,
  `argument_evidence`, `provenance`.
- `app/backend/app/services/video_eval_jobs.py` – URL-/DNS-Prüfung, yt-dlp-
  Probe, Untertitelabruf/-normalisierung, Gemini-Fallback, A1/A2-Auswertung,
  lokale Job-/Artefaktpersistenz, Consent und Abbruch.
- `app/backend/app/services/video_context.py` – lange Kontextsegmente,
  Fehlerklassifikation, Checkpoints, Merge/Deduplizierung und kontrollierter
  Kontextwechsel.
- `app/backend/app/routers/video_eval.py` – additive API-Routerdefinition.
- `app/backend/scripts/video_eval_batch.py` – Linkeingänge nutzen zuerst
  Untertitel; bei fehlendem Transkript wird kein stiller Cloud-Upload ausgelöst.
- `app/backend/tests/test_video_eval_jobs.py` – Untertitelreihenfolge,
  Normalisierung, Consent, fehlender Gemini-Key und Artefaktzugriff.
- `app/backend/tests/test_video_eval_router.py` – API-Vertrag und Token-Scope.
- `app/backend/tests/test_video_context.py` – Chunking, Overlap,
  Fehlerklassen, Rollover, Checkpoints und Secret-Scrubbing.
- `app/docs/changes/TRACK_A_VIDEO_EVIDENCE_API.md` – API-/Artefaktspezifikation
  für Arbeitsstrang B.

## API-Vertrag

Die Endpunkte sind im Router implementiert:

- `POST /api/video-eval/jobs` mit `{url, language}`
- `GET /api/video-eval/jobs/{id}`
- `POST /api/video-eval/jobs/{id}/consent` mit
  `{provider: "gemini_api", approved}`
- `POST /api/video-eval/jobs/{id}/cancel`
- `GET /api/video-eval/jobs/{id}/artifact`

Alle Job-Status-/Mutation-/Artefaktabfragen verwenden `X-DebateAI-Job-Token`.
Die vollständigen Beispielantworten, Zustände und Mock-Hinweise stehen in
`app/docs/changes/TRACK_A_VIDEO_EVIDENCE_API.md`.

## Tests und Verifikation

Erfolgreich:

```text
python -m compileall -q app/backend/app app/backend/scripts app/backend/tests
```

Zusätzliche lokale Smoke-Prüfungen decken VTT/SRT-Normalisierung, manuelle
gegen automatische Tracks, `awaiting_consent` → `gemini_key_missing`, lokale
Artefaktspeicherung, A1/A2-Felder und erlaubten Kontext-Rollover ab.

Der Lauf von pytest wurde versucht, ist in der bereitgestellten Runtime aber
nicht möglich, weil `pytest`/`pytest-asyncio` nicht installiert sind:

```text
python -m pytest -q -p no:cacheprovider \
  tests/test_video_context.py tests/test_video_eval_jobs.py \
  tests/test_video_eval_router.py tests/test_video_eval_pipeline.py \
  tests/test_video_eval_evaluator.py
# No module named pytest
```

Keine echten Provideraufrufe, Kosten oder Browserlogins wurden ausgelöst.

## Recherchequellen

Zum Implementierungszeitpunkt wurden die offiziellen Primärquellen geprüft:

- yt-dlp README und Python-Embedding:
  <https://github.com/yt-dlp/yt-dlp#usage-and-options> und
  <https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp>
- Gemini Video Understanding:
  <https://ai.google.dev/gemini-api/docs/video-understanding>
- Gemini Audio/Transkription:
  <https://ai.google.dev/gemini-api/docs/audio>
- Gemini Files API:
  <https://ai.google.dev/gemini-api/docs/files>
- Gemini Structured Output:
  <https://ai.google.dev/gemini-api/docs/structured-output>
- Gemini Rate Limits und Preismodelle:
  <https://ai.google.dev/gemini-api/docs/rate-limits> und
  <https://ai.google.dev/gemini-api/docs/pricing>
- YouTube Terms und Developer Policies für öffentliche Inhalte, Zustimmung,
  Löschung und Downloadgrenzen:
  <https://www.youtube.com/t/terms> und
  <https://developers.google.com/youtube/terms/api-services-terms-of-service>

Die Dokumentation weist darauf hin, dass der YouTube-URL-Weg nur öffentliche
Videos verarbeitet, Preview-/Tariflimits sich ändern können und Files-API-
Uploads einen eigenen Processing-/ACTIVE-/FAILED-Lifecycle sowie automatische
Aufbewahrungs- und Löschregeln haben. Die Implementierung hält diese Grenzen
konfigurierbar und überträgt ohne Consent keine Medien.

## Grenzen

- `app/main.py` registriert den neuen Router noch nicht. Das ist absichtlich,
  damit der parallele Integrator C die gemeinsame Routerliste einmalig ändert:
  `from app.routers import video_eval` und
  `app.include_router(video_eval.router)`.
- Der Gemini-Adapter nutzt für öffentliche YouTube-URLs den direkten URI-Weg.
  Files-API-Uploads für andere Plattformen, Status-Polling, vorzeitiges
  `files.delete` und feinere Tarif-/Kostenlimits sind als Erweiterungspunkt
  vorbereitet, aber nicht ohne Providerfreigabe getestet.
- Quellen werden lokal als `mentioned` erfasst. Die vorhandene
  `debate_research`-Verifikation darf C hinter einem expliziten
  Recherche-/Provider-Consent anschließen und danach `retrieved` sowie
  `supports`/`contradicts` setzen.
- Die JSON-Jobpersistenz ist für den bestehenden Single-User-Desktop gedacht.
  Für Multiworker-Serverbetrieb braucht C eine DB-Journal-/Lockschicht oder
  einen dedizierten Worker.
- Der bestehende ChatGPT-Web-Adapter startet pro `generate()` einen eigenen
  Oracle-Prozess und hält einen exklusiven Browserprofil-Lock. Deshalb ist ein
  Chatwechsel im normalen Adapter derzeit nicht nötig; `video_context.py`
  schützt nur tatsächlich wiederverwendete Chats und meldet einen fehlenden
  sicheren Wechsel explizit.

## Integrationsaufgaben für C

1. Router in `main.py` registrieren und die vorhandene Request-/Runtime-
   Middleware prüfen.
2. API-Spezifikation an B übergeben; B kann den Router mit dem dokumentierten
   Mock-Store testen.
3. Bei aktivierter externer Quellenrecherche den bestehenden
   `debate_research.research_claim`-Pfad mit Provider-/Datenklassen-Consent
   verbinden und seine Ergebnisse in A2-Quellzustände mappen.
4. Falls relationale Dauerpersistenz für Jobs/Artefakte erforderlich wird,
   additive Alembic-Migration und Zugriffskontrolle ergänzen; vorhandene
   `VideoEvalArtifact`-JSONs rückwärtskompatibel importieren.
5. Provider-/Browser-Integrationstests mit sicheren Mocks und die fehlende
   Windows-/Desktop-Abnahme getrennt durchführen.
