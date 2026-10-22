"""Required fields hidden by their show_when/visible_when condition are not required."""

from typing import Any

import pytest

from app.crud.precuration_required import missing_required_fields

pytestmark = pytest.mark.unit

# Lumping section of the seeded "ClinGen Precuration" schema (016_seed_precuration_schema.sql)
SEEDED = {
    "sections": [
        {
            "id": "lumping_splitting",
            "fields": [
                {
                    "id": "lumping_splitting_applicable",
                    "type": "boolean",
                    "required": True,
                },
                {
                    "id": "lumping_splitting_decision",
                    "required": True,
                    "show_when": {"lumping_splitting_applicable": True},
                },
                {
                    "id": "lumping_splitting_rationale",
                    "required": True,
                    "show_when": {"lumping_splitting_applicable": True},
                },
            ],
        }
    ]
}
HIDDEN = ["lumping_splitting_decision", "lumping_splitting_rationale"]


@pytest.mark.parametrize(
    ("data", "missing"),
    [
        ({}, ["lumping_splitting_applicable"]),  # required booleans need an answer
        ({"lumping_splitting_applicable": False}, []),
        ({"lumping_splitting_applicable": True}, HIDDEN),
        (
            {"lumping_splitting_applicable": 1},
            [],
        ),  # equals is strict, like the frontend
        (
            {
                "lumping_splitting_applicable": True,
                "lumping_splitting_decision": "LUMP",
            },
            ["lumping_splitting_rationale"],
        ),
    ],
)
def test_seeded_lumping_fields_only_required_when_shown(
    data: dict[str, Any], missing: list[str]
) -> None:
    assert missing_required_fields(SEEDED, data) == missing


def test_listed_required_field_hidden_by_condition_is_skipped() -> None:
    rules = {"required_fields": HIDDEN}
    assert (
        missing_required_fields(SEEDED, {"lumping_splitting_applicable": False}, rules)
        == []
    )


@pytest.mark.parametrize(
    ("data", "missing"),
    [
        ({"moi": {"code": "AR"}}, []),
        ({"moi": {"code": "AD"}}, ["details"]),
        ({}, []),
    ],
)
def test_visible_when_in_and_nested_paths(
    data: dict[str, Any], missing: list[str]
) -> None:
    defs = {
        "details": {"required": True, "visible_when": {"moi.code": ["AD", "XL"]}},
        "odd": {"required": True, "visible_when": "not-a-condition"},
    }
    assert missing_required_fields(defs, {**data, "odd": "x"}) == missing
