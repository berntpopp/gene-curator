"""Tolerant reading of stored evidence items."""

from typing import Any


def rows(value: Any) -> list[dict[str, Any]]:
    """Evidence items from stored data: lists lose non-dict entries; a legacy
    ``{count, points}`` summary dict counts as one item; anything else is empty."""
    if isinstance(value, dict):
        return [value] if "points" in value else []
    if isinstance(value, list):
        return [i for i in value if isinstance(i, dict)]
    return []


# Defaults a new contradictory row is created with (ContradictoryEvidenceSection.vue)
_ROW_DEFAULTS = {"evidence_type": "population", "impact": "note"}
# Case-level row fields preset on a new row (GeneticEvidenceSection.vue); not entered evidence
_PRESET_KEYS = {"variant_type", "score_status"}


def has_content(value: Any) -> bool:
    """True if the value holds anything; blank rows from an untouched form row do not count."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_content(v) for v in value)
    if isinstance(value, dict):
        return any(
            has_content(v)
            for k, v in value.items()
            if k not in _PRESET_KEYS and _ROW_DEFAULTS.get(k) != v
        )
    return value is not None and value is not False


def case_row_has_content(item: dict[str, Any], default_points: float) -> bool:
    """Like has_content, but points still at the new-row default are not entered evidence."""
    if item.get("proband_counted_points") == default_points:
        item = {**item, "proband_counted_points": None}
    return has_content(item)
