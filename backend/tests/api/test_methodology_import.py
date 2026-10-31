"""Idempotent methodology bundle import (#575).

One platform-admin call creates the schemas (v1), the workflow pair and the scope default;
the same bundle again changes nothing; changed content publishes the next version; a dry
run or an invalid bundle writes nothing.
"""

import copy
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select, update
from sqlalchemy.orm import Session

from app.crud.methodology_import import _write_schema
from app.models import AuditLogNew, CurationSchema, Scope, UserNew, WorkflowPair
from app.models.methodology import MethodologyVersion
from app.schemas.schema_repository import CurationSchemaCreate
from tests.api.schema_api_support import auth, schema_payload

pytestmark = pytest.mark.unit

URL = "/api/v1/schemas/methodologies/import"


@pytest.fixture(autouse=True)
def audit_ids() -> Any:
    """audit_log ids by hand (SQLite has no BigInteger autoincrement)."""

    def assign_id(mapper: Any, connection: Any, target: AuditLogNew) -> None:
        top = select(func.coalesce(func.max(AuditLogNew.id), 0))
        target.id = target.id or connection.scalar(top) + 1

    event.listen(AuditLogNew, "before_insert", assign_id)
    yield
    event.remove(AuditLogNew, "before_insert", assign_id)


def bundle(scope_name: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schemas": [
            schema_payload("Kidney Pre", "1", schema_type="precuration"),
            schema_payload("Kidney Cur", "1"),
        ],
        "workflow_pairs": [
            {
                "name": "Kidney Pair",
                "version": "1",
                "precuration_schema": "Kidney Pre",
                "curation_schema": "Kidney Cur",
            }
        ],
    }
    if scope_name:
        out["scope_default"] = {
            "scope_name": scope_name,
            "workflow_pair": "Kidney Pair",
        }
    return out


def _actions(body: dict[str, Any]) -> list[tuple[str, str, Any]]:
    return [(i["kind"], i["action"], i["methodology_version"]) for i in body["items"]]


def _count(db: Session, model: Any) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def test_import_creates_then_is_a_no_op(
    client: TestClient, db_session: Session, admin_token: str, test_scope: Scope
) -> None:
    r = client.post(URL, json=bundle(test_scope.name), headers=auth(admin_token))
    assert r.status_code == 200, r.text
    assert r.json()["errors"] == []
    assert _actions(r.json()) == [
        ("schema", "create", 1),
        ("schema", "create", 1),
        ("workflow_pair", "create", None),
        ("scope_default", "update", None),
    ]
    pair = db_session.get(WorkflowPair, r.json()["items"][2]["id"])
    assert pair is not None and pair.curation_schema_id is not None
    db_session.refresh(test_scope)
    assert test_scope.default_workflow_pair_id == pair.id
    counts = [
        _count(db_session, m)
        for m in (CurationSchema, MethodologyVersion, WorkflowPair)
    ]

    again = client.post(URL, json=bundle(test_scope.name), headers=auth(admin_token))
    assert again.status_code == 200, again.text
    assert _actions(again.json()) == [
        ("schema", "unchanged", 1),
        ("schema", "unchanged", 1),
        ("workflow_pair", "unchanged", None),
        ("scope_default", "unchanged", None),
    ]
    assert [i["id"] for i in again.json()["items"]] == [
        i["id"] for i in r.json()["items"]
    ]
    assert counts == [
        _count(db_session, m)
        for m in (CurationSchema, MethodologyVersion, WorkflowPair)
    ]


