"""Manage the optional Gemini Web subscription bridge without exposing secrets."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.secrets import MasterKeyUnavailable, master_key_recovery_message
from app.services.subscription_bridge import (
    cleanup_gemini_web_cookie,
    gemini_web_models,
    materialize_gemini_web_cookie,
    save_gemini_web_cookie,
    sync_gemini_web_bridge,
    stored_gemini_web_cookie_configured,
)

router = APIRouter(prefix="/api/gemini-web", tags=["gemini-web"])

_MAX_COOKIE_BYTES = 64 * 1024
_REQUIRED_COOKIES = ("__Secure-1PSID", "__Secure-1PSIDTS")
_PRO_MODEL = "gemini-3.1-pro"
_login_process: subprocess.Popen | None = None
_login_lock = threading.Lock()


async def _status(
    db: AsyncSession,
    *,
    login_state: str = "idle",
    login_message: str = "",
) -> dict[str, object]:
    configured = await stored_gemini_web_cookie_configured(db)
    models = gemini_web_models()
    pro_available = _PRO_MODEL in models
    return {
        "available": bool(
            os.environ.get("BACKCHANNEL_GEMINI_WEB_URL", "").strip()
            and os.environ.get("BACKCHANNEL_GEMINI_WEB_KEY", "").strip()
        ),
        "configured": configured,
        "ready": configured and bool(models),
        "pro_available": pro_available,
        "models": models,
        "model": _PRO_MODEL if pro_available else "",
        "thinking": "High wird angefordert; die Antwort weist das tatsaechliche Modell aus.",
        "login_available": bool(
            os.environ.get("BACKCHANNEL_GEMINI_WEB_LOGIN_COMMAND", "").strip()
            and os.environ.get("BACKCHANNEL_GEMINI_WEB_LOGIN_RESULT", "").strip()
        ),
        "login_state": login_state,
        "message": (
            login_message
            or (
                "Gemini 3.1 Pro ist fuer dieses Konto nachgewiesen und als Web-Fallback bereit."
                if pro_available
                else (
                    "Die Anmeldung ist aktiv, aber das Konto meldet Gemini 3.1 Pro nicht als waehlbares Modell."
                    if configured and models
                    else (
                        "Die Anmeldung wird geprueft."
                        if configured
                        else "Melde dich lokal mit deinem Gemini-Konto an."
                    )
                )
            )
        ),
    }


def _from_netscape_cookie_file(value: str) -> str:
    pairs: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) >= 7:
            pairs.append(f"{fields[-2]}={fields[-1]}")
    return "; ".join(pairs)


def _normalize_cookie(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Die Cookie-Datei ist leer.")
    if value.startswith("{"):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Die Cookie-JSON-Datei ist ungueltig.") from exc
        value = str(payload.get("cookie", "")).strip()
    elif "\t" in value:
        value = _from_netscape_cookie_file(value)
    value = value.replace("\r", "").replace("\n", "")
    missing = [name for name in _REQUIRED_COOKIES if f"{name}=" not in value]
    if missing:
        raise ValueError(
            "Die Datei enthaelt nicht die erforderlichen Gemini-Cookies: "
            + ", ".join(missing)
        )
    return value


def _login_configuration() -> tuple[list[str], Path]:
    raw_command = os.environ.get("BACKCHANNEL_GEMINI_WEB_LOGIN_COMMAND", "").strip()
    raw_result = os.environ.get("BACKCHANNEL_GEMINI_WEB_LOGIN_RESULT", "").strip()
    if not raw_command or not raw_result:
        raise ValueError("Das lokale Gemini-Anmeldemodul ist nicht verfuegbar.")
    try:
        command = json.loads(raw_command)
    except json.JSONDecodeError as exc:
        raise ValueError("Das lokale Gemini-Anmeldemodul ist ungueltig konfiguriert.") from exc
    if not isinstance(command, list) or not command or not all(
        isinstance(part, str) and part for part in command
    ):
        raise ValueError("Das lokale Gemini-Anmeldemodul ist ungueltig konfiguriert.")
    return command, Path(raw_result)


def _take_login_result() -> tuple[dict[str, str] | None, str]:
    global _login_process
    command, result_path = _login_configuration()
    del command
    with _login_lock:
        process = _login_process
        if result_path.is_file():
            try:
                raw = result_path.read_bytes()
            finally:
                result_path.unlink(missing_ok=True)
            if len(raw) > _MAX_COOKIE_BYTES:
                return None, "Die lokale Anmeldung lieferte zu viele Daten."
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None, "Die lokale Anmeldung lieferte ein ungueltiges Ergebnis."
            _login_process = None
            return payload if isinstance(payload, dict) else None, ""
        if process is not None and process.poll() is None:
            return None, "pending"
        if process is not None:
            _login_process = None
            return None, "Die lokale Anmeldung wurde ohne Ergebnis beendet."
    return None, "idle"


@router.get("/status")
async def read_status(db: AsyncSession = Depends(get_db)):
    return await _status(db)


@router.post("/login")
async def start_login(db: AsyncSession = Depends(get_db)):
    global _login_process
    try:
        command, result_path = _login_configuration()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    already_open = False
    with _login_lock:
        if _login_process is not None and _login_process.poll() is None:
            already_open = True
        else:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.unlink(missing_ok=True)
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
            try:
                _login_process = subprocess.Popen(
                    [*command, "--gemini-web-login", str(result_path)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=flags,
                )
            except OSError as exc:
                _login_process = None
                raise HTTPException(
                    status_code=503, detail="Das Gemini-Anmeldefenster konnte nicht gestartet werden."
                ) from exc
    if already_open:
        return await _status(
            db,
            login_state="pending",
            login_message="Das Anmeldefenster ist bereits offen.",
        )
    return await _status(
        db,
        login_state="pending",
        login_message="Melde dich im geoeffneten Fenster mit deinem eigenen Google-Konto an.",
    )


@router.get("/login")
async def poll_login(db: AsyncSession = Depends(get_db)):
    try:
        payload, state = _take_login_result()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if payload is None:
        if state in {"pending", "idle"}:
            return await _status(db, login_state=state)
        return await _status(db, login_state="error", login_message=state)
    error = str(payload.get("error") or "").strip()
    if error:
        return await _status(db, login_state="error", login_message=error)
    try:
        normalized = _normalize_cookie(str(payload.get("cookie") or ""))
    except ValueError as exc:
        return await _status(db, login_state="error", login_message=str(exc))
    try:
        await save_gemini_web_cookie(db, normalized)
        await db.commit()
    except MasterKeyUnavailable as exc:
        raise HTTPException(status_code=503, detail=master_key_recovery_message(exc)) from exc
    materialize_gemini_web_cookie(normalized)
    await sync_gemini_web_bridge(db)
    await db.commit()
    return await _status(
        db,
        login_state="complete",
        login_message="Die lokale Gemini-Anmeldung wurde sicher uebernommen.",
    )


@router.put("/cookie")
async def import_cookie(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    content = await file.read(_MAX_COOKIE_BYTES + 1)
    if len(content) > _MAX_COOKIE_BYTES:
        raise HTTPException(status_code=413, detail="Die Cookie-Datei ist zu gross.")
    try:
        normalized = _normalize_cookie(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        await save_gemini_web_cookie(db, normalized)
        await db.commit()
    except MasterKeyUnavailable as exc:
        raise HTTPException(status_code=503, detail=master_key_recovery_message(exc)) from exc
    materialize_gemini_web_cookie(normalized)
    await sync_gemini_web_bridge(db)
    await db.commit()
    return await _status(db)


@router.delete("/cookie", status_code=204)
async def delete_cookie(db: AsyncSession = Depends(get_db)):
    try:
        await save_gemini_web_cookie(db, "")
        await db.commit()
    except MasterKeyUnavailable as exc:
        raise HTTPException(status_code=503, detail=master_key_recovery_message(exc)) from exc
    cleanup_gemini_web_cookie()
    await sync_gemini_web_bridge(db)
    await db.commit()
