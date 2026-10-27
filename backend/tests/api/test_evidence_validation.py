"""Evidence items are validated against the curation's schema (MCP study round 1, finding 2)."""

import pytest
from fastapi.testclient import TestClient

from app.models.models import CurationNew, EvidenceItem
from app.schemas.validation import PMIDValidationResult
from app.services.evidence_validation import evidence_item_errors
from app.services.publication_service import PublicationService

pytestmark = pytest.mark.unit

STUDY_PAYLOAD = {  # what the T5b agent sent: a flat category and free-form keys
    "evidence_category": "case_level",
    "evidence_type": "genetic",
    "evidence_data": {"pmid": "123", "variant": "homozygous NPHP1 deletion"},
}


def _post(client: TestClient, token: str, curation: CurationNew, body: dict) -> object:
    return client.post(
        f"/api/v1/curations/{curation.id}/evidence",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


def _errors(response) -> dict[str, str]:  # type: ignore[no-untyped-def]
    assert response.status_code == 422, response.text
    return {".".join(e["loc"][1:]): e["msg"] for e in response.json()["detail"]}


def _row(category: str, data: object, kind: str = "genetic") -> dict:
    return {"evidence_category": category, "evidence_type": kind, "evidence_data": data}


@pytest.mark.parametrize(
    ("body", "field", "hint"),
    [
        (STUDY_PAYLOAD, "evidence_category", "segregation"),
        (_row("segregation", {"pmid": "1"}, "functional"), "evidence_type", "genetic"),
        (_row("segregation", {}), "evidence_data", "pmid"),
        (_row("segregation", {"pmid": "", "points": None}), "evidence_data", "pmid"),
        (_row("segregation", {"pmid": "abc"}), "evidence_data.pmid", "digits"),
        (
            _row("segregation", {"pmid": "1", "zyg": "hom"}),
            "evidence_data.zyg",
            "lod_score",
        ),
        (_row("segregation", {"pmid": "1", "points": 99}), "evidence_data.points", "3"),
        (
            _row("segregation", {"pmid": "1"}, "experimental"),
            "evidence_category",
            "function.expression",
        ),
    ],
)
def test_create_rejects_items_that_do_not_fit_the_schema(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    evidence_schema: object,
    db_session,
    body: dict,
    field: str,
    hint: str,
) -> None:
    errors = _errors(_post(client, curator_token, test_curation, body))
    assert hint in errors[field]
    assert db_session.query(EvidenceItem).count() == 0


def test_valid_item_is_stored_and_says_it_is_unscored(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    evidence_schema: object,
) -> None:
    body = _row(
        "function.expression", {"pmid": "PMID:31558469", "points": 0.5}, "experimental"
    )
    r = _post(client, curator_token, test_curation, body)
    assert r.status_code == 201, r.text
    assert r.json()["computed_score"] is None
    assert "not scored" in r.json()["score_note"]
    assert "save_draft_curations" in r.json()["score_note"]


def test_update_validates_against_the_items_table(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    test_evidence_item: EvidenceItem,
    evidence_schema: object,
) -> None:
    url = f"/api/v1/curations/{test_curation.id}/evidence/{test_evidence_item.id}"
    h = {"Authorization": f"Bearer {curator_token}"}
    bad = client.put(url, json={"evidence_data": {"pmid": "12x"}}, headers=h)
    assert "digits" in _errors(bad)["evidence_data.pmid"]
    ok = client.put(url, json={"validation_status": "valid"}, headers=h)
    assert ok.status_code == 200, ok.text


def test_schema_without_evidence_tables_points_to_evidence_data(
    client: TestClient, curator_token: str, test_curation: CurationNew
) -> None:
    errors = _errors(_post(client, curator_token, test_curation, STUDY_PAYLOAD))
    assert "save_draft_curations" in errors["evidence_category"]


def test_legacy_array_group_is_not_an_evidence_table() -> None:
    legacy = {
        "field_definitions": {
            "genetic_evidence": {"type": "array", "items": {"properties": {"pmid": {}}}}
        }
    }
    (error,) = evidence_item_errors(legacy, "case_level", "genetic", {"pmid": "1"})
    assert error["loc"] == ["body", "evidence_category"]


def test_pmid_lookup_unknown_is_refused_unreachable_is_flagged(
    client: TestClient,
    curator_token: str,
    test_curation: CurationNew,
    evidence_schema: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existence via the publication service: not found is 422, offline saves as unverified."""
    outcome = {"123": "Publication not found: 123", "456": "API timeout; retry lookup"}

    async def fetch(self: PublicationService, pmid: str) -> PMIDValidationResult:
        error = outcome.get(pmid)
        return PMIDValidationResult(pmid=pmid, is_valid=error is None, error=error)

    monkeypatch.setattr(PublicationService, "fetch_publication", fetch)
    errors = _errors(
        _post(
            client, curator_token, test_curation, _row("segregation", {"pmid": "123"})
        )
    )
    assert "123 not found" in errors["evidence_data.pmid"]
    r = _post(
        client, curator_token, test_curation, _row("segregation", {"pmid": "PMID: 456"})
    )
    assert r.status_code == 201, r.text
    assert r.json()["unverified_pmids"] == ["456"]
    ok = _post(
        client, curator_token, test_curation, _row("segregation", {"pmid": "789"})
    )
    assert ok.status_code == 201 and ok.json()["unverified_pmids"] == []


def test_legacy_category_item_stays_editable_with_pmid_checks(
    client: TestClient,
    curator_token: str,
    db_session,
    test_curation: CurationNew,
    test_evidence_item: EvidenceItem,
    evidence_schema: object,
) -> None:
    test_evidence_item.evidence_category = "case_level"  # flat, pre-table category
    db_session.commit()
    url = f"/api/v1/curations/{test_curation.id}/evidence/{test_evidence_item.id}"
    h = {"Authorization": f"Bearer {curator_token}"}
    ok = client.put(
        url, json={"evidence_data": {"pmid": "1", "proband_count": 2}}, headers=h
    )
    assert ok.status_code == 200, ok.text
    bad = client.put(url, json={"evidence_data": {"pmid": "12x"}}, headers=h)
    assert "digits" in _errors(bad)["evidence_data.pmid"]
