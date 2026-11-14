"""AgentOrchestrator — event-driven agent coordination.

Architecture:
- Audio Gateway (native-audio model, Gemini Live) — silent listener, relays input_transcription
- Consolidated Analyst (text model, batch interval) — questions, observations, opportunities, action items
- Objection Handler (fast text model, short interval) — flags objections with a ready response
- Synthesizer (meta-agent) — event-driven, runs on new_insight with cooldown
- Opportunity Specialist (DB-backed) — event-driven, runs on new_opportunity
- Internal EventBus for pub/sub coordination between agents
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime

from fastapi import WebSocket
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.services.identity import env_value
from app.models import Directive, Question, TranscriptEntry, Speaker
from app.services.transcript_refiner import (
    REFINER_LIVE_WINDOW,
    REFINER_SLUG as TRANSCRIPT_REFINER_SLUG,
    live_refiner_is_idle,
    refine_session,
    update_payload as refiner_update_payload,
)
from app.services.agents.activity import (
    ActivityRegistry,
    classify_error,
    saved_outcome,
)
from app.services.agents.base import TranscriptBuffer
from app.services.agents.speaker_context import (
    build_speaker_aliases,
    format_transcript_segment,
    speaker_display_name,
)
from app.services.agents.consolidated_analyst import ConsolidatedAnalystAgent
from app.services.agents.event_bus import CooldownSubscriber, EventBus
from app.services.agents.objection_handler import (
    ConditionalFollowUp,
    DeepDebateAnalysis,
    DebateRecommendation,
    ObjectionHandlerAgent,
    build_atomic_claims,
    normalize_experimental_strategies,
    _has_speakable_guidance,
)
from app.services.debate_contracts import DebateSource
from app.services.experimental_debate import build_experimental_update
from app.services.agents.opportunity_specialist import run_opportunity_specialist_cycle
from app.services.agents.strategic_signals import (
    STRATEGIC_SIGNALS_SLUG,
    run_strategic_signals_cycle,
)
from app.services.agents.synthesizer import clear_synthesizer_state, run_synthesizer_cycle
from app.services.briefing_synthesis import (
    BRIEF_ARBITER_SLUG,
    agent_config_enabled,
    run_session_synthesis,
)
from app.services.gemini_live import GeminiLiveSession
from app.services.llm import provider_for, registry_entry
from app.services.privacy import allows_local_only
from app.services.speaker_name_rewriter import replace_speaker_labels
from app.services.local_live_captioner import LocalLiveCaptioner, is_local_live_model
from app.services.openai_realtime import OpenAIRealtimeSession
from app.services.meeting_context import (
    build_meeting_context_text,
    debate_mode_for_meeting_type,
    normalize_meeting_type,
    should_match_offerings,
)
from app.services.debate_research import (
    ResearchResult,
    is_safe_research_query,
    research_claim,
)
from app.services.debate_settings import DebateSettings
from app.services.argument_graph import load_argument_graph, persist_argument_recommendation
from app.services.semantic_argument_memory import SemanticArgumentMemory
from app.services.knowledge_context import select_context_sections
from app.services.session_manager import get_local_dossier_context
from app.services.debate_learning import (
    load_good_debate_examples,
    revoke_good_debate_example,
    save_good_debate_example,
)
from app.services.ai_config import (
    adaptive_reasoning_settings,
    analysis_deadline_seconds,
    create_configuration_snapshot,
    live_research_deadline_seconds,
    deep_analysis_models,
    max_parallel_analyses,
    model_cooldown_seconds,
    model_timeout_seconds,
    playbook_controls,
    provider_route,
    research_settings,
    use_configuration_snapshot,
)
from app.services.external_analysis_scheduler import (
    AnalysisJobContext,
    ExternalAnalysisCancelled,
    ExternalAnalysisDeadline,
    ExternalAnalysisPriority,
    ExternalAnalysisQueueFull,
    ExternalAnalysisSuperseded,
    external_analysis_scheduler,
)
from app.services.external_reasoning import AdaptiveReasoningEffort
from app.services.provider_capabilities import (
    classify_provider_failure,
    effective_reasoning_effort,
)
from app.services.agents.prompt_resources import load_prompt_resource

logger = logging.getLogger(__name__)
AUTOMATIC_RESEARCH_STABILITY_SECONDS = 1.5


def _select_relevant_transcript_excerpt(
    transcript: str,
    *,
    claim: str,
    standpoint: str,
    context: str,
    max_chars: int = 2400,
) -> str:
    """Select claim-relevant transcript lines before external analysis."""
    clean = " ".join(str(transcript or "").split()).strip()
    if not clean:
        return ""
    budget = max(800, min(int(max_chars), 2400))
    lines = [line.strip() for line in re.split(r"(?<=[.!?])\s+", clean) if line.strip()]
    if not lines:
        return clean[:budget]
    terms = {
        token.casefold()
        for value in (claim, standpoint, context)
        for token in re.findall(r"[\wäöüß]+", str(value or ""))
        if len(token) >= 4
    }
    scored = []
    for index, line in enumerate(lines):
        words = set(re.findall(r"[\wäöüß]+", line.casefold()))
        score = len(terms.intersection(words))
        if index == len(lines) - 1:
            score += 1
        scored.append((score, index, line))
    selected = sorted(scored, key=lambda item: (-item[0], item[1]))
    chosen: list[str] = []
    chars = 0
    for _score, _index, line in selected:
        if line in chosen:
            continue
        needed = len(line) + (1 if chosen else 0)
        if chosen and chars + needed > budget:
            continue
        if not chosen and len(line) > budget:
            chosen.append(line[:budget])
            break
        chosen.append(line)
        chars += needed
    if not chosen:
        chosen = [lines[-1][:budget]]
    return " ".join(chosen)[:budget]


def _external_analysis_deadline(priority: ExternalAnalysisPriority) -> int:
    """Keep live automatic research short while manual deep work stays long."""
    if priority is ExternalAnalysisPriority.MANUAL:
        return analysis_deadline_seconds()
    return live_research_deadline_seconds()


def _annotate_experimental_sources(
    sources: list[DebateSource],
    *,
    target_claim: str,
) -> list[DebateSource]:
    """Attach deterministic evidence metadata without inventing a fact.

    A conflict is only marked when already-read evidence has an explicit
    supports/contradicts relation. Search hits, unread passages, and unclear
    relations remain unknown so the UI never treats a URL list as proof.
    """
    if not sources:
        return []
    groups: dict[str, list[tuple[int, str]]] = {}
    for index, source in enumerate(sources):
        relation = str(source.claim_relation or "unclear")
        if (
            source.retrieval_status != "read"
            or not str(source.passage or "").strip()
            or relation not in {"supports", "contradicts"}
        ):
            continue
        claim_key = " ".join(
            str(source.claim or target_claim or "").casefold().split()
        )[:320]
        if claim_key:
            groups.setdefault(claim_key, []).append((index, relation))
    conflict_ids: dict[int, str] = {}
    for claim_key, members in groups.items():
        relations = {relation for _, relation in members}
        if relations == {"supports", "contradicts"}:
            conflict_id = "conflict-" + hashlib.sha256(
                claim_key.encode("utf-8")
            ).hexdigest()[:16]
            for index, _relation in members:
                conflict_ids[index] = conflict_id
    annotated: list[DebateSource] = []
    claim_terms = {
        token for token in re.findall(r"[\wäöüß]+", str(target_claim).casefold())
        if len(token) >= 5
    }
    for index, source in enumerate(sources):
        update: dict[str, object] = {}
        if index in conflict_ids:
            update["conflict_group_id"] = conflict_ids[index]
        if (
            source.retrieval_status == "read"
            and str(source.passage or "").strip()
            and claim_terms
        ):
            passage_terms = set(
                re.findall(r"[\wäöüß]+", str(source.passage).casefold())
            )
            overlap = len(claim_terms.intersection(passage_terms))
            if overlap >= min(2, len(claim_terms)):
                update["scope_match"] = "match"
                update["entailment_confidence"] = max(
                    float(source.entailment_confidence or 0.0),
                    0.7,
                )
        annotated.append(source.model_copy(update=update) if update else source)
    return annotated


def _bind_research_result(
    result: ResearchResult,
    claim: str,
    *,
    claim_revision: int,
) -> ResearchResult:
    """Attach reusable query results to the exact current claim revision."""
    return result.model_copy(update={
        "claim": claim,
        "sources": [
            source.model_copy(update={
                "claim": claim,
                "claim_revision": claim_revision,
            })
            for source in result.sources
        ],
    })

_DEBATE_MEETING_TYPES = {"debate_persuasive", "debate_forceful"}
_DEBATE_LIVE_AGENTS = {
    "audio_gateway",
    "objection_handler",
    "consolidated_analyst",
}

_CHATGPT_WEB_ANALYST = "chatgpt-web:gpt-6"
_SUBSCRIPTION_GPT_ANALYST = "endpoint:subscription-ai:gpt-6-sol"
_SUBSCRIPTION_GPT_FALLBACK = "endpoint:subscription-ai:gpt-6.1-sol"
_SUBSCRIPTION_GEMINI_ANALYST = "endpoint:subscription-ai:gemini-3.1-pro-preview"
_GOOGLE_GEMINI_ANALYST = "gemini-3.1-pro-preview"
_SUBSCRIPTION_GEMINI_AVAILABLE_FALLBACK = "endpoint:subscription-ai:gemini-3.8-flash-high"
_GEMINI_WEB_ANALYST = "endpoint:gemini-web:gemini-3.1-pro"


def _uses_adaptive_gpt6_reasoning(model_id: str) -> bool:
    return model_id.rsplit(":", 1)[-1].casefold().startswith("gpt-6")

_PLAYBOOK_CONTROLS = (
    (
        ("zeile fuer zeile", "zeile für zeile", "punkt fuer punkt", "punkt für punkt"),
        "[PLAYBOOK] Zeile fuer Zeile: Beantworte die Punkte des aktuellen Zugs einzeln und knapp.",
    ),
    (
        ("zugestehen", "concede", "drehen"),
        "[PLAYBOOK] Zugestehen und drehen: Raeume nur den berechtigten Kern ein und fuehre zur Nutzerposition zurueck.",
    ),
    (
        ("widerlegen", "widerlegung", "rebuttal"),
        "[PLAYBOOK] Widerlegung: Greife den schwaechsten tragenden Punkt des aktuellen Zugs direkt an.",
    ),
    (
        ("folgen abwaegen", "folgen abwägen", "weigh impacts"),
        "[PLAYBOOK] Folgen abwaegen: Vergleiche die Folgen beider Positionen am entscheidenden Unterschied.",
    ),
    (
        ("offene frage", "zurueck zu meiner frage", "zurück zu meiner frage"),
        "[PLAYBOOK] Offene Frage: Kehre zur relevantesten noch unbeantworteten Frage im Kontext zurueck.",
    ),
    (
        ("sei offensiver", "direkter", "haerter", "härter"),
        "[PLAYBOOK] Offensiver: Formuliere direkter und benenne die entscheidende Beweislast, ohne zu beleidigen.",
    ),
    (
        ("humor", "ironisch", "ironie", "schlagfertig"),
        "[PLAYBOOK] Humor: Nutze nur eine zur Situation passende kurze Pointe; erfinde dafuer keine Tatsachen.",
    ),
)


def _normalize_debate_control(text: str) -> str:
    normalized = " ".join(text.split()).strip()
    folded = normalized.casefold()
    for terms, directive in playbook_controls() or _PLAYBOOK_CONTROLS:
        if any(term in folded for term in terms):
            return directive
    return normalized


_VOICE_COMMANDS = {
    "recherche an": "Recherche an",
    "recherche aus": "Recherche aus",
    "modus hart": "Modus hart",
    "modus überzeugend": "Modus überzeugen",
    "modus ueberzeugend": "Modus ueberzeugen",
    "tiefenanalyse": "Tiefenanalyse",
    "faktencheck": "Faktencheck",
    "originalquelle": "Originalquelle",
    "zeile für zeile": "Zeile für Zeile",
    "zeile fuer zeile": "Zeile fuer Zeile",
    "punkt für punkt": "Punkt für Punkt",
    "punkt fuer punkt": "Punkt fuer Punkt",
    "zugestehen und drehen": "Zugestehen und drehen",
    "widerlegen": "Widerlegen",
    "folgen abwägen": "Folgen abwägen",
    "folgen abwaegen": "Folgen abwaegen",
    "offene frage": "Offene Frage",
    "sei offensiver": "Sei offensiver",
    "humor": "Humor",
}
_VOICE_COMMAND_FORBIDDEN = (
    "api", "abo", "account", "anmeldung", "budget", "kosten", "konto",
    "login", "passwort", "provider", "zahlung",
)


def _parse_voice_command(text: str) -> str | None:
    """Return one canonical, deliberately tiny voice command or ``None``."""
    normalized = " ".join(text.casefold().split()).strip(" .,!?:;-")
    # ASR commonly inserts a comma or colon after the wake phrase. Accept the
    # punctuation without weakening the deliberately small command allowlist.
    prefix = re.match(r"^debate\s+ai[\s,:;-]+(.+)$", normalized)
    if prefix is None:
        return None
    command = prefix.group(1).strip()
    if (
        any(marker in text for marker in ('"', "'", "„", "“", "«", "»"))
        or any(term in normalized for term in (" sagte ", " sagt ", " zitat "))
        or any(term in command for term in _VOICE_COMMAND_FORBIDDEN)
    ):
        return None
    return _VOICE_COMMANDS.get(command)


_RESEARCH_CATEGORY_TERMS = {
    "counterevidence": (
        "Widerlegung Gegenbeleg Faktencheck Primaerquelle Statistik Zahlen Daten"
    ),
    "translation": "Originalquelle Originaltext Uebersetzung pruefen",
    "interpretation": "Originalquelle Kontext Interpretation pruefen",
    "all": (
        "Widerlegung Gegenbeleg Faktencheck Statistik Zahlen Daten Originalquelle "
        "Originaltext Uebersetzung Kontext Interpretation"
    ),
}


def _manual_research_query(
    recommendation: DebateRecommendation,
    category: str,
) -> str:
    """Build one bounded query from context the copilot already extracted."""
    terms = _RESEARCH_CATEGORY_TERMS.get(category)
    if not terms:
        return ""
    claim = recommendation.target_claim.strip()
    if not claim:
        claim = next(
            (point.strip() for point in recommendation.argument_points if point.strip()),
            "",
        )
    if not claim:
        return ""
    return " ".join(f"{claim} {terms}".split())[:300].rstrip()


def _recommendation_quality(recommendation: DebateRecommendation) -> int:
    """Small deterministic gate so slower work only replaces a clearly better card."""
    score = {"low": 0, "medium": 2, "high": 3}[recommendation.confidence]
    score += bool(recommendation.target_claim.strip())
    score += min(2, len([point for point in recommendation.argument_points if point.strip()]))
    score += recommendation.question_status != "none"
    score += bool(recommendation.open_question.strip())
    score += bool(recommendation.follow_ups)
    score += bool(recommendation.research_query.strip())
    score += 3 * bool(recommendation.sources)
    score += 2 * bool(recommendation.research_alert.strip())
    return int(score)


def _materially_better_recommendation(
    current: DebateRecommendation,
    candidate: DebateRecommendation,
) -> bool:
    current_terms = _claim_terms(current.target_claim)
    candidate_terms = _claim_terms(candidate.target_claim)
    if current_terms and (
        not candidate_terms or not current_terms.intersection(candidate_terms)
    ):
        return False
    if _contains_unsupported_numeric_assertion(candidate):
        return False
    if _contains_unsupported_evidence_claim(candidate):
        return False
    return _recommendation_quality(candidate) > _recommendation_quality(current)


_CLAIM_STOPWORDS = {
    "aber", "auch", "dass", "deine", "deiner", "dies", "diese", "dieser",
    "doch", "eine", "einen", "einer", "haben", "heute", "ihre", "nicht",
    "oder", "sagen", "seien", "sind", "wird", "wurde", "zum", "zur",
}
_NUMBER_WORDS = {
    "null", "eins", "ein", "eine", "zwei", "drei", "vier", "fuenf",
    "fünf", "sechs", "sieben", "acht", "neun", "zehn", "zwanzig",
    "dreissig", "dreißig", "vierzig", "fuenfzig", "fünfzig", "sechzig",
    "siebzig", "achtzig", "neunzig", "hundert", "tausend", "million",
    "milliarde", "prozent",
}
_UNCERTAINTY_MARKERS = (
    "behaupt", "unbelegt", "ungeprueft", "ungeprüft", "ohne beleg",
    "ohne quelle", "quelle fehlt", "nicht belegt", "unklar",
)


def _claim_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\wäöüß]+", text.casefold())
        if len(token) >= 4 and token not in _CLAIM_STOPWORDS
    }


def _unicode_words(text: str) -> set[str]:
    """Tokenize words without encoding-specific character classes."""
    return set(re.findall(r"[\wäöüß]+", text.casefold()))


_NUMERIC_UNIT_ALIASES = {
    "%": {"%", "prozent", "percent"},
    "prozent": {"%", "prozent", "percent"},
    "percent": {"%", "prozent", "percent"},
}


def _structured_numeric_scope_matches(
    source: DebateSource,
    context: str,
) -> bool:
    """Require structured source scope to be present in the spoken claim.

    A valid source identifier and matching number are not enough when the
    source carries an explicit unit, period, or population. Missing or
    contradictory scope keeps the recommendation unverified rather than
    silently treating the source as a truth certificate.
    """
    folded = context.casefold()
    for field in ("numeric_unit", "numeric_period", "numeric_population"):
        value = str(getattr(source, field, "") or "").strip().casefold()
        if not value:
            continue
        aliases = _NUMERIC_UNIT_ALIASES.get(value)
        if aliases is not None:
            if not any(alias in folded for alias in aliases):
                return False
            continue
        terms = _claim_terms(value)
        context_terms = _claim_terms(context)
        if terms and any(
            not any(
                candidate == term
                or (len(term) >= 5 and len(candidate) >= 5 and (
                    candidate.startswith(term[:5]) or term.startswith(candidate[:5])
                ))
                for candidate in context_terms
            )
            for term in terms
        ):
            return False
    return True


def _contains_unsupported_numeric_assertion(
    recommendation: DebateRecommendation,
) -> bool:
    spoken = " ".join(
        (recommendation.answer_now, recommendation.counterargument)
    ).casefold()
    has_number = bool(re.search(r"\d", spoken)) or bool(
        set(re.findall(r"[\wäöüß]+", spoken)).intersection(_NUMBER_WORDS)
    )
    has_number = has_number or bool(_unicode_words(spoken).intersection(_NUMBER_WORDS))
    if not has_number:
        return False
    if any(marker in spoken for marker in _UNCERTAINTY_MARKERS):
        return False

    spoken_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", spoken))
    spoken_number_words = set(
        re.findall(r"[\wÃ¤Ã¶Ã¼ÃŸ]+", spoken)
    ).intersection(_NUMBER_WORDS)
    spoken_number_words = _unicode_words(spoken).intersection(_NUMBER_WORDS)
    target_terms = _claim_terms(recommendation.target_claim)
    context = " ".join((recommendation.target_claim, spoken))
    for source in recommendation.sources:
        if (
            source.retrieval_status != "read"
            or not source.passage.strip()
            or (
                source.claim_relation != "supports"
                and source.verification_status != "supports"
            )
        ):
            continue
        evidence = " ".join((source.claim, source.passage)).casefold()
        evidence_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", evidence))
        evidence_number_words = set(
            re.findall(r"[\wÃ¤Ã¶Ã¼ÃŸ]+", evidence)
        ).intersection(_NUMBER_WORDS)
        evidence_number_words = _unicode_words(evidence).intersection(_NUMBER_WORDS)
        claim_matches = not target_terms or bool(
            target_terms.intersection(_claim_terms(source.claim))
        )
        number_matches = bool(
            spoken_numbers.intersection(evidence_numbers)
            or spoken_number_words.intersection(evidence_number_words)
        )
        if claim_matches and number_matches:
            if not _structured_numeric_scope_matches(source, context):
                continue
            return False
    return True


def _contains_unsupported_evidence_claim(
    recommendation: DebateRecommendation,
) -> bool:
    """Gate quotes, attributions, conditions and causal claims like numbers."""
    spoken = " ".join(
        (recommendation.answer_now, recommendation.counterargument)
    ).strip()
    folded = spoken.casefold()
    if not spoken or any(marker in folded for marker in _UNCERTAINTY_MARKERS):
        return False
    readable_support = [
        source
        for source in recommendation.sources
        if source.retrieval_status == "read"
        and (source.claim_relation == "supports" or source.verification_status == "supports")
        and source.passage.strip()
    ]
    evidence = "\n".join(
        " ".join((source.title, source.publisher, source.passage, source.claim))
        for source in readable_support
    ).casefold()
    quotes = [
        value.strip().casefold()
        for value in re.findall(r'["„“«»]([^"„“«»]{4,180})["„“«»]', spoken)
    ]
    if quotes and any(quote not in evidence for quote in quotes):
        return True
    has_attribution = bool(
        re.search(r"\b(laut|gem[aä]ß|nach angaben von|sagt|schreibt|studie von)\b", folded)
    )
    if has_attribution and not readable_support:
        return True
    has_causal_claim = any(
        marker in folded
        for marker in (
            "führt zu", "fuehrt zu", "verursacht", "bewirkt", "ist der grund",
            "deshalb entsteht", "dadurch steigt", "dadurch sinkt",
        )
    )
    if has_causal_claim and not readable_support:
        return True
    target_folded = recommendation.target_claim.casefold()
    target_is_conditional = bool(
        re.search(r"\b(wenn|falls|sofern|unter der bedingung)\b", target_folded)
    )
    if target_is_conditional and not re.search(
        r"\b(wenn|falls|sofern|unter dieser bedingung|nur dann)\b", folded
    ):
        return True
    return False


def _parse_model_intervals(raw: str) -> dict[str, int]:
    """Parse AgentConfig.model_intervals JSON into {model_id: interval}, tolerant
    of empty/garbage so a bad value never breaks scheduling."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): int(v) for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


