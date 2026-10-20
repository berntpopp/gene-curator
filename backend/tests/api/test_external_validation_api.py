"""API tests for /external-validation endpoints.

External validators and the validation service are patched at the class level so
no request leaves the process; the tests cover auth, parameter validation and the
response shapes the endpoints return.
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.schemas.validation import (
    HGNCGeneSearchResult,
    HGNCSearchResponse,
    ValidationResult,
)
from app.services.validation_service import ValidationService
from app.services.validators import HGNCValidator

pytestmark = pytest.mark.unit

BASE = "/api/v1/external-validation"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def valid_result() -> ValidationResult:
    return ValidationResult(
        is_valid=True,
        status="valid",
        data={"approved_symbol": "BRCA1", "hgnc_id": "HGNC:1100"},
    )


def test_endpoints_require_authentication(client: TestClient) -> None:
    assert client.post(f"{BASE}/validate/hgnc?gene_symbol=BRCA1").status_code in (
        401,
        403,
    )
    assert client.get(f"{BASE}/cache/statistics").status_code in (401, 403)


def test_validate_hgnc_returns_service_result(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    valid_result: ValidationResult,
) -> None:
    mock = AsyncMock(return_value=valid_result)
    monkeypatch.setattr(ValidationService, "validate", mock)

    response = client.post(
        f"{BASE}/validate/hgnc?gene_symbol=BRCA1&skip_cache=true",
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is True
    assert response.json()["data"]["hgnc_id"] == "HGNC:1100"
    mock.assert_awaited_once_with("hgnc", "BRCA1", skip_cache=True)


def test_validate_hgnc_rejects_empty_symbol(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        f"{BASE}/validate/hgnc?gene_symbol=",
        headers=_auth(admin_token),
    )
    assert response.status_code == 422


def test_validate_pubmed_requires_numeric_pmid(
    client: TestClient, admin_token: str
) -> None:
    bad = client.post(f"{BASE}/validate/pubmed?pmid=PMID1", headers=_auth(admin_token))
    assert bad.status_code == 422


def test_validate_pubmed_passes_pmid_to_service(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
) -> None:
    mock = AsyncMock(return_value=ValidationResult(is_valid=False, status="not_found"))
    monkeypatch.setattr(ValidationService, "validate", mock)

    response = client.post(
        f"{BASE}/validate/pubmed?pmid=31558469", headers=_auth(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "not_found"
    mock.assert_awaited_once_with("pubmed", "31558469", skip_cache=False)


def test_validate_hpo_requires_seven_digit_term(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        f"{BASE}/validate/hpo?hpo_term=HP:12", headers=_auth(admin_token)
    )
    assert response.status_code == 422


def test_validate_hpo_passes_term_to_service(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
) -> None:
    mock = AsyncMock(return_value=ValidationResult(is_valid=True, status="valid"))
    monkeypatch.setattr(ValidationService, "validate", mock)

    response = client.post(
        f"{BASE}/validate/hpo?hpo_term=HP:0001250", headers=_auth(admin_token)
    )

    assert response.status_code == 200
    mock.assert_awaited_once_with("hpo", "HP:0001250", skip_cache=False)


def test_validate_batch_returns_mapping(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
    valid_result: ValidationResult,
) -> None:
    mock = AsyncMock(
        return_value={
            "BRCA1": valid_result,
            "NOPE": ValidationResult(is_valid=False, status="not_found"),
        }
    )
    monkeypatch.setattr(ValidationService, "validate_batch", mock)

    response = client.post(
        f"{BASE}/validate/batch",
        json={"validator_name": "hgnc", "values": ["BRCA1", "NOPE"]},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["BRCA1"]["is_valid"] is True
    assert body["NOPE"]["status"] == "not_found"
    mock.assert_awaited_once_with("hgnc", ["BRCA1", "NOPE"])


def test_validate_batch_rejects_missing_fields(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        f"{BASE}/validate/batch",
        json={"validator_name": "hgnc"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 422


def test_hgnc_search_delegates_to_validator_and_closes_client(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
) -> None:
    gene = HGNCGeneSearchResult(hgnc_id="HGNC:1100", symbol="BRCA1")
    search = AsyncMock(
        return_value=HGNCSearchResponse(query="BRCA", total_results=1, results=[gene])
    )
    close = AsyncMock()
    monkeypatch.setattr(HGNCValidator, "search", search)
    monkeypatch.setattr(HGNCValidator, "close", close)

    response = client.post(
        f"{BASE}/hgnc/search",
        json={"query": "BRCA", "limit": 5},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["symbol"] == "BRCA1"
    search.assert_awaited_once_with("BRCA", 5)
    close.assert_awaited_once()


def test_hgnc_fetch_returns_single_result_or_empty(
    client: TestClient,
    admin_token: str,
    monkeypatch: MonkeyPatch,
) -> None:
    gene = HGNCGeneSearchResult(hgnc_id="HGNC:1100", symbol="BRCA1")
    monkeypatch.setattr(HGNCValidator, "fetch_gene_by_id", AsyncMock(return_value=gene))
    monkeypatch.setattr(HGNCValidator, "close", AsyncMock())

    found = client.get(f"{BASE}/hgnc/fetch/HGNC:1100", headers=_auth(admin_token))
    assert found.json()["total_results"] == 1

    monkeypatch.setattr(HGNCValidator, "fetch_gene_by_id", AsyncMock(return_value=None))
    missing = client.get(f"{BASE}/hgnc/fetch/HGNC:0", headers=_auth(admin_token))
    assert missing.json() == {"query": "HGNC:0", "total_results": 0, "results": []}


def test_cache_statistics_endpoint_returns_counts(
    client: TestClient, admin_token: str
) -> None:
    response = client.get(f"{BASE}/cache/statistics", headers=_auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_entries"] == 0
    assert body["expired_entries"] == 0
    assert body["hgnc"] == 0
