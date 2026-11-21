"""One-shot adapter for the user's normal ChatGPT web subscription.

Oracle drives a dedicated Chrome profile and deliberately fails when it cannot
confirm GPT-6 in the visible ChatGPT UI.  This is separate from API keys
and from the CLIProxyAPI/Codex OAuth bridge.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.services import external_audit
from app.services.identity import env_value
from app.services.redaction import redact_text

MODEL_ID = "chatgpt-web:gpt-6"
PROVIDER = "chatgpt-web"
# Keep consumer-web runs isolated from the user's history and memory. Oracle
# accepts this URL directly and still uses the dedicated signed-in profile for
# the model-selection check; the temporary-chat flag only changes conversation
# persistence/personalization in ChatGPT Web.
CHATGPT_TEMPORARY_URL = "https://chatgpt.com/?temporary-chat=true"
_ORACLE_LOCK = asyncio.Lock()
_LOGIN_RESERVED = False


def _setting(name: str) -> str:
    return env_value(f"DEBATEAI_CHATGPT_WEB_{name}").strip()


def reserve_login() -> bool:
    """Reserve the dedicated browser for the asynchronous login helper."""
    global _LOGIN_RESERVED
    if _LOGIN_RESERVED or _ORACLE_LOCK.locked():
        return False
    _LOGIN_RESERVED = True
    return True


def release_login() -> None:
    global _LOGIN_RESERVED
    _LOGIN_RESERVED = False


def browser_busy() -> bool:
    return _LOGIN_RESERVED or _ORACLE_LOCK.locked()


def _path(name: str) -> Path:
    suffix = name.rsplit("_", 1)[-1]
    value = (
        _setting(suffix)
        if name.startswith("DEBATEAI_CHATGPT_WEB_")
        else os.environ.get(name, "").strip()
    )
    return Path(value) if value else Path()


def runtime_available() -> bool:
    return bool(
        _setting("NODE")
        and _setting("ORACLE")
        and _path("DEBATEAI_CHATGPT_WEB_NODE").is_file()
        and _path("DEBATEAI_CHATGPT_WEB_ORACLE").is_file()
    )


def verification_evidence() -> dict[str, object]:
    """Read the non-secret Oracle proof for the dedicated browser account."""
    marker = _setting("MARKER")
    if not marker:
        return {}
    try:
        payload = json.loads(Path(marker).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def verified_selection() -> dict[str, bool]:
    evidence = verification_evidence()
    actual_model = str(evidence.get("actual_model") or "").casefold().strip()
    requested_model = str(evidence.get("requested_model") or "").casefold().strip()
    model_label = str(evidence.get("model_label") or "").strip()
    thinking = str(evidence.get("thinking") or "").casefold().strip()
    thinking_label = str(evidence.get("thinking_label") or "").casefold().strip()
    verification = str(evidence.get("verification") or "").strip()
    return {
        "model_confirmed": (
            actual_model == "gpt-6"
            and requested_model == "gpt-6"
            and model_label == "GPT-6"
            and bool(verification)
            and bool(evidence.get("verified_at"))
        ),
        "thinking_confirmed": (
            thinking == "xhigh"
            and thinking_label == "extra high"
            and bool(verification)
            and bool(evidence.get("verified_at"))
        ),
    }


def model_confirmed() -> bool:
    return verified_selection()["model_confirmed"]


def configured() -> bool:
    marker = _setting("MARKER")
    if not marker or not Path(marker).is_file():
        return False
    selection = verified_selection()
    if not selection["model_confirmed"] or not selection["thinking_confirmed"]:
        return False
    failure = _verification_failure_path()
    try:
        return (
            not failure.is_file()
            or Path(marker).stat().st_mtime_ns > failure.stat().st_mtime_ns
        )
    except OSError:
        return False


def _verification_failure_path() -> Path:
    marker = _setting("MARKER")
    return Path(marker).with_name("verification-failed.json") if marker else Path()


def verification_failure() -> str:
    failure = _verification_failure_path()
    if configured() or not failure.is_file():
        return ""
    try:
        payload = json.loads(failure.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Die letzte ChatGPT-Web-Pruefung ist fehlgeschlagen."
    return str(
        payload.get("message") or "Die letzte ChatGPT-Web-Pruefung ist fehlgeschlagen."
    )


def _record_verification_failure(message: str) -> None:
    failure = _verification_failure_path()
    if not failure.name:
        return
    failure.parent.mkdir(parents=True, exist_ok=True)
    temporary = failure.with_suffix(".json.new")
    temporary.write_text(
        json.dumps({"message": message}, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(failure)


def _research_status_path() -> Path:
    home = _path("DEBATEAI_CHATGPT_WEB_HOME")
    return home / "research-status.json" if home.name else Path()


def research_status() -> dict[str, object]:
    path = _research_status_path()
    default = {
        "provider": PROVIDER,
        "model": "gpt-6",
        "model_confirmed": False,
        "research_mode": None,
        "search_requested": False,
        "search_confirmed": False,
        "state": "idle",
    }
    if not path.is_file():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**default, "state": "invalid"}
    if not isinstance(payload, dict):
        return {**default, "state": "invalid"}
    allowed = {
        "provider",
        "model",
        "model_confirmed",
        "research_mode",
        "search_requested",
        "search_confirmed",
        "state",
        "requested_at",
        "completed_at",
        "error_class",
    }
    return {
        **default,
        **{key: value for key, value in payload.items() if key in allowed},
    }


def _write_research_status(
    *,
    state: str,
    research: str | None,
    requested_at: str,
    error_class: str | None = None,
) -> None:
    path = _research_status_path()
    if not path.name:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "provider": PROVIDER,
        "model": "gpt-6",
        "model_confirmed": model_confirmed(),
        "research_mode": research,
        "search_requested": research in {"search", "deep"},
        # Oracle was instructed to search, but this backend has no structured
        # proof that a browser search actually ran. Never claim confirmation.
        "search_confirmed": False,
        "state": state,
        "requested_at": requested_at,
    }
    if state != "started":
        payload["completed_at"] = datetime.now(UTC).isoformat()
    if error_class:
        payload["error_class"] = error_class
    temporary = path.with_suffix(".json.new")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _thinking_time(reasoning_effort: str | None) -> str:
    return (
        "extra-high" if (reasoning_effort or "").casefold() == "xhigh" else "extended"
    )


def research_mode(prompt: str, *, source: str = "") -> str | None:
    """Enable browser research only for an explicit research request."""
    normalized_source = source.casefold().replace("-", "_")
    if any(
        token in normalized_source for token in ("research", "recherche", "fact_check")
    ):
        return "search"
    lowered = prompt.casefold()
    explicit_markers = (
        "[web_research]",
        "[web-recherche]",
        "recherchiere im web",
        "suche im web",
        "fuehre eine web-recherche",
        "f\u00fchre eine web-recherche",
    )
    return "search" if any(marker in lowered for marker in explicit_markers) else None


def oracle_command(
    output_path: Path,
    *,
    reasoning_effort: str | None = "xhigh",
    research: str | None = None,
) -> list[str]:
    command = [
        str(_path("DEBATEAI_CHATGPT_WEB_NODE")),
        str(_path("DEBATEAI_CHATGPT_WEB_ORACLE")),
        "--engine",
        "browser",
        "--chatgpt-url",
        CHATGPT_TEMPORARY_URL,
        "--browser-manual-login",
        "--browser-manual-login-profile-dir",
        str(_path("DEBATEAI_CHATGPT_WEB_PROFILE")),
        "--model",
        "gpt-6",
        "--browser-model-strategy",
        "current",
        "--browser-thinking-time",
        _thinking_time(reasoning_effort),
        "--browser-no-focus",
        "--browser-archive",
        "auto",
        "--browser-profile-lock-timeout",
        "2m",
        "--browser-timeout",
        "10m",
    ]
    if research in {"search", "deep"}:
        command.extend(["--browser-research", research])
    command.extend(["--write-output", str(output_path), "--wait", "-p", "-"])
    return command


async def _terminate_child(process: asyncio.subprocess.Process) -> None:
    """Terminate an Oracle child and reap it after timeout/cancellation."""
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except TimeoutError:
        process.kill()
        await asyncio.wait_for(process.wait(), timeout=5)


async def _reap_before_release(process: asyncio.subprocess.Process) -> None:
    """Keep ownership through bounded cleanup, including repeated cancellation."""
    cleanup = asyncio.create_task(_terminate_child(process))
    cancelled = False
    while not cleanup.done():
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            cancelled = True
    cleanup.result()
    if cancelled:
        raise asyncio.CancelledError


def _record_refusal(source: str, research: str | None, error_class: str) -> None:
    category = (
        "research_claim"
        if research in {"search", "deep"}
        else external_audit.data_category_for_source(source)
    )
    external_audit.record_external_request(
        provider_route="chatgpt-web:gpt-6",
        approval=False,
        data_category=category,
        claim_id=external_audit.current_claim_id(),
        status="refused",
        model_id=MODEL_ID,
        error_class=error_class,
    )


def _require_ready(source: str, research_mode_value: str | None) -> None:
    if not runtime_available():
        _record_refusal(source, research_mode_value, "RuntimeUnavailable")
        raise RuntimeError("ChatGPT Web ist in dieser Installation nicht verfuegbar.")
    if not configured():
        _record_refusal(source, research_mode_value, "VerificationRequired")
        raise RuntimeError(
            "ChatGPT Web ist nicht mehr bestaetigt. Bitte erneut anmelden."
        )
    if _LOGIN_RESERVED:
        _record_refusal(source, research_mode_value, "LoginBusy")
        raise RuntimeError(
            "Die ChatGPT-Anmeldung laeuft gerade. Bitte danach erneut versuchen."
        )


async def generate(
    prompt: str,
    *,
    system: str | None = None,
    reasoning_effort: str | None = "xhigh",
    research: str | None = None,
    timeout_seconds: float = 660,
    source: str = "",
) -> str:
    research_mode_value = research if research in {"search", "deep"} else None
    deadline = asyncio.get_running_loop().time() + max(1.0, float(timeout_seconds))
    _require_ready(source, research_mode_value)

    # Oracle owns one dedicated Chrome profile. Keep its complete browser
    # lifecycle single-flight so one agent cannot close another agent's window.
    try:
        async with asyncio.timeout_at(deadline):
            await _ORACLE_LOCK.acquire()
    except TimeoutError:
        _record_refusal(source, research_mode_value, "TimeoutError")
        raise
    try:
        _require_ready(source, research_mode_value)
        home = _path("DEBATEAI_CHATGPT_WEB_HOME")
        home.mkdir(parents=True, exist_ok=True)
        jobs = home / "jobs"
        jobs.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(prefix="answer-", suffix=".md", dir=jobs)
        os.close(handle)
        output = Path(name)
        output.unlink(missing_ok=True)
        requested_at = datetime.now(UTC).isoformat()
        _write_research_status(
            state="started",
            research=research_mode_value,
            requested_at=requested_at,
        )
        command = oracle_command(
            output, reasoning_effort=reasoning_effort, research=research_mode_value
        )
        audit_category = (
            "research_claim"
            if research_mode_value
            else external_audit.data_category_for_source(source)
        )
        audit_id = external_audit.start_external_request(
            provider_route="chatgpt-web:gpt-6",
            approval=external_audit.current_approval(),
            data_category=audit_category,
            claim_id=external_audit.current_claim_id(),
            model_id=MODEL_ID,
        )
        env = os.environ.copy()
        env.update(
            {
                "ORACLE_HOME_DIR": str(home),
                "ORACLE_BROWSER_PROFILE_DIR": str(
                    _path("DEBATEAI_CHATGPT_WEB_PROFILE")
                ),
                "NO_COLOR": "1",
            }
        )
        flags = 0x08000000 if os.name == "nt" else 0
        content = f"{system.strip()}\n\n{prompt.strip()}" if system else prompt.strip()
        process = None
        try:
            try:
                async with asyncio.timeout_at(deadline):
                    process = await asyncio.create_subprocess_exec(
                        *command,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                        creationflags=flags,
                    )
                    stdout, stderr = await process.communicate(content.encode("utf-8"))
            except (TimeoutError, asyncio.CancelledError):
                if process is not None:
                    await _reap_before_release(process)
                raise
            if process.returncode:
                diagnostic = stderr or stdout
                detail = redact_text(diagnostic.decode("utf-8", "replace"))[
                    -1200:
                ].strip()
                if not detail:
                    detail = f"Oracle wurde mit Code {process.returncode} beendet."
                if "Unable to locate the ChatGPT model selector button" in detail:
                    _record_verification_failure(detail)
                raise RuntimeError(
                    f"ChatGPT Web konnte die Anfrage nicht ausfuehren: {detail}"
                )
            answer = output.read_text(encoding="utf-8").strip()
            if not answer:
                raise RuntimeError("ChatGPT Web hat keine Antwort geliefert.")
            _write_research_status(
                state="completed",
                research=research_mode_value,
                requested_at=requested_at,
            )
            external_audit.finish_external_request(
                audit_id,
                approval=external_audit.current_approval(),
                status="completed",
                provider_route="chatgpt-web:gpt-6",
                data_category=audit_category,
                claim_id=external_audit.current_claim_id(),
                model_id=MODEL_ID,
            )
            return answer
        except asyncio.CancelledError:
            _write_research_status(
                state="cancelled",
                research=research_mode_value,
                requested_at=requested_at,
                error_class="CancelledError",
            )
            external_audit.finish_external_request(
                audit_id,
                approval=external_audit.current_approval(),
                status="cancelled",
                provider_route="chatgpt-web:gpt-6",
                data_category=audit_category,
                claim_id=external_audit.current_claim_id(),
                model_id=MODEL_ID,
            )
            raise
        except Exception as exc:
            _write_research_status(
                state="failed",
                research=research_mode_value,
                requested_at=requested_at,
                error_class=type(exc).__name__,
            )
            external_audit.finish_external_request(
                audit_id,
                approval=external_audit.current_approval(),
                status="failed",
                provider_route="chatgpt-web:gpt-6",
                data_category=audit_category,
                claim_id=external_audit.current_claim_id(),
                model_id=MODEL_ID,
                error_class=type(exc).__name__,
            )
            raise
        finally:
            output.unlink(missing_ok=True)
    finally:
        _ORACLE_LOCK.release()
