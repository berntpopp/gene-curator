"""`source` field type (#593): identifier formats per kind, refused by field path."""

from typing import Any

import pytest

from app.core.schema_validation_result import SchemaValidationResult
from app.core.schema_validator import schema_validator
from app.core.source_field import source_errors

pytestmark = pytest.mark.unit

GOOD = [
    ("pmid", "12345678"),
    ("doi", "10.1038/s41586-020-2308-7"),
    ("clinvar", "VCV000012345"),
    ("clinvar", "SCV000123456.2"),
    ("clinvar", "RCV000000123"),
    ("clingen_allele", "CA123456"),
    ("clingen_validity", "CGGV:assertion_6c4f6a5e-4b59-4b0f-8b55-7c1b2a7c6a10"),
    ("url", "https://example.org/record/1"),
    ("database", "LOVD #0001234"),
]
BAD = [
    ("pmid", "PMID12"),
    ("doi", "11.1038/x"),
    ("doi", "10.12/short-registrant"),
    ("clinvar", "VCV12345"),
    ("clinvar", "NCV000012345"),
    ("clingen_allele", "CAX12"),
    ("clingen_validity", "CGGV:12345"),
    ("url", "javascript:alert(1)"),
]


def _errors(value: Any) -> list[tuple[str, str]]:
    res = SchemaValidationResult()
    source_errors("rows[0].source", value, {}, res)
    return [(e["field"], e["message"]) for e in res.errors]


@pytest.mark.parametrize(("kind", "ident"), GOOD)
def test_good_ids_pass(kind: str, ident: str) -> None:
    assert _errors({"kind": kind, "id": ident}) == []


@pytest.mark.parametrize(("kind", "ident"), BAD)
def test_bad_ids_are_refused_with_the_field_path(kind: str, ident: str) -> None:
    [(path, _)] = _errors({"kind": kind, "id": ident})
    assert path == "rows[0].source.id"


def test_genefoundry_provenance_is_checked_and_blank_is_fine() -> None:
    full = {
        "kind": "clinvar",
        "id": "VCV000012345",
        "url": "https://www.ncbi.nlm.nih.gov/clinvar/variation/12345/",
        "title": "NM_000000.0:c.1A>G",
        "retrieved_at": "2026-10-31T12:00:00Z",
        "tool": "genefoundry:clinvar_get_variant",
        "record_sha256": "a" * 64,
        "citation": "ClinVar VCV000012345",
    }
    assert _errors(full) == []
    assert _errors({}) == [] and _errors(None) == [] and _errors({"kind": ""}) == []
    bad = {
        **full,
        "url": "ftp://x",
        "retrieved_at": "yesterday",
        "record_sha256": "xyz",
        "title": 3,
    }
    assert [p for p, _ in _errors(bad)] == [
        "rows[0].source.url",
        "rows[0].source.retrieved_at",
        "rows[0].source.record_sha256",
        "rows[0].source.title",
    ]
    assert [p for p, _ in _errors({"kind": "book", "id": "x"})] == [
        "rows[0].source.kind"
    ]
    assert [p for p, _ in _errors({"kind": "doi"})] == ["rows[0].source.id"]
    assert [p for p, _ in _errors("12345")] == ["rows[0].source"]
    assert _errors({"kind": "url", "url": "https://example.org"}) == []


def test_a_list_of_sources_names_each_item() -> None:
    value = [{"kind": "pmid", "id": "1"}, {"kind": "doi", "id": "x"}]
    assert [p for p, _ in _errors(value)] == ["rows[0].source[1].id"]


def test_table_cells_and_source_lists_are_validated_at_submit() -> None:
    definition = {
        "field_definitions": {
            "probands": {
                "type": "evidence_table",
                "columns": {"label": {"type": "text"}, "sources": {"type": "source"}},
            },
            "references": {"type": "array", "items": {"type": "source"}},
        }
    }
    evidence = {
        "probands": [
            {"label": "P1", "sources": [{"kind": "clinvar", "id": "VCV1"}]},
            {"label": "P2", "sources": {"kind": "pmid", "id": "123"}},
        ],
        "references": [{"kind": "clingen_allele", "id": "CA1"}, {"kind": "doi"}],
    }
    result = schema_validator.validate_evidence_data(evidence, definition)
    assert sorted(e["field"] for e in result.errors) == [
        "probands[0].sources[0].id",
        "references[1].id",
    ]
