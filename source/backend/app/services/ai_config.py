"""Small runtime loader for the user-editable Debate AI configuration."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from string import Formatter
from types import MappingProxyType
from typing import Any

from app.services.identity import env_value


_PROMPT_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,119}$")
_EFFORTS = {"low", "medium", "high", "xhigh"}
_CONFIG_LOCK = threading.RLock()
_MAX_PROMPT_CHARACTERS = 200_000
_REQUIRED_PLACEHOLDERS = {
    "debate_deep_v1": {"claim", "own_position", "relevant_context", "evidence"},
    "speaker_context_enhancement": {
        "meeting_context_text", "speakers_text", "insights_json", "transcript_text",
    },
}
# The application renders prompts with named values only.  Keeping this
# allowlist at the validation boundary prevents an editable prompt from
# introducing an unexpected field lookup (or a typo that silently renders as
# an empty/incorrect value) when it is later formatted by an agent.
_ALLOWED_PROMPT_PLACEHOLDERS = frozenset({
    "claim",
    "own_position",
    "relevant_context",
    "evidence",
    "meeting_context_text",
    "speakers_text",
    "insights_json",
    "transcript_text",
    "transcript_window",
    "directives_text",
    "document_summaries",
    "active_questions",
    "lens_sections",
    "item_type_values",
    "recent_objections",
    "knowledge_context",
    "opportunities_json",
    "insights_text",
    "discovery_lens_json",
    "meeting_lens_json",
    "mode",
})
_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class AIConfigSnapshot:
    generation: int
    providers: MappingProxyType
    prompts: MappingProxyType
    playbooks: tuple[MappingProxyType, ...]


_ACTIVE_SNAPSHOT: ContextVar[AIConfigSnapshot | None] = ContextVar(
    "active_ai_configuration_snapshot", default=None
)
_LAST_VALID_PROVIDERS: dict[str, Any] | None = None
_LAST_VALID_SNAPSHOT: AIConfigSnapshot | None = None


def _bundled_ai_directory() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root) / "ai"
    return Path(__file__).resolve().parents[3] / "ai"


def _frozen_executable_directory() -> Path | None:
    """Return the directory of the actually started frozen executable.

    ``sys._MEIPASS`` is deliberately not used here: in a one-dir bundle it is
    the read-only/internal resource root, while editable configuration must
    live beside the executable or in the user data directory.
    """
    if not getattr(sys, "frozen", False):
        return None
    executable = str(getattr(sys, "executable", "") or "").strip()
    if not executable:
        return None
    try:
        return Path(executable).resolve().parent
    except OSError:
        return Path(executable).absolute().parent


def _contains_symlink(path: Path) -> bool:
    """Reject an explicit config path that traverses an existing symlink."""
    current = path
    while current != current.parent:
        if current.exists() and current.is_symlink():
            return True
        current = current.parent
    return False


def _explicit_external_directory() -> Path | None:
    raw = (
        os.environ.get("DEBATE_AI_CONFIG_DIR", "").strip()
        or env_value("DEBATEAI_PROMPT_DIR").strip()
    )
    if not raw:
        return None
    try:
        candidate = Path(raw).expanduser()
        if _contains_symlink(candidate):
            return None
        resolved = candidate.resolve()
        bundled_root = getattr(sys, "_MEIPASS", None)
        if bundled_root:
            bundle = Path(bundled_root).resolve()
            if resolved == bundle or bundle in resolved.parents:
                return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


@lru_cache(maxsize=4)
def _packaged_ai_directory(data_root: str, bundled_root: str) -> Path:
    """Merge immutable bundled defaults once for one packaged process."""
    target = Path(data_root).parent / "ai"
    target.mkdir(parents=True, exist_ok=True)
    _merge_bundled_defaults(Path(bundled_root), target)
    return target


def ai_directory() -> Path:
    explicit = _explicit_external_directory()
    if explicit is not None:
        return explicit
    if getattr(sys, "_MEIPASS", None):
        data_dir = Path(
            os.environ.get("DATA_DIR", Path.home() / ".debate-ai" / "data")
        )
        # Portable mode is explicit.  The executable directory is resolved
        # from sys.executable, never from the current working directory or the
        # temporary PyInstaller resource root.
        if env_value("DEBATEAI_PORTABLE").casefold() in _TRUTHY:
            executable_dir = _frozen_executable_directory()
            if executable_dir is not None:
                data_dir = executable_dir / "data"
        return _packaged_ai_directory(
            str(data_dir.resolve()),
            str(_bundled_ai_directory().resolve()),
        )
    return _bundled_ai_directory()


def _merge_bundled_defaults(source_root: Path, target_root: Path) -> None:
    """Three-way update bundled defaults without replacing user edits."""
    baseline_root = target_root / ".bundled-baseline"
    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        destination = target_root / relative
        baseline = baseline_root / relative
        try:
            incoming = source.read_bytes()
            current = destination.read_bytes() if destination.is_file() else None
            previous = baseline.read_bytes() if baseline.is_file() else None
            if current is None or (previous is not None and current == previous):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(incoming)
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_bytes(incoming)
        except OSError:
            continue


@lru_cache(maxsize=16)
def _read_json(path: str, modified_ns: int) -> Any:
    del modified_ns
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_ai_json(name: str, fallback: Any) -> Any:
    path = ai_directory() / name
    try:
        return _read_json(str(path), path.stat().st_mtime_ns)
    except (OSError, ValueError, TypeError):
        return fallback


def load_ai_text(name: str, fallback: str) -> str:
    path = ai_directory() / name
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback
    return value or fallback


def _atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
        os.replace(temporary, path)
        _read_json.cache_clear()
    finally:
        temporary.unlink(missing_ok=True)


def _snapshot(path: Path, history_directory: Path) -> None:
    if not path.is_file():
        return
    content = path.read_bytes()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    version = f"{stamp}-{sha256(content).hexdigest()[:12]}"
    destination = history_directory / f"{version}{path.suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        _atomic_write(destination, content.decode("utf-8"))


def _validate_provider_configuration(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Die Anbieter-Konfiguration muss ein JSON-Objekt sein.")
    routes = data.get("routes")
    if routes is not None:
        if not isinstance(routes, list) or not routes:
            raise ValueError("Mindestens eine Anbieterroute ist erforderlich.")
        seen: set[str] = set()
        for position, route in enumerate(routes, 1):
            if not isinstance(route, dict):
                raise ValueError(f"Anbieterroute {position} ist ungueltig.")
            route_id = str(route.get("id") or "").strip()
            model_id = str(route.get("model_id") or "").strip()
            if not route_id or route_id in seen:
                raise ValueError("Jede Anbieterroute braucht eine eindeutige ID.")
            if not model_id:
                raise ValueError(f"Anbieterroute '{route_id}' braucht ein Modell.")
            if not isinstance(route.get("enabled", True), bool):
                raise ValueError(f"Anbieterroute '{route_id}' hat keinen gueltigen Aktivstatus.")
            effort = route.get("reasoning_effort")
            if effort is not None and effort not in _EFFORTS:
                raise ValueError(f"Anbieterroute '{route_id}' hat eine ungueltige Denkstufe.")
            for field in ("timeout_seconds", "cooldown_seconds"):
                if field in route:
                    try:
                        value = int(route[field])
                    except (TypeError, ValueError) as exc:
                        raise ValueError(f"'{field}' von '{route_id}' muss eine Zahl sein.") from exc
                    if value < 1 or value > 86400:
                        raise ValueError(f"'{field}' von '{route_id}' liegt ausserhalb 1-86400.")
            seen.add(route_id)
    return data


def _read_provider_configuration() -> dict[str, Any]:
    path = ai_directory() / "providers.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError, TypeError) as exc:
        # Do not silently turn a damaged user configuration into an empty
        # provider list.  The API can expose this as a safe, non-secret error;
        # callers with an already validated in-process snapshot still retain
        # that last-known-good value through provider_configuration().
        raise ValueError("Die Anbieter-Konfiguration ist ungueltiges JSON.") from exc
    if not data:
        return {}
    validated = _validate_provider_configuration(data)
    if not isinstance(validated.get("routes"), list):
        order = validated.get("deep_analysis_order")
        effort_map = validated.get("reasoning_effort")
        if isinstance(order, list):
            validated = {
                **validated,
                "schema_version": 2,
                "routes": [
                    {
                        "id": f"legacy_{index + 1}",
                        "label": str(model_id),
                        "provider": "legacy",
                        "model_id": str(model_id),
                        "enabled": True,
                        "reasoning_effort": (
                            effort_map.get(model_id, "high")
                            if isinstance(effort_map, dict)
                            else "high"
                        ),
                        "timeout_seconds": 180,
                        "cooldown_seconds": int(validated.get("unavailable_cooldown_seconds", 900)),
                    }
                    for index, model_id in enumerate(order)
                    if str(model_id).strip()
                ],
            }
    return validated


def provider_configuration() -> dict[str, Any]:
    global _LAST_VALID_PROVIDERS
    active = _ACTIVE_SNAPSHOT.get()
    if active is not None:
        return json.loads(json.dumps(dict(active.providers)))
    with _CONFIG_LOCK:
        try:
            value = _read_provider_configuration()
        except ValueError:
            if _LAST_VALID_PROVIDERS is not None:
                return json.loads(json.dumps(_LAST_VALID_PROVIDERS))
            raise
        _LAST_VALID_PROVIDERS = json.loads(json.dumps(value))
        return value


def save_provider_configuration(data: Any) -> dict[str, Any]:
    validated = _validate_provider_configuration(data)
    path = ai_directory() / "providers.json"
    with _CONFIG_LOCK:
        _snapshot(path, ai_directory() / "history" / "providers")
        _atomic_write(path, json.dumps(validated, ensure_ascii=False, indent=2) + "\n")
    return provider_configuration()


def ensure_gemini_cli_route(wire_model: str = "gemini-3.1-pro-preview") -> dict[str, Any]:
    """Add the explicit Gemini CLI Pro/High route without replacing user config.

    Packaged installs copy ``providers.json`` only once.  A user who upgrades
    and then deliberately completes Google OAuth must therefore receive the
    new route through a narrow migration rather than a reset to new defaults.
    Existing labels, ordering, enabled state, timeouts, and all other routes
    are preserved.
    """
    data = provider_configuration()
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, list):
        return data
    wire_model = str(wire_model or "").strip() or "gemini-3.1-pro-preview"
    model_id = f"endpoint:subscription-ai:{wire_model}"
    route_label = (
        "Gemini CLI OAuth (3.1 Pro High)"
        if wire_model == "gemini-3.1-pro-preview"
        else f"Gemini CLI OAuth ({wire_model}, High)"
    )
    next_routes = [dict(route) if isinstance(route, dict) else route for route in routes]
    for route in next_routes:
        if not isinstance(route, dict):
            continue
        if route.get("id") == "gemini_cli" or route.get("model_id") == model_id:
            if (
                route.get("model_id") == model_id
                and route.get("reasoning_effort") == "high"
                and route.get("label") == route_label
            ):
                return data
            route["model_id"] = model_id
            route["reasoning_effort"] = "high"
            route["label"] = route_label
            return save_provider_configuration({**data, "routes": next_routes})
    route = {
        "id": "gemini_cli",
        "label": route_label,
        "provider": "google-login",
        "model_id": model_id,
        "enabled": True,
        "reasoning_effort": "high",
        "timeout_seconds": 180,
        "cooldown_seconds": 900,
        "lazy_start": False,
    }
    insert_at = next(
        (
            index + 1
            for index, existing in enumerate(next_routes)
            if isinstance(existing, dict) and existing.get("id") == "cliproxyapi"
        ),
        len(next_routes),
    )
    next_routes.insert(insert_at, route)
    return save_provider_configuration({**data, "routes": next_routes})


def reset_provider_configuration() -> dict[str, Any]:
    directory = ai_directory()
    default_path = directory / "providers.default.json"
    try:
        defaults = json.loads(default_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("Der Auslieferungsstandard fuer KI-Anbieter fehlt oder ist ungueltig.") from exc
    return save_provider_configuration(defaults)


def _prompt_path(name: str) -> Path:
    if not _PROMPT_NAME.fullmatch(name):
        raise ValueError("Ungueltiger Promptname.")
    return ai_directory() / f"{name}.txt"


def _validate_prompt_content(name: str, content: str) -> str:
    value = str(content).strip()
    if not value:
        raise ValueError("Ein aktiver Prompt darf nicht leer sein.")
    if len(value) > _MAX_PROMPT_CHARACTERS:
        raise ValueError("Der Prompt ist zu gross.")
    try:
        placeholders = {
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _literal, field_name, _format, _conversion in Formatter().parse(value)
            if field_name
        }
    except ValueError as exc:
        raise ValueError("Der Prompt enthaelt ungueltige Template-Klammern.") from exc
    unknown = placeholders - _ALLOWED_PROMPT_PLACEHOLDERS
    if unknown:
        raise ValueError(
            "Unbekannte Promptplatzhalter: "
            + ", ".join(f"{{{item}}}" for item in sorted(unknown))
        )
    missing = _REQUIRED_PLACEHOLDERS.get(name, set()) - placeholders
    if missing:
        raise ValueError(
            "Pflichtplatzhalter fehlen: "
            + ", ".join(f"{{{item}}}" for item in sorted(missing))
        )
    return value


def active_prompt(name: str, fallback: str = "") -> str:
    active = _ACTIVE_SNAPSHOT.get()
    if active is not None:
        return str(active.prompts.get(name, fallback))
    try:
        value = _prompt_path(name).read_text(encoding="utf-8").strip()
    except OSError:
        return fallback
    if not value:
        return fallback
    try:
        return _validate_prompt_content(name, value)
    except ValueError:
        # A malformed user file is never executed and is never overwritten by
        # startup seeding.  The caller receives its explicit safe fallback.
        return fallback


def save_prompt(name: str, content: str) -> dict[str, Any]:
    path = _prompt_path(name)
    value = _validate_prompt_content(name, content)
    try:
        current = path.read_text(encoding="utf-8").strip()
    except OSError:
        current = ""
    with _CONFIG_LOCK:
        if current and current != value:
            _snapshot(path, ai_directory() / "history" / "prompts" / name)
        _atomic_write(path, value + "\n")
    return {
        "name": name,
        "content": value,
        "version": sha256(value.encode("utf-8")).hexdigest()[:12],
        "path": str(path),
    }


def list_prompt_versions(name: str) -> list[dict[str, str]]:
    _prompt_path(name)
    history = ai_directory() / "history" / "prompts" / name
    if not history.is_dir():
        return []
    result = []
    for path in sorted(history.glob("*.*"), reverse=True):
        result.append({"version": path.stem, "path": str(path)})
    return result


def restore_prompt_version(name: str, version: str) -> dict[str, Any]:
    _prompt_path(name)
    if not re.fullmatch(r"[0-9TZ.]+-[a-f0-9]{12}", version):
        raise ValueError("Ungueltige Promptversion.")
    source = ai_directory() / "history" / "prompts" / name / f"{version}.txt"
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError("Die angeforderte Promptversion wurde nicht gefunden.") from exc
    return save_prompt(name, content)


def _validate_playbooks(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not data:
        raise ValueError("RhetoricIQ braucht mindestens eine Strategie.")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Jede RhetoricIQ-Strategie muss ein Objekt sein.")
        terms = item.get("terms")
        if not isinstance(terms, list) or not all(
            isinstance(term, str) and term.strip() for term in terms
        ):
            raise ValueError("Jede Strategie braucht gueltige Ausloeser.")
        if not isinstance(item.get("directive"), str) or not item["directive"].strip():
            raise ValueError("Jede Strategie braucht eine Anweisung.")
    return data


def save_playbooks(data: Any) -> list[dict[str, Any]]:
    validated = _validate_playbooks(data)
    path = ai_directory() / "playbooks.json"
    _snapshot(path, ai_directory() / "history" / "prompts" / "rhetoriciq.playbooks")
    _atomic_write(path, json.dumps(validated, ensure_ascii=False, indent=2) + "\n")
    return validated


def restore_playbooks_version(version: str) -> list[dict[str, Any]]:
    if not re.fullmatch(r"[0-9TZ.]+-[a-f0-9]{12}", version):
        raise ValueError("Ungueltige Strategieversion.")
    source = ai_directory() / "history" / "prompts" / "rhetoriciq.playbooks" / f"{version}.json"
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Die Strategieversion wurde nicht gefunden.") from exc
    return save_playbooks(data)


def deep_analysis_models(default: list[str]) -> list[str]:
    data = load_ai_json("providers.json", {})
    routes = data.get("routes") if isinstance(data, dict) else None
    if isinstance(routes, list):
        result = [
            str(route.get("model_id") or "").strip()
            for route in routes
            if isinstance(route, dict)
            and route.get("enabled", True) is True
            and str(route.get("model_id") or "").strip()
        ]
        forced = str(data.get("forced_model") or "").strip()
        if forced and forced in result:
            result.remove(forced)
            result.insert(0, forced)
        if data.get("fallback_enabled", True) is False:
            result = result[:1]
        return result
    values = data.get("deep_analysis_order") if isinstance(data, dict) else None
    if not isinstance(values, list):
        return default
    result = [str(value).strip() for value in values if str(value).strip()]
    return result or default


def reasoning_effort(model_id: str, default: str = "low") -> str:
    data = load_ai_json("providers.json", {})
    routes = data.get("routes") if isinstance(data, dict) else None
    if isinstance(routes, list):
        for route in routes:
            if not isinstance(route, dict) or route.get("model_id") != model_id:
                continue
            value = route.get("reasoning_effort")
            return value if value in _EFFORTS else default
    mapping = data.get("reasoning_effort") if isinstance(data, dict) else None
    value = mapping.get(model_id) if isinstance(mapping, dict) else None
    return value if value in {"low", "medium", "high", "xhigh"} else default


def provider_route(model_id: str) -> dict[str, Any]:
    """Return a detached route description for capability decisions."""
    routes = provider_configuration().get("routes")
    if not isinstance(routes, list):
        return {"id": "unknown", "provider": "unknown", "model_id": model_id}
    for route in routes:
        if isinstance(route, dict) and route.get("model_id") == model_id:
            return dict(route)
    return {"id": "unknown", "provider": "unknown", "model_id": model_id}


def _route_number(model_id: str, field: str, default: int, minimum: int, maximum: int) -> int:
    data = load_ai_json("providers.json", {})
    routes = data.get("routes") if isinstance(data, dict) else None
    if isinstance(routes, list):
        for route in routes:
            if isinstance(route, dict) and route.get("model_id") == model_id:
                try:
                    return max(minimum, min(maximum, int(route.get(field, default))))
                except (TypeError, ValueError):
                    return default
    return default


def model_timeout_seconds(model_id: str) -> int:
    return _route_number(model_id, "timeout_seconds", 180, 1, 86400)


def model_cooldown_seconds(model_id: str) -> int:
    return _route_number(
        model_id,
        "cooldown_seconds",
        unavailable_cooldown_seconds(),
        1,
        86400,
    )


def unavailable_cooldown_seconds() -> int:
    data = load_ai_json("providers.json", {})
    value = data.get("unavailable_cooldown_seconds", 900) if isinstance(data, dict) else 900
    try:
        return max(60, min(86400, int(value)))
    except (TypeError, ValueError):
        return 900


def max_parallel_analyses() -> int:
    data = load_ai_json("providers.json", {})
    value = data.get("max_parallel_analyses", 1) if isinstance(data, dict) else 1
    try:
        return max(1, min(8, int(value)))
    except (TypeError, ValueError):
        return 1


def analysis_deadline_seconds() -> int:
    """Long budget for deep analysis, retries, and provider fallbacks."""
    data = load_ai_json("providers.json", {})
    value = data.get("analysis_deadline_seconds", 180) if isinstance(data, dict) else 180
    try:
        return max(5, min(900, int(value)))
    except (TypeError, ValueError):
        return 180


def live_research_deadline_seconds() -> int:
    """Short budget for automatic live research before deep analysis."""
    data = load_ai_json("providers.json", {})
    value = data.get("live_research_deadline_seconds", 12) if isinstance(data, dict) else 12
    try:
        return max(8, min(15, int(value)))
    except (TypeError, ValueError):
        return 12


def configuration_generation() -> int:
    """Content-derived generation for all active, user-editable AI inputs."""
    directory = ai_directory()
    digest = sha256()
    paths = {directory / "providers.json", directory / "playbooks.json"}
    paths.update(directory.glob("*.txt"))
    for path in sorted(paths, key=lambda item: item.name):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return int.from_bytes(digest.digest()[:8], "big")


def create_configuration_snapshot() -> AIConfigSnapshot:
    """Read one validated immutable generation for a complete model job."""
    global _LAST_VALID_SNAPSHOT
    with _CONFIG_LOCK:
        try:
            directory = ai_directory()
            providers = _read_provider_configuration()
            prompts: dict[str, str] = {}
            for path in sorted(directory.glob("*.txt")):
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                prompts[path.stem] = _validate_prompt_content(path.stem, content)
            raw_playbooks = load_ai_json("playbooks.json", [])
            playbooks = _validate_playbooks(raw_playbooks) if raw_playbooks else []
            snapshot = AIConfigSnapshot(
                generation=configuration_generation(),
                providers=MappingProxyType(json.loads(json.dumps(providers))),
                prompts=MappingProxyType(dict(prompts)),
                playbooks=tuple(
                    MappingProxyType(json.loads(json.dumps(item))) for item in playbooks
                ),
            )
        except (OSError, TypeError, ValueError):
            if _LAST_VALID_SNAPSHOT is not None:
                return _LAST_VALID_SNAPSHOT
            raise
        _LAST_VALID_SNAPSHOT = snapshot
        return snapshot


@contextmanager
def use_configuration_snapshot(snapshot: AIConfigSnapshot):
    token = _ACTIVE_SNAPSHOT.set(snapshot)
    try:
        yield snapshot
    finally:
        _ACTIVE_SNAPSHOT.reset(token)


def adaptive_reasoning_settings() -> dict[str, Any]:
    data = load_ai_json("providers.json", {})
    raw = data.get("adaptive_reasoning") if isinstance(data, dict) else None
    raw = raw if isinstance(raw, dict) else {}

    def bounded(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            return max(minimum, min(maximum, int(raw.get(name, default))))
        except (TypeError, ValueError):
            return default

    def effort(name: str, default: str) -> str:
        value = str(raw.get(name, default)).casefold()
        return value if value in {"high", "xhigh"} else default

    def bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
        try:
            return max(minimum, min(maximum, float(raw.get(name, default))))
        except (TypeError, ValueError):
            return default

    return {
        "enabled": raw.get("enabled", True) is not False,
        "new_topic_effort": effort("new_topic_effort", "xhigh"),
        "follow_up_effort": effort("follow_up_effort", "high"),
        "deep_reanalysis_effort": effort("deep_reanalysis_effort", "xhigh"),
        "latency_threshold_ms": bounded("latency_threshold_ms", 45000, 1000, 600000),
        "queue_threshold": bounded("queue_threshold", 1, 1, 20),
        "stable_calls_to_restore": bounded("stable_calls_to_restore", 2, 1, 20),
        "reuse_topic_analysis": raw.get("reuse_topic_analysis", True) is not False,
        "topic_similarity_threshold": bounded_float(
            "topic_similarity_threshold", 0.46, 0.1, 0.95
        ),
    }


def research_settings() -> dict[str, Any]:
    data = load_ai_json("providers.json", {})
    raw = data.get("research") if isinstance(data, dict) else None
    raw = raw if isinstance(raw, dict) else {}
    providers = raw.get("providers")
    enabled = []
    if isinstance(providers, list):
        enabled = [
            str(item.get("id") or "").strip()
            for item in providers
            if isinstance(item, dict)
            and item.get("enabled", True) is True
            and str(item.get("id") or "").strip()
        ]
    def bounded(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            return max(minimum, min(maximum, int(raw.get(name, default))))
        except (TypeError, ValueError):
            return default
    # Legacy search endpoints are retired globally. Research must use the
    # configured AI web/API providers so the visible answer can integrate the
    # findings without exposing provider-by-provider output.
    legacy_disabled = {"duckduckgo", "wikipedia"}
    enabled = [provider for provider in enabled if provider not in legacy_disabled]
    configured_fallback = raw.get("fallback_providers")
    fallback = (
        [
            str(provider)
            for provider in configured_fallback
            if str(provider) not in legacy_disabled
        ]
        if isinstance(configured_fallback, list)
        else ["gemini_web", "gemini_api", "cliproxyapi"]
    )
    return {
        "enabled": raw.get("enabled", True) is not False,
        "providers": enabled if isinstance(providers, list) else ["chatgpt_web", "gemini_web"],
        "steps": bounded("steps", 2, 1, 5),
        "timeout_seconds": bounded("timeout_seconds", 20, 3, 120),
        "original_sources_required": raw.get("original_sources_required", True) is not False,
        "legacy_providers_disabled": sorted(legacy_disabled),
        "primary_provider": str(raw.get("primary_provider") or "chatgpt_web"),
        "fallback_providers": fallback,
        "experimental_external_parallelism": bounded(
            "experimental_external_parallelism", 3, 1, 4
        ),
    }


def playbook_controls() -> list[tuple[tuple[str, ...], str]]:
    data = load_ai_json("playbooks.json", [])
    result: list[tuple[tuple[str, ...], str]] = []
    if not isinstance(data, list):
        return result
    for item in data:
        if not isinstance(item, dict):
            continue
        terms = tuple(str(term).casefold().strip() for term in item.get("terms", []) if str(term).strip())
        directive = str(item.get("directive") or "").strip()
        if terms and directive:
            result.append((terms, directive))
    return result