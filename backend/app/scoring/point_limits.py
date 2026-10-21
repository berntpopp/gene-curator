"""Per-item point caps for ClinGen evidence tables (mirrors the editor's min/max columns).

Keyed by the evidence list's name; every row's `points` / `proband_counted_points` must be
a number between 0 and the cap. Empty values are not entered evidence and are skipped.
"""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import CurationSchema, WorkflowPair

POINT_KEYS = ("points", "proband_counted_points")
POINT_CAPS: dict[str, float] = {
    "predicted_or_proven_null": 3,
    "other_variant_type": 1.5,
    "segregation": 3,
    "single_variant_analysis": 6,
    "aggregate_variant_analysis": 6,
    "biochemical_function": 2,
    "protein_interaction": 2,
    "expression": 2,
    "patient_cells": 2,
    "non_patient_cells": 1,
    "non_human_model_organism": 4,
    "cell_culture_model": 2,
    "human": 4,  # rescue
    "cell_culture": 2,  # rescue
}


def _row_errors(path: str, index: int, row: Any, cap: float) -> list[str]:
    if not isinstance(row, dict):
        return []
    errors = []
    for key in POINT_KEYS:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = None
        if number is None or not 0 <= number <= cap:
            errors.append(
                f"{path}[{index}].{key} must be a number between 0 and {cap:g} (got {value!r})"
            )
    return errors


def point_range_errors(evidence: Any, path: str = "") -> list[str]:
    """Human-readable errors for every evidence point outside its allowed range."""
    errors: list[str] = []
    if not isinstance(evidence, dict):
        return errors
    for key, value in evidence.items():
        here = f"{path}.{key}" if path else key
        if key in POINT_CAPS and isinstance(value, list):
            for i, row in enumerate(value):
                errors += _row_errors(here, i, row, POINT_CAPS[key])
        else:
            errors += point_range_errors(value, here)
    return errors


def enforce_clingen_point_ranges(
    db: Session, workflow_pair_id: UUID, evidence: Any
) -> None:
    """422 on out-of-range points, but only for ClinGen SOP v11 curation schemas."""
    pair = db.get(WorkflowPair, workflow_pair_id)
    schema = (
        db.get(CurationSchema, pair.curation_schema_id)
        if pair and pair.curation_schema_id
        else None
    )
    if ((schema and schema.scoring_configuration) or {}).get(
        "engine"
    ) != "clingen_sop_v11":
        return
    if errors := point_range_errors(evidence):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(errors)
        )
