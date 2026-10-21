"""Migration 035: reviews has the audit columns the audit trigger reads (assign-reviewer 500)."""

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.main import app
from app.models.models import (
    CurationNew,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.postgres

MIGRATION = Path(__file__).parents[3] / "database/sql/035_reviews_audit_columns.sql"


@pytest.fixture
def api(owner_session: Session) -> Iterator[TestClient]:
    users = owner_session.scalars(select(UserNew)).all()
    app.dependency_overrides[get_db] = lambda: owner_session
    app.dependency_overrides[get_current_active_user] = lambda: users[0]
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _curation(s: Session, stage: str) -> tuple[CurationNew, list[UserNew]]:
    users = list(s.scalars(select(UserNew)).all())
    scope = s.scalars(select(Scope)).first()
    pair = s.scalars(select(WorkflowPair)).first()
    assert scope and pair and len(users) >= 2
    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:999035",
        approved_symbol="AUD035",
        record_hash="0" * 64,
    )
    s.add(gene)
    s.flush()
    c = CurationNew(
        id=uuid4(),
        gene_id=gene.id,
        scope_id=scope.id,
        workflow_pair_id=pair.id,
        workflow_stage=stage,
        status=CurationStatus.DRAFT,
        evidence_data={"n": uuid4().hex},
        created_by=users[0].id,
    )
    s.add(c)
    s.flush()
    return c, users


def test_assign_reviewer_on_curation(api: TestClient, owner_session: Session) -> None:
    c, users = _curation(owner_session, "review")
    r = api.post(
        f"/api/v1/workflow/curation/{c.id}/assign-reviewer",
        json={"reviewer_id": str(users[1].id), "review_type": "peer_review"},
    )
    assert r.status_code == 200, r.text


def test_assign_reviewer_on_precuration_is_rejected_not_500(
    api: TestClient, owner_session: Session
) -> None:
    c, users = _curation(owner_session, "review")
    r = api.post(
        f"/api/v1/workflow/precuration/{c.id}/assign-reviewer",
        json={"reviewer_id": str(users[1].id), "review_type": "peer_review"},
    )
    assert r.status_code == 400


def test_migration_idempotent(owner_session: Session) -> None:
    for _ in range(2):
        owner_session.execute(text(MIGRATION.read_text()))
    cols = owner_session.scalars(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'reviews' AND column_name IN ('created_by', 'updated_by')"
        )
    ).all()
    assert sorted(cols) == ["created_by", "updated_by"]
