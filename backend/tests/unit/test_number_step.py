"""#615: a points value off its field's `step` (counted from `min`) is refused at submit,
as a form field or an evidence-table column named points; float noise is not an error.
Other numbers keep the step as an input hint (a LOD of 3.125 at step 0.01 is valid)."""

import pytest

from app.services.evidence_ids import evidence_errors

pytestmark = pytest.mark.unit

DEFINITION = {
    "field_definitions": {
        "points": {"type": "number", "min": 0, "step": 0.5},
        "lod": {"type": "number", "min": 0, "step": 0.01},
        "rows": {
            "type": "evidence_table",
            "columns": {"points": {"type": "number", "min": 0, "max": 3, "step": 0.1}},
        },
        "nested": {
            "type": "object",
            "properties": {"points": {"type": "number", "min": 0.25, "step": 0.5}},
        },
    }
}


def _paths(evidence: dict) -> list[str]:
    return [e.path for e in evidence_errors(evidence, DEFINITION)]


@pytest.mark.parametrize(
    ("evidence", "paths"),
    [
        ({"points": 0.2}, ["points"]),
        ({"points": 1.5, "nested": {"points": 0.75}}, []),
        ({"nested": {"points": 0.5}}, ["nested.points"]),  # the step counts from min
        ({"points": float("nan")}, []),  # not a step question (the range check owns it)
        ({"points": float("inf")}, []),
        ({"lod": 3.125}, []),  # not points: the step is an input hint
        (
            {"rows": [{"points": 0.3}, {"points": 1.6}, {"points": 0.15}]},
            ["rows[2].points"],
        ),
    ],
)
def test_values_off_the_step_are_refused(evidence: dict, paths: list[str]) -> None:
    assert _paths(evidence) == paths
