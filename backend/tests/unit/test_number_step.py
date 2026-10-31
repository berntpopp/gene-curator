"""#615: a number off its field's `step` (counted from `min`) is refused at submit, in a
form field and in an evidence-table cell; float noise is not an error."""

import pytest

from app.services.evidence_ids import evidence_errors

pytestmark = pytest.mark.unit

DEFINITION = {
    "field_definitions": {
        "score": {"type": "number", "min": 0, "step": 0.5},
        "rows": {
            "type": "evidence_table",
            "columns": {"points": {"type": "number", "min": 0, "max": 3, "step": 0.1}},
        },
        "offset": {"type": "number", "min": 0.25, "step": 0.5},
    }
}


def _paths(evidence: dict) -> list[str]:
    return [e.path for e in evidence_errors(evidence, DEFINITION)]


@pytest.mark.parametrize(
    ("evidence", "paths"),
    [
        ({"score": 0.2}, ["score"]),
        ({"score": 1.5, "offset": 0.75}, []),
        ({"offset": 0.5}, ["offset"]),  # the step counts from min
        ({"score": float("nan")}, []),  # not a step question (the range check owns it)
        ({"score": float("inf")}, []),
        (
            {"rows": [{"points": 0.3}, {"points": 1.6}, {"points": 0.15}]},
            ["rows[2].points"],
        ),
    ],
)
def test_values_off_the_step_are_refused(evidence: dict, paths: list[str]) -> None:
    assert _paths(evidence) == paths
