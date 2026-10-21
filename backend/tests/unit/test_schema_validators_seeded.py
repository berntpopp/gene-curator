"""#207/#269: seeded schema formats are accepted; cheap static checks name a JSON path."""

from typing import Any, ClassVar

import pytest

from app.core.schema_rules import check_schema_definition

pytestmark = pytest.mark.unit

# Stage map, sections and validation_rules as database/sql/016_seed_precuration_schema.sql seeds them
PRECURATION: dict[str, Any] = {
    "field_definitions": {
        "sections": [
            {
                "id": "disease",
                "fields": [{"id": "mondo_id", "type": "external_reference"}],
            },
            {"id": "moi", "fields": [{"id": "mode_of_inheritance", "type": "enum"}]},
        ]
    },
    "workflow_states": {
        "entry": {"allowed_transitions": ["precuration"]},
        "precuration": {"allowed_transitions": ["review"]},
        "review": {"allowed_transitions": ["precuration", "approved"]},
        "approved": {"allowed_transitions": ["curation"]},
    },
    "ui_configuration": {"form_layout": "wizard"},
    "validation_rules": {
        "required_fields": ["mondo_id", "mode_of_inheritance"],
        "custom_validators": [{"field": "mondo_id", "pattern": "^MONDO:"}],
    },
}


def errors(**changes: Any) -> list[tuple[str, str]]:
    schema = {**PRECURATION, **changes}
    return [(p, m) for s, p, m in check_schema_definition(schema) if s == "error"]


def test_seeded_precuration_shape_has_no_errors() -> None:
    assert errors() == []


def test_json_schema_style_fields_accepted() -> None:
    defs = {"a": {"type": "string", "title": "A"}, "b": {"type": "integer"}}
    assert errors(field_definitions=defs, validation_rules={}) == []


class TestTransitions:
    def test_unknown_target_is_reported_at_its_index(self) -> None:
        states = {
            **PRECURATION["workflow_states"],
            "review": {"allowed_transitions": ["nope"]},
        }
        assert errors(workflow_states=states) == [
            (
                "workflow_states.review.allowed_transitions[0]",
                "Unknown transition target: nope",
            )
        ]

    @pytest.mark.parametrize("value", [0, 6, 2.5, True, "2"])
    def test_reviewers_required_must_be_1_to_5(self, value: Any) -> None:
        states = {
            **PRECURATION["workflow_states"],
            "review": {"reviewers_required": value},
        }
        assert [p for p, _ in errors(workflow_states=states)] == [
            "workflow_states.review.reviewers_required"
        ]

    @pytest.mark.parametrize("value", [1, 5])
    def test_reviewers_required_in_range_is_fine(self, value: int) -> None:
        states = {
            **PRECURATION["workflow_states"],
            "review": {"reviewers_required": value},
        }
        assert errors(workflow_states=states) == []


class TestValidationRulesNameFields:
    def test_unknown_required_field(self) -> None:
        rules = {"required_fields": ["mondo_id", "ghost"]}
        assert errors(validation_rules=rules) == [
            (
                "validation_rules.required_fields[1]",
                "Unknown field in required_fields: ghost",
            )
        ]

    def test_unknown_custom_validator_field(self) -> None:
        rules = {"custom_validators": [{"field": "ghost"}, "junk"]}
        assert [p for p, _ in errors(validation_rules=rules)] == [
            "validation_rules.custom_validators[0].field",
            "validation_rules.custom_validators[1].field",
        ]


class TestEvidenceTable:
    def table(self, columns: Any) -> list[tuple[str, str]]:
        defs = {"proband": {"type": "evidence_table", "columns": columns}}
        return errors(field_definitions=defs, validation_rules={})

    def test_typed_columns_pass(self) -> None:
        assert self.table({"pmid": {"type": "publication"}}) == []
        assert self.table([{"id": "pmid", "type": "publication"}]) == []

    def test_untyped_column_reported(self) -> None:
        assert self.table({"pmid": {"label": "PMID"}}) == [
            (
                "field_definitions.proband.columns.pmid.type",
                "Column 'pmid' of 'proband' has no type",
            )
        ]
        assert [p for p, _ in self.table([{"type": "text"}, "x"])] == [
            "field_definitions.proband.columns.1.type"
        ]

    def test_missing_columns_reported(self) -> None:
        assert [p for p, _ in self.table(None)] == ["field_definitions.proband.columns"]


