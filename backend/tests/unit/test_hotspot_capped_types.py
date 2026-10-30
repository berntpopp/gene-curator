"""#559: the hotspot flag counts every type the per-variant group cap (#557) groups, with
the capped points, so the flag and the cap agree (KGDB probands have no case_row rule)."""

from typing import Any

import pytest

from app.scoring.evidence_lint import evidence_warnings
from app.scoring.point_model import score

pytestmark = pytest.mark.unit

PMID = "12345678"
# As docs/schemas/kidney-genetics/kgdb-methodology.json declares its probands
PROBANDS = {
    "path": "probands",
    "default": 1,
    "range": [0, 2],
    "require_variant": True,
    "group_by": "variant",
    "group_cap": 2,
}
MODEL = {
    "sections": [
        {
            "key": "genetic",
            "categories": [
                {"key": "probands", "types": [PROBANDS]},
                {"key": "cohort", "types": [{"path": "cohort", "default": 2}]},
            ],
        }
    ],
    "bands": [{"class": "limited", "min": 0.1}, {"class": "no_known"}],
    "review_flags": {"hotspot": {"max_variants": 2, "min_share": 0.5}},
}


def _hotspot(*variants: str) -> list[str]:
    rows = [{"variant": v, "pmid": PMID} for v in variants]
    evidence: dict[str, Any] = {"genetic": {"probands": rows}}
    result = score(MODEL, evidence)
    return [w for w in evidence_warnings(evidence, result) if "hotspot" in w]


def test_recurrent_variant_rows_raise_the_flag_with_capped_points() -> None:
    (warning,) = _hotspot(*["c.100A>G"] * 4, "c.200C>T", "c.300G>A", "c.400T>C")
    assert "3 of 5 proband points (60%)" in warning  # c.100A>G capped at 2, not 4


def test_spread_variants_do_not() -> None:
    assert _hotspot("c.1A>G", "c.2A>G", "c.3A>G", "c.4A>G", "c.5A>G") == []


def test_groups_are_normalised_like_the_cap() -> None:
    result = score(
        MODEL,
        {
            "genetic": {
                "probands": [
                    {"variant": " C.1a>g", "pmid": PMID},
                    {"variant": "c.1A>G ", "pmid": PMID},
                ]
            }
        },
    )
    assert result["variant_points"] == {"c.1a>g": 2.0}
