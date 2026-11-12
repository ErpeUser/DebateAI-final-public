"""Objection Handler agent — fast scan loop over the freshest transcript.

Optimized for latency: a lean prompt, a short transcript window, and a
low-latency default model so objections surface while the moment to
respond is still open. Each finding pairs an immediate suggested reply
(micro) with the underlying concern and strategic angle (macro).
"""

import json
import hashlib
import logging
import re
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.services.agents.activity import classify_error
from app.services.agents.prompts import (
    DEBATE_RECOMMENDATION_PROMPT,
    OBJECTION_HANDLER_PROMPT,
)
from app.services.ai_config import reasoning_effort
from app.services.agents.prompt_resources import load_prompt_resource
from app.services.agents.speaker_context import (
    build_speaker_aliases,
    format_speakers_list,
    resolve_speaker_reference,
)
from app.services.llm import generate_json
from app.services.meeting_context import build_meeting_context_text, format_prompt_layers
from app.services.debate_contracts import AtomicClaim, DebateSource, LogicalRelation

logger = logging.getLogger(__name__)

# Low-latency model: objection surfacing is time-critical, so the default
# trades some depth for speed. Overridable via agent config.
DEFAULT_OBJECTION_MODEL = "gemini-3.5-flash-lite"

VALID_SEVERITIES = {"high", "medium", "low"}

# How many surfaced objections to remind the model about so overlapping
# scan windows don't re-flag the same pushback every cycle.
_MAX_RECENT_OBJECTIONS = 12


class ObjectionHandlerItem(BaseModel):
    item_type: str | None = None
    question: str
    response_now: str = ""
    bigger_picture: str = ""
    source_context: str = ""
    severity: str | None = None
    speaker_id: str | None = None


class DeepDebateAnalysis(BaseModel):
    """Compact result from the configured hosted background analyst."""

    best_reply: str
    counterarguments: list[str] = Field(default_factory=list, max_length=3)
    rebuttal: str = ""
    interpretation: str = ""
    followups: list[str] = Field(default_factory=list, max_length=2)
    evidence: list[str] = Field(default_factory=list, max_length=4)
    logical_relations: list[LogicalRelation] = Field(default_factory=list, max_length=4)

    @field_validator("best_reply")
    @classmethod
    def limit_best_reply(cls, value: str) -> str:
        return _limit_spoken_words(value, 32)


_DEEP_ANALYSIS_PROMPT_TEMPLATE = """Gegnerisches Argument: {claim}
Meine Position: {own_position}
Relevanter Verlauf: {relevant_context}
Gelesene Belege: {evidence}

Auftrag: Pruefe Praemissen und Schluss, entwickle die staerkste sachlich
haltbare Widerlegung, ein konkretes Gegenbeispiel und bis zu zwei praezise
Anschlussfragen. Trenne Beleg, Interpretation und Unsicherheit. Formuliere
kurz, natuerlich und direkt sprechbar auf Deutsch. Pruefe Beziehungen zu
frueheren Claims nur anhand der genannten claim-IDs. Setze verified nur bei
direkter textlicher Stuetzung und confidence nur bei klarer Beziehung auf
mindestens 0.7. Thematische Aehnlichkeit ist keine logische Beziehung."""


def deep_analysis_reasoning_effort(model_id: str) -> str:
    """Reasoning requested from supported login-bridge analyst profiles."""
    wire_model = model_id.rsplit(":", 1)[-1].casefold()
    fallback = "high" if "gemini-3.1" in wire_model and "pro" in wire_model else "low"
    if model_id == "chatgpt-web:gpt-6":
        fallback = "xhigh"
    if model_id.startswith("endpoint:gemini-web:"):
        # The selected adapter maps this OpenAI field to Gemini Web's visible
        # Low/Medium/High selector and reports the resolved response model.
        fallback = "high"
    if model_id.startswith("endpoint:subscription-ai:") and wire_model.startswith("gpt-6"):
        fallback = "xhigh"
    return reasoning_effort(model_id, fallback)

def build_deep_analysis_prompt(
    *,
    claim: str,
    own_position: str,
    relevant_context: str,
    sources: list[DebateSource],
    prompt_name: str = "debate_deep_v1",
) -> str:
    """Build one bounded, dynamic analyst request without generic playbooks."""
    source_lines = []
    for source in sources[:3]:
        passage = " ".join((source.passage or source.snippet).split())[:360]
        if passage:
            source_lines.append(f"- {source.title[:120]}: {passage}")
    evidence = "\n".join(source_lines) or "(keine gelesenen Quellen; nichts als belegt ausgeben)"
    template = load_prompt_resource(prompt_name, _DEEP_ANALYSIS_PROMPT_TEMPLATE)
    values = {
        "claim": claim[:700],
        "own_position": (own_position or "(nicht explizit angegeben)")[:500],
        "relevant_context": (relevant_context or "(keiner)")[:700],
        "evidence": evidence,
    }
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def _limit_spoken_words(value: str, limit: int, *, question: bool = False) -> str:
    """Prefer a complete short sentence and never cut a sentence mid-meaning."""
    normalized = " ".join(value.split()).strip()
    if len(normalized.split()) > limit:
        complete_sentences = re.split(r"(?<=[.!?])\s+", normalized)
        short_prefix: list[str] = []
        for sentence in complete_sentences:
            candidate = " ".join((*short_prefix, sentence)).strip()
            if len(candidate.split()) > limit:
                break
            short_prefix.append(sentence)
        if short_prefix:
            normalized = " ".join(short_prefix)
    if question and normalized and not normalized.endswith("?"):
        normalized = normalized.rstrip(".,;:!") + "?"
    return normalized


