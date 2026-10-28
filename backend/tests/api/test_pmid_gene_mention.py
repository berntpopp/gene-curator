"""validate_pmids flags off-topic PMIDs (gene_symbol) and says not_found vs retry."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas.validation import (
    PMIDValidationResponse,
    PMIDValidationResult,
    PublicationData,
)
from app.services.publication_search import mentions
from app.services.publication_service import PublicationService
from tests.api.test_publications_api import fake_db  # noqa: F401 (fixture)

pytestmark = pytest.mark.unit


def _pub(title: str, abstract: str | None) -> PublicationData:
    return PublicationData(pmid="1", title=title, journal="J", abstract=abstract)


def test_mentions_matches_whole_names_and_needs_an_abstract_to_say_no() -> None:
    names = {"PKD1", "PBP"}
    assert mentions(names, _pub("Variants in pkd1", None)) is True
    assert mentions(names, _pub("T", "Loss of PBP causes cysts")) is True
    assert mentions(names, _pub("T", "PKD10 and PKD2 only")) is False
    assert mentions(names, _pub("Unrelated", None)) is None
    assert mentions(names, None) is None


def test_status_separates_not_found_from_upstream_unavailable() -> None:
    def r(**kw: Any) -> str:
        return PMIDValidationResult(pmid="1", **kw).status

    assert r(is_valid=True) == "found"
    assert r(is_valid=False, error="Publication not found: 1") == "not_found"
    assert (
        r(is_valid=False, error="API timeout; retry lookup") == "upstream_unavailable"
    )


def test_validate_pmids_with_gene_symbol_flags_off_topic(
    client: TestClient,
    admin_token: str,
    fake_db: MagicMock,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = MagicMock(previous_symbols=["PBP"], alias_symbols=None)
    fake_db.execute.return_value = MagicMock(first=MagicMock(return_value=row))
    payload = PMIDValidationResponse(
        total_requested=3,
        valid_count=2,
        invalid_count=1,
        results=[
            PMIDValidationResult(pmid="1", is_valid=True, publication=_pub("PBP", "x")),
            PMIDValidationResult(
                pmid="2", is_valid=True, publication=_pub("T", "BRCA1")
            ),
            PMIDValidationResult(pmid="3", is_valid=False, error="API timeout"),
        ],
    )
    monkeypatch.setattr(
        PublicationService, "validate_pmids", AsyncMock(return_value=payload)
    )
    r = client.post(
        "/api/v1/publications/validate",
        json={"pmids": ["1", "2", "3"], "gene_symbol": "pkd1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    assert [(x.get("mentions_gene"), x["status"]) for x in r.json()["results"]] == [
        (True, "found"),
        (False, "found"),
        (None, "upstream_unavailable"),
    ]


def test_a_blank_gene_symbol_is_ignored(
    client: TestClient,
    admin_token: str,
    fake_db: MagicMock,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = PMIDValidationResponse(
        total_requested=1,
        valid_count=1,
        invalid_count=0,
        results=[
            PMIDValidationResult(pmid="1", is_valid=True, publication=_pub("T", "x"))
        ],
    )
    monkeypatch.setattr(
        PublicationService, "validate_pmids", AsyncMock(return_value=payload)
    )
    r = client.post(
        "/api/v1/publications/validate",
        json={"pmids": ["1"], "gene_symbol": "   "},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["results"][0].get("mentions_gene") is None
    fake_db.execute.assert_not_called()  # no gene lookup for a blank symbol
