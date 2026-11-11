"""Interactive first-time login and strict GPT-6 Extra High verification."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from debateai_identity import env_value


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".new")
    pending.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    pending.replace(path)


def _verified_oracle_selection(home: Path, started_at: float) -> dict[str, object] | None:
    candidates = [
        path for path in (home / "sessions").glob("*/meta.json")
        if path.stat().st_mtime >= started_at - 2
    ]
    for path in sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        browser = metadata.get("browser") if isinstance(metadata, dict) else None
        model = browser.get("modelSelection") if isinstance(browser, dict) else None
        thinking = browser.get("thinkingSelection") if isinstance(browser, dict) else None
        if not isinstance(model, dict) or not isinstance(thinking, dict):
            continue
        if not model.get("verified") or str(model.get("resolvedLabel", "")).strip() not in {"GPT-6", "Latest"}:
            continue
        if not thinking.get("verified") or thinking.get("requestedLevel") != "extra-high":
            continue
        return {"model": model, "thinking": thinking}
    return None


def run_chatgpt_web_login(result_path: Path) -> int:
    """Open Oracle's private Chrome profile and verify the requested UI model."""
    from app.services.chatgpt_web import oracle_command

    result_path = Path(result_path)
    marker = Path(env_value("DEBATEAI_CHATGPT_WEB_MARKER"))
    profile = Path(env_value("DEBATEAI_CHATGPT_WEB_PROFILE"))
    home = Path(env_value("DEBATEAI_CHATGPT_WEB_HOME"))
    home.mkdir(parents=True, exist_ok=True)
    output = home / "login-verification.md"
    output.unlink(missing_ok=True)
    command = oracle_command(output, reasoning_effort="xhigh")
    # A browser profile can exist before sign-in is complete (Chrome creates
    # Local State immediately). Keep the first verification window alive until
    # a verified marker exists; later rechecks stay one-shot.
    if not marker.is_file():
        insert_at = command.index("--browser-no-focus")
        command[insert_at:insert_at + 1] = ["--browser-keep-browser"]
    env = os.environ.copy()
    env.update({
        "ORACLE_HOME_DIR": str(home),
        "ORACLE_BROWSER_PROFILE_DIR": str(profile),
        "NO_COLOR": "1",
    })
    started = time.perf_counter()
    started_wall = time.time()
    try:
        completed = subprocess.run(
            command,
            input="Antworte nur mit: OK",
            text=True,
            capture_output=True,
            timeout=20 * 60,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        answer = output.read_text(encoding="utf-8").strip() if output.is_file() else ""
        selection = _verified_oracle_selection(home, started_wall)
        if completed.returncode or not answer or selection is None:
            # Test doubles and a few subprocess wrappers may omit stderr/stdout
            # or expose non-string placeholders.  Diagnostics must never turn
            # a provider failure into a secondary TypeError.
            stderr = completed.stderr if isinstance(completed.stderr, str) else ""
            stdout = completed.stdout if isinstance(completed.stdout, str) else ""
            diagnostic = (stderr or stdout).strip()
            if "No Chrome installations found" in diagnostic:
                message = "Kein kompatibler Chrome-/Edge-Browser wurde gefunden."
            elif completed.returncode:
                message = diagnostic[-600:] or f"Oracle wurde mit Code {completed.returncode} beendet."
            elif not answer:
                message = "ChatGPT Web hat nach der Anmeldung keine Antwort geliefert."
            else:
                message = "GPT-6 mit Extra High konnte in der ChatGPT-Oberflaeche nicht bestaetigt werden."
            _write_json(result_path, {
                "error": message,
                "exit_code": completed.returncode,
            })
            return 1
        model_selection = selection["model"]
        thinking_selection = selection["thinking"]
        evidence = {
            "provider": "ChatGPT Web via Oracle 0.22.2",
            "requested_model": "gpt-6",
            "actual_model": "gpt-6",
            "model_label": model_selection.get("resolvedLabel"),
            "thinking": "xhigh",
            "thinking_label": thinking_selection.get("resolvedLabel"),
            "verification": "Oracle UI-Auswahl fuer Modell und Extra High bestaetigt",
            "answer": answer[:200],
            "latency_ms": latency_ms,
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _write_json(marker, evidence)
        _write_json(result_path, evidence)
        return 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        _write_json(result_path, {"error": f"Die ChatGPT-Anmeldung konnte nicht abgeschlossen werden: {type(exc).__name__}"})
        return 1
    finally:
        output.unlink(missing_ok=True)
