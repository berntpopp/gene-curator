"""Routing a precuration or curation to a peer reviewer (MCP study round 1, findings 1 and 4)."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.crud import workflow_engine as engine_module
from app.models.models import (
    CurationStatus,
    NotificationNew,
    PrecurationNew,
    Scope,
    UserNew,
    WorkflowStage as S,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_precuration,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/workflow"


@pytest.fixture
def submitted_precuration(
    db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> PrecurationNew:
    p = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    p.status = CurationStatus.SUBMITTED
    db_session.commit()
    return p


def _assign(
    client: TestClient, kind: str, item_id: UUID, who: UserNew, by: UserNew
) -> Response:
    return client.post(
        f"{BASE}/{kind}/{item_id}/assign-reviewer",
        json={"reviewer_id": str(who.id)},
        headers=auth_headers(by),
    )


def test_curator_routes_submitted_precuration_to_reviewer(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    submitted_precuration: PrecurationNew,
) -> None:
    r = _assign(client, "precuration", submitted_precuration.id, reviewer, curator)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["item_type"] == "precuration"
    assert body["reviewer_id"] == str(reviewer.id)
    assert body["review_id"] is None
    note = db_session.scalars(
        select(NotificationNew).where(NotificationNew.user_id == reviewer.id)
    ).one()
    assert str(submitted_precuration.id) in note.link

    # routing again while unread does not duplicate; once read, it notifies again
    _assign(client, "precuration", submitted_precuration.id, reviewer, curator)
    db_session.expire_all()
    note = db_session.scalars(
        select(NotificationNew).where(NotificationNew.user_id == reviewer.id)
    ).one()
    note.is_read = True
    db_session.commit()
    _assign(client, "precuration", submitted_precuration.id, reviewer, curator)
    notes = db_session.scalars(
        select(NotificationNew).where(NotificationNew.user_id == reviewer.id)
    ).all()
    assert len(notes) == 2


def test_precuration_routing_refusals_name_item_status_and_approvers(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    viewer: UserNew,
    scope_with_admin: Scope,
    submitted_precuration: PrecurationNew,
) -> None:
    draft = make_precuration(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    r = _assign(client, "precuration", draft.id, reviewer, curator)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert str(draft.id) in detail and "draft" in detail and "reviewer" in detail

    # D1: never the author
    r = _assign(client, "precuration", submitted_precuration.id, curator, curator)
    assert r.status_code == 400
    assert "4-eyes" in r.json()["detail"]

    r = _assign(client, "precuration", submitted_precuration.id, viewer, curator)
    assert r.status_code == 400
    assert "accepted reviewer or admin" in r.json()["detail"]

    # a viewer may not route work
    r = _assign(client, "precuration", submitted_precuration.id, reviewer, viewer)
    assert r.status_code == 403


def test_unknown_item_type_is_400(
    client: TestClient, curator: UserNew, reviewer: UserNew
) -> None:
    r = _assign(client, "active", reviewer.id, reviewer, curator)
    assert r.status_code == 400


def test_curation_not_in_review_refusal_names_item_and_status(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    c = make_curation(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=S.CURATION,
        status=CurationStatus.DRAFT,
    )
    r = _assign(client, "curation", c.id, reviewer, curator)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert str(c.id) in detail and "draft" in detail and "reviewer" in detail


def test_unknown_curation_is_400_naming_it(
    client: TestClient, curator: UserNew, reviewer: UserNew
) -> None:
    missing = uuid4()
    r = _assign(client, "curation", missing, reviewer, curator)
    assert r.status_code == 400
    assert f"Curation {missing} not found" in r.json()["detail"]
    r = _assign(client, "precuration", missing, reviewer, curator)
    assert r.status_code == 404
    assert f"Precuration {missing} not found" in r.json()["detail"]


@pytest.mark.parametrize(("pgcode", "expected"), [("42501", 403), ("23505", None)])
def test_rls_denied_insert_is_403_other_db_errors_propagate(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
    monkeypatch: pytest.MonkeyPatch,
    pgcode: str,
    expected: int | None,
) -> None:
    c = make_curation(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=S.REVIEW,
    )
    orig = type("Orig", (Exception,), {"pgcode": pgcode})()

    def deny(**_: object) -> None:
        raise DBAPIError("INSERT INTO notifications", None, orig)

    monkeypatch.setattr(engine_module, "NotificationNew", deny)
    if expected is None:
        with pytest.raises(DBAPIError):
            _assign(client, "curation", c.id, reviewer, curator)
    else:
        assert _assign(client, "curation", c.id, reviewer, curator).status_code == 403
