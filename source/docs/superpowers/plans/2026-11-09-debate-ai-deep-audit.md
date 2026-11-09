# Debate AI Deep Audit and German Branding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Beheben der nachgewiesenen P0/P1-Vertragslücken aus dem statischen Audit und die sichtbare Anwendung vollständig als deutsches Programm „Debate AI“ ausweisen.

**Architecture:** Die bestehende Audio-, Transcript- und Agentenarchitektur bleibt erhalten. Der lokale Dossierkontext erhält ein technisches Egress-Gate vor Retrieval und Modellaufruf; danach werden einzelne Pipeline-Fehler mit kleinen, isolierten Änderungen behoben. Sichtbare UI-, Export- und Desktop-Texte werden auf Deutsch und Debate AI vereinheitlicht, während technische Backward-Compatibility-Schlüssel nur dort erhalten bleiben, wo Protokoll oder Installation sie benötigt.

**Tech Stack:** FastAPI/Python, SQLAlchemy, asyncio, React/TypeScript, stdlib `unittest`, Vite.

**Spec:** `C:/Users/User/.codex/attachments/b8e75662-2258-43c7-ae60-6c6ae659c89c/pasted-text.txt`

## Global Constraints

- Keine Git-Resets, Clean-Befehle oder Löschung fremder Arbeitsbaumänderungen.
- Lokaler Dossiertext darf nur an eine technisch als lokal/on-prem zugelassene Modellroute gehen.
- Akzeptiertes Audio darf nicht stillschweigend verworfen werden.
- Sichtbare Produktbezeichnung und Nutzertexte sind Deutsch und „Debate AI“; technische Umgebungsvariablen/Protokollheader bleiben aus Kompatibilitätsgründen unverändert, sofern keine sichere Migration vorhanden ist.
- Jeder Fix erhält einen reproduzierbaren Test und wird mit fokussierten Regressionstests verifiziert.
- Nach jedem Paket werden `.ai/DEBATE_AI_OPTIMIERUNG.md` und der private Snapshot-Nachweis aktualisiert.

## Review Focus

- Cloud-/Web-/OAuth-Route mit vorhandenem lokalem Dossier darf keinen Dossiertext erhalten.
- On-prem-Endpunkt darf Dossiertext nach erfolgreicher Zulassungsprüfung erhalten.
- Neue Transcript-Ergebnisse dürfen sich nicht gegenseitig durch einen Emit-Lock blockieren.
- Während eines Cooldown-Handlers eintreffende Events müssen nach Handler-Ende erneut geplant werden.
- Deutsche Zahlenwörter und Prompt-Platzhalter dürfen nicht durch Encoding- oder Validierungsfehler abgelehnt werden.
- Sichtbare Oberfläche darf nicht mit `lang="en"` oder englischen Standardaktionen ausgeliefert werden.

### Task 1: Technisches Dossier-Egress-Gate

**Files:**
- Modify: `backend/app/services/agents/orchestrator.py`
- Modify: `backend/tests/test_debate_copilot.py`
- Modify: `backend/tests/test_dossier_hybrid_integration.py`

- [ ] Gate vor Retrieval anhand der tatsächlich verwendeten `objection_handler`-Modellroute prüfen.
- [ ] Cloud-/unbekannte Route ohne Dossierblock ausführen; on-prem/local Route darf den Kontext laden.
- [ ] Read-only Dossierretrieval ohne unnötigen Commit ausführen.
- [ ] Tests für Cloud-Ausschluss, zugelassene Local-Route und no-commit ergänzen.

### Task 2: Ordered-Transcript- und EventBus-Stabilität

**Files:**
- Modify: `backend/app/services/ordered_transcription.py`
- Modify: `backend/app/services/agents/event_bus.py`
- Test: `backend/tests/test_ordered_transcription.py`
- Test: `backend/tests/test_event_bus.py`

- [ ] Unter Locks nur fertige Reihenfolge entnehmen; externe Emits außerhalb des Locks ausführen.
- [ ] Pending-Events nach Abschluss eines Cooldown-Handlers sicher neu terminieren.
- [ ] Bestehende Sequenz- und Cancellation-Semantik erhalten und fokussiert testen.

### Task 3: Deterministische Prompt-/Zahlenvalidierung

**Files:**
- Modify: `backend/app/services/agents/orchestrator.py`
- Modify: `backend/app/services/agents/prompt_resources.py`
- Test: `backend/tests/test_debate_copilot.py`
- Test: `backend/tests/test_prompt_resources.py`

- [ ] Deutsche Unicode-Zahlenwörter zentral tokenisieren, ohne Mojibake-Literale.
- [ ] Prompt-Platzhalter gegen eine Allowlist validieren und Fehler vor Runtime-Formatierung melden.

### Task 4: Deutsche Debate-AI-Oberfläche und sichtbares Branding

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/i18n/de.ts`
- Modify: sichtbare React-Komponenten mit englischen Nutzertexten
- Modify: `backend/app/services/briefing_document.py`, Desktop-UI und sichtbare Release-/Starttexte
- Test: vorhandene Frontend-/Branding-Suites und `backend/tests/test_debate_branding.py`

- [ ] `lang="de"` setzen und zentrale deutsche Texte ohne Mojibake ausliefern.
- [ ] Sichtbares „Backchannel“ in Nutzeroberfläche, Exporten, Desktoptitel und Starttexten durch „Debate AI“ ersetzen.
- [ ] Technische Header, Umgebungsvariablen, Pfad- und API-Kompatibilität nur erhalten, wenn sie keine sichtbare Produktbezeichnung sind.
- [ ] Englische sichtbare Standardaktionen in den berührten Komponenten übersetzen; Modell-/Provider-Eigennamen bleiben unverändert.

### Task 5: Verifikation und Fortschrittssicherung

**Files:**
- Modify: `.ai/DEBATE_AI_OPTIMIERUNG.md`
- Modify: `docs/debate-ai-optimization-report.md` und Audit-/Release-Nachweise bei Bedarf

- [ ] Backend-Fokustests, Frontend-Build und Branding-Scan ausführen.
- [ ] Private Snapshot-Dateien/Manifest synchronisieren, ohne lokale Cookies, Logs, Datenbanken oder Browserprofile zu übernehmen.
- [ ] Echte Hardware-/Audio-/menschliche Abnahmen als BLOCKED dokumentieren, nicht simulieren.

