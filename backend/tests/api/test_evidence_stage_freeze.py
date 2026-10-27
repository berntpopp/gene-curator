"""Evidence writes are frozen outside draft/rejected for every role (4-eyes)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.models import CurationNew, EvidenceItem, Scope, UserNew
from tests.api.scopes.factories import make_member

pytestmark = pytest.mark.unit

PAYLOAD = {
    "evidence_category": "segregation",
    "evidence_type": "genetic",
    "evidence_data": {"pmid": "1", "lod_score": 1},
}


@pytest.mark.parametrize(
    "stage_status", ["submitted", "in_review", "approved", "active"]
)
@pytest.mark.parametrize("who", ["creator", "scope_admin", "app_admin"])
def test_evidence_writes_refused_after_draft(
    client: TestClient,
    db_session: Session,
    test_scope: Scope,
    test_curation: CurationNew,
    test_evidence_item: EvidenceItem,
    curator_token: str,
    admin_token: str,
    who: str,
    stage_status: str,
) -> None:
    if who == "scope_admin":
        sa = UserNew(
            id=uuid4(),
            email="sa-ev@test.com",
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
    h = {"Authorization": f"Bearer {token}"}
    base = f"/api/v1/curations/{test_curation.id}/evidence"

    assert client.post(base, json=PAYLOAD, headers=h).status_code in (400, 403)
    item = f"{base}/{test_evidence_item.id}"
    assert client.put(
        item, json={"evidence_data": {"x": 1}}, headers=h
    ).status_code in (400, 403)
    assert client.delete(item, headers=h).status_code in (400, 403)


def test_app_admin_can_still_edit_draft(
    client: TestClient,
    test_curation: CurationNew,
    admin_token: str,
    evidence_schema: object,
) -> None:
    r = client.post(
        f"/api/v1/curations/{test_curation.id}/evidence",
        json=PAYLOAD,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201
