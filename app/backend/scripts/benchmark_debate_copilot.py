"""Measure the production German debate event path without fake latency.

The benchmark feeds deterministic final transcript turns through the real
AgentOrchestrator, ObjectionHandlerAgent, structured LLM router, inference
scheduler, revision cancellation, and debate_update WebSocket publisher. It
records the emitted application event rather than a raw provider token.
Research is disabled, so source refinement remains explicitly null.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import sys
import time
import uuid
from collections import deque
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_TURNS = (
    {
        "speaker": "Gegenseite",
        "text": "Erneuerbare Energien sind unzuverlaessig, weil nachts keine Sonne scheint.",
    },
    {
        "speaker": "Moderatorin",
        "text": "Wie soll das Stromnetz dann im Winter stabil bleiben?",
    },
    {
        "speaker": "Gegenseite",
        "text": "Speicher machen den Strom fuer Haushalte zwangslaeufig unbezahlbar.",
    },
    {
        "speaker": "Gegenseite",
        "text": "Deutschland kann mit seinem Anteil ohnehin nichts am Weltklima aendern.",
    },
    {
        "speaker": "Moderatorin",
        "text": "Nennen Sie jetzt bitte Ihr staerkstes Gegenargument in einem Satz.",
    },
)

SYSTEM_PROMPT = """Du bist ein deutscher Live-Debattenassistent. Antworte sofort, kurz und aussprechbar.
Gib ausschliesslich ein einzelnes JSON-Objekt ohne Markdown aus. Pflichtfelder:
answer_now, counterargument, counter_question, analogy. Jeder Wert hat hoechstens zwei Saetze.
Erfinde keine Quellen und behaupte keine Webrecherche. /no_think"""


async def benchmark_protect_and_guard(
    prompt: str,
    *,
    system: str | None = None,
    **_kwargs,
) -> tuple[str, str | None]:
    """Avoid database-backed PII settings in this loopback-only harness.

    ``run_benchmark`` rejects accidental non-loopback use in its report and
    never reads production session data. Hitting the application database here
    made a standalone timing run measure DNS/database retries instead of model
    latency.
    """
    return prompt, system


def endpoint_scope(endpoint: str) -> str:
    """Admit only explicit local HTTP endpoints; malformed URLs fail closed.

    Locality does not prove that a third-party local proxy stays on-device.
    The benchmark must be pointed at a trusted native model server, not a
    subscription bridge. It never imports account credentials from profiles.
    """
    if not isinstance(endpoint, str) or any(ord(c) < 33 for c in endpoint):
        return "network"
    try:
        parsed = urlparse(endpoint)
        port = parsed.port  # validate malformed/out-of-range ports as well
        valid = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and (port is None or port > 0)
        )
        return "loopback" if valid else "network"
    except (TypeError, ValueError):
        return "network"


async def verify_native_local_model(endpoint: str, model: str, *, client=None) -> None:
    """Reject missing weights and hosted aliases even behind a loopback URL.

    This is a native Ollama calibration contract, not proof against a malicious
    proxy. It requests metadata only and never installs or downloads a model.
    """
    if endpoint_scope(endpoint) != "loopback":
        raise ValueError("Benchmark requires a loopback endpoint")
    if client is None:
        async with httpx.AsyncClient(
            timeout=10, trust_env=False, follow_redirects=False
        ) as owned:
            return await verify_native_local_model(endpoint, model, client=owned)
    base = endpoint.rstrip("/")
    base = base.removesuffix("/v1")
    async with client.stream("GET", f"{base}/api/tags") as response:
        if response.status_code != 200:
            raise ValueError("Native local model catalog unavailable")
        chunks = bytearray()
        async for chunk in response.aiter_bytes():
            if len(chunks) + len(chunk) > 256 * 1024:
                raise ValueError("Native model catalog exceeds limit")
            chunks.extend(chunk)
    payload = json.loads(chunks)
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise ValueError("Native local model catalog is invalid")
    names = {model, model + ":latest"}
    selected = next(
        (m for m in models if isinstance(m, dict) and m.get("name") in names), None
    )
    if selected is None:
        raise ValueError(
            "Selected native model is not installed; no download was started"
        )
    if (
        selected.get("remote_host")
        or selected.get("remote_model")
        or model.endswith(("-cloud", ":cloud"))
    ):
        raise ValueError(
            "A remote/cloud model alias is not allowed in a local benchmark"
        )


class StreamingClient(Protocol):
    async def stream(self, turns: list[dict[str, str]]) -> AsyncIterator[str]: ...


def elapsed_ms(start: float, end: float) -> float:
    if end < start:
        raise ValueError("monotonic clock moved backwards")
    return round((end - start) * 1000.0, 3)


def load_turns(path: str | Path | None) -> list[dict[str, str]]:
    if path is None:
        return [dict(turn) for turn in DEFAULT_TURNS]
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("fixture must be a non-empty JSON array")
    turns: list[dict[str, str]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"fixture turn {index} must be an object")
        speaker = str(item.get("speaker") or "").strip()
        text = str(item.get("text") or "").strip()
        if not speaker or not text:
            raise ValueError(f"fixture turn {index} needs speaker and text")
        turns.append({"speaker": speaker, "text": text})
    return turns


def _extract_object(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise ValueError("model returned no JSON object")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(value, dict):
        raise ValueError("model response is not a JSON object")
    required = ("answer_now", "counterargument", "counter_question", "analogy")
    missing = [key for key in required if not str(value.get(key) or "").strip()]
    if missing:
        raise ValueError(f"model response is missing: {', '.join(missing)}")
    return value


async def measure_turn(
    client: StreamingClient,
    turns: list[dict[str, str]],
    *,
    turn_index: int,
    clock: Callable[[], float] = time.perf_counter,
) -> dict:
    started = clock()
    first_at: float | None = None
    chunks: list[str] = []
    record = {
        "turn_index": turn_index,
        "speaker": turns[-1]["speaker"],
        "text": turns[-1]["text"],
        "status": "failed",
        "first_update_ms": None,
        "current_update_ms": None,
        "source_refinement_ms": None,
        "research_status": "disabled",
        "recommendation": None,
        "error_type": None,
        "error": None,
    }
    try:
        async for chunk in client.stream(turns):
            if not chunk:
                continue
            if first_at is None:
                first_at = clock()
            chunks.append(chunk)
        finished = clock()
        if first_at is None:
            raise ValueError("endpoint completed without a visible update")
        record["first_update_ms"] = elapsed_ms(started, first_at)
        record["current_update_ms"] = elapsed_ms(started, finished)
        record["recommendation"] = _extract_object("".join(chunks))
        record["status"] = "ok"
    except asyncio.CancelledError:
        record["status"] = "cancelled"
        raise
    except Exception as exc:  # benchmark output must retain honest failures
        record["error_type"] = type(exc).__name__
        record["error"] = str(exc)[:500]
    return record


async def run_supersession_probe(
    client: StreamingClient,
    turns: list[dict[str, str]],
    *,
    delay_seconds: float,
) -> dict:
    history: list[dict[str, str]] = []
    pending: asyncio.Task | None = None
    cancellation_count = 0
    completed_count = 0
    statuses: list[str] = []
    records: list[dict] = []

    for index, turn in enumerate(turns):
        if pending is not None:
            if not pending.done():
                pending.cancel()
                cancellation_count += 1
            try:
                result = await pending
                completed_count += 1
                statuses.append(result["status"])
                records.append(result)
            except asyncio.CancelledError:
                statuses.append("cancelled")
                records.append({"turn_index": index - 1, "status": "cancelled"})
        history.append(dict(turn))
        pending = asyncio.create_task(
            measure_turn(client, list(history), turn_index=index)
        )
        if index < len(turns) - 1:
            await asyncio.sleep(delay_seconds)

    if pending is not None:
        try:
            result = await pending
            completed_count += 1
            statuses.append(result["status"])
            records.append(result)
        except asyncio.CancelledError:
            statuses.append("cancelled")
            records.append({"turn_index": len(turns) - 1, "status": "cancelled"})
    return {
        "delay_ms": round(delay_seconds * 1000.0, 3),
        "cancellation_count": cancellation_count,
        "completed_count": completed_count,
        "statuses": statuses,
        "failure_count": sum(record.get("status") == "failed" for record in records),
        "records": records,
    }


def _percentile_nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 3)


def evaluate_recommendation_contract(payload: dict) -> dict:
    """Run deterministic preflight checks without pretending to judge rhetoric.

    The checks cover the parts that can be measured reproducibly in a local
    benchmark: schema normalization, a speakable primary move, bounded spoken
    fields, a bound target claim, and evidence guards for numeric/attributed
    assertions.  Human review stays explicitly required because this is not a
    semantic or stylistic quality verdict.
    """
    from app.services.agents.objection_handler import (
        DebateRecommendation,
        _has_speakable_guidance,
    )
    from app.services.agents.orchestrator import (
        _contains_unsupported_evidence_claim,
        _contains_unsupported_numeric_assertion,
    )

    checks = {
        "schema_valid": False,
        "speakable_primary": False,
        "answer_word_limit": False,
        "question_word_limit": False,
        "target_claim_present": False,
        "evidence_guard": False,
    }
    try:
        recommendation = DebateRecommendation.model_validate(payload)
    except Exception as exc:
        return {
            "status": "fail",
            "score": 0.0,
            "checks": checks,
            "human_review_required": True,
            "error": f"{type(exc).__name__}: {str(exc)[:240]}",
        }

    checks["schema_valid"] = True
    checks["speakable_primary"] = _has_speakable_guidance(recommendation)
    checks["answer_word_limit"] = len(recommendation.answer_now.split()) <= 25
    checks["question_word_limit"] = len(recommendation.counter_question.split()) <= 14
    checks["target_claim_present"] = bool(recommendation.target_claim.strip())
    checks["evidence_guard"] = not (
        _contains_unsupported_numeric_assertion(recommendation)
        or _contains_unsupported_evidence_claim(recommendation)
    )
    passed = sum(checks.values())
    return {
        "status": "pass" if passed == len(checks) else "fail",
        "score": round(passed / len(checks), 3),
        "checks": checks,
        "human_review_required": True,
        "note": "technical contract preflight only; not a human rhetorical acceptance",
    }


def summarize(
    records: list[dict],
    *,
    cancellation_count: int,
    probe_failure_count: int = 0,
    stale_publishes: int = 0,
) -> dict:
    ok = [record for record in records if record.get("status") == "ok"]
    first = [float(record["first_update_ms"]) for record in ok]
    current = [float(record["current_update_ms"]) for record in ok]
    deep = [
        float(record["deep_revision_ms"])
        for record in ok
        if record.get("deep_revision_ms") is not None
    ]
    accepted = [
        float(record["accepted_model_ms"])
        for record in ok
        if record.get("accepted_model_ms") is not None
        and record.get("ui_acknowledged") is True
    ]
    quality = [
        record["quality_preflight"]
        for record in records
        if isinstance(record.get("quality_preflight"), dict)
    ]
    return {
        "turn_count": len(records),
        "success_count": len(ok),
        "turn_failure_count": sum(
            record.get("status") == "failed" for record in records
        ),
        "probe_failure_count": probe_failure_count,
        "failure_count": (
            sum(record.get("status") == "failed" for record in records)
            + probe_failure_count
        ),
        "cancellation_count": cancellation_count,
        "stale_publishes": stale_publishes,
        "median_first_update_ms": round(statistics.median(first), 3) if first else None,
        "p95_first_update_ms": _percentile_nearest_rank(first, 0.95),
        "median_current_update_ms": round(statistics.median(current), 3)
        if current
        else None,
        "p95_current_update_ms": _percentile_nearest_rank(current, 0.95),
        "median_deep_revision_ms": round(statistics.median(deep), 3) if deep else None,
        "p95_deep_revision_ms": _percentile_nearest_rank(deep, 0.95),
        "median_accepted_model_ms": round(statistics.median(accepted), 3)
        if accepted
        else None,
        "p95_accepted_model_ms": _percentile_nearest_rank(accepted, 0.95),
        "accepted_model_count": len(accepted),
        "technical_quality_pass_count": sum(
            item.get("status") == "pass" for item in quality
        ),
        "technical_quality_failure_count": sum(
            item.get("status") == "fail" for item in quality
        ),
        "human_review_required_count": sum(
            item.get("human_review_required") is True for item in quality
        ),
        "source_refinement_latency_ms": None,
        "source_refinement_note": "disabled: benchmark ran with Privacy First semantics",
    }


class _CaptureWebSocket:
    def __init__(self, clock: Callable[[], float]):
        self.clock = clock
        self.messages: list[dict] = []
        self.timeline: list[tuple[float, dict]] = []
        self.events: asyncio.Queue[tuple[float, dict]] = asyncio.Queue()
        self.head_provider: Callable[[], dict] | None = None
        self.stale_publishes = 0
        self.stale_publish_events: list[dict] = []

    def set_head_provider(self, provider: Callable[[], dict]) -> None:
        self.head_provider = provider

    def _record_stale_publish(self, captured_at: float, message: dict) -> None:
        if message.get("type") != "debate_update":
            return
        data = message.get("data") or {}
        if data.get("origin") not in {"model", "model_stream"}:
            return
        head = self.head_provider() if self.head_provider is not None else {}
        if not isinstance(head, dict):
            return
        current_claim_id = str(head.get("claim_id") or "")
        published_claim_id = str(data.get("claim_id") or "")
        if (
            current_claim_id
            and published_claim_id
            and current_claim_id != published_claim_id
        ):
            stale = True
        else:
            current_revision = int(head.get("transcript_revision") or 0)
            published_revision = max(
                int(data.get("transcript_revision") or 0),
                int(data.get("claim_revision") or 0),
            )
            stale = bool(
                current_revision
                and published_revision
                and published_revision < current_revision
                and not bool(head.get("claim_is_interim"))
            )
        if stale:
            self.stale_publishes += 1
            self.stale_publish_events.append(
                {
                    "captured_at": captured_at,
                    "data": dict(data),
                    "head": dict(head),
                }
            )

    async def send_json(self, message: dict) -> None:
        if message.get("type") != "debate_update":
            return
        captured_at = self.clock()
        self._record_stale_publish(captured_at, message)
        self.messages.append(message)
        self.timeline.append((captured_at, message))
        await self.events.put((captured_at, message))

    @staticmethod
    def matches_turn(
        message: dict,
        claim_id: str,
        transcript_revision: int,
        *,
        final_only: bool = False,
    ) -> bool:
        # Visible card revisions advance on both partial and final publishes.
        # Model worker revisions advance even when a request is cancelled.
        # Neither counter identifies the transcript a card actually answers.
        data = message.get("data") or {}
        return bool(
            claim_id
            and transcript_revision > 0
            and message.get("type") == "debate_update"
            and data.get("claim_id") == claim_id
            and data.get("transcript_revision") == transcript_revision
            and data.get("origin")
            in ({"model"} if final_only else {"model_stream", "model"})
            and _has_visible_spoken_text(data)
        )

    async def wait_for_turn(
        self,
        claim_id: str,
        transcript_revision: int,
        timeout_seconds: float,
    ) -> tuple[float, dict]:
        async with asyncio.timeout(timeout_seconds):
            while True:
                captured_at, message = await self.events.get()
                if self.matches_turn(message, claim_id, transcript_revision):
                    return captured_at, message

    def has_turn(self, claim_id: str, transcript_revision: int) -> bool:
        return any(
            self.matches_turn(message, claim_id, transcript_revision, final_only=True)
            for message in self.messages
        )


class _NoopActivity:
    async def cycle_started(self, *_args, **_kwargs):
        return None

    async def cycle_finished(self, *_args, **_kwargs):
        return None

    async def cycle_error(self, *_args, **_kwargs):
        return None


class _NoopEventBus:
    def publish(self, *_args, **_kwargs):
        return None


def _has_visible_spoken_text(data: dict) -> bool:
    primary = (
        "counter_question" if data.get("primary_move") == "question" else "answer_now"
    )
    value = data.get(primary)
    return isinstance(value, str) and bool(value.strip())


class ApplicationReplay:
    """Timestamp transcript ingestion and the actual debate_update event."""

    def __init__(self, orchestrator, websocket: _CaptureWebSocket, clock):
        self.orchestrator = orchestrator
        self.websocket = websocket
        self.clock = clock
        self._unavailable = False

    async def measure_turn(
        self,
        turn: dict[str, str],
        *,
        turn_index: int,
        timeout_seconds: float,
    ) -> dict:
        # A turn can emit a streamed model card and a later complete model card.
        # Discard unread events from the completed prior turn so their older
        # timestamps cannot be mistaken for this turn's first model paint.
        while not self.websocket.events.empty():
            self.websocket.events.get_nowait()
        stale_before = self.websocket.stale_publishes
        started = self.clock()
        record = {
            "turn_index": turn_index,
            "speaker": turn["speaker"],
            "text": turn["text"],
            "revision": None,
            "claim_id": None,
            "transcript_revision": None,
            "recommendation_revision": None,
            "status": "failed",
            "first_update_ms": None,
            "current_update_ms": None,
            "deep_revision_ms": None,
            "accepted_model_ms": None,
            "ui_acknowledged": False,
            "stale_publishes": 0,
            "deep_recommendation": None,
            "source_refinement_ms": None,
            "research_status": "disabled",
            "recommendation": None,
            "error_type": None,
            "error": None,
        }
        try:
            if self._unavailable:
                raise RuntimeError(
                    "Replay is quarantined after timeout or cancellation"
                )
            if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be finite and positive")
            deadline = asyncio.get_running_loop().time() + timeout_seconds
            await self.orchestrator.feed_transcript(turn["text"], turn["speaker"])
            claim_id = str(self.orchestrator._active_claim_id or "")
            transcript_revision = self.orchestrator._transcript_revision
            record["claim_id"] = claim_id
            record["transcript_revision"] = transcript_revision
            # The production scheduler starts a single coalescing worker so
            # continuous speech cannot cancel every useful reply. Let that
            # worker claim its revision before observing the event.
            await asyncio.sleep(0)
            revision = self.orchestrator._debate_revision
            record["revision"] = revision  # Retain the worker counter for diagnostics.
            try:
                captured_at, _message = await self.websocket.wait_for_turn(
                    claim_id,
                    transcript_revision,
                    max(0.0, deadline - asyncio.get_running_loop().time()),
                )
            except TimeoutError as exc:
                raise TimeoutError(
                    "model did not emit a debate_update before the timeout"
                ) from exc
            task = self.orchestrator._objection_task
            if task is not None:
                remaining = max(0.0, deadline - asyncio.get_running_loop().time())
                # Shield avoids wait_for waiting forever for a cancellation-
                # resistant worker. The exception path quarantines this replay.
                await asyncio.wait_for(asyncio.shield(task), remaining)
            record["first_update_ms"] = elapsed_ms(started, captured_at)
            accepted = next(
                (
                    (at, item)
                    for at, item in reversed(self.websocket.timeline)
                    if at >= started
                    and self.websocket.matches_turn(
                        item, claim_id, transcript_revision, final_only=True
                    )
                ),
                None,
            )
            if accepted is None:
                raise RuntimeError(
                    "model answer was not accepted/displayed: "
                    + str(
                        getattr(self.orchestrator.objection_agent, "last_outcome", None)
                    )[:300]
                )
            accepted_at, accepted_message = accepted
            data = accepted_message["data"]
            record["recommendation_revision"] = data.get("recommendation_revision")
            record["deep_revision_ms"] = elapsed_ms(started, accepted_at)
            record["accepted_model_ms"] = elapsed_ms(started, accepted_at)
            record["deep_recommendation"] = {
                key: data.get(key)
                for key in (
                    "answer_now",
                    "counterargument",
                    "counter_question",
                    "analogy",
                    "primary_move",
                    "confidence",
                    "needs_research",
                )
            }
            record["ui_acknowledged"] = self.orchestrator.acknowledge_debate_update(
                claim_id=str(data.get("claim_id") or ""),
                recommendation_revision=int(data.get("recommendation_revision") or 0),
            )
            if record["ui_acknowledged"] is not True:
                raise RuntimeError(
                    "Current model event was not accepted by the headless acknowledgement contract"
                )
            record["current_update_ms"] = elapsed_ms(started, accepted_at)
            record["recommendation"] = {
                key: data.get(key, "")
                for key in (
                    "answer_now",
                    "counterargument",
                    "counter_question",
                    "analogy",
                    "primary_move",
                )
            }
            record["quality_preflight"] = evaluate_recommendation_contract(data)
            required = ["answer_now"]
            if data.get("primary_move") == "question":
                required.append("counter_question")
            missing = [
                key
                for key in required
                if not isinstance(data.get(key), str) or not data[key].strip()
            ]
            if missing:
                raise ValueError("debate_update is missing: " + ", ".join(missing))
            record["status"] = "ok"
        except asyncio.CancelledError:
            self._quarantine()
            record["status"] = "cancelled"
            raise
        except Exception as exc:
            if isinstance(exc, TimeoutError):
                self._quarantine()
            record["error_type"] = type(exc).__name__
            record["error"] = str(exc)[:500]
        record["stale_publishes"] = self.websocket.stale_publishes - stale_before
        return record

    def _quarantine(self) -> None:
        """Never start another turn after abandoning an owned model worker."""
        self._unavailable = True
        task = self.orchestrator._objection_task
        if task is not None and not task.done():
            task.cancel()

            def consume(completed):
                if not completed.cancelled():
                    completed.exception()

            task.add_done_callback(consume)
        # Cancellation is not physical thread termination. The benchmark
        # process owner supplies a final deadline; this replay is not reused.

    async def supersession_probe(
        self,
        turns: list[dict[str, str]],
        *,
        delay_seconds: float,
        timeout_seconds: float,
    ) -> dict:
        previous = None
        statuses: list[str] = []
        records: list[dict] = []
        evidence: list[tuple[str, int]] = []
        cancellation_count = 0
        for index, turn in enumerate(turns):
            await self.orchestrator.feed_transcript(turn["text"], turn["speaker"])
            evidence.append(
                (
                    str(self.orchestrator._active_claim_id or ""),
                    self.orchestrator._transcript_revision,
                )
            )
            # The coalescing worker increments the production revision when it
            # claims pending speech, not synchronously inside feed_transcript.
            # Yield once so a one-turn probe does not check revision zero.
            await asyncio.sleep(0)
            current = self.orchestrator._objection_task
            if previous is not None:
                try:
                    await previous
                    status = (
                        "ok"
                        if self.websocket.has_turn(*evidence[index - 1])
                        else "failed"
                    )
                    statuses.append(status)
                    records.append({"turn_index": index - 1, "status": status})
                except asyncio.CancelledError:
                    cancellation_count += 1
                    statuses.append("cancelled")
                    records.append({"turn_index": index - 1, "status": "cancelled"})
            previous = current
            if index < len(turns) - 1:
                await asyncio.sleep(delay_seconds)

        if previous is not None:
            try:
                await asyncio.wait_for(previous, timeout_seconds)
                status = "ok" if self.websocket.has_turn(*evidence[-1]) else "failed"
                record = {"turn_index": len(turns) - 1, "status": status}
                if status == "failed":
                    record["error"] = str(
                        getattr(self.orchestrator.objection_agent, "last_outcome", None)
                    )[:500]
                statuses.append(status)
                records.append(record)
            except asyncio.CancelledError:
                cancellation_count += 1
                statuses.append("cancelled")
                records.append({"turn_index": len(turns) - 1, "status": "cancelled"})
            except Exception as exc:
                statuses.append("failed")
                records.append(
                    {
                        "turn_index": len(turns) - 1,
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    }
                )
        for record in records:
            claim_id, transcript_revision = evidence[record["turn_index"]]
            record.update(claim_id=claim_id, transcript_revision=transcript_revision)
        return {
            "delay_ms": round(delay_seconds * 1000.0, 3),
            "cancellation_count": cancellation_count,
            "completed_count": sum(status != "cancelled" for status in statuses),
            "statuses": statuses,
            "failure_count": sum(status == "failed" for status in statuses),
            "stale_publishes": self.websocket.stale_publishes,
            "records": records,
        }

    async def interim_continuation_probe(
        self,
        *,
        partial: str,
        continuation: str,
        delay_seconds: float,
        timeout_seconds: float,
    ) -> dict:
        """Prove a response already generating survives more words in one turn."""
        while not self.websocket.events.empty():
            self.websocket.events.get_nowait()
        started = self.clock()
        utterance_id = "benchmark-live-utterance"
        await self.orchestrator.feed_interim_transcript(
            partial,
            utterance_id=utterance_id,
        )
        await asyncio.sleep(delay_seconds)
        continued_at = self.clock()
        await self.orchestrator.feed_interim_transcript(
            continuation,
            utterance_id=utterance_id,
        )
        task = self.orchestrator._objection_task
        if task is not None:
            await asyncio.wait_for(task, timeout_seconds)
        model_updates = [
            (at, message["data"])
            for at, message in self.websocket.timeline
            if at >= started
            and message.get("data", {}).get("claim_id") == utterance_id
            and message.get("data", {}).get("origin") in {"model_stream", "model"}
        ]
        first = model_updates[0] if model_updates else None
        return {
            "delay_ms": round(delay_seconds * 1000.0, 3),
            "same_claim": bool(model_updates)
            and all(data.get("claim_id") == utterance_id for _, data in model_updates),
            "arrived_after_continuation": bool(first and first[0] > continued_at),
            "visible_model_updates": len(model_updates),
            "first_visible_ms": elapsed_ms(started, first[0]) if first else None,
            "first_answer": first[1].get("answer_now") if first else None,
            "stale_publishes": self.websocket.stale_publishes,
            "status": "ok" if first else "failed",
        }

    async def spoken_playbook_probe(
        self,
        *,
        context: str,
        timeout_seconds: float,
    ) -> dict:
        """Run a voice control against existing context without new opponent text."""
        await self.orchestrator.feed_transcript(context, "Gegenseite")
        task = self.orchestrator._objection_task
        if task is not None:
            await asyncio.wait_for(task, timeout_seconds)
        before = await self.orchestrator.transcript_buffer.get_window()
        started = self.clock()
        consumed = await self.orchestrator.feed_transcript(
            "Debate AI, Zeile für Zeile",
            "Nutzer",
            speaker_type="team",
            is_local_mic=True,
        )
        task = self.orchestrator._objection_task
        if task is not None:
            await asyncio.wait_for(task, timeout_seconds)
        after = await self.orchestrator.transcript_buffer.get_window()
        updates = [
            (at, message["data"])
            for at, message in self.websocket.timeline
            if at >= started
            and message.get("data", {}).get("origin") in {"model_stream", "model"}
        ]
        first = updates[0] if updates else None
        return {
            "command_consumed": consumed is True,
            "transcript_unchanged": before == after,
            "normalized_control": self.orchestrator.directives[-1]
            if self.orchestrator.directives
            else "",
            "visible_model_updates": len(updates),
            "first_visible_ms": elapsed_ms(started, first[0]) if first else None,
            "first_answer": first[1].get("answer_now") if first else None,
            "stale_publishes": self.websocket.stale_publishes,
            "status": "ok" if consumed is True and first else "failed",
        }


def create_application_replay(
    agent,
    *,
    clock: Callable[[], float] = time.perf_counter,
) -> ApplicationReplay:
    """Build the production orchestrator path with persistence stubbed out."""
    from app.services.agents.orchestrator import AgentOrchestrator, TranscriptBuffer
    from app.services.debate_settings import DebateSettings

    orchestrator = object.__new__(AgentOrchestrator)
    websocket = _CaptureWebSocket(clock)
    orchestrator.session_id = uuid.uuid4()
    orchestrator.websocket = websocket
    orchestrator.directives = []
    orchestrator.speakers = []
    orchestrator.local_only = True
    mode = getattr(agent, "_debate_mode", "persuasive")
    orchestrator.debate_settings = DebateSettings(
        mode=mode if mode in {"persuasive", "forceful"} else "persuasive"
    )
    orchestrator.transcript_buffer = TranscriptBuffer()
    orchestrator.objection_agent = agent
    orchestrator.activity = _NoopActivity()
    orchestrator._event_bus = _NoopEventBus()

    async def save_without_database(*_args, **_kwargs):
        return True

    orchestrator._save_and_send_insight = save_without_database
    orchestrator._get_model = lambda _slug: getattr(agent, "_model", "benchmark")
    orchestrator._is_enabled = lambda slug, fallback=True: slug == "objection_handler"
    orchestrator._stopped = False
    orchestrator._consolidated_context_event = asyncio.Event()
    orchestrator._objection_task = None
    orchestrator._debate_pending = False
    orchestrator._interim_debate_chunks = deque(maxlen=3)
    orchestrator._interim_debate_hypotheses = {}
    orchestrator._active_utterance_id = None
    orchestrator._active_claim_id = None
    orchestrator._transcript_revision = 0
    orchestrator._recommendation_revision = 0
    orchestrator._debate_revision = 0
    orchestrator._research_tasks = set()
    orchestrator._research_cache = {}
    orchestrator._last_research_at = 0.0
    orchestrator._debate_diagnostics = []
    websocket.set_head_provider(
        lambda: {
            "claim_id": getattr(orchestrator, "_active_claim_id", None),
            "transcript_revision": getattr(orchestrator, "_transcript_revision", 0),
            "claim_is_interim": getattr(
                orchestrator, "_active_claim_is_interim", False
            ),
        }
    )
    return ApplicationReplay(orchestrator, websocket, clock)


class OpenAIStreamingClient:
    def __init__(self, endpoint: str, model: str, timeout_seconds: float):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    async def stream(self, turns: list[dict[str, str]]) -> AsyncIterator[str]:
        payload = build_request_payload(turns, self.model)
        async with (
            httpx.AsyncClient(
                timeout=self.timeout, trust_env=False, follow_redirects=False
            ) as session,
            session.stream(
                "POST", f"{self.endpoint}/chat/completions", json=payload
            ) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                event = json.loads(data)
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content") or ""
                if content:
                    yield content


def build_request_payload(turns: list[dict[str, str]], model: str) -> dict:
    transcript = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in turns)
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Bisherige Debatte:\n{transcript}\n\n/no_think",
            },
        ],
        # Ollama's OpenAI endpoint otherwise spends the short live budget in
        # Qwen's reasoning channel and can finish with empty visible content.
        "reasoning_effort": "none",
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 220,
        "stream": True,
    }


async def _ollama_metadata(endpoint: str, model: str) -> dict:
    base = endpoint.rstrip("/")
    base = base.removesuffix("/v1")
    try:
        async with httpx.AsyncClient(
            timeout=10.0, trust_env=False, follow_redirects=False
        ) as session:
            response = await session.post(f"{base}/api/show", json={"model": model})
            response.raise_for_status()
            payload = response.json()
        details = payload.get("details") or {}
        return {
            "parameter_size": details.get("parameter_size"),
            "quantization_level": details.get("quantization_level"),
            "family": details.get("family"),
        }
    except Exception as exc:
        return {"metadata_error": f"{type(exc).__name__}: {str(exc)[:200]}"}


async def run_benchmark(args: argparse.Namespace) -> dict:
    # Validate direct Python callers too, before any database/PII substitutions.
    if endpoint_scope(args.endpoint) != "loopback":
        raise ValueError("Benchmark requires a trusted loopback HTTP model endpoint")
    mode = getattr(args, "mode", "persuasive")
    if mode not in {"persuasive", "forceful"}:
        raise ValueError("Unsupported debate mode")
    if (
        not math.isfinite(args.timeout)
        or args.timeout <= 0
        or not math.isfinite(args.cancellation_delay_ms)
        or args.cancellation_delay_ms < 0
    ):
        raise ValueError("Benchmark timing limits must be finite and valid")
    if args.app_model_id and (
        not args.app_model_id.startswith("endpoint:")
        or args.app_model_id.startswith(
            ("endpoint:subscription-ai:", "endpoint:gemini-web:")
        )
    ):
        raise ValueError(
            "Benchmark requires a local endpoint model, not a hosted bridge"
        )
    await verify_native_local_model(args.endpoint, args.model)
    from app.services import llm
    from app.services.agents.objection_handler import ObjectionHandlerAgent
    from app.services.llm_endpoint import OpenAIEndpoint

    turns = load_turns(args.fixture)
    app_model_id = args.app_model_id or f"endpoint:german-debate-ollama:{args.model}"
    original_resolve_endpoint = llm.resolve_endpoint
    original_is_local_only = llm.is_local_only
    original_record_token_usage = llm.record_token_usage
    original_protect_and_guard = llm.pii_egress.protect_and_guard

    async def resolve_benchmark_endpoint(provider: str, model_id: str):
        if model_id == app_model_id:
            return OpenAIEndpoint(
                base_url=args.endpoint.rstrip("/"),
                model=args.model,
                api_key=args.api_key,
            )
        raise ValueError("Benchmark refused an unselected model route")

    # The saved endpoint uses host.docker.internal for the container. The
    # benchmark runs on the Windows host, so resolve this one model to the
    # explicit CLI URL while retaining every production layer after routing.
    llm.resolve_endpoint = resolve_benchmark_endpoint

    # This standalone harness has no application database. The measured model
    # endpoint is explicitly required to be loopback above, so bypass only the
    # database-backed global privacy flag while retaining every generation and
    # scheduler layer in the production path.
    async def benchmark_local_only() -> bool:
        return False

    llm.is_local_only = benchmark_local_only

    async def ignore_benchmark_usage(*_args, **_kwargs) -> None:
        return None

    llm.record_token_usage = ignore_benchmark_usage
    llm.pii_egress.protect_and_guard = benchmark_protect_and_guard
    try:
        live_agent = ObjectionHandlerAgent(
            model_override=app_model_id,
            recommendation_only=True,
            style_focus="natural",
            debate_mode=mode,
        )
        prompt_template_sha256 = hashlib.sha256(
            live_agent._current_prompt_template().encode("utf-8")
        ).hexdigest()
        replay = create_application_replay(live_agent)
        records: list[dict] = []
        for index, turn in enumerate(turns):
            records.append(
                await replay.measure_turn(
                    dict(turn),
                    turn_index=index,
                    timeout_seconds=args.timeout,
                )
            )

        if getattr(args, "skip_probes", False):
            probe = {
                "status": "not_requested",
                "cancellation_count": 0,
                "failure_count": 0,
                "stale_publishes": 0,
            }
            interim_probe = {"status": "not_requested", "stale_publishes": 0}
            spoken_playbook_probe = {"status": "not_requested", "stale_publishes": 0}
        elif replay._unavailable:
            probe = {
                "status": "not_run_after_timeout",
                "cancellation_count": 0,
                "failure_count": 1,
                "stale_publishes": 0,
            }
            interim_probe = {"status": "not_run_after_timeout", "stale_publishes": 0}
            spoken_playbook_probe = {
                "status": "not_run_after_timeout",
                "stale_publishes": 0,
            }
        else:
            probe_replay = create_application_replay(
                ObjectionHandlerAgent(
                    model_override=app_model_id,
                    recommendation_only=True,
                    style_focus="natural",
                    debate_mode=mode,
                )
            )
            probe = await probe_replay.supersession_probe(
                turns[: min(3, len(turns))],
                delay_seconds=args.cancellation_delay_ms / 1000.0,
                timeout_seconds=args.timeout,
            )
            interim_replay = create_application_replay(
                ObjectionHandlerAgent(
                    model_override=app_model_id,
                    recommendation_only=True,
                    style_focus="natural",
                    debate_mode=mode,
                )
            )
            interim_probe = await interim_replay.interim_continuation_probe(
                partial="Solarstrom ist nachts nutzlos, weil",
                continuation=(
                    "Solarstrom ist nachts nutzlos, weil keine Sonne scheint und "
                    "Speicher angeblich zu teuer sind."
                ),
                delay_seconds=args.cancellation_delay_ms / 1000.0,
                timeout_seconds=args.timeout,
            )
            control_replay = create_application_replay(
                ObjectionHandlerAgent(
                    model_override=app_model_id,
                    recommendation_only=True,
                    style_focus="natural",
                    debate_mode=mode,
                )
            )
            spoken_playbook_probe = await control_replay.spoken_playbook_probe(
                context=turns[0]["text"],
                timeout_seconds=args.timeout,
            )
    finally:
        llm.resolve_endpoint = original_resolve_endpoint
        llm.is_local_only = original_is_local_only
        llm.record_token_usage = original_record_token_usage
        llm.pii_egress.protect_and_guard = original_protect_and_guard
    return {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "measurement_path": "transcript_ingest_to_debate_update",
        "mode": mode,
        "prompt_template_sha256": prompt_template_sha256,
        "prompt_fingerprint_scope": "resolved live template only; excludes dynamic inputs",
        "fixture_sha256": hashlib.sha256(
            json.dumps(
                turns, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
        "acceptance_scope": "headless orchestrator callback; not real UI paint or human acceptance",
        "endpoint": args.endpoint,
        "model": args.model,
        "app_model_id": app_model_id,
        "model_metadata": await _ollama_metadata(args.endpoint, args.model),
        "fixture": "built-in-german-debate"
        if args.fixture is None
        else str(args.fixture),
        "research_egress": "disabled",
        "generation_egress": endpoint_scope(args.endpoint),
        "turns": records,
        "supersession_probe": probe,
        "interim_continuation_probe": interim_probe,
        "spoken_playbook_probe": spoken_playbook_probe,
        "summary": summarize(
            records,
            cancellation_count=probe["cancellation_count"],
            probe_failure_count=probe["failure_count"],
            stale_publishes=(
                sum(int(record.get("stale_publishes") or 0) for record in records)
                + int(probe.get("stale_publishes") or 0)
                + int(interim_probe.get("stale_publishes") or 0)
                + int(spoken_playbook_probe.get("stale_publishes") or 0)
            ),
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument(
        "--mode", choices=("persuasive", "forceful"), default="persuasive"
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Bearer key for the benchmark endpoint; omitted for local Ollama",
    )
    parser.add_argument(
        "--app-model-id",
        help=(
            "Configured DebateAI endpoint model id; defaults to the id "
            "created by setup_debate_assistant.ps1"
        ),
    )
    parser.add_argument(
        "--skip-probes",
        action="store_true",
        help="Only measure ordered turns for a paired export",
    )
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--cancellation-delay-ms", type=float, default=150.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if endpoint_scope(args.endpoint) != "loopback":
        print("Benchmark refused a non-loopback or invalid endpoint.", file=sys.stderr)
        return 2
    result = asyncio.run(run_benchmark(args))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(rendered)
    return 1 if result["summary"]["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
