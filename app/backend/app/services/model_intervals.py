"""Shared, fault-tolerant parsing of per-model interval configuration."""

import json


def parse_model_intervals(raw: str) -> dict[str, int]:
    """Decode numeric intervals without letting malformed config break a cycle.

    Preserve the historical behavior for valid integers/floats (including zero
    and negatives). Bool and non-numeric values are not intervals; non-finite
    JSON floats are ignored instead of crashing int(NaN/Infinity).
    """
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}

    intervals: dict[str, int] = {}
    for key, value in data.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        try:
            intervals[str(key)] = int(value)
        except (ValueError, OverflowError):
            continue
    return intervals
