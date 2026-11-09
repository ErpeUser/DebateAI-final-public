"""Local-only controls for the desktop WASAPI capture service."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session
from pydantic import BaseModel

from app.services.windows_audio_capture import native_windows_audio


router = APIRouter(prefix="/api/native-audio", tags=["native-audio"])


class NativeAudioStart(BaseModel):
    session_id: uuid.UUID
    system_audio: bool = True
    microphone_index: int | None = None
    loopback_index: int | None = None
    microphone_id: str | None = None
    loopback_id: str | None = None
    microphone_mode: Literal["fixed", "follow_default"] = "follow_default"
    loopback_mode: Literal["fixed", "follow_default"] = "follow_default"


class NativeAudioProbe(BaseModel):
    microphone_index: int


class NativeAudioStop(BaseModel):
    session_id: uuid.UUID


@router.get("/status")
async def native_audio_status():
    return native_windows_audio.status()


@router.get("/devices")
async def native_audio_devices():
    return {
        "available": native_windows_audio.available,
        "devices": native_windows_audio.devices(),
    }


@router.post("/start")
async def start_native_audio(request: NativeAudioStart, db: AsyncSession = Depends(get_db)):
    session = await db.get(Session, request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.state) not in {"pre_call", "active"}:
        raise HTTPException(status_code=409, detail="Session is not recordable")
    if not native_windows_audio.available:
        raise HTTPException(status_code=503, detail="Native Windows-Audioaufnahme ist nicht verfuegbar")
    try:
        return await native_windows_audio.start(
            request.session_id,
            system_audio=request.system_audio,
            microphone_index=request.microphone_index,
            loopback_index=request.loopback_index,
            microphone_id=request.microphone_id,
            loopback_id=request.loopback_id,
            microphone_mode=request.microphone_mode,
            loopback_mode=request.loopback_mode,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"Audiogeraet konnte nicht geoeffnet werden: {exc}") from exc


@router.post("/stop")
async def stop_native_audio(request: NativeAudioStop, db: AsyncSession = Depends(get_db)):
    session = await db.get(Session, request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return await native_windows_audio.stop_session(request.session_id)


@router.post("/probe")
async def probe_native_audio(request: NativeAudioProbe, db: AsyncSession = Depends(get_db)):
    try:
        level = await native_windows_audio.probe_microphone(request.microphone_index)
        return {"level": level}
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
