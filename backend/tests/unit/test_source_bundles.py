"""#593: the KGDB and ClinGen bundles give every evidence table a source cell and a
direction (additive: the other field ids stay as they were)."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.crud.schema_repository import publish_errors

pytestmark = pytest.mark.unit

DOCS = Path(__file__).parents[3] / "docs/schemas"
BUNDLES = ["kidney-genetics/kgdb-methodology.json", "clingen/clingen-methodology.json"]


def _tables(fields: dict[str, Any], path: str = "") -> Any:
    for key, cfg in fields.items():
        if not isinstance(cfg, dict):
            continue
        columns = cfg.get("columns") or (cfg.get("items") or {}).get("properties")
        if cfg.get("type") in ("evidence_table", "array") and isinstance(columns, dict):
            yield f"{path}{key}", columns
        yield from _tables(cfg.get("properties") or {}, f"{path}{key}.")


@pytest.mark.parametrize("bundle", BUNDLES)
def test_every_evidence_table_has_sources_and_a_direction(bundle: str) -> None:
    schemas = json.loads((DOCS / bundle).read_text())["schemas"]
    curations = [s for s in schemas if s["schema_type"] == "curation"]
    assert curations
    for schema in schemas:
        assert publish_errors(schema) == [], schema["name"]
    tables = [t for s in curations for t in _tables(s["field_definitions"])]
    assert tables
    for path, columns in tables:
        if path.startswith("diagnostics."):  # KGDB's own Diagnostics shape
            continue
        assert columns["sources"]["type"] == "source", path
        values = [o["value"] for o in columns["direction"]["options"]]
        assert values == ["supports", "disputes", "neutral"], path


@pytest.mark.parametrize("bundle", BUNDLES)
def test_curation_schemas_name_evidence_summary_as_synopsis(bundle: str) -> None:
    schemas = json.loads((DOCS / bundle).read_text())["schemas"]
    for schema in schemas:
        if schema["schema_type"] == "curation":
            assert schema["ui_configuration"]["synopsis_field"] == "evidence_summary"
            assert schema["field_definitions"]["evidence_summary"]["type"] == "textarea"
