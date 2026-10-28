"""One reviewer read: curation, trace with excluded rows, warnings, workflow state, diff."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    CurationStatus,
    Review,
    ReviewItemComment,
    ReviewStatus,
    Scope,
    UserNew,
    WorkflowStage,
)
from app.schemas.curation import capped
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_user,
)

pytestmark = pytest.mark.unit

TRACE = {
    "sections": [
        {
            "key": "genetic",
            "raw": 14,
            "cap": 12,
            "score": 12,
            "categories": [
                {
                    "key": "cases",
                    "raw": 14,
                    "cap": 12,
                    "score": 12,
                    "types": [
                        {"path": "a", "items": 2, "score": 14},
                        {"path": "b", "items": 0, "score": 0},
                    ],
                }
            ],
        },
        {"key": "experimental", "raw": 1, "cap": 6, "score": 1, "categories": []},
    ]
}


def test_capped_names_each_section_and_category_over_cap() -> None:
    assert capped(TRACE) == [
        "genetic: 14 points claimed, capped at 12",
        "genetic.cases: 14 points claimed, capped at 12",
    ]
    assert capped(None) == []


def test_reviewer_reads_everything_in_one_call(
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
        evidence_data={"genetic": {"cases": [{"pmid": "999999999"}]}},
    )
    excluded = [{"path": "genetic.cases[0]", "pmid": "999999999", "reason": "unknown"}]
    c.computed_scores = {
        "total_score": 12,
        "trace": TRACE,
        "excluded": excluded,
        "warnings": ["genetic.cases[0].pmid: 999999999 not found in PubMed"],
    }
    db_session.commit()

    r = client.get(f"/api/v1/curations/{c.id}/review", headers=auth_headers(reviewer))

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["curation"]["evidence_data"] == c.evidence_data
    assert body["curation"]["computed_scores"]["excluded"] == excluded
    (cases,) = body["curation"]["computed_scores"]["trace"]["sections"][0]["categories"]
    assert [t["path"] for t in cases["types"]] == ["a"]  # zero-item types dropped
    assert "warnings" not in body["curation"]["computed_scores"]  # listed once
    assert body["warnings"] == [
        "genetic.cases[0].pmid: 999999999 not found in PubMed",
        "genetic: 14 points claimed, capped at 12",
        "genetic.cases: 14 points claimed, capped at 12",
    ]
    assert body["workflow"]["current_stage"] == "review"
    assert body["first_submission"] is True
    assert "diff" not in body or body["diff"] is None  # no all-"added" diff
    assert body["previous_reviews"] == body["open_item_comments"] == []


def test_outsider_cannot_read_for_review(
    client: TestClient, db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:

    c = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    r = client.get(
        f"/api/v1/curations/{c.id}/review", headers=auth_headers(make_user(db_session))
    )
    assert r.status_code == 403


def test_resubmission_carries_the_earlier_rounds_feedback(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
) -> None:
    c = make_curation(
        db_session, scope=scope_with_admin, gene=make_gene(db_session), creator=curator
    )
    now = datetime.now(UTC)
    c.submitted_at = now
    db_session.add_all(
        [
            Review(
                curation_id=c.id,
                reviewer_id=reviewer.id,
                assigned_by=curator.id,
                status=ReviewStatus.NEEDS_REVISION,
                comments="PMID 1 is a review, not a case",
                feedback_data={"pmids": ["1"]},
                assigned_at=now - timedelta(days=2),
                reviewed_at=now - timedelta(days=1),
            ),
            ReviewItemComment(
                curation_id=c.id,
                item_path="genetic_evidence.segregation[0]",
                body="LOD score source?",
                author_id=reviewer.id,
                created_at=now - timedelta(days=1),
            ),
            ReviewItemComment(  # resolved: not repeated
                curation_id=c.id,
                item_path="x",
                body="done",
                author_id=reviewer.id,
                status="resolved",
                created_at=now - timedelta(days=1),
            ),
        ]
    )
    db_session.commit()

    body = client.get(
        f"/api/v1/curations/{c.id}/review", headers=auth_headers(reviewer)
    ).json()

    assert body["first_submission"] is False
    (prev,) = body["previous_reviews"]
    assert (prev["reviewer"], prev["decision"], prev["comments"]) == (
        "Reviewer",
        "needs_revision",
        "PMID 1 is a review, not a case",
    )
    assert prev["feedback_data"] == {"pmids": ["1"]}
    (comment,) = body["open_item_comments"]
    assert comment.pop("id")  # resolve it without another call
    assert [comment] == [
        {
            "item_path": "genetic_evidence.segregation[0]",
            "kind": "query",
            "body": "LOD score source?",
        }
    ]


@pytest.mark.parametrize("via", ["peer_review", "transition"])
def test_request_changes_then_resubmit_lists_round_one(
    client: TestClient,
    db_session: Session,
    curator: UserNew,
    reviewer: UserNew,
    scope_with_admin: Scope,
    via: str,
) -> None:
    """The exact flow: submit, request changes with comments, edit, resubmit, review read."""
    c = make_curation(
        db_session,
        scope=scope_with_admin,
        gene=make_gene(db_session),
        creator=curator,
        stage=WorkflowStage.CURATION,
        status=CurationStatus.DRAFT,
    )
    url = f"/api/v1/curations/{c.id}"
    me, rev = auth_headers(curator), auth_headers(reviewer)

    def submit() -> None:
        lock = client.get(url, headers=me).json()["lock_version"]
        r = client.post(
            f"{url}/submit",
            json={"lock_version": lock, "reviewer_id": str(reviewer.id)},
            headers=me,
        )
        assert r.status_code == 200, r.text

    submit()
    comment = client.post(
        f"{url}/review-comments",
        json={"item_path": "summary", "body": "Which PMID?"},
        headers=rev,
    )
    assert comment.status_code in (200, 201), comment.text
    if via == "peer_review":
        (review,) = client.get(
            "/api/v1/workflow/reviews/my-assignments", headers=rev
        ).json()
        sent = client.post(
            f"/api/v1/workflow/reviews/{review['review_id']}/submit",
            json={"decision": "request_changes", "comments": "Cite the case report"},
            headers=rev,
        )
    else:
        sent = client.post(
            f"/api/v1/workflow/curation/{c.id}/transition",
            json={"target_stage": "curation", "notes": "Cite the case report"},
            headers=rev,
        )
    assert sent.status_code == 200, sent.text
    back = client.get(f"{url}/review", headers=me).json()  # changes requested
    assert [p["comments"] for p in back["previous_reviews"]] == ["Cite the case report"]
    assert [x["body"] for x in back["open_item_comments"]] == ["Which PMID?"]
    lock = client.get(url, headers=me).json()["lock_version"]
    edited = client.patch(
        f"{url}/draft",
        json={"evidence_data": {"summary": "PMID 123"}, "lock_version": lock},
        headers=me,
    )
    assert edited.status_code == 200, edited.text
    submit()

    body = client.get(f"{url}/review", headers=rev).json()

    assert body["first_submission"] is False
    assert [(p["reviewer"], p["comments"]) for p in body["previous_reviews"]] == [
        ("Reviewer", "Cite the case report")
    ]
    assert [x["body"] for x in body["open_item_comments"]] == ["Which PMID?"]
