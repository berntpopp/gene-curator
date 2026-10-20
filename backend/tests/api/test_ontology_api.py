"""API tests for /ontology endpoints (MONDO, OMIM, HPO search and validation).

OntologyService is patched at the class level so no request leaves the process.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.schemas.validation import (
    HPOInheritancePattern,
    HPOInheritanceResponse,
    HPOSearchResponse,
    HPOSearchResult,
    MONDOSearchResponse,
    MONDOSearchResult,
    OMIMDiseaseResult,
    OMIMSearchResponse,
)
from app.services.ontology_service import OntologyService

pytestmark = pytest.mark.unit

BASE = "/api/v1/ontology"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ontology_close(monkeypatch: MonkeyPatch) -> AsyncMock:
    close = AsyncMock()
    monkeypatch.setattr(OntologyService, "close", close)
    return close


def test_ontology_routes_require_authentication(client: TestClient) -> None:
    response = client.post(f"{BASE}/mondo/search", json={"query": "x"})
    assert response.status_code in (401, 403)


def test_mondo_search_returns_service_payload(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    payload = MONDOSearchResponse(
        query="breast",
        total_results=1,
        results=[MONDOSearchResult(mondo_id="MONDO:0007254", label="breast cancer")],
    )
    search = AsyncMock(return_value=payload)
    monkeypatch.setattr(OntologyService, "search_mondo", search)

    response = client.post(
        f"{BASE}/mondo/search",
        json={"query": "breast", "limit": 3},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["mondo_id"] == "MONDO:0007254"
    search.assert_awaited_once_with("breast", 3)
    ontology_close.assert_awaited_once()


def test_mondo_search_validates_request_body(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(f"{BASE}/mondo/search", json={}, headers=_auth(admin_token))
    assert response.status_code == 422


def test_omim_search_returns_results(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    payload = OMIMSearchResponse(query="300855", total_results=0, results=[])
    search = AsyncMock(return_value=payload)
    monkeypatch.setattr(OntologyService, "search_omim", search)

    response = client.post(
        f"{BASE}/omim/search", json={"query": "300855"}, headers=_auth(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["total_results"] == 0
    search.assert_awaited_once()


def test_omim_detail_returns_disease(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    disease = OMIMDiseaseResult(omim_id="OMIM:300855", name="Rett syndrome")
    fetch = AsyncMock(return_value=disease)
    monkeypatch.setattr(OntologyService, "get_omim_disease", fetch)

    response = client.get(f"{BASE}/omim/OMIM:300855", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()["name"] == "Rett syndrome"
    fetch.assert_awaited_once_with("OMIM:300855")


def test_omim_detail_404_when_unknown(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    monkeypatch.setattr(
        OntologyService, "get_omim_disease", AsyncMock(return_value=None)
    )

    response = client.get(f"{BASE}/omim/999999", headers=_auth(admin_token))

    assert response.status_code == 404
    assert "999999" in response.json()["detail"]


def test_hpo_search_returns_results(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    payload = HPOSearchResponse(
        query="seizure",
        total_results=1,
        results=[HPOSearchResult(hpo_id="HP:0001250", name="Seizure")],
    )
    search = AsyncMock(return_value=payload)
    monkeypatch.setattr(OntologyService, "search_hpo", search)

    response = client.post(
        f"{BASE}/hpo/search", json={"query": "seizure"}, headers=_auth(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["hpo_id"] == "HP:0001250"
    search.assert_awaited_once()


def test_hpo_validate_reports_found_flag_via_limit_one(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    search = AsyncMock(
        return_value=HPOSearchResponse(query="HP:0001250", total_results=0, results=[])
    )
    monkeypatch.setattr(OntologyService, "search_hpo", search)

    response = client.get(f"{BASE}/hpo/HP:0001250/validate", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()["total_results"] == 0
    search.assert_awaited_once_with("HP:0001250", limit=1)


def test_inheritance_patterns_endpoint(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    ontology_close: AsyncMock,
) -> None:
    payload = HPOInheritanceResponse(
        total_patterns=1,
        mendelian=[
            HPOInheritancePattern(
                hpo_id="HP:0000007",
                name="Autosomal recessive inheritance",
                category="mendelian",
            )
        ],
        non_mendelian=[],
        cached=True,
    )
    monkeypatch.setattr(
        OntologyService, "get_inheritance_patterns", AsyncMock(return_value=payload)
    )

    response = client.get(f"{BASE}/hpo/inheritance", headers=_auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_patterns"] == 1
    assert body["cached"] is True
    assert body["mendelian"][0]["hpo_id"] == "HP:0000007"
