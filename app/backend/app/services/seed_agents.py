"""Seed default agent configurations into the database."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentConfig, CustomEndpoint
from app.services.app_settings import get_app_setting, set_app_setting
from app.services.agents.prompts import (
    AUDIO_BRIDGE_PROMPT,
    BRIEF_ARBITER_PROMPT,
    BRIEF_DISCOVERY_LENS_PROMPT,
    BRIEF_MEETING_LENS_PROMPT,
    CONSOLIDATED_ANALYST_BASE_PROMPT,
    DEFAULT_ANALYST_LENSES,
    DEBATE_RECOMMENDATION_PROMPT,
    OBJECTION_HANDLER_PROMPT,
    OPPORTUNITY_SPECIALIST_PROMPT,
    PRINCIPAL_AGENT_PROMPT,
    STRATEGIC_SIGNALS_PROMPT,
)
from app.services.transcript_refiner import SYSTEM_PROMPT as TRANSCRIPT_REFINER_PROMPT
from app.services.transcription_runtime import SETTING_BATCH_TRANSCRIBER_MODEL
from app.services.transcription_language import SETTING_TRANSCRIPTION_LANGUAGE
from app.services.agents.prompt_resources import load_prompt_resource
from app.services.identity import env_value

# Default prompt lookup by slug (used for reset endpoint)
DEFAULT_PROMPTS = {
    "audio_gateway": AUDIO_BRIDGE_PROMPT,
    "consolidated_analyst": CONSOLIDATED_ANALYST_BASE_PROMPT,
    "objection_handler": OBJECTION_HANDLER_PROMPT,
    "synthesizer": PRINCIPAL_AGENT_PROMPT,
    "opportunity_specialist": OPPORTUNITY_SPECIALIST_PROMPT,
    "strategic_signals": STRATEGIC_SIGNALS_PROMPT,
    "transcript_refiner": TRANSCRIPT_REFINER_PROMPT,
    "brief_meeting_lens": BRIEF_MEETING_LENS_PROMPT,
    "brief_discovery_lens": BRIEF_DISCOVERY_LENS_PROMPT,
    "brief_arbiter": BRIEF_ARBITER_PROMPT,
}

# Default lens configs by slug (used for seeding and the reset endpoint)
DEFAULT_LENSES_BY_SLUG = {
    "consolidated_analyst": DEFAULT_ANALYST_LENSES,
}

DESKTOP_DEBATE_ENDPOINT_ID = "german-debate-ollama"
DESKTOP_DEBATE_WIRE_MODEL = "qwen3:4b"
DESKTOP_DEBATE_MODEL_ID = (
    f"endpoint:{DESKTOP_DEBATE_ENDPOINT_ID}:{DESKTOP_DEBATE_WIRE_MODEL}"
)
_DESKTOP_DEBATE_BOOTSTRAP_KEY = "debate.desktop.local_live.v1"
_DEBATE_PROMPT_VERSION_KEY = "debate.prompt.objection_handler.version"
_FIXED_GERMAN_ASR_VERSION_KEY = "transcription.fixed_german_asr.v1"
_IDEAL_DEBATE_DEFAULTS_VERSION_KEY = "debate.desktop.ideal_defaults.v1"
_WEB_FIRST_AGENT_MODELS_VERSION_KEY = "debate.desktop.web_first_agents.v1"
DEBATE_LIVE_PROMPT_VERSION = "debate_live_v3"
_WEB_FIRST_ANALYSIS_SLUGS = {
    "consolidated_analyst",
    "synthesizer",
    "opportunity_specialist",
    "strategic_signals",
    "brief_meeting_lens",
    "brief_discovery_lens",
    "brief_arbiter",
}
_KNOWN_OLD_ANALYSIS_MODELS = {"", "gemini-3.8-flash"}
_BUILTIN_DEBATE_PROMPT_HASHES = {
    hashlib.sha256(value.encode("utf-8")).hexdigest()
    for value in (OBJECTION_HANDLER_PROMPT, DEBATE_RECOMMENDATION_PROMPT)
}

SEED_CONFIGS = [
    {
        "slug": "audio_gateway",
        "name": "Live-Transkription",
        "description": "Erfasst Mikrofon und Gesprächston für deutsche Live-Untertitel. Dieser Assistent hört nur zu und erzeugt selbst keine Empfehlungen.",
        "agent_type": "audio",
        "model_id": "",
        "prompt": AUDIO_BRIDGE_PROMPT,
        "enabled": True,
        "sub_types": "",
        "display_order": 1,
    },
    {
        "slug": "consolidated_analyst",
        "name": "Gesamtanalyse",
        "description": "Erkennt relevante Fragen, Beobachtungen, Chancen und nächste Schritte und liefert die Grundlage für die Abschlussanalyse.",
        "agent_type": "text",
        "model_id": "",
        "prompt": CONSOLIDATED_ANALYST_BASE_PROMPT,
        "enabled": True,
        "sub_types": "question,observation,opportunity,action_item",
        "lenses": json.dumps(DEFAULT_ANALYST_LENSES),
        "interval_seconds": 40,
        "display_order": 2,
    },
    {
        "slug": "objection_handler",
        "name": "Debate Copilot",
        "description": "Ereignisgesteuerter Live-Debattenassistent: reagiert auf neue Aussagen, Fragen und Einwaende mit sofort aussprechbaren Empfehlungen auf Deutsch. Kann unsichere Sachfragen optional im Hintergrund ueber quellengestuetzte, keyless Recherche pruefen.",
        "agent_type": "text",
        "model_id": "",
        "prompt": OBJECTION_HANDLER_PROMPT,
        "enabled": True,
        "sub_types": "",
        "interval_seconds": 10,
        "display_order": 8,
    },
    {
        "slug": "synthesizer",
        "name": "Hauptanalyse",
        "description": "Prüft Hinweise auf Qualität und Widersprüche, verbindet zusammengehörige Punkte und verdichtet das strategische Gesamtbild.",
        "agent_type": "meta",
        "model_id": "",
        "prompt": PRINCIPAL_AGENT_PROMPT,
        "enabled": True,
        "sub_types": "",
        "interval_seconds": 75,
        "display_order": 3,
    },
    {
        "slug": "opportunity_specialist",
        "name": "Chancen-Abgleich",
        "description": "Gleicht erkannte Chancen mit den vorhandenen Wissensquellen ab und ergänzt nur passende, belegte Verbindungen.",
        "agent_type": "db",
        "model_id": "",
        "prompt": OPPORTUNITY_SPECIALIST_PROMPT,
        "enabled": True,
        "sub_types": "",
        "interval_seconds": 55,
        "display_order": 4,
    },
    {
        "slug": "strategic_signals",
        "name": "Strategische Signale",
        "description": "Zeigt live das wichtigste Signal, Risiko, die beste nächste Frage und einen konkreten Handlungsimpuls.",
        "agent_type": "meta",
        "model_id": "",
        "prompt": STRATEGIC_SIGNALS_PROMPT,
        "enabled": True,
        "sub_types": "",
        "interval_seconds": 45,
        "display_order": 9,
    },
    {
        "slug": "transcript_refiner",
        "name": "Transkript-Korrektur",
        "description": "Korrigiert Zeichensetzung, Großschreibung, Satzgrenzen und offensichtliche Verhörer, ohne den Inhalt umzuschreiben.",
        "agent_type": "text",
        "model_id": "",
        "prompt": TRANSCRIPT_REFINER_PROMPT,
        "enabled": False,
        "sub_types": "",
        "interval_seconds": 45,
        "display_order": 10,
    },
    {
        "slug": "brief_meeting_lens",
        "name": "Sitzungsprotokoll",
        "description": "Erstellt nach Gesprächsende ein sachliches Protokoll mit Ergebnissen, Entscheidungen, Hindernissen, Zusagen und nächsten Schritten.",
        "agent_type": "meta",
        "model_id": "",
        "prompt": BRIEF_MEETING_LENS_PROMPT,
        "enabled": True,
        "sub_types": "",
        "display_order": 5,
    },
    {
        "slug": "brief_discovery_lens",
        "name": "Erkenntnisanalyse",
        "description": "Verdichtet nach Gesprächsende Ziele, Probleme, Wissenslücken, Chancen, Risiken und offene Fragen.",
        "agent_type": "meta",
        "model_id": "",
        "prompt": BRIEF_DISCOVERY_LENS_PROMPT,
        "enabled": True,
        "sub_types": "",
        "display_order": 6,
    },
    {
        "slug": "brief_arbiter",
        "name": "Abschlussredaktion",
        "description": "Führt Protokoll und Erkenntnisanalyse zu einer widerspruchsarmen, klaren Abschlussanalyse zusammen.",
        "agent_type": "meta",
        "model_id": "",
        "prompt": BRIEF_ARBITER_PROMPT,
        "enabled": True,
        "sub_types": "",
        "display_order": 7,
    },
]


async def seed_agent_configs(db: AsyncSession):
    """Insert default agent configs if they don't already exist."""
    for cfg in SEED_CONFIGS:
        result = await db.execute(
            select(AgentConfig).where(AgentConfig.slug == cfg["slug"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(AgentConfig(**cfg))
        # Descriptions are seed-owned (no UI edits them): keep rows in sync
        if existing is not None and existing.description != cfg["description"]:
            existing.description = cfg["description"]
        # Preserve custom names while translating former seeded labels.
        if (
            existing is not None
            and existing.name in {
                "Audio Bridge",
                "Consolidated Analyst",
                "Objection Handler",
                "Principal Agent",
                "Opportunity Specialist",
                "Strategic Signals",
                "Transcript Refiner",
                "Briefing Meeting Lens",
                "Briefing Discovery Lens",
                "Briefing Arbiter",
            }
        ):
            existing.name = cfg["name"]
        if existing is not None:
            _seed_missing_lenses(existing)
        load_prompt_resource(
            f"agent.{cfg['slug']}",
            str(existing.prompt if existing is not None else cfg.get("prompt", "")),
        )
    batch_model = await get_app_setting(db, SETTING_BATCH_TRANSCRIBER_MODEL, None)
    fixed_german_asr = await get_app_setting(db, _FIXED_GERMAN_ASR_VERSION_KEY, "")
    if fixed_german_asr != "1":
        if batch_model in (None, "", "local-parakeet-tdt-0.6b-v3"):
            # Parakeet v3 is fast, but it detects language independently for
            # every segment and cannot honor the fixed German setting. Whisper
            # takes language="de", so final transcript entries never begin as
            # English guesses. This one-time migration preserves later manual
            # model choices.
            await set_app_setting(
                db,
                SETTING_BATCH_TRANSCRIBER_MODEL,
                "local-whisper-base",
            )
        await set_app_setting(db, _FIXED_GERMAN_ASR_VERSION_KEY, "1")
    # This desktop edition is configured as a German-only debate assistant.
    # Migrate the old automatic-detection default as well as a missing value;
    # explicit non-German choices remain respected.
    language = await get_app_setting(db, SETTING_TRANSCRIPTION_LANGUAGE, None)
    if language in (None, "", "auto"):
        await set_app_setting(db, SETTING_TRANSCRIPTION_LANGUAGE, "de")
    await db.commit()


async def configure_desktop_debate_runtime(db: AsyncSession) -> None:
    """One-time native-desktop wiring for the latency-critical live copilot.

    The standalone Docker setup already registers Ollama through the REST API.
    A native desktop launch owns the local Ollama lifecycle itself, so it also
    needs the matching registry row. The marker is written once: later manual
    model choices remain authoritative instead of being reset on every start.
    """
    if env_value("DEBATEAI_DESKTOP") != "1":
        return
    completed = await get_app_setting(db, _DESKTOP_DEBATE_BOOTSTRAP_KEY, "")
    first_bootstrap = completed != "1"

    defaults_version = await get_app_setting(
        db, _IDEAL_DEBATE_DEFAULTS_VERSION_KEY, ""
    )
    if defaults_version != "1":
        from app.services.debate_settings import (
            SETTING_KEY as DEBATE_SETTINGS_KEY,
            DebateSettings,
            set_debate_settings,
        )

        raw_settings = await get_app_setting(db, DEBATE_SETTINGS_KEY, "") or ""
        known_old_defaults = {
            "",
            DebateSettings().to_json(),
            DebateSettings(
                research_enabled=True,
                research_frequency="often",
            ).to_json(),
        }
        if raw_settings in known_old_defaults:
            await set_debate_settings(db, DebateSettings(
                mode="persuasive",
                research_enabled=False,
                research_frequency="never",
                always_analogy=False,
                style_focus="natural",
                voice_commands_enabled=True,
                argument_memory_enabled=True,
                transcript_retention_enabled=True,
                audio_archive_enabled=False,
                session_retrieval_enabled=True,
                learning_examples_enabled=True,
                graph_recording_enabled=True,
                performance_profile="balanced",
            ))
        await set_app_setting(db, _IDEAL_DEBATE_DEFAULTS_VERSION_KEY, "1")

    # Older desktop seeds pointed every analysis role at the official Gemini
    # API.  That both bypasses the user's personal web subscriptions and leaves
    # a fresh install asking for an API key.  Migrate only that exact old seed
    # (or an unselected seed); any other model is an explicit user choice.
    web_first_models_version = await get_app_setting(
        db, _WEB_FIRST_AGENT_MODELS_VERSION_KEY, ""
    )
    if web_first_models_version != "1":
        result = await db.execute(
            select(AgentConfig).where(AgentConfig.slug.in_(_WEB_FIRST_ANALYSIS_SLUGS))
        )
        for agent in result.scalars().all():
            if (agent.model_id or "").strip() in _KNOWN_OLD_ANALYSIS_MODELS:
                agent.model_id = "chatgpt-web:gpt-6"
        await set_app_setting(db, _WEB_FIRST_AGENT_MODELS_VERSION_KEY, "1")

    endpoint = await db.get(CustomEndpoint, DESKTOP_DEBATE_ENDPOINT_ID)
    if first_bootstrap and endpoint is None:
        db.add(
            CustomEndpoint(
                id=DESKTOP_DEBATE_ENDPOINT_ID,
                name="Deutsche Live-Debatte (Ollama)",
                base_url="http://127.0.0.1:11434/v1",
                api_key="",
                models=[
                    {
                        "id": DESKTOP_DEBATE_WIRE_MODEL,
                        "label": "Qwen3 4B – Deutsche Live-Debatte",
                    }
                ],
                enabled=True,
                display_order=0,
            )
        )

    result = await db.execute(
        select(AgentConfig).where(AgentConfig.slug == "objection_handler")
    )
    objection_handler = result.scalar_one_or_none()
    if objection_handler is not None:
        if first_bootstrap:
            objection_handler.model_id = DESKTOP_DEBATE_MODEL_ID

        prompt_version = await get_app_setting(db, _DEBATE_PROMPT_VERSION_KEY, "")
        current_prompt = str(objection_handler.prompt or "")
        prompt_hash = hashlib.sha256(current_prompt.encode("utf-8")).hexdigest()
        if prompt_version != DEBATE_LIVE_PROMPT_VERSION:
            if not current_prompt or prompt_hash in _BUILTIN_DEBATE_PROMPT_HASHES:
                objection_handler.prompt = DEBATE_RECOMMENDATION_PROMPT
                prompt_version = DEBATE_LIVE_PROMPT_VERSION
            elif prompt_version != "manual-preserved":
                prompt_version = "manual-preserved"
            await set_app_setting(db, _DEBATE_PROMPT_VERSION_KEY, prompt_version)

    if first_bootstrap:
        await set_app_setting(db, _DESKTOP_DEBATE_BOOTSTRAP_KEY, "1")
    await db.flush()


def _seed_missing_lenses(existing: AgentConfig):
    """Populate the lenses column for pre-lens rows, honoring the old sub_types
    selection so previously deselected lenses stay off."""
    if (getattr(existing, "lenses", "") or "").strip():
        return
    defaults = DEFAULT_LENSES_BY_SLUG.get(existing.slug)
    if not defaults:
        return
    selected = {t.strip() for t in (existing.sub_types or "").split(",") if t.strip()}
    lenses = [dict(lens) for lens in defaults]
    if selected:
        for lens in lenses:
            lens["enabled"] = lens["item_type"] in selected
    existing.lenses = json.dumps(lenses)
