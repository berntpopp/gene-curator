"""MCP study F7: curation_diff takes a baseline (submitted, active or an audit id) and says
whether anything changed."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import ActiveCuration, AuditLogNew, CurationNew, Review, UserNew
from tests.api.test_review_comments_api import (  # noqa: F401 (fixture)
    _auth,
    _snapshot,
    reviewer,
)

pytestmark = pytest.mark.unit


def _get(client: TestClient, user: UserNew, curation: CurationNew, baseline: str):
    return client.get(
        f"/api/v1/curations/{curation.id}/diff",
        params={"baseline": baseline},
        headers=_auth(user),
    )


def test_submitted_baseline_reports_changed(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,  # noqa: F811
    test_curation: CurationNew,
) -> None:
    v1 = {"score": 1}
    _snapshot(
        db_session, test_curation, v1, "submitted", datetime.now(UTC) - timedelta(1)
    )
    test_curation.evidence_data = v1
    db_session.commit()

    same = _get(client, reviewer, test_curation, "submitted").json()
    assert (same["changed"], same["items"], same["baseline"]["source"]) == (
        False,
        [],
        "submitted",
    )

    test_curation.evidence_data = {"score": 2}
    db_session.commit()
    moved = _get(client, reviewer, test_curation, "submitted").json()
    assert moved["changed"] is True
    assert [i["path"] for i in moved["items"]] == ["score"]


def test_audit_id_baseline_and_missing_baselines(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,  # noqa: F811
    test_curation: CurationNew,
) -> None:
    assert _get(client, reviewer, test_curation, "submitted").status_code == 404
    assert _get(client, reviewer, test_curation, "active").status_code == 404
    assert _get(client, reviewer, test_curation, "999").status_code == 404
    assert _get(client, reviewer, test_curation, "latest").status_code == 422

    _snapshot(db_session, test_curation, {"a": 1}, "draft", datetime.now(UTC))
    row = db_session.query(AuditLogNew).one()
    test_curation.evidence_data = {"a": 1}
    db_session.commit()
    body = _get(client, reviewer, test_curation, str(row.id)).json()
    assert body["baseline"] == {
        "audit_id": row.id,
        "as_of": body["baseline"]["as_of"],
        "source": "audit",
        "note": None,
    }
    assert body["changed"] is False


def test_active_baseline_compares_with_the_active_curation(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,  # noqa: F811
    test_curation: CurationNew,
) -> None:
    active = CurationNew(
        id=uuid4(),
        scope_id=test_curation.scope_id,
        gene_id=test_curation.gene_id,
        workflow_pair_id=test_curation.workflow_pair_id,
        workflow_stage="active",
        status="active",
        evidence_data={"a": 1},
        created_by=test_curation.created_by,
    )
    db_session.add(active)
    db_session.flush()
    db_session.add(
        ActiveCuration(
            gene_id=active.gene_id, scope_id=active.scope_id, curation_id=active.id
        )
    )
    test_curation.evidence_data = {"a": 2}
    db_session.commit()

    body = _get(client, reviewer, test_curation, "active").json()
    assert body["baseline"]["source"] == "active_curation"
    assert body["changed"] is True


def test_resubmission_is_compared_with_the_previous_submission(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,  # noqa: F811
    test_curation: CurationNew,
) -> None:
    """MCP study round 3 T6: baseline=submitted silently returned no changes after a
    resubmission; previous_submission is the one before, and submitted says so."""
    now = datetime.now(UTC)
    _snapshot(db_session, test_curation, {"score": 1}, "submitted", now - timedelta(2))
    assert (
        _get(client, reviewer, test_curation, "previous_submission").status_code == 404
    )
    _snapshot(
        db_session,
        test_curation,
        {"score": 2},
        "submitted",
        now - timedelta(1),
        "draft",
    )
    first, latest = db_session.query(AuditLogNew).order_by(AuditLogNew.id).all()
    test_curation.evidence_data = {"score": 2}
    db_session.commit()

    same = _get(client, reviewer, test_curation, "submitted").json()
    assert (same["changed"], same["baseline"]["audit_id"]) == (False, latest.id)
    assert same["baseline"]["note"] == (
        f"The latest submission (audit {latest.id}) is the current evidence; "
        f"baseline=previous_submission compares with audit {first.id}"
    )
    before = _get(client, reviewer, test_curation, "previous_submission").json()
    assert before["baseline"]["source"] == "previous_submission"
    assert before["baseline"]["audit_id"] == first.id
    assert before["baseline"]["note"] is None
    assert [i["path"] for i in before["items"]] == ["score"]

    test_curation.evidence_data = {"score": 3}  # edited since: no note needed
    db_session.commit()
    moved = _get(client, reviewer, test_curation, "submitted").json()
    assert (moved["changed"], moved["baseline"]["note"]) == (True, None)


def test_audit_trail_lists_every_submission_with_its_snapshot_id(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,  # noqa: F811
    test_curation: CurationNew,
) -> None:
    now = datetime.now(UTC)
    _snapshot(db_session, test_curation, {"score": 1}, "submitted", now - timedelta(3))
    _snapshot(db_session, test_curation, {"score": 2}, "submitted", now - timedelta(1))
    first, latest = db_session.query(AuditLogNew).order_by(AuditLogNew.id).all()
    db_session.add(
        Review(
            curation_id=test_curation.id,
            reviewer_id=reviewer.id,
            assigned_by=test_curation.created_by,
            status="needs_revision",
            reviewed_at=now - timedelta(2),
            comments="Add variants",
        )
    )
    db_session.commit()

    trail = client.get(
        f"/api/v1/workflow/curation/{test_curation.id}/audit-trail",
        headers=_auth(reviewer),
    )
    assert trail.status_code == 200, trail.text
    entries = trail.json()["entries"]
    assert [(e["to_stage"], e["audit_id"]) for e in entries] == [
        ("review", first.id),
        ("curation", first.id),  # the decision reviewed the first submission
        ("review", latest.id),
    ]
    body = _get(client, reviewer, test_curation, str(entries[1]["audit_id"])).json()
    assert body["baseline"]["source"] == "audit"
