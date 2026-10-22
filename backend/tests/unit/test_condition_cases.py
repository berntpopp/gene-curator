"""The shared condition table (#433): the frontend runs the same cases (conditions.spec.ts)."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.crud.precuration_required import condition_holds, missing_required_fields

pytestmark = pytest.mark.unit

CASES = json.loads(
    (
        Path(__file__).parents[3]
        / "frontend/src/components/dynamic/__tests__/conditionCases.json"
    ).read_text()
)


@pytest.mark.parametrize(
    "case", CASES["conditions"], ids=[c["name"] for c in CASES["conditions"]]
)
def test_condition(case: dict[str, Any]) -> None:
    assert condition_holds(case["condition"], case["data"]) is case["holds"]


@pytest.mark.parametrize(
    "case", CASES["required"], ids=[c["name"] for c in CASES["required"]]
)
def test_required(case: dict[str, Any]) -> None:
    missing = missing_required_fields(case["fields"], case["data"], case.get("rules"))
    assert missing == case["missing"]
