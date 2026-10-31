"""D1 for edits by someone other than the author (#609 delta review): a scope admin may edit
a member's precuration or curation (#284), but then may not approve it; other curators of
the scope may not edit it at all."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationStatus, WorkflowStage
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_precuration,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite() -> Iterator[None]:
    with (
        patch("app.api.v1.endpoints.precurations.set_rls_context"),
        patch("app.api.v1.endpoints.curations.set_rls_context"),
    ):
        yield


@pytest.fixture
def team(db_session: Session) -> dict:
    scope = make_scope(db_session)
    users = {
        r: make_user(db_session) for r in ("author", "sadmin", "other", "reviewer")
    }
    make_member(db_session, scope, users["author"], "curator")
    make_member(db_session, scope, users["sadmin"], "admin")
    make_member(db_session, scope, users["other"], "curator")
    make_member(db_session, scope, users["reviewer"], "reviewer")
    return {"scope": scope, **users}


@pytest.mark.parametrize("method", ["put", "patch_draft"])
def test_admin_edits_a_precuration_and_then_may_not_approve_it(
    client: TestClient, db_session: Session, team: dict, method: str
) -> None:
    pre = make_precuration(
        db_session,
        scope=team["scope"],
        gene=make_gene(db_session),
        creator=team["author"],
    )
    url = f"/api/v1/precurations/{pre.id}"
    path, verb = (url, "put") if method == "put" else (f"{url}/draft", "patch")
    body = {"evidence_data": {"note": "x"}, "lock_version": pre.lock_version}
    refused = client.request(verb, path, json=body, headers=auth_headers(team["other"]))
    assert refused.status_code == 403, refused.text
    r = client.request(verb, path, json=body, headers=auth_headers(team["sadmin"]))
    assert r.status_code == 200, r.text
    pre.status, pre.workflow_stage = CurationStatus.SUBMITTED, WorkflowStage.REVIEW
    db_session.commit()
    for action in ("approve", "reject"):
        r = client.post(
            f"{url}/{action}",
            json={"reason": "no"} if action == "reject" else None,
            headers=auth_headers(team["sadmin"]),
        )
        assert r.status_code == 403, (action, r.text)
        assert "4-eyes" in r.json()["detail"]
    # a third member, neither author nor editor, still approves it
    r = client.post(f"{url}/approve", headers=auth_headers(team["reviewer"]))
    assert r.status_code == 200, r.text
    assert r.json()["approved"] is True


def test_curation_put_needs_the_author_or_a_scope_admin(
    client: TestClient, db_session: Session, team: dict
) -> None:
    curation = make_curation(
        db_session,
        scope=team["scope"],
        gene=make_gene(db_session),
        creator=team["author"],
        stage=WorkflowStage.CURATION,
        status=CurationStatus.DRAFT,
    )
    url = f"/api/v1/curations/{curation.id}"
    body = {"evidence_data": {}, "lock_version": curation.lock_version}
    r = client.put(url, json=body, headers=auth_headers(team["other"]))
    assert r.status_code == 403, r.text
    r = client.put(url, json=body, headers=auth_headers(team["author"]))
    assert r.status_code == 200, r.text
    body["lock_version"] = r.json()["lock_version"]
    r = client.put(url, json=body, headers=auth_headers(team["sadmin"]))
    assert r.status_code == 200, r.text


def test_admin_edits_a_curation_and_a_third_reviewer_approves_it(
    client: TestClient, db_session: Session, team: dict
) -> None:
    curation = make_curation(
        db_session,
        scope=team["scope"],
        gene=make_gene(db_session),
        creator=team["author"],
        stage=WorkflowStage.CURATION,
        status=CurationStatus.DRAFT,
    )
    body = {"evidence_data": {"note": "x"}, "lock_version": curation.lock_version}
    r = client.patch(
        f"/api/v1/curations/{curation.id}/draft",
        json=body,
        headers=auth_headers(team["sadmin"]),
    )
    assert r.status_code == 200, r.text
    curation.status, curation.workflow_stage = (
        CurationStatus.SUBMITTED,
        WorkflowStage.REVIEW,
    )
    db_session.commit()
    url = f"/api/v1/workflow/curation/{curation.id}"
    move = {"target_stage": "active", "notes": "ok"}
    r = client.post(
        f"{url}/transition", json=move, headers=auth_headers(team["sadmin"])
    )
    assert r.status_code == 403, r.text
    r = client.post(
        f"{url}/transition", json=move, headers=auth_headers(team["reviewer"])
    )
    assert r.status_code == 200, r.text
    db_session.refresh(curation)
    assert curation.status == CurationStatus.ACTIVE
