"""Validated, persisted controls for the live Debate Copilot."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.app_settings import get_app_setting, set_app_setting

SETTING_KEY = "debate.copilot.settings"
RESEARCH_COOLDOWNS = {"never": 0, "low": 180, "normal": 60, "often": 20}
DebateMode = Literal["persuasive", "forceful"]
PipelineMode = Literal["standard", "experimental_debateai"]
ResearchFrequency = Literal["never", "low", "normal", "often"]
StyleFocus = Literal["balanced", "natural", "concise", "evidence"]
PerformanceProfile = Literal["balanced", "economy"]

PROFILE_DEFINITIONS = {
    "factual": {
        "id": "factual", "name": "Sachlich",
        "description": "Belege, faire Einordnung und eine klare Schlussfolgerung.",
        "mode": "persuasive", "style_focus": "evidence",
        "research_frequency": "normal", "always_analogy": False,
        "playbook_term": "beweislast",
    },
    "concise": {
        "id": "concise", "name": "Knapp",
        "description": "Eine direkte Hauptantwort ohne Einleitung oder Wiederholung.",
        "mode": "persuasive", "style_focus": "concise",
        "research_frequency": "low", "always_analogy": False,
        "playbook_term": "widerlegen",
    },
    "socratic": {
        "id": "socratic", "name": "Sokratisch",
        "description": "Die engste Frage legt Prämisse und Beweislast offen.",
        "mode": "persuasive", "style_focus": "natural",
        "research_frequency": "low", "always_analogy": False,
        "playbook_term": "gegenfrage",
    },
    "confrontational": {
        "id": "confrontational", "name": "Konfrontativ",
        "description": "Direkt und druckvoll in der Sache, ohne persönlichen Angriff.",
        "mode": "forceful", "style_focus": "concise",
        "research_frequency": "normal", "always_analogy": False,
        "playbook_term": "offensiv",
    },
}


def is_desktop_bundle() -> bool:
    return bool(getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None))


@dataclass(frozen=True)
class DebateSettings:
    mode: DebateMode = "persuasive"
    research_enabled: bool = False
    research_frequency: ResearchFrequency = "normal"
    always_analogy: bool = False
    style_focus: StyleFocus = "natural"
    voice_commands_enabled: bool = True
    argument_memory_enabled: bool = True
    transcript_retention_enabled: bool = True
    audio_archive_enabled: bool = False
    session_retrieval_enabled: bool = True
    learning_examples_enabled: bool = True
    graph_recording_enabled: bool = True
    memory_similarity_threshold: float = 0.34
    performance_profile: PerformanceProfile = "balanced"
    simple_1to1_audio_mode: bool = False
    profile_id: str = ""
    profile_directive: str = ""
    # Selects the orchestration pipeline; standard preserves positional compatibility.
    pipeline_mode: PipelineMode = "standard"

    @property
    def cooldown_seconds(self) -> int:
        return RESEARCH_COOLDOWNS[self.research_frequency]

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


def default_debate_settings() -> DebateSettings:
    if is_desktop_bundle():
        return DebateSettings(research_enabled=False, research_frequency="never")
    return DebateSettings()


def _from_json(raw: str) -> DebateSettings:
    fallback = default_debate_settings()
    if not raw:
        return fallback
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return fallback
    if not isinstance(data, dict):
        return fallback

    mode = data.get("mode")
    pipeline_mode = data.get("pipeline_mode")
    frequency = data.get("research_frequency")
    enabled = data.get("research_enabled")
    analogy = data.get("always_analogy")
    style_focus = data.get("style_focus")
    voice_commands = data.get("voice_commands_enabled")
    argument_memory = data.get("argument_memory_enabled")
    transcript_retention = data.get("transcript_retention_enabled")
    audio_archive = data.get("audio_archive_enabled")
    session_retrieval = data.get("session_retrieval_enabled")
    learning_examples = data.get("learning_examples_enabled")
    graph_recording = data.get("graph_recording_enabled")
    memory_threshold = data.get("memory_similarity_threshold")
    performance_profile = data.get("performance_profile")
    simple_1to1_audio_mode = data.get("simple_1to1_audio_mode")
    profile_id = data.get("profile_id")
    profile_directive = data.get("profile_directive")
    if not isinstance(profile_id, str):
        profile_id = ""
    if not isinstance(frequency, str):
        frequency = ""
    if not isinstance(memory_threshold, (int, float)) or isinstance(memory_threshold, bool):
        memory_threshold = fallback.memory_similarity_threshold
    elif not 0.1 <= float(memory_threshold) <= 0.95:
        memory_threshold = fallback.memory_similarity_threshold
    return DebateSettings(
        mode=mode if mode in ("persuasive", "forceful") else fallback.mode,
        pipeline_mode=(
            pipeline_mode
            if pipeline_mode in ("standard", "experimental_debateai")
            else fallback.pipeline_mode
        ),
        research_enabled=enabled if isinstance(enabled, bool) else fallback.research_enabled,
        research_frequency=(
            frequency if frequency in RESEARCH_COOLDOWNS else fallback.research_frequency
        ),
        always_analogy=analogy if isinstance(analogy, bool) else fallback.always_analogy,
        style_focus=(
            style_focus
            if style_focus in ("balanced", "natural", "concise", "evidence")
            else fallback.style_focus
        ),
        voice_commands_enabled=(
            voice_commands if isinstance(voice_commands, bool)
            else fallback.voice_commands_enabled
        ),
        argument_memory_enabled=(
            argument_memory if isinstance(argument_memory, bool)
            else fallback.argument_memory_enabled
        ),
        transcript_retention_enabled=(
            transcript_retention if isinstance(transcript_retention, bool)
            else fallback.transcript_retention_enabled
        ),
        audio_archive_enabled=(
            audio_archive if isinstance(audio_archive, bool)
            else fallback.audio_archive_enabled
        ),
        session_retrieval_enabled=(
            session_retrieval if isinstance(session_retrieval, bool)
            else fallback.session_retrieval_enabled
        ),
        learning_examples_enabled=(
            learning_examples if isinstance(learning_examples, bool)
            else fallback.learning_examples_enabled
        ),
        graph_recording_enabled=(
            graph_recording if isinstance(graph_recording, bool)
            else fallback.graph_recording_enabled
        ),
        memory_similarity_threshold=float(memory_threshold),
        performance_profile=(
            performance_profile
            if performance_profile in ("balanced", "economy")
            else fallback.performance_profile
        ),
        simple_1to1_audio_mode=(
            simple_1to1_audio_mode
            if isinstance(simple_1to1_audio_mode, bool)
            else fallback.simple_1to1_audio_mode
        ),
        profile_id=profile_id if profile_id in PROFILE_DEFINITIONS else "",
        profile_directive=(
            profile_directive
            if isinstance(profile_directive, str) and profile_id in PROFILE_DEFINITIONS
            else ""
        ),
    )


async def get_debate_settings(db: AsyncSession) -> DebateSettings:
    raw = await get_app_setting(db, SETTING_KEY, "")
    return _from_json(raw)


async def set_debate_settings(
    db: AsyncSession, value: DebateSettings
) -> DebateSettings:
    await set_app_setting(db, SETTING_KEY, value.to_json())
    return value


def settings_payload(value: DebateSettings) -> dict:
    return {**asdict(value), "cooldown_seconds": value.cooldown_seconds}


def debate_profiles() -> list[dict]:
    from app.services.ai_config import playbook_controls

    controls = playbook_controls()
    profiles = []
    for value in PROFILE_DEFINITIONS.values():
        directive = next(
            (
                directive
                for terms, directive in controls
                if value["playbook_term"] in {term.casefold() for term in terms}
            ),
            "",
        )
        profiles.append({
            **value,
            "profile_directive": directive,
            "resources": [
                f"mode.{value['mode']}",
                f"style.{value['style_focus']}",
                "phase.automatic",
                "playbooks.json",
            ],
        })
    return profiles
