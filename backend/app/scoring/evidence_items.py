"""Tolerant reading of stored evidence items."""

from typing import Any

from .case_rows import is_variant


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


def _blank(value: Any) -> bool:
    return not str(value if value is not None else "").strip()


# Reasons uncited() gives; rows with points they name score 0
UNCITED = (
    "no_pmid",
    "no_variant",
    "placeholder_variant",
    "not_scored",
    "missing_status",
)


def uncited(
    row: dict[str, Any], case_level: bool, by_status: bool = False
) -> dict[str, str] | None:
    """Why a row with points scores none (owner decisions 2026-10-27/28): with ``by_status``
    (SOP v11 case rows) a score_status other than "score" (review, contradicts:
    not_scored; blank: missing_status); no PMID; or a case-level row without a real variant
    (AD rows hold ``variant``, AR rows ``variant_1``): blank is no_variant, prose without
    HGVS, rsID or coordinate is placeholder_variant."""
    status = str(row.get("score_status") or "").strip()
    if by_status and status != "score":
        reason = "not_scored" if status else "missing_status"
        return {"field": "score_status", "reason": reason}
    if _blank(row.get("pmid")):
        return {"field": "pmid", "reason": "no_pmid"}
    variant = "variant_1" if "variant_1" in row else "variant"
    if case_level and _blank(row.get(variant)):
        return {"field": variant, "reason": "no_variant"}
    if case_level and not is_variant(row.get(variant)):
        return {"field": variant, "reason": "placeholder_variant"}
    return None


def indexed(value: Any) -> list[tuple[int, dict[str, Any]]]:
    """(index, row) pairs like ``rows``; indices stay those of the stored list, so a row
    dropped as None (unknown PMID) does not shift the paths of the rows after it."""
    items = value if isinstance(value, list) else rows(value)
    return [(i, row) for i, row in enumerate(items) if isinstance(row, dict)]