def test_changed_content_publishes_a_new_version_and_keeps_the_old(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    first = client.post(URL, json=bundle(), headers=auth(admin_token)).json()
    schema_id = first["items"][1]["id"]
    v1 = db_session.scalars(
        select(MethodologyVersion).where(MethodologyVersion.schema_id == schema_id)
    ).one()
    old_snapshot = copy.deepcopy(v1.snapshot)

    changed = bundle()
    changed["schemas"][1]["field_definitions"] = {
        "gene": {"type": "text", "label": "HGNC"}
    }
    plan = client.post(f"{URL}?dry_run=true", json=changed, headers=auth(admin_token))
    assert _actions(plan.json())[:2] == [
        ("schema", "unchanged", 1),
        ("schema", "new_version", 2),
    ]
    assert _count(db_session, MethodologyVersion) == 2  # the dry run wrote nothing

    r = client.post(URL, json=changed, headers=auth(admin_token))
    assert r.status_code == 200, r.text
    assert _actions(r.json())[:3] == [
        ("schema", "unchanged", 1),
        ("schema", "new_version", 2),
        ("workflow_pair", "unchanged", None),
    ]
    versions = db_session.scalars(
        select(MethodologyVersion)
        .where(MethodologyVersion.schema_id == schema_id)
        .order_by(MethodologyVersion.version)
    ).all()
    assert [v.version for v in versions] == [1, 2]
    assert versions[0].snapshot == old_snapshot
    # an editor that loaded the schema before the import now saves a stale copy (#282)
    stale = client.put(
        f"/api/v1/schemas/curation-schemas/{schema_id}",
        json={"description": "editor", "lock_version": 0},
        headers=auth(admin_token),
    )
    assert stale.status_code == 409, stale.text
    assert versions[1].snapshot["field_definitions"]["gene"]["label"] == "HGNC"


def test_dry_run_plans_creates_without_writing(
    client: TestClient, db_session: Session, admin_token: str, test_scope: Scope
) -> None:
    r = client.post(
        f"{URL}?dry_run=true", json=bundle(test_scope.name), headers=auth(admin_token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["dry_run"] is True
    assert [i["action"] for i in r.json()["items"]] == ["create"] * 3 + ["update"]
    assert all(i["id"] is None for i in r.json()["items"][:3])
    assert _count(db_session, CurationSchema) == 0


def _invalid() -> dict[str, Any]:
    out = bundle("no-such-scope")
    out["schemas"][1]["workflow_states"] = {"review": {"reviewers_required": 9}}
    out["schemas"].append(schema_payload("Kidney Pre", "2", schema_type="precuration"))
    out["schemas"][0]["is_active"] = False
    out["workflow_pairs"].append(dict(out["workflow_pairs"][0]))
    out["workflow_pairs"].append(
        {"name": "Bad", "version": "1", "precuration_schema": "Kidney Cur",
         "curation_schema": "Missing"}
    )  # fmt: skip
    return out


@pytest.mark.parametrize(
    "error",
    [
        "schema Kidney Cur: ",  # the publish gate's report
        "schema Kidney Pre: appears more than once",
        "workflow pair Bad: precuration_schema Kidney Cur is a curation schema",
        "workflow pair Bad: no bundle schema Missing",
        "scope_default: no scope no-such-scope",
        "workflow pair Kidney Pair: appears more than once",
        "workflow pair Kidney Pair: schema Kidney Pre is inactive",
    ],
)
def test_invalid_bundle_is_refused_and_writes_nothing(
    client: TestClient, db_session: Session, admin_token: str, error: str
) -> None:
    dry = client.post(f"{URL}?dry_run=true", json=_invalid(), headers=auth(admin_token))
    assert dry.status_code == 200 and any(
        e.startswith(error) for e in dry.json()["errors"]
    )
    r = client.post(URL, json=_invalid(), headers=auth(admin_token))
    assert r.status_code == 422, r.text
    assert any(e.startswith(error) for e in r.json()["detail"]["errors"])
    assert _count(db_session, CurationSchema) == 0


def test_existing_schema_of_another_type_is_refused(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    client.post(URL, json=bundle(), headers=auth(admin_token))
    swapped = bundle()
    swapped["schemas"][0]["schema_type"] = "curation"
    swapped["workflow_pairs"] = []
    r = client.post(URL, json=swapped, headers=auth(admin_token))
    assert r.status_code == 422
    assert "schema Kidney Pre: is a precuration schema" in r.json()["detail"]["errors"]


def test_repointed_pair_is_updated(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    client.post(URL, json=bundle(), headers=auth(admin_token))
    moved = bundle()
    moved["schemas"].append(schema_payload("Kidney Cur B", "1"))
    moved["workflow_pairs"][0]["curation_schema"] = "Kidney Cur B"
    r = client.post(URL, json=moved, headers=auth(admin_token))
    assert r.status_code == 200, r.text
    pair_item = r.json()["items"][3]
    assert pair_item["action"] == "update"
    pair = db_session.get(WorkflowPair, pair_item["id"])
    assert (
        pair is not None and str(pair.curation_schema_id) == r.json()["items"][2]["id"]
    )


def test_only_platform_admins_import(
    client: TestClient, db_session: Session, curator_token: str
) -> None:
    r = client.post(URL, json=bundle(), headers=auth(curator_token))
    assert r.status_code == 403, r.text
    assert _count(db_session, CurationSchema) == 0


def _cur_row(db: Session) -> CurationSchema:
    return db.scalars(
        select(CurationSchema).where(CurationSchema.name == "Kidney Cur")
    ).one()


def _edit_unpublished(db: Session, label: str) -> None:
    """What a UI save (PUT) does: change the row, publish nothing."""
    row = _cur_row(db)
    row.field_definitions = {"gene": {"type": "text", "label": label}}
    db.commit()


def test_unpublished_edits_are_refused_not_overwritten(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    client.post(URL, json=bundle(), headers=auth(admin_token))
    _edit_unpublished(db_session, "UI edit")
    r = client.post(URL, json=bundle(), headers=auth(admin_token))
    assert r.status_code == 422, r.text
    assert any(
        e.startswith("schema Kidney Cur: has unpublished edits")
        for e in r.json()["detail"]["errors"]
    )
    db_session.expire_all()
    assert _cur_row(db_session).field_definitions["gene"]["label"] == "UI edit"


def test_dry_run_labels_a_refused_schema_refused_not_create(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    client.post(URL, json=bundle(), headers=auth(admin_token))
    _edit_unpublished(db_session, "UI edit")
    plan = client.post(f"{URL}?dry_run=true", json=bundle(), headers=auth(admin_token))
    assert plan.status_code == 200, plan.text
    actions = {i["name"]: i["action"] for i in plan.json()["items"]}
    assert actions["Kidney Cur"] == "refused"


def test_unpublished_row_equal_to_the_bundle_is_published(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    client.post(URL, json=bundle(), headers=auth(admin_token))
    _edit_unpublished(db_session, "HGNC")
    changed = bundle()
    changed["schemas"][1]["field_definitions"] = {
        "gene": {"type": "text", "label": "HGNC"}
    }
    r = client.post(URL, json=changed, headers=auth(admin_token))
    assert r.status_code == 200, r.text
    assert _actions(r.json())[1] == ("schema", "new_version", 2)
    latest = db_session.scalars(
        select(MethodologyVersion)
        .where(MethodologyVersion.schema_id == _cur_row(db_session).id)
        .order_by(MethodologyVersion.version.desc())
    ).first()
    assert latest is not None and latest.version == 2
    assert latest.snapshot["field_definitions"]["gene"]["label"] == "HGNC"


def test_inactive_existing_schema_in_a_pair_is_refused(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    client.post(URL, json=bundle(), headers=auth(admin_token))
    _cur_row(db_session).is_active = False
    db_session.commit()
    r = client.post(URL, json=bundle(), headers=auth(admin_token))
    assert r.status_code == 422, r.text
    assert (
        "workflow pair Kidney Pair: schema Kidney Cur is inactive"
        in (r.json()["detail"]["errors"])
    )


def test_bundle_lists_are_capped(client: TestClient, admin_token: str) -> None:
    big = bundle()
    big["schemas"] = [schema_payload(f"S{i}", "1") for i in range(51)]
    assert client.post(URL, json=big, headers=auth(admin_token)).status_code == 422
    big = bundle()
    big["workflow_pairs"] = big["workflow_pairs"] * 51
    assert client.post(URL, json=big, headers=auth(admin_token)).status_code == 422


def test_each_import_is_audited_once(
    client: TestClient,
    db_session: Session,
    admin_token: str,
    test_user_admin: UserNew,
) -> None:
    client.post(f"{URL}?dry_run=true", json=bundle(), headers=auth(admin_token))
    audited = select(AuditLogNew).where(AuditLogNew.change_type == "methodology_import")
    assert db_session.scalars(audited).all() == []
    r = client.post(URL, json=bundle(), headers=auth(admin_token))
    client.post(URL, json=bundle(), headers=auth(admin_token))  # a no-op, still audited
    rows = db_session.scalars(audited.order_by(AuditLogNew.id)).all()
    assert len(rows) == 2
    assert rows[0].user_id == test_user_admin.id
    assert rows[0].changes == {"items": r.json()["items"]}


def test_reimport_writes_a_changed_description(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    """Description is not versioned content: an unchanged schema and a new version both
    take the bundle's description."""
    first = client.post(URL, json=bundle(), headers=auth(admin_token)).json()
    changed = bundle()
    for spec in changed["schemas"]:
        spec["description"] = f"{spec['name']} approved"
    changed["schemas"][1]["field_definitions"] = {
        "gene": {"type": "text", "label": "HGNC"}
    }
    dry = client.post(f"{URL}?dry_run=true", json=changed, headers=auth(admin_token))
    plan = [("schema", "update", 1), ("schema", "new_version", 2)]
    assert _actions(dry.json())[:2] == plan  # the dry run reports what the apply writes
    r = client.post(URL, json=changed, headers=auth(admin_token))
    assert _actions(r.json())[:2] == plan
    for item in first["items"][:2]:
        row = db_session.get(CurationSchema, item["id"])
        assert row is not None
        db_session.refresh(row)
        assert row.description == f"{row.name} approved"
        assert row.lock_version == 1  # an editor's stale copy is refused (#282)


def test_import_bumps_the_stored_lock_version_not_a_stale_copy(
    client: TestClient, db_session: Session, admin_token: str, test_user_admin: UserNew
) -> None:
    """An editor save between loading the row and the import's write is not lost (#282)."""
    first = client.post(URL, json=bundle(), headers=auth(admin_token)).json()
    row = db_session.get(CurationSchema, first["items"][1]["id"])
    assert row is not None and row.lock_version == 0
    db_session.execute(  # an editor saved meanwhile; the loaded row still says 0
        update(CurationSchema)
        .where(CurationSchema.id == row.id)
        .values(lock_version=5)
        .execution_options(synchronize_session=False)
    )
    changed = bundle()["schemas"][1]
    changed["field_definitions"] = {"gene": {"type": "text", "label": "HGNC"}}
    _write_schema(
        db_session, CurationSchemaCreate(**changed), row, 2, test_user_admin.id
    )
    db_session.refresh(row)
    assert row.lock_version == 6


def test_the_bundles_other_pairs_become_allowed_in_the_default_scope(
    client: TestClient, db_session: Session, admin_token: str, test_scope: Scope
) -> None:
    """#284: a scope uses its default pair plus its allowed list; a bundle's second pair
    (e.g. susceptibility next to Mendelian) is selectable there after the import."""
    body = bundle(test_scope.name)
    body["workflow_pairs"].append({**body["workflow_pairs"][0], "name": "Kidney Risk"})
    r = client.post(URL, json=body, headers=auth(admin_token))
    assert r.status_code == 200, r.text
    risk = r.json()["items"][3]["id"]
    db_session.refresh(test_scope)
    assert [str(i) for i in test_scope.allowed_workflow_pair_ids] == [risk]
    again = client.post(URL, json=body, headers=auth(admin_token))
    assert again.status_code == 200, again.text
    db_session.refresh(test_scope)
    assert [str(i) for i in test_scope.allowed_workflow_pair_ids] == [risk]
