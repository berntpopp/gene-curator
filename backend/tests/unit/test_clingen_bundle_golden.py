"""Golden scores of the ClinGen bundle (docs/schemas/clingen): its embedded tests through
the engine, pinned, so engine changes for other methodologies (group_values, the range
check before factor/max, #615) cannot shift ClinGen points; and a LOD with more decimals
than its input step (3.125 at step 0.01) is valid evidence at submit."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.crud.schema_repository import _score
from app.services.evidence_ids import evidence_errors

pytestmark = pytest.mark.unit

BUNDLE = Path(__file__).parents[3] / "docs/schemas/clingen/clingen-methodology.json"
[SOP] = [
    s
    for s in json.loads(BUNDLE.read_text())["schemas"]
    if s["name"] == "ClinGen Gene-Disease Validity SOP"
]
GOLDEN = [  # (total, class, genetic, experimental)
    (1.7, "limited", 1.7, 0.0),
    (2.0, "limited", 2.0, 0.0),
    (0.0, "no_known", 0.0, 0.0),
]


def test_embedded_tests_score_the_pinned_values() -> None:
    config: dict[str, Any] = SOP["scoring_configuration"]
    got = []
    for test in config["tests"]:
        r = _score(test["evidence_data"], config)
        scores = r.scores or {}
        got.append(
            (
                r.total_score,
                r.verdict,
                scores["genetic_evidence_total"],
                scores["experimental_evidence_total"],
            )
        )
    assert got == GOLDEN


def test_a_lod_off_its_input_step_is_valid_at_submit() -> None:
    family = {"family_label": "F1", "lod_source": "published", "published_lod": 3.125}
    evidence = {"genetic_evidence": {"segregation": [family]}}
    assert [e.path for e in evidence_errors(evidence, SOP) if "lod" in e.path] == []
