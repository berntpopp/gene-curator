"""PATCH /curations/{id}/draft is frozen outside draft/rejected (4-eyes)."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationNew, Scope, UserNew

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_rls_context():
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


@pytest.mark.parametrize(
    "stage_status", ["submitted", "in_review", "approved", "active"]
)
@pytest.mark.parametrize("who", ["creator", "scope_admin", "app_admin"])
def test_save_draft_blocked_outside_draft_or_rejected(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_curation: CurationNew,
    curator_token: str,
    admin_token: str,
    who: str,
    stage_status: str,
):
    """4-eyes: nobody may change evidence once the curation left draft/rejected."""
    from app.core.security import create_access_token, get_password_hash
    from tests.api.scopes.factories import make_member

    if who == "scope_admin":
        sa = UserNew(
            id=uuid4(),
            email="sa-draft@test.com",
            hashed_password=get_password_hash("x"),
            name="SA",
            role="user",
            is_active=True,
        )
        db_session.add(sa)
        db_session.flush()
        make_member(db_session, test_scope, sa, "admin")
        token = create_access_token(
            data={"sub": str(sa.id), "email": sa.email, "role": "user"}
        )
    else:
        token = curator_token if who == "creator" else admin_token
    test_curation.status = stage_status
    db_session.commit()

    response = client.patch(
        f"/api/v1/curations/{test_curation.id}/draft",
        json={
            "evidence_data": {"tampered": True},
            "lock_version": test_curation.lock_version,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    db_session.refresh(test_curation)
    assert "tampered" not in test_curation.evidence_data


def test_save_draft_allowed_when_rejected(
    client: TestClient,
    db_session: Session,
    test_curation: CurationNew,
    admin_token: str,
):
    test_curation.status = "rejected"
    db_session.commit()
    response = client.patch(
        f"/api/v1/curations/{test_curation.id}/draft",
        json={"evidence_data": {"x": 1}, "lock_version": test_curation.lock_version},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
