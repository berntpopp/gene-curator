"""Curator classification (#533): which classes a curator may choose, and the save values."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import CurationNew, Gene
from app.schemas.clingen_adoption import ClinGenRecord, entity_errors
from app.schemas.curation import (
    CLASSIFICATION_KEYS,
    CurationUpdate,
    CuratorClassificationIn,
    class_key,
)
from app.scoring.classifications import TONES
from app.scoring.clingen import ClinGenEngine
from app.scoring.point_limits import scoring_configuration
from app.scoring.registry import engine_for


def class_key_sql(value: Any) -> ColumnElement[str]:
    """schemas.curation.class_key in SQL (PostgreSQL and SQLite), for grouping and filters."""
    key = func.replace(func.replace(func.lower(func.trim(value)), " ", "_"), "-", "_")
    return case((func.substr(key, 1, 8) == "no_known", "no_known"), else_=key)


# ClinGen keys as the frontend labels them (config/classification.ts)
_LABELS = {t: t.capitalize() for t in TONES} | {
    "no_known": "No known disease relationship"
}


def class_label(value: str) -> str:
    """A ClinGen key's label; any other value (an engine label, a custom key) as is."""
    return _LABELS.get(value, value)


def classification_choices(config: dict[str, Any]) -> list[dict[str, str]]:
    """{key, label} a curator may choose: the schema's declared vocabulary in its order
    (#539), then the engine's verdicts it lacks, from the point model for ClinGen (#533,
    same rule as the registry's engine info)."""
    engine = engine_for(config)
    verdicts = (
        engine.get_supported_verdicts(config)
        if isinstance(engine, ClinGenEngine)
        else engine.get_supported_verdicts()
    )
    declared = config.get("classifications")
    entries = [
        c
        for c in (declared if isinstance(declared, list) else [])
        if isinstance(c, dict) and isinstance(c.get("key"), str)
    ]
    entries.sort(key=lambda c: c["order"] if _is_number(c.get("order")) else 0)
    out: dict[str, str] = {}
    for c in entries:
        out.setdefault(class_key(c["key"]), str(c.get("label") or c["key"]))
    for v in verdicts:
        out.setdefault(class_key(v), class_label(v))
    return [{"key": k, "label": label} for k, label in out.items()]


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def allowed_classifications(config: dict[str, Any]) -> list[str]:
    """Class keys a curator may choose (classification_choices)."""
    return [c["key"] for c in classification_choices(config)]


def curator_call(
    db: Session, curation: CurationNew, sent: CuratorClassificationIn
) -> dict[str, Any]:
    """The sent classification keys, the class as its key; 422 for an unknown class."""
    values = sent.model_dump(include=CLASSIFICATION_KEYS, exclude_unset=True)
    if proposed := values.get("curator_classification"):
        allowed = allowed_classifications(
            scoring_configuration(
                db, curation.workflow_pair_id, curation.methodology_version_id
            )
        )
        if (key := class_key(proposed)) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "Unknown classification",
                    "errors": [
                        {
                            "path": "curator_classification",
                            "message": f"One of: {', '.join(allowed)}",
                        }
                    ],
                },
            )
        values["curator_classification"] = key
    if isinstance(sent, CurationUpdate) and sent.clingen_reference:
        values["clingen_reference"] = _reference(db, curation, sent.clingen_reference)
    return values


def _reference(
    db: Session, curation: CurationNew, record: ClinGenRecord
) -> dict[str, Any]:
    """The ClinGen record as stored; 422 when it names another entity (as adoption)."""
    gene = db.get(Gene, curation.gene_id)
    mondo, _, rest = curation.entity_key.partition("|")
    moi = rest.partition("|")[0]
    errors = entity_errors(
        record, gene.hgnc_id if gene else "", mondo, moi, "clingen_reference"
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "ClinGen record of another entity",
                "errors": [
                    dict(zip(("path", "message"), e.split(": ", 1), strict=True))
                    for e in errors
                ],
            },
        )
    return record.model_dump(mode="json")
