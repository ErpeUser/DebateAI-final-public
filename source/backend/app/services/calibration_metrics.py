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

_TOKEN = re.compile(r"[+\-\u2212]?\d+(?:[.,]\d+)*|[%\u2030\u20ac$]|[^\W\d_]+(?:['\u2019-][^\W\d_]+)*", re.UNICODE)
_NEGATIONS = {'nicht', 'nein', 'nie', 'niemals', 'kein', 'keine', 'keinen', 'keinem', 'keiner', 'ohne'}


def normalized_tokens(text: str) -> list[str]:
    return _TOKEN.findall(unicodedata.normalize('NFC', text).casefold())


def score_transcript(reference: str, hypothesis: str) -> dict:
    if not isinstance(reference, str) or not isinstance(hypothesis, str):
        raise ValueError('Reference and hypothesis must be strings.')
    if len(reference) > 2000 or len(hypothesis) > 4000:
        raise ValueError('Transcript exceeds the calibration scoring limit.')
    ref, hyp = normalized_tokens(reference), normalized_tokens(hypothesis)
    # Join product tokens explicitly so JiWER does not discard decimal
    # separators, signs, percent symbols or currency units.
    word_output = jiwer.process_words(' '.join(ref), ' '.join(hyp))
    char_output = jiwer.process_characters(''.join(ref), ''.join(hyp))
    s, d, i = (
        int(word_output.substitutions),
        int(word_output.deletions),
        int(word_output.insertions),
    )
    ref_chars, hyp_chars = ''.join(ref), ''.join(hyp)
    char_errors = (
        int(char_output.substitutions)
        + int(char_output.deletions)
        + int(char_output.insertions)
    )
    return {
        'normalization': 'NFC+casefold; punctuation ignored; decimal separators retained; CER excludes spaces',
        'reference_words': len(ref), 'hypothesis_words': len(hyp),
        'substitutions': s, 'deletions': d, 'insertions': i,
        'wer': float(word_output.wer) if ref else None,
        'cer': char_errors / len(ref_chars) if ref_chars else None,
        'hallucinated_words': len(hyp) if not ref else None,
        'critical_reference_tokens': [t for t in ref if t in _NEGATIONS or any(c.isdigit() for c in t) or t in {'%', '\u2030', '\u20ac', '$'}],
        'critical_hypothesis_tokens': [t for t in hyp if t in _NEGATIONS or any(c.isdigit() for c in t) or t in {'%', '\u2030', '\u20ac', '$'}],
        'factual_status': 'unverified',
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not 0 <= fraction <= 1 or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError('Percentiles require finite nonnegative durations.')
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)