class ConditionalFollowUp(BaseModel):
    condition: str = ""
    question: str = ""

    @field_validator("question")
    @classmethod
    def limit_question_words(cls, value: str) -> str:
        return _limit_spoken_words(value, 14, question=True)


class LiveDebateResponse(BaseModel):
    """The small model-owned contract for the latency-critical live turn."""

    answer_now: str = ""
    counterargument: str = ""
    counter_question: str = ""
    analogy: str = ""
    primary_move: Literal["answer", "question"]
    target_claim: str
    argument_points: list[str] = Field(default_factory=list, max_length=3)
    confidence: Literal["high", "medium", "low"] = "low"
    needs_research: bool = False
    research_query: str = ""


class DebateRecommendation(BaseModel):
    session_id: str = ""
    answer_now: str = ""
    counterargument: str = ""
    counter_question: str = ""
    analogy: str = ""
    primary_move: Literal["answer", "question"] = "answer"
    question_status: Literal[
        "none", "open", "partial", "answered", "unclear", "evaded"
    ] = "none"
    open_question: str = ""
    follow_ups: list[ConditionalFollowUp] = Field(default_factory=list, max_length=2)
    target_claim: str = ""
    # A compact argument tree, not a transcript copy. It lets research target
    # one point when a speaker stacks several claims in one turn.
    argument_points: list[str] = Field(default_factory=list, max_length=12)
    atomic_claims: list[AtomicClaim] = Field(default_factory=list, max_length=12)
    logical_relations: list[LogicalRelation] = Field(default_factory=list, max_length=4)
    confidence: Literal["high", "medium", "low"] = "low"
    needs_research: bool = False
    research_query: str = ""
    research_status: Literal[
        "idle", "searching", "completed", "unavailable", "cancelled"
    ] = "idle"
    research_alert: str = ""
    sources: list[DebateSource] = Field(default_factory=list)
    analysis_status: Literal[
        "idle", "analyzing", "completed", "unavailable", "cancelled"
    ] = "idle"
    analysis_can_cancel: bool = False
    generation_id: str = ""
    analyst_provider: str = ""
    analyst_model: str = ""
    analyst_research_performed: bool = False
    analyst_prompt: str = ""
    provisional: bool = False
    claim_id: str = ""
    utterance_id: str = ""
    transcript_revision: int = 0
    claim_revision: int = 0
    directive_revision: int = 0
    config_generation: int = 0
    recommendation_revision: int = 0
    prompt_version: str = "debate_live_v2"

    @field_validator("answer_now")
    @classmethod
    def limit_answer_words(cls, value: str) -> str:
        return _limit_spoken_words(value, 25)

    @field_validator("counter_question")
    @classmethod
    def limit_counter_question_words(cls, value: str) -> str:
        return _limit_spoken_words(value, 14, question=True)


