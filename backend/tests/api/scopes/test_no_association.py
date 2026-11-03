"""KGDB #535 on SQLite: a gene-only precuration of the imported bundle is approved on
submit, and a no_association assessment cannot archive an active disease entity."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.workflow_errors import WorkflowConflictError
from app.crud.activation import activate_item
from app.models import PrecurationNew
from app.models.methodology import MethodologyVersion
from app.models.models import CurationStatus, Scope, UserNew, WorkflowStage as S
from tests.api.schema_api_support import auth
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_scope,
    make_user,
)
from tests.unit.test_kgdb_methodology import BUNDLE

pytestmark = pytest.mark.unit
NO_ASSOCIATION = {"relationship_type": "no_association"}


def test_assessment_never_archives_an_active_disease_entity(
    db_session: Session, curator: UserNew, scope_with_admin: Scope
) -> None:
    gene = make_gene(db_session)
    entity = make_curation(
        db_session, scope=scope_with_admin, gene=gene, creator=curator,
        stage=S.ACTIVE, status=CurationStatus.ACTIVE,
    )  # fmt: skip
    entity.entity_key = "MONDO:0000001|AD"
    assessment = make_curation(
        db_session, scope=scope_with_admin, gene=gene, creator=curator,
        evidence_data=NO_ASSOCIATION,
    )  # fmt: skip
    db_session.commit()
    with pytest.raises(WorkflowConflictError, match=str(entity.id)):
        activate_item(db_session, assessment, curator.id)
    db_session.rollback()

    entity.status = CurationStatus.ARCHIVED  # retracted: nothing left to hide
    db_session.commit()
    activate_item(db_session, assessment, curator.id)
    assert assessment.status == CurationStatus.ACTIVE


def test_gene_only_precuration_is_approved_on_submit(
    client: TestClient, db_session: Session, admin_token: str
) -> None:
    scope = make_scope(db_session, name="kidney-genetics")
    imported = client.post(
        "/api/v1/schemas/methodologies/import", json=BUNDLE, headers=auth(admin_token)
    )
    assert imported.status_code == 200, imported.text
    [schema] = [
        i["id"]
        for i in imported.json()["items"]
        if i["name"] == "KGDB No Kidney Association Precuration"
    ]
    author = make_user(db_session, name="Curator agent")
    make_member(db_session, scope, author, "curator")
    pre = client.post(
        "/api/v1/precurations/",
        json={
            "gene_id": str(make_gene(db_session).id), "scope_id": str(scope.id),
            "precuration_schema_id": schema, "evidence_data": NO_ASSOCIATION,
        },
        headers=auth_headers(author),
    )  # fmt: skip
    assert pre.status_code == 201, pre.text
    # PostgreSQL's create trigger pins the published version (042); SQLite has none
    version = db_session.scalar(
        select(MethodologyVersion.id).where(
            MethodologyVersion.schema_id == UUID(schema)
        )
    )
    row = db_session.get(PrecurationNew, UUID(pre.json()["id"]))
    assert row is not None
    row.methodology_version_id = version
    db_session.commit()
    submitted = client.post(
        f"/api/v1/precurations/{pre.json()['id']}/submit",
        json={"lock_version": pre.json()["lock_version"]},
        headers=auth_headers(author),
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "approved"
    cid = submitted.json()["curation_id"]
    draft = client.get(f"/api/v1/curations/{cid}", headers=auth_headers(author))
    assert (draft.status_code, draft.json()["status"]) == (200, "draft")
