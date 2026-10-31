"""#611: a draft save reports what submit will refuse (bad select, date, length and
source cells), as warnings; drafts still never block."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew, CurationSchema, PrecurationNew, WorkflowPair
from app.services.review_guards import save_warnings
from tests.unit.test_evidence_table_cells import RESOURCES

pytestmark = pytest.mark.unit

BAD = {
    "resources": [
        {"type": "patient_organization", "sources": "PMID:1"},
        {"type": "registry", "verified_date": "2026-10-30T12:00:00Z"},
    ],
    "evidence_summary": "x" * 11,
}
PATHS = {
    "resources[0].type",
    "resources[0].sources",
    "resources[1].verified_date",
    "evidence_summary",
}


def _schema(db_session: Session, kind: str) -> CurationSchema:
    schema = CurationSchema(
        id=uuid4(),
        name=f"cells-{kind}",
        version="1.0",
        schema_type=kind,
        field_definitions=RESOURCES["field_definitions"],
        validation_rules={},
        workflow_states={},
        ui_configuration={},
        is_active=True,
        schema_hash=uuid4().hex,
    )
    db_session.add(schema)
    db_session.flush()
    return schema


def _draft(client: TestClient, token: str, kind: str, item) -> set[str]:
    response = client.patch(
        f"/api/v1/{kind}/{item.id}/draft?detail=true",
        json={"evidence_data": BAD, "lock_version": item.lock_version},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return {w["path"] for w in response.json()["warnings"]}


def test_curation_draft_warns_on_bad_cells(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_curation: CurationNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    test_workflow_pair.curation_schema_id = _schema(db_session, "curation").id
    db_session.commit()
    assert _draft(client, admin_token, "curations", test_curation) >= PATHS


def test_precuration_draft_warns_on_bad_cells(
    client: TestClient,
    admin_token: str,
    db_session: Session,
    test_scope,
    test_gene,
    test_user_admin,
) -> None:
    item = PrecurationNew(
        id=uuid4(),
        scope_id=test_scope.id,
        gene_id=test_gene.id,
        precuration_schema_id=_schema(db_session, "precuration").id,
        workflow_stage="precuration",
        evidence_data={},
        created_by=test_user_admin.id,
        updated_by=test_user_admin.id,
    )
    db_session.add(item)
    db_session.commit()
    assert _draft(client, admin_token, "precurations", item) >= PATHS


def test_an_unreadable_pin_leaves_draft_warnings_alone(db_session: Session) -> None:
    item = PrecurationNew(methodology_version_id=uuid4())
    assert save_warnings(db_session, item, BAD, []) == []
