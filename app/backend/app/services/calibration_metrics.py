"""Bounded, explicit German ASR metrics backed by JiWER/RapidFuzz.

Scores are not factual truth labels. Tokenization remains product-specific
so German decimals, units, negations and names are preserved before JiWER
computes the standard edit distance and WER/CER outputs.
"""

from __future__ import annotations

import math
import re
import unicodedata

import jiwer

_TOKEN = re.compile(
    r"[+\-−]?\d+(?:[.,]\d+)*|[%‰€$]|[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE
)
_NEGATIONS = {
    "nicht",
    "nein",
    "nie",
    "niemals",
    "kein",
    "keine",
    "keinen",
    "keinem",
    "keiner",
    "ohne",
}


def normalized_tokens(text: str) -> list[str]:
    return _TOKEN.findall(unicodedata.normalize("NFC", text).casefold())


def _critical_token(token: str) -> bool:
    return (
        token in _NEGATIONS
        or any(char.isdigit() for char in token)
        or token in {"%", "‰", "€", "$"}
    )


def _deleted_reference_tokens(word_output, reference_tokens: list[str]) -> list[str]:
    deleted: list[str] = []
    for alignment in getattr(word_output, "alignments", []) or []:
        for chunk in alignment:
            if getattr(chunk, "type", "") == "delete":
                deleted.extend(
                    reference_tokens[chunk.ref_start_idx : chunk.ref_end_idx]
                )
    return deleted


def score_transcript(reference: str, hypothesis: str) -> dict:
    if not isinstance(reference, str) or not isinstance(hypothesis, str):
        raise ValueError("Reference and hypothesis must be strings.")
    if len(reference) > 2000 or len(hypothesis) > 4000:
        raise ValueError("Transcript exceeds the calibration scoring limit.")
    ref, hyp = normalized_tokens(reference), normalized_tokens(hypothesis)
    if not ref:
        # JiWER rejects an empty reference in newer releases. Calibration
        # still needs to represent silence and hallucinated speech explicitly.
        return {
            "normalization": "NFC+casefold; punctuation ignored; decimal separators retained; CER excludes spaces",
            "reference_words": 0,
            "hypothesis_words": len(hyp),
            "substitutions": 0,
            "deletions": 0,
            "insertions": len(hyp),
            "wer": None,
            "cer": None,
            "hallucinated_words": len(hyp),
            "critical_reference_tokens": [],
            "critical_hypothesis_tokens": [
                token for token in hyp if _critical_token(token)
            ],
            "deleted_reference_tokens": [],
            "false_deletions": 0,
            "false_deletion_tokens": [],
            "factual_status": "unverified",
        }
    # Join product tokens explicitly so JiWER does not discard decimal
    # separators, signs, percent symbols or currency units.
    word_output = jiwer.process_words(" ".join(ref), " ".join(hyp))
    char_output = jiwer.process_characters("".join(ref), "".join(hyp))
    substitutions = int(word_output.substitutions)
    deletions = int(word_output.deletions)
    insertions = int(word_output.insertions)
    ref_chars = "".join(ref)
    char_errors = (
        int(char_output.substitutions)
        + int(char_output.deletions)
        + int(char_output.insertions)
    )
    critical_reference_tokens = [token for token in ref if _critical_token(token)]
    critical_hypothesis_tokens = [token for token in hyp if _critical_token(token)]
    deleted_reference_tokens = _deleted_reference_tokens(word_output, ref)
    false_deletion_tokens = [
        token for token in deleted_reference_tokens if _critical_token(token)
    ]
    return {
        "normalization": "NFC+casefold; punctuation ignored; decimal separators retained; CER excludes spaces",
        "reference_words": len(ref),
        "hypothesis_words": len(hyp),
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "wer": float(word_output.wer) if ref else None,
        "cer": char_errors / len(ref_chars) if ref_chars else None,
        "hallucinated_words": len(hyp) if not ref else None,
        "critical_reference_tokens": critical_reference_tokens,
        "critical_hypothesis_tokens": critical_hypothesis_tokens,
        "deleted_reference_tokens": deleted_reference_tokens,
        "false_deletions": len(false_deletion_tokens),
        "false_deletion_tokens": false_deletion_tokens,
        "factual_status": "unverified",
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not 0 <= fraction <= 1 or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("Percentiles require finite nonnegative durations.")
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)
