"""Editable AI routing and prompt files used by the native settings UI."""

from __future__ import annotations

import json
import os
import re
from hashlib import sha256

from app.database import get_db
from app.models import AgentConfig
from app.services.agents.prompt_resources import load_prompt_resource
from app.services.ai_config import (
    active_prompt,
    ai_directory,
    configuration_generation,
    list_prompt_versions,
    load_ai_json,
    provider_configuration,
    reset_provider_configuration,
    restore_playbooks_version,
    restore_prompt_version,
    save_playbooks,
    save_prompt,
    save_provider_configuration,
)
from app.services.provider_capabilities import provider_capability_payload
from app.services.seed_agents import DEFAULT_PROMPTS
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/ai-config", tags=["ai-config"])

_PROMPT_LABELS = {
    "debate_live_v2": ("Qwen-Live-Debattencoach", "Live-Debatte"),
    "debate_deep_v1": ("Externe Tiefenanalyse", "Hintergrundanalyse"),
    "agent.audio_gateway": ("Audio-Weiterleitung", "Agenten"),
    "agent.consolidated_analyst": ("Konsolidierte Analyse", "Agenten"),
    "agent.objection_handler": ("Debatten-Copilot", "Agenten"),
    "agent.synthesizer": ("Synthese und Qualitaetskontrolle", "Agenten"),
    "agent.opportunity_specialist": ("Chancen-Abgleich", "Agenten"),
    "agent.strategic_signals": ("Strategische Live-Signale", "Agenten"),
    "agent.transcript_refiner": ("Transkript-Korrektur", "Audio und ASR"),
    "agent.brief_meeting_lens": ("Nachdebatte: Gespraechsprotokoll", "Nachdebatte"),
    "agent.brief_discovery_lens": ("Nachdebatte: Erkenntnisse", "Nachdebatte"),
    "agent.brief_arbiter": ("Nachdebatte: Zusammenfuehrung", "Nachdebatte"),
    "postcall_chat_system": ("Chat nach der Debatte", "Chat und Zusammenfassung"),
    "live_chat_system": ("Live-Chat", "Live-Debatte"),
    "batch_transcription": ("Audio-Transkription", "Audio und ASR"),
    "gemini_live_gateway": ("Gemini-Live-Audio", "Audio und ASR"),
    "transcript_refiner_system": ("Transkript-Korrekturvertrag", "Audio und ASR"),
    "speaker_context_enhancement": (
        "Sprecherkorrektur und Neuanalyse",
        "Argumentgedaechtnis",
    ),
    "debate_review_system": ("Nachdebatten-Review: Rolle", "Nachdebatte"),
    "debate_review_task": ("Nachdebatten-Review: Auftrag", "Nachdebatte"),
    "analyze_transcript": ("Importiertes Transkript analysieren", "Argumentanalyse"),
    "mode.persuasive": ("Modus Überzeugen", "Debattenverhalten"),
    "mode.forceful": ("Modus Hart", "Debattenverhalten"),
    "style.natural": ("Stil Natürlich", "Debattenverhalten"),
    "style.concise": ("Stil Kurz", "Debattenverhalten"),
    "style.evidence": ("Stil Belegfokus", "Debattenverhalten"),
    "debate_user_loyalty": ("Nutzerposition und Loyalität", "Debattenverhalten"),
    "analogy.required": ("Analogie verpflichtend", "Rhetorik"),
    "analogy.optional": ("Analogie optional", "Rhetorik"),
    "background.gpt6": ("GPT-6-Hintergrundanalyse", "Hintergrundanalyse"),
    "background.gemini": ("Gemini-Hintergrundanalyse", "Hintergrundanalyse"),
    "background.oracle": ("Oracle-Hintergrundanalyse", "Hintergrundanalyse"),
    "background.system": ("Feste Rolle der Hintergrundanalyse", "Hintergrundanalyse"),
    "phase.new_topic": ("Neue-Themen-Erstanalyse", "Hintergrundanalyse"),
    "phase.follow_up": ("High-Folgeanalyse", "Hintergrundanalyse"),
    "phase.deep_reanalysis": ("Erneute Tiefenanalyse", "Hintergrundanalyse"),
    "research_source_refinement": ("Recherche und Quellenbewertung", "Recherche"),
    "research_source_system": ("Quellenprüfung: feste Rolle", "Recherche"),
    "rhetoriciq.playbooks": ("RhetoricIQ-Strategien und Sprachbefehle", "Rhetorik"),
}


