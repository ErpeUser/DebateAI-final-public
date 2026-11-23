"""Versioned, immutable holdout cases for the Quality Lab."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

HOLDOUT_DATASET_ID = "de-debate-holdout-v1"
HOLDOUT_VERSION = "1"

_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "public-transit-001",
        "title": "ÖPNV-Ausbau",
        "claim": "Soll eine Stadt den öffentlichen Nahverkehr ausbauen?",
        "context": "Bewerte Nutzen, Kosten und soziale Auswirkungen einer kommunalen Entscheidung.",
        "allowed_sources": [],
    },
    {
        "case_id": "school-tablets-002",
        "title": "Digitale Lernmittel",
        "claim": "Soll eine Schule Tablets für alle Lernenden bereitstellen?",
        "context": "Berücksichtige Lernqualität, Chancengleichheit, Datenschutz und laufende Kosten.",
        "allowed_sources": [],
    },
    {
        "case_id": "energy-renovation-003",
        "title": "Energetische Sanierung",
        "claim": "Soll eine Gemeinde ihre öffentlichen Gebäude energetisch sanieren?",
        "context": "Vergleiche kurzfristige Investitionen mit langfristiger Wirkung und Unsicherheit.",
        "allowed_sources": [],
    },
)


def list_cases() -> list[dict[str, Any]]:
    """Return a copy so callers cannot mutate the versioned catalog."""
    return deepcopy(list(_CASES))


def get_case(case_id: str) -> dict[str, Any] | None:
    for case in _CASES:
        if case["case_id"] == case_id:
            return deepcopy(case)
    return None