def build_atomic_claims(
    recommendation: DebateRecommendation,
    *,
    parent_claim_id: str,
    speaker_id: str = "",
) -> list[AtomicClaim]:
    """Reuse model-extracted points; never split blindly on punctuation."""
    original = recommendation.target_claim.strip()
    candidates = [" ".join(point.split()) for point in recommendation.argument_points]
    candidates = [point for point in candidates if point]
    if not candidates and original:
        candidates = [original]
    folded_original = original.casefold()
    pieces: list[tuple[str, int, int, bool]] = []
    covered: list[tuple[int, int]] = []
    search_from = 0
    for point in candidates:
        start = folded_original.find(point.casefold(), search_from) if original else -1
        if start < 0 and original:
            start = folded_original.find(point.casefold())
        end = start + len(point) if start >= 0 else -1
        if start >= 0:
            covered.append((start, end))
            search_from = end
        pieces.append((point, start, end, start < 0))

    # Every original character carrying content must remain represented even
    # when the model omitted, reordered, or paraphrased one part.  Source
    # slices are kept verbatim so numbers, units, conditions and alternatives
    # cannot disappear during atomization.
    if original:
        cursor = 0
        for start, end in sorted(covered):
            if start > cursor:
                gap_start, gap_end = cursor, start
                gap = original[gap_start:gap_end].strip(" \t\r\n,;:-")
                if gap and re.search(r"\w", gap):
                    real_start = original.find(gap, gap_start, gap_end)
                    pieces.append((gap, real_start, real_start + len(gap), True))
            cursor = max(cursor, end)
        if cursor < len(original):
            gap = original[cursor:].strip(" \t\r\n,;:-")
            if gap and re.search(r"\w", gap):
                real_start = original.find(gap, cursor)
                pieces.append((gap, real_start, real_start + len(gap), True))
        if not covered and not any(piece[1] >= 0 for piece in pieces):
            pieces.insert(0, (original, 0, len(original), True))

    # Exact source spans come first. If the model returned paraphrases as well,
    # they remain useful grouped interpretations but never displace coverage.
    pieces.sort(key=lambda item: (item[1] < 0, item[1] if item[1] >= 0 else 10**9, item[0].casefold()))
    deduped: list[tuple[str, int, int, bool]] = []
    seen = set()
    for piece in pieces:
        key = (piece[0].casefold(), piece[1], piece[2])
        if key not in seen:
            seen.add(key)
            deduped.append(piece)
    if len(deduped) > 12:
        # Preserve full source coverage in one final compound atom rather than
        # silently dropping the tail.
        head = deduped[:11]
        tail = deduped[11:]
        source_tail = [item for item in tail if item[1] >= 0]
        if source_tail:
            start = min(item[1] for item in source_tail)
            end = max(item[2] for item in source_tail)
            head.append((original[start:end], start, end, True))
        else:
            head.append((" / ".join(item[0] for item in tail), -1, -1, True))
        deduped = head

    claims: list[AtomicClaim] = []
    for point, start, end, grouped in deduped:
        folded = point.casefold()
        quantifier = next(
            (
                term
                for term in ("alle", "jeder", "immer", "nie", "manche", "meist")
                if re.search(rf"\b{re.escape(term)}\b", folded)
            ),
            "",
        )
        temporal_scope = next(
            (term for term in ("heute", "gestern", "morgen", "früher", "derzeit", "künftig") if term in folded),
            "",
        )
        condition_match = re.search(
            r"\b(?:wenn|falls|sofern|vorausgesetzt|unter der bedingung)\b.{0,180}",
            point,
            re.IGNORECASE,
        )
        stable_seed = f"{parent_claim_id}\0{start}\0{end}\0{point.casefold()}"
        claims.append(AtomicClaim(
            id="atomic-" + hashlib.sha256(stable_seed.encode("utf-8")).hexdigest()[:20],
            parent_claim_id=parent_claim_id,
            text=point,
            start=start,
            end=end,
            speaker_id=speaker_id,
            negated=bool(re.search(r"\b(nicht|kein|keine|nie|niemals)\b", folded)),
            quantifier=quantifier,
            temporal_scope=temporal_scope,
            condition=(condition_match.group(0).strip() if condition_match else ""),
            grouped=grouped or len(deduped) == 1,
        ))
    return claims


class ObjectionHandlerOutput(BaseModel):
    recommendation: DebateRecommendation = Field(default_factory=DebateRecommendation)
    items: list[ObjectionHandlerItem] = Field(default_factory=list)


def _has_speakable_guidance(
    recommendation: DebateRecommendation, require_analogy: bool = False
) -> bool:
    primary_text = (
        recommendation.counter_question
        if recommendation.primary_move == "question"
        else recommendation.answer_now
    )
    return bool(primary_text.strip()) and (
        not require_analogy or bool(recommendation.analogy.strip())
    )


def _has_any_guidance(recommendation: DebateRecommendation) -> bool:
    """Return whether the model supplied any actual response material.

    A schema-valid recommendation may intentionally contain no advice when the
    latest window does not warrant an intervention.  That is a normal live
    outcome, not a malformed response requiring a second provider call.  The
    check deliberately ignores control metadata such as ``primary_move`` and
    confidence, which are populated by defaults even for an empty answer.
    """
    return any(
        text.strip()
        for text in (
            recommendation.answer_now,
            recommendation.counterargument,
            recommendation.counter_question,
            recommendation.analogy,
            recommendation.open_question,
        )
    ) or any(
        follow_up.question.strip() for follow_up in recommendation.follow_ups
    )


def _compact_live_context(value: str) -> str:
    """Keep user-supplied debate context, not generic meeting boilerplate."""
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    selected = [
        line
        for line in lines
        if line.startswith(("Meeting type:", "User-provided context:"))
    ]
    return "\n".join(selected) if selected else value[:800]


_MODE_INSTRUCTIONS = {
    "persuasive": (
        "\n\n## MODUS UEBERZEUGEND\nNutze einen knappen Steelman und eine "
        "gemeinsame Basis, bevor du die schwaechste tragende Praemisse widerlegst. "
        "Bleibe im eigenen Lager anschlussfaehig und erreiche unentschlossene Mitleser."
    ),
    "forceful": (
        "\n\n## MODUS BRUTAL-SACHLICH\nGreife die konkrete Behauptung hart in der "
        "Sache an, nie die Person. Pruefe Position, Beweislast und Konsistenz; "
        "benenne besonders eine Ausnahme fuer sich selbst oder eine unbelegte Folgerung."
    ),
}

