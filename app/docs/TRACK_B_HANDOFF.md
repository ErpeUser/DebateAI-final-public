# DebateAI – Arbeitsstrang B Übergabe

## Änderungsstand

- Basis-SHA: `445ee4a6eb5d1fb271e485aa132a6031e2b26db1`
- Branch: `feat/prelive-prompt-quality`
- Arbeitsbereich: eigener Worktree `/workspace/scratch/01cefca878b0/worktree-b`
- Ziel: kontrollierte Promptqualität, zugängliches A/B-/Sprachlabor, Videolink-UI und nachvollziehbare Übergabe an Integrationsdurchgang C.

## Gelieferte Funktionen

### Promptqualität und Optimierung

`app/backend/app/services/prompt_optimization.py` ist ein providerunabhängiger,
kontrollierter Store. Er vergleicht dieselben `fixed`- und `holdout`-Fälle,
aggregiert Natürlichkeit, Faktentreue, argumentative Stärke, Quellenredlichkeit,
Sprechbarkeit/Nutzbarkeit, Latenz und Kosten und verweigert die Aktivierung bei
fehlenden Fällen oder Regressionen. Vorschläge werden mit Inhaltshash,
Baseline-Hash, Grund, Risiken, Quellen und Zeitstempel protokolliert.

Der Standardpfad bleibt Vorschlag beziehungsweise manuelle Freigabe. Auto-Apply
muss sowohl in der Policy als auch durch eine ausdrückliche Aktivierung gesetzt
werden. Das Änderungsbudget ist standardmäßig klein. Aktivierung und Auditdatei
werden atomar geschrieben; bei einem Schreibfehler wird der vorherige Prompt
wiederhergestellt. `rollback()` ist jederzeit möglich. `rollback_if_regressed()`
prüft zusätzlich den aktiven Hash und verhindert, dass ein inzwischen manuell
geänderter Prompt überschrieben wird. Platzhalter laufen vor der Aktivierung
durch die vorhandene Produktionsvalidierung.

`video_eval_autotune.py` bietet jetzt Fixture-Normalisierung,
`compare_evaluations`-Entscheidung, report-only-Ausgabe und explizit gated
`apply_prompt_proposal`/`apply_optimization`-Wrapper. Ohne Freigabe entsteht
keine Mutation. Die bestehende Video-Pipeline und Batch-Verarbeitung bleiben
unverändert.

Die aktive Live-Promptfassung wurde mit der Defaultfassung vereinheitlicht: Das
`counterargument` muss die Antwort mit dem stärksten ehrlichen Grund stützen und
niemals dagegen argumentieren; `analogy` erklärt die entscheidende Logik. Der
Vertragstest prüft außerdem kurze sprechbare Antworten, Claim-Zielgenauigkeit,
Negationen und das Verbot erfundener Fakten.

### Labor und Desktop

Der neue Admin-Tab `Labor` enthält:

- blindes A/B-/Sprachlabor mit zwei tatsächlich verfügbaren Modellen oder Promptvarianten,
- gleiche Eingabe, Quellen und Datensatz-ID, optional unabhängiger Holdout,
- wechselnde, deterministische A/B-Reihenfolge und Reveal erst nach gespeicherter Bewertung,
- Bewertungen für Natürlichkeit, Stärke, Präzision, Quellenredlichkeit und Nutzbarkeit,
- „beide ungeeignet“, Export, Latenz-/Kosten-/Prompt-Hash-Anzeige,
- kontrollierte Übernahme und Rollback sowie Rater-Übereinstimmung aus dem Backend,
- Videolink-Card gegen den vereinbarten `/api/video-eval/jobs...`-Vertrag mit
  Statusanzeige, Gemini-Fallback-Einwilligung, Abbruch und Artifact-Ansicht.

Die API-Funktionen zeigen Providerfehler sichtbar an und behaupten keinen
Live-Erfolg, wenn das Backend oder ein Cloudmodell nicht verfügbar ist.

## Prompt-Matrix und Forschung

Die vollständige Matrix steht in [`app/docs/PROMPT_MATRIX_B.md`](app/docs/PROMPT_MATRIX_B.md).
Sie unterscheidet aktive, experimentelle, doppelte und ungenutzte Ressourcen und
führt Eingaben, Ausgabeformate, Modellroute, Hash, Schwächen, Tests und Bewertung
auf.

