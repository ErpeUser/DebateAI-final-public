"""Status and interactive login for the normal ChatGPT browser provider."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.services import chatgpt_web
from app.services.identity import env_value

router = APIRouter(prefix="/api/chatgpt-web", tags=["chatgpt-web"])
_login_process: subprocess.Popen | None = None
_login_lock = threading.Lock()


def _setting(name: str) -> str:
    return env_value(f"DEBATEAI_CHATGPT_WEB_{name}").strip()


def _archive_dedicated_account(*, include_profile: bool) -> Path:
    """Recoverably detach only DebateAI's dedicated ChatGPT account state."""
    home = Path(_setting("HOME"))
    profile = Path(_setting("PROFILE"))
    marker = Path(_setting("MARKER"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = home / "account-backups" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    moves = [(marker, archive / "verified.json")]
    if include_profile:
        moves.append((profile, archive / "browser-profile"))
    completed: list[tuple[Path, Path]] = []
    try:
        for source, destination in moves:
            if not source.exists():
                continue
            source.replace(destination)
            completed.append((source, destination))
    except OSError:
        for source, destination in reversed(completed):
            if destination.exists() and not source.exists():
                destination.replace(source)
        raise
    return archive


def _configuration() -> tuple[list[str], Path]:
    raw_command = _setting("LOGIN_COMMAND")
    raw_result = _setting("LOGIN_RESULT")
    if not raw_command or not raw_result:
        raise ValueError("Das lokale ChatGPT-Anmeldemodul ist nicht verfuegbar.")
    try:
        command = json.loads(raw_command)
    except json.JSONDecodeError as exc:
        raise ValueError("Das lokale ChatGPT-Anmeldemodul ist ungueltig konfiguriert.") from exc
    if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("Das lokale ChatGPT-Anmeldemodul ist ungueltig konfiguriert.")
    return command, Path(raw_result)


def _evidence() -> dict[str, object]:
    marker = _setting("MARKER")
    if not marker:
        return {}
    try:
        value = json.loads(Path(marker).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status(*, state: str = "idle", message: str = "") -> dict[str, object]:
    evidence = _evidence()
    ready = chatgpt_web.runtime_available() and chatgpt_web.configured() and bool(evidence)
    verification_failure = chatgpt_web.verification_failure()
    return {
        "available": chatgpt_web.runtime_available(),
        "configured": chatgpt_web.configured(),
        "ready": ready,
        "model": evidence.get("actual_model", ""),
        "thinking": evidence.get("thinking", ""),
        "latency_ms": evidence.get("latency_ms"),
        "verified_at": evidence.get("verified_at", ""),
        "verification": evidence.get("verification", ""),
        "research_status": chatgpt_web.research_status(),
        "login_available": bool(_setting("LOGIN_COMMAND")),
        "login_state": state,
        "message": message or (
            "GPT-6 mit Extra High wurde in der ChatGPT-Oberflaeche bestaetigt und ist bereit."
            if ready
            else "Die ChatGPT-Auswahl konnte nicht mehr bestaetigt werden. Erneut anmelden."
            if verification_failure
            else "Melde dich einmal im separaten ChatGPT-Fenster an."
        ),
    }


@router.get("/status")
async def read_status():
    return _status()


@router.post("/login")
async def start_login():
    global _login_process
    try:
        command, result = _configuration()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with _login_lock:
        if _login_process is not None and _login_process.poll() is None:
            return _status(state="pending", message="Das ChatGPT-Anmeldefenster ist bereits offen.")
        if not chatgpt_web.reserve_login():
            raise HTTPException(
                status_code=409,
                detail="ChatGPT Web bearbeitet gerade eine Anfrage. Bitte gleich erneut versuchen.",
            )
        result.parent.mkdir(parents=True, exist_ok=True)
        result.unlink(missing_ok=True)
        try:
            _login_process = subprocess.Popen(
                [*command, "--chatgpt-web-login", str(result)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0,
            )
        except OSError as exc:
            chatgpt_web.release_login()
            raise HTTPException(status_code=503, detail="Das ChatGPT-Anmeldefenster konnte nicht gestartet werden.") from exc
    return _status(state="pending", message="Melde dich im geoeffneten Chrome-Fenster bei ChatGPT an. Die Pro-Pruefung startet danach automatisch.")


@router.get("/login")
async def poll_login():
    global _login_process
    try:
        _command, result = _configuration()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with _login_lock:
        process = _login_process
        if result.is_file():
            try:
                payload = json.loads(result.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {"error": "Die lokale Anmeldung lieferte ein ungueltiges Ergebnis."}
            finally:
                result.unlink(missing_ok=True)
            _login_process = None
            chatgpt_web.release_login()
            error = str(payload.get("error", "")) if isinstance(payload, dict) else ""
            return _status(state="error" if error else "complete", message=error)
        if process is not None and process.poll() is None:
            return _status(state="pending", message="Die Anmeldung oder Pro-Pruefung laeuft.")
        if process is not None:
            _login_process = None
            chatgpt_web.release_login()
            return _status(state="error", message="Die Anmeldung wurde ohne bestaetigten GPT-6-Pro-Nachweis beendet.")
    return _status()


@router.post("/account/disconnect")
async def disconnect_account():
    with _login_lock:
        if (_login_process is not None and _login_process.poll() is None) or chatgpt_web.browser_busy():
            raise HTTPException(status_code=409, detail="ChatGPT Web ist gerade beschaeftigt.")
        try:
            _archive_dedicated_account(include_profile=False)
        except (KeyError, OSError) as exc:
            raise HTTPException(
                status_code=409,
                detail="Die ChatGPT-Verbindung konnte nicht getrennt werden. Bitte das separate ChatGPT-Fenster schliessen und erneut versuchen.",
            ) from exc
    return _status(message="Verbindung getrennt. Die lokale Sitzung bleibt fuer eine erneute Anmeldung erhalten.")


@router.post("/account/switch")
async def switch_account():
    with _login_lock:
        if (_login_process is not None and _login_process.poll() is None) or chatgpt_web.browser_busy():
            raise HTTPException(status_code=409, detail="ChatGPT Web ist gerade beschaeftigt.")
        try:
            _archive_dedicated_account(include_profile=True)
        except (KeyError, OSError) as exc:
            raise HTTPException(
                status_code=409,
                detail="Das dedizierte ChatGPT-Profil ist noch geoeffnet. Bitte das separate ChatGPT-Fenster schliessen und erneut versuchen.",
            ) from exc
    return await start_login()
