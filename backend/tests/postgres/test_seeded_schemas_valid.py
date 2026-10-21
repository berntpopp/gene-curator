"""#207: every seeded curation schema passes the structure validator."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.crud.schema_validators import validate_schema_structure

pytestmark = pytest.mark.postgres

_COLUMNS = (
    "field_definitions, validation_rules, scoring_configuration, "
    "workflow_states, ui_configuration"
)


def test_seeded_schemas_are_valid(db: Session) -> None:
    rows = db.execute(text(f"SELECT name, {_COLUMNS} FROM curation_schemas")).mappings()
    checked = 0
    for row in rows:
        data = {k: v for k, v in row.items() if k != "name"}
        errors, _ = validate_schema_structure(data)
        assert errors == [], f"{row['name']}: {errors}"
        checked += 1
    assert checked >= 4
