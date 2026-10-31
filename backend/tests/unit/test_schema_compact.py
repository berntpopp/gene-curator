"""get_curation_schema(path=) point ranges come from the point model (round 5)."""

import pytest

from app.core.schema_compact import ranges_for, subtree
from app.scoring.point_model import template

pytestmark = pytest.mark.unit

AR = "genetic_evidence.case_level.autosomal_recessive"


def test_ranges_cover_the_types_at_under_and_above_the_path() -> None:
    model = template("clingen_sop_v11")
    assert model is not None
    under = ranges_for(model, AR)
    assert [r["path"] for r in under] == [
        f"{AR}.predicted_or_proven_null",
        f"{AR}.other_variant_type",
    ]
    assert {r["category_cap"] for r in under} == {12}
    # a row field inside one table gets that table's range
    (row,) = ranges_for(model, f"{AR}.predicted_or_proven_null.pmid")
    assert row == {
        "path": f"{AR}.predicted_or_proven_null",
        "range": [0, 3],
        "category_cap": 12,
    }
    assert ranges_for(model, "genetic_evidence.case") == []  # no prefix matches


def test_subtree_reaches_an_evidence_table_column() -> None:
    """#612: genetic.probands.sources is a column, not "none, it is a single field"."""
    source = {"type": "source"}
    fields = {
        "genetic": {
            "type": "object",
            "properties": {
                "probands": {"type": "evidence_table", "columns": {"sources": source}},
                "rows": {"type": "evidence_table", "columns": [{"id": "pmid"}]},
            },
        }
    }
    assert subtree(fields, "genetic.probands.sources") == source
    assert subtree(fields, "genetic.rows.pmid") == {"id": "pmid"}
