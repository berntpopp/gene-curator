"""Rows outside their pinned range are flagged in the trace, never clamped (#434).

Finite out-of-range points keep counting as before (stored totals stay reproducible; saves
and submits still 422); non-finite points cannot be summed or stored and count nothing."""

import json

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import score

pytestmark = pytest.mark.unit

AD_NULL = "genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null"


def _null_rows(*points: object) -> dict:
    rows = [{"pmid": "1", "proband_counted_points": p} for p in points]
    return {
        "genetic_evidence": {
            "case_level": {
                "autosomal_dominant_or_x_linked": {"predicted_or_proven_null": rows}
            }
        }
    }


@pytest.mark.parametrize(
    ("points", "total", "flagged"),
    [
        ((2, 3, 0), 5, []),  # in range: no flag, trace unchanged
        ((2, -1), 1, [(1, -1.0)]),
        ((99,), 12, [(0, 99.0)]),  # category cap applies, as before
        ((2, "nan", float("inf"), "-inf"), 2, [(1, "nan"), (2, "inf"), (3, "-inf")]),
    ],
)
def test_out_of_range_rows_are_flagged_not_clamped(
    points: tuple, total: float, flagged: list
) -> None:
    result = ClinGenEngine().calculate_scores(_null_rows(*points), {})
    trace = result.evidence_breakdown["trace"]
    assert result.total_score == total
    expected = [
        {"path": f"{AD_NULL}[{i}].proband_counted_points", "value": v, "range": [0, 3]}
        for i, v in flagged
    ]
    assert trace.get("out_of_range", []) == expected
    assert "out_of_range" in trace or not flagged
    json.dumps(trace, allow_nan=False)  # storable in JSONB
    assert [w for w in result.warnings if "outside" in w] == [
        f"{f['path']} = {f['value']} is outside the pinned range 0-3" for f in expected
    ]


def test_types_without_a_range_only_flag_non_finite_points() -> None:
    model = {
        "sections": [
            {"key": "s", "categories": [{"key": "c", "types": [{"path": "t"}]}]}
        ],
        "bands": [{"class": "any"}],
    }
    result = score(model, {"s": {"t": [{"points": 50}, {"points": "nan"}]}})
    assert result["total"] == 50
    assert result["trace"]["out_of_range"] == [
        {"path": "s.t[1].points", "value": "nan", "range": None}
    ]
    warnings = (
        ClinGenEngine()
        .calculate_scores({"s": {"t": [{"points": "inf"}]}}, {"point_model": model})
        .warnings
    )
    assert warnings == ["s.t[0].points = inf is not a finite number"]
