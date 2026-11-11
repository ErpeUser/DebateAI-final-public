"""Bounded, explicit German ASR metrics. Scores are not factual truth labels."""
from __future__ import annotations

import math
import re
import unicodedata

_TOKEN = re.compile(r"[+\-\u2212]?\d+(?:[.,]\d+)*|[%\u2030\u20ac$]|[^\W\d_]+(?:['\u2019-][^\W\d_]+)*", re.UNICODE)
_NEGATIONS = {'nicht', 'nein', 'nie', 'niemals', 'kein', 'keine', 'keinen', 'keinem', 'keiner', 'ohne'}


def normalized_tokens(text: str) -> list[str]:
    return _TOKEN.findall(unicodedata.normalize('NFC', text).casefold())


def _distance(reference, hypothesis) -> tuple[int, int, int]:
    # One row of (distance, substitutions, deletions, insertions). Memory O(H).
    row = [(j, 0, 0, j) for j in range(len(hypothesis) + 1)]
    for i, expected in enumerate(reference, 1):
        current = [(i, 0, i, 0)]
        for j, actual in enumerate(hypothesis, 1):
            if expected == actual:
                current.append(row[j - 1])
                continue
            _, s, d, ins = row[j - 1]
            sub = (row[j - 1][0] + 1, s + 1, d, ins)
            _, s, d, ins = row[j]
            delete = (row[j][0] + 1, s, d + 1, ins)
            _, s, d, ins = current[j - 1]
            insert = (current[j - 1][0] + 1, s, d, ins + 1)
            # Prefer substitution on equal cost; the total edit distance is invariant.
            current.append(min((sub, delete, insert), key=lambda entry: entry[0]))
        row = current
    return row[-1][1:]


def score_transcript(reference: str, hypothesis: str) -> dict:
    if not isinstance(reference, str) or not isinstance(hypothesis, str):
        raise ValueError('Reference and hypothesis must be strings.')
    if len(reference) > 2000 or len(hypothesis) > 4000:
        raise ValueError('Transcript exceeds the calibration scoring limit.')
    ref, hyp = normalized_tokens(reference), normalized_tokens(hypothesis)
    s, d, i = _distance(ref, hyp)
    ref_chars, hyp_chars = ''.join(ref), ''.join(hyp)
    char_errors = sum(_distance(ref_chars, hyp_chars))
    return {
        'normalization': 'NFC+casefold; punctuation ignored; decimal separators retained; CER excludes spaces',
        'reference_words': len(ref), 'hypothesis_words': len(hyp),
        'substitutions': s, 'deletions': d, 'insertions': i,
        'wer': (s + d + i) / len(ref) if ref else None,
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
