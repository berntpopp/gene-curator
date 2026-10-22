"""GET /curations/{id} tells a reviewer whether they can still approve (#430).

With `reviewers_required: 2` a reviewer who approved sees `has_approved` and the remaining count
and keeps `can_review` (request changes, replies); a second approval by the same reviewer is not
counted, and a new review round starts again from the full count.
"""

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, Scope, UserNew
from app.models.methodology import MethodologyVersion
from app.models.models import CurationSchema
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_user,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def curation(db_session: Session, curator: UserNew, scope_with_admin: Scope) -> Any:
    """In-review curation pinned to a methodology version requiring two reviewers."""
    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    schema = CurationSchema(
        id=uuid4(),
        name=f"wf-{uuid4().hex[:6]}",
        version="1",
        schema_type="curation",
        field_definitions={},
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex * 2,
    )
    db_session.add(schema)
    db_session.flush()
    version = MethodologyVersion(
        schema_id=schema.id,
        version=1,
        snapshot={"workflow_states": {"review": {"reviewers_required": 2}}},
    )
    db_session.add(version)
    db_session.flush()
    cur.methodology_version_id = version.id
    db_session.commit()
    return cur


@pytest.fixture
def second(db_session: Session, scope_with_admin: Scope) -> UserNew:
    user = make_user(db_session, name="Second reviewer")
    make_member(db_session, scope_with_admin, user, "reviewer")
    return user


def _view(client: TestClient, cur: CurationNew, user: UserNew) -> tuple[Any, ...]:
    r = client.get(f"/api/v1/curations/{cur.id}", headers=auth_headers(user))
    assert r.status_code == 200, r.text
    body = r.json()
    return body["can_review"], body["has_approved"], body["approvals_remaining"]


def _move(client: TestClient, cur: CurationNew, user: UserNew, stage: str) -> str:
    r = client.post(
        f"/api/v1/workflow/curation/{cur.id}/transition",
        json={"target_stage": stage, "notes": "x"},
        headers=auth_headers(user),
    )
    assert r.status_code == 200, r.text
    return str(r.json()["to_stage"])


def test_approver_sees_remaining_count_and_cannot_approve_twice(
    client: TestClient,
    curation: CurationNew,
    reviewer: UserNew,
    second: UserNew,
) -> None:
    assert _view(client, curation, reviewer) == (True, False, 2)
    assert _move(client, curation, reviewer, "active") == "review"
    assert _view(client, curation, reviewer) == (True, True, 1)
    # a second approval by the same reviewer does not count
    assert _move(client, curation, reviewer, "active") == "review"
    assert _view(client, curation, reviewer) == (True, True, 1)
    assert _view(client, curation, second) == (True, False, 1)
    assert _move(client, curation, second, "active") == "active"
    assert _view(client, curation, reviewer) == (False, False, None)


def test_new_round_ignores_earlier_approvals(
    client: TestClient,
    curation: CurationNew,
    curator: UserNew,
    reviewer: UserNew,
    second: UserNew,
) -> None:
    _move(client, curation, reviewer, "active")
    assert _move(client, curation, second, "curation") == "curation"
    assert _view(client, curation, reviewer) == (False, False, None)
    assert _move(client, curation, curator, "review") == "review"
    assert _view(client, curation, reviewer) == (True, False, 2)


def test_author_and_non_member_admin_cannot_review(
    client: TestClient,
    db_session: Session,
    curation: CurationNew,
    curator: UserNew,
    app_admin: UserNew,
    scope_with_admin: Scope,
) -> None:
    assert _view(client, curation, curator) == (False, False, 2)
    assert _view(client, curation, app_admin) == (False, False, 2)
    author = make_user(db_session, role="admin", name="Admin author")
    make_member(db_session, scope_with_admin, author, "admin")
    own = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=author
    )
    assert _view(client, own, author) == (False, False, 1)


def test_approval_recorded_by_review_submit_can_still_activate(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    second: UserNew,
    scope_with_admin: Scope,
) -> None:
    """An approval via /reviews/{id}/submit waits for the other open review; Approve activates."""
    cur = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    review_ids = []
    for user in (reviewer, second):
        r = client.post(
            f"/api/v1/workflow/curation/{cur.id}/assign-reviewer",
            json={"reviewer_id": str(user.id)},
            headers=auth_headers(curator),
        )
        assert r.status_code == 200, r.text
        review_ids.append(r.json()["review_id"])
    r = client.post(
        f"/api/v1/workflow/reviews/{review_ids[0]}/submit",
        json={"decision": "approve", "comments": "ok"},
        headers=auth_headers(reviewer),
    )
    assert r.json()["auto_transitioned"] is False, r.text
    assert _view(client, cur, reviewer) == (True, True, 0)
    assert _move(client, cur, reviewer, "active") == "active"
