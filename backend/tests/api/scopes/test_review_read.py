"""One reviewer read: curation, trace with excluded rows, warnings, workflow state, diff."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Scope, UserNew
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
            "categories": [{"key": "cases", "raw": 14, "cap": 12, "score": 12}],
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
    assert body["curation"]["computed_scores"]["trace"]["sections"][1]["key"] == (
        "experimental"  # detail: zero-point rows stay
    )
    assert body["warnings"] == [
        "genetic.cases[0].pmid: 999999999 not found in PubMed",
        "genetic: 14 points claimed, capped at 12",
        "genetic.cases: 14 points claimed, capped at 12",
    ]
    assert body["workflow"]["current_stage"] == "review"
    assert body["diff"]["items"][0]["change"] == "added"


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
