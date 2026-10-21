"""Per-item point ranges from the pinned point model, and the pinned scoring config itself.

Every row's `points` / `proband_counted_points` must be a number inside its evidence type's
`range`. Empty values are not entered evidence and are skipped.
"""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CurationSchema, WorkflowPair
from app.models.methodology import MethodologyVersion

from .clingen import ENGINE_NAME
from .point_model import point_model, template

POINT_KEYS = ("points", "proband_counted_points")
Ranges = dict[str, tuple[float, float]]


def scoring_configuration(
    db: Session, workflow_pair_id: UUID | None, version_id: UUID | None = None
) -> dict[str, Any]:
    """Scoring config of the pinned version, else the latest version of the pair's schema.

    Without any published version (SQLite tests; PostgreSQL always has one after 042) the
    live schema's config applies."""
    pair = db.get(WorkflowPair, workflow_pair_id) if workflow_pair_id else None
    if version_id is None and pair is not None:
        version_id = db.scalar(
            select(MethodologyVersion.id)
            .where(MethodologyVersion.schema_id == pair.curation_schema_id)
            .order_by(MethodologyVersion.version.desc())
            .limit(1)
        )
    if version_id is not None:
        version = db.get(MethodologyVersion, version_id)
        config = (
            (version.snapshot or {}).get("scoring_configuration") if version else None
        )
    else:
        schema_id = pair.curation_schema_id if pair else None
        schema = db.get(CurationSchema, schema_id) if schema_id else None
        config = schema.scoring_configuration if schema else None
    return config if isinstance(config, dict) else {}


def point_ranges(model: dict[str, Any]) -> Ranges:
    """{type path: (min, max)} for every type with a range.

    Paths are relative to their section, so AD and AR ``other_variant_type`` keep their own
    ranges; stored evidence matches a type by path suffix."""
    return {
        t["path"]: (float(t["range"][0]), float(t["range"][1]))
        for s in model["sections"]
        for c in s["categories"]
        for t in c["types"]
        if "range" in t
    }


def _limits(path: str, ranges: Ranges) -> tuple[float, float] | None:
    """The type's range by path suffix; for an unknown parent path, the narrowest range of
    the types sharing its last segment (a shape we do not know gets the strictest check)."""
    for type_path, limits in ranges.items():
        if path == type_path or path.endswith(f".{type_path}"):
            return limits
    leaf = path.rsplit(".", 1)[-1]
    same = [v for k, v in ranges.items() if k.rsplit(".", 1)[-1] == leaf]
    return min(same, key=lambda limits: limits[1], default=None)


def _row_errors(
    path: str, index: int, row: Any, limits: tuple[float, float]
) -> list[str]:
    if not isinstance(row, dict):
        return []
    low, high = limits
    errors = []
    for key in POINT_KEYS:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = None
        if number is None or not low <= number <= high:
            errors.append(
                f"{path}[{index}].{key} must be a number between {low:g} and {high:g} (got {value!r})"
            )
    return errors


def point_range_errors(
    evidence: Any, path: str = "", ranges: Ranges | None = None
) -> list[str]:
    """Human-readable errors for every evidence point outside its allowed range."""
    if ranges is None:
        model = template(ENGINE_NAME)
        ranges = point_ranges(model) if model else {}
    errors: list[str] = []
    if not isinstance(evidence, dict):
        return errors
    for key, value in evidence.items():
        here = f"{path}.{key}" if path else key
        limits = _limits(here, ranges) if isinstance(value, list) else None
        if limits is not None:
            for i, row in enumerate(value):
                errors += _row_errors(here, i, row, limits)
        else:
            errors += point_range_errors(value, here, ranges)
    return errors


def enforce_clingen_point_ranges(
    db: Session,
    workflow_pair_id: UUID,
    evidence: Any,
    methodology_version_id: UUID | None = None,
) -> None:
    """422 on out-of-range points, for schemas whose version carries a point model."""
    model = point_model(
        scoring_configuration(db, workflow_pair_id, methodology_version_id)
    )
    if model is None:
        return
    if errors := point_range_errors(evidence, ranges=point_ranges(model)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(errors)
        )
