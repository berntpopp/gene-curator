"""Band ``section_min`` (#556): a band matches only if each listed section reaches its
minimum, checked against the capped section scores."""

from typing import Any

import pytest

from app.scoring.point_model import TEMPLATES, score, template
from tests.unit.test_schema_validators_seeded import errors

pytestmark = pytest.mark.unit

PMID = "12345678"


def _model(**band: Any) -> dict[str, Any]:
    def section(key: str, cap: float) -> dict[str, Any]:
        types = [{"path": "rows"}]
        return {"key": key, "cap": cap, "categories": [{"key": "c", "types": types}]}

    return {
        "sections": [section("genetic", 12), section("experimental", 6)],
        "bands": [
            {"class": "moderate", "min": 7, **band},
            {"class": "limited", "min": 0.1},
            {"class": "no_known"},
        ],
    }


def _evidence(genetic: float, experimental: float) -> dict[str, Any]:
    def rows(points: float) -> dict[str, Any]:
        return {"rows": [{"points": points, "pmid": PMID}]}

    return {"genetic": rows(genetic), "experimental": rows(experimental)}


def test_thin_genetics_falls_to_the_next_band() -> None:
    model = _model(section_min={"genetic": 4})
    result = score(model, _evidence(2, 6))
    assert (result["total"], result["class"]) == (8, "limited")
    assert score(_model(), _evidence(2, 6))["class"] == "moderate"  # unchanged without


def test_band_matches_when_every_section_reaches_its_minimum() -> None:
    model = _model(section_min={"genetic": 4, "experimental": 2})
    assert score(model, _evidence(4, 3))["class"] == "moderate"
    assert score(model, _evidence(5, 1))["class"] == "limited"


def test_minimum_uses_the_capped_section_score() -> None:
    model = _model(section_min={"experimental": 7})  # experimental is capped at 6
    assert score(model, _evidence(1, 10))["class"] == "limited"


def _errors(bands: list[Any]) -> list[str]:
    model = {**_model(), "bands": bands}
    cfg = {"engine": "clingen_sop_v11", "point_model": model}
    prefix = "scoring_configuration.point_model"
    return [p.removeprefix(prefix) for p, _ in errors(scoring_configuration=cfg)]


@pytest.mark.parametrize(
    "section_min",
    [{"genetic": 4}, {"genetic": 4.5, "experimental": 0}],
)
def test_valid_section_min(section_min: Any) -> None:
    assert _errors([{"class": "m", "min": 7, "section_min": section_min}]) == []


@pytest.mark.parametrize(
    ("section_min", "path"),
    [
        ({"genetc": 4}, ".bands[0].section_min.genetc"),
        ({"genetic": "4"}, ".bands[0].section_min.genetic"),
        ({"genetic": True}, ".bands[0].section_min.genetic"),
        ([4], ".bands[0].section_min"),
    ],
)
def test_invalid_section_min(section_min: Any, path: str) -> None:
    assert _errors([{"class": "m", "min": 7, "section_min": section_min}]) == [path]


def test_unknown_band_key_is_an_error() -> None:
    assert _errors([{"class": "m", "min": 7, "min_section": {"genetic": 4}}]) == [
        ".bands[0].min_section"
    ]


def test_every_bundled_template_still_validates() -> None:
    """Rejecting unknown band keys must not reject a shipped model."""
    for path in TEMPLATES.glob("*.json"):
        model = template(path.stem)
        cfg = {"engine": "clingen_sop_v11", "point_model": model}
        assert errors(scoring_configuration=cfg) == [], path.stem
