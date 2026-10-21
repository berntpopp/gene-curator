"""Catalogue regressions through the public API."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import ActiveCuration, CurationNew, Gene

pytestmark = pytest.mark.unit


@pytest.fixture
def active_curation(db_session: Session, test_curation: CurationNew) -> CurationNew:
    db_session.add(
        ActiveCuration(
            gene_id=test_curation.gene_id,
            scope_id=test_curation.scope_id,
            curation_id=test_curation.id,
            activated_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    return test_curation


@pytest.mark.parametrize("query", ["NAA10", "ARD1", "TE2"])
def test_search_matches_symbol_alias_and_previous_symbol(
    client: TestClient,
    db_session: Session,
    test_gene: Gene,
    active_curation: CurationNew,
    query: str,
) -> None:
    test_gene.approved_symbol = "NAA10"
    test_gene.alias_symbols = ["ARD1"]
    test_gene.previous_symbols = ["TE2"]
    db_session.commit()

    response = client.get("/api/v1/gene-catalogue/", params={"search": query})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [entry["approved_symbol"] for entry in response.json()["entries"]] == [
        "NAA10"
    ]
    missing = client.get("/api/v1/gene-catalogue/", params={"search": "UNMATCHED"})
    assert missing.status_code == 200
    assert missing.json()["entries"] == []


def test_scopes_filter_matches_response_schema(
    client: TestClient, active_curation: CurationNew
) -> None:
    response = client.get("/api/v1/gene-catalogue/filters/scopes")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(active_curation.scope_id),
            "name": "test-scope",
            "display_name": "Test Scope",
            "is_active": True,
        }
    ]


def test_catalogue_returns_disease_from_precuration(
    client: TestClient,
    db_session: Session,
    active_curation: CurationNew,
    test_precuration,
) -> None:
    test_precuration.evidence_data = {
        "disease_name": "NAA10-related syndrome",
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "X-linked",
    }
    active_curation.precuration_id = test_precuration.id
    db_session.commit()
    response = client.get("/api/v1/gene-catalogue/")
    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["diseases"] == ["NAA10-related syndrome"]
    detail = entry["scope_curations"][0]
    assert detail["disease_name"] == "NAA10-related syndrome"
    assert detail["mondo_id"] == "MONDO:0000001"
    assert detail["mode_of_inheritance"] == "X-linked"


def test_sort_by_total_curations_and_unknown_sort_rejected(
    client: TestClient, active_curation: CurationNew
) -> None:
    ok = client.get(
        "/api/v1/gene-catalogue/",
        params={"sort_by": "total_curations", "sort_order": "desc"},
    )
    assert ok.status_code == 200
    assert ok.json()["total"] == 1
    assert len(ok.json()["entries"]) == 1

    bad = client.get("/api/v1/gene-catalogue/", params={"sort_by": "nope"})
    assert bad.status_code == 422