_STYLE_INSTRUCTIONS = {
    "balanced": "",
    "natural": (
        "\n\n## STIL NATUERLICH\nFormuliere wie in gesprochenem Deutsch: kurze "
        "Hauptsaetze, konkrete Verben, keine Seminarfloskeln und keine kuenstliche "
        "Dreierliste. Eine kleine Unvollkommenheit ist besser als Robotersprache."
    ),
    "concise": (
        "\n\n## STIL KNAPP\nStreiche Einleitung und Wiederholung. Beginne mit dem "
        "entscheidenden Verb oder Gegensatz und ende nach genau einem Gedanken."
    ),
    "evidence": (
        "\n\n## STIL BELEGBASIERT\nTrenne Behauptung, Belegstatus und Schluss sichtbar. "
        "Bei fehlendem Beleg Unsicherheit benennen und die engste pruefbare Frage stellen."
    ),
}

_LIVE_POSITION_INSTRUCTIONS = (
    "\n\nCoache nur die Nutzerseite. Staerke ihre aktuelle Position ehrlich, "
    "ohne Fakten zu erfinden oder zur Gegenseite zu wechseln."
)

_ANALOGY_INSTRUCTION_DEFAULTS = {
    True: (
        "## ANALOGIE\nDie beste kurze, sachlich passende Analogie MUSS in "
        "`analogy` mitgeliefert werden. Sie darf keinen Beleg ersetzen."
    ),
    False: (
        "## ANALOGIE\nEine Analogie nur liefern, wenn sie den konkreten Punkt "
        "wirklich klarer macht; sonst `analogy` leer lassen."
    ),
}


def _mode_instruction(mode: str) -> str:
    fallback = _MODE_INSTRUCTIONS.get(mode, _MODE_INSTRUCTIONS["persuasive"])
    return load_prompt_resource(f"mode.{mode}", fallback)


def _style_instruction(style: str) -> str:
    fallback = _STYLE_INSTRUCTIONS.get(style, "")
    if not fallback:
        return ""
    return load_prompt_resource(f"style.{style}", fallback)


def _position_instruction() -> str:
    return load_prompt_resource("debate_user_loyalty", _LIVE_POSITION_INSTRUCTIONS)


def _analogy_instruction(required: bool) -> str:
    name = "analogy.required" if required else "analogy.optional"
    return load_prompt_resource(name, _ANALOGY_INSTRUCTION_DEFAULTS[required])

_FOCUS_STOPWORDS = {
    "aber", "also", "auch", "bisschen", "dann", "das", "dass", "denn",
    "der", "die", "doch", "ein", "eine", "einem", "einen", "einer", "es",
    "halt", "hier", "ich", "ist", "ja", "kann", "mal", "mehr", "mich",
    "mir", "nicht", "noch", "nur", "oder", "schon", "sehr", "sie", "so",
    "und", "vom", "von", "war", "was", "wie", "wir", "wird", "zu", "zum",
}


def _turn_text(line: str) -> str:
    match = re.match(r"^\[([^\]]+)\]:\s*(.*)$", line.strip())
    return (match.group(2) if match else line).strip()


def _focus_terms(line: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[\wäöüß]+", _turn_text(line).casefold())
        if len(token) >= 3 and token not in _FOCUS_STOPWORDS
    ]


def _select_focus_turn(transcript_window: str) -> str:
    """Prefer the newest substantive claim over a trailing filler fragment."""
    lines = [line.strip() for line in transcript_window.splitlines() if line.strip()]
    if not lines:
        return "die letzte Aussage"
    latest = lines[-1]
    latest_text = _turn_text(latest)
    latest_terms = _focus_terms(latest)
    if latest_text.endswith("?") or len(latest_terms) >= 3:
        return latest

    candidates = lines[-6:]
    best = max(
        candidates,
        key=lambda line: (
            len(_focus_terms(line)),
            bool(re.search(r"\d", _turn_text(line))),
            len(_turn_text(line)),
        ),
    )
    return best if len(_focus_terms(best)) >= len(latest_terms) + 2 else latest


def _normalize_speaker_id(
    raw: object,
    valid_speaker_ids: set[str],
    aliases: dict[str, str] | None = None,
) -> str | None:
    """A participant tag or a raw UUID, as a known speaker UUID or None."""
    return resolve_speaker_reference(raw, aliases, valid_speaker_ids)


def _compose_rationale(item: dict) -> str:
    """Fold the micro/macro fields into the insight rationale."""
    parts = []
    response_now = item.get("response_now")
    if isinstance(response_now, str) and response_now.strip():
        parts.append(f"Respond now: {response_now.strip()}")
    bigger_picture = item.get("bigger_picture")
    if isinstance(bigger_picture, str) and bigger_picture.strip():
        parts.append(f"Bigger picture: {bigger_picture.strip()}")
    severity = item.get("severity")
    if isinstance(severity, str) and severity.strip().lower() in VALID_SEVERITIES:
        parts.append(f"(Severity: {severity.strip().lower()})")
    return " ".join(parts)


