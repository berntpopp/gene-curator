"""Scope admins correct a legacy curation's disease entity, audited (#453)."""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.models import AuditLogNew, CurationNew, CurationStatus, WorkflowStage
from tests.api.scopes.factories import auth_headers, make_member, make_user
from tests.unit.test_split_entities import A, World

pytestmark = pytest.mark.unit

FIX = {
    "disease_name": "HNF1B disorder",
    "mondo_id": "MONDO:0000001",
    "mode_of_inheritance": "AD",
    "reason": "Legacy import lost the disease",
}


@pytest.fixture(autouse=True)
def no_rls_on_sqlite():
    """No RLS, and audit_log ids by hand (SQLite has no BigInteger autoincrement)."""

    def assign_id(mapper: Any, connection: Any, target: AuditLogNew) -> None:
        top = select(func.coalesce(func.max(AuditLogNew.id), 0))
        target.id = target.id or connection.scalar(top) + 1

    event.listen(AuditLogNew, "before_insert", assign_id)
    with patch("app.api.v1.endpoints.disease_correction.set_rls_context"):
        yield
    event.remove(AuditLogNew, "before_insert", assign_id)


def _legacy(world: World, evidence: Any = None, **kw: Any) -> CurationNew:
    c = CurationNew(
        gene_id=world.gene.id,
        scope_id=world.scope.id,
        workflow_pair_id=world.pair.id,
        status=kw.pop("status", CurationStatus.DRAFT),
        workflow_stage=WorkflowStage.CURATION,
        evidence_data={"summary": "kept"} if evidence is None else evidence,
        created_by=world.author.id,
        **kw,
    )
    world.db.add(c)
    world.db.commit()
    return c


def _correct(client: TestClient, c: CurationNew, user, **body: Any):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/curations/{c.id}/disease-correction",
        json={**FIX, "lock_version": c.lock_version, **body},
        headers=auth_headers(user),
    )


def _admin(world: World):  # type: ignore[no-untyped-def]
    admin = make_user(world.db)
    make_member(world.db, world.scope, admin, "admin")
    return admin


def test_only_a_scope_admin_corrects(db_session: Session, client: TestClient) -> None:
    world = World(db_session)
    c = _legacy(world)
    for user in (world.author, world.reviewer):
        assert _correct(client, c, user).status_code == 403
    admin = _admin(world)
    r = _correct(client, c, admin)
    assert r.status_code == 200, r.text
    db_session.refresh(c)
    assert c.evidence_data == {
        "summary": "kept",
        "entity_definition": {
            "disease_name": "HNF1B disorder",
            "mondo_id": "MONDO:0000001",
            "mode_of_inheritance": "AD",
        },
    }
    assert c.entity_key == "MONDO:0000001|AD" and c.updated_by == admin.id
    audit = db_session.scalars(
        select(AuditLogNew).where(
            AuditLogNew.entity_id == c.id,
            AuditLogNew.change_type == "disease_correction",
        )
    ).one()
    assert audit.user_id == admin.id and audit.changes == {"reason": FIX["reason"]}
    assert audit.old_values and audit.old_values["entity_key"] == ""
    assert audit.old_values["mondo_id"] is None
    assert audit.new_values and audit.new_values["mondo_id"] == "MONDO:0000001"
    assert audit.new_values["entity_key"] == "MONDO:0000001|AD"


@pytest.mark.parametrize(
    "body",
    [{"reason": "  "}, {"mondo_id": "0000001"}, {"disease_name": ""}],
)
def test_reason_and_entity_are_validated(
    db_session: Session, client: TestClient, body: dict
) -> None:
    world = World(db_session)
    c = _legacy(world)
    assert _correct(client, c, _admin(world), **body).status_code == 422


