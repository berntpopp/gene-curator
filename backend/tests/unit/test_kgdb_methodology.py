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
    [("KGDB Mendelian Curation", 13), ("KGDB Susceptibility Curation", 12)],
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


@pytest.mark.parametrize(
    "name", ["KGDB Mendelian Curation", "KGDB Susceptibility Curation"]
)
def test_kgdb_text_and_list_limits_are_refused(name: str) -> None:
    """#611: KGDB's limits (summary 2000, notes 300 / 500, at most 10 detectability
    sources) are refused at submit; values at the limit pass."""
    from app.services.evidence_ids import evidence_errors

    def paths(evidence: dict[str, Any]) -> set[str]:
        return {e.path for e in evidence_errors(evidence, SCHEMAS[name])}

    def evidence(n: int, sources: int) -> dict[str, Any]:
        return {
            "evidence_summary": "x" * (2000 + n),
            "diagnostics_notes": {
                "transcript_verified_via": "x" * (300 + n),
                "detectability_note": "x" * (500 + n),
            },
            "diagnostics": {
                "detectability": [
                    {"challenge": "other", "sources": ["PMID:1"] * sources}
                ]
            },
        }

    assert paths(evidence(0, 10)) == set()
    assert paths(evidence(1, 11)) == {
        "evidence_summary",
        "diagnostics_notes.transcript_verified_via",
        "diagnostics_notes.detectability_note",
        "diagnostics.detectability[0].sources",
    }


def test_proband_help_says_enter_the_full_allele_sum() -> None:
    """Review of #619: the engine halves unknown phase, so the agent must not halve too."""
    schema = SCHEMAS["KGDB Mendelian Curation"]
    points = schema["field_definitions"]["genetic"]["properties"]["probands"]["columns"]
    tabs = schema["ui_configuration"]["layout"]["tabs"]
    [section] = [s for t in tabs for s in t["sections"] if s.get("name") == "Probands"]
    for text in (points["points"]["help_text"], section["help_text"]):
        assert "full allele sum" in text and "halves" in text, text


def test_moi_options_carry_their_hpo_label() -> None:
    """Review of #619: each MOI option's HPO id and label as HPO 2026-09-01 names them."""
    hpo = {
        "HP:0000006": "Autosomal dominant",
        "HP:0000007": "Autosomal recessive",
        "HP:0001417": "X-linked",
        "HP:0001423": "X-linked dominant",
        "HP:0001419": "X-linked recessive",
        "HP:0032113": "Semidominant",
        "HP:0001427": "Mitochondrial",
        "HP:0001450": "Y-linked",
        "HP:0000005": "Undetermined",
        "HP:0010982": "Multifactorial (polygenic)",
    }
    for name in ("KGDB Mendelian Precuration", "KGDB Susceptibility Precuration"):
        sections = SCHEMAS[name]["field_definitions"]["sections"]
        [moi] = [
            f for s in sections for f in s["fields"] if f["id"] == "mode_of_inheritance"
        ]
        for option in moi["options"]:
            assert option["label"] == f"{hpo[option['value']]} ({option['value']})"


@pytest.mark.parametrize(
    "name", ["KGDB Mendelian Precuration", "KGDB Susceptibility Precuration"]
)
def test_required_fields_list_every_required_field(name: str) -> None:
    """KGDB end-to-end: a field marked required is also in validation_rules."""
    schema = SCHEMAS[name]
    required = {
        f["id"]
        for s in schema["field_definitions"]["sections"]
        for f in s["fields"]
        if f.get("required")
    }
    assert set(schema["validation_rules"]["required_fields"]) == required


def test_curation_descriptions_name_iteration_8() -> None:
    """KGDB end-to-end: the Mendelian description still said draft iteration 3."""
    assert "iteration 8" in SCHEMAS["KGDB Mendelian Curation"]["description"]
    assert "iteration 3" not in json.dumps(BUNDLE)


def test_variant_class_offers_the_prompt_values_and_keeps_old_ones() -> None:
    """KGDB end-to-end: the prompt's allele classes (null|missense|inframe|splice_other|
    other) are options; lof and splice stay valid for rows stored before."""
    probands = SCHEMAS["KGDB Mendelian Curation"]["field_definitions"]["genetic"]
    column = probands["properties"]["probands"]["columns"]["variant_class"]
    values = [o["value"] for o in column["options"]]
    assert values[:5] == ["null", "missense", "inframe", "splice_other", "other"]
    assert {"lof", "splice"} <= set(values)


def test_a_row_without_its_quote_warns_that_it_scores_0() -> None:
    """KGDB e2e (NPHS2): a row zeroed for a missing evidence_quote names the field."""
    config = SCHEMAS["KGDB Mendelian Curation"]["scoring_configuration"]
    [cldn16] = [t for t in config["tests"] if t["name"].startswith("CLDN16")]
    evidence = json.loads(json.dumps(cldn16["evidence_data"]))
    assert not [w for w in _score(evidence, config).warnings if "scores 0" in w]
    del evidence["genetic"]["probands"][0]["evidence_quote"]
    result = _score(evidence, config)
    assert result.total_score < cldn16["expect"]["total"]
    assert "genetic.probands[0].evidence_quote: missing, so this row scores 0" in (
        result.warnings
    )


@pytest.mark.parametrize(
    "name", ["KGDB Mendelian Curation", "KGDB Susceptibility Curation"]
)
def test_clinical_group_takes_kgdb_groups_and_is_optional(name: str) -> None:
    """KGDB clinical group: primary + secondary from KGDB's seven HPO groups, a sourced
    rationale (<= 400); not required, shown in the Summary tab after the evidence summary."""
    from app.core.schema_validator import SchemaValidator
    from app.services.evidence_ids import evidence_errors

    schema = SCHEMAS[name]
    group = schema["field_definitions"]["clinical_group"]["properties"]
    keys = ["complement", "cakut", "glomerulopathy", "cyst_cilio", "tubulopathy"]
    keys += ["nephrolithiasis", "neoplasia"]
    for field in ("primary", "secondary"):
        assert [o["value"] for o in group[field]["options"]] == keys
    assert "clinical_group" not in schema.get("required_fields", [])
    summary = schema["ui_configuration"]["layout"]["tabs"][0]["sections"]
    assert [s["name"] for s in summary][:2] == ["Evidence summary", "Clinical group"]

    def errors(value: dict[str, Any]) -> set[str]:
        result = SchemaValidator().validate_evidence_data(
            {"clinical_group": value}, schema["field_definitions"], schema
        )
        refused = {
            e.field_path for e in result.errors if "clinical_group" in e.field_path
        }
        return refused | {
            e.path for e in evidence_errors({"clinical_group": value}, schema)
        }

    ok = {"primary": "cakut", "secondary": ["tubulopathy"], "rationale": "x" * 400}
    assert errors(ok) == set()
    assert errors({"primary": "kidney"}) != set()
    assert errors({**ok, "rationale": "x" * 401}) == {"clinical_group.rationale"}
