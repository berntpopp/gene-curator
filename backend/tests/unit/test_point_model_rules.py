"""#576: native row rules (``points_when``, ``rule: step``), validator cross-checks of the
paths a point model reads, and the neutral ``point_model`` engine alias."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from app.scoring.clingen import ClinGenEngine
from app.scoring.point_model import score
from app.scoring.registry import engine_for, scoring_registry
from tests.unit.test_schema_validators_seeded import errors

pytestmark = pytest.mark.unit

PMID = "12345678"
P = "scoring_configuration.point_model"
# KGDB draft-4 rules; an exclusion (0 points) wins wherever it stands
PROBAND_RULES = [
    {"field": "de_novo", "in": ["confirmed"], "points": 1.5},
    {"field": "duplicate_of", "present": True, "points": 0},
    {"field": "phase", "in": ["not_given", "unknown"], "points": 0},
    {"field": "allele_frequency", "gt": 0.0025, "points": 0},
    {
        "field": "allele_frequency",
        "gt": 0.0001,
        "and": [{"field": "zygosity", "in": ["heterozygous"]}],
        "points": 0,
    },
]
LOD = {
    "rule": "step",
    "field": "lod",
    "steps": [
        {"min": 2, "points": 1},
        {"min": 3, "points": 2},
        {"min": 5, "points": 3},
    ],
}


def _model(*types: dict[str, Any]) -> dict[str, Any]:
    return {
        "sections": [{"key": "g", "categories": [{"key": "c", "types": list(types)}]}],
        "bands": [{"class": "any"}],
    }


def _probands(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"g": {"probands": [{"pmid": PMID, **r} for r in rows]}}


PROBANDS = {"path": "probands", "default": 1, "points_when": PROBAND_RULES}


class TestPointsWhen:
    @pytest.mark.parametrize(
        ("row", "points"),
        [
            ({"de_novo": "confirmed"}, 1.5),
            ({"de_novo": "assumed"}, 1),
            ({"duplicate_of": "P1"}, 0),
            ({"de_novo": "confirmed", "duplicate_of": "P1"}, 0),
            ({"de_novo": "confirmed", "duplicate_of": " "}, 1.5),  # blank: not present
            ({"de_novo": "confirmed", "duplicate_of": None}, 1.5),
            ({"phase": "unknown"}, 0),
            ({"phase": "in_trans"}, 1),
            ({"allele_frequency": 0.01}, 0),
            ({"allele_frequency": "0.01"}, 0),  # a text cell still compares
            ({"allele_frequency": 0.001, "zygosity": "heterozygous"}, 0),
            ({"allele_frequency": 0.001, "zygosity": "homozygous"}, 1),
            ({"allele_frequency": "n/a"}, 1),  # no number: the comparison never holds
        ],
    )
    def test_row_fields_set_the_points(
        self, row: dict[str, Any], points: float
    ) -> None:
        assert score(_model(PROBANDS), _probands(row))["total"] == points

    def test_in_is_strict(self) -> None:
        model = _model(
            {
                "path": "probands",
                "default": 1,
                "points_when": [{"field": "flag", "in": [True], "points": 2}],
            }
        )
        assert score(model, _probands({"flag": 1}))["total"] == 1
        assert score(model, _probands({"flag": True}))["total"] == 2

    def test_trace_lists_each_applied_rule(self) -> None:
        result = score(_model(PROBANDS), _probands({}, {"de_novo": "confirmed"}))
        assert result["trace"]["rules_applied"] == [
            {
                "path": "g.probands[1]",
                "rule": "points_when",
                "index": 0,
                "entered": 1.0,
                "points": 1.5,
                "applied": True,
            }
        ]
        assert "rules_applied" not in score(_model(PROBANDS), _probands({}))["trace"]

    @pytest.mark.parametrize(
        ("row", "points", "applied"),
        [
            ({"de_novo": "confirmed", "points": 0}, 0, False),  # curator judgement
            ({"de_novo": "confirmed", "points": 2}, 2, False),
            ({"de_novo": "confirmed", "points": ""}, 1.5, True),  # blank: rule fills
            ({"phase": "unknown", "points": 2}, 0, True),  # exclusion always wins
        ],
    )
    def test_entered_points_stand_unless_excluded(
        self, row: dict[str, Any], points: float, applied: bool
    ) -> None:
        result = score(_model(PROBANDS), _probands(row))
        assert result["total"] == points
        (entry,) = result["trace"]["rules_applied"]
        assert (entry["points"], entry["applied"]) == (points, applied)

    @pytest.mark.parametrize(
        ("row", "total"), [({"x": "a"}, 1), ({"x": ""}, 0), ({}, 0)]
    )
    def test_present_false_matches_blank(
        self, row: dict[str, Any], total: float
    ) -> None:
        rule = {"field": "x", "present": False, "points": 0}
        model = _model({"path": "probands", "default": 1, "points_when": [rule]})
        assert score(model, _probands(row))["total"] == total

    def test_set_points_still_need_a_citation(self) -> None:
        evidence = {"g": {"probands": [{"de_novo": "confirmed"}]}}  # no pmid
        result = score(_model(PROBANDS), evidence)
        assert result["total"] == 0
        assert result["excluded"] == [
            {"path": "g.probands[0]", "field": "pmid", "reason": "no_pmid"}
        ]


class TestStep:
    @pytest.mark.parametrize(
        ("lods", "points"),
        [([1.9], 0), ([2], 1), ([1.5, 1.5], 2), ([3, "2.5"], 3), ([9], 3)],
    )
    def test_summed_field_reaches_a_step(self, lods: list[Any], points: float) -> None:
        evidence = {"g": {"seg": [{"pmid": PMID, "lod": v} for v in lods]}}
        result = score(_model({"path": "seg", **LOD}), evidence)
        assert result["total"] == points
        assert result["trace"]["rules_applied"][0] == {
            "path": "g.seg",
            "rule": "step",
            "field": "lod",
            "sum": pytest.approx(sum(float(v) for v in lods)),
            "points": points,
        }

    def test_blank_uncited_and_non_numeric_rows(self) -> None:
        rows = [
            {"pmid": PMID, "lod": 2},
            {"lod": 3},
            {"pmid": PMID, "lod": "x"},
            {"pmid": PMID, "lod": " "},
            {"pmid": PMID},
        ]
        result = score(_model({"path": "seg", **LOD}), {"g": {"seg": rows}})
        assert result["total"] == 1
        assert result["excluded"] == [
            {"path": "g.seg[1]", "field": "pmid", "reason": "no_pmid"}
        ]
        assert result["trace"]["out_of_range"] == [
            {"path": "g.seg[2].lod", "value": "x", "range": None}
        ]

    def test_no_value_is_no_item(self) -> None:
        result = score(_model({"path": "seg", **LOD}), {"g": {"seg": [{"pmid": PMID}]}})
        assert result["total"] == 0
        assert "rules_applied" not in result["trace"]


def _scoring_errors(
    model: dict[str, Any], fields: dict[str, Any] | None = None
) -> list[str]:
    cfg = {"engine": "point_model", "point_model": model}
    changes: dict[str, Any] = {"scoring_configuration": cfg}
    if fields is not None:
        changes |= {"field_definitions": fields, "validation_rules": {}}
    return [p.removeprefix(P) for p, _ in errors(**changes)]


TYPE = ".sections[0].categories[0].types[0]"


class TestRuleShapes:
    def test_valid_rules(self) -> None:
        assert _scoring_errors(_model(PROBANDS, {"path": "seg", **LOD})) == []

    @pytest.mark.parametrize(
        ("rule", "paths"),
        [
            ({"field": "x", "points": 1}, [""]),
            ({"field": "x", "in": "a", "points": 1}, [".in"]),
            ({"field": "x", "gt": "1", "points": 1}, [".gt"]),
            ({"field": "x", "in": [1], "points": "1"}, [".points"]),
            ({"field": "x", "present": "yes", "points": 1}, [".present"]),
            ({"in": [1], "points": 1}, [".field"]),
            ({"field": "x", "in": [1], "points": 1, "when": 1}, [".when"]),
            ({"field": "x", "in": [1], "points": 1, "and": {}}, [".and"]),
            (
                {
                    "field": "x",
                    "in": [1],
                    "points": 1,
                    "and": [{"field": "y", "points": 1}],
                },
                [".and[0]", ".and[0].points"],
            ),
        ],
    )
    def test_bad_points_when(self, rule: dict[str, Any], paths: list[str]) -> None:
        found = _scoring_errors(_model({"path": "p", "points_when": [rule]}))
        assert sorted(found) == sorted(f"{TYPE}.points_when[0]{p}" for p in paths)

    def test_points_when_must_be_a_list(self) -> None:
        found = _scoring_errors(_model({"path": "p", "points_when": {}}))
        assert found == [f"{TYPE}.points_when"]

    @pytest.mark.parametrize(
        ("change", "paths"),
        [
            ({"field": None}, [".field"]),
            ({"steps": None}, [".steps"]),
            ({"steps": [{"min": 3, "points": 1}, {"min": 2, "points": 2}]}, [".steps"]),
            ({"steps": [{"min": 2, "points": 1}, {"min": 2, "points": 2}]}, [".steps"]),
            ({"steps": [{"min": 2}]}, [".steps"]),
        ],
    )
    def test_bad_step(self, change: dict[str, Any], paths: list[str]) -> None:
        rule = {k: v for k, v in {**LOD, **change}.items() if v is not None}
        found = _scoring_errors(_model({"path": "seg", **rule}))
        assert found == [f"{TYPE}{p}" for p in paths]

    def test_point_model_engine_needs_a_model(self) -> None:
        cfg = {"engine": "point_model"}
        assert [p for p, _ in errors(scoring_configuration=cfg)] == [P]


FIELDS: dict[str, Any] = {
    "g": {
        "type": "object",
        "properties": {
            "probands": {
                "type": "evidence_table",
                "columns": {
                    k: {"type": "text"}
                    for k in (
                        "pmid",
                        "points",
                        "duplicate_of",
                        "phase",
                        "allele_frequency",
                        "zygosity",
                        "de_novo",
                    )
                },
            },
            "seg": {
                "type": "array",
                "items": {"properties": {"lod": {"type": "number"}}},
            },
        },
    },
    "contra": {"type": "array", "item_schema": {"impact": {"type": "text"}}},
    "kind": {"type": "select", "options": [{"value": "a"}]},
    "note": {"type": "text", "show_when": {"kind": "a", "g.probands.0.phase": "x"}},
}


class TestPathCrossChecks:
    def test_known_paths_pass(self) -> None:
        model = {
            **_model(PROBANDS, {"path": "seg", **LOD}),
            "overrides": [
                {"when": "contra", "field": "impact", "in": ["d"], "class": "disputed"}
            ],
        }
        assert _scoring_errors(model, FIELDS) == []

    def test_typos_are_named(self) -> None:
        bad_rule = [
            {
                "field": "de_nov",
                "in": ["confirmed"],
                "points": 1.5,
                "and": [{"field": "zyg", "in": ["a"]}],
            }
        ]
        model = {
            "sections": [
                {
                    "key": "g",
                    "categories": [
                        {
                            "key": "c",
                            "types": [
                                {"path": "proband", "default": 1},
                                {"path": "probands", "points_when": bad_rule},
                                {"path": "seg", **LOD, "field": "lods"},
                            ],
                        }
                    ],
                },
                {"key": "experimental", "categories": []},
            ],
            "overrides": [
                {"when": "contra", "field": "impakt", "in": ["d"], "class": "x"},
                {"when": "contr", "class": "x"},
            ],
            "bands": [{"class": "any"}],
        }
        types = ".sections[0].categories[0].types"
        assert sorted(_scoring_errors(model, FIELDS)) == sorted(
            [
                ".sections[1].key",
                f"{types}[0].path",
                f"{types}[1].points_when[0].field",
                f"{types}[1].points_when[0].and[0].field",
                f"{types}[2].field",
                ".overrides[0].field",
                ".overrides[1].when",
            ]
        )

    def test_unrelated_fields_and_legacy_lists_are_not_checked(self) -> None:
        model = _model({"path": "nowhere"})
        assert _scoring_errors(model, {"x": {"type": "text"}}) == []
        legacy = {
            "g": {"type": "array", "items": {"properties": {"a": {"type": "text"}}}}
        }
        assert _scoring_errors(model, legacy) == []

    def test_unknown_show_when_targets(self) -> None:
        fields = {
            **FIELDS,
            "note": {"type": "text", "visible_when": {"knd": "a"}},
            "g": {
                "type": "object",
                "properties": {
                    "x": {"type": "text", "show_when": {"g.y": 1, "kind": "a"}}
                },
            },
        }
        found = errors(field_definitions=fields, validation_rules={})
        assert [p for p, _ in found] == [
            "field_definitions.g.properties.x.show_when.g.y",
            "field_definitions.note.visible_when.knd",
        ]

    def test_seeded_precuration_targets_pass(self) -> None:
        fields = {
            "sections": [
                {
                    "id": "s",
                    "fields": [
                        {"id": "moi", "type": "select"},
                        {"id": "notes", "type": "text", "show_when": {"moi": "Other"}},
                    ],
                }
            ]
        }
        assert errors(field_definitions=fields, validation_rules={}) == []


class TestEngineAlias:
    def test_point_model_scores_like_the_interpreter(self) -> None:
        cfg = {"engine": "point_model", "point_model": _model(PROBANDS)}
        engine = engine_for(cfg)
        assert engine.name == "point_model"
        result = engine.calculate_scores(_probands({"de_novo": "confirmed"}), cfg)
        assert (result.total_score, result.verdict) == (1.5, "any")
        assert "sop_version" not in result.metadata
        assert ClinGenEngine().calculate_scores({}, {}).metadata["sop_version"] == "v11"
        assert engine.supports_schema("ClinGen_SOP", "11.0") is False
        assert scoring_registry.get_engine_info("point_model", cfg)[
            "supported_verdicts"
        ] == ["any"]


def test_clingen_scores_are_byte_identical() -> None:
    """Digest of every golden case's full result, captured before #576."""
    digest = hashlib.sha256()
    golden = Path(__file__).with_name("point_model_golden.jsonl")
    for line in golden.read_text().splitlines():
        r = ClinGenEngine().calculate_scores(json.loads(line)["evidence"], {})
        parts = [
            r.scores,
            r.verdict,
            r.verdict_rationale,
            r.evidence_breakdown,
            r.warnings,
        ]
        digest.update(json.dumps(parts, sort_keys=True).encode())
    assert digest.hexdigest() == (
        "e5be33ad5cd7e26e434a93ac697b692b3db51adb907cf0050689de1a546a34ca"
    )