# Restatements cluster about a minute apart: on a measured 57-minute meeting the
# median gap between insights the synthesizer later merged was 1.0 minute, and 90
# percent were within 2.1 minutes. A 60s window structurally missed 13 of 21 of
# them and left the synthesizer to merge them afterwards at full corpus cost.
_DEDUP_WINDOW_SECONDS = 300

# Open questions carried into the analyst and strategic-signals prompts so they
# stop re-proposing what is already on the board. Only pruned when a question is
# answered, so on a measured meeting it grew to 45 entries and never shrank --
# unbounded in call length. Kept generous: the emission-time dedup cannot catch
# a re-proposal at minute 40 of something first raised at minute 12, so this
# list is the only thing standing between the user and that repeat (ALP-287).
_MAX_ACTIVE_QUESTIONS = 24

# Non-question insights already saved this call, stubbed for the analyst's
# "already on the board" context. The emission-time word-overlap dedup only
# reaches back _DEDUP_WINDOW_SECONDS and active_questions only carries
# item_type question, so nothing stopped the analyst from re-proposing a
# minute-12 observation at minute 40 in fresh words; the synthesizer then had
# to merge the copies after the user saw both. Stubs are head-truncated the
# way the synthesizer's settled records are (ALP-283) and the cap bounds the
# prompt cost on long calls: 48 stubs at 110 chars is roughly 1.5k tokens.
_MAX_BOARD_STUBS = 48
_BOARD_STUB_CHARS = 110
ProgressCallback = Callable[[dict[str, object]], Awaitable[None]]

# Drain modes for call finalization: "full" runs every post-call stage,
# "skip_analysis" stops after insight reconciliation, and "minimal"
# (disconnect/error path) runs no analysis stages at all.
DRAIN_MODE_FULL = "full"
DRAIN_MODE_SKIP_ANALYSIS = "skip_analysis"
DRAIN_MODE_MINIMAL = "minimal"

_SHIELD_GATEWAY_REMEDY = (
    "Cloud live captions would hear the names the shield withholds. "
    "Switch the Audio Bridge to the on-device captioner (Admin -> Agents) "
    "or turn off the PII Shield (Admin -> Privacy)."
)


def _shield_locks_gateway(slug: str, audio_local_only: bool, model_id: str) -> bool:
    """The PII Shield admits only an on-device model as the audio gateway."""
    return slug == "audio_gateway" and audio_local_only and not is_local_live_model(model_id)


_ACTIVITY_AGENTS = (
    ("audio_gateway", "Audio Bridge", "stream", None, True),
    (
        "consolidated_analyst",
        "Consolidated Analyst",
        "interval",
        settings.TEXT_AGENT_INTERVAL_SECONDS,
        True,
    ),
    (
        "objection_handler",
        "Debate Copilot",
        "event",
        None,
        True,
    ),
    (
        "synthesizer",
        "Principal Agent",
        "event",
        settings.SYNTHESIZER_COOLDOWN_SECONDS,
        True,
    ),
    (
        "opportunity_specialist",
        "Opportunity Specialist",
        "event",
        settings.OPPORTUNITY_SPECIALIST_COOLDOWN_SECONDS,
        True,
    ),
    ("strategic_signals", "Strategic Signals", "interval", 45, False),
    (TRANSCRIPT_REFINER_SLUG, "Transcript Refiner", "interval", 45, False),
    ("brief_meeting_lens", "Briefing Meeting Lens", "post_call", None, True),
    ("brief_discovery_lens", "Briefing Discovery Lens", "post_call", None, True),
    ("brief_arbiter", "Briefing Arbiter", "post_call", None, True),
)


def drain_progress_percent(current_step: int, total_steps: int) -> int:
    """Map a finalization step onto the 15..95 band shown by the progress overlay."""
    if total_steps <= 1:
        return 95
    return 15 + round((current_step - 1) * 80 / (total_steps - 1))

# Live orchestrators by session id so REST routes can push mid-call updates.
# ponytail: in-process dict; needs a shared channel if the app ever runs multi-worker.
_live_orchestrators: dict[uuid.UUID, "AgentOrchestrator"] = {}


def get_live_orchestrator(session_id: uuid.UUID) -> "AgentOrchestrator | None":
    return _live_orchestrators.get(session_id)


def live_debate_snapshot() -> dict[str, object]:
    """Read-only overlay state without opening a second live-call connection."""
    from app.services.ws_event_stream import latest_session_event

    for session_id, orchestrator in reversed(list(_live_orchestrators.items())):
        if getattr(orchestrator, "_stopped", True):
            continue
        latest = latest_session_event(session_id, "debate_update")
        recommendation = (
            latest["data"]
            if latest is not None
            else orchestrator.objection_agent.latest_recommendation.model_dump(mode="json")
        )
        return {
            "active": True,
            "session_id": str(session_id),
            "recommendation": recommendation,
        }
    return {"active": False, "session_id": "", "recommendation": None}


# Matches the cadence the client already sees during transcription drain, so a
# quiet analysis stage is not mistaken for a stalled one.
DRAIN_HEARTBEAT_SECONDS = 5.0


async def _run_drain_heartbeat(
    progress_callback: ProgressCallback,
    latest: dict[str, dict],
    interval: float = DRAIN_HEARTBEAT_SECONDS,
) -> None:
    """Re-announce the running stage until the drain moves on.

    Repeats the last progress event rather than inventing one, so the client
    sees the same stage and step it already knows, marked as a heartbeat. A send
    failure ends the heartbeat quietly: the socket is gone, which the drain
    itself does not care about.
    """
    while True:
        await asyncio.sleep(interval)
        event = latest.get("event")
        if not event:
            continue
        try:
            await progress_callback({**event, "heartbeat": True})
        except Exception:
            return


async def _emit_progress(
    progress_callback: ProgressCallback | None,
    stage: str,
    message: str,
    current_step: int,
    total_steps: int,
    progress: int,
):
    if not progress_callback:
        return
    await progress_callback(
        {
            "stage": stage,
            "message": message,
            "current_step": current_step,
            "total_steps": total_steps,
            "progress": progress,
        }
    )


_DEDUP_NEGATIONS = {"nicht", "kein", "keine", "nie", "niemals", "ohne"}
_DEDUP_TIME_MARKERS = {
    "heute", "gestern", "morgen", "derzeit", "aktuell", "frueher",
    "kuenftig", "jaehrlich",
}


def _dedup_semantic_markers(text: str) -> tuple[set[str], bool, set[str], set[str]]:
    folded = text.casefold()
    tokens = set(re.findall(r"[\w]+", folded))
    numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", folded))
    conditions = {
        " ".join(match.group(0).split())
        for match in re.finditer(
            r"\b(?:wenn|falls|sofern|vorausgesetzt|unter der bedingung)\b[^,.;!?]{0,160}",
            folded,
        )
    }
    return (
        numbers,
        bool(tokens & _DEDUP_NEGATIONS),
        tokens & _DEDUP_TIME_MARKERS,
        conditions,
    )


def _texts_similar(a: str, b: str, threshold: float = 0.6) -> bool:
    """Simple word-overlap similarity check for near-duplicate detection."""
    if _dedup_semantic_markers(a) != _dedup_semantic_markers(b):
        return False
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b)
    return overlap / min(len(words_a), len(words_b)) >= threshold