class ObjectionHandlerAgent:
    """Fast-cycle scanner that flags objections with a ready response."""

    def __init__(
        self,
        model_override: str | None = None,
        prompt_override: str | None = None,
        meeting_context_text: str | None = None,
        session_id: uuid.UUID | None = None,
        debate_mode: Literal["persuasive", "forceful"] = "persuasive",
        always_analogy: bool = False,
        style_focus: Literal["balanced", "natural", "concise", "evidence"] = "balanced",
        recommendation_only: bool = False,
    ):
        self._model = DEFAULT_OBJECTION_MODEL if model_override is None else model_override
        self._prompt_resource_name: str | None = None
        built_in_prompt = prompt_override in {
            None,
            "",
            OBJECTION_HANDLER_PROMPT,
            DEBATE_RECOMMENDATION_PROMPT,
        }
        if recommendation_only and built_in_prompt:
            self._prompt_template = DEBATE_RECOMMENDATION_PROMPT
            self._prompt_resource_name = "debate_live_v2"
        elif prompt_override and prompt_override != OBJECTION_HANDLER_PROMPT:
            self._prompt_template = prompt_override
            self._prompt_resource_name = "agent.objection_handler"
        else:
            self._prompt_template = prompt_override or OBJECTION_HANDLER_PROMPT
        self.meeting_context_text = meeting_context_text or build_meeting_context_text()
        self._recent_objections: deque[str] = deque(maxlen=_MAX_RECENT_OBJECTIONS)
        self._last_window = ""
        self._session_id = session_id
        self._debate_mode = debate_mode
        self._always_analogy = always_analogy
        self._style_focus = style_focus
        self._recommendation_only = recommendation_only
        self.last_outcome: dict | None = None
        self.latest_recommendation = DebateRecommendation()
        self._conversation_state: dict[str, object] | None = None

    def _current_prompt_template(self) -> str:
        if self._prompt_resource_name is None:
            return self._prompt_template
        return load_prompt_resource(
            self._prompt_resource_name,
            self._prompt_template,
        )

    def update_meeting_context(self, meeting_context_text: str):
        self.meeting_context_text = meeting_context_text
        # Clear the unchanged-window skip so the current window is rescanned with the new context.
        self._last_window = ""

    def update_debate_mode(self, debate_mode: Literal["persuasive", "forceful"]):
        """Apply a preconfigured debate template without rebuilding the agent."""
        self._debate_mode = debate_mode
        self._last_window = ""

    def request_rescan(self) -> None:
        """Run the existing model path again after a control-only directive."""
        self._last_window = ""

    async def run_cycle(
        self,
        transcript_window: str,
        directives: list[str],
        speakers: list[dict],
        support_context: str = "",
        on_model_partial: Callable[[DebateRecommendation], Awaitable[None]] | None = None,
        resource_profile: Literal["balanced", "economy"] = "balanced",
    ) -> list[dict]:
        """Execute one fast scan. Returns list of objection insight dicts."""
        # No new speech since the last scan — skip the LLM call entirely.
        if transcript_window == self._last_window:
            self.last_outcome = {
                "kind": "skipped_unchanged",
                "detail": "No new speech since the last check.",
                "items": 0,
            }
            return []
        live_directives = [" ".join(d.split())[:240] for d in directives[-4:]]
        directives_text = "\n".join(f"- {d}" for d in live_directives) if live_directives else "(No directives set)"
        aliases = build_speaker_aliases(speakers)
        speakers_text = format_speakers_list(speakers, aliases)
        valid_speaker_ids = {str(s["id"]) for s in speakers if s.get("id")}
        if self._recent_objections:
            recent_text = "\n".join(f'- "{o}"' for o in self._recent_objections)
        else:
            recent_text = "(No objections surfaced yet)"
        latest_turn = _select_focus_turn(transcript_window)
        live_transcript = (
            latest_turn
            if self._recommendation_only and latest_turn
            else transcript_window
        )

        system, prompt = format_prompt_layers(
            self._current_prompt_template(),
            (
                _compact_live_context(self.meeting_context_text)
                if self._recommendation_only
                else self.meeting_context_text
            ),
            transcript_window=live_transcript,
            directives_text=directives_text,
            speakers_text=speakers_text,
            recent_objections=recent_text,
        )
        system += "\n\n" + _mode_instruction(self._debate_mode)
        system += "\n\n" + _analogy_instruction(self._always_analogy)
        if not self._recommendation_only:
            system += "\n\n" + _style_instruction(self._style_focus)
            system += "\n\n" + _position_instruction()
        if self._conversation_state is not None and not self._recommendation_only:
            prompt += (
                "\n\n## Kompakter bisheriger Debattenzustand\n"
                + json.dumps(self._conversation_state, ensure_ascii=False)
                + "\nBewerte diesen Zustand anhand der neuesten Aussage neu. "
                "Uebernimm ihn nicht, wenn der neue Verlauf ihn schliesst oder widerlegt."
            )
        if support_context.strip():
            prompt += (
                "\n\n## Verdichtete Hintergrundanalyse\n"
                + support_context.strip()
                + "\nNutze davon nur unmittelbar relevante, belastbare Hinweise. "
                "Erfinde keine Belege und wiederhole die Liste nicht."
            )
        if latest_turn:
            prompt += (
                "\n\n## VERBINDLICHER AKTUELLER ZUG\n"
                + latest_turn
                + "\nAntworte genau auf diesen Zug. Aeltere Zeilen sind nur Kontext. "
                "Setze target_claim auf dessen konkrete Behauptung oder Frage."
            )
        # Qwen's switch is positional: after the dynamic transcript and support
        # blocks it must be the final instruction, not merely the first line of
        # the static template. Otherwise Ollama can spend the live budget on a
        # hidden reasoning trace and truncate the required spoken JSON fields.
        prompt = prompt.rstrip() + "\n\n/no_think"

        async def request_guidance(
            request_prompt: str,
            *,
            stream_first_answer: bool = False,
        ) -> ObjectionHandlerOutput:
            schema = LiveDebateResponse if self._recommendation_only else ObjectionHandlerOutput

            async def publish_partial(answer_now: str) -> None:
                if on_model_partial is None:
                    return
                await on_model_partial(DebateRecommendation(
                    answer_now=answer_now,
                    target_claim=latest_turn,
                    confidence="low",
                    provisional=True,
                ))

            generated = await generate_json(
                self._model,
                request_prompt,
                schema,
                session_id=self._session_id,
                source="debate_copilot",
                reasoning_effort="none",
                system=system,
                on_partial_json=(
                    publish_partial
                    if stream_first_answer and self._recommendation_only
                    else None
                ),
                resource_profile=resource_profile,
            )
            if isinstance(generated, LiveDebateResponse):
                data = generated.model_dump()
                has_question = bool(generated.counter_question.strip())
                return ObjectionHandlerOutput(
                    recommendation=DebateRecommendation(
                        **data,
                        question_status="open" if has_question else "none",
                        open_question=generated.counter_question,
                    )
                )
            if isinstance(generated, DebateRecommendation):
                return ObjectionHandlerOutput(recommendation=generated)
            return generated

        guidance_error: Exception | None = None
        try:
            first_output = await request_guidance(prompt, stream_first_answer=True)
        except Exception as e:
            logger.error(f"[objection_handler] API call failed: {e}")
            if isinstance(e, (json.JSONDecodeError, ValidationError)):
                self.last_outcome = {
                    "kind": "parse_failed",
                    "detail": f"The structured reply was not usable: {e}",
                    "items": 0,
                }
            else:
                self.last_outcome = {
                    "kind": "error",
                    "error": classify_error(e, self._model),
                }
            self.latest_recommendation = DebateRecommendation()
            return []

        output = first_output
        guidance_empty = False
        if not _has_speakable_guidance(
            first_output.recommendation, self._always_analogy
        ):
            if not _has_any_guidance(first_output.recommendation):
                # A syntactically valid empty recommendation is an explicit
                # no-op.  Do not spend another live-call request trying to
                # manufacture advice that the model did not find warranted.
                guidance_empty = True
            else:
                primary_field = (
                    "counter_question"
                    if first_output.recommendation.primary_move == "question"
                    else "answer_now"
                )
                analogy_requirement = (
                    " `analogy` MUSS zusaetzlich eine kurze sachlich passende "
                    "Analogie enthalten."
                    if self._always_analogy
                    else " `analogy` bleibt optional."
                )
                try:
                    retry_output = await request_guidance(
                        prompt
                        + "\n\nKRITISCHE KORREKTUR: Der gewaehlte Hauptbeitrag war leer. "
                        f"Fuellen Sie `{primary_field}` mit genau einem kurzen, sofort "
                        "aussprechbaren deutschen Beitrag. Andere Sprechoptionen duerfen "
                        f"leer bleiben.{analogy_requirement}"
                    )
                except Exception as exc:
                    guidance_error = exc
                else:
                    if _has_speakable_guidance(
                        retry_output.recommendation, self._always_analogy
                    ):
                        output = retry_output.model_copy(
                            update={
                                "items": [*first_output.items, *retry_output.items],
                            }
                        )
                    else:
                        guidance_error = ValueError(
                            "The model returned incomplete debate guidance twice."
                        )

        self.latest_recommendation = output.recommendation
        if _has_speakable_guidance(output.recommendation, self._always_analogy):
            self._conversation_state = {
                "primary_move": output.recommendation.primary_move,
                "question_status": output.recommendation.question_status,
                "open_question": output.recommendation.open_question,
                "follow_ups": [
                    follow_up.model_dump()
                    for follow_up in output.recommendation.follow_ups
                ],
                "argument_points": output.recommendation.argument_points,
                "target_claim": output.recommendation.target_claim,
            }
        elif guidance_empty:
            self._conversation_state = {}
        raw_items = [item.model_dump(exclude_unset=True) for item in output.items]
        items = self._parse_response(raw_items, valid_speaker_ids)
        for item in items:
            self._recent_objections.append(item["question"])
        if guidance_error is not None:
            self.last_outcome = {
                "kind": "error",
                "error": classify_error(guidance_error, self._model),
            }
        elif guidance_empty:
            self.last_outcome = {
                "kind": "no_guidance",
                "detail": "No immediate debate guidance was warranted.",
                "items": len(items),
            }
        elif items:
            logger.info(f"[objection_handler] flagged {len(items)} objection(s)")
            self.last_outcome = {
                "kind": "insights",
                "detail": f"{len(items)} objection{'s' if len(items) != 1 else ''} surfaced",
                "items": len(items),
            }
        elif not raw_items:
            self.last_outcome = {
                "kind": "no_findings",
                "detail": "No new objection was found.",
                "items": 0,
            }
        else:
            self.last_outcome = {
                "kind": "all_filtered",
                "detail": (
                    f"{len(raw_items)} structured item"
                    f"{'s' if len(raw_items) != 1 else ''} yielded 0 usable items"
                ),
                "items": 0,
            }
        # Mark only a fully successful cycle. Provider/validation failures,
        # including a failed corrective request, must remain retryable.
        if guidance_error is None:
            self._last_window = transcript_window
        return items

    async def refine_with_sources(
        self,
        recommendation: DebateRecommendation,
        sources: list[DebateSource],
        *,
        model_override: str | None = None,
    ) -> DebateRecommendation:
        """Turn verified, claim-linked source excerpts into sharper spoken guidance."""
        if not sources:
            return recommendation.model_copy(
                update={"research_status": "unavailable", "sources": []}
            )
        readable_sources = [source for source in sources if source.passage.strip()]
        if not readable_sources:
            return recommendation.model_copy(update={
                "needs_research": False,
                "research_status": "completed",
                "sources": sources,
            })
        source_payload = [source.model_dump() for source in readable_sources]
        prompt = (
            "Ueberarbeite die folgende Live-Debattenempfehlung anhand der "
            "verifizierbaren Quellen. Nutze nur Aussagen, die in den Auszuegen "
            "stehen, nenne keine erfundene Genauigkeit und formuliere jeden "
            "Ein fehlender oder nicht gelesener Beleg bedeutet unklar, niemals falsch. "
            "Sprechtext in hoechstens 1-2 kurzen deutschen Saetzen. Verknuepfe "
            "die Evidenz konkret mit target_claim. Extrahiere vorrangig "
            "widerlegende Fakten, amtliche Statistiken, Zahlen, Prozentwerte, "
            "Groessenordnungen und relevante Daten. Wenn ein solcher Wert im "
            "Quellenauszug steht und den Punkt wirklich traegt, formuliere den "
            "staerksten Wert oder Fakt direkt in answer_now oder counterargument "
            "ein und nenne die Quelle knapp. Pruefe dabei Zeitraum, Grundgesamtheit "
            "und Bezugswert; uebertrage Zahlen nie auf einen anderen Kontext.\n\n"
            "Bewahre beide Sprechoptionen, primary_move, question_status, "
            "open_question und follow_ups, sofern die verifizierte Evidenz sie "
            "nicht materiell aendert. Erfinde insbesondere kein Ausweichen. "
            "Setze argument_points nach der Recherche auf die 1-3 staerksten "
            "quellengetragene Gegenargumente. Jeder Punkt muss kurz, allgemein "
            "verstaendlich und direkt nutzbar sein; nenne darin einen tragenden "
            "Fakt oder Zahlenwert, wenn die Quelle ihn wirklich belegt. Keine "
            "Dopplungen und keine Recherche-Methodik. Wenn eine Quelle "
            "target_claim direkt widerlegt, eine Uebersetzung falsch erscheinen "
            "laesst oder die behauptete Interpretation im Originalkontext nicht "
            "traegt, setze research_alert auf einen kurzen deutschen Alarm mit "
            "dem entscheidenden Gegenbeleg; sonst leer lassen. "
            "Bewahre oder verbessere auch analogy; sie muss kurz, treffend und "
            "ohne erfundene Tatsachen sein. Gib fuer jede gelesene Quelle unter "
            "sources dieselbe URL mit claim_relation supports, contradicts oder "
            "unclear zur konkreten target_claim zurueck. Ein Suchtreffer allein "
            "ist nie supports.\n\n"
            f"Bisherige Empfehlung:\n{json.dumps(recommendation.model_dump(), ensure_ascii=False)}\n\n"
            f"Quellen:\n{json.dumps(source_payload, ensure_ascii=False)}"
        )
        default_research_instruction = prompt.split("\n\nBisherige Empfehlung:", 1)[0]
        prompt = (
            load_prompt_resource("research_source_refinement", default_research_instruction)
            + f"\n\nBisherige Empfehlung:\n{json.dumps(recommendation.model_dump(), ensure_ascii=False)}"
            + f"\n\nQuellen:\n{json.dumps(source_payload, ensure_ascii=False)}"
        )
        default_system = (
            "/no_think\nDu bist ein schneller deutschsprachiger Debatten-Coach. "
            "Gib nur das verlangte strukturierte Ergebnis zurueck. "
            "answer_now, counterargument und counter_question muessen sofort "
            "aussprechbar sein."
        )
        system = load_prompt_resource(
            "research_source_system", default_system
        ) + "\n\n" + _mode_instruction(self._debate_mode) + "\n\n" + _style_instruction(self._style_focus)
        try:
            refined = await generate_json(
                model_override or self._model,
                prompt,
                DebateRecommendation,
                session_id=self._session_id,
                source="debate_copilot",
                reasoning_effort="none",
                system=system,
            )
        except Exception as exc:  # Keep the verified cards even if refinement fails.
            logger.warning("[debate_copilot] source refinement failed: %s", exc)
            refined = recommendation.model_copy()
        preserve_when_omitted = {
            field_name: getattr(recommendation, field_name)
            for field_name in (
                "answer_now",
                "counterargument",
                "counter_question",
                "analogy",
                "primary_move",
                "question_status",
                "open_question",
                "follow_ups",
                "argument_points",
                "research_alert",
            )
            if field_name not in refined.model_fields_set
        }
        assessed_by_url = {
            source.url: source
            for source in refined.sources
            if source.url and source.claim_relation in {"supports", "contradicts", "unclear"}
        }
        assessed_sources = []
        for source in sources:
            assessment = assessed_by_url.get(source.url)
            relation = assessment.claim_relation if assessment else source.claim_relation
            assessed_sources.append(source.model_copy(update={
                "claim_relation": relation,
                "verification_status": (
                    relation if relation in {"supports", "contradicts"}
                    else source.verification_status
                ),
            }))
        return refined.model_copy(
            update={
                **preserve_when_omitted,
                "needs_research": False,
                "research_query": recommendation.research_query,
                "research_status": "completed",
                "sources": assessed_sources,
                "target_claim": refined.target_claim or recommendation.target_claim,
            }
        )

    async def analyze_deep(
        self,
        recommendation: DebateRecommendation,
        *,
        model_id: str,
        own_position: str,
        relevant_context: str,
        sources: list[DebateSource],
        reasoning_effort_override: str | None = None,
        analysis_phase: str = "follow_up",
    ) -> tuple[DeepDebateAnalysis, str]:
        """Use the existing hosted model route as a debate analyst, not a search summary."""
        if model_id == "chatgpt-web:gpt-6":
            prompt_name = "background.oracle"
        elif "gemini" in model_id.casefold():
            prompt_name = "background.gemini"
        else:
            prompt_name = "background.gpt6"
        prompt = build_deep_analysis_prompt(
            claim=recommendation.target_claim,
            own_position=own_position,
            relevant_context=relevant_context,
            sources=sources,
            prompt_name=prompt_name,
        )
        phase_defaults = {
            "new_topic": "Erstelle einmalig eine belastbare Themenlandkarte mit Positionen, Prämissen, Beweislast, Gegenargumenten, offenen Fragen und Recherchebedarf.",
            "follow_up": "Nutze die vorhandene Themenanalyse wieder und bearbeite nur das neue oder noch offene Argument, ohne die gesamte Debatte zu wiederholen.",
            "deep_reanalysis": "Prüfe den entscheidenden Argumentzweig erneut in voller Tiefe, weil neues Material, ein schwerer Widerspruch oder eine ausdrückliche Tiefenanalyse vorliegt.",
        }
        phase = analysis_phase if analysis_phase in phase_defaults else "follow_up"
        prompt += "\n\n" + load_prompt_resource(
            f"phase.{phase}", phase_defaults[phase]
        )
        analysis = await generate_json(
            model_id,
            prompt,
            DeepDebateAnalysis,
            session_id=self._session_id,
            source="debate_analyst",
            reasoning_effort=(
                reasoning_effort_override or deep_analysis_reasoning_effort(model_id)
            ),
            system=load_prompt_resource(
                "background.system",
                "Du bist ein praeziser deutschsprachiger Debattenanalyst und "
                "Rechercheexperte. Analysiere nur den konkreten Argumentationszug. "
                "Gib nur die verlangten strukturierten Ergebnisse zurueck und "
                "erfinde keine Quellen.",
            ),
        )
        return analysis, prompt

    def _parse_response(
        self,
        items: list[object],
        valid_speaker_ids: set[str],
    ) -> list[dict]:
        """Normalize schema-validated objections for the insight pipeline."""
        valid = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning(
                    "[objection_handler] dropped item: expected object "
                    "(entry_type=%s)",
                    type(item).__name__,
                )
                continue
            text = item.get("question")
            if not isinstance(text, str) or not text.strip():
                logger.warning(
                    "[objection_handler] dropped item: question=%r must be "
                    "a non-empty string",
                    text,
                )
                continue
            valid.append({
                "item_type": "objection",
                "question": text.strip(),
                "rationale": _compose_rationale(item),
                "source_context": item.get("source_context", "") or "",
                "speaker_id": _normalize_speaker_id(item.get("speaker_id"), valid_speaker_ids),
                "agent_source": "objection_handler",
            })

        return valid