def test_flat_answers_are_corrected_where_they_take_precedence(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    c = _legacy(world, {"mondo_id": "", "entity_definition": {"mondo_id": "MONDO:9"}})
    r = _correct(client, c, _admin(world), relationship_type="susceptibility")
    assert r.status_code == 200, r.text
    db_session.refresh(c)
    assert c.evidence_data["mondo_id"] == "MONDO:0000001"
    assert c.evidence_data["entity_definition"]["mondo_id"] == "MONDO:0000001"
    assert c.entity_key == "MONDO:0000001|AD|SUSCEPTIBILITY"


@pytest.mark.parametrize(
    ("kw", "lock", "code"),
    [
        ({}, 7, 409),  # stale
        ({"status": CurationStatus.SUBMITTED}, 0, 409),  # in review: not here
        ({"evidence_data": {"entity_definition": "MONDO:1"}}, 0, 422),  # malformed
    ],
)
def test_refused_corrections_change_nothing(
    db_session: Session, client: TestClient, kw: dict, lock: int, code: int
) -> None:
    world = World(db_session)
    evidence = kw.pop("evidence_data", None)
    c = _legacy(world, evidence, **kw)
    before = (dict(c.evidence_data), c.lock_version, c.entity_key, c.status)
    r = _correct(client, c, _admin(world), lock_version=lock)
    assert r.status_code == code, r.text
    db_session.refresh(c)
    assert (c.evidence_data, c.lock_version, c.entity_key, c.status) == before


def test_an_entity_another_open_curation_has_is_409(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    other = _legacy(world, entity_key="MONDO:0000001|AD")
    c = _legacy(world)
    r = _correct(client, c, _admin(world))
    assert r.status_code == 409 and r.json()["detail"]["curation_id"] == str(other.id)


def test_missing_curation_is_404(db_session: Session, client: TestClient) -> None:
    world = World(db_session)
    r = client.post(
        "/api/v1/curations/00000000-0000-0000-0000-000000000000/disease-correction",
        json={**FIX, "lock_version": 0},
        headers=auth_headers(_admin(world)),
    )
    assert r.status_code == 404


def test_races_and_rls_denials_are_409_and_403(
    db_session: Session, client: TestClient
) -> None:
    from sqlalchemy.exc import DBAPIError, IntegrityError

    world = World(db_session)
    c, admin = _legacy(world), _admin(world)
    race = IntegrityError("UPDATE", {}, Exception("uq_curations_one_open"))
    with patch("app.crud.disease_correction.claim_version", side_effect=race):
        assert _correct(client, c, admin).status_code == 409
    denied = DBAPIError("UPDATE", {}, Exception("rls"))
    with patch(
        "app.api.v1.endpoints.disease_correction.correct_disease", side_effect=denied
    ):
        assert _correct(client, c, admin).status_code == 403


def test_the_corrector_may_not_review_the_curation(
    db_session: Session, client: TestClient
) -> None:
    """D1: a correction is their work, so the scope admin who made it cannot approve it."""
    world = World(db_session)
    c, admin = _legacy(world), _admin(world)
    assert _correct(client, c, admin).status_code == 200
    c.status, c.workflow_stage = CurationStatus.SUBMITTED, WorkflowStage.REVIEW
    db_session.commit()
    url = f"/api/v1/workflow/curation/{c.id}"
    body = {"target_stage": "active", "notes": "ok"}

    def errors(user) -> list[str]:  # type: ignore[no-untyped-def]
        r = client.post(
            f"{url}/validate-transition", json=body, headers=auth_headers(user)
        )
        return [e for e in r.json()["errors"] if "4-eyes" in e]

    assert errors(admin) == ["4-eyes principle violation: Cannot review your own work"]
    assert errors(world.reviewer) == []
    r = client.post(f"{url}/transition", json=body, headers=auth_headers(admin))
    assert r.status_code >= 400, r.text
    db_session.refresh(c)
    assert c.status == CurationStatus.SUBMITTED


def test_the_corrector_is_no_peer_reviewer(
    db_session: Session, client: TestClient
) -> None:
    """D1 on the peer-review path, two reviewers required: the corrector can neither be
    assigned nor submit a review, and an approval of theirs never counts."""
    from datetime import UTC, datetime, timedelta

    from app.crud.review_round import approving_reviewers
    from app.models import Review, ReviewStatus
    from app.services.curation_access import _can_user_review_curation
    from tests.unit.scope.test_workflow_config import _pin

    world = World(db_session)
    c, admin = _legacy(world), _admin(world)
    assert _correct(client, c, admin).status_code == 200
    db_session.refresh(c)
    c.status, c.workflow_stage = CurationStatus.IN_REVIEW, WorkflowStage.REVIEW
    c.submitted_at = datetime.now(UTC) - timedelta(minutes=1)
    _pin(db_session, c, {"review": {"reviewers_required": 2}})

    r = client.post(
        f"/api/v1/workflow/curation/{c.id}/assign-reviewer",
        json={"reviewer_id": str(admin.id)},
        headers=auth_headers(world.author),
    )
    assert r.status_code == 403 and "4-eyes" in r.text, r.text
    # An assignment from before the correction (or a legacy row) is refused at submit
    review = Review(
        curation_id=c.id,
        reviewer_id=admin.id,
        assigned_by=world.author.id,
        status=ReviewStatus.PENDING,
    )
    db_session.add(review)
    db_session.commit()
    r = client.post(
        f"/api/v1/workflow/reviews/{review.id}/submit",
        json={"decision": "approve"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 403 and "corrected" in r.text, r.text
    db_session.refresh(review)
    assert review.status == ReviewStatus.PENDING
    review.status, review.recommendation = ReviewStatus.APPROVED, "approve"
    db_session.commit()
    assert approving_reviewers(db_session, c) == 0
    assert not _can_user_review_curation(db_session, admin, c)
    assert _can_user_review_curation(db_session, world.reviewer, c)

    # A real reviewer approves too: one approval counts, two are required, still in review
    r = client.post(
        f"/api/v1/workflow/curation/{c.id}/assign-reviewer",
        json={"reviewer_id": str(world.reviewer.id)},
        headers=auth_headers(world.author),
    )
    assert r.status_code == 200, r.text
    real = db_session.scalar(
        select(Review).where(
            Review.curation_id == c.id, Review.reviewer_id == world.reviewer.id
        )
    )
    r = client.post(
        f"/api/v1/workflow/reviews/{real.id}/submit",
        json={"decision": "approve"},
        headers=auth_headers(world.reviewer),
    )
    assert r.status_code == 200, r.text
    db_session.refresh(c)
    assert approving_reviewers(db_session, c) == 1
    assert c.status == CurationStatus.IN_REVIEW


def test_a_short_reason_names_its_trimmed_length(
    db_session: Session, client: TestClient
) -> None:
    """Monkey L5: '  a    ' was reported as 7 characters, min 3."""
    world = World(db_session)
    r = _correct(client, _legacy(world), _admin(world), reason="  a    ")
    assert r.status_code == 422
    assert "1 characters after trimming, min 3" in r.text, r.text


def test_old_values_name_the_entity_the_precuration_supplied(
    db_session: Session, client: TestClient
) -> None:
    """Monkey L5: the audit logged null old values for a curation whose disease
    came from its precuration."""
    world = World(db_session)
    _, cid = world.approve({**A, "disease_name": "old"})
    c = db_session.get(CurationNew, cid)
    assert c is not None
    assert _correct(client, c, _admin(world)).status_code == 200, c.evidence_data
    audit = db_session.scalars(
        select(AuditLogNew).where(AuditLogNew.change_type == "disease_correction")
    ).one()
    assert audit.old_values is not None
    assert audit.old_values["disease_name"] == "old"
    assert audit.old_values["mondo_id"] == A["mondo_id"]
    assert audit.old_values["relationship_type"] == "mendelian"


def test_the_detail_tells_the_corrector_why_they_cannot_review(
    db_session: Session, client: TestClient
) -> None:
    """Monkey R2-5: the corrector saw "No actions available" with no reason."""
    world = World(db_session)
    c, admin = _legacy(world), _admin(world)
    assert _correct(client, c, admin).status_code == 200
    c.status, c.workflow_stage = CurationStatus.IN_REVIEW, WorkflowStage.REVIEW
    db_session.commit()

    def detail(user):  # type: ignore[no-untyped-def]
        r = client.get(f"/api/v1/curations/{c.id}", headers=auth_headers(user))
        assert r.status_code == 200, r.text
        return r.json()

    assert detail(admin)["corrected_disease"] is True
    assert detail(admin)["can_review"] is False
    assert detail(world.reviewer)["corrected_disease"] is False


def test_a_new_entity_drops_the_clingen_reference_of_the_old_one(
    db_session: Session, client: TestClient
) -> None:
    world = World(db_session)
    c = _legacy(world, entity_key="MONDO:0000002|AD", clingen_reference={"x": 1})
    r = _correct(client, c, _admin(world))
    assert r.status_code == 200, r.text
    db_session.refresh(c)
    assert (c.entity_key, c.clingen_reference) == ("MONDO:0000001|AD", None)
