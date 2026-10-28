"""validate_pmids says per PMID whether PubMed lacks it or the lookup should be retried."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.validation import (
    PMIDValidationResponse,
    PMIDValidationResult,
    PublicationData,
)
from app.services.publication_service import PublicationService
from tests.api.test_publications_api import fake_db  # noqa: F401 (fixture)

pytestmark = pytest.mark.unit


def test_status_separates_not_found_from_upstream_unavailable() -> None:
    def r(**kw: Any) -> str:
        return PMIDValidationResult(pmid="1", **kw).status

    assert r(is_valid=True) == "found"
    assert r(is_valid=False, error="Publication not found: 1") == "not_found"
    assert (
        r(is_valid=False, error="API timeout; retry lookup") == "upstream_unavailable"
    )


def test_validate_pmids_returns_the_status(
    client: TestClient,
    admin_token: str,
    fake_db: MagicMock,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pub = PublicationData(pmid="1", title="T", journal="J")
    payload = PMIDValidationResponse(
        total_requested=2,
        valid_count=1,
        invalid_count=1,
        results=[
            PMIDValidationResult(pmid="1", is_valid=True, publication=pub),
            PMIDValidationResult(pmid="2", is_valid=False, error="API timeout"),
        ],
    )
    monkeypatch.setattr(
        PublicationService, "validate_pmids", AsyncMock(return_value=payload)
    )
    r = client.post(
        "/api/v1/publications/validate",
        json={"pmids": ["1", "2"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    assert [x["status"] for x in r.json()["results"]] == [
        "found",
        "upstream_unavailable",
    ]
