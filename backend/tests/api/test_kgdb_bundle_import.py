"""The KGDB bundle through the import endpoint as platform admin: a dry run writes nothing,
the import creates four schemas (v1), two pairs and the kidney-genetics default, and the
same file again is a no-op."""

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CurationSchema, Scope, WorkflowPair
from tests.api.schema_api_support import auth
from tests.api.test_methodology_import import audit_ids
from tests.unit.test_kgdb_methodology import BUNDLE

__all__ = ["audit_ids"]
URL = "/api/v1/schemas/methodologies/import"


def _post(client: TestClient, token: str, **params: Any) -> dict[str, Any]:
    r = client.post(URL, json=BUNDLE, params=params, headers=auth(token))
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    assert body["errors"] == []
    return body


def _plan(body: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(i["kind"], i["name"], i["action"]) for i in body["items"]]


def test_kgdb_bundle_imports_once(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    scope = Scope(id=uuid4(), name="kidney-genetics", display_name="Kidney Genetics")
    db_session.add(scope)
    db_session.commit()
    count = select(func.count()).select_from(CurationSchema)

    dry = _post(client, admin_token, dry_run=True)
    assert {action for _, _, action in _plan(dry)} == {"create", "update"}
    assert db_session.scalar(count) == 0

    body = _post(client, admin_token)
    assert _plan(body) == _plan(dry)
    assert [i["methodology_version"] for i in body["items"][:4]] == [1, 1, 1, 1]
    assert db_session.scalar(count) == 4
    db_session.refresh(scope)
    pair = db_session.get(WorkflowPair, scope.default_workflow_pair_id)
    assert pair is not None and pair.name == "KGDB Mendelian"

    again = _post(client, admin_token)
    assert {action for _, _, action in _plan(again)} == {"unchanged"}
