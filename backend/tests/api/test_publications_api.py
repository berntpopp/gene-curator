"""API tests for /publications endpoints.

The async DB dependency is replaced with a mock session (aiosqlite is not
installed), and PublicationService is patched at the class level so no request
reaches Europe PMC.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.deps import get_async_db
from app.main import app
from app.models.models import Publication
from app.schemas.validation import (
    PMIDValidationResponse,
    PMIDValidationResult,
    PublicationData,
)
from app.services.publication_service import PublicationService

pytestmark = pytest.mark.unit

BASE = "/api/v1/publications"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _publication_data(pmid: str = "31558469") -> PublicationData:
    return PublicationData(
        pmid=pmid, title="A paper", authors=["Smith J"], journal="Nat Genet"
    )


@pytest.fixture
def fake_db() -> Generator[MagicMock, None, None]:
    session = MagicMock()
    session.execute = AsyncMock()
    app.dependency_overrides[get_async_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_async_db, None)


@pytest.fixture(autouse=True)
def publication_close(monkeypatch: MonkeyPatch) -> AsyncMock:
    close = AsyncMock()
    monkeypatch.setattr(PublicationService, "close", close)
    return close


def test_publication_routes_require_authentication(
    client: TestClient, fake_db: MagicMock
) -> None:
    assert client.get(f"{BASE}/31558469").status_code in (401, 403)
    assert client.post(f"{BASE}/validate", json={"pmids": ["1"]}).status_code in (
        401,
        403,
    )


def test_get_publication_returns_data(
    client: TestClient,
    admin_token: str,
    fake_db: MagicMock,
    monkeypatch: MonkeyPatch,
    publication_close: AsyncMock,
) -> None:
    get = AsyncMock(return_value=_publication_data())
    monkeypatch.setattr(PublicationService, "get_publication", get)

    response = client.get(f"{BASE}/31558469", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json()["title"] == "A paper"
    get.assert_awaited_once_with("31558469")
    publication_close.assert_awaited_once()


def test_get_publication_404_when_service_returns_none(
    client: TestClient,
    admin_token: str,
    fake_db: MagicMock,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        PublicationService, "get_publication", AsyncMock(return_value=None)
    )

    response = client.get(f"{BASE}/999", headers=_auth(admin_token))

    assert response.status_code == 404
    assert response.json()["detail"] == "Publication not found: 999"


def test_get_publication_rejects_non_numeric_pmid(
    client: TestClient, admin_token: str, fake_db: MagicMock
) -> None:
    response = client.get(f"{BASE}/PMID1", headers=_auth(admin_token))
    assert response.status_code == 422


def test_validate_pmids_returns_service_response(
    client: TestClient,
    admin_token: str,
    fake_db: MagicMock,
    monkeypatch: MonkeyPatch,
) -> None:
    payload = PMIDValidationResponse(
        total_requested=2,
        valid_count=1,
        invalid_count=1,
        results=[
            PMIDValidationResult(
                pmid="31558469", is_valid=True, publication=_publication_data()
            ),
            PMIDValidationResult(pmid="1", is_valid=False, error="not found"),
        ],
    )
    validate = AsyncMock(return_value=payload)
    monkeypatch.setattr(PublicationService, "validate_pmids", validate)

    response = client.post(
        f"{BASE}/validate",
        json={"pmids": ["31558469", "1"]},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["valid_count"] == 1
    assert body["results"][1]["error"] == "not found"
    assert validate.await_args is not None
    assert validate.await_args.args[0] == ["31558469", "1"]


def test_validate_pmids_enforces_request_bounds(
    client: TestClient, admin_token: str, fake_db: MagicMock
) -> None:
    empty = client.post(
        f"{BASE}/validate", json={"pmids": []}, headers=_auth(admin_token)
    )
    assert empty.status_code == 422

    too_many = client.post(
        f"{BASE}/validate",
        json={"pmids": [str(i) for i in range(51)]},
        headers=_auth(admin_token),
    )
    assert too_many.status_code == 422


def _row(pmid: str, title: str) -> Publication:
    return Publication(
        pmid=pmid,
        title=title,
        authors=None,
        author_string="Smith J",
        journal="Nat Genet",
        pub_year=2019,
        pub_date="2019-09-26",
        is_open_access=True,
        cited_by_count=3,
    )


def test_list_publications_maps_rows(
    client: TestClient, admin_token: str, fake_db: MagicMock
) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _row("1", "First"),
        _row("2", "Second"),
    ]
    fake_db.execute.return_value = result

    response = client.get(f"{BASE}?limit=2&search=smith", headers=_auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert [p["pmid"] for p in body] == ["1", "2"]
    assert body[0]["authors"] == []  # None authors normalised to empty list
    assert body[0]["year"] == 2019
    assert body[0]["publication_date"] == "2019-09-26"
    assert fake_db.execute.await_count == 1


def test_list_publications_rejects_out_of_range_paging(
    client: TestClient, admin_token: str, fake_db: MagicMock
) -> None:
    assert client.get(f"{BASE}?limit=0", headers=_auth(admin_token)).status_code == 422
    assert client.get(f"{BASE}?skip=-1", headers=_auth(admin_token)).status_code == 422


def test_publication_stats_counts_total_and_open_access(
    client: TestClient, admin_token: str, fake_db: MagicMock
) -> None:
    total = MagicMock()
    total.scalar.return_value = 10
    open_access = MagicMock()
    open_access.scalar.return_value = 4
    fake_db.execute.side_effect = [total, open_access]

    response = client.get(f"{BASE}/stats/count", headers=_auth(admin_token))

    assert response.status_code == 200
    assert response.json() == {"total_cached": 10, "open_access_count": 4}
