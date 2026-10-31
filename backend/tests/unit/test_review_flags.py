"""Point model ``review_flags`` (#559): reviewer warnings for a total near a band edge, a
recurrent-variant hotspot and experimental points above genetic; never without the key."""

from typing import Any

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.evidence_lint import evidence_warnings
from app.scoring.point_model import score
from tests.unit.test_schema_validators_seeded import errors

pytestmark = pytest.mark.unit

PMID = "12345678"
CASE = {"rule": "case_row", "points_key": "points", "blank_at": 1}


def _model(**flags: Any) -> dict[str, Any]:
    model: dict[str, Any] = {
        "sections": [
            {
                "key": "gen",
                "categories": [{"key": "c", "types": [{"path": "p", **CASE}]}],
            },
            {"key": "exp", "categories": [{"key": "e", "types": [{"path": "x"}]}]},
        ],
        "bands": [{"class": "strong", "min": 12}, {"class": "limited", "min": 0.1}],
    }
    return model | ({"review_flags": flags} if flags else {})


def _evidence(variants: list[str], points: float = 1, exp: float = 0) -> dict[str, Any]:
    rows = [
        {"variant": v, "points": points, "pmid": PMID, "score_status": "score"}
        for v in variants
    ]
    return {"gen": {"p": rows}, "exp": {"x": [{"points": exp, "pmid": PMID}]}}


def _distinct(n: int) -> list[str]:
    return [f"c.{i + 2}A>G" for i in range(n)]


def _flags(model: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    warnings = evidence_warnings(evidence, score(model, evidence))
    return [w for w in warnings if w.startswith("review_flags.")]


ALL = {
    "band_margin": 2,
    "hotspot": {"max_variants": 2, "min_share": 0.5},
    "experimental_over_genetic": ["exp", "gen"],
}


def test_no_flag_without_review_flags() -> None:
    assert _flags(_model(), _evidence(["c.1A>G"] * 11, exp=3)) == []


def test_band_margin_fires_near_an_edge_only() -> None:
    model = _model(band_margin=2)
    near = _flags(model, _evidence(_distinct(10)))
    assert near == [
        "review_flags.band_margin: the total of 10 points is within 2 points of the "
        "strong band edge at 12; check the evidence near the boundary"
    ]
    assert _flags(model, _evidence(_distinct(7))) == []


def test_hotspot_fires_when_few_variants_carry_the_points() -> None:
    model = _model(hotspot={"max_variants": 2, "min_share": 0.5})
    hot = _flags(model, _evidence(["c.1A>G", "C.1a>g ", "c.1a>G", *_distinct(3)]))
    assert hot == [
        "review_flags.hotspot: 4 of 6 proband points (67%) come from 2 variants; "
        "check for a recurrent-variant hotspot"
    ]
    spread = _flags(model, _evidence(_distinct(5)))
    assert spread == []


def test_hotspot_is_recurrence() -> None:
    """A hotspot is a variant in 2+ scoring probands; single-proband variants that carry
    the points are no hotspot however few they are (monkey M3, orchestrator decision)."""
    model = _model(hotspot={"max_variants": 2, "min_share": 0.5})
    assert _flags(model, _evidence(["c.1A>G"] * 6)) == [
        "review_flags.hotspot: 6 of 6 proband points (100%) come from 1 variant; "
        "check for a recurrent-variant hotspot"
    ]
    assert _flags(model, _evidence(_distinct(3))) == []
    assert _flags(model, _evidence(_distinct(2))) == []


def test_experimental_over_genetic_fires_only_when_greater() -> None:
    model = _model(experimental_over_genetic=["exp", "gen"])
    assert _flags(model, _evidence(["c.1A>G"], exp=2)) == [
        "review_flags.experimental_over_genetic: exp scores 2 points, more than gen "
        "(1); check the experimental evidence"
    ]
    assert _flags(model, _evidence(["c.1A>G"], exp=1)) == []


def test_all_flags_together() -> None:
    # 9 points: none near 12 or 0.1; three variants, two carry 3 of 4 genetic points
    evidence = _evidence(["c.1A>G"] * 2 + _distinct(2), exp=5)
    assert [w.split(":")[0] for w in _flags(_model(**ALL), evidence)] == [
        "review_flags.hotspot",
        "review_flags.experimental_over_genetic",
    ]


def _flag_errors(flags: Any) -> list[str]:
    model = _model() | {"review_flags": flags}
    cfg = {"engine": "clingen_sop_v11", "point_model": model}
    prefix = "scoring_configuration.point_model.review_flags"
    return [p.removeprefix(prefix) for p, _ in errors(scoring_configuration=cfg)]


def test_valid_review_flags() -> None:
    assert _flag_errors(ALL) == []
    assert _flag_errors({}) == []


@pytest.mark.parametrize(
    ("flags", "paths"),
    [
        ([], [""]),
        ({"band_margins": 2}, [".band_margins"]),
        ({"band_margin": "2"}, [".band_margin"]),
        ({"band_margin": -1}, [".band_margin"]),
        ({"hotspot": {"max_variants": 0, "min_share": 0.5}}, [".hotspot.max_variants"]),
        ({"hotspot": {"max_variants": 2, "min_share": 1.5}}, [".hotspot.min_share"]),
        ({"hotspot": {"max_variants": 2}}, [".hotspot.min_share"]),
        ({"hotspot": 2}, [".hotspot"]),
        ({"experimental_over_genetic": ["exp"]}, [".experimental_over_genetic"]),
        (
            {"experimental_over_genetic": ["exp", "nope"]},
            [".experimental_over_genetic"],
        ),
    ],
)
def test_invalid_review_flags(flags: Any, paths: list[str]) -> None:
    assert _flag_errors(flags) == paths


def test_engine_warnings_carry_the_schema_flags() -> None:
    model = _model(experimental_over_genetic=["exp", "gen"])
    config = {"engine": "clingen_sop_v11", "point_model": model}
    result = ClinGenEngine().calculate_scores(_evidence(["c.1A>G"], exp=2), config)
    assert any(w.startswith("review_flags.experimental") for w in result.warnings)


def test_band_margin_ignores_edges_at_or_below_zero() -> None:
    model = _model(band_margin=2)
    model["bands"] = [{"class": "strong", "min": 12}, {"class": "no_known", "min": 0}]
    model["bands"].append({"class": "disputed", "min": -1})
    assert _flags(model, _evidence(_distinct(1))) == []


def test_hotspot_names_the_variants_there_are() -> None:
    model = _model(hotspot={"max_variants": 2, "min_share": 0.5})
    assert _flags(model, _evidence(["c.1A>G"] * 3)) == [
        "review_flags.hotspot: 3 of 3 proband points (100%) come from 1 variant; "
        "check for a recurrent-variant hotspot"
    ]


@pytest.mark.parametrize(
    ("flags", "paths"),
    [
        ({"hotspot": {"max_variants": 2, "min_share": 0.5, "x": 1}}, [".hotspot.x"]),
        ({"experimental_over_genetic": ["exp", "exp"]}, [".experimental_over_genetic"]),
    ],
)
def test_more_invalid_review_flags(flags: Any, paths: list[str]) -> None:
    assert _flag_errors(flags) == paths
