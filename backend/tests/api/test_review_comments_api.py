"""Per-item review comments and the evidence diff endpoints (#279).

SQLite has no RLS or audit triggers, so these cover the application-level rules (which mirror
the policies) and write the audit snapshot by hand; backend/tests/postgres covers the real
policies and real transitions.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.models import (
    AuditLogNew,
    CurationNew,
    Review,
    Scope,
    ScopeMembership,
    UserNew,
)

pytestmark = pytest.mark.unit


def _auth(user: UserNew) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(data={'sub': str(user.id)})}"
    }


def _member(db: Session, scope: Scope, role: str, *, accepted: bool = True) -> UserNew:
    user = UserNew(
        id=uuid4(),
        email=f"{role}-{uuid4().hex[:6]}@test.org",
        hashed_password=get_password_hash("x"),
        name=role,
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.add(
        ScopeMembership(
            scope_id=scope.id,
            user_id=user.id,
            role=role,
            accepted_at=datetime.now(UTC) if accepted else None,
        )
    )
    db.commit()
    return user


@pytest.fixture
def reviewer(db_session: Session, test_scope: Scope) -> UserNew:
    return _member(db_session, test_scope, "reviewer")


def _url(curation: CurationNew, tail: str = "") -> str:
    return f"/api/v1/curations/{curation.id}/review-comments{tail}"


def _comment(client: TestClient, user: UserNew, curation: CurationNew, **over) -> dict:
    body = {"item_path": "genetic.case_level[a].score", "body": "Source?", **over}
    response = client.post(_url(curation), json=body, headers=_auth(user))
    assert response.status_code == 201, response.text
    return response.json()


def test_reviewer_comments_and_members_read_it(
    client: TestClient,
    reviewer: UserNew,
    test_user_viewer: UserNew,
    test_curation: CurationNew,
) -> None:
    made = _comment(client, reviewer, test_curation)
    assert made["status"] == "open"
    assert made["author_id"] == str(reviewer.id)
    listed = client.get(_url(test_curation), headers=_auth(test_user_viewer))
    assert [c["id"] for c in listed.json()] == [made["id"]]


def test_the_curations_curator_may_reply_but_other_curators_and_viewers_may_not(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_user_viewer: UserNew,
    test_curation: CurationNew,
) -> None:
    _comment(client, test_user_curator, test_curation, body="Added the source")
    other = _member(db_session, test_scope, "curator")
    for user in (other, test_user_viewer):
        response = client.post(
            _url(test_curation),
            json={"item_path": "a", "body": "hi"},
            headers=_auth(user),
        )
        assert response.status_code == 403


def test_pending_invitation_and_outsiders_see_nothing_and_cannot_write(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_curation: CurationNew,
) -> None:
    pending = _member(db_session, test_scope, "reviewer", accepted=False)
    outsider = UserNew(
        id=uuid4(),
        email="out@test.org",
        hashed_password=get_password_hash("x"),
        name="out",
        role="user",
        is_active=True,
    )
    db_session.add(outsider)
    db_session.commit()
    for user in (pending, outsider):
        assert client.get(_url(test_curation), headers=_auth(user)).status_code == 403
        assert (
            client.post(
                _url(test_curation),
                json={"item_path": "a", "body": "x"},
                headers=_auth(user),
            ).status_code
            == 403
        )


def test_requires_authentication(
    client: TestClient, test_curation: CurationNew
) -> None:
    assert client.get(_url(test_curation)).status_code in (401, 403)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"item_path": "", "body": "x"},
        {"item_path": "a", "body": ""},
        {"item_path": "a", "body": "x" * 5001},
        {"item_path": "a" * 501, "body": "x"},
        {"item_path": "a\x00b", "body": "x"},
    ],
)
def test_rejects_malformed_comments(
    client: TestClient, reviewer: UserNew, test_curation: CurationNew, payload: dict
) -> None:
    response = client.post(_url(test_curation), json=payload, headers=_auth(reviewer))
    assert response.status_code == 422


def test_unknown_curation_is_404(client: TestClient, reviewer: UserNew) -> None:
    response = client.get(
        f"/api/v1/curations/{uuid4()}/review-comments", headers=_auth(reviewer)
    )
    assert response.status_code == 404


def test_only_the_author_edits_the_text(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    reviewer: UserNew,
    test_curation: CurationNew,
) -> None:
    made = _comment(client, reviewer, test_curation)
    peer = _member(db_session, test_scope, "reviewer")
    url = _url(test_curation, f"/{made['id']}")
    assert (
        client.patch(url, json={"body": "hijack"}, headers=_auth(peer)).status_code
        == 403
    )
    edited = client.patch(
        url, json={"body": "Better question"}, headers=_auth(reviewer)
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "Better question"


def test_curator_or_reviewer_resolves_but_a_viewer_cannot(
    client: TestClient,
    reviewer: UserNew,
    test_user_curator: UserNew,
    test_user_viewer: UserNew,
    test_curation: CurationNew,
) -> None:
    made = _comment(client, reviewer, test_curation)
    url = _url(test_curation, f"/{made['id']}")
    resolve = {"status": "resolved"}
    assert (
        client.patch(url, json=resolve, headers=_auth(test_user_viewer)).status_code
        == 403
    )
    done = client.patch(url, json=resolve, headers=_auth(test_user_curator))
    assert done.status_code == 200
    assert done.json()["status"] == "resolved"
    reopened = client.patch(url, json={"status": "open"}, headers=_auth(reviewer))
    assert reopened.json()["status"] == "open"
    # a resolver who is not the author cannot smuggle a text edit into the same request
    both = {"status": "resolved", "body": "rewritten"}
    assert (
        client.patch(url, json=both, headers=_auth(test_user_curator)).status_code
        == 403
    )


def test_patch_needs_a_change_and_a_valid_status(
    client: TestClient, reviewer: UserNew, test_curation: CurationNew
) -> None:
    made = _comment(client, reviewer, test_curation)
    url = _url(test_curation, f"/{made['id']}")
    assert client.patch(url, json={}, headers=_auth(reviewer)).status_code == 422
    assert (
        client.patch(
            url, json={"status": "deleted"}, headers=_auth(reviewer)
        ).status_code
        == 422
    )
    assert (
        client.patch(
            _url(test_curation, f"/{uuid4()}"),
            json={"body": "x"},
            headers=_auth(reviewer),
        ).status_code
        == 404
    )


def test_comment_cannot_be_read_through_another_curation(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    test_curation: CurationNew,
) -> None:
    made = _comment(client, reviewer, test_curation)
    twin = CurationNew(
        id=uuid4(),
        scope_id=test_curation.scope_id,
        gene_id=test_curation.gene_id,
        workflow_pair_id=test_curation.workflow_pair_id,
        workflow_stage="curation",
        evidence_data={},
    )
    db_session.add(twin)
    db_session.commit()
    response = client.patch(
        _url(twin, f"/{made['id']}"),
        json={"status": "resolved"},
        headers=_auth(reviewer),
    )
    assert response.status_code == 404


def _snapshot(
    db: Session,
    curation: CurationNew,
    data: dict,
    status: str,
    when: datetime,
    previous: str = "draft",
) -> None:
    db.add(
        AuditLogNew(
            id=db.query(AuditLogNew).count()
            + 1,  # SQLite does not autoincrement BigInteger
            entity_type="curations",
            entity_id=curation.id,
            scope_id=curation.scope_id,
            operation="UPDATE",
            changes={"evidence_data": data},
            previous_status=previous,
            new_status=status,
            timestamp=when,
        )
    )
    db.commit()


def _decision(
    db: Session, curation: CurationNew, reviewer: UserNew, when: datetime
) -> None:
    db.add(
        Review(
            curation_id=curation.id,
            reviewer_id=reviewer.id,
            status="needs_revision",
            reviewed_at=when,
        )
    )
    db.commit()


def _diff(client: TestClient, user: UserNew, curation: CurationNew) -> dict:
    response = client.get(f"/api/v1/curations/{curation.id}/diff", headers=_auth(user))
    assert response.status_code == 200, response.text
    return response.json()


def test_resubmission_diff_shows_only_what_changed_since_the_last_review(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    test_curation: CurationNew,
) -> None:
    """submit -> review decision -> curator edits one item -> resubmit."""
    now = datetime.now(UTC)
    v1 = {"cases": [{"id": "a", "score": 1}, {"id": "b", "score": 2}], "summary": "s"}
    v2 = {"cases": [{"id": "a", "score": 1}, {"id": "b", "score": 4}], "summary": "s"}
    _snapshot(db_session, test_curation, v1, "submitted", now - timedelta(days=5))
    _decision(db_session, test_curation, reviewer, now - timedelta(days=4))
    _snapshot(db_session, test_curation, v1, "draft", now - timedelta(days=3))
    _snapshot(db_session, test_curation, v2, "draft", now - timedelta(days=2), "draft")
    _snapshot(
        db_session, test_curation, v2, "submitted", now - timedelta(days=1), "draft"
    )
    test_curation.evidence_data = (
        v2  # the row after the resubmission, as the trigger stores it
    )
    db_session.commit()

    body = _diff(client, reviewer, test_curation)

    assert [(i["path"], i["before"], i["after"]) for i in body["items"]] == [
        ("cases[b].score", 2, 4)
    ]
    assert body["baseline"]["source"] == "review"
    assert body["baseline"]["as_of"].startswith(
        (now - timedelta(days=4)).date().isoformat()
    )


def test_without_a_decision_the_baseline_is_the_previous_submission(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    test_curation: CurationNew,
) -> None:
    now = datetime.now(UTC)
    _snapshot(
        db_session,
        test_curation,
        {"score": 1, "old": 1},
        "submitted",
        now - timedelta(days=2),
    )
    _snapshot(
        db_session,
        test_curation,
        {"score": 3},
        "draft",
        now - timedelta(days=1.5),
        "submitted",
    )
    _snapshot(
        db_session,
        test_curation,
        {"score": 3, "new": "x"},
        "submitted",
        now - timedelta(days=1),
        "draft",
    )
    test_curation.evidence_data = {"score": 3, "new": "x"}
    db_session.commit()

    body = _diff(client, reviewer, test_curation)

    got = {i["path"]: i for i in body["items"]}
    assert set(got) == {"score", "old", "new"}
    assert got["old"]["change"] == "removed"
    assert body["baseline"]["source"] == "previous_submission"


def test_a_first_submission_shows_every_item_as_added(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    test_curation: CurationNew,
) -> None:
    _snapshot(
        db_session,
        test_curation,
        {"a": 1, "b": {"c": 2}},
        "submitted",
        datetime.now(UTC),
    )
    test_curation.evidence_data = {"a": 1, "b": {"c": 2}}
    db_session.commit()
    body = _diff(client, reviewer, test_curation)
    assert body["baseline"] is None
    assert {(i["path"], i["change"]) for i in body["items"]} == {
        ("a", "added"),
        ("b", "added"),
    }


def test_diff_ignores_edits_made_while_already_submitted_when_finding_submissions(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,
    test_curation: CurationNew,
) -> None:
    now = datetime.now(UTC)
    _snapshot(
        db_session, test_curation, {"score": 1}, "submitted", now - timedelta(days=2)
    )
    _snapshot(
        db_session,
        test_curation,
        {"score": 2},
        "submitted",
        now - timedelta(days=1),
        "submitted",
    )
    test_curation.evidence_data = {"score": 2}
    db_session.commit()
    # one real submission only, so there is no earlier version a reviewer could have seen
    assert _diff(client, reviewer, test_curation)["baseline"] is None


def test_never_submitted_curation_lists_everything_as_added(
    client: TestClient, reviewer: UserNew, test_curation: CurationNew
) -> None:
    body = _diff(client, reviewer, test_curation)
    assert body["baseline"] is None
    assert [i["path"] for i in body["items"]] == ["status"]


def test_reviewer_marks_an_item_accepted_and_only_reviewers_may(
    client: TestClient,
    reviewer: UserNew,
    test_user_curator: UserNew,
    test_curation: CurationNew,
) -> None:
    ok = client.post(
        _url(test_curation),
        json={"item_path": "cases[b]", "kind": "accepted"},
        headers=_auth(reviewer),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["kind"] == "accepted"
    assert ok.json()["body"] == "Accepted"
    # a curator's reply is a query-kind comment; marking an item accepted is the reviewer's call
    denied = client.post(
        _url(test_curation),
        json={"item_path": "cases[b]", "kind": "accepted"},
        headers=_auth(test_user_curator),
    )
    assert denied.status_code == 403
    reply = client.post(
        _url(test_curation),
        json={"item_path": "cases[b]", "body": "Fixed"},
        headers=_auth(test_user_curator),
    )
    assert reply.json()["kind"] == "query"


def test_diff_is_for_scope_members_only(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_curation: CurationNew,
) -> None:
    pending = _member(db_session, test_scope, "reviewer", accepted=False)
    response = client.get(
        f"/api/v1/curations/{test_curation.id}/diff", headers=_auth(pending)
    )
    assert response.status_code == 403
