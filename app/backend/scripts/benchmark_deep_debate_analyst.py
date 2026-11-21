"""Two-call proof for local Qwen plus the configured hosted debate analyst."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from app.services.agents.objection_handler import DebateSource, ObjectionHandlerAgent
from app.services.agents.orchestrator import (
    AgentOrchestrator,
    _materially_better_recommendation,
)
from app.services.debate_research import research_claim
from app.services.llm import provider_for

CASES = (
    {
        "kind": "argumentation",
        "claim": (
            "Wenn persoenliche Freiheit der hoechste politische Wert ist, darf der Staat "
            "keine verbindlichen Regeln setzen; jede Regel widerlegt sonst den Freiheitsanspruch."
        ),
        "position": "Freiheit gilt fuer alle und braucht deshalb faire gemeinsame Grenzen.",
        "context": "Die Gegenseite setzte zuvor Freiheit mehrfach mit voelliger Regellosigkeit gleich.",
        "research_query": "",
    },
    {
        "kind": "fakten",
        "claim": "Deutschland hatte im Jahr 2025 eine Inflationsrate von acht Prozent.",
        "position": "Statistische Behauptungen muessen am amtlichen Jahreswert geprueft werden.",
        "context": "Offen ist, welche Grundgesamtheit und welcher Zeitraum gemeint sind.",
        "research_query": "Deutschland Inflationsrate 2025 Destatis Jahresdurchschnitt",
    },
)


async def run_case(case: dict, qwen_model: str, analyst_model: str) -> dict:
    qwen = ObjectionHandlerAgent(
        model_override=qwen_model,
        session_id=None,
        recommendation_only=True,
        always_analogy=False,
        style_focus="concise",
    )
    started = time.perf_counter()
    await qwen.run_cycle(
        transcript_window=f"[Gegenseite]: {case['claim']}",
        directives=[],
        speakers=[],
    )
    qwen_ms = round((time.perf_counter() - started) * 1000, 1)
    recommendation = qwen.latest_recommendation.model_copy(
        update={
            "target_claim": qwen.latest_recommendation.target_claim or case["claim"],
        }
    )

    sources: list[DebateSource] = []
    if case["research_query"]:
        result = await research_claim(case["claim"], case["research_query"])
        sources = [
            DebateSource(**source.model_dump())
            for source in result.sources
            if source.passage.strip()
        ]

    started = time.perf_counter()
    analysis, prompt = await qwen.analyze_deep(
        recommendation,
        model_id=analyst_model,
        own_position=case["position"],
        relevant_context=case["context"],
        sources=sources,
    )
    analyst_ms = round((time.perf_counter() - started) * 1000, 1)
    merger = object.__new__(AgentOrchestrator)
    candidate = merger._merge_deep_analysis(
        recommendation,
        analysis,
        model_id=analyst_model,
        prompt=prompt,
        sources=sources,
    )
    replaced = _materially_better_recommendation(recommendation, candidate)
    adopted = (
        candidate
        if replaced
        else candidate.model_copy(
            update={
                "answer_now": recommendation.answer_now,
                "counterargument": recommendation.counterargument,
            }
        )
    )
    return {
        "kind": case["kind"],
        "claim": case["claim"],
        "qwen": {
            "model": qwen_model,
            "latency_ms": qwen_ms,
            "answer": recommendation.answer_now,
        },
        "analyst": {
            "provider": "Google"
            if provider_for(analyst_model) == "google"
            else "OpenAI",
            "model": analyst_model,
            "latency_ms": analyst_ms,
            "prompt": prompt,
            "result": analysis.model_dump(mode="json"),
            "external_research": bool(sources),
            "sources": [source.model_dump(mode="json") for source in sources],
        },
        "adoption": {
            "qwen_answer_replaced": replaced,
            "best_reply": adopted.answer_now,
            "counterarguments": adopted.argument_points,
            "followups": [item.question for item in adopted.follow_ups],
        },
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--qwen-model", default="endpoint:german-debate-ollama:qwen3:4b"
    )
    parser.add_argument("--analyst-model", default="gemini-3.8-flash")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = [
        await run_case(case, args.qwen_model, args.analyst_model) for case in CASES
    ]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases": cases,
    }
    Path(args.output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"2 bestanden; Provider={cases[0]['analyst']['provider']} ({args.analyst_model})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
