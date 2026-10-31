"""Capability matrix as data and scope-owned configuration (#284).

Each configuration capability against viewer, curator, reviewer, the scope's admin, another
scope's admin and a platform admin; allowed workflow pairs; audit rows. RLS: the Postgres lane
(tests/postgres/test_capability_matrix_rls.py).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import capabilities as caps
from app.crud.schema_repository import SNAPSHOT_KEYS
from app.models import (
    AuditLogNew,
    CurationSchema,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)
from app.models.methodology import MethodologyVersion
from app.models.permissions import RoleCapability
from tests.api.schema_api_support import insert_pair, insert_schema, schema_payload
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit

SCHEMAS = "/api/v1/schemas/curation-schemas"
PAIRS = "/api/v1/schemas/workflow-pairs"
ROLES = ["viewer", "curator", "reviewer", "scope_admin", "other_admin", "platform"]
CONFIGURERS = {"scope_admin", "platform"}


@dataclass
class World:
    scope: Scope
    other: Scope
    users: dict[str, UserNew]
    pre: UUID  # global precuration schema
    cur: UUID  # global curation schema


@pytest.fixture
def w(db_session: Session) -> World:
    scope, other = make_scope(db_session), make_scope(db_session)
    users = {r: make_user(db_session) for r in ROLES[:5]}
    users["platform"] = make_user(db_session, role="admin")
    for role in ("viewer", "curator", "reviewer"):
        make_member(db_session, scope, users[role], role)
    make_member(db_session, scope, users["scope_admin"], "admin")
    make_member(db_session, other, users["other_admin"], "admin")
    pre = insert_schema(db_session, name=f"pre-{uuid4()}", schema_type="precuration")
    cur = insert_schema(db_session, name=f"cur-{uuid4()}")
    return World(scope, other, users, pre.id, cur.id)


def _owned_schema(db: Session, owner: UUID) -> UUID:
    schema = insert_schema(db, name=f"owned-{uuid4()}")
    schema.owner_scope_id = owner
    db.add(MethodologyVersion(schema_id=schema.id, version=1, snapshot={}))
    db.commit()
    return schema.id


def _create_schema(c: TestClient, db: Session, w: World, h: dict) -> Response:
    payload = schema_payload(name=f"n-{uuid4()}", owner_scope_id=str(w.scope.id))
    return c.post(SCHEMAS, headers=h, json=payload)


def _derive(c: TestClient, db: Session, w: World, h: dict) -> Response:
    snapshot = {k: getattr(_schema(db, w.cur), k) for k in SNAPSHOT_KEYS}
    version = MethodologyVersion(schema_id=w.cur, version=1, snapshot=snapshot)
    db.add(version)
    db.commit()
    body = {"name": f"d-{uuid4()}", "version": "1", "owner_scope_id": str(w.scope.id)}
    return c.post(
        f"{SCHEMAS}/{w.cur}/versions/{version.id}/derive", headers=h, json=body
    )


def _publish(c: TestClient, db: Session, w: World, h: dict) -> Response:
    return c.post(f"{SCHEMAS}/{_owned_schema(db, w.scope.id)}/versions", headers=h)


def _edit(c: TestClient, db: Session, w: World, h: dict) -> Response:
    url = f"{SCHEMAS}/{_owned_schema(db, w.scope.id)}"
    return c.put(url, headers=h, json={"description": "edited", "lock_version": 0})


def _create_pair(c: TestClient, db: Session, w: World, h: dict) -> Response:
    body = {
        "name": f"p-{uuid4()}",
        "version": "1",
        "precuration_schema_id": str(w.pre),
        "curation_schema_id": str(w.cur),
        "owner_scope_id": str(w.scope.id),
    }
    return c.post(PAIRS, headers=h, json=body)


def _allow_pairs(c: TestClient, db: Session, w: World, h: dict) -> Response:
    pair = insert_pair(db, _schema(db, w.pre), _schema(db, w.cur), name=f"a-{uuid4()}")
    url = f"/api/v1/scopes/{w.scope.id}/workflow-pairs"
    return c.put(url, headers=h, json={"workflow_pair_ids": [str(pair.id)]})


def _schema(db: Session, schema_id: UUID) -> CurationSchema:
    return db.get_one(CurationSchema, schema_id)


def _global_schema(c: TestClient, db: Session, w: World, h: dict) -> Response:
    return c.post(SCHEMAS, headers=h, json=schema_payload(name=f"g-{uuid4()}"))


Call = Callable[[TestClient, Session, World, dict], Response]
SCOPE_CONFIG: dict[str, Call] = {
    caps.METHODOLOGY_DERIVE + " (create)": _create_schema,
    caps.METHODOLOGY_DERIVE: _derive,
    caps.METHODOLOGY_PUBLISH: _publish,
    caps.METHODOLOGY_EDIT: _edit,
    caps.WORKFLOW_CREATE: _create_pair,
    caps.WORKFLOW_ASSIGN: _allow_pairs,
}


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("capability", [*SCOPE_CONFIG, caps.PLATFORM])
def test_configuration_capability_by_role(
    client: TestClient, db_session: Session, w: World, capability: str, role: str
) -> None:
    call = SCOPE_CONFIG.get(capability, _global_schema)
    response = call(client, db_session, w, auth_headers(w.users[role]))
    allowed = role == "platform" or (
        role in CONFIGURERS and capability != caps.PLATFORM
    )
    assert (response.status_code < 300) == allowed, response.text
    if not allowed:
        assert response.status_code == 403


def test_scope_admin_cannot_configure_another_scope(
    client: TestClient, db_session: Session, w: World
) -> None:
    h = auth_headers(w.users["other_admin"])
    owned = _owned_schema(db_session, w.scope.id)
    assert client.post(f"{SCHEMAS}/{owned}/versions", headers=h).status_code == 403
    # its own scope's pair may not reuse another scope's schema
    body = {
        "name": f"p-{uuid4()}",
        "version": "1",
        "precuration_schema_id": str(w.pre),
        "curation_schema_id": str(owned),
        "owner_scope_id": str(w.other.id),
    }
    assert client.post(PAIRS, headers=h, json=body).status_code == 403


def test_scope_admin_cannot_derive_another_scopes_schema_into_its_own(
    client: TestClient, db_session: Session, w: World
) -> None:
    owned = _owned_schema(db_session, w.scope.id)
    version = db_session.scalar(
        select(MethodologyVersion.id).where(MethodologyVersion.schema_id == owned)
    )
    body = {"name": f"d-{uuid4()}", "version": "1", "owner_scope_id": str(w.other.id)}
    url = f"{SCHEMAS}/{owned}/versions/{version}/derive"
    response = client.post(url, headers=auth_headers(w.users["other_admin"]), json=body)
    assert response.status_code == 403, response.text


@pytest.mark.parametrize(("role", "status"), [("viewer", 403), ("other_admin", 403)])
def test_only_the_author_or_a_curator_assigns_a_curation_reviewer(
    client: TestClient, db_session: Session, w: World, role: str, status: int
) -> None:
    """As RLS 061: author or curation.edit in the scope; viewers get 403, not a 500."""
    author = w.users["curator"]
    curation = make_curation(
        db_session, scope=w.scope, gene=make_gene(db_session), creator=author
    )
    url = f"/api/v1/workflow/curation/{curation.id}/assign-reviewer"
    body = {"reviewer_id": str(w.users["reviewer"].id)}
    response = client.post(url, headers=auth_headers(w.users[role]), json=body)
    assert response.status_code == status, response.text


def test_permission_relevant_actions_are_audited(
    client: TestClient, db_session: Session, w: World
) -> None:
    admin = w.users["scope_admin"]
    created = _create_pair(client, db_session, w, auth_headers(admin))
    assert created.status_code == 200, created.text
    row = db_session.scalar(
        select(AuditLogNew).where(AuditLogNew.entity_id == UUID(created.json()["id"]))
    )
    assert row is not None
    assert (row.user_id, row.operation, row.scope_id) == (
        admin.id,
        caps.WORKFLOW_CREATE,
        w.scope.id,
    )
    assert row.changes == {"capability": caps.WORKFLOW_CREATE}


def test_the_matrix_is_data(db_session: Session, w: World) -> None:
    """Removing a row from role_capabilities takes the capability away."""
    admin = w.users["scope_admin"]
    caps.require(db_session, admin, w.scope.id, caps.WORKFLOW_CREATE)
    row = db_session.get(RoleCapability, ("admin", caps.WORKFLOW_CREATE))
    db_session.delete(row)
    db_session.commit()
    try:
        with pytest.raises(HTTPException) as error:
            caps.require(db_session, admin, w.scope.id, caps.WORKFLOW_CREATE)
        assert error.value.status_code == 403
    finally:
        db_session.add(RoleCapability(role="admin", capability=caps.WORKFLOW_CREATE))
        db_session.commit()


def test_seed_matches_the_default_matrix(db_session: Session) -> None:
    rows = db_session.execute(select(RoleCapability.role, RoleCapability.capability))
    assert set(rows) == {
        (role.value, cap) for role, held in caps.DEFAULT_MATRIX.items() for cap in held
    }


# -----------------------------------------------------------------------------
# Allowed workflow pairs
# -----------------------------------------------------------------------------


@pytest.fixture
def pairs(db_session: Session, w: World) -> tuple[WorkflowPair, WorkflowPair]:
    pre, cur = _schema(db_session, w.pre), _schema(db_session, w.cur)
    default = insert_pair(db_session, pre, cur, name=f"default-{uuid4()}")
    alt_pre = insert_schema(
        db_session, name=f"alt-{uuid4()}", schema_type="precuration"
    )
    extra = insert_pair(db_session, alt_pre, cur, name=f"extra-{uuid4()}")
    w.scope.default_workflow_pair_id = default.id
    db_session.commit()
    return default, extra


def test_create_refuses_a_pair_the_scope_does_not_allow(
    client: TestClient,
    db_session: Session,
    w: World,
    pairs: tuple[WorkflowPair, WorkflowPair],
) -> None:
    _, extra = pairs
    h = auth_headers(w.users["curator"])
    gene = make_gene(db_session)
    curation = {
        "gene_id": str(gene.id),
        "scope_id": str(w.scope.id),
        "workflow_pair_id": str(extra.id),
        "evidence_data": {},
    }
    refused = client.post("/api/v1/curations/", headers=h, json=curation)
    assert refused.status_code == 422, refused.text
    assert "not allowed in this scope" in refused.json()["detail"]
    precuration = {
        "gene_id": str(gene.id),
        "scope_id": str(w.scope.id),
        "precuration_schema_id": str(extra.precuration_schema_id),
    }
    refused = client.post("/api/v1/precurations/", headers=h, json=precuration)
    assert refused.status_code == 422, refused.text

    # the scope admin allows it: the same create now passes the check
    url = f"/api/v1/scopes/{w.scope.id}/workflow-pairs"
    admin = auth_headers(w.users["scope_admin"])
    set_ = client.put(url, headers=admin, json={"workflow_pair_ids": [str(extra.id)]})
    assert set_.status_code == 200, set_.text
    assert set_.json()["allowed_workflow_pair_ids"] == [str(extra.id)]
    created = client.post("/api/v1/precurations/", headers=h, json=precuration)
    assert created.status_code == 201, created.text


def test_allowed_pairs_must_be_global_or_the_scopes_own(
    client: TestClient,
    db_session: Session,
    w: World,
    pairs: tuple[WorkflowPair, WorkflowPair],
) -> None:
    _, extra = pairs
    extra.owner_scope_id = w.other.id
    db_session.commit()
    url = f"/api/v1/scopes/{w.scope.id}/workflow-pairs"
    h = auth_headers(w.users["scope_admin"])
    for ids in ([str(extra.id)], [str(uuid4())]):
        refused = client.put(url, headers=h, json={"workflow_pair_ids": ids})
        assert refused.status_code == 422, refused.text
    # and the default pair too
    patch = client.patch(
        f"/api/v1/scopes/{w.scope.id}",
        headers=h,
        json={"default_workflow_pair_id": str(extra.id)},
    )
    assert patch.status_code == 422, patch.text


# -----------------------------------------------------------------------------
# Scope management (review of #604)
# -----------------------------------------------------------------------------


def test_scope_admin_reactivates_its_deactivated_scope(
    client: TestClient, w: World
) -> None:
    """API and RLS agree: scope management works on an inactive scope."""
    h, url = auth_headers(w.users["scope_admin"]), f"/api/v1/scopes/{w.scope.id}"
    assert client.patch(url, headers=h, json={"is_active": False}).status_code == 200
    assert client.get(f"{url}/members", headers=h).status_code == 200
    back = client.patch(url, headers=h, json={"is_active": True})
    assert back.status_code == 200, back.text
    assert back.json()["is_active"] is True


def test_curation_writes_stay_refused_in_an_inactive_scope(
    db_session: Session, w: World
) -> None:
    w.scope.is_active = False
    db_session.commit()
    with pytest.raises(HTTPException):
        caps.require(db_session, w.users["curator"], w.scope.id, caps.EDIT)


def test_only_platform_admins_delete_scopes(
    client: TestClient, db_session: Session, w: World
) -> None:
    """RLS lets platform admins delete scopes, so the API does too, creators included."""
    w.scope.created_by = w.users["scope_admin"].id
    db_session.commit()
    url = f"/api/v1/scopes/{w.scope.id}"
    creator = client.delete(url, headers=auth_headers(w.users["scope_admin"]))
    assert creator.status_code == 403, creator.text
    gone = client.delete(url, headers=auth_headers(w.users["platform"]))
    assert gone.status_code == 204, gone.text


def test_deleting_a_scope_does_not_turn_its_items_into_global_templates(
    client: TestClient, db_session: Session, w: World
) -> None:
    schema_id = _owned_schema(db_session, w.scope.id)
    pair = insert_pair(
        db_session, _schema(db_session, w.pre), _schema(db_session, w.cur)
    )
    pair.owner_scope_id = w.scope.id
    db_session.commit()
    url = f"/api/v1/scopes/{w.scope.id}"
    assert (
        client.delete(url, headers=auth_headers(w.users["platform"])).status_code == 204
    )
    db_session.expire_all()
    assert db_session.get_one(CurationSchema, schema_id).is_active is False
    assert db_session.get_one(WorkflowPair, pair.id).is_active is False


def test_a_new_scope_cannot_default_to_another_scopes_pair(
    client: TestClient, db_session: Session, w: World
) -> None:
    pair = insert_pair(
        db_session, _schema(db_session, w.pre), _schema(db_session, w.cur)
    )
    pair.owner_scope_id = w.other.id
    db_session.commit()
    body = {
        "name": f"new-{uuid4().hex[:8]}",
        "display_name": "New",
        "default_workflow_pair_id": str(pair.id),
    }
    created = client.post(
        "/api/v1/scopes/", headers=auth_headers(w.users["curator"]), json=body
    )
    assert created.status_code == 400, created.text


def _ops(db: Session, scope_id: UUID) -> list[str]:
    rows = db.scalars(
        select(AuditLogNew.operation)
        .where(AuditLogNew.scope_id == scope_id)
        .order_by(AuditLogNew.id)
    )
    return list(rows)


def test_member_changes_and_default_pair_changes_are_audited(
    client: TestClient,
    db_session: Session,
    w: World,
    pairs: tuple[WorkflowPair, WorkflowPair],
) -> None:
    h = auth_headers(w.users["scope_admin"])
    members = f"/api/v1/scopes/{w.scope.id}/members/{w.users['viewer'].id}"
    changed = client.patch(members, headers=h, json={"role": "curator"})
    assert changed.status_code == 200, changed.text
    assert client.delete(members, headers=h).status_code == 204
    _, extra = pairs
    patch = client.patch(
        f"/api/v1/scopes/{w.scope.id}",
        headers=h,
        json={"default_workflow_pair_id": str(extra.id)},
    )
    assert patch.status_code == 200, patch.text
    assert _ops(db_session, w.scope.id) == [
        caps.MANAGE_MEMBERS,
        caps.MANAGE_MEMBERS,
        caps.MANAGE_SCOPE,
    ]


# #604 review: the audit row commits with its change; a failed insert leaves no
# unaudited change behind (it used to commit after it)
def _state(db: Session, w: World) -> tuple[Any, ...]:
    db.expire_all()
    counts = tuple(
        db.scalar(select(func.count()).select_from(m))
        for m in (CurationSchema, MethodologyVersion, WorkflowPair)
    )
    edited = db.scalar(
        select(func.count()).where(CurationSchema.description == "edited")
    )
    roles = sorted(
        (str(m.user_id), str(m.role), m.is_active)
        for m in db.scalars(
            select(ScopeMembership).where(ScopeMembership.scope_id == w.scope.id)
        )
    )
    scope = w.scope
    return (
        *counts,
        edited,
        roles,
        scope.default_workflow_pair_id,
        sorted(map(str, scope.allowed_workflow_pair_ids)),
    )


class AuditDownError(Exception):
    pass


def _broken(*_: Any, **__: Any) -> None:
    raise AuditDownError


def _member_role(c: TestClient, db: Session, w: World, h: dict) -> Any:
    url = f"/api/v1/scopes/{w.scope.id}/members/{w.users['viewer'].id}"
    return c.patch(url, headers=h, json={"role": "curator"})


def _member_remove(c: TestClient, db: Session, w: World, h: dict) -> Any:
    url = f"/api/v1/scopes/{w.scope.id}/members/{w.users['viewer'].id}"
    return c.delete(url, headers=h)


CALLS: dict[str, Call] = {
    **SCOPE_CONFIG,
    "member role": _member_role,
    "member remove": _member_remove,
}


@pytest.mark.parametrize("action", [*CALLS, "default pair"])
def test_a_failed_audit_insert_rolls_the_change_back(
    client: TestClient,
    db_session: Session,
    w: World,
    pairs: tuple[WorkflowPair, WorkflowPair],
    monkeypatch: pytest.MonkeyPatch,
    action: str,
) -> None:
    h = auth_headers(w.users["scope_admin"])
    if action == "default pair":
        call: Call = lambda c, db, w, h: c.patch(  # noqa: E731
            f"/api/v1/scopes/{w.scope.id}",
            headers=h,
            json={"default_workflow_pair_id": str(pairs[1].id)},
        )
    else:
        call = CALLS[action]
    seen: list[tuple[Any, ...]] = []
    send = client.request

    def snapshot_then_send(*a: Any, **k: Any) -> Any:
        seen.append(_state(db_session, w))  # after the call's own setup rows
        return send(*a, **k)

    monkeypatch.setattr(client, "request", snapshot_then_send)
    monkeypatch.setattr("app.core.capabilities.AuditLogNew", _broken)
    with pytest.raises(AuditDownError):
        call(client, db_session, w, h)
    db_session.rollback()
    assert _state(db_session, w) == seen[-1], action


def test_audited_changes_still_commit(
    client: TestClient, db_session: Session, w: World
) -> None:
    h = auth_headers(w.users["scope_admin"])
    for action, call in CALLS.items():
        r = call(client, db_session, w, h)
        assert r.status_code in (200, 201, 204), (action, r.text)
