"""Review decisions made through the generic transition endpoint keep their notes (the curator sees
the request-changes feedback); approve notes are kept too."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    CurationNew,
    Review,
    ReviewStatus,
    Scope,
    UserNew,
)
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
)

pytestmark = pytest.mark.unit

BASE = "/api/v1/workflow"


@pytest.fixture
def in_review(
    db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> CurationNew:
    curation = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    curation.submitted_at = datetime.now(UTC) - timedelta(hours=1)
    curation.submitted_by = curator.id
    db_session.commit()
    return curation


def _transition(
    client: TestClient, user: UserNew, item: str, item_id: object, **body: object
):
    return client.post(
        f"{BASE}/{item}/{item_id}/transition", json=body, headers=auth_headers(user)
    )


def test_request_changes_feedback_reaches_the_curator(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    in_review,
) -> None:
    sent = _transition(
        client,
        reviewer,
        "curation",
        in_review.id,
        target_stage="curation",
        notes="Add the segregation data",
    )
    assert sent.status_code == 200, sent.text

    review = db_session.query(Review).filter_by(curation_id=in_review.id).one()
    assert review.reviewer_id == reviewer.id
    assert review.status == ReviewStatus.NEEDS_REVISION
    assert review.comments == "Add the segregation data"

    trail = client.get(
        f"{BASE}/curation/{in_review.id}/audit-trail", headers=auth_headers(curator)
    )
    assert trail.status_code == 200, trail.text
    entries = trail.json()["entries"]
    assert [(e["from_stage"], e["to_stage"]) for e in entries] == [
        ("curation", "review"),
        ("review", "curation"),
    ]
    assert entries[-1]["notes"] == "Add the segregation data"
    assert entries[-1]["executed_by"] == str(reviewer.id)
    assert entries[-1]["executed_by_name"] == "Reviewer"
    assert trail.json()["total_transitions"] == 2


def test_approve_notes_fill_the_reviewers_pending_review(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    in_review,
) -> None:
    db_session.add(
        Review(
            curation_id=in_review.id, reviewer_id=reviewer.id, assigned_by=curator.id
        )
    )
    db_session.commit()

    sent = _transition(
        client, reviewer, "curation", in_review.id, target_stage="active", notes="Solid"
    )
    assert sent.status_code == 200, sent.text

    review = db_session.query(Review).filter_by(curation_id=in_review.id).one()
    assert (review.status, review.recommendation, review.comments) == (
        ReviewStatus.APPROVED,
        "approve",
        "Solid",
    )
    assert review.reviewed_at is not None


def test_auto_activation_keeps_the_submitted_review(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    in_review,
) -> None:
    review = Review(
        curation_id=in_review.id, reviewer_id=reviewer.id, assigned_by=curator.id
    )
    db_session.add(review)
    db_session.commit()

    sent = client.post(
        f"{BASE}/reviews/{review.id}/submit",
        json={"decision": "approve", "comments": "Looks good"},
        headers=auth_headers(reviewer),
    )
    assert sent.status_code == 200, sent.text
    rows = db_session.query(Review).filter_by(curation_id=in_review.id).all()
    assert [r.comments for r in rows] == ["Looks good"]


def test_audit_trail_needs_scope_membership(
    client: TestClient, outsider: UserNew, in_review
) -> None:
    trail = client.get(
        f"{BASE}/curation/{in_review.id}/audit-trail", headers=auth_headers(outsider)
    )
    assert trail.status_code == 403


def test_only_the_activating_approval_moves_to_active(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    owner: UserNew,
    in_review,
) -> None:
    """W11 A4: the first of two approvals leaves the curation in review."""
    now = datetime.now(UTC)
    for who, minutes in ((owner, 30), (reviewer, 10)):
        db_session.add(
            Review(
                curation_id=in_review.id,
                reviewer_id=who.id,
                assigned_by=curator.id,
                status=ReviewStatus.APPROVED,
                recommendation="approve",
                reviewed_at=now - timedelta(minutes=minutes),
            )
        )
    db_session.commit()

    def stages() -> list[tuple[str, str]]:
        trail = client.get(
            f"{BASE}/curation/{in_review.id}/audit-trail",
            headers=auth_headers(curator),
        )
        return [(e["from_stage"], e["to_stage"]) for e in trail.json()["entries"]]

    still_open = [("curation", "review"), ("review", "review"), ("review", "review")]
    assert stages() == still_open
    in_review.approved_at = now - timedelta(minutes=9)
    db_session.commit()
    assert stages()[-1] == ("review", "active")
    assert stages()[1] == ("review", "review")