class TestPointModel:
    """W4E interpreter shape: sections > categories > types; bands first match wins."""

    MODEL: ClassVar[dict[str, Any]] = {
        "total_cap": 18,
        "sections": [
            {
                "key": "genetic",
                "cap": 12,
                "categories": [
                    {
                        "key": "proband",
                        "cap": 12,
                        "combine": "sum",
                        "types": [{"path": "p", "default": 1.5, "range": [0, 3]}],
                    },
                    {"key": "segregation", "combine": "max", "types": []},
                ],
            },
            {"key": "experimental", "cap": 6.0, "categories": []},
        ],
        "overrides": [{"when": "contradictory", "class": "disputed"}],
        # as templates/clingen_sop_v11.json orders them
        "bands": [
            {"class": "definitive", "min": 12, "requires": "replicated_over_time"},
            {"class": "strong", "min": 12},
            {"class": "moderate", "min": 7},
            {"class": "limited", "min": 0.1},
            {"class": "refuted"},
        ],
    }
    P = "scoring_configuration.point_model"

    def scoring(self, **changes: Any) -> list[str]:
        model = {k: v for k, v in {**self.MODEL, **changes}.items() if v is not None}
        cfg = {"engine": "clingen_sop_v11", "point_model": model}
        return [p.removeprefix(self.P) for p, _ in errors(scoring_configuration=cfg)]

    def section(self, **cat: Any) -> list[dict[str, Any]]:
        return [{"key": "s", "categories": [{"key": "c", "types": [], **cat}]}]

    def test_valid_point_model(self) -> None:
        assert self.scoring() == []

    @pytest.mark.parametrize("key", ["sections", "bands"])
    @pytest.mark.parametrize("value", [None, {"a": 1}])
    def test_sections_and_bands_are_required_lists(self, key: str, value: Any) -> None:
        assert self.scoring(**{key: value}) == [f".{key}"]

    def test_scorer_indexed_keys_are_required(self) -> None:
        sections = [
            "junk",
            {"categories": [{"types": [{}]}, {"key": "c"}]},
            {"key": "s"},
        ]
        assert self.scoring(sections=sections) == [
            ".sections[0]",
            ".sections[1].key",
            ".sections[1].categories[0].key",
            ".sections[1].categories[0].types[0].path",
            ".sections[1].categories[1].types",
            ".sections[2].categories",
        ]

    def test_overrides_and_bands_need_their_keys(self) -> None:
        overrides = [{"class": "disputed"}, "junk"]
        bands = [{"min": 1}, 5]
        assert self.scoring(overrides=overrides, bands=bands) == [
            ".overrides[1]",
            ".overrides[0].when",
            ".bands[1]",
            ".bands[0].class",
        ]

    def test_caps_must_be_numeric_and_keys_unique(self) -> None:
        sections = [
            {"key": "a", "cap": "12", "categories": []},
            {"key": "a", "cap": True, "categories": []},
        ]
        assert self.scoring(total_cap="18", sections=sections) == [
            ".total_cap",
            ".sections[0].cap",
            ".sections[1].cap",
            ".sections[1].key",
        ]
        cats = [{"key": "c", "types": []}, {"key": "c", "types": []}]
        assert self.scoring(sections=[{"key": "s", "categories": cats}]) == [
            ".sections[0].categories[1].key"
        ]

    def test_optional_settings_are_type_checked(self) -> None:
        item = {"path": "p", "rule": ["case_row"], "points_key": 1, "default": "abc"}
        sections = self.section(types=[item])
        bands = [{"class": "strong", "min": 12, "requires": ["replicated"]}]
        assert self.scoring(sections=sections, bands=bands) == [
            ".sections[0].categories[0].types[0].rule",
            ".sections[0].categories[0].types[0].points_key",
            ".sections[0].categories[0].types[0].default",
            ".bands[0].requires",
        ]

    @pytest.mark.parametrize("rng", [[3, 0], [0], ["0", 1], "0..3"])
    def test_type_range_must_be_ordered_pair(self, rng: Any) -> None:
        sections = self.section(combine="avg", types=[{"path": "p", "range": rng}])
        assert self.scoring(sections=sections) == [
            ".sections[0].categories[0].combine",
            ".sections[0].categories[0].types[0].range",
        ]

    @pytest.mark.parametrize("mins", [[1, 7], ["1"], [None]])
    def test_bands_must_not_increase(self, mins: list[Any]) -> None:
        bands = [{"class": f"b{i}", "min": m} for i, m in enumerate(mins)]
        assert self.scoring(bands=bands) == [".bands"]
