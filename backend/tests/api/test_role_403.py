"""#612: a member without the needed role is told which role it needs; a stranger is not
told anything about the scope."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import CurationSchema, Gene, PrecurationNew, Scope, UserNew

pytestmark = pytest.mark.unit


def _approve(client: TestClient, token: str, item: PrecurationNew) -> str:
    response = client.post(
        f"/api/v1/precurations/{item.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    return response.json()["detail"]


@pytest.fixture
def item(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_admin: UserNew,
    test_precuration_schema: CurationSchema,
) -> PrecurationNew:
    precuration = PrecurationNew(
        id=uuid4(),
        scope_id=test_scope.id,
        gene_id=test_gene.id,
        precuration_schema_id=test_precuration_schema.id,
        workflow_stage="precuration",
        evidence_data={},
        created_by=test_user_admin.id,
        updated_by=test_user_admin.id,
    )
    db_session.add(precuration)
    db_session.commit()
    return precuration


def test_a_curator_is_told_the_reviewer_role_is_missing(
    client: TestClient, curator_token: str, item: PrecurationNew
) -> None:
    detail = _approve(client, curator_token, item)
    assert "curator" in detail and "reviewer" in detail


def test_a_stranger_learns_nothing(
    client: TestClient, db_session: Session, item: PrecurationNew
) -> None:
    stranger = UserNew(
        id=uuid4(),
        email="stranger@example.org",
        name="Stranger",
        hashed_password="x",
        role="user",
        is_active=True,
    )
    db_session.add(stranger)
    db_session.commit()
    token = create_access_token(
        data={"sub": str(stranger.id), "email": stranger.email, "role": "user"}
    )
    assert _approve(client, token, item) == "Not authorized to access this scope"


def test_detail_names_the_role(
    client: TestClient, curator_token: str, item: PrecurationNew
) -> None:
    assert _approve(client, curator_token, item) == (
        "Your scope role curator cannot do curation.review; it needs the admin or "
        "reviewer role"
    )
