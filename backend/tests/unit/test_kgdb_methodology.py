"""The KGDB methodology bundle (docs/schemas/kidney-genetics): every schema passes the
publish gate with its embedded pilot-gene scoring tests, and the field ids frozen in the
README (the KGDB import contract) are exactly the bundle's."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.crud.schema_repository import _score, publish_errors
from app.llm.sharing import JUDGEMENT_KEYS, field_specs

pytestmark = pytest.mark.unit

DIR = Path(__file__).parents[3] / "docs/schemas/kidney-genetics"
BUNDLE: dict[str, Any] = json.loads((DIR / "kgdb-methodology.json").read_text())
SCHEMAS = {s["name"]: s for s in BUNDLE["schemas"]}


def field_ids(fields: dict[str, Any], prefix: str = "") -> list[str]:
    """Data keys: precuration section field ids, else dotted paths, `[]` for table rows."""
    if isinstance(fields.get("sections"), list):
        return [f["id"] for s in fields["sections"] for f in s["fields"]]
    out = []
    for key, cfg in fields.items():
        out.append(prefix + key)
        out += field_ids(cfg.get("properties", {}), f"{prefix}{key}.")
        out += [f"{prefix}{key}[].{column}" for column in cfg.get("columns", {})]
    return out


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_publishes_with_its_scoring_tests(name: str) -> None:
    assert publish_errors(SCHEMAS[name]) == []


@pytest.mark.parametrize(
    ("name", "tests"),
    [("KGDB Mendelian Curation", 8), ("KGDB Susceptibility Curation", 7)],
)
def test_embedded_tests_score_as_expected(name: str, tests: int) -> None:
    config = SCHEMAS[name]["scoring_configuration"]
    assert len(config["tests"]) == tests
    for test in config["tests"]:
        result = _score(test["evidence_data"], config)
        got = {"total": result.total_score, "class": result.verdict}
        assert got == test["expect"], test["name"]


def test_pilot_genes_are_embedded() -> None:
    names = " ".join(
        t["name"]
        for t in SCHEMAS["KGDB Mendelian Curation"]["scoring_configuration"]["tests"]
    )
    for gene in ("CLDN16", "NEK8", "SIX5", "DNAJB11", "Hotspot"):
        assert gene in names


def test_pairs_and_scope_default() -> None:
    pairs = {
        p["name"]: (p["precuration_schema"], p["curation_schema"])
        for p in BUNDLE["workflow_pairs"]
    }
    assert pairs == {
        "KGDB Mendelian": ("KGDB Mendelian Precuration", "KGDB Mendelian Curation"),
        "KGDB Susceptibility": (
            "KGDB Susceptibility Precuration",
            "KGDB Susceptibility Curation",
        ),
    }
    assert BUNDLE["scope_default"] == {
        "scope_name": "kidney-genetics",
        "workflow_pair": "KGDB Mendelian",
    }


def test_llm_share_marks_evidence_never_judgement() -> None:
    shared = {
        key
        for s in SCHEMAS.values()
        for _, key, cfg in field_specs(s["field_definitions"])
        if cfg.get("llm_share") is True
    }
    assert {"variant_source", "allele_frequency", "summed_lod", "tools"} <= shared
    assert not shared & JUDGEMENT_KEYS


def test_readme_freezes_the_bundle_field_ids() -> None:
    readme = (DIR / "README.md").read_text()
    frozen = dict(re.findall(r"### (KGDB [^\n]+)\n\n```text\n(.*?)```", readme, re.S))
    assert set(frozen) == set(SCHEMAS)
    for name, schema in SCHEMAS.items():
        assert frozen[name].split() == field_ids(schema["field_definitions"]), name


def test_hotspot_pilot_case_raises_the_hotspot_flag() -> None:
    """Embedded tests assert total and class only; the reviewer flag is checked here."""
    config = SCHEMAS["KGDB Mendelian Curation"]["scoring_configuration"]
    test = next(t for t in config["tests"] if t["name"].startswith("Hotspot"))
    warnings = _score(test["evidence_data"], config).warnings
    assert any(w.startswith("review_flags.hotspot") for w in warnings), warnings


@pytest.mark.parametrize(
    "name", ["KGDB Mendelian Curation", "KGDB Susceptibility Curation"]
)
def test_summaries_name_the_classification(name: str) -> None:
    """Monkey M2: bands without a description ended "could not be determined"."""
    config = SCHEMAS[name]["scoring_configuration"]
    for test in config["tests"]:
        rationale = _score(test["evidence_data"], config).verdict_rationale
        assert "could not be determined" not in rationale, test["name"]


def test_a_band_without_description_falls_back_to_its_label() -> None:
    config = json.loads(
        json.dumps(SCHEMAS["KGDB Mendelian Curation"]["scoring_configuration"])
    )
    for band in config["point_model"]["bands"]:
        band.pop("description", None)
    rationale = _score({}, config).verdict_rationale
    assert rationale.endswith("Classification: No Known Disease Relationship.")
