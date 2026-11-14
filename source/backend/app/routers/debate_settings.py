"""Administration controls for live debate analysis and research."""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.debate_settings import (
    DebateMode,
    PipelineMode,
    DebateSettings,
    PerformanceProfile,
    ResearchFrequency,
    StyleFocus,
    get_debate_settings,
    set_debate_settings,
    settings_payload,
    debate_profiles,
)

router = APIRouter(prefix="/api/debate-settings", tags=["debate-settings"])


class DebateSettingsUpdate(BaseModel):
    mode: DebateMode | None = None
    pipeline_mode: PipelineMode | None = None
    research_enabled: bool | None = None
    research_frequency: ResearchFrequency | None = None
    always_analogy: bool | None = None
    style_focus: StyleFocus | None = None
    voice_commands_enabled: bool | None = None
    argument_memory_enabled: bool | None = None
    transcript_retention_enabled: bool | None = None
    audio_archive_enabled: bool | None = None
    session_retrieval_enabled: bool | None = None
    learning_examples_enabled: bool | None = None
    graph_recording_enabled: bool | None = None
    memory_similarity_threshold: float | None = Field(default=None, ge=0.1, le=0.95)
    performance_profile: PerformanceProfile | None = None
    simple_1to1_audio_mode: bool | None = None


@router.get("")
async def read_debate_settings(db: AsyncSession = Depends(get_db)):
    return settings_payload(await get_debate_settings(db))


@router.patch("")
async def update_debate_settings(
    update: DebateSettingsUpdate, db: AsyncSession = Depends(get_db)
):
    current = await get_debate_settings(db)
    changes = {
        name: value
        for name, value in update.model_dump().items()
        if value is not None
    }
    if set(changes).intersection({"mode", "style_focus", "research_frequency", "always_analogy"}):
        changes.update({"profile_id": "", "profile_directive": ""})
    updated: DebateSettings = replace(current, **changes)
    await set_debate_settings(db, updated)
    await db.commit()
    return settings_payload(updated)


@router.get("/profiles")
async def read_debate_profiles():
    return debate_profiles()


@router.post("/profiles/{profile_id}")
async def apply_debate_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = next((item for item in debate_profiles() if item["id"] == profile_id), None)
    if profile is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Unknown debate profile")
    current = await get_debate_settings(db)
    updated = replace(
        current,
        mode=profile["mode"],
        style_focus=profile["style_focus"],
        research_frequency=profile["research_frequency"],
        always_analogy=profile["always_analogy"],
        profile_id=profile["id"],
        profile_directive=profile["profile_directive"],
    )
    await set_debate_settings(db, updated)
    await db.commit()
    return settings_payload(updated)
