"""Move curations to a newer methodology version (#591) through the public API.

v2 of the fixture schema adds a field (required when ``needs`` is true), removes one
(``old_note``) and raises the class threshold from 3 to 5 points.
"""

from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.core.capabilities import INACTIVE_SCOPE
from app.crud.review_round import corrected_by
from app.models import AuditLogNew, NotificationNew
from app.models.methodology import MethodologyVersion
from app.models.model_enums import NotificationType, ReviewStatus
from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    Review,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)
from app.services import version_move
from tests.api.schema_api_support import auth

pytestmark = pytest.mark.unit

PMID = "12345678"
FIELDS = {
    "s": {"type": "object", "properties": {"t": {"type": "array"}}},
    "needs": {"type": "boolean"},
}
V1 = {**FIELDS, "old_note": {"type": "text"}}
V2 = {**FIELDS, "new_req": {"type": "text", "required_when": {"needs": True}}}


def _config(threshold: int) -> dict[str, Any]:
    model = {
        "sections": [
            {
                "key": "s",
                "categories": [{"key": "c", "types": [{"path": "t", "default": 2}]}],
            }
        ],
        "bands": [{"class": "high", "min": threshold}, {"class": "low"}],
    }
    return {"point_model": model}


def _snapshot(fields: dict[str, Any], threshold: int) -> dict[str, Any]:
    return {
        "field_definitions": fields,
        "validation_rules": {},
        "scoring_configuration": _config(threshold),
        "workflow_states": {},
        "ui_configuration": {},
    }


@pytest.fixture(autouse=True)
def audit_ids() -> Any:
    """audit_log ids by hand (SQLite has no BigInteger autoincrement); one flush inserts
    several rows, so the ids come from a counter."""
    ids = count(1)

    def assign_id(mapper: Any, connection: Any, target: AuditLogNew) -> None:
        target.id = target.id or next(ids)

    event.listen(AuditLogNew, "before_insert", assign_id)
    yield
    event.remove(AuditLogNew, "before_insert", assign_id)


class World:
    schema: UUID
    v1: UUID
    v2: UUID
    rows: dict[str, CurationNew]


def _rows(n: int) -> dict[str, Any]:
    return {"t": [{"pmid": PMID} for _ in range(n)]}


@pytest.fixture
def world(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_curator: UserNew,
) -> World:
    w = World()
    schema = CurationSchema(
        id=uuid4(),
        name="Move",
        version="1",
        schema_type="curation",
        field_definitions=V2,
        workflow_states={},
        ui_configuration={},
        scoring_configuration=_config(5),
        schema_hash=uuid4().hex * 2,
    )
    db_session.add(schema)
    db_session.flush()
    v1, v2 = (
        MethodologyVersion(schema_id=schema.id, version=n, snapshot=_snapshot(f, t))
        for n, f, t in ((1, V1, 3), (2, V2, 5))
    )
    pair = WorkflowPair(id=uuid4(), name="m", version="1", curation_schema_id=schema.id)
    db_session.add_all([v1, v2, pair])
    db_session.flush()
    w.schema, w.v1, w.v2 = schema.id, v1.id, v2.id
    # name: (evidence, class under v1); a, b and c are active
    specs = {
        "a": ({"s": _rows(2), "old_note": "gone"}, "high"),  # 4 points: high -> low
        "b": ({"s": _rows(1)}, "low"),  # 2 points: low either way
        "c": ({"s": _rows(3), "needs": True}, "high"),  # misses new_req
        "d": ({"s": _rows(2)}, "high"),  # a draft: class changes, stays a draft
    }
    w.rows = {}
    for key, (evidence, verdict) in specs.items():
        active = key != "d"
        row = CurationNew(
            id=uuid4(),
            gene_id=test_gene.id,
            scope_id=test_scope.id,
            workflow_pair_id=pair.id,
            entity_key=key,
            methodology_version_id=v1.id,
            evidence_data=evidence,
            computed_scores={"total_score": 2.0 * len(evidence["s"]["t"])},
            computed_verdict=verdict,
            status=CurationStatus.ACTIVE if active else CurationStatus.DRAFT,
            workflow_stage="active" if active else "curation",
            is_draft=not active,
            created_by=test_user_curator.id,
        )
        db_session.add(row)
        db_session.flush()
        if active:
            db_session.add(
                ActiveCuration(
                    gene_id=test_gene.id,
                    scope_id=test_scope.id,
                    curation_id=row.id,
                    entity_key=key,
                )
            )
        w.rows[key] = row
    db_session.commit()
    return w