class AgentOrchestrator:
    """Central coordinator for all agents with event-driven coordination."""

    def _privacy_admits(self, model_id: str) -> bool:
        """Return whether the current privacy mode permits ``model_id``.

        Keeping this as a real method also makes the routing helpers safe for
        the deliberately lightweight orchestrators used by diagnostics and
        replay tests.  ``__init__`` replaces it with the equivalent closure
        below so existing per-session wiring remains unchanged.
        """
        if not getattr(self, "local_only", False):
            return True
        admitted_models = getattr(self, "admitted_models", None)
        if admitted_models is not None:
            return model_id in admitted_models
        return provider_for(model_id) == "local"

    def __init__(
        self,
        session_id: uuid.UUID,
        websocket: WebSocket,
        directives: list[str],
        doc_summaries: str,
        active_questions: list[dict],
        speakers: list[dict],
        local_dossier_context: str = "",
        agent_configs: dict | None = None,
        meeting_type: str = "general",
        meeting_context: str = "",
        local_only: bool = False,
        admitted_models: set[str] | None = None,
        board_stubs: list[dict] | None = None,
        audio_local_only: bool = False,
        transcription_language: str = "auto",
        debate_settings: DebateSettings | None = None,
        capture_id: str = "",
    ):
        self.session_id = session_id
        # The browser keeps this token across a socket reconnect. It makes an
        # identical in-flight capture replay idempotent while a genuinely new
        # capture (new token) cannot coalesce with the previous one.
        # Leave room for the gateway/track suffix in the VARCHAR(128) segment ID.
        self.capture_id = str(capture_id or uuid.uuid4().hex)[:96]
        self.websocket = websocket
        self.directives = directives
        self.doc_summaries = doc_summaries
        self.local_dossier_context = local_dossier_context
        self.active_questions = active_questions
        self.speakers = speakers
        self._agent_configs = agent_configs or {}
        self.local_only = local_only
        self.debate_settings = debate_settings or DebateSettings()
        self._experimental_mode = self.debate_settings.pipeline_mode == "experimental_debateai"
        if self.debate_settings.profile_directive:
            self.directives = [
                directive for directive in self.directives
                if not directive.startswith("[PLAYBOOK]")
            ] + [self.debate_settings.profile_directive]
        self._default_debate_mode = self.debate_settings.mode
        # The PII Shield locks audio alone: a cloud live gateway would hear
        # the names the shield exists to withhold, so it is skipped while
        # cloud text models (which receive tokens only) stay admitted.
        self.audio_local_only = audio_local_only or local_only
        # Model ids Privacy First admits, resolved by the caller because the
        # verdict needs a database read (see privacy.admitted_model_ids) and
        # this constructor is synchronous. None means "not resolved": fall back
        # to the bundled-local check so a caller that predates this stays safe.
        self.admitted_models = admitted_models
        self.privacy_blocked_agents: list[dict] = []
        self.meeting_type = normalize_meeting_type(meeting_type)
        self._debate_live_mode = self.meeting_type in _DEBATE_MEETING_TYPES
        self.meeting_context = meeting_context
        self._derive_meeting_context()

        def _get_model(slug: str) -> str:
            cfg = self._agent_configs.get(slug)
            return cfg.model_id if cfg else ""

        def _privacy_admits(model_id: str) -> bool:
            """Whether Privacy First lets this model run.

            Membership in the caller-resolved set, because admission is about
            where the model is served, not what its provider is called: a qwen
            on an endpoint at localhost qualifies while the same model behind a
            public URL does not. Only when the set was never resolved do we fall
            back to the bundled-ONNX check, which is conservative by design.
            """
            if not self.local_only:
                return True
            if self.admitted_models is not None:
                return model_id in self.admitted_models
            return provider_for(model_id) == "local"

        # Helper to check if an agent is enabled (DB config with fallback).
        # In Privacy First mode an enabled agent also needs a model that stays
        # on this machine or its network; one that does not is recorded so the
        # call can say so instead of the agent silently never running.
        def _is_enabled(slug: str, fallback: bool = True) -> bool:
            if self._debate_live_mode and slug not in _DEBATE_LIVE_AGENTS:
                return False
            cfg = self._agent_configs.get(slug)
            enabled = cfg.enabled if cfg else fallback
            if not enabled:
                return False
            model_id = _get_model(slug)
            if not model_id:
                return False
            if _shield_locks_gateway(slug, self.audio_local_only, model_id):
                return False
            if not self.local_only:
                return enabled
            if _privacy_admits(model_id):
                return True
            if not any(b["agent"] == slug for b in self.privacy_blocked_agents):
                self.privacy_blocked_agents.append({"agent": slug, "model_id": model_id})
            return False

        def _get_prompt(slug: str) -> str:
            cfg = self._agent_configs.get(slug)
            fallback = cfg.prompt if cfg else ""
            return load_prompt_resource(f"agent.{slug}", fallback) if fallback else ""

        def _get_interval(slug: str, fallback: int) -> int:
            cfg = self._agent_configs.get(slug)
            if not cfg:
                return fallback
            # A per-model budget for the agent's assigned model wins, so the same
            # agent can run tighter on a fast model and looser on a slow one.
            per_model = _parse_model_intervals(getattr(cfg, "model_intervals", "")).get(cfg.model_id)
            if per_model:
                return per_model
            return cfg.interval_seconds if cfg.interval_seconds else fallback

        def _get_knowledge_source_ids(slug: str) -> list[uuid.UUID]:
            cfg = self._agent_configs.get(slug)
            raw = getattr(cfg, "knowledge_source_ids", "") if cfg else ""
            ids = []
            for part in (raw or "").split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    ids.append(uuid.UUID(part))
                except ValueError:
                    logger.warning(f"[orchestrator] invalid knowledge source id '{part}' on agent '{slug}'")
            return ids

        self._is_enabled = _is_enabled
        self._privacy_admits = _privacy_admits
        self._get_model = _get_model
        self._get_prompt = _get_prompt
        self._get_interval = _get_interval
        self._get_knowledge_source_ids = _get_knowledge_source_ids

        # Consolidated text analyst (includes question generation). Built before
        # the activity roster so its active lens count rides in the snapshot.
        enabled_types: set[str] = set()
        ca_cfg = self._agent_configs.get("consolidated_analyst")
        if ca_cfg and ca_cfg.sub_types:
            enabled_types = {t.strip() for t in ca_cfg.sub_types.split(",") if t.strip()}
        else:
            # Fallback to config.py settings
            enabled_types.add("question")
            if settings.AGENT_OBSERVER_ENABLED:
                enabled_types.add("observation")
            if settings.AGENT_OPPORTUNITY_SCOUT_ENABLED:
                enabled_types.add("opportunity")
            if settings.AGENT_ACTION_TRACKER_ENABLED:
                enabled_types.add("action_item")

        # Configurable lens definitions (JSON column); None falls back to the
        # defaults filtered by the legacy sub_types selection above.
        ca_lenses: list | None = None
        raw_lenses = (getattr(ca_cfg, "lenses", "") or "") if ca_cfg else ""
        if raw_lenses.strip():
            try:
                parsed = json.loads(raw_lenses)
                if isinstance(parsed, list):
                    ca_lenses = parsed
            except json.JSONDecodeError:
                logger.warning("[orchestrator] invalid lenses JSON on consolidated_analyst; using defaults")

        ca_model = _get_model("consolidated_analyst")
        self.consolidated_agent = ConsolidatedAnalystAgent(
            enabled_types=enabled_types or None,
            model_override=ca_model,
            prompt_override=_get_prompt("consolidated_analyst") or None,
            meeting_context_text=self.meeting_context_text,
            lenses=ca_lenses,
            session_id=session_id,
            suppressed_types=self._suppressed_analyst_types(),
        )

        activity_agents = []
        for slug, fallback_name, trigger, fallback_interval, fallback_enabled in _ACTIVITY_AGENTS:
            cfg = self._agent_configs.get(slug)
            configured_enabled = cfg.enabled if cfg else fallback_enabled
            admitted = _is_enabled(slug, fallback_enabled)
            session_override = getattr(cfg, "_session_override", None) if cfg else None
            interval = (
                _get_interval(slug, fallback_interval)
                if fallback_interval is not None
                else None
            )
            if interval is not None and (
                not isinstance(interval, (int, float))
                or isinstance(interval, bool)
            ):
                interval = fallback_interval
            debate_suppressed = self._debate_live_mode and slug not in _DEBATE_LIVE_AGENTS
            if debate_suppressed:
                state = "off"
                blocked_reason = "debate_live_minimal"
                remedy = (
                    "In Debatten laufen live nur Transkription, Debate Copilot, "
                    "und eine verdichtete Hintergrundanalyse."
                )
            elif not configured_enabled:
                state = "off"
                blocked_reason = (
                    "session_override" if session_override is False else "disabled"
                )
                remedy = (
                    "Enabled globally but turned off for this session in pre-call agent selection."
                    if blocked_reason == "session_override"
                    else "Enable it in Admin -> Agents."
                )
            elif not _get_model(slug):
                state = "blocked"
                blocked_reason = "no_model"
                remedy = "Choose a model for this agent in Admin -> Agents."
            elif not admitted and not self.local_only and _shield_locks_gateway(slug, self.audio_local_only, _get_model(slug)):
                state = "blocked"
                blocked_reason = "pii_shield"
                remedy = _SHIELD_GATEWAY_REMEDY
            elif not admitted:
                state = "blocked"
                blocked_reason = "privacy_first"
                remedy = (
                    "Assign a local model to this agent (Admin -> Agents) or "
                    "turn off Privacy First (Admin -> Connections)."
                )
            elif slug == "opportunity_specialist" and not self._offering_matching_enabled:
                state = "blocked"
                blocked_reason = "meeting_type"
                remedy = (
                    "Runs for client/sales and customer delivery conversations; "
                    "change the conversation type to enable it."
                )
            else:
                state = "waiting"
                blocked_reason = ""
                remedy = ""
            record = {
                "slug": slug,
                "name": getattr(cfg, "name", "") or fallback_name,
                "trigger": trigger,
                "state": state,
                "enabled": configured_enabled,
                "blocked_reason": blocked_reason,
                "remedy": remedy,
                "interval_seconds": interval,
            }
            if slug == "consolidated_analyst":
                record["lens_count"] = self.consolidated_agent.lens_count
            activity_agents.append(record)
        self.activity = ActivityRegistry(
            session_id,
            websocket,
            activity_agents,
            privacy_first=local_only,
        )

        # Audio Gateway: a cloud streaming session (Gemini Live / OpenAI Realtime)
        # or the on-device local captioner, chosen by the gateway agent's model.
        # The cloud gateways take the workspace transcription language (ALP-399);
        # Parakeet v3 is multilingual; the configured language also suppresses
        # misleading short-window English greeting flashes.
        gw_model = _get_model("audio_gateway")
        self.audio_gateway = None
        if is_local_live_model(gw_model):
            self.audio_gateway = LocalLiveCaptioner(
                model_override=gw_model,
                session_id=session_id,
                language=transcription_language,
            )
        elif provider_for(gw_model) == "openai":
            self.audio_gateway = OpenAIRealtimeSession(
                model_override=gw_model,
                session_id=session_id,
                language=transcription_language,
            )
        elif gw_model:
            self.audio_gateway = GeminiLiveSession(
                model_override=gw_model,
                session_id=session_id,
                language=transcription_language,
            )

        # Objection handler (fast scan loop over the freshest transcript)
        objection_prompt = _get_prompt("objection_handler") or None
        if self._experimental_mode:
            objection_prompt = load_prompt_resource(
                "experimental_debate_live_v1",
                objection_prompt or "",
            )
        self.objection_agent = ObjectionHandlerAgent(
            model_override=_get_model("objection_handler"),
            prompt_override=objection_prompt,
            meeting_context_text=self.meeting_context_text,
            session_id=session_id,
            debate_mode=debate_mode_for_meeting_type(
                self.meeting_type,
                self._default_debate_mode,
            ),
            always_analogy=self.debate_settings.always_analogy,
            style_focus=self.debate_settings.style_focus,
            recommendation_only=self._debate_live_mode,
        )

        # Shared transcript buffer
        self.transcript_buffer = TranscriptBuffer()

        # Event bus
        self._event_bus = EventBus()

        # Cooldown subscribers (created in start())
        self._synth_subscriber: CooldownSubscriber | None = None
        self._opp_specialist_subscriber: CooldownSubscriber | None = None

        # Coordination
        self._consolidated_task: asyncio.Task | None = None
        self._objection_task: asyncio.Task | None = None
        self._debate_pending = False
        self._last_transcript_activity_at: float | None = None
        self._refiner_job: asyncio.Task | None = None
        # Once a speakable streaming partial is visible, keep that worker alive
        # long enough to publish its complete answer.  Cancelling at that point
        # makes continuous speech look like a broken copilot: every new partial
        # resets the clock before the first useful card can finish.
        self._debate_partial_visible = False
        self._interim_debate_hypotheses: dict[str, str] = {}
        self._active_utterance_id: str | None = None
        self._gateway_segment_id = f"{self.capture_id}:gateway"
        self._active_interim_segment_id = self._gateway_segment_id
        self._gateway_segment_revision = 0
        self._gateway_segment_start_sample = 0
        self._gateway_samples_sent = 0
        self._interim_segment_revisions: dict[str, int] = {}
        self._finalized_interim_segments: set[str] = set()
        self._active_claim_id: str | None = None
        self._active_claim_is_interim = False
        self._transcript_revision = 0
        self._directive_revision = 0
        self._recommendation_revision = 0
        self._debate_revision = 0
        self._research_tasks: set[asyncio.Task] = set()
        # One external research group may serve several distinct analysis
        # lanes, but the same claim revision/query must never create duplicate
        # groups while the first one is still active.
        self._research_group_tasks: dict[tuple[str, int, int, int, str], asyncio.Task] = {}
        self._research_cache: dict[str, ResearchResult] = {}
        self._topic_knowledge: dict[str, dict[str, object]] = {}
        self._experimental_lane_artifacts: list[dict[str, object]] = []
        self._external_model_unavailable_until: dict[str, float] = {}
        try:
            configured_parallelism = (
                int(research_settings().get("experimental_external_parallelism", 3))
                if self._experimental_mode
                else max_parallel_analyses()
            )
            self._external_analysis_scheduler = external_analysis_scheduler(
                max(1, min(4, configured_parallelism))
            )
        except RuntimeError:
            self._external_analysis_scheduler = None
        self._manual_analysis_tasks: dict[str, asyncio.Task] = {}
        adaptive_config = adaptive_reasoning_settings()
        self._adaptive_reasoning_enabled = bool(adaptive_config.pop("enabled", True))
        self._reuse_topic_analysis = bool(adaptive_config.pop("reuse_topic_analysis", True))
        self._topic_similarity_threshold = float(
            adaptive_config.pop("topic_similarity_threshold", 0.46)
        )
        self._adaptive_external_reasoning = AdaptiveReasoningEffort(**adaptive_config)
        self._force_deep_analysis_once = False
        self._last_research_at = 0.0
        self._debate_diagnostics: list[dict[str, object]] = []
        self._argument_memory: deque[dict[str, object]] = deque(maxlen=16)
        self._semantic_argument_memory = (
            SemanticArgumentMemory(
                minimum_score=self.debate_settings.memory_similarity_threshold
            )
            if self.debate_settings.argument_memory_enabled
            else None
        )
        self._semantic_memory_tasks: set[asyncio.Task] = set()
        self._good_answer_examples: list[dict[str, object]] = []
        self._active_speaker_id: str | None = None
        self._active_speaker_name: str | None = None
        self._active_speaker_type: str | None = None
        self._argument_memory_enabled = self.debate_settings.argument_memory_enabled
        self._argument_graph_enabled = self.debate_settings.graph_recording_enabled
        self._argument_graph_tasks: set[asyncio.Task] = set()
        self._gateway_task: asyncio.Task | None = None
        self._strategic_signals_task: asyncio.Task | None = None
        self._refiner_task = None
        self._stopped = False

        # Recent insights for dedup (text -> timestamp)
        self._recent_insights: dict[str, float] = {}

        # Non-question insights on the board, stubbed for the analyst's
        # context (see _MAX_BOARD_STUBS). Seeded from the session's saved
        # insights so a resumed call remembers its own board.
        self._board_stubs: list[dict] = []
        for note in board_stubs or []:
            self._remember_board_stub(
                str(note.get("item_type") or "insight"),
                str(note.get("text") or ""),
            )


    def _experimentalize_recommendation(self, recommendation: DebateRecommendation) -> DebateRecommendation:
        """Attach the four local response moves for the isolated pipeline."""
        if not getattr(self, "_experimental_mode", False):
            return recommendation
        recommendation = recommendation.model_copy(update={"pipeline_mode": "experimental_debateai"})
        options = normalize_experimental_strategies(recommendation)
        selected = recommendation.selected_strategy_id
        if not selected:
            preferred_kinds = ("example", "refutation", "contradiction", "counter_question")
            selected = next(
                (
                    item["id"]
                    for kind in preferred_kinds
                    for item in options
                    if item.get("kind") == kind and item.get("text")
                ),
                "",
            )
        selected_item = next((item for item in options if item.get("id") == selected), None)
        if selected_item is None:
            selected_item = next((item for item in options if item.get("text")), None)
            selected = str((selected_item or {}).get("id") or "")
        selected_text = str((selected_item or {}).get("text") or "")
        selected_kind = str((selected_item or {}).get("kind") or "")
        options = [
            {**item, "selected": str(item.get("id") or "") == selected}
            for item in options
        ]
        # The chosen move is the only large visible answer; alternatives remain
        # available as compact blobs for deliberate selection in the UI.
        return recommendation.model_copy(update={
            "strategy_options": options,
            "selected_strategy_id": selected,
            "answer_now": selected_text or recommendation.answer_now,
            "primary_move": "question" if selected_kind == "counter_question" else "answer",
            "selection_reason": recommendation.selection_reason or "Sofort passendster Zug mit konkretem Beispiel.",
        })
    def briefing_enabled(self) -> bool:
        # The arbiter settles the briefing, so its model decides whether the
        # stage can run at all; a lens on a refused model degrades to a partial
        # briefing rather than cancelling it (see briefing_synthesis).
        if not agent_config_enabled(self._agent_configs, BRIEF_ARBITER_SLUG):
            return False
        if not self._get_model(BRIEF_ARBITER_SLUG):
            return True
        if not self.local_only:
            return True
        return self._privacy_admits(self._get_model(BRIEF_ARBITER_SLUG))

    def drain_stages(self, mode: str = DRAIN_MODE_FULL) -> list[str]:
        """Ordered analysis stages graceful_drain runs for a drain mode.

        The websocket handler owns the surrounding steps: the transcript
        flush (speaker_assignment) before these and the session save after.
        """
        if mode == DRAIN_MODE_MINIMAL:
            return []
        stages = []
        # First, so the final insights and the briefing read the corrected
        # wording rather than the transcriber's.
        if self._is_enabled(TRANSCRIPT_REFINER_SLUG, False):
            stages.append("transcript_refinement")
        stages.extend(["final_insights", "insight_reconciliation"])
        if mode != DRAIN_MODE_SKIP_ANALYSIS:
            stages.append("opportunity_matching")
            if self.briefing_enabled():
                stages.append("call_briefing")
        return stages

    def drain_total_steps(self, mode: str = DRAIN_MODE_FULL) -> int:
        # Transcript flush (step 1) + drain stages + the final save step.
        return 2 + len(self.drain_stages(mode))

    async def _get_complete_transcript(self) -> str:
        """Load the durable, ordered transcript for experimental checkpoints."""
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(TranscriptEntry, Speaker.name, Speaker.speaker_type)
                    .outerjoin(Speaker, Speaker.id == TranscriptEntry.speaker_id)
                    .where(TranscriptEntry.session_id == self.session_id)
                    .order_by(TranscriptEntry.sequence.asc())
                )
                rows = result.all()
            aliases = self.speaker_aliases()
            lines = []
            for entry, speaker_name, speaker_type in rows:
                speaker_id = str(entry.speaker_id) if entry.speaker_id else ""
                lines.append(
                    format_transcript_segment(
                        entry.text,
                        speaker_name or "Unknown",
                        speaker_id=speaker_id,
                        speaker_type=speaker_type,
                        alias=aliases.get(speaker_id),
                    )
                )
            if lines:
                return "\n".join(lines)
        except Exception as exc:
            logger.warning("Complete transcript load failed; using live buffer: %s", exc)
        return await self.transcript_buffer.get_full(aliases=self.speaker_aliases())

    async def start(self):
        """Connect all agents and wire event subscriptions."""
        try:
            if not self._argument_memory_enabled:
                raise LookupError("Argumentgedaechtnis ist deaktiviert")
            async with async_session() as db:
                graph = (
                    await load_argument_graph(db, self.session_id)
                    if self.debate_settings.session_retrieval_enabled
                    else None
                )
                good_examples = (
                    await load_good_debate_examples(db)
                    if self.debate_settings.learning_examples_enabled
                    else []
                )
            claims = sorted(
                (node for node in (graph.nodes if graph else []) if node.kind == "claim"),
                key=lambda node: node.revision,
            )
            for claim in claims[-16:]:
                question = next(
                    (
                        node.text for node in (graph.nodes if graph else [])
                        if node.claim_id == claim.claim_id and node.kind == "question"
                    ),
                    "",
                )
                self._argument_memory.append({
                    "claim_id": claim.claim_id,
                    "target_claim": claim.text,
                    "open_question": question,
                    "revision": claim.revision,
                    "speaker_id": claim.speaker_id,
                    "speaker_name": claim.speaker_name,
                    "speaker_type": claim.speaker_type,
                })
            self._good_answer_examples = [
                {
                    "claim_id": f"good:{example.id}",
                    "target_claim": example.claim,
                    "good_answer": example.answer,
                    "counterargument": example.counterargument,
                    "mode": example.mode,
                    "style_focus": example.style_focus,
                }
                for example in good_examples
            ]
            semantic_task = asyncio.create_task(
                asyncio.to_thread(
                    self._semantic_argument_memory.rebuild,
                    [*self._argument_memory, *self._good_answer_examples],
                ),
                name=f"semantic-argument-memory-{self.session_id}",
            )
            self._semantic_memory_tasks.add(semantic_task)
            semantic_task.add_done_callback(self._semantic_memory_tasks.discard)
        except LookupError:
            pass
        except Exception as exc:
            logger.warning("Argument memory could not be restored: %s", exc)

        # --- Audio Gateway (silent listener) ---
        if self._is_enabled("audio_gateway"):
            try:
                await self.audio_gateway.connect()
                self._gateway_task = asyncio.create_task(self._handle_gateway_responses())
                await self.activity.set_agent_state("audio_gateway", "running")
                await self.activity.update_call(
                    gateway={"state": "ok", "detail": ""}
                )
            except Exception as e:
                logger.error(f"Audio gateway unavailable, continuing without interim transcription: {e}")
                await self.activity.cycle_error(
                    "audio_gateway",
                    classify_error(e, self._get_model("audio_gateway")),
                )
                await self.activity.update_call(
                    gateway={"state": "reconnecting", "detail": str(e)}
                )
        else:
            await self.activity.update_call(
                gateway={"state": "off", "detail": ""}
            )

        # --- Consolidated Analyst ---
        if self._is_enabled("consolidated_analyst") and self.consolidated_agent.enabled_types:
            self._consolidated_task = asyncio.create_task(self._consolidated_agent_loop())

        # --- Debate Copilot ---
        # Transcript arrival schedules this agent directly; there is no polling
        # loop and therefore no artificial wait before a reply can surface.

        # --- Event-driven: Synthesizer ---
        if self._is_enabled("synthesizer"):
            synth_cooldown = self._get_interval("synthesizer", settings.SYNTHESIZER_COOLDOWN_SECONDS)
            self._synth_subscriber = CooldownSubscriber(
                handler=self._run_synthesizer,
                cooldown_seconds=synth_cooldown,
            )
            self._event_bus.subscribe("new_insight", self._synth_subscriber)

        # --- Event-driven: Opportunity Specialist ---
        self._wire_opportunity_specialist()

        if self._is_enabled(STRATEGIC_SIGNALS_SLUG, False):
            self._strategic_signals_task = asyncio.create_task(
                self._strategic_signals_loop()
            )

        if self._is_enabled(TRANSCRIPT_REFINER_SLUG, False):
            self._refiner_task = asyncio.create_task(self._transcript_refiner_loop())

        ca_interval = self._get_interval("consolidated_analyst", settings.TEXT_AGENT_INTERVAL_SECONDS)
        logger.info(
            f"Orchestrator started: gateway={self._is_enabled('audio_gateway')} "
            f"consolidated={self._is_enabled('consolidated_analyst')} "
            f"interval={ca_interval}s "
            f"types={self.consolidated_agent.enabled_types} "
            f"objection={self._is_enabled('objection_handler')} "
            f"synth={self._is_enabled('synthesizer')}(event-driven) "
            f"opp_specialist={self._is_enabled('opportunity_specialist')}(event-driven) "
            f"strategic_signals={self._is_enabled(STRATEGIC_SIGNALS_SLUG, False)}"
        )
        _live_orchestrators[self.session_id] = self

    def _wire_opportunity_specialist(self):
        """Subscribe the opportunity specialist if enabled and the meeting type warrants it."""
        if self._opp_specialist_subscriber is not None:
            return
        if not (self._is_enabled("opportunity_specialist") and self._offering_matching_enabled):
            return
        self._opp_specialist_subscriber = CooldownSubscriber(
            handler=self._run_opportunity_specialist,
            cooldown_seconds=self._get_interval(
                "opportunity_specialist", settings.OPPORTUNITY_SPECIALIST_COOLDOWN_SECONDS
            ),
        )
        self._event_bus.subscribe("new_opportunity", self._opp_specialist_subscriber)

    def _remember_active_question(self, item_id: str, text: str, item_type: str = "question"):
        """Track an open question, dropping the oldest past the cap."""
        self.active_questions.append({"id": item_id, "question": text, "item_type": item_type})
        overflow = len(self.active_questions) - _MAX_ACTIVE_QUESTIONS
        if overflow > 0:
            del self.active_questions[:overflow]

    def _forget_active_question(self, item_id: str | None):
        """Stop carrying a question once it is answered or dismissed."""
        if not item_id:
            return
        self.active_questions[:] = [aq for aq in self.active_questions if aq["id"] != item_id]

    def _remember_board_stub(self, item_type: str, text: str):
        """Track a non-question insight so the analyst stops restating it."""
        text = text.strip()
        if not text:
            return
        if len(text) > _BOARD_STUB_CHARS:
            text = text[:_BOARD_STUB_CHARS].rstrip() + "..."
        self._board_stubs.append({"item_type": item_type, "text": text})
        overflow = len(self._board_stubs) - _MAX_BOARD_STUBS
        if overflow > 0:
            del self._board_stubs[:overflow]

    def _debate_support_context(
        self,
        current_text: str = "",
        *,
        include_local_dossier: bool = False,
        return_related_ids: bool = False,
    ) -> str | tuple[str, list[str]]:
        """Return a tiny evidence board for the next deep debate revision."""
        economy = getattr(
            getattr(self, "debate_settings", None),
            "performance_profile",
            "balanced",
        ) == "economy"
        board_limit = 2 if economy else 4
        lines = [
            f"- [{row.get('item_type') or 'Hinweis'}] {row.get('text', '').strip()}"
            for row in list(getattr(self, "_board_stubs", []))[-board_limit:]
            if row.get("text", "").strip()
        ]
        if include_local_dossier and getattr(self, "local_dossier_context", "").strip():
            lines.append(
                "- [lokales Vorbereitungsdossier; nicht an Cloudmodelle senden]\n"
                + select_context_sections(
                    self.local_dossier_context,
                    current_text,
                    budget=12_000,
                )
            )
        lines.extend(
            f"- [offene Frage] {row.get('question', '').strip()}"
            for row in getattr(self, "active_questions", [])[-2:]
            if row.get("question", "").strip()
        )
        semantic_memory = getattr(self, "_semantic_argument_memory", None)
        semantic_result = (
            semantic_memory.search_targets(
                current_text,
                related_limit=2 if economy else 4,
                conflict_limit=1 if economy else 3,
                exclude_claim_id=str(getattr(self, "_active_claim_id", "") or ""),
                speaker_id=str(getattr(self, "_active_speaker_id", "") or ""),
            )
            if semantic_memory is not None
            else None
        )
        semantic_matches = semantic_result.related if semantic_result is not None else []
        conflict_matches = (
            semantic_result.possible_conflicts if semantic_result is not None else []
        )
        current_terms = _claim_terms(current_text)
        folded = current_text.casefold()
        refers_back = any(
            marker in folded
            for marker in ("deine position", "dieser punkt", "dieser beleg", "dazu", "darum")
        )
        related: list[dict[str, object]] = [match.row for match in semantic_matches]
        related_claim_ids = [
            str(match.row.get("claim_id") or "")
            for match in semantic_matches
            if str(match.row.get("claim_id") or "")
            and match.score >= getattr(self, "_topic_similarity_threshold", 0.46)
        ]
        if not return_related_ids:
            self._active_semantic_related_claim_ids = related_claim_ids
        if not related:
            for row in reversed(list(getattr(self, "_argument_memory", []))):
                claim = str(row.get("target_claim") or "")
                if current_terms.intersection(_claim_terms(claim)) or (
                    refers_back and not related
                ):
                    related.append(row)
                if len(related) == 2:
                    break
            # Lexical fallback is still a real same-topic hit.  Preserve its
            # claim ids for research routing so an unavailable/unwarmed embedder
            # does not misclassify a known topic as new and trigger unnecessary
            # deep analysis.
            for row in related:
                claim_id = str(row.get("claim_id") or "")
                if claim_id and claim_id not in related_claim_ids:
                    related_claim_ids.append(claim_id)
            if not return_related_ids:
                self._active_semantic_related_claim_ids = related_claim_ids
        for row in reversed(related):
            good_answer = str(row.get("good_answer") or "").strip()
            if good_answer:
                lines.append(
                    f"- [bestaetigte eigene Antwort; claim:{str(row.get('claim_id') or '')[:80]}] "
                    f"Auf '{str(row.get('target_claim') or '')[:180]}' "
                    f"passte: {good_answer[:240]}"
                )
                continue
            speaker = str(row.get("speaker_name") or "frueherer Sprecher")
            lines.append(
                f"- [claim:{str(row.get('claim_id') or '')[:80]}; Sprecher:{speaker}] "
                f"{str(row.get('target_claim') or '')[:240]}"
            )
            open_question = str(row.get("open_question") or "").strip()
            if open_question:
                lines.append(f"  Offene Frage: {open_question[:180]}")
        for match in conflict_matches:
            row = match.row
            claim_id = str(row.get("claim_id") or "")[:80]
            reasons = ",".join(match.conflict_reasons)
            span = row.get("original_span")
            span_label = ""
            if (
                isinstance(span, (list, tuple))
                and len(span) == 2
                and all(isinstance(value, int) for value in span)
            ):
                span_label = f"; Originalspanne:{span[0]}-{span[1]}"
            lines.append(
                f"- [moeglicher Konflikt; nur Pruefkandidat; "
                f"claim:{claim_id}; Signale:{reasons}{span_label}] "
                f"{str(row.get('target_claim') or '')[:260]}"
            )
        for knowledge in reversed(list(getattr(self, "_topic_knowledge", {}).values())):
            claim = str(knowledge.get("target_claim") or "")
            if current_terms and not current_terms.intersection(_claim_terms(claim)):
                continue
            claim_id = str(knowledge.get("claim_id") or "")[:80]
            for source in list(knowledge.get("sources") or [])[:2]:
                if not isinstance(source, dict):
                    continue
                passage = str(source.get("passage") or source.get("snippet") or "").strip()
                if passage:
                    lines.append(
                        f"- [Themenwissen; claim:{claim_id}; Quelle:{str(source.get('url') or '')[:240]}] "
                        f"{passage[:320]}"
                    )
            for finding in list(knowledge.get("findings") or [])[:2]:
                if str(finding).strip():
                    lines.append(
                        f"- [Themenwissen; claim:{claim_id}] {str(finding).strip()[:320]}"
                    )
            if len(lines) >= 14:
                break
        context = "\n".join(lines)
        if return_related_ids:
            return context, related_claim_ids
        return context

    async def _debate_support_context_async(
        self,
        current_text: str = "",
        *,
        include_local_dossier: bool = False,
    ) -> str:
        claim_snapshot = str(getattr(self, "_active_claim_id", "") or "")
        transcript_snapshot = int(getattr(self, "_transcript_revision", 0))

        async def retrieve_base_context() -> str:
            context, related_ids = await asyncio.to_thread(
                self._debate_support_context,
                current_text,
                return_related_ids=True,
            )
            if (
                claim_snapshot == str(getattr(self, "_active_claim_id", "") or "")
                and transcript_snapshot == int(getattr(self, "_transcript_revision", 0))
            ):
                self._active_semantic_related_claim_ids = related_ids
            return context

        local_dossier_context = str(
            getattr(self, "local_dossier_context", "") or ""
        )
        if not include_local_dossier or not local_dossier_context.strip():
            # SemanticArgumentMemory uses an ONNX embedding model. Retrieval is
            # small but CPU-bound, so never run it on the WebSocket event loop.
            return await retrieve_base_context()
        model_id = ""
        get_model = getattr(self, "_get_model", None)
        if callable(get_model):
            model_id = str(get_model("objection_handler") or "").strip()
        admitted_models = getattr(self, "admitted_models", None)
        if getattr(self, "local_only", False) and admitted_models is not None:
            dossier_admitted = model_id in admitted_models
        else:
            try:
                dossier_admitted = bool(model_id) and await allows_local_only(model_id)
            except Exception:  # noqa: BLE001 - fail closed before any retrieval
                logger.warning(
                    "Could not verify dossier egress route for %s; omitting local context",
                    model_id or "unconfigured model",
                    exc_info=True,
                )
                dossier_admitted = False
        if not dossier_admitted:
            logger.info(
                "Omitting local dossier from non-local debate route %s",
                model_id or "unconfigured model",
            )
            return await retrieve_base_context()
        try:
            async with async_session() as db:
                dossier_context = await get_local_dossier_context(
                    self.session_id,
                    db,
                    query=current_text,
                )
        except Exception:
            logger.warning("Hybrid dossier retrieval failed", exc_info=True)
            dossier_context = select_context_sections(
                local_dossier_context,
                current_text,
                budget=12_000,
            )
        base_context = await retrieve_base_context()
        dossier_block = (
            "- [lokales Vorbereitungsdossier; nicht an Cloudmodelle senden]\n"
            + dossier_context
        ) if dossier_context.strip() else ""
        return "\n".join(part for part in (dossier_block, base_context) if part)

    def _external_analysis_models(self) -> list[str]:
        """Return configured ChatGPT/Gemini models in existing agent priority order."""
        candidates: list[str] = []
        try:
            served_subscription_models = {
                str(value).strip()
                for value in json.loads(
                    env_value("DEBATEAI_SUBSCRIPTION_MODELS", "[]")
                )
                if str(value).strip()
            }
        except (TypeError, ValueError):
            served_subscription_models = set()
        bridge_configured = bool(
            env_value("DEBATEAI_SUBSCRIPTION_BRIDGE_URL").strip()
            and env_value("DEBATEAI_SUBSCRIPTION_BRIDGE_KEY").strip()
        )
        from app.services.subscription_bridge import (
            gemini_web_cookie_configured,
            gemini_web_models,
        )

        web_bridge_configured = gemini_web_cookie_configured()
        served_web_models = set(gemini_web_models())
        from app.services.chatgpt_web import configured as chatgpt_web_configured
        from app.services.chatgpt_web import runtime_available as chatgpt_web_available

        consumer_chatgpt_ready = chatgpt_web_available() and chatgpt_web_configured()
        # The editable order can mix normal consumer-web accounts, OAuth bridge
        # models and explicitly enabled official APIs. Only advertise a bridge
        # model that its live /models response actually serves.
        for model_id in deep_analysis_models([
            _SUBSCRIPTION_GPT_ANALYST,
            _SUBSCRIPTION_GEMINI_ANALYST,
            _GEMINI_WEB_ANALYST,
            _CHATGPT_WEB_ANALYST,
            _GOOGLE_GEMINI_ANALYST,
            _SUBSCRIPTION_GPT_FALLBACK,
            _SUBSCRIPTION_GEMINI_AVAILABLE_FALLBACK,
        ]):
            if model_id == _CHATGPT_WEB_ANALYST:
                if not consumer_chatgpt_ready:
                    continue
            elif model_id.startswith("endpoint:subscription-ai:"):
                wire_model = model_id.split(":", 2)[-1]
                if not bridge_configured or wire_model not in served_subscription_models:
                    continue
            elif model_id == _GEMINI_WEB_ANALYST:
                wire_model = model_id.split(":", 2)[-1]
                if not web_bridge_configured or wire_model not in served_web_models:
                    continue
            else:
                provider = provider_for(model_id)
                known_cloud_model = bool(registry_entry(model_id)) or model_id.startswith(
                    ("gemini-", "gpt-", "openai-", "o1", "o3", "o4")
                )
                if provider not in {"google", "openai"} or not known_cloud_model:
                    continue
            if model_id not in candidates and self._privacy_admits(model_id):
                candidates.append(model_id)
        for slug in (
            "consolidated_analyst",
            "strategic_signals",
            BRIEF_ARBITER_SLUG,
            "objection_handler",
        ):
            if not self._is_enabled(slug, False):
                continue
            model_id = (self._get_model(slug) or "").strip()
            if not model_id or model_id in candidates:
                continue
            provider = provider_for(model_id)
            known_cloud_model = bool(registry_entry(model_id)) or model_id.startswith(
                ("gemini-", "gpt-", "openai-", "o1", "o3", "o4")
            )
            subscription_bridge = model_id.startswith("endpoint:subscription-ai:")
            gemini_web_bridge = model_id.startswith("endpoint:gemini-web:")
            consumer_chatgpt = model_id == _CHATGPT_WEB_ANALYST
            if subscription_bridge:
                wire_model = model_id.rsplit(":", 1)[-1]
                if wire_model not in served_subscription_models:
                    continue
            if gemini_web_bridge:
                wire_model = model_id.split(":", 2)[-1]
                if wire_model not in served_web_models:
                    continue
            if not (
                (provider in {"google", "openai"} and known_cloud_model)
                or (consumer_chatgpt and consumer_chatgpt_ready)
                or subscription_bridge
                or (gemini_web_bridge and web_bridge_configured)
            ):
                continue
            if not self._privacy_admits(model_id):
                continue
            candidates.append(model_id)
        unavailable = getattr(self, "_external_model_unavailable_until", {})
        now = time.monotonic()
        return [model_id for model_id in candidates if unavailable.get(model_id, 0.0) <= now]

    @staticmethod
    def _analyst_provider_label(model_id: str) -> str:
        if model_id == _CHATGPT_WEB_ANALYST:
            return "OpenAI Web"
        if model_id.startswith("endpoint:gemini-web:"):
            return "Google Web"
        if model_id.startswith("endpoint:subscription-ai:"):
            wire_model = model_id.rsplit(":", 1)[-1].casefold()
            return "Google" if wire_model.startswith("gemini-") else "OpenAI"
        return "Google" if provider_for(model_id) == "google" else "OpenAI"

    def _merge_deep_analysis(
        self,
        recommendation: DebateRecommendation,
        analysis: DeepDebateAnalysis,
        *,
        model_id: str,
        prompt: str,
        sources: list[DebateSource],
    ) -> DebateRecommendation:
        points: list[str] = []
        for value in [*analysis.counterarguments, analysis.rebuttal, analysis.interpretation]:
            value = " ".join(value.split()).strip()
            if value and value not in points:
                points.append(value)
            if len(points) == 12:
                break
        followups = [
            ConditionalFollowUp(condition="Naechster Einwand", question=question)
            for question in analysis.followups[:2]
            if question.strip()
        ]
        counter_question = (
            followups[0].question if followups else recommendation.counter_question
        )
        updates = {
            "answer_now": analysis.best_reply or recommendation.answer_now,
            "counterargument": analysis.rebuttal
            or (points[0] if points else recommendation.counterargument),
            "counter_question": counter_question,
            "open_question": counter_question or recommendation.open_question,
            "follow_ups": followups or recommendation.follow_ups,
            "argument_points": points or recommendation.argument_points,
            "logical_relations": analysis.logical_relations,
            "confidence": "high" if sources else "medium",
            "needs_research": False,
            "research_status": (
                "completed" if sources else recommendation.research_status
            ),
            "sources": sources or recommendation.sources,
            "analysis_status": "completed",
            "analysis_can_cancel": False,
            "analyst_provider": self._analyst_provider_label(model_id),
            "analyst_model": model_id,
            "analyst_research_performed": bool(sources),
            "analyst_prompt": prompt,
        }
        return DebateRecommendation.model_validate({
            **recommendation.model_dump(),
            **updates,
        })

    def _remember_argument_context(self, recommendation: DebateRecommendation) -> None:
        if not getattr(self, "_argument_memory_enabled", True):
            return
        if not recommendation.target_claim.strip():
            return
        memory = getattr(self, "_argument_memory", None)
        if memory is None:
            memory = deque(maxlen=16)
            self._argument_memory = memory
        retained = [
            row for row in memory
            if row.get("claim_id") != recommendation.claim_id
        ]
        memory.clear()
        memory.extend(retained)
        row = {
            "claim_id": recommendation.claim_id,
            "target_claim": recommendation.target_claim,
            "open_question": recommendation.open_question
            or recommendation.counter_question,
            "revision": recommendation.recommendation_revision,
            "speaker_id": getattr(self, "_active_speaker_id", None),
            "speaker_name": getattr(self, "_active_speaker_name", None),
            "speaker_type": getattr(self, "_active_speaker_type", None),
        }
        memory.append(row)
        semantic_memory = getattr(self, "_semantic_argument_memory", None)
        if semantic_memory is not None:
            task = asyncio.create_task(
                asyncio.to_thread(semantic_memory.upsert, row),
                name=f"semantic-argument-upsert-{self.session_id}-{recommendation.claim_id}",
            )
            tasks = getattr(self, "_semantic_memory_tasks", None)
            if tasks is None:
                tasks = set()
                self._semantic_memory_tasks = tasks
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    def _derive_meeting_context(self):
        """Recompute the fields derived from meeting_type/meeting_context."""
        self.meeting_context_text = build_meeting_context_text(self.meeting_type, self.meeting_context)
        self._offering_matching_enabled = should_match_offerings(self.meeting_type)

    def _suppressed_analyst_types(self) -> set[str]:
        """Item types the analyst should not produce for this meeting type.

        Opportunity scouting only pays off when the offering specialist can
        enrich the result. On a meeting type where offering matching is off,
        the lens produced 57 of 199 insights on a measured call and every one
        carried an empty offering_match, so it is dropped from the prompt.
        """
        return set() if self._offering_matching_enabled else {"opportunity"}

    def update_meeting_context(self, meeting_type: str | None = None, meeting_context: str | None = None):
        """Apply a mid-call session context edit to the running text agents."""
        if meeting_type is not None:
            self.meeting_type = normalize_meeting_type(meeting_type)
        if meeting_context is not None:
            self.meeting_context = meeting_context
        self._derive_meeting_context()
        self.consolidated_agent.meeting_context_text = self.meeting_context_text
        self.consolidated_agent.set_suppressed_types(self._suppressed_analyst_types())
        self.objection_agent.update_meeting_context(self.meeting_context_text)
        self.objection_agent.update_debate_mode(
            debate_mode_for_meeting_type(self.meeting_type, self._default_debate_mode)
        )
        # If the type change turned offering matching on, the specialist may not be wired yet.
        self._wire_opportunity_specialist()
        if self._is_enabled("opportunity_specialist"):
            if self._offering_matching_enabled:
                asyncio.create_task(
                    self.activity.set_agent_state(
                        "opportunity_specialist",
                        "waiting",
                    )
                )
            else:
                asyncio.create_task(
                    self.activity.set_agent_state(
                        "opportunity_specialist",
                        "blocked",
                        blocked_reason="meeting_type",
                        remedy=(
                            "Runs for client/sales and customer delivery conversations; "
                            "change the conversation type to enable it."
                        ),
                    )
                )
        logger.info(
            f"[orchestrator] meeting context updated mid-call: type={self.meeting_type} "
            f"offering_matching={self._offering_matching_enabled}"
        )

    async def send_audio(self, pcm_data: bytes):
        if self._is_enabled("audio_gateway"):
            self._gateway_samples_sent += len(pcm_data) // 2
            await self.audio_gateway.send_audio(pcm_data)

    async def feed_transcript(
        self,
        text: str,
        speaker_name: str | None = None,
        speaker_id: str | None = None,
        speaker_type: str | None = None,
        utterance_id: str | None = None,
        is_local_mic: bool = False,
    ):
        self._mark_transcript_activity()
        if (
            getattr(self, "debate_settings", DebateSettings()).voice_commands_enabled
            and is_local_mic
            and speaker_type == "team"
        ):
            command = _parse_voice_command(text)
            if command:
                await self.send_directive(command)
                return True
        hypotheses = getattr(self, "_interim_debate_hypotheses", {})
        continued_utterance_id = (
            getattr(self, "_active_utterance_id", None)
            if hypotheses and not utterance_id
            else None
        )
        if utterance_id:
            hypotheses.pop(utterance_id, None)
        else:
            hypotheses.clear()
        self._active_utterance_id = (
            utterance_id or continued_utterance_id or uuid.uuid4().hex
        )
        finalized_segments = getattr(self, "_finalized_interim_segments", None)
        if finalized_segments is None:
            finalized_segments = set()
            self._finalized_interim_segments = finalized_segments
        finalized_segments.add(self._active_utterance_id)
        active_interim_segment_id = getattr(
            self, "_active_interim_segment_id", None
        )
        if active_interim_segment_id:
            finalized_segments.add(active_interim_segment_id)
        # Gateway partials often have no provider segment id, while the final
        # batch transcript uses TurnAssembler ids. Rotate the gateway segment
        # explicitly on every durable final so append replay cannot grow for
        # the whole call as one unbounded interim value.
        gateway_segment_id = getattr(self, "_gateway_segment_id", None)
        if gateway_segment_id:
            finalized_segments.add(gateway_segment_id)
            self._gateway_segment_start_sample = self._gateway_samples_sent
            self._gateway_segment_id = f"{self.capture_id}:{uuid.uuid4().hex}"
            self._active_interim_segment_id = self._gateway_segment_id
            self._gateway_segment_revision = 0
        self._active_claim_id = self._active_utterance_id
        self._active_claim_is_interim = False
        self._active_semantic_related_claim_ids = []
        self._active_speaker_id = speaker_id
        self._active_speaker_name = speaker_name
        self._active_speaker_type = speaker_type
        self._transcript_revision = getattr(self, "_transcript_revision", 0) + 1
        await self.transcript_buffer.add(
            text,
            speaker_name,
            speaker_id=speaker_id,
            speaker_type=speaker_type,
            utterance_id=self._active_utterance_id,
        )
        if self._stopped or not self._is_enabled("objection_handler"):
            return

        self._schedule_debate_revision()
        return False

    async def apply_manual_transcript_correction(
        self,
        *,
        text: str,
        speaker_name: str | None,
        speaker_id: str | None,
        speaker_type: str | None,
        utterance_id: str,
    ) -> bool:
        """Replace one live utterance and visibly retire its dependent card."""
        normalized = " ".join(text.split()).strip()
        if not normalized or not utterance_id:
            return False
        self._mark_transcript_activity()
        await self.transcript_buffer.add(
            normalized,
            speaker_name,
            speaker_id=speaker_id,
            speaker_type=speaker_type,
            utterance_id=utterance_id,
        )
        self._transcript_revision = getattr(self, "_transcript_revision", 0) + 1
        recommendation = self.objection_agent.latest_recommendation
        depends_on_utterance = utterance_id in {
            str(getattr(self, "_active_claim_id", "") or ""),
            str(recommendation.claim_id or ""),
            str(recommendation.utterance_id or ""),
        }
        if not depends_on_utterance:
            return False

        self._active_utterance_id = utterance_id
        self._active_claim_id = utterance_id
        self._active_claim_is_interim = False
        self._active_semantic_related_claim_ids = []
        self._active_speaker_id = speaker_id
        self._active_speaker_name = speaker_name
        self._active_speaker_type = speaker_type
        scheduler = getattr(self, "_external_analysis_scheduler", None)
        if scheduler is not None:
            scheduler.cancel_session(str(self.session_id))
        invalidated = recommendation.model_copy(update={
            "answer_now": "Transkript korrigiert - Empfehlung wird neu geprueft.",
            "counterargument": "",
            "counter_question": "",
            "analogy": "",
            "target_claim": normalized,
            "argument_points": [],
            "atomic_claims": [],
            "logical_relations": [],
            "confidence": "low",
            "needs_research": False,
            "research_query": "",
            "research_status": "cancelled",
            "research_alert": "Abhaengige Empfehlung wegen manueller Korrektur entwertet.",
            "sources": [],
            "analysis_status": "analyzing",
            "analysis_can_cancel": False,
            "generation_id": uuid.uuid4().hex,
            "claim_id": utterance_id,
            "utterance_id": utterance_id,
            "transcript_revision": self._transcript_revision,
            "claim_revision": self._transcript_revision,
            "recommendation_revision": 0,
        })
        await self._send_debate_update(
            getattr(self, "_debate_revision", 0),
            invalidated,
            origin="instant",
        )
        self._schedule_debate_revision()
        return True

    async def feed_interim_transcript(
        self,
        text: str,
        *,
        utterance_id: str | None = None,
        segment_revision: int | None = None,
    ) -> bool:
        """Use a useful live partial without persisting or duplicating it."""
        normalized = " ".join(text.split()).strip()
        filler = normalized.casefold().strip(" .,!?;:")
        if (
            self._stopped
            or not self._is_enabled("objection_handler")
            or len(normalized) < 2
            or filler in {"aeh", "aehm", "äh", "ähm", "hm", "mhm"}
        ):
            return False
        self._mark_transcript_activity()
        hypotheses = getattr(self, "_interim_debate_hypotheses", {})
        utterance_id = utterance_id or getattr(self, "_active_utterance_id", None) or uuid.uuid4().hex
        finalized_segments = getattr(self, "_finalized_interim_segments", set())
        if utterance_id in finalized_segments:
            return False
        if segment_revision is not None:
            previous_revision = self._interim_segment_revisions.get(utterance_id, -1)
            if segment_revision <= previous_revision:
                return False
            self._interim_segment_revisions[utterance_id] = segment_revision
        if hypotheses.get(utterance_id) == normalized:
            return False
        self._active_utterance_id = utterance_id
        self._active_claim_id = utterance_id
        self._active_claim_is_interim = True
        self._active_semantic_related_claim_ids = []
        self._interim_debate_hypotheses = {utterance_id: normalized[:500]}
        self._transcript_revision = getattr(self, "_transcript_revision", 0) + 1
        if getattr(self.debate_settings, "performance_profile", "balanced") == "economy":
            now = time.monotonic()
            if now - getattr(self, "_last_economy_interim_at", 0.0) < 1.5:
                return True
            self._last_economy_interim_at = now
        self._schedule_debate_revision()
        return True

    def _schedule_debate_revision(self) -> None:
        """Run only the newest latency-critical revision.

        A stale live call can otherwise occupy the provider and keep running
        until its response arrives. Before any useful partial is visible we
        still cancel it, which keeps fast providers responsive. After a
        speakable partial is visible we coalesce newer speech and let the
        current worker publish its complete answer before running the newest
        revision. This preserves a usable card during continuous speech.
        """
        self._debate_pending = True
        active_task = self._objection_task
        if active_task and not active_task.done():
            if getattr(self, "_debate_partial_visible", False):
                return
            active_task.cancel("newer transcript revision")
        self._debate_partial_visible = False
        self._objection_task = asyncio.create_task(
            self._run_debate_worker(),
            name=f"debate-copilot-{self.session_id}-worker",
        )

    async def _run_debate_worker(self) -> None:
        # Never cancel a useful response just because another 3-second caption
        # arrived. Publish it, then immediately analyze the coalesced latest text.
        while self._debate_pending and not self._stopped:
            self._debate_pending = False
            self._debate_partial_visible = False
            self._debate_revision += 1
            await self._run_debate_revision(
                self._debate_revision,
                claim_id=self._active_claim_id,
                transcript_revision=self._transcript_revision,
            )

    async def send_directive(self, text: str) -> bool:
        raw = " ".join(text.split()).strip()
        raw = re.sub(r"^debate\s*[- ]?ai\b[\s,:;-]*", "", raw, flags=re.IGNORECASE)
        folded = raw.casefold()
        if not folded:
            return False
        self._directive_revision = getattr(self, "_directive_revision", 0) + 1
        if "recherche" in folded and any(word in folded for word in ("aus", "stop", "pause")):
            await self.update_debate_research(False)
            return True
        if "recherche" in folded and any(word in folded for word in (" an", " ein", "start", "weiter")):
            await self.update_debate_research(True)
            return True
        if any(term in folded for term in ("extra high", "xhigh", "tiefenanalyse", "tief analys")):
            self._force_deep_analysis_once = True
        if any(term in folded for term in ("modus hart", "brutal sachlich", "hart-modus")):
            self.debate_settings = replace(self.debate_settings, mode="forceful")
            self.objection_agent.update_debate_mode("forceful")
        elif any(term in folded for term in ("modus ueberzeugen", "modus überzeugen", "ueberzeugen-modus", "überzeugen-modus")):
            self.debate_settings = replace(self.debate_settings, mode="persuasive")
            self.objection_agent.update_debate_mode("persuasive")
        if any(term in folded for term in ("faktencheck", "gegenbeleg", "zahlen pruefen", "zahlen prüfen", "statistik pruefen", "statistik prüfen")):
            if await self.request_debate_research("counterevidence"):
                return True
        elif any(term in folded for term in ("originalquelle", "originaltext", "quelle lesen")):
            if await self.request_debate_research("all"):
                return True
        normalized = _normalize_debate_control(raw)
        if not normalized:
            return False
        if normalized.startswith("[PLAYBOOK]"):
            self.directives = [
                directive
                for directive in self.directives
                if not directive.startswith("[PLAYBOOK]")
            ]
        self.directives.append(normalized)
        request_rescan = getattr(self.objection_agent, "request_rescan", None)
        if callable(request_rescan):
            request_rescan()
        self._schedule_debate_revision()
        return True

    async def update_debate_research(self, enabled: bool) -> None:
        """Apply the live auto-research switch without restarting the call."""
        self._directive_revision = getattr(self, "_directive_revision", 0) + 1
        self.debate_settings = replace(
            self.debate_settings,
            research_enabled=bool(enabled),
        )
        await self.websocket.send_json(
            {
                "type": "debate_research_control",
                "data": {"enabled": self.debate_settings.research_enabled},
            }
        )

    async def check_health(self) -> bool:
        if not self._is_enabled("audio_gateway"):
            return True
        if self._gateway_task is None:
            return False
        if self._gateway_task.done():
            exc = (
                self._gateway_task.exception()
                if not self._gateway_task.cancelled()
                else None
            )
            if exc:
                logger.warning("Audio Gateway died: %s", exc)
            else:
                logger.warning("Audio Gateway ended")
            return False
        return True

    def _unregister_live(self):
        # Guarded so a newer orchestrator registered for the same session survives.
        if _live_orchestrators.get(self.session_id) is self:
            del _live_orchestrators[self.session_id]

    async def _load_complete_transcript(self) -> str:
        """Load the durable full transcript for final/checkpoint analysis.

        The live ring buffer stays bounded for latency. At a final checkpoint
        the persisted rows are the source of truth, so long meetings do not
        silently lose older turns merely because the in-memory window rolled.
        """
        try:
            async with async_session() as db:
                rows = (
                    await db.execute(
                        select(TranscriptEntry)
                        .where(TranscriptEntry.session_id == self.session_id)
                        .order_by(TranscriptEntry.sequence)
                    )
                ).scalars().all()
        except Exception as exc:
            logger.warning("Complete transcript load failed; using live buffer: %s", exc)
            return await self.transcript_buffer.get_full(aliases=self.speaker_aliases())
        if not rows:
            return await self.transcript_buffer.get_full(aliases=self.speaker_aliases())
        aliases = self.speaker_aliases()
        names = {
            str(speaker.get("id") or ""): speaker_display_name(speaker)
            for speaker in self.speakers
        }
        lines = [
            format_transcript_segment(
                row.text,
                names.get(str(row.speaker_id or ""), "Unknown"),
                speaker_id=str(row.speaker_id) if row.speaker_id else None,
                alias=aliases.get(str(row.speaker_id or "")),
            )
            for row in rows
            if str(row.text or "").strip()
        ]
        return "\n".join(lines) or await self.transcript_buffer.get_full(aliases=aliases)

    async def close_all(self):
        self._stopped = True
        self._unregister_live()
        clear_synthesizer_state(self.session_id)

        # Stop cooldown subscribers
        if self._synth_subscriber:
            self._synth_subscriber.stop()
        if self._opp_specialist_subscriber:
            self._opp_specialist_subscriber.stop()
        self._event_bus.clear()

        # Cancel tasks
        for task in [
            self._consolidated_task,
            self._objection_task,
            self._gateway_task,
            self._strategic_signals_task,
            self._refiner_task,
        ]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        for task in list(self._research_tasks):
            if not task.done():
                task.cancel()
        if self._research_tasks:
            await asyncio.gather(*self._research_tasks, return_exceptions=True)
        self._research_tasks.clear()
        argument_tasks = list(getattr(self, "_argument_graph_tasks", set()))
        if argument_tasks:
            await asyncio.gather(*argument_tasks, return_exceptions=True)
        semantic_tasks = list(getattr(self, "_semantic_memory_tasks", set()))
        if semantic_tasks:
            await asyncio.gather(*semantic_tasks, return_exceptions=True)

        if self.audio_gateway:
            await self.audio_gateway.close()
        await self.activity.close()
        logger.info("Orchestrator shut down")

    async def graceful_drain(
        self,
        progress_callback: ProgressCallback | None = None,
        mode: str = DRAIN_MODE_FULL,
    ) -> dict[str, int | bool]:
        """Run the drain, keeping the client informed while a stage is slow.

        A single agent stage can run for minutes - one Gemini call hung nearly
        four on a malformed structured reply - and nothing crossed the socket
        while it did, so the client could not tell a working drain from a dead
        backend and gave up on it (ALP-171). Re-announcing the running stage on
        an interval gives the client something to wait on.
        """
        if progress_callback is None:
            return await self._run_drain_stages(None, mode)

        latest: dict[str, dict] = {}

        async def tracked(event: dict) -> None:
            latest["event"] = event
            await progress_callback(event)

        heartbeat = asyncio.create_task(_run_drain_heartbeat(progress_callback, latest))
        try:
            return await self._run_drain_stages(tracked, mode)
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except (asyncio.CancelledError, Exception):
                pass

    async def _run_drain_stages(
        self,
        progress_callback: ProgressCallback | None = None,
        mode: str = DRAIN_MODE_FULL,
    ) -> dict[str, int | bool]:
        """Run final text-agent passes before shutting down a live call.

        mode selects how much analysis runs (see drain_stages); per-agent
        enablement still applies within each mode.
        """
        self._stopped = True
        # Unregister up front: mid-drain context edits are pointless (loops are
        # stopping), and a drain error must not leave a dead entry in the registry.
        self._unregister_live()

        if self._synth_subscriber:
            self._synth_subscriber.stop()
        if self._opp_specialist_subscriber:
            self._opp_specialist_subscriber.stop()
        self._event_bus.clear()

        # No live audio responses may outlive the drain boundary. The gateway
        # is a consumer task, so stop it before final transcript/agent passes.
        if self._gateway_task and not self._gateway_task.done():
            self._gateway_task.cancel()
            try:
                await self._gateway_task
            except (asyncio.CancelledError, Exception):
                pass

        if self._consolidated_task and not self._consolidated_task.done():
            self._consolidated_task.cancel()
            try:
                await self._consolidated_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._objection_task and not self._objection_task.done():
            self._objection_task.cancel()
            try:
                await self._objection_task
            except (asyncio.CancelledError, Exception):
                pass
        for task in list(self._research_tasks):
            if not task.done():
                task.cancel()
        if self._research_tasks:
            await asyncio.gather(*self._research_tasks, return_exceptions=True)
        self._research_tasks.clear()
        argument_tasks = list(getattr(self, "_argument_graph_tasks", set()))
        if argument_tasks:
            await asyncio.gather(*argument_tasks, return_exceptions=True)
        if (
            self._strategic_signals_task
            and not self._strategic_signals_task.done()
        ):
            self._strategic_signals_task.cancel()
            try:
                await self._strategic_signals_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._refiner_task and not self._refiner_task.done():
            self._refiner_task.cancel()
            try:
                await self._refiner_task
            except (asyncio.CancelledError, Exception):
                pass

        result: dict = {
            "transcript_available": False,
            "insights_saved": 0,
            "synthesizer_ops": 0,
            "opportunity_ops": 0,
            # Stages that failed. The drain already degrades past a failure and
            # the call still finalizes, but until this was reported the client
            # saw only counts, so a failed briefing was indistinguishable from a
            # clean finish - and a slow one from a stranded call.
            "stage_errors": [],
        }
        debate_diagnostics = self._debate_diagnostics_summary()
        if debate_diagnostics["recommendations"]:
            result["debate_copilot"] = debate_diagnostics

        stages = self.drain_stages(mode)
        drain_total_steps = 2 + len(stages)
        if "call_briefing" in stages:
            result["synthesis_generated"] = False

        transcript_window = await self._load_complete_transcript()
        transcript_available = transcript_window != "(No recent transcript)"
        result["transcript_available"] = transcript_available

        await self._run_transcript_refinement_stage(
            stages,
            progress_callback,
            drain_total_steps,
            result,
        )
        if getattr(self, "_experimental_mode", False):
            # Refinement may have replaced durable rows; refresh the complete
            # transcript before final reasoning so earlier turns remain visible.
            transcript_window = await self._get_complete_transcript()
            transcript_available = transcript_window != "(No recent transcript)"
            result["transcript_available"] = transcript_available
        await self._run_final_insights_stage(
            stages,
            progress_callback,
            drain_total_steps,
            transcript_window,
            transcript_available,
            result,
        )
        await self._run_insight_reconciliation_stage(
            stages,
            progress_callback,
            drain_total_steps,
            result,
        )
        await self._run_opportunity_matching_stage(
            stages,
            progress_callback,
            drain_total_steps,
            result,
        )
        await self._run_call_briefing_stage(
            stages,
            progress_callback,
            drain_total_steps,
            result,
        )

        logger.info(
            "Graceful drain complete: "
            f"transcript={result['transcript_available']} "
            f"insights={result['insights_saved']} "
            f"synth_ops={result['synthesizer_ops']} "
            f"opp_ops={result['opportunity_ops']}"
        )
        return result

    async def _run_final_insights_stage(
        self,
        stages: list[str],
        progress_callback: ProgressCallback | None,
        drain_total_steps: int,
        transcript_window: str,
        transcript_available: bool,
        result: dict,
    ) -> None:
        if not (
            "final_insights" in stages
            and transcript_available
            and self._is_enabled("consolidated_analyst")
            and self.consolidated_agent.enabled_types
        ):
            return
        stage_step = 2 + stages.index("final_insights")
        await _emit_progress(
            progress_callback,
            "final_insights",
            "Running final insight pass...",
            stage_step,
            drain_total_steps,
            drain_progress_percent(stage_step, drain_total_steps),
        )
        await self.activity.cycle_started("consolidated_analyst")
        try:
            insights = await self.consolidated_agent.run_cycle(
                transcript_window=transcript_window,
                directives=self.directives,
                doc_summaries=self.doc_summaries,
                speakers=self.speakers,
                active_questions=self.active_questions,
                board_notes=self._board_stubs,
            )

            for insight in insights:
                agent_source = insight.get("agent_source", "consolidated_analyst")
                saved = await self._save_and_send_insight(insight, agent_source=agent_source)
                if saved:
                    result["insights_saved"] = int(result["insights_saved"]) + 1

            if insights:
                logger.info(f"[consolidated_analyst] final drain produced {len(insights)} insights")
            last_outcome = self.consolidated_agent.last_outcome or {}
            if last_outcome.get("kind") == "error":
                await self.activity.cycle_error(
                    "consolidated_analyst",
                    last_outcome["error"],
                )
            else:
                await self.activity.cycle_finished(
                    "consolidated_analyst",
                    saved_outcome(
                        last_outcome,
                        produced=len(insights),
                        saved=int(result["insights_saved"]),
                    ),
                )
        except Exception as e:
            logger.error(f"Final consolidated analyst drain error: {e}")
            result["stage_errors"].append(
                {"stage": "final_insights", "detail": str(e)}
            )
            await self.activity.cycle_error(
                "consolidated_analyst",
                classify_error(e, self._get_model("consolidated_analyst")),
            )

    async def _run_insight_reconciliation_stage(
        self,
        stages: list[str],
        progress_callback: ProgressCallback | None,
        drain_total_steps: int,
        result: dict,
    ) -> None:
        if (
            "insight_reconciliation" not in stages
            or not self._is_enabled("synthesizer")
        ):
            return
        stage_step = 2 + stages.index("insight_reconciliation")
        await _emit_progress(
            progress_callback,
            "insight_reconciliation",
            "Reconciling and enriching saved insights...",
            stage_step,
            drain_total_steps,
            drain_progress_percent(stage_step, drain_total_steps),
        )
        await self.activity.cycle_started("synthesizer")
        try:
            applied_ops = await run_synthesizer_cycle(
                self.session_id,
                model_override=self._get_model("synthesizer"),
                prompt_override=self._get_prompt("synthesizer") or None,
            )
            result["synthesizer_ops"] = len(applied_ops)
            await self._broadcast_operation_results(applied_ops)
            await self.activity.cycle_finished(
                "synthesizer",
                {
                    "kind": "insights" if applied_ops else "no_findings",
                    "detail": (
                        f"{len(applied_ops)} insight operations applied"
                        if applied_ops
                        else "No saved insight needed reconciliation."
                    ),
                    "items": len(applied_ops),
                },
            )
        except Exception as e:
            logger.error(f"Final synthesizer drain error: {e}")
            result["stage_errors"].append(
                {"stage": "insight_reconciliation", "detail": str(e)}
            )
            await self.activity.cycle_error(
                "synthesizer",
                classify_error(e, self._get_model("synthesizer")),
            )

    async def _run_opportunity_matching_stage(
        self,
        stages: list[str],
        progress_callback: ProgressCallback | None,
        drain_total_steps: int,
        result: dict,
    ) -> None:
        if (
            "opportunity_matching" not in stages
            or not self._is_enabled("opportunity_specialist")
            or not self._offering_matching_enabled
        ):
            return
        stage_step = 2 + stages.index("opportunity_matching")
        await _emit_progress(
            progress_callback,
            "opportunity_matching",
            "Matching opportunities to the offerings catalog...",
            stage_step,
            drain_total_steps,
            drain_progress_percent(stage_step, drain_total_steps),
        )
        await self.activity.cycle_started("opportunity_specialist")
        try:
            applied_ops = await run_opportunity_specialist_cycle(
                self.session_id,
                model_override=self._get_model("opportunity_specialist"),
                knowledge_source_ids=self._get_knowledge_source_ids(
                    "opportunity_specialist"
                ),
                prompt_override=self._get_prompt("opportunity_specialist") or None,
            )
            result["opportunity_ops"] = len(applied_ops)
            await self._broadcast_operation_results(applied_ops)
            await self.activity.cycle_finished(
                "opportunity_specialist",
                {
                    "kind": "insights" if applied_ops else "no_findings",
                    "detail": (
                        f"{len(applied_ops)} opportunity matches applied"
                        if applied_ops
                        else "No offering match was found."
                    ),
                    "items": len(applied_ops),
                },
            )
        except Exception as e:
            logger.error(f"Final opportunity specialist drain error: {e}")
            result["stage_errors"].append(
                {"stage": "opportunity_matching", "detail": str(e)}
            )
            await self.activity.cycle_error(
                "opportunity_specialist",
                classify_error(e, self._get_model("opportunity_specialist")),
            )

    async def _run_call_briefing_stage(
        self,
        stages: list[str],
        progress_callback: ProgressCallback | None,
        drain_total_steps: int,
        result: dict,
    ) -> None:
        if "call_briefing" not in stages:
            return
        stage_step = 2 + stages.index("call_briefing")
        await _emit_progress(
            progress_callback,
            "call_briefing",
            "Settling the call briefing...",
            stage_step,
            drain_total_steps,
            drain_progress_percent(stage_step, drain_total_steps),
        )
        briefing_slugs = [
            record["slug"]
            for record in self.activity.snapshot()["agents"]
            if record["trigger"] == "post_call"
            and record["state"] not in {"off", "blocked"}
        ]
        for slug in briefing_slugs:
            await self.activity.cycle_started(slug)
        try:
            synthesis = await run_session_synthesis(
                self.session_id,
                mode="post_call",
                agent_configs=self._agent_configs,
            )
            result["synthesis_generated"] = synthesis is not None
            if synthesis:
                await self._send_synthesis_update(synthesis)
            for slug in briefing_slugs:
                await self.activity.cycle_finished(
                    slug,
                    {
                        "kind": "insights" if synthesis else "no_findings",
                        "detail": (
                            "Call briefing generated."
                            if synthesis
                            else "No call briefing was generated."
                        ),
                        "items": 1 if synthesis else 0,
                    },
                )
        except Exception as e:
            logger.error(f"Final briefing synthesis error: {e}")
            result["stage_errors"].append(
                {"stage": "call_briefing", "detail": str(e)}
            )
            for slug in briefing_slugs:
                await self.activity.cycle_error(
                    slug,
                    classify_error(e, self._get_model(slug)),
                )

    # ── Audio Gateway (silent listener) ──────────────────────────────────

    async def _handle_gateway_responses(self):
        """Relay input_transcription from the audio gateway to the frontend."""
        async for event in self.audio_gateway.receive_responses():
            if event["type"] == "transcript":
                text = str(event["data"])
                mode = str(event.get("mode") or "append")
                if self._gateway_segment_id in self._finalized_interim_segments:
                    self._gateway_segment_start_sample = self._gateway_samples_sent
                    self._gateway_segment_id = uuid.uuid4().hex
                    self._gateway_segment_revision = 0
                self._gateway_segment_revision += 1
                event_segment_id = str(event.get("segment_id") or "")
                segment_id = (
                    event_segment_id
                    if event_segment_id
                    and event_segment_id not in self._finalized_interim_segments
                    else self._gateway_segment_id
                )
                self._active_interim_segment_id = segment_id
                segment_revision = int(
                    event.get("segment_revision")
                    if event_segment_id == segment_id and event.get("segment_revision")
                    else self._gateway_segment_revision
                )
                track_id = str(event.get("track_id") or "mixed")
                event_audio_start = event.get("audio_start_sample")
                event_audio_end = event.get("audio_end_sample")
                audio_start_sample = int(
                    self._gateway_segment_start_sample
                    if event_audio_start is None
                    else event_audio_start
                )
                audio_end_sample = int(
                    self._gateway_samples_sent
                    if event_audio_end is None
                    else event_audio_end
                )
                try:
                    await self.websocket.send_json({
                        "type": "interim_transcript",
                        "data": {
                            "text": text,
                            "mode": mode,
                            "track_id": track_id,
                            "segment_id": segment_id,
                            "segment_revision": segment_revision,
                            "audio_start_sample": audio_start_sample,
                            "audio_end_sample": audio_end_sample,
                            "sample_rate": 16000,
                            "final": False,
                        },
                    })
                except Exception:
                    pass
                await self.feed_interim_transcript(
                    text,
                    utterance_id=segment_id,
                    segment_revision=segment_revision,
                )

    # ── Save + broadcast (shared by all agents) ─────────────────────────

    async def _save_and_send_insight(self, q_json: dict, agent_source: str) -> bool:
        """Save a new insight. Returns True if saved (not deduped)."""
        if "question" not in q_json:
            return False

        # Scrub before anything reads the text, so dedup compares what will
        # actually be stored: a tag in one cycle and the same person's name in
        # the next would otherwise look like two different insights.
        scrub = self._alias_prose_scrub()
        if scrub:
            for field in ("question", "rationale", "source_context"):
                value = q_json.get(field)
                if isinstance(value, str) and value:
                    q_json[field] = replace_speaker_labels(value, scrub)

        text = q_json["question"]

        # Dedup check
        now = time.time()
        self._recent_insights = {
            k: v for k, v in self._recent_insights.items()
            if now - v < _DEDUP_WINDOW_SECONDS
        }
        for existing_text in self._recent_insights:
            if _texts_similar(text, existing_text):
                logger.info(f"[{agent_source}] Skipping near-duplicate: {text[:60]}")
                return False
        # Do not reserve the fingerprint until the database transaction
        # has committed. A transient DB failure must remain retryable.
        # Use agent_source from the insight dict if provided (consolidated analyst sets per-type)
        effective_source = q_json.get("agent_source", agent_source)
        speaker_id = self._validated_speaker_id(q_json.get("speaker_id"))

        async with async_session() as db:
            directive_id = None
            directive_source = q_json.get("directive_source")
            if directive_source:
                result = await db.execute(
                    select(Directive.id).where(
                        Directive.session_id == self.session_id,
                        Directive.text == directive_source,
                    )
                )
                directive_id = result.scalar_one_or_none()

            question = Question(
                session_id=self.session_id,
                item_type=q_json.get("item_type", "question"),
                lens_label=str(q_json.get("lens_label") or "")[:120],
                question=text,
                rationale=q_json.get("rationale", ""),
                source_context=q_json.get("source_context", ""),
                speaker_id=uuid.UUID(speaker_id) if speaker_id else None,
                directive_id=directive_id,
                agent_source=effective_source,
            )
            db.add(question)
            await db.commit()
            await db.refresh(question)
            self._recent_insights[text] = now

            if question.item_type == "question":
                self._remember_active_question(str(question.id), question.question, question.item_type)
            else:
                self._remember_board_stub(question.item_type, question.question)

            try:
                await self.websocket.send_json({
                    "type": "question",
                    "data": {
                        "id": str(question.id),
                        "item_type": question.item_type,
                        "lens_label": question.lens_label,
                        "question": question.question,
                        "rationale": question.rationale,
                        "source_context": question.source_context,
                        "speaker_id": speaker_id,
                        "directive_id": str(question.directive_id) if question.directive_id else None,
                        "is_followup": False,
                        "timestamp": question.created_at.isoformat(),
                        "agent_source": effective_source,
                        "offering_match": "",
                        "enhanced": False,
                    },
                })
            except Exception as e:
                logger.info(f"[{effective_source}] Insight saved but websocket broadcast failed: {e}")

            return True

    async def _send_signal_insights(self, signal_rows: dict | None) -> int:
        """Push this cycle's signal insight rows to the browser.

        New rows arrive as ordinary insights; a signal that aged into history,
        or came back, arrives as an update to the row already on screen.
        """
        if not signal_rows:
            return 0

        created = signal_rows.get("created") or []
        updated = signal_rows.get("updated") or []
        for row in created:
            self._remember_board_stub(
                str(row.get("item_type") or "signal"),
                str(row.get("question") or row.get("text") or ""),
            )
        for message_type, rows in (("question", created), ("insight_updated", updated)):
            for row in rows:
                try:
                    await self.websocket.send_json({"type": message_type, "data": row})
                except Exception as e:
                    logger.info(f"[strategic_signals] signal insight broadcast failed: {e}")
                    return len(created)
        return len(created)

    def speaker_aliases(self) -> dict[str, str]:
        """The participant tags for this call, derived fresh from the roster.

        Not cached: the roster is appended to mid-call when a new voice is
        enrolled, and an append can only add a tag, never move one. Deriving
        on read is what makes the map identical across a resume without
        anything being stored (ALP-282).
        """
        return build_speaker_aliases(self.speakers)

    def _validated_speaker_id(self, raw: object) -> str | None:
        """Keep insight attribution tied to the session speaker roster.

        Deliberately UUID-only. The agents translate a participant tag back to
        a UUID before anything reaches here, so the save boundary's contract
        is unchanged by aliasing.
        """
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            speaker_id = str(uuid.UUID(raw.strip()))
        except ValueError:
            return None
        known_ids = {str(s.get("id")) for s in self.speakers if s.get("id")}
        return speaker_id if speaker_id in known_ids else None

    def _alias_prose_scrub(self) -> dict[str, str]:
        """Participant tag -> the person's name, for insight text.

        Aliases put "S1"-style vocabulary in the model's context, and the
        prompts already have to forbid invented labels like "Speaker 1/Mark"
        from leaking into insight prose. The prompt rule is the first line of
        defense; this is the deterministic one, so a tag can never reach a
        card a person reads (ALP-282).
        """
        aliases = self.speaker_aliases()
        by_id = {str(s.get("id")): s for s in self.speakers if s.get("id")}
        return {
            alias: speaker_display_name(by_id[speaker_id])
            for speaker_id, alias in aliases.items()
            if speaker_id in by_id
        }

    # ── Consolidated Analyst (single batch call) ─────────────────────────

    async def _consolidated_agent_loop(self):
        """Run consolidated analyst on interval."""
        interval = self._get_interval("consolidated_analyst", settings.TEXT_AGENT_INTERVAL_SECONDS)
        # Run immediately when a session already has transcript context; the
        # interval is the delay between subsequent cycles, not startup latency.

        last_window = ""
        while not self._stopped:
            await self.activity.cycle_started("consolidated_analyst")
            try:
                transcript_window = await self.transcript_buffer.get_window(
                    aliases=self.speaker_aliases()
                )
                if transcript_window == "(No recent transcript)":
                    logger.debug("[consolidated_analyst] No transcript yet, skipping cycle")
                    await self.activity.cycle_finished(
                        "consolidated_analyst",
                        {
                            "kind": "skipped_no_transcript",
                            "detail": "Nothing to analyze yet.",
                            "items": 0,
                        },
                    )
                    await asyncio.sleep(interval)
                    continue
                # Nobody spoke since the last cycle: the model has already read
                # exactly this window, so re-reading it buys nothing. Mirrors the
                # guard the objection handler has always had.
                if transcript_window == last_window:
                    logger.debug("[consolidated_analyst] Window unchanged, skipping cycle")
                    await asyncio.sleep(interval)
                    continue
                logger.info(f"[consolidated_analyst] Running cycle with {len(transcript_window)} chars of transcript")
                insights = await self.consolidated_agent.run_cycle(
                    transcript_window=transcript_window,
                    directives=self.directives,
                    doc_summaries=self.doc_summaries,
                    speakers=self.speakers,
                    active_questions=self.active_questions,
                )

                saved_count = 0
                for insight in insights:
                    agent_source = insight.get("agent_source", "consolidated_analyst")
                    saved = await self._save_and_send_insight(insight, agent_source=agent_source)
                    if saved:
                        saved_count += 1
                        item_type = insight.get("item_type", "")
                        self._event_bus.publish("new_insight", {
                            "item_type": item_type,
                            "agent_source": agent_source,
                        })
                        if item_type == "opportunity" and self._offering_matching_enabled:
                            self._event_bus.publish("new_opportunity", {
                                "agent_source": agent_source,
                            })

                if insights:
                    logger.info(f"[consolidated_analyst] produced {len(insights)} insights")
                last_outcome = self.consolidated_agent.last_outcome or {}
                if last_outcome.get("kind") == "error":
                    await self.activity.cycle_error(
                        "consolidated_analyst",
                        last_outcome["error"],
                    )
                else:
                    await self.activity.cycle_finished(
                        "consolidated_analyst",
                        saved_outcome(
                            last_outcome,
                            produced=len(insights),
                            saved=saved_count,
                        ),
                    )
                    # Advance only after the complete cycle succeeded. A
                    # transient model or persistence failure must be retried
                    # against the same transcript window.
                    last_window = transcript_window

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consolidated analyst loop error: {e}")
                await self.activity.cycle_error(
                    "consolidated_analyst",
                    classify_error(e, self._get_model("consolidated_analyst")),
                )

            await asyncio.sleep(interval)

    async def _send_debate_update(
        self,
        revision: int,
        recommendation: DebateRecommendation,
        *,
        latency_ms: int | None = None,
        origin: str = "model",
    ) -> None:
        """Push the latest speakable recommendation without coupling it to DB work."""
        active_claim_id = str(getattr(self, "_active_claim_id", "") or "")
        current_transcript_revision = int(getattr(self, "_transcript_revision", 0))
        explicit_revision = max(
            int(recommendation.transcript_revision or 0),
            int(recommendation.claim_revision or 0),
        )
        existing = getattr(self.objection_agent, "latest_recommendation", None)
        existing_revision = max(
            int(getattr(existing, "transcript_revision", 0) or 0),
            int(getattr(existing, "claim_revision", 0) or 0),
        )
        same_claim_visible_card = bool(
            recommendation.claim_id
            and active_claim_id
            and recommendation.claim_id == active_claim_id
            and bool(getattr(self, "_active_claim_is_interim", False))
            and origin in {"model", "model_stream"}
            and (
                not existing
                or str(getattr(existing, "claim_id", "") or "") != active_claim_id
                or existing_revision <= explicit_revision
            )
        )
        if (
            (recommendation.claim_id and active_claim_id and recommendation.claim_id != active_claim_id)
            or (
                explicit_revision
                and current_transcript_revision
                and explicit_revision < current_transcript_revision
                and not same_claim_visible_card
            )
        ):
            logger.debug(
                "Discarded stale debate update claim=%s revision=%s current_claim=%s current_revision=%s",
                recommendation.claim_id,
                explicit_revision,
                active_claim_id,
                current_transcript_revision,
            )
            return
        self._recommendation_revision = getattr(self, "_recommendation_revision", 0) + 1
        recommendation = recommendation.model_copy(
            update={
                "session_id": recommendation.session_id or str(self.session_id),
                "claim_id": recommendation.claim_id
                or getattr(self, "_active_claim_id", None)
                or f"claim-{revision}",
                "utterance_id": recommendation.utterance_id
                or getattr(self, "_active_utterance_id", None)
                or "",
                "transcript_revision": recommendation.transcript_revision or revision,
                "claim_revision": recommendation.claim_revision
                or recommendation.transcript_revision
                or int(getattr(self, "_transcript_revision", revision)),
                "directive_revision": recommendation.directive_revision
                or int(getattr(self, "_directive_revision", 0)),
                "config_generation": recommendation.config_generation
                or create_configuration_snapshot().generation,
                "generation_id": recommendation.generation_id or uuid.uuid4().hex,
                "recommendation_revision": self._recommendation_revision,
            }
        )
        if not recommendation.atomic_claims:
            recommendation = recommendation.model_copy(update={
                "atomic_claims": build_atomic_claims(
                    recommendation,
                    parent_claim_id=recommendation.claim_id,
                    speaker_id=str(getattr(self, "_active_speaker_id", "") or ""),
                )
            })
        if recommendation.sources:
            atomic_ids = [claim.id for claim in recommendation.atomic_claims]
            bound_sources = [
                source.model_copy(update={
                    "claim_id": source.claim_id or recommendation.claim_id,
                    "claim_revision": source.claim_revision or recommendation.claim_revision,
                    "transcript_revision": source.transcript_revision or recommendation.transcript_revision,
                    "affected_claim_ids": source.affected_claim_ids or atomic_ids,
                    "affected_claims": source.affected_claims or [claim.text for claim in recommendation.atomic_claims],
                })
                for source in recommendation.sources
            ]
            if recommendation.pipeline_mode == "experimental_debateai":
                bound_sources = _annotate_experimental_sources(
                    bound_sources,
                    target_claim=recommendation.target_claim,
                )
            recommendation = recommendation.model_copy(update={"sources": bound_sources})
        self.objection_agent.latest_recommendation = recommendation
        payload = recommendation.model_dump(mode="json")
        payload.update(
            {
                # Evidence packets from completed experimental lanes are retained
                # beside the revision-addressed claim record. They are metadata
                # and structured findings only; the visible answer remains local.
                **(
                    {
                        "external_lane_artifacts": list(
                            getattr(self, "_experimental_lane_artifacts", [])
                        )
                    }
                    if recommendation.pipeline_mode == "experimental_debateai"
                    else {}
                ),
                # Legacy clients use revision; keep it monotonic with the actual
                # visible card revision instead of the model request revision.
                "revision": self._recommendation_revision,
                "origin": origin,
                "generated_at": datetime.now(UTC).isoformat(),
                "latency_ms": latency_ms,
                "speaker_id": getattr(self, "_active_speaker_id", None),
                "speaker_name": getattr(self, "_active_speaker_name", None),
                "speaker_type": getattr(self, "_active_speaker_type", None),
                "semantic_related_claim_ids": list(
                    getattr(self, "_active_semantic_related_claim_ids", [])
                ),
            }
        )
        if origin in {"model", "research"}:
            self._remember_argument_context(recommendation)
        diagnostic_fields = {
            "revision": revision,
            "recommendation_revision": self._recommendation_revision,
            "transcript_revision": recommendation.transcript_revision,
            "claim_id": recommendation.claim_id,
            "utterance_id": recommendation.utterance_id,
            "origin": origin,
            "prompt_version": recommendation.prompt_version,
            "answer_words": len(recommendation.answer_now.split()),
            "question_words": len(recommendation.counter_question.split()),
            "answer_now": recommendation.answer_now,
            "counterargument": recommendation.counterargument,
            "counter_question": recommendation.counter_question,
            "analogy": recommendation.analogy,
            "primary_move": recommendation.primary_move,
            "question_status": recommendation.question_status,
            "target_claim": recommendation.target_claim,
            "argument_points": list(recommendation.argument_points),
            "confidence": recommendation.confidence,
            "research_status": recommendation.research_status,
            "research_alert": recommendation.research_alert,
            "sources": [source.model_dump(mode="json") for source in recommendation.sources],
            "analysis_status": recommendation.analysis_status,
            "analyst_provider": recommendation.analyst_provider,
            "analyst_model": recommendation.analyst_model,
            "analyst_research_performed": recommendation.analyst_research_performed,
            "analyst_prompt": recommendation.analyst_prompt,
        }
        diagnostics = getattr(self, "_debate_diagnostics", None)
        if diagnostics is None:
            diagnostics = []
            self._debate_diagnostics = diagnostics
        if latency_ms is not None:
            diagnostics.append({**diagnostic_fields, "latency_ms": latency_ms})
            del diagnostics[:-20]
            logger.info(
                "[debate_copilot] revision=%s latency_ms=%s answer_words=%s question_words=%s",
                revision,
                latency_ms,
                len(recommendation.answer_now.split()),
                len(recommendation.counter_question.split()),
            )
        else:
            # Research is deliberately slower and has no first-response latency of
            # its own. Merge its final, source-backed state into the measured sample
            # for this revision so post-call review sees what the user actually saw.
            existing = next(
                (
                    sample
                    for sample in reversed(diagnostics)
                    if sample.get("revision") == revision
                ),
                None,
            )
            if existing is not None:
                existing.update(diagnostic_fields)
        try:
            await self.websocket.send_json({"type": "debate_update", "data": payload})
        except Exception as exc:  # A closed socket must not strand persistence.
            logger.debug("Debate update socket closed: %s", exc)
        if recommendation.pipeline_mode == "experimental_debateai":
            try:
                experimental_payload = build_experimental_update(
                    recommendation,
                    external_insight_count=len(recommendation.sources),
                ).model_dump(mode="json")
                # The dedicated event carries a full recommendation snapshot too.
                # Preserve the incremental evidence packets there so its
                # backwards-compatible reducer cannot erase lane blobs that the
                # preceding debate_update already exposed.
                if recommendation.pipeline_mode == "experimental_debateai":
                    experimental_payload.setdefault("recommendation", {})[
                        "external_lane_artifacts"
                    ] = list(getattr(self, "_experimental_lane_artifacts", []))
                await self.websocket.send_json({
                    "type": "experimental_debate_update",
                    "data": experimental_payload,
                })
            except Exception as exc:
                # A malformed optional event must never suppress the legacy
                # debate_update that old clients already received.
                logger.warning("Experimental debate event could not be emitted: %s", exc)
        if getattr(self, "_argument_graph_enabled", False):
            task = asyncio.create_task(
                self._persist_argument_recommendation(payload),
                name=f"argument-graph-{self.session_id}-{self._recommendation_revision}",
            )
            tasks = getattr(self, "_argument_graph_tasks", None)
            if tasks is None:
                tasks = set()
                self._argument_graph_tasks = tasks
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    async def apply_source_correction(
        self,
        *,
        claim_id: str,
        source_url: str,
        relation: str,
        affected_claim_ids: list[str],
    ) -> bool:
        recommendation = self.objection_agent.latest_recommendation
        if recommendation.claim_id != claim_id:
            return False
        changed = False
        sources = []
        for source in recommendation.sources:
            if source.url.rstrip("/") == source_url.rstrip("/"):
                if (
                    relation in {"supports", "contradicts"}
                    and (
                        source.retrieval_status != "read"
                        or not source.passage.strip()
                    )
                ):
                    return False
                source = source.model_copy(update={
                    "claim_relation": relation,
                    "verification_status": relation,
                    "affected_claim_ids": affected_claim_ids,
                })
                changed = True
            sources.append(source)
        if not changed:
            return False
        await self._send_debate_update(
            recommendation.transcript_revision,
            recommendation.model_copy(update={
                "sources": sources,
                "research_alert": "Quellenzuordnung wurde manuell korrigiert.",
            }),
            origin="research",
        )
        return True

    async def _persist_argument_recommendation(self, payload: dict) -> None:
        try:
            await persist_argument_recommendation(self.session_id, payload)
        except Exception as exc:
            # The live card is latency-critical; durable memory degrades without
            # ever delaying or suppressing the response the user is reading.
            logger.warning("Argument graph persistence failed: %s", exc)

    def _debate_diagnostics_summary(self) -> dict[str, object]:
        samples = list(getattr(self, "_debate_diagnostics", []))
        latencies = [int(item.get("latency_ms", 0)) for item in samples]
        answer_words = [int(item.get("answer_words", 0)) for item in samples]
        question_words = [int(item.get("question_words", 0)) for item in samples]
        count = len(samples)
        return {
            "recommendations": count,
            "average_latency_ms": round(sum(latencies) / count) if count else 0,
            "maximum_latency_ms": max(latencies, default=0),
            "average_answer_words": round(sum(answer_words) / count, 1) if count else 0,
            "average_question_words": round(sum(question_words) / count, 1) if count else 0,
            "samples": samples,
        }

    def acknowledge_debate_update(
        self,
        *,
        claim_id: str,
        recommendation_revision: int,
    ) -> bool:
        """Record that React committed the exact card; no transcript text is logged."""
        sample = next(
            (
                item
                for item in reversed(getattr(self, "_debate_diagnostics", []))
                if item.get("claim_id") == claim_id
                and item.get("recommendation_revision") == recommendation_revision
            ),
            None,
        )
        if sample is None:
            return False
        sample["ui_acknowledged"] = True
        sample["ui_acknowledged_at"] = datetime.now(UTC).isoformat()
        return True

    async def select_experimental_option(
        self,
        *,
        claim_id: str,
        recommendation_revision: int,
        option_id: str,
    ) -> bool:
        """Apply a deliberate experimental response choice to the visible card."""
        recommendation = self.objection_agent.latest_recommendation
        if (
            getattr(self, "_experimental_mode", False) is not True
            or not claim_id
            or recommendation.pipeline_mode != "experimental_debateai"
            or recommendation.claim_id != claim_id
            or recommendation.recommendation_revision != recommendation_revision
            or not option_id
        ):
            return False
        options = []
        selected_item = None
        for option in recommendation.strategy_options:
            if str(option.get("id") or "") == option_id:
                selected_item = option
            options.append({**option, "selected": str(option.get("id") or "") == option_id})
        if selected_item is None or not str(selected_item.get("text") or "").strip():
            return False
        selected_kind = str(selected_item.get("kind") or "")
        selected_text = " ".join(str(selected_item.get("text") or "").split())
        updated = recommendation.model_copy(update={
            "strategy_options": options,
            "selected_strategy_id": option_id,
            "answer_now": selected_text,
            "primary_move": "question" if selected_kind == "counter_question" else "answer",
            "selection_reason": "Vom Nutzer als passendster Antwortzug ausgewählt.",
        })
        await self._send_debate_update(
            recommendation.transcript_revision or self._debate_revision,
            updated,
            origin="user_selection",
        )
        return True

    async def confirm_good_debate_answer(
        self,
        *,
        claim_id: str,
        recommendation_revision: int,
    ) -> bool:
        """Persist only a recommendation the user explicitly marked as good."""
        recommendation = self.objection_agent.latest_recommendation
        if (
            not claim_id
            or recommendation.claim_id != claim_id
            or recommendation.recommendation_revision != recommendation_revision
            or not recommendation.target_claim.strip()
            or not recommendation.answer_now.strip()
        ):
            return False
        async with async_session() as db:
            from app.services.debate_settings import get_debate_settings

            current_settings = await get_debate_settings(db)
            if (
                not current_settings.learning_examples_enabled
                or not current_settings.transcript_retention_enabled
            ):
                return False
            example = await save_good_debate_example(
                db,
                claim=recommendation.target_claim,
                answer=recommendation.answer_now,
                counterargument=recommendation.counterargument,
                mode=getattr(self.objection_agent, "_debate_mode", ""),
                style_focus=getattr(self.objection_agent, "_style_focus", ""),
                evidence_sources=[source.url for source in recommendation.sources],
                context=(self.meeting_context or "")[:700],
            )
            await db.commit()
        row = {
            "claim_id": f"good:{example.id}",
            "target_claim": example.claim,
            "good_answer": example.answer,
            "counterargument": example.counterargument,
            "mode": example.mode,
            "style_focus": example.style_focus,
        }
        self._good_answer_examples.append(row)
        semantic_memory = getattr(self, "_semantic_argument_memory", None)
        if semantic_memory is not None:
            task = asyncio.create_task(
                asyncio.to_thread(semantic_memory.upsert, row),
                name=f"semantic-good-answer-{self.session_id}-{example.id}",
            )
            self._semantic_memory_tasks.add(task)
            task.add_done_callback(self._semantic_memory_tasks.discard)
        return True

    async def revoke_good_debate_answer(
        self,
        *,
        example_id: str,
        correction: str = "",
    ) -> bool:
        """Revoke one learned example so retrieval cannot reuse it."""
        if not example_id:
            return False
        async with async_session() as db:
            changed = await revoke_good_debate_example(
                db, example_id, correction=correction
            )
            if changed:
                await db.commit()
        if not changed:
            return False
        claim_id = f"good:{example_id}"
        self._good_answer_examples = [
            row for row in self._good_answer_examples
            if row.get("claim_id") != claim_id
        ]
        semantic_memory = getattr(self, "_semantic_argument_memory", None)
        if semantic_memory is not None:
            semantic_memory.remove(claim_id)
        return True

    def _new_analysis_context(
        self,
        revision: int,
        *,
        generation_id: str | None = None,
    ) -> AnalysisJobContext:
        return AnalysisJobContext(
            session_id=str(self.session_id),
            claim_id=str(getattr(self, "_active_claim_id", None) or f"claim-{revision}"),
            claim_revision=int(getattr(self, "_transcript_revision", revision)),
            directive_revision=int(getattr(self, "_directive_revision", 0)),
            config_generation=create_configuration_snapshot().generation,
            generation_id=generation_id or uuid.uuid4().hex,
        )

    def _remember_topic_knowledge(
        self,
        context: AnalysisJobContext,
        recommendation: DebateRecommendation,
        sources: list[DebateSource],
        *,
        analysis: DeepDebateAnalysis | None = None,
    ) -> None:
        """Retain revision-addressed facts without adopting a stale speaking line."""
        if not sources and analysis is None:
            return
        store = getattr(self, "_topic_knowledge", None)
        if store is None:
            store = {}
            self._topic_knowledge = store
        previous = store.get(context.claim_id)
        if previous and int(previous.get("claim_revision") or 0) > context.claim_revision:
            return
        findings: list[str] = []
        if analysis is not None:
            for value in (
                *analysis.counterarguments,
                analysis.interpretation,
                analysis.rebuttal,
            ):
                clean = " ".join(str(value or "").split()).strip()
                if clean and clean not in findings:
                    findings.append(clean)
                if len(findings) == 4:
                    break
        store[context.claim_id] = {
            "claim_id": context.claim_id,
            "claim_revision": context.claim_revision,
            "target_claim": recommendation.target_claim,
            "sources": [source.model_dump(mode="json") for source in sources],
            "findings": findings,
        }

    def _analysis_context_is_current(
        self,
        context: AnalysisJobContext,
        *,
        allow_newer_revision_same_claim: bool = False,
    ) -> bool:
        active_claim_id = getattr(self, "_active_claim_id", None)
        current_revision = int(
            getattr(self, "_transcript_revision", context.claim_revision)
        )
        revision_is_current = context.claim_revision == current_revision
        if allow_newer_revision_same_claim:
            if active_claim_id:
                revision_is_current = (
                    context.claim_revision <= current_revision
                    and context.claim_id == str(active_claim_id)
                )
            # Before the first persisted claim exists, the exact transcript
            # revision is still authoritative. Requiring an active claim here
            # would discard the initial live partial and its saved objection.
        return bool(
            not self._stopped
            and context.session_id == str(self.session_id)
            and (not active_claim_id or context.claim_id == str(active_claim_id))
            and revision_is_current
            and context.directive_revision == int(
                getattr(self, "_directive_revision", 0)
            )
            and context.config_generation == create_configuration_snapshot().generation
        )

    @staticmethod
    def _research_group_query_key(query: str) -> str:
        return " ".join(str(query or "").casefold().split())[:500]

    def _research_group_key(
        self,
        context: AnalysisJobContext,
        query: str,
    ) -> tuple[str, int, int, int, str]:
        return (
            str(context.claim_id),
            int(context.claim_revision),
            int(context.directive_revision),
            int(context.config_generation),
            self._research_group_query_key(query),
        )

    def _active_research_group(
        self,
        key: tuple[str, int, int, int, str],
    ) -> asyncio.Task | None:
        groups = getattr(self, "_research_group_tasks", None)
        if groups is None:
            groups = {}
            self._research_group_tasks = groups
        task = groups.get(key)
        if task is not None and not task.done():
            return task
        if task is not None:
            groups.pop(key, None)
        return None

    def _register_research_group(
        self,
        key: tuple[str, int, int, int, str],
        task: asyncio.Task,
    ) -> asyncio.Task:
        groups = getattr(self, "_research_group_tasks", None)
        if groups is None:
            groups = {}
            self._research_group_tasks = groups
        groups[key] = task

        def discard(completed: asyncio.Task) -> None:
            if groups.get(key) is completed:
                groups.pop(key, None)

        task.add_done_callback(discard)
        return task

    def _register_research_task(
        self,
        task: asyncio.Task,
        *,
        generation_id: str,
        manual: bool,
    ) -> asyncio.Task:
        self._research_tasks.add(task)
        if manual:
            manual_tasks = getattr(self, "_manual_analysis_tasks", None)
            if manual_tasks is None:
                manual_tasks = {}
                self._manual_analysis_tasks = manual_tasks
            manual_tasks[generation_id] = task

        def discard(completed: asyncio.Task) -> None:
            self._research_tasks.discard(completed)
            manual_tasks = getattr(self, "_manual_analysis_tasks", {})
            if manual_tasks.get(generation_id) is completed:
                manual_tasks.pop(generation_id, None)

        task.add_done_callback(discard)
        task.analysis_generation_id = generation_id
        task.manual_analysis = manual
        return task

    def _maybe_schedule_research(
        self,
        revision: int,
        recommendation: DebateRecommendation,
    ) -> asyncio.Task | None:
        """Start optional research without ever delaying the immediate guidance."""
        debate_settings = getattr(self, "debate_settings", DebateSettings())
        query = recommendation.research_query.strip()
        model_ids = self._external_analysis_models()
        manual = bool(getattr(self, "_force_deep_analysis_once", False))
        is_new_topic = not bool(
            getattr(self, "_active_semantic_related_claim_ids", [])
        )
        has_numeric_fact = bool(re.search(r"\b\d+(?:[.,]\d+)?\b", recommendation.target_claim))
        if (
            not debate_settings.research_enabled
            or debate_settings.performance_profile == "economy"
            or self.local_only
            or not model_ids
            or not recommendation.target_claim.strip()
            or (
                len(recommendation.target_claim.split()) < 5
                and not recommendation.needs_research
            )
            or (
                recommendation.needs_research
                and query
                and not is_safe_research_query(query)
            )
            or revision != self._debate_revision
            or (
                not manual
                and not is_new_topic
                and not recommendation.needs_research
                and not has_numeric_fact
            )
        ):
            return None

        if (
            not manual
            and getattr(self, "_active_claim_is_interim", False)
            and (
                self._last_transcript_activity_at is None
                or time.monotonic() - self._last_transcript_activity_at
                < AUTOMATIC_RESEARCH_STABILITY_SECONDS
            )
        ):
            # Interim speech is still changing. Wait for a later stable
            # revision or the final transcript checkpoint before spending an
            # external provider call; explicit manual research remains allowed.
            return None

        cached = query in self._research_cache
        now = time.monotonic()
        if (
            not cached
            and self._last_research_at
            and now - self._last_research_at < debate_settings.cooldown_seconds
        ):
            return None
        if not cached:
            self._last_research_at = now

        self._force_deep_analysis_once = False
        context = self._new_analysis_context(revision)
        group_key = self._research_group_key(context, query)
        existing = self._active_research_group(group_key)
        if existing is not None:
            return existing
        task = asyncio.create_task(
            self._run_debate_research(
                revision,
                recommendation,
                model_ids=model_ids,
                context=context,
                priority=(
                    ExternalAnalysisPriority.MANUAL
                    if manual
                    else ExternalAnalysisPriority.AUTOMATIC
                ),
            ),
            name=f"debate-research-{self.session_id}-{revision}",
        )
        self._register_research_task(
            task,
            generation_id=context.generation_id,
            manual=manual,
        )
        return self._register_research_group(group_key, task)

    async def request_debate_research(self, category: str) -> bool:
        """Force one fresh, narrow check of the currently visible claim."""
        if self._stopped:
            return False
        if self.local_only:
            # Privacy-First blocks cloud research explicitly while preserving
            # the local live answer. The UI receives a durable status instead
            # of waiting forever for a task that must never be scheduled.
            recommendation = self.objection_agent.latest_recommendation
            if recommendation.target_claim.strip():
                blocked = recommendation.model_copy(update={
                    "research_status": "blocked_by_privacy",
                    "research_alert": "Recherche ist im Privacy-First-Modus deaktiviert.",
                    "analysis_status": "completed",
                    "analysis_can_cancel": False,
                })
                await self._send_debate_update(
                    self._debate_revision,
                    blocked,
                    origin="research",
                )
            return False
        model_ids = self._external_analysis_models()
        if not model_ids:
            return False
        recommendation = self.objection_agent.latest_recommendation
        query = _manual_research_query(recommendation, category)
        if not is_safe_research_query(query):
            return False

        revision = self._debate_revision
        context = self._new_analysis_context(revision)
        group_key = self._research_group_key(context, query)
        if self._active_research_group(group_key) is not None:
            return True
        pending = recommendation.model_copy(
            update={
                "needs_research": True,
                "research_query": query,
                "research_status": "searching",
                "research_alert": "",
                "analysis_status": "analyzing",
                "analysis_can_cancel": True,
                "generation_id": context.generation_id,
            }
        )
        self.objection_agent.latest_recommendation = pending
        task = asyncio.create_task(
            self._run_debate_research(
                revision,
                pending,
                force_refresh=True,
                model_ids=model_ids,
                context=context,
                priority=ExternalAnalysisPriority.MANUAL,
            ),
            name=f"debate-manual-research-{self.session_id}-{category}-{revision}",
        )
        self._register_research_task(
            task,
            generation_id=context.generation_id,
            manual=True,
        )
        self._register_research_group(group_key, task)
        await self._send_debate_update(revision, pending, origin="research")
        return True

    async def cancel_manual_debate_analysis(self) -> bool:
        """Cancel this session's manual requests, never a shared provider bridge."""
        tasks = [
            task
            for task in getattr(self, "_manual_analysis_tasks", {}).values()
            if not task.done()
        ]
        if not tasks:
            return False
        scheduler = getattr(self, "_external_analysis_scheduler", None)
        for generation_id, task in tuple(self._manual_analysis_tasks.items()):
            if task.done():
                continue
            cancelled_by_scheduler = bool(
                scheduler is not None
                and scheduler.cancel_generation(generation_id)
            )
            if not cancelled_by_scheduler:
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        recommendation = self.objection_agent.latest_recommendation
        if recommendation.analysis_status == "analyzing":
            cancelled = recommendation.model_copy(update={
                "analysis_status": "cancelled",
                "analysis_can_cancel": False,
                "research_status": (
                    "cancelled"
                    if recommendation.research_status == "searching"
                    else recommendation.research_status
                ),
            })
            await self._send_debate_update(
                self._debate_revision,
                cancelled,
                origin="research",
            )
        return True

    async def _run_debate_research(
        self,
        revision: int,
        recommendation: DebateRecommendation,
        *,
        force_refresh: bool = False,
        model_ids: list[str] | None = None,
        context: AnalysisJobContext | None = None,
        priority: ExternalAnalysisPriority = ExternalAnalysisPriority.AUTOMATIC,
    ) -> None:
        context = context or self._new_analysis_context(revision)
        snapshot = create_configuration_snapshot()
        if snapshot.generation != context.config_generation:
            return
        scheduler = getattr(self, "_external_analysis_scheduler", None)
        if scheduler is None:
            configured_parallelism = (
                int(research_settings().get("experimental_external_parallelism", 3))
                if getattr(self, "_experimental_mode", False)
                else max_parallel_analyses()
            )
            scheduler = external_analysis_scheduler(max(1, min(4, configured_parallelism)))
            self._external_analysis_scheduler = scheduler
        async def execute_with_snapshot():
            with use_configuration_snapshot(snapshot):
                return await self._execute_debate_research(
                    revision,
                    recommendation,
                    force_refresh=force_refresh,
                    model_ids=model_ids,
                    context=context,
                    manual=priority is ExternalAnalysisPriority.MANUAL,
                )

        if self.local_only:
            # Defensive guard for replay/import callers that bypass the public
            # research request method. Never enqueue a cloud provider in this
            # mode, and surface the reason to the client.
            if self._analysis_context_is_current(context):
                blocked = recommendation.model_copy(update={
                    "research_status": "blocked_by_privacy",
                    "research_alert": "Recherche ist im Privacy-First-Modus deaktiviert.",
                    "analysis_status": "completed",
                    "analysis_can_cancel": False,
                })
                await self._send_debate_update(
                    revision,
                    blocked,
                    origin="research",
                )
            return
        try:
            await scheduler.run(
                context,
                priority,
                execute_with_snapshot,
                deadline_seconds=_external_analysis_deadline(priority),
                is_current=lambda: self._analysis_context_is_current(context),
            )
        except (ExternalAnalysisCancelled, ExternalAnalysisSuperseded):
            return
        except ExternalAnalysisDeadline:
            if self._analysis_context_is_current(context):
                unavailable = recommendation.model_copy(update={
                    "analysis_status": "unavailable",
                    "analysis_can_cancel": False,
                    "research_status": (
                        "unavailable" if recommendation.needs_research
                        else recommendation.research_status
                    ),
                })
                await self._send_debate_update(
                    revision,
                    unavailable,
                    origin="research",
                )
        except ExternalAnalysisQueueFull:
            if priority is ExternalAnalysisPriority.MANUAL:
                unavailable = recommendation.model_copy(update={
                    "analysis_status": "unavailable",
                    "analysis_can_cancel": False,
                })
                await self._send_debate_update(revision, unavailable, origin="research")

    def _experimental_lane_effort(
        self,
        analysis_phase: str,
        *,
        lane_label: str = "research",
        base_effort: str = "high",
        model_id: str = "",
    ) -> str:
        """Choose and capability-clamp one effort from the shared controller."""
        controller = getattr(self, "_adaptive_external_reasoning", None)
        if (
            not getattr(self, "_adaptive_reasoning_enabled", True)
            or controller is None
        ):
            requested = base_effort
        else:
            requested = controller.effort_for_next(
                queue_depth=0,
                is_new_topic=analysis_phase == "new_topic",
                needs_deep_reanalysis=analysis_phase == "deep_reanalysis",
            )
            # Rhetoric remains a medium-effort lane for providers that support
            # it; under overload the shared controller can still raise it.
            if lane_label == "rhetoric" and requested == "xhigh":
                requested = base_effort
        if not model_id:
            return requested or base_effort
        clamped = effective_reasoning_effort(
            provider_route(model_id),
            requested,
            complex_request=analysis_phase in {"new_topic", "deep_reanalysis"},
            remaining_seconds=model_timeout_seconds(model_id),
        )
        return clamped or requested or base_effort

    async def _run_experimental_external_lanes(
        self,
        recommendation: DebateRecommendation,
        *,
        model_id: str,
        relevant_context: str,
        sources: list[DebateSource],
        analysis_phase: str,
    ) -> tuple[DeepDebateAnalysis | None, str, str]:
        """Run logical research, adversarial and rhetoric lanes in parallel.

        ChatGPT Web still owns its dedicated-profile lock, so the scheduler
        permits overlap without cloning cookies or bypassing the existing lock.
        Each lane has a separate prompt and result, then local integration
        merges the findings into one recommendation.
        """
        lane_specs = (
            ("research", "Finde Originalquellen und ordne jede Quelle dem Claim zu.",
             "experimental_research_v1", "high"),
            ("adversarial", "Suche Gegenbeispiele, Widersprüche und doppelte Maßstäbe.",
             "experimental_adversarial_v1", "high"),
            ("rhetoric", "Formuliere die schlagfertigste, natürlich sprechbare Fassung mit Beispiel.",
             "experimental_strategist_v1", "medium"),
        )
        try:
            complete_transcript = await self._get_complete_transcript()
        except Exception:
            complete_transcript = ""
        recent_transcript = _select_relevant_transcript_excerpt(
            complete_transcript,
            claim=recommendation.target_claim,
            standpoint=self.meeting_context,
            context=relevant_context,
            max_chars=2400,
        )

        async def run_lane(
            label: str,
            directive: str,
            prompt_resource: str,
            base_effort: str,
        ):
            effort = self._experimental_lane_effort(
                analysis_phase,
                lane_label=label,
                base_effort=base_effort,
                model_id=model_id,
            )
            started_at = time.perf_counter()
            started_at_iso = datetime.now(UTC).isoformat()
            lane_id = (
                f"lane-{self.session_id}-{recommendation.claim_id or 'claim'}-"
                f"{recommendation.claim_revision}-{label}-{uuid.uuid4().hex[:10]}"
            )
            route = provider_route(model_id)
            provider = str(
                route.get("provider")
                or route.get("kind")
                or model_id.split(":", 1)[0]
            )
            standpoint_snapshot = str(self.meeting_context or "")[:1200]
            recent_transcript_window = recent_transcript
            consolidated_context = str(relevant_context or "")[:2400]
            try:
                result = await self.objection_agent.analyze_deep(
                    recommendation,
                    model_id=model_id,
                    own_position=self.meeting_context,
                    relevant_context=(
                        relevant_context
                        + "\n[RELEVANT TRANSCRIPT]\n"
                        + recent_transcript_window
                        + "\n[EXPERIMENTELLE LANE: "
                        + label
                        + "]\n"
                        + directive
                    ),
                    sources=sources,
                    reasoning_effort_override=effort,
                    analysis_phase=analysis_phase,
                    prompt_resource=prompt_resource,
                )
                return {
                    "lane_id": lane_id,
                    "label": label,
                    "session_id": str(self.session_id),
                    "claim_id": recommendation.claim_id,
                    "claim_revision": recommendation.claim_revision,
                    "transcript_revision": recommendation.transcript_revision,
                    "generation_id": recommendation.generation_id,
                    "standpoint_snapshot": standpoint_snapshot,
                    "recent_transcript_window": recent_transcript_window,
                    "consolidated_context": consolidated_context,
                    "provider": provider,
                    "model": model_id,
                    "started_at": started_at_iso,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "status": "completed",
                    "prompt_version": prompt_resource,
                    "prompt_resource": prompt_resource,
                    "reasoning_effort": effort,
                    "analysis": result[0],
                    "prompt": result[1],
                    "latency_ms": round((time.perf_counter() - started_at) * 1000),
                    "error": "",
                }
            except Exception as exc:
                return {
                    "lane_id": lane_id,
                    "label": label,
                    "session_id": str(self.session_id),
                    "claim_id": recommendation.claim_id,
                    "claim_revision": recommendation.claim_revision,
                    "transcript_revision": recommendation.transcript_revision,
                    "generation_id": recommendation.generation_id,
                    "standpoint_snapshot": standpoint_snapshot,
                    "recent_transcript_window": recent_transcript_window,
                    "consolidated_context": consolidated_context,
                    "provider": provider,
                    "model": model_id,
                    "started_at": started_at_iso,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "status": "failed",
                    "prompt_version": prompt_resource,
                    "prompt_resource": prompt_resource,
                    "reasoning_effort": effort,
                    "analysis": None,
                    "prompt": "",
                    "latency_ms": round((time.perf_counter() - started_at) * 1000),
                    "error": str(exc)[:240],
                }

        tasks = [
            asyncio.create_task(run_lane(*spec))
            for spec in lane_specs
        ]
        artifacts: list[dict] = []
        analyses: list[DeepDebateAnalysis] = []
        prompts: list[str] = []
        try:
            for completed in asyncio.as_completed(tasks):
                artifact = await completed
                controller = getattr(self, "_adaptive_external_reasoning", None)
                if (
                    getattr(self, "_adaptive_reasoning_enabled", True)
                    and controller is not None
                ):
                    latency_ms = int(artifact.get("latency_ms") or 0)
                    if (
                        artifact.get("status") == "completed"
                        or latency_ms >= controller.latency_threshold_ms
                    ):
                        # Experimental lanes start together, so their queue
                        # depth is zero; measured latency still feeds the same
                        # controller used by serialized deep analysis.
                        controller.observe(
                            latency_ms=latency_ms,
                            queue_depth=0,
                        )
                analysis_result = artifact.get("analysis")
                external_insights: list[dict[str, object]] = []
                if analysis_result is not None:
                    source_ids = [
                        str(source.url)
                        for source in sources[:8]
                        if (
                            str(getattr(source, "url", "") or "").strip()
                            and getattr(source, "retrieval_status", "") == "read"
                        )
                    ]

                    def add_lane_insights(kind: str, values: object) -> None:
                        for index, value in enumerate(values if isinstance(values, list) else []):
                            text = " ".join(str(value or "").split()).strip()
                            if not text:
                                continue
                            external_insights.append({
                                "insight_id": (
                                    f"{artifact['lane_id']}:{kind}:{index}"
                                ),
                                "lane_id": artifact["lane_id"],
                                "kind": kind,
                                "text": text[:1200],
                                "source_ids": source_ids,
                                "confidence": "low",
                                "claim_id": artifact["claim_id"],
                                "claim_revision": artifact["claim_revision"],
                                "transcript_revision": artifact["transcript_revision"],
                                "generation_id": artifact["generation_id"],
                            })

                    add_lane_insights(
                        "counterexample",
                        getattr(analysis_result, "counterarguments", []),
                    )
                    add_lane_insights(
                        "rebuttal",
                        [getattr(analysis_result, "rebuttal", "")],
                    )
                    add_lane_insights(
                        "counter_question",
                        getattr(analysis_result, "followups", []),
                    )
                    add_lane_insights(
                        "source",
                        getattr(analysis_result, "evidence", []),
                    )
                artifact_summary = {
                    "lane_id": artifact["lane_id"],
                    "lane": artifact["label"],
                    "session_id": artifact["session_id"],
                    "claim_id": artifact["claim_id"],
                    "claim_revision": artifact["claim_revision"],
                    "transcript_revision": artifact["transcript_revision"],
                    "generation_id": artifact["generation_id"],
                    "standpoint_snapshot": artifact["standpoint_snapshot"],
                    "recent_transcript_window": artifact["recent_transcript_window"],
                    "consolidated_context": artifact["consolidated_context"],
                    "provider": artifact["provider"],
                    "model": artifact["model"],
                    "started_at": artifact["started_at"],
                    "completed_at": artifact["completed_at"],
                    "status": artifact["status"],
                    "prompt_version": artifact["prompt_version"],
                    "prompt_resource": artifact["prompt_resource"],
                    "reasoning_effort": artifact["reasoning_effort"],
                    "latency_ms": artifact["latency_ms"],
                    "error": artifact["error"],
                    "external_insights": external_insights,
                }
                artifacts.append(artifact_summary)
                # Surface each completed lane immediately. The speakable local
                # answer remains unchanged; only the structured evidence packet
                # is attached so the UI can show arriving rebuttal/example blobs
                # before all lanes and the final consolidation finish.
                self._experimental_lane_artifacts = list(artifacts)
                if (
                    getattr(self, "_experimental_mode", False)
                    and getattr(self, "_argument_graph_enabled", False)
                ):
                    lane_payload = recommendation.model_dump(mode="json")
                    lane_payload["external_lane_artifacts"] = list(artifacts)
                    await self._persist_argument_recommendation(lane_payload)
                try:
                    await self._send_debate_update(
                        recommendation.transcript_revision,
                        recommendation.model_copy(update={
                            "analysis_status": "analyzing",
                            "research_status": "searching",
                        }),
                        origin="research",
                    )
                except Exception:
                    # A partial lane must never block the remaining lanes.
                    pass
                try:
                    await self.websocket.send_json({
                        "type": "experimental_lane_update",
                        "data": {
                            "session_id": str(self.session_id),
                            "claim_id": recommendation.claim_id,
                            "claim_revision": recommendation.claim_revision,
                            "transcript_revision": recommendation.transcript_revision,
                            "generation_id": recommendation.generation_id,
                            **artifact_summary,
                        },
                    })
                except Exception:
                    pass
                if artifact["analysis"] is not None:
                    analyses.append(artifact["analysis"])
                    prompts.append(artifact["prompt"])
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        self._experimental_lane_artifacts = artifacts
        if not analyses:
            return None, "", ""

        def unique(values: list[str], limit: int) -> list[str]:
            result: list[str] = []
            for value in values:
                clean = " ".join(str(value or "").split())
                if clean and clean not in result:
                    result.append(clean)
                if len(result) >= limit:
                    break
            return result

        merged = analyses[0].model_copy(update={
            "counterarguments": unique(
                [value for item in analyses for value in item.counterarguments], 3
            ),
            "followups": unique(
                [value for item in analyses for value in item.followups], 2
            ),
            "evidence": unique(
                [value for item in analyses for value in item.evidence], 4
            ),
            "rebuttal": next(
                (item.rebuttal for item in analyses if item.rebuttal),
                analyses[0].rebuttal,
            ),
            "interpretation": next(
                (item.interpretation for item in analyses if item.interpretation),
                analyses[0].interpretation,
            ),
        })
        return merged, json.dumps(
            {"lanes": artifacts, "prompts": prompts},
            ensure_ascii=False,
        ), model_id


    async def _execute_debate_research(
        self,
        revision: int,
        recommendation: DebateRecommendation,
        *,
        force_refresh: bool,
        model_ids: list[str] | None,
        context: AnalysisJobContext,
        manual: bool,
    ) -> None:
        # Replay/import tests and older in-process callers may construct a
        # lightweight orchestrator without running the full constructor. Keep
        # the background-only controls lazy so that path stays compatible.
        if (
            getattr(self, "_experimental_mode", False)
            and getattr(self, "_active_claim_is_interim", False)
            and not manual
        ):
            # Interim hypotheses only use the local fast path. External lanes
            # start after a final segment or an explicit manual request.
            return
        if not manual and getattr(self, "debate_settings", None) is not None:
            if getattr(self.debate_settings, "research_frequency", "normal") == "never":
                return
        if not hasattr(self, "_external_analysis_waiters"):
            self._external_analysis_waiters = 0
        if not hasattr(self, "_external_analysis_lock"):
            self._external_analysis_lock = asyncio.Semaphore(
                max_parallel_analyses()
            )
        if not hasattr(self, "_external_model_unavailable_until"):
            self._external_model_unavailable_until = {}
        if not hasattr(self, "_adaptive_external_reasoning"):
            adaptive_config = adaptive_reasoning_settings()
            self._adaptive_reasoning_enabled = bool(
                adaptive_config.pop("enabled", True)
            )
            self._reuse_topic_analysis = bool(
                adaptive_config.pop("reuse_topic_analysis", True)
            )
            self._topic_similarity_threshold = float(
                adaptive_config.pop("topic_similarity_threshold", 0.46)
            )
            self._adaptive_external_reasoning = AdaptiveReasoningEffort(
                **adaptive_config
            )
        model_ids = model_ids or self._external_analysis_models()
        if not model_ids:
            return
        query = recommendation.research_query.strip()
        research_mode = "deep" if manual else "live"
        cache_modes = getattr(self, "_research_cache_modes", None)
        if cache_modes is None:
            cache_modes = {}
            self._research_cache_modes = cache_modes
        sources: list[DebateSource] = []
        if recommendation.needs_research and is_safe_research_query(query):
            result = None if force_refresh else self._research_cache.get(query)
            if result is not None and cache_modes.get(query, "deep") != research_mode:
                result = None
            if result is None:
                result = await research_claim(
                    recommendation.target_claim,
                    query,
                    research_mode=research_mode,
                )
                self._research_cache[query] = result
                cache_modes[query] = research_mode
            result = _bind_research_result(
                result,
                recommendation.target_claim,
                claim_revision=context.claim_revision,
            )
            if result.status == "completed":
                sources = [
                    DebateSource(**source.model_dump())
                    for source in result.sources
                ]

        # A slow answer from an older utterance may still be useful in the cache,
        # but it must never overwrite what the user is currently seeing.
        if revision != self._debate_revision or not self._analysis_context_is_current(context):
            self._remember_topic_knowledge(context, recommendation, sources)
            return
        analysis = None
        prompt = ""
        used_model = ""
        reuse_topic_analysis = getattr(self, "_reuse_topic_analysis", True)
        relevant_context = (
            await self._debate_support_context_async(recommendation.target_claim)
            if reuse_topic_analysis
            else ""
        )
        is_new_topic = (
            not reuse_topic_analysis
            or not bool(getattr(self, "_active_semantic_related_claim_ids", []))
        )
        needs_deep_reanalysis = manual
        self._external_analysis_waiters += 1
        try:
            async with self._external_analysis_lock:
                if not self._analysis_context_is_current(context):
                    return
                queue_depth = max(0, self._external_analysis_waiters - 1)
                for model_id in (() if getattr(self, "_experimental_mode", False) else model_ids):
                    if not self._analysis_context_is_current(context):
                        return
                    adaptive = (
                        self._adaptive_reasoning_enabled
                        and _uses_adaptive_gpt6_reasoning(model_id)
                    )
                    effort = (
                        self._adaptive_external_reasoning.effort_for_next(
                            queue_depth=queue_depth,
                            is_new_topic=is_new_topic,
                            needs_deep_reanalysis=needs_deep_reanalysis,
                        )
                        if adaptive
                        else None
                    )
                    effort = effective_reasoning_effort(
                        provider_route(model_id),
                        effort,
                        complex_request=is_new_topic or needs_deep_reanalysis,
                        remaining_seconds=model_timeout_seconds(model_id),
                    )
                    call_started = time.perf_counter()
                    succeeded = False
                    try:
                        analysis, prompt = await asyncio.wait_for(
                            self.objection_agent.analyze_deep(
                                recommendation,
                                model_id=model_id,
                                own_position=self.meeting_context,
                                relevant_context=relevant_context,
                                sources=sources,
                                reasoning_effort_override=effort,
                                analysis_phase=(
                                    "new_topic" if is_new_topic
                                    else "deep_reanalysis" if needs_deep_reanalysis
                                    else "follow_up"
                                ),
                            ),
                            timeout=model_timeout_seconds(model_id),
                        )
                        succeeded = True
                        used_model = model_id
                        break
                    except Exception as exc:
                        failure = classify_provider_failure(exc)
                        cooldown = (
                            failure.retry_after_seconds
                            if failure.retry_after_seconds is not None
                            else model_cooldown_seconds(model_id)
                        )
                        self._external_model_unavailable_until[model_id] = (
                            time.monotonic() + max(1, cooldown)
                        )
                        logger.warning(
                            "[debate_analyst] %s failed kind=%s retryable=%s cooldown=%ss; trying configured fallback: %s",
                            model_id,
                            failure.kind,
                            failure.retryable,
                            cooldown,
                            exc,
                        )
                    finally:
                        latency_ms = round((time.perf_counter() - call_started) * 1000)
                        overloaded_failure = (
                            latency_ms
                            >= self._adaptive_external_reasoning.latency_threshold_ms
                            or queue_depth
                            >= self._adaptive_external_reasoning.queue_threshold
                        )
                        if adaptive and (succeeded or overloaded_failure):
                            previous = self._adaptive_external_reasoning.current
                            self._adaptive_external_reasoning.observe(
                                latency_ms=latency_ms,
                                queue_depth=queue_depth,
                            )
                            logger.info(
                                "[debate_analyst] model=%s effort=%s latency_ms=%s queue=%s next_effort=%s previous_state=%s",
                                model_id,
                                effort,
                                latency_ms,
                                queue_depth,
                                self._adaptive_external_reasoning.current,
                                previous,
                            )
        finally:
            self._external_analysis_waiters = max(
                0, self._external_analysis_waiters - 1
            )

        if getattr(self, "_experimental_mode", False):
            lane_model = (model_ids or self._external_analysis_models() or ["chatgpt-web:gpt-6"])[0]
            analysis, prompt, used_model = await self._run_experimental_external_lanes(
                recommendation,
                model_id=lane_model,
                relevant_context=relevant_context,
                sources=sources,
                analysis_phase=(
                    "new_topic" if is_new_topic
                    else "deep_reanalysis" if needs_deep_reanalysis
                    else "follow_up"
                ),
            )

        self._remember_topic_knowledge(
            context,
            recommendation,
            sources,
            analysis=analysis,
        )
        if revision != self._debate_revision or not self._analysis_context_is_current(context):
            if (
                getattr(self, "_experimental_mode", False)
                and getattr(self, "_argument_graph_enabled", False)
                and getattr(self, "_experimental_lane_artifacts", None)
            ):
                stale_payload = recommendation.model_dump(mode="json")
                stale_payload["external_lane_artifacts"] = list(
                    self._experimental_lane_artifacts
                )
                await self._persist_argument_recommendation(stale_payload)
            return
        if analysis is None:
            unavailable = recommendation.model_copy(update={
                "analysis_status": "unavailable",
                "analysis_can_cancel": False,
                "research_status": (
                    "unavailable" if recommendation.needs_research
                    else recommendation.research_status
                ),
            })
            await self._send_debate_update(revision, unavailable, origin="research")
            return

        if getattr(self, "_experimental_mode", False):
            # External lanes contribute evidence and adversarial material, while
            # the local live line remains the selected answer.
            candidate = recommendation.model_copy(update={
                "pipeline_mode": "experimental_debateai",
                "counterargument": analysis.counterarguments[0] if analysis.counterarguments else recommendation.counterargument,
                "analogy": analysis.interpretation or recommendation.analogy,
                "counter_question": analysis.followups[0] if analysis.followups else recommendation.counter_question,
                "research_alert": analysis.rebuttal or recommendation.research_alert,
                "analysis_status": "completed",
                "analyst_model": used_model,
                "analyst_prompt": prompt,
                "sources": [
                    *recommendation.sources,
                    *[
                        source for source in sources
                        if source.url and source.url not in {existing.url for existing in recommendation.sources}
                    ],
                ],
            })
            candidate = self._experimentalize_recommendation(candidate)
        else:
            candidate = self._merge_deep_analysis(
                recommendation,
                analysis,
                model_id=used_model,
                prompt=prompt,
                sources=sources,
            )
        if recommendation.needs_research and not sources:
            candidate = candidate.model_copy(update={"research_status": "unavailable"})
        candidate = candidate.model_copy(update={
            "analysis_can_cancel": False,
            "generation_id": context.generation_id,
        })
        if not _materially_better_recommendation(recommendation, candidate):
            # Keep Qwen's speaking line, but retain the hosted analyst's extra
            # counters, interpretation and follow-ups in the same claim branch.
            candidate = candidate.model_copy(update={
                "answer_now": recommendation.answer_now,
                "counterargument": recommendation.counterargument,
            })
        if self._analysis_context_is_current(context):
            await self._send_debate_update(revision, candidate, origin="research")

    async def _run_debate_revision(
        self,
        revision: int,
        *,
        claim_id: str | None = None,
        transcript_revision: int | None = None,
    ) -> None:
        """Analyze one transcript revision and discard it if newer speech wins."""
        if claim_id is None:
            claim_id = getattr(self, "_active_claim_id", None)
        if transcript_revision is None:
            transcript_revision = getattr(self, "_transcript_revision", 0)
        generation_context = self._new_analysis_context(revision)

        def stamp_context(value: DebateRecommendation) -> DebateRecommendation:
            value = self._experimentalize_recommendation(value)
            return value.model_copy(update={
                "session_id": value.session_id or str(self.session_id),
                "claim_id": value.claim_id or generation_context.claim_id,
                "transcript_revision": transcript_revision,
                "claim_revision": generation_context.claim_revision,
                "directive_revision": generation_context.directive_revision,
                "config_generation": generation_context.config_generation,
                "generation_id": generation_context.generation_id,
            })

        def snapshot_is_current() -> bool:
            return bool(
                not self._stopped
                and self._analysis_context_is_current(
                    generation_context,
                    allow_newer_revision_same_claim=True,
                )
                and revision == self._debate_revision
                and (
                    not claim_id
                    or claim_id == getattr(self, "_active_claim_id", None)
                )
            )

        started_at = time.perf_counter()
        await self.activity.cycle_started("objection_handler")
        try:
            if getattr(self, "_experimental_mode", False) and not getattr(
                self, "_active_claim_is_interim", False
            ):
                # Final/checkpoint turns get the complete bounded transcript;
                # interim turns keep the short window for immediate latency.
                transcript_window = await self._get_complete_transcript()
            else:
                transcript_window = await self.transcript_buffer.get_window(
                    max_age_seconds=settings.OBJECTION_WINDOW_SECONDS,
                    aliases=self.speaker_aliases(),
                )
            interim_hypotheses = getattr(self, "_interim_debate_hypotheses", {})
            if interim_hypotheses:
                live_partial = next(reversed(interim_hypotheses.values()))[-1200:]
                partial_block = (
                    "[LIVE-TEILTRANSKRIPT - kann unvollstaendig sein]: "
                    f"{live_partial}"
                )
                transcript_window = (
                    partial_block
                    if transcript_window == "(No recent transcript)"
                    else f"{transcript_window}\n{partial_block}"
                )
            if transcript_window == "(No recent transcript)":
                await self.activity.cycle_finished(
                    "objection_handler",
                    {
                        "kind": "skipped_no_transcript",
                        "detail": "Nothing to scan yet.",
                        "items": 0,
                    },
                )
                return

            debate_settings = getattr(self, "debate_settings", DebateSettings())
            partial_sent = False

            async def publish_model_partial(
                partial: DebateRecommendation,
            ) -> None:
                nonlocal partial_sent
                if partial_sent or not snapshot_is_current():
                    return
                partial_sent = True
                self._debate_partial_visible = True
                await self._send_debate_update(
                    revision,
                    stamp_context(partial),
                    latency_ms=max(
                        0,
                        round((time.perf_counter() - started_at) * 1000),
                    ),
                    origin="model_stream",
                )

            current_line = next(
                (
                    line for line in reversed(transcript_window.splitlines())
                    if line.strip()
                ),
                transcript_window,
            )
            insights = await self.objection_agent.run_cycle(
                transcript_window=transcript_window,
                directives=self.directives,
                speakers=self.speakers,
                support_context=await self._debate_support_context_async(
                    current_line,
                    include_local_dossier=True,
                ),
                on_model_partial=publish_model_partial,
                resource_profile=getattr(
                    self.debate_settings, "performance_profile", "balanced"
                ),
            )
            if not snapshot_is_current():
                return

            model_recommendation = stamp_context(
                self.objection_agent.latest_recommendation
            )
            model_has_guidance = _has_speakable_guidance(
                model_recommendation,
                debate_settings.always_analogy,
            )
            recommendation = model_recommendation
            if self.local_only and recommendation.needs_research:
                recommendation = recommendation.model_copy(update={
                    "research_status": "blocked_by_privacy",
                    "research_alert": "Recherche ist im Privacy-First-Modus deaktiviert.",
                    "analysis_status": "completed",
                    "analysis_can_cancel": False,
                })
            if _has_speakable_guidance(
                recommendation, debate_settings.always_analogy
            ):
                research_task = self._maybe_schedule_research(revision, recommendation)
                if research_task is not None:
                    recommendation = recommendation.model_copy(update={
                        "analysis_status": "analyzing",
                        "analysis_can_cancel": bool(
                            getattr(research_task, "manual_analysis", False)
                        ),
                        "generation_id": str(
                            getattr(research_task, "analysis_generation_id", "")
                        ),
                        "research_status": (
                            "searching"
                            if recommendation.needs_research
                            else recommendation.research_status
                        ),
                    })

                # A complete, valid model answer always replaces its own streamed
                # partial. It is not scored against a canned fallback card.
                if (
                    _contains_unsupported_numeric_assertion(recommendation)
                    or _contains_unsupported_evidence_claim(recommendation)
                ):
                    recommendation = recommendation.model_copy(update={
                        "confidence": "low",
                        "needs_research": True,
                        "research_query": recommendation.research_query
                        or recommendation.target_claim,
                    })
                latency_ms = (
                    max(
                        0,
                        round((time.perf_counter() - started_at) * 1000),
                    )
                    if model_has_guidance
                    else None
                )
                await self._send_debate_update(
                    revision,
                    recommendation,
                    latency_ms=latency_ms,
                    origin="model",
                )

            saved_count = 0
            for insight in insights:
                if not snapshot_is_current():
                    return
                saved = await self._save_and_send_insight(
                    insight,
                    agent_source="objection_handler",
                )
                if saved:
                    saved_count += 1
                    self._event_bus.publish(
                        "new_insight",
                        {
                            "item_type": "objection",
                            "agent_source": "objection_handler",
                        },
                    )

            last_outcome = self.objection_agent.last_outcome or {}
            if last_outcome.get("kind") == "error":
                await self.activity.cycle_error(
                    "objection_handler",
                    last_outcome["error"],
                )
            else:
                await self.activity.cycle_finished(
                    "objection_handler",
                    saved_outcome(
                        last_outcome,
                        produced=len(insights),
                        saved=saved_count,
                    ),
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Debate copilot revision failed: %s", exc)
            await self.activity.cycle_error(
                "objection_handler",
                classify_error(exc, self._get_model("objection_handler")),
            )

    def _mark_transcript_activity(self) -> None:
        """Cancel a live refinement as soon as speech resumes."""
        self._last_transcript_activity_at = time.monotonic()
        task = getattr(self, "_refiner_job", None)
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel("live transcript activity")

    def _live_refiner_is_idle(self) -> bool:
        return live_refiner_is_idle(
            stopped=self._stopped,
            debate_pending=self._debate_pending,
            objection_task=self._objection_task,
            active_claim_is_interim=self._active_claim_is_interim,
            last_transcript_at=self._last_transcript_activity_at,
        )

    async def _refine_recent_transcript(self, *, limit: int | None, source_label: str) -> int:
        """Refine pending entries and push each rewrite to the interface."""
        from app.database import async_session

        model_id = self._get_model(TRANSCRIPT_REFINER_SLUG)
        async with async_session() as db:
            changed = await refine_session(db, self.session_id, model_id, limit=limit)
            payloads = [refiner_update_payload(entry) for entry in changed]
            await db.commit()
        for payload in payloads:
            try:
                await self.websocket.send_json({"type": "transcript_updated", "data": payload})
            except Exception:  # noqa: BLE001 - a closed socket must not stop the pass
                break
        if payloads:
            logger.info("[%s] refined %d transcript entries", source_label, len(payloads))
        return len(payloads)

    async def _transcript_refiner_loop(self):
        interval = self._get_interval(TRANSCRIPT_REFINER_SLUG, 45)
        await asyncio.sleep(interval)
        while not self._stopped:
            if not self._live_refiner_is_idle():
                await asyncio.sleep(interval)
                continue
            await self.activity.cycle_started(TRANSCRIPT_REFINER_SLUG)
            self._refiner_job = asyncio.create_task(
                self._refine_recent_transcript(
                    limit=REFINER_LIVE_WINDOW,
                    source_label="transcript_refiner",
                ),
                name=f"transcript-refiner-{self.session_id}-job",
            )
            try:
                count = await self._refiner_job
                await self.activity.cycle_finished(
                    TRANSCRIPT_REFINER_SLUG,
                    {
                        "kind": "insights" if count else "no_findings",
                        "detail": f"{count} transcript lines refined." if count else "Nothing new to refine.",
                        "items": count,
                    },
                )
            except asyncio.CancelledError:
                if self._stopped:
                    break
                logger.debug("Transcript refiner pass cancelled because live speech resumed")
            except Exception as e:
                logger.error(f"Transcript refiner loop error: {e}")
                await self.activity.cycle_error(
                    TRANSCRIPT_REFINER_SLUG,
                    classify_error(e, self._get_model(TRANSCRIPT_REFINER_SLUG)),
                )
            finally:
                self._refiner_job = None
            await asyncio.sleep(interval)
    async def _run_transcript_refinement_stage(
        self,
        stages: list[str],
        progress_callback,
        drain_total_steps: int,
        result: dict,
    ) -> None:
        if "transcript_refinement" not in stages:
            return
        step = 1 + stages.index("transcript_refinement")
        await _emit_progress(
            progress_callback,
            "transcript_refinement",
            "Refining the transcript wording",
            step,
            drain_total_steps,
            drain_progress_percent(step, drain_total_steps),
        )
        await self.activity.cycle_started(TRANSCRIPT_REFINER_SLUG)
        try:
            count = await self._refine_recent_transcript(limit=None, source_label="transcript_refinement")
            result["transcript_refined"] = count
            await self.activity.cycle_finished(
                TRANSCRIPT_REFINER_SLUG,
                {"kind": "insights" if count else "no_findings", "detail": f"{count} lines refined at call end.", "items": count},
            )
        except Exception as e:  # noqa: BLE001 - the drain degrades past a failed stage
            logger.error(f"Transcript refinement stage failed: {e}")
            result["stage_errors"].append({"stage": "transcript_refinement", "error": str(e)})
            await self.activity.cycle_error(
                TRANSCRIPT_REFINER_SLUG,
                classify_error(e, self._get_model(TRANSCRIPT_REFINER_SLUG)),
            )

    async def _strategic_signals_loop(self):
        interval = self._get_interval(STRATEGIC_SIGNALS_SLUG, 45)
        # Do not add a full interval before the first signal snapshot.
        last_window = ""
        while not self._stopped:
            await self.activity.cycle_started(STRATEGIC_SIGNALS_SLUG)
            try:
                transcript_window = await self.transcript_buffer.get_window(
                    aliases=self.speaker_aliases()
                )
                if transcript_window == last_window:
                    logger.debug("[strategic_signals] Window unchanged, skipping cycle")
                elif transcript_window != "(No recent transcript)":
                    cycle = await run_strategic_signals_cycle(
                        self.session_id,
                        agent_configs=self._agent_configs,
                        transcript_window=transcript_window,
                        directives=self.directives,
                        doc_summaries=self.doc_summaries,
                        speakers=self.speakers,
                        active_questions=self.active_questions,
                    )
                    synthesis, signal_rows = cycle if cycle else (None, None)
                    if synthesis:
                        await self._send_synthesis_update(synthesis)
                    filed = await self._send_signal_insights(signal_rows)
                    await self.activity.cycle_finished(
                        STRATEGIC_SIGNALS_SLUG,
                        {
                            "kind": "insights" if synthesis else "no_findings",
                            "detail": (
                                f"Live strategic signals updated; {filed} filed as insights."
                                if synthesis and filed
                                else "Live strategic signals updated."
                                if synthesis
                                else "No strategic signal changed."
                            ),
                            "items": 1 if synthesis else 0,
                        },
                    )
                    # Do not mark the window processed until the cycle has
                    # completed, so transient provider errors are retried.
                    last_window = transcript_window
                else:
                    await self.activity.cycle_finished(
                        STRATEGIC_SIGNALS_SLUG,
                        {
                            "kind": "skipped_no_transcript",
                            "detail": "Nothing to analyze yet.",
                            "items": 0,
                        },
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Strategic signals loop error: {e}")
                await self.activity.cycle_error(
                    STRATEGIC_SIGNALS_SLUG,
                    classify_error(e, self._get_model(STRATEGIC_SIGNALS_SLUG)),
                )
            await asyncio.sleep(interval)

    async def _send_synthesis_update(self, synthesis):
        try:
            await self.websocket.send_json({
                "type": "synthesis_updated",
                "data": _synthesis_payload(synthesis),
            })
        except Exception:
            pass

    # ── Event-driven: Synthesizer ────────────────────────────────────────

    async def _run_synthesizer(self, events: list[dict]):
        """Called by CooldownSubscriber when new_insight events arrive."""
        await self.activity.cycle_started("synthesizer")
        try:
            logger.info(f"Running synthesizer (triggered by {len(events)} events)")
            applied_ops = await run_synthesizer_cycle(
                self.session_id,
                model_override=self._get_model("synthesizer"),
                prompt_override=self._get_prompt("synthesizer") or None,
            )

            await self._broadcast_operation_results(applied_ops)

            if applied_ops:
                logger.info(f"Synthesizer applied {len(applied_ops)} operations")
            await self.activity.cycle_finished(
                "synthesizer",
                {
                    "kind": "insights" if applied_ops else "no_findings",
                    "detail": (
                        f"{len(applied_ops)} insight operation"
                        f"{'s' if len(applied_ops) != 1 else ''} applied"
                        if applied_ops
                        else "No saved insight needed reconciliation."
                    ),
                    "items": len(applied_ops),
                },
            )

        except Exception as e:
            logger.error(f"Synthesizer cycle error: {e}")
            await self.activity.cycle_error(
                "synthesizer",
                classify_error(e, self._get_model("synthesizer")),
            )

    # ── Event-driven: Opportunity Specialist ──────────────────────────────

    async def _run_opportunity_specialist(self, events: list[dict]):
        """Called by CooldownSubscriber when new_opportunity events arrive."""
        await self.activity.cycle_started("opportunity_specialist")
        try:
            logger.info(f"Running opportunity specialist (triggered by {len(events)} events)")
            applied_ops = await run_opportunity_specialist_cycle(
                self.session_id,
                model_override=self._get_model("opportunity_specialist"),
                knowledge_source_ids=self._get_knowledge_source_ids("opportunity_specialist"),
                prompt_override=self._get_prompt("opportunity_specialist") or None,
            )

            await self._broadcast_operation_results(applied_ops)
            await self.activity.cycle_finished(
                "opportunity_specialist",
                {
                    "kind": "insights" if applied_ops else "no_findings",
                    "detail": (
                        f"{len(applied_ops)} opportunity match"
                        f"{'es' if len(applied_ops) != 1 else ''} applied"
                        if applied_ops
                        else "No offering match was found."
                    ),
                    "items": len(applied_ops),
                },
            )

        except Exception as e:
            logger.error(f"Opportunity specialist cycle error: {e}")
            await self.activity.cycle_error(
                "opportunity_specialist",
                classify_error(e, self._get_model("opportunity_specialist")),
            )

    async def _broadcast_operation_results(self, applied_ops: list[dict]):
        for op_result in applied_ops:
            ws_type = op_result.get("ws_type")
            ws_data = op_result.get("ws_data")
            if ws_type and ws_data:
                try:
                    await self.websocket.send_json({
                        "type": ws_type,
                        "data": ws_data,
                    })
                except Exception:
                    pass

            op_name = op_result.get("op")
            if op_name in ("answer", "dismiss", "merge"):
                # A merged-away or dismissed question is as closed as an
                # answered one; only "answer" used to prune, so the rest
                # accumulated for the rest of the call.
                self._forget_active_question(op_result.get("id"))
                self._forget_active_question(op_result.get("remove_id"))
            elif op_name == "create" and ws_data:
                if (ws_data.get("item_type") or "question") == "question":
                    self._remember_active_question(
                        ws_data["id"], ws_data["question"], ws_data.get("item_type") or "question"
                    )

    # ── Reconnection ─────────────────────────────────────────────────────

    async def _reconnect_gateway(self) -> bool:
        if self.audio_gateway is None:
            return False
        try:
            if self._gateway_task and not self._gateway_task.done():
                self._gateway_task.cancel()
                try:
                    await self._gateway_task
                except (asyncio.CancelledError, Exception):
                    pass
            await self.audio_gateway.close()