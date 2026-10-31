"""KGDB smoke test: a row cell the table does not define is a save warning, never a refusal."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import CurationNew
from app.services import review_guards
from app.services.review_guards import unknown_columns

pytestmark = pytest.mark.unit

BUNDLE = json.loads(
    (
        Path(__file__).parents[3] / "docs/schemas/kidney-genetics/kgdb-methodology.json"
    ).read_text()
)
[KGDB] = [s for s in BUNDLE["schemas"] if s["name"] == "KGDB Mendelian Curation"]


def test_stray_row_columns_are_named_by_path(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(review_guards, "item_definition", lambda db, item: KGDB)
    row = {"id": "row-1", "pmid": "123", "variant": "c.1A>G", "variant_type": "SNV"}
    evidence = {"genetic": {"probands": [row]}, "evidence_summary": "kept"}
    [warning] = unknown_columns(db_session, CurationNew(), evidence)
    assert (warning.path, warning.message) == (
        "genetic.probands[0].variant_type",
        "not a column of this table",
    )
    del row["variant_type"]
    assert unknown_columns(db_session, CurationNew(), evidence) == []


def test_an_unreadable_pin_warns_nothing(db_session: Session) -> None:
    curation = CurationNew(methodology_version_id=uuid4())
    assert unknown_columns(db_session, curation, {"a": [{"b": 1}]}) == []