def _url(w: World, **params: Any) -> str:
    query = "&".join(f"{k}={str(v).lower()}" for k, v in params.items())
    return f"/api/v1/schemas/curation-schemas/{w.schema}/move-to-version?{query}"


def _by_id(body: dict[str, Any], w: World) -> dict[str, dict[str, Any]]:
    names = {str(r.id): k for k, r in w.rows.items()}
    return {names[i["id"]]: i for i in body["items"]}


def _copy(db: Session, active: CurationNew) -> CurationNew:
    """The open copy of an active curation (same entity, not itself)."""
    return db.scalars(
        select(CurationNew).where(
            CurationNew.entity_key == active.entity_key, CurationNew.id != active.id
        )
    ).one()


def test_dry_run_reports_and_writes_nothing(
    client: TestClient, db_session: Session, admin_token: str, world: World
) -> None:
    r = client.post(_url(world), headers=auth(admin_token))  # dry run by default
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["dry_run"], body["to_version"]) == (True, 2)
    items = _by_id(body, world)
    a, b, c, d = (items[k] for k in "abcd")
    assert (a["kept"], a["dropped"]) == (["s"], ["old_note"])
    assert (a["old_score"], a["new_score"], a["old_class"], a["new_class"]) == (
        4,
        4,
        "high",
        "low",
    )
    assert a["back_to"] == "review"
    assert (b["new_class"], b["back_to"]) == ("low", None)
    assert (c["missing_required"], c["back_to"]) == (["new_req"], "draft")
    assert (d["new_class"], d["back_to"]) == ("low", None)
    db_session.expire_all()
    assert {
        r.methodology_version_id for r in db_session.scalars(select(CurationNew))
    } == {world.v1}
    assert db_session.scalar(select(func.count()).select_from(AuditLogNew)) == 0


