"""Curator classification (#533): which classes a curator may choose, and the save values."""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import CurationNew
from app.schemas.curation import CLASSIFICATION_KEYS, CuratorClassificationIn, class_key
from app.scoring.clingen import ClinGenEngine
from app.scoring.point_limits import scoring_configuration
from app.scoring.registry import engine_for


def class_key_sql(value: Any) -> ColumnElement[str]:
    """schemas.curation.class_key in SQL (PostgreSQL and SQLite), for grouping and filters."""
    key = func.replace(func.replace(func.lower(func.trim(value)), " ", "_"), "-", "_")
    return case((func.substr(key, 1, 8) == "no_known", "no_known"), else_=key)


def allowed_classifications(config: dict[str, Any]) -> list[str]:
    """Class keys a curator may choose (#533): the engine's verdicts, from the schema's point
    model for ClinGen (same rule as the registry's engine info)."""
    engine = engine_for(config)
    verdicts = (
        engine.get_supported_verdicts(config)
        if isinstance(engine, ClinGenEngine)
        else engine.get_supported_verdicts()
    )
    return list(dict.fromkeys(class_key(v) for v in verdicts))


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
    return values
