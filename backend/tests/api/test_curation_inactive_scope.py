"""#483: curations of an inactive scope are read-only, for platform admins too: a clear 409
instead of the 500 the RLS-blocked UPDATE caused, and no Edit/Delete offered."""

from collections.abc import Iterator
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, CurationStatus, Review, UserNew, WorkflowStage
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_scope,
    make_user,
    make_workflow_pair,
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


def test_create_in_inactive_scope_is_409(
    client: TestClient, db_session: Session, setup: tuple[CurationNew, dict[str, str]]
) -> None:
    curation, headers = setup
    body = {
        "gene_id": str(make_gene(db_session).id),
        "scope_id": str(curation.scope_id),
        "workflow_pair_id": str(make_workflow_pair(db_session).id),
        "evidence_data": {},
    }
    r = client.post("/api/v1/curations/", headers=headers, json=body)
    assert r.status_code == 409, r.text


EVIDENCE = {"evidence_category": "case_level", "evidence_type": "genetic"}


@pytest.mark.parametrize(
    ("method", "item", "body"),
    [
        ("post", False, {**EVIDENCE, "evidence_data": {}}),
        ("put", True, {"evidence_data": {}}),
        ("delete", True, None),
    ],
)
def test_evidence_writes_in_inactive_scope_are_409(
    client: TestClient,
    setup: tuple[CurationNew, dict[str, str]],
    method: str,
    item: bool,
    body: dict[str, object] | None,
) -> None:
    curation, headers = setup
    path = f"/api/v1/curations/{curation.id}/evidence" + (f"/{uuid4()}" if item else "")
    r = client.request(method, path, headers=headers, json=body)
    assert r.status_code == 409, r.text
    assert "inactive" in r.json()["detail"]


def test_workflow_writes_in_inactive_scope_are_409(
    client: TestClient, db_session: Session, setup: tuple[CurationNew, dict[str, str]]
) -> None:
    curation, headers = setup
    r = client.post(
        f"/api/v1/workflow/curation/{curation.id}/transition",
        headers=headers,
        json={"target_stage": "review"},
    )
    assert r.status_code == 409, r.text

    reviewer = make_user(db_session)
    review = Review(
        curation_id=curation.id, reviewer_id=reviewer.id, assigned_by=reviewer.id
    )
    db_session.add(review)
    db_session.commit()
    r = client.post(
        f"/api/v1/workflow/reviews/{review.id}/submit",
        headers=auth_headers(reviewer),
        json={"decision": "approve"},
    )
    assert r.status_code == 409, r.text


def test_scope_permissions_refuse_editing_in_inactive_scope(
    db_session: Session, setup: tuple[CurationNew, dict[str, str]]
) -> None:
    from app.services.scope_permissions import ScopePermissionService

    curation, _ = setup
    admin = db_session.get(UserNew, curation.created_by)
    assert admin is not None
    assert (
        ScopePermissionService.can_edit_curation(db_session, admin, curation) is False
    )