@pytest.fixture
def earlier_reviewer(
    db_session: Session, test_scope: Scope, test_user_admin: UserNew, world: World
) -> UserNew:
    """A scope reviewer who approved curation a."""
    user = UserNew(
        id=uuid4(),
        email="rev@test.com",
        hashed_password="x",
        name="Rev",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add_all(
        [
            ScopeMembership(
                scope_id=test_scope.id,
                user_id=user.id,
                role="reviewer",
                accepted_at=datetime.now(UTC),
            ),
            Review(
                curation_id=world.rows["a"].id,
                reviewer_id=user.id,
                assigned_by=test_user_admin.id,
                status=ReviewStatus.APPROVED,
                assigned_at=datetime.now(UTC) - timedelta(days=1),
            ),
        ]
    )
    db_session.commit()
    return user


def test_apply_keeps_approved_results_and_opens_copies(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    curator_token: str,
    test_user_admin: UserNew,
    test_user_curator: UserNew,
    earlier_reviewer: UserNew,
    world: World,
) -> None:
    assert (
        client.post(_url(world, dry_run=False), headers=auth(curator_token)).status_code
        == 403
    )

    r = client.post(_url(world, dry_run=False), headers=auth(admin_token))
    assert r.status_code == 200, r.text
    db_session.expire_all()
    a, b, c, d = (db_session.get(CurationNew, world.rows[k].id) for k in "abcd")
    assert a and b and c and d
    # the approved results that would change stay active, untouched
    for active in (a, c):
        assert (active.status, active.methodology_version_id) == (
            CurationStatus.ACTIVE,
            world.v1,
        )
    assert (a.computed_verdict, a.evidence_data["old_note"]) == ("high", "gone")
    # class change: an open copy goes to review, a second person approves it
    copy_a, copy_c = _copy(db_session, a), _copy(db_session, c)
    assert (copy_a.status, copy_a.workflow_stage.value, copy_a.computed_verdict) == (
        CurationStatus.IN_REVIEW,
        "review",
        "low",
    )
    assert copy_a.methodology_version_id == world.v2
    assert copy_a.evidence_data == {"s": _rows(2)}  # old_note dropped, s kept
    assert copy_a.created_by == test_user_curator.id and copy_a.submitted_at
    assert (copy_c.status, copy_c.is_draft) == (CurationStatus.DRAFT, True)
    # unchanged results and open work are re-pinned in place
    assert (b.status, b.methodology_version_id) == (CurationStatus.ACTIVE, world.v2)
    assert (d.status, d.computed_verdict, d.lock_version) == (
        CurationStatus.DRAFT,
        "low",
        1,
    )

    # the earlier reviewer is asked again, with a notification
    review = db_session.scalars(
        select(Review).where(Review.curation_id == copy_a.id)
    ).one()
    assert (review.reviewer_id, review.status) == (
        earlier_reviewer.id,
        ReviewStatus.PENDING,
    )
    note = db_session.scalars(
        select(NotificationNew).where(NotificationNew.user_id == earlier_reviewer.id)
    ).one()
    assert note.type == NotificationType.REVIEW_ASSIGNED

    audits = db_session.scalars(
        select(AuditLogNew).where(AuditLogNew.change_type == "version_move")
    ).all()
    assert len(audits) == 4
    log = next(x for x in audits if x.entity_id == copy_a.id)
    assert (log.previous_status, log.new_status) == ("active", "in_review")
    assert log.changes is not None
    assert (log.changes["from_version"], log.changes["to_version"]) == (1, 2)
    assert (log.changes["old_class"], log.changes["new_class"]) == ("high", "low")
    assert log.changes["dropped_values"] == {"old_note": "gone"}
    assert log.changes["id"] == str(a.id)
    # D1: the admin who moved it cannot review it (the curator is its author)
    assert corrected_by(db_session, copy_a.id, test_user_admin.id)

    # the export keeps the approved class and shows the new version where it moved
    export = client.get("/api/v1/export/curations", headers=auth(curator_token))
    assert export.status_code == 200, export.text
    exported = {i["curation_id"]: i for i in export.json()["items"]}
    assert exported[str(a.id)]["computed_verdict"] == "high"
    assert exported[str(b.id)]["methodology"]["version"] == 2

    again = client.post(_url(world, dry_run=False), headers=auth(admin_token))
    assert again.status_code == 200 and again.json()["items"] == []
    assert db_session.scalar(select(func.count()).select_from(AuditLogNew)) == 4


def test_an_open_recuration_is_moved_instead_of_copying(
    client: TestClient, db_session: Session, admin_token: str, world: World
) -> None:
    a = world.rows["a"]
    twin = CurationNew(
        id=uuid4(),
        gene_id=a.gene_id,
        scope_id=a.scope_id,
        workflow_pair_id=a.workflow_pair_id,
        entity_key="a",
        methodology_version_id=world.v1,
        evidence_data={},
        status=CurationStatus.DRAFT,
    )
    db_session.add(twin)
    db_session.commit()
    r = client.post(_url(world, dry_run=False), headers=auth(admin_token))
    assert r.status_code == 200, r.text
    ids = {i["id"] for i in r.json()["items"]}
    assert str(twin.id) in ids and str(a.id) not in ids
    db_session.expire_all()
    moved = db_session.get(CurationNew, twin.id)
    assert moved is not None and moved.methodology_version_id == world.v2
    assert _copy(db_session, a).id == twin.id  # no second open copy


def test_a_failed_row_moves_nothing(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    real = version_move._apply

    def fail_second(*args: Any) -> None:
        calls.append(1)
        if len(calls) == 2:
            args[0].flush()  # the first row's writes reached the database
            raise RuntimeError("boom")
        real(*args)

    monkeypatch.setattr(version_move, "_apply", fail_second)
    with pytest.raises(RuntimeError, match="boom"):
        client.post(_url(world, dry_run=False), headers=auth(admin_token))
    db_session.expire_all()
    rows = db_session.scalars(select(CurationNew)).all()
    assert len(rows) == 4  # no copy
    assert {r.methodology_version_id for r in rows} == {world.v1}
    assert db_session.scalar(select(func.count()).select_from(AuditLogNew)) == 0


def test_unknown_or_stale_version(
    client: TestClient, admin_token: str, world: World
) -> None:
    assert (
        client.post(_url(world, version=9), headers=auth(admin_token)).status_code
        == 404
    )
    # planned against version 1, but 2 is the latest now
    stale = client.post(
        _url(world, version=1, dry_run=False), headers=auth(admin_token)
    )
    assert stale.status_code == 409 and "plan the move again" in stale.json()["detail"]
    missing = f"/api/v1/schemas/curation-schemas/{uuid4()}/move-to-version"
    assert client.post(missing, headers=auth(admin_token)).status_code == 404


def test_inactive_scope_rows_are_reported_as_skipped(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_scope: Scope,
    world: World,
) -> None:
    test_scope.is_active = False
    db_session.commit()
    r = client.post(_url(world, dry_run=False), headers=auth(admin_token))
    assert r.status_code == 200, r.text
    assert {i["skipped"] for i in r.json()["items"]} == {INACTIVE_SCOPE}
    assert db_session.scalar(select(func.count()).select_from(AuditLogNew)) == 0
