from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationNew


class TestListExcludeOwn:
    """exclude_own backs the cheap review-badge count (limit=1, use total)."""

    def test_exclude_own_drops_callers_curations(
        self,
        client: TestClient,
        admin_token: str,
        db_session: Session,
        test_scope,
        test_gene,
        test_workflow_pair,
        test_user_curator,
        test_user_admin,
    ):
        for creator in (test_user_curator, test_user_admin):
            db_session.add(
                CurationNew(
                    id=uuid4(),
                    scope_id=test_scope.id,
                    gene_id=test_gene.id,
                    workflow_pair_id=test_workflow_pair.id,
                    workflow_stage="review",
                    status="in_review",
                    evidence_data={},
                    created_by=creator.id,
                )
            )
        db_session.commit()
        headers = {"Authorization": f"Bearer {admin_token}"}
        url = "/api/v1/curations/?curation_status=in_review&limit=1"

        assert client.get(url, headers=headers).json()["total"] == 2
        data = client.get(url + "&exclude_own=true", headers=headers).json()
        assert data["total"] == 1
        assert len(data["curations"]) == 1