Verwendete überprüfbare Referenzen:

- OpenAI, *Evaluation best practices*: https://developers.openai.com/api/docs/guides/evaluation-best-practices
- OpenAI, *Agent evals*: https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI, *Graders*: https://developers.openai.com/api/docs/guides/graders
- Shi et al., *Judging the Judges*, IJCNLP-AACL 2025: https://aclanthology.org/2025.ijcnlp-long.18/
- Findings of EMNLP 2025, multi-agent judge bias: https://aclanthology.org/2025.findings-emnlp.941/
- OpenAI, *Whisper*: https://cdn.openai.com/papers/whisper.pdf

Die Entscheidungen daraus sind im Code sichtbar: feste Datensätze, Holdouts,
blinde Reihenfolge, getrennte Qualitätsdimensionen, keine alleinige Bestätigung
durch den vorschlagenden Judge und kontinuierliche Auditdaten.

## Geänderte Dateien

- `app/ai/debate_live_v2.txt`
- `app/ai/defaults/prompts/debate_live_v2.txt`
- `app/backend/app/services/prompt_optimization.py`
- `app/backend/scripts/video_eval_autotune.py`
- `app/backend/tests/test_prompt_optimization.py`
- `app/backend/tests/test_video_eval_autotune_controlled.py`
- `app/backend/tests/test_ai_prompt_contracts.py`
- `app/frontend/src/components/AdminPanel.tsx`
- `app/frontend/src/components/QualityLabCard.tsx`
- `app/frontend/src/components/QualityLabCard.test.mjs`
- `app/frontend/src/components/VideoEvalCard.tsx`
- `app/frontend/src/components/VideoEvalCard.test.mjs`
- `app/frontend/src/lib/qualityLab.ts`
- `app/frontend/src/lib/qualityLab.test.mjs`
- `app/frontend/src/services/api.ts`
- `app/docs/PROMPT_MATRIX_B.md`
- `TRACK_B_HANDOFF.md`

## Verifikation

- `PYTHONPATH=app/backend python -m unittest tests.test_prompt_optimization tests.test_video_eval_autotune_controlled`: **10/10 bestanden**.
- `PYTHONPATH=app/backend python -m unittest tests.test_ai_prompt_contracts`: Promptvertrag und Live-Qualitätsvertrag bestanden.
- Frontend `npm test`: **377/377 bestanden**.
- Frontend `npm run build`: **Exit 0**; Vite meldet weiterhin die bekannten Chunk-Größenwarnungen.
- `python -m py_compile app/backend/app/services/prompt_optimization.py app/backend/scripts/video_eval_autotune.py`: bestanden.
- Breitere Backendtests, die SQLAlchemy/Google-Provider importieren, konnten in der Minimalumgebung nicht geladen werden, weil diese optionalen Testabhängigkeiten dort fehlen. Sie wurden nicht als bestanden gezählt.

## Integrationshinweise für C

1. Die Quality-/Video-Lab-Routen sind im Frontend typisiert, aber absichtlich noch
   nicht in der zentralen Backend-Routerregistrierung enthalten. C soll die
   vorhandenen Verträge implementieren und die Mocks durch echte, fail-closed
   Provider-/Jobdienste ersetzen.
2. Für Promptübernahmen soll C `PromptOptimizationStore(ai_config.ai_directory())`
   verwenden und `approved_by_user` beziehungsweise beide Auto-Apply-Schalter
   explizit setzen. `user_managed=True` schützt persönliche Prompts.
3. `experimental_external_parallelism` beschreibt logische Lanes. Der
   ChatGPT-Webadapter bleibt exklusiv gesperrt; die UI darf daraus keine drei
   parallelen Browserzugriffe ableiten.
4. Die lokale Sofortantwort bleibt zeitkritisch und darf nicht auf einen externen
   Judge, Holdout-Lauf oder Videolink-Job warten.
5. A kann die Videobeweis-Persistenz und Backendjobs an den UI-Vertrag anschließen,
   ohne die in B geschützten Promptdateien, Store-Auditdaten oder Frontendtests
   zu überschreiben.
6. Persönliche Promptdateien und Playbooks bleiben updatefest; keine Seed-/Reset-
   Routine darf sie still ersetzen.
