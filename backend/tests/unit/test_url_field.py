"""#538: `url` fields and evidence-table columns publish and accept real-world http(s) URLs."""

from typing import Any

import pytest

from app.core.schema_validator import SchemaValidator
from tests.unit.test_schema_validators_seeded import errors

pytestmark = pytest.mark.unit

VALID = [
    "https://www.erknet.org/subregistries/adtkd-registry",
    "https://www.medrxiv.org/content/10.64898/2026.05.27.26352937v1",
    "https://pkdb.mayo.edu/search?gene=PKD1&q=c.1-2A>G#top",
    "http://localhost:8080/a:b",
    " https://adtkd.de ",
]
INVALID = [
    "javascript:alert(1)",
    "data:text/html,x",
    "ftp://x.org",
    "https://",
    "adtkd.de",
    "https://exa mple.com",
    5,
]
FIELDS = {
    "home": {"type": "url"},
    "resources": {
        "type": "evidence_table",
        "columns": {"name": {"type": "text"}, "link": {"type": "url"}},
    },
}


def url_errors(data: dict[str, Any]) -> list[str]:
    result = SchemaValidator().validate_evidence_data(
        data, {"field_definitions": FIELDS}
    )
    return [e["field"] for e in result.errors if e["type"] == "format"]


def test_schema_with_url_fields_and_columns_publishes() -> None:
    assert errors(field_definitions=FIELDS, validation_rules={}) == []


@pytest.mark.parametrize("url", VALID)
def test_valid_urls_pass(url: str) -> None:
    assert url_errors({"home": url, "resources": [{"link": url}]}) == []


@pytest.mark.parametrize("url", INVALID)
def test_invalid_urls_fail_in_fields_and_cells(url: Any) -> None:
    rows = [{"link": VALID[0]}, {"name": "x", "link": url}]
    assert url_errors({"home": url, "resources": rows}) == [
        "home",
        "resources[1].link",
    ]


def test_blank_cells_are_not_checked() -> None:
    assert url_errors({"resources": [{"name": "x"}, {"link": ""}, "junk"]}) == []


def test_list_columns_are_checked() -> None:
    fields = {"t": {"type": "evidence_table", "columns": [{"id": "u", "type": "url"}]}}
    schema = {"field_definitions": fields}
    result = SchemaValidator().validate_evidence_data({"t": [{"u": "x"}]}, schema)
    assert [e["field"] for e in result.errors] == ["t[0].u"]


def test_a_cleared_optional_url_is_no_error() -> None:
    assert url_errors({"home": ""}) == []
    fields = {"home": {"type": "url", "required": True}}
    result = SchemaValidator().validate_evidence_data(
        {"home": ""}, {"field_definitions": fields}
    )
    assert [e["type"] for e in result.errors] == ["required"]


def test_a_required_url_of_only_spaces_fails() -> None:
    fields = {"home": {"type": "url", "required": True}}
    result = SchemaValidator().validate_evidence_data(
        {"home": "   "}, {"field_definitions": fields}
    )
    assert result.errors and not result.is_valid
