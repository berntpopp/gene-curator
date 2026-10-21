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


def test_active_schemas_use_registered_scoring_engines(db: Session) -> None:
    from app.scoring.registry import scoring_registry

    rows = db.execute(
        text(
            "SELECT name, version, scoring_configuration->>'engine' AS engine "
            "FROM curation_schemas WHERE is_active AND scoring_configuration IS NOT NULL"
        )
    ).mappings()
    bad = [
        (r["name"], r["version"], r["engine"])
        for r in rows
        if scoring_registry.get_engine(r["engine"] or "") is None
    ]
    assert bad == []


def _walk(node, key):  # every dict carrying `key`, at any depth
    if isinstance(node, dict):
        if key in node:
            yield node
        for child in node.values():
            yield from _walk(child, key)
    elif isinstance(node, list):
        for child in node:
            yield from _walk(child, key)


def test_seeded_schemas_emit_labelled_enum_options(db: Session) -> None:
    from app.core.schema_validator import SchemaValidator

    rows = db.execute(
        text("SELECT name, field_definitions FROM curation_schemas")
    ).mappings()
    seen = 0
    for row in rows:
        fields = row["field_definitions"]
        if not isinstance(fields, dict) or not all(
            isinstance(v, dict) for v in fields.values()
        ):
            continue  # sectioned list format: generate_json_schema does not support it
        generated = SchemaValidator().generate_json_schema(
            {"field_definitions": row["field_definitions"]}
        )["properties"]
        with_options = [
            d for d in _walk(row["field_definitions"], "options") if d["options"]
        ]
        labelled = list(_walk(generated, "enumOptions"))
        assert len(labelled) == len(with_options), row["name"]
        for prop in labelled:
            for option in prop["enumOptions"]:
                assert option["label"].strip(), (row["name"], option)
                seen += 1
    assert seen > 0
