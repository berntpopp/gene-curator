"""#483: curations of an inactive scope are read-only, for platform admins too: a clear 409
instead of the 500 the RLS-blocked UPDATE caused, and no Edit/Delete offered."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, CurationStatus, WorkflowStage
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite() -> Iterator[None]:
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


@pytest.fixture
def setup(db_session: Session) -> tuple[CurationNew, dict[str, str]]:
    scope = make_scope(db_session)
    admin = make_user(db_session, role="admin")
    curation = make_curation(
        db_session,
        scope=scope,
        gene=make_gene(db_session),
        creator=admin,
        stage=WorkflowStage.CURATION,
        status=CurationStatus.DRAFT,
    )
    scope.is_active = False
    db_session.commit()
    return curation, auth_headers(admin)


def test_delete_in_inactive_scope_is_409(
    client: TestClient, setup: tuple[CurationNew, dict[str, str]]
) -> None:
    curation, headers = setup
    r = client.delete(f"/api/v1/curations/{curation.id}", headers=headers)
    assert r.status_code == 409, r.text
    assert "inactive" in r.json()["detail"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("put", "", {"evidence_data": {}, "lock_version": 0}),
        ("patch", "/draft", {"evidence_data": {}, "lock_version": 0}),
        ("post", "/submit", {"lock_version": 0}),
    ],
)
def test_writes_in_inactive_scope_are_409(
    client: TestClient,
    setup: tuple[CurationNew, dict[str, str]],
    method: str,
    path: str,
    body: dict[str, object],
) -> None:
    curation, headers = setup
    r = client.request(
        method, f"/api/v1/curations/{curation.id}{path}", headers=headers, json=body
    )
    assert r.status_code == 409, r.text


def test_detail_offers_no_edit_or_delete_in_inactive_scope(
    client: TestClient, setup: tuple[CurationNew, dict[str, str]]
) -> None:
    curation, headers = setup
    body = client.get(f"/api/v1/curations/{curation.id}", headers=headers).json()
    assert body["can_edit"] is False
    assert body["can_delete"] is False