class PromptUpdate(BaseModel):
    content: str


def _prompt_payload(name: str, content: str) -> dict:
    title, category = _PROMPT_LABELS.get(
        name, (name.replace("_", " ").replace(".", " / ").title(), "Weitere")
    )
    placeholders = sorted(set(re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", content)))
    path = ai_directory() / f"{name}.txt"
    return {
        "name": name,
        "title": title,
        "category": category,
        "agent_slug": name.removeprefix("agent.") if name.startswith("agent.") else "",
        "content": content,
        "version": sha256(content.encode("utf-8")).hexdigest()[:12],
        "hash": sha256(content.encode("utf-8")).hexdigest(),
        "path": str(path),
        "active_source": "Benutzerdatei im aktiven ai-Ordner",
        "placeholders": placeholders,
        "versions": list_prompt_versions(name),
    }


async def _ensure_agent_prompts(db: AsyncSession) -> None:
    result = await db.execute(select(AgentConfig).order_by(AgentConfig.display_order))
    for agent in result.scalars().all():
        agent.prompt = load_prompt_resource(f"agent.{agent.slug}", agent.prompt or "")


def _static_prompt_defaults() -> dict[str, str]:
    # Imports stay local so the settings router does not create startup cycles.
    from app.routers.analyze import ANALYZE_TRANSCRIPT_PROMPT
    from app.routers.chat import SYSTEM_PROMPT as POSTCALL_CHAT
    from app.services.agents.objection_handler import (
        _ANALOGY_INSTRUCTION_DEFAULTS,
        _LIVE_POSITION_INSTRUCTIONS,
        _MODE_INSTRUCTIONS,
        _STYLE_INSTRUCTIONS,
    )
    from app.services.batch_transcriber import TRANSCRIBE_PROMPT
    from app.services.gemini_live import GATEWAY_SYSTEM_PROMPT
    from app.services.live_chat_context import LIVE_SYSTEM_PROMPT
    from app.services.speaker_context_enhancer import ENHANCEMENT_PROMPT_TEMPLATE
    from app.services.transcript_refiner import SYSTEM_PROMPT as TRANSCRIPT_REFINER

    deep_path = ai_directory() / "debate_deep_v1.txt"
    deep_default = (
        deep_path.read_text(encoding="utf-8")
        if deep_path.is_file()
        else (
            "Gegnerisches Argument: {claim}\nMeine Position: {own_position}\n"
            "Relevanter Verlauf: {relevant_context}\nGelesene Belege: {evidence}\n"
            "Pruefe Praemissen, Schluss, Gegenbelege und offene Fragen auf Deutsch."
        )
    )
    return {
        "postcall_chat_system": POSTCALL_CHAT,
        "live_chat_system": LIVE_SYSTEM_PROMPT,
        "batch_transcription": TRANSCRIBE_PROMPT,
        "gemini_live_gateway": GATEWAY_SYSTEM_PROMPT,
        "transcript_refiner_system": TRANSCRIPT_REFINER,
        "speaker_context_enhancement": ENHANCEMENT_PROMPT_TEMPLATE,
        "analyze_transcript": ANALYZE_TRANSCRIPT_PROMPT,
        "mode.persuasive": _MODE_INSTRUCTIONS["persuasive"],
        "mode.forceful": _MODE_INSTRUCTIONS["forceful"],
        "style.natural": _STYLE_INSTRUCTIONS["natural"],
        "style.concise": _STYLE_INSTRUCTIONS["concise"],
        "style.evidence": _STYLE_INSTRUCTIONS["evidence"],
        "debate_user_loyalty": _LIVE_POSITION_INSTRUCTIONS,
        "analogy.required": _ANALOGY_INSTRUCTION_DEFAULTS[True],
        "analogy.optional": _ANALOGY_INSTRUCTION_DEFAULTS[False],
        "background.gpt6": deep_default,
        "background.gemini": deep_default,
        "background.oracle": deep_default,
        "background.system": "Du bist ein praeziser deutschsprachiger Debattenanalyst und Rechercheexperte. Analysiere nur den konkreten Argumentationszug. Gib nur die verlangten strukturierten Ergebnisse zurueck und erfinde keine Quellen.",
        "phase.new_topic": "Erstelle einmalig eine belastbare Themenlandkarte mit Positionen, Prämissen, Beweislast, Gegenargumenten, offenen Fragen und Recherchebedarf.",
        "phase.follow_up": "Nutze die vorhandene Themenanalyse wieder und bearbeite nur das neue oder noch offene Argument, ohne die gesamte Debatte zu wiederholen.",
        "phase.deep_reanalysis": "Prüfe den entscheidenden Argumentzweig erneut in voller Tiefe, weil neues Material, ein schwerer Widerspruch oder eine ausdrückliche Tiefenanalyse vorliegt.",
        "research_source_refinement": "Überarbeite die Live-Empfehlung nur anhand gelesener Auszüge. Trenne Behauptung, Beleg und Unsicherheit; prüfe Zeitraum, Grundgesamtheit und Bezugswert von Zahlen. Weise Widersprüche und falsche Übersetzungen knapp aus und erfinde keine Genauigkeit.",
        "research_source_system": "/no_think\nDu bist ein schneller deutschsprachiger Debatten-Coach. Gib nur das verlangte strukturierte Ergebnis zurück; die Sprechtexte müssen sofort nutzbar sein.",
        "debate_review_system": (
            "/no_think\nDu bist ein praeziser deutschsprachiger Debattencoach. "
            "Bewerte fair, konkret und ohne erfundene Motive. Zitiere hoechstens "
            "zwoelf Woerter am Stueck. Empfehle nur die vorgegebenen Enum-Werte."
        ),
        "debate_review_task": (
            "Analysiere die beendete Debatte erst nach ausdruecklicher Bestaetigung. "
            "Pruefe Sprache, Kuerze, Logik, Beweislast, offene Fragen, Quellenqualitaet, "
            "Nutzerloyalitaet, Themenwechsel und den Nutzen der Analogien. Nenne konkrete "
            "bessere Formulierungen."
        ),
    }


def _ensure_static_prompts() -> None:
    for name, fallback in _static_prompt_defaults().items():
        load_prompt_resource(name, fallback)


@router.get("")
async def read_ai_configuration(db: AsyncSession = Depends(get_db)):
    await _ensure_agent_prompts(db)
    _ensure_static_prompts()
    # The two latency-critical resources predate the unified editor. Loading
    # them here migrates them into the same source-of-truth contract.
    for name in ("debate_live_v2", "debate_deep_v1"):
        legacy = ai_directory() / f"{name}.txt"
        load_prompt_resource(
            name, legacy.read_text(encoding="utf-8") if legacy.is_file() else ""
        )
    prompts = []
    for path in sorted(ai_directory().glob("*.txt")):
        content = active_prompt(path.stem, "")
        if content:
            prompts.append(_prompt_payload(path.stem, content))
    playbooks = load_ai_json("playbooks.json", [])
    if playbooks:
        content = json.dumps(playbooks, ensure_ascii=False, indent=2)
        item = _prompt_payload("rhetoriciq.playbooks", content)
        item["path"] = str(ai_directory() / "playbooks.json")
        item["active_source"] = "Strukturierte Benutzerdatei im aktiven ai-Ordner"
        prompts.append(item)
    providers = provider_configuration()
    return {
        "directory": str(ai_directory()),
        "providers_path": str(ai_directory() / "providers.json"),
        "configuration_generation": configuration_generation(),
        "providers": providers,
        "provider_capabilities": provider_capability_payload(providers),
        "prompts": prompts,
    }


@router.put("/providers")
async def update_providers(data: dict = Body(...)):
    try:
        return save_provider_configuration(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/providers/reset")
async def reset_providers():
    try:
        return reset_provider_configuration()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/prompts/{name}")
async def update_prompt(
    name: str, update: PromptUpdate, db: AsyncSession = Depends(get_db)
):
    if name == "rhetoriciq.playbooks":
        try:
            content = json.dumps(
                save_playbooks(json.loads(update.content)),
                ensure_ascii=False,
                indent=2,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(400, str(exc)) from exc
        item = _prompt_payload(name, content)
        item["path"] = str(ai_directory() / "playbooks.json")
        return item
    agent = None
    if name.startswith("agent."):
        slug = name.removeprefix("agent.")
        result = await db.execute(select(AgentConfig).where(AgentConfig.slug == slug))
        agent = result.scalar_one_or_none()
        if agent is None:
            raise HTTPException(404, "Der zugeordnete Agent wurde nicht gefunden.")
    prompt_path = ai_directory() / f"{name}.txt"
    previous_prompt = (
        prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else None
    )
    try:
        saved = save_prompt(name, update.content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if agent is not None:
        agent.prompt = saved["content"]
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            if previous_prompt is None:
                prompt_path.unlink(missing_ok=True)
            else:
                prompt_path.write_text(previous_prompt, encoding="utf-8")
            raise
    return _prompt_payload(name, saved["content"])


@router.post("/prompts/{name}/reset")
async def reset_prompt(name: str, db: AsyncSession = Depends(get_db)):
    if name == "rhetoriciq.playbooks":
        path = ai_directory() / "defaults" / "playbooks.json"
        if not path.is_file():
            raise HTTPException(400, "Der RhetoricIQ-Auslieferungsstandard fehlt.")
        return await update_prompt(
            name, PromptUpdate(content=path.read_text(encoding="utf-8")), db
        )
    default = ""
    if name.startswith("agent."):
        default = DEFAULT_PROMPTS.get(name.removeprefix("agent."), "")
    if not default:
        default = _static_prompt_defaults().get(name, "")
    if not default:
        default_path = ai_directory() / "defaults" / "prompts" / f"{name}.txt"
        if default_path.is_file():
            default = default_path.read_text(encoding="utf-8")
    if not default.strip():
        raise HTTPException(
            400, "Fuer diesen Prompt ist kein Auslieferungsstandard hinterlegt."
        )
    return await update_prompt(name, PromptUpdate(content=default), db)


@router.post("/prompts/{name}/restore/{version}")
async def restore_prompt(name: str, version: str, db: AsyncSession = Depends(get_db)):
    if name == "rhetoriciq.playbooks":
        try:
            restored = restore_playbooks_version(version)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return await update_prompt(
            name,
            PromptUpdate(content=json.dumps(restored, ensure_ascii=False, indent=2)),
            db,
        )
    try:
        restored = restore_prompt_version(name, version)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return await update_prompt(name, PromptUpdate(content=restored["content"]), db)


@router.post("/open-folder")
async def open_ai_folder():
    if os.name != "nt" or not hasattr(os, "startfile"):
        raise HTTPException(
            400, "Ordner oeffnen ist nur in der Windows-App verfuegbar."
        )
    os.startfile(str(ai_directory()))  # type: ignore[attr-defined]
    return {"opened": True, "directory": str(ai_directory())}
