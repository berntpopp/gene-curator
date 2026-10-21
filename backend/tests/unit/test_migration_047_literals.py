"""047 replaces exactly 046's embedded ClinGen model, and its result is the template file."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.scoring.point_model import template

pytestmark = pytest.mark.unit

SQL = Path(__file__).parents[3] / "database/sql"


def literal(name: str, tag: str) -> Any:
    found = re.search(rf"\${tag}\$(.*?)\${tag}\$", (SQL / name).read_text(), re.S)
    assert found
    return json.loads(found.group(1))


def test_047_turns_046_model_into_the_template() -> None:
    old = literal("047_contradictory_by_impact.sql", "old")
    assert old == literal("046_clingen_v1_correction.sql", "model")
    overrides = literal("047_contradictory_by_impact.sql", "overrides")
    assert {**old, "overrides": overrides} == template("clingen_sop_v11")
    assert overrides == [
        {
            "when": "contradictory_evidence",
            "field": "impact",
            "in": ["disputed"],
            "class": "disputed",
            "description": overrides[0]["description"],
        }
    ]
