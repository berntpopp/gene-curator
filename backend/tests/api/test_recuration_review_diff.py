"""A re-curation's first review diffs against the active curation it replaces (#399)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import ActiveCuration, CurationNew, UserNew
from tests.api.test_review_comments_api import _diff, reviewer  # noqa: F401 (fixture)

pytestmark = pytest.mark.unit


def test_a_recurations_first_review_compares_against_the_active_curation(
    client: TestClient,
    db_session: Session,
    reviewer: UserNew,  # noqa: F811
    test_curation: CurationNew,
) -> None:
    """#399: a re-curation is not all new; its baseline is the active curation it replaces."""
    active = CurationNew(
        id=uuid4(),
        scope_id=test_curation.scope_id,
        gene_id=test_curation.gene_id,
        workflow_pair_id=test_curation.workflow_pair_id,
        workflow_stage="active",
        status="active",
        evidence_data={"a": 1, "b": 2},
        created_by=test_curation.created_by,
    )
    db_session.add(active)
    db_session.flush()
    db_session.add(
        ActiveCuration(
            gene_id=active.gene_id, scope_id=active.scope_id, curation_id=active.id
        )
    )
    test_curation.evidence_data = {"a": 1, "b": 3}
    db_session.commit()

    body = _diff(client, reviewer, test_curation)

    assert body["baseline"]["source"] == "active_curation"
    assert body["baseline"]["audit_id"] is None
    assert [(i["path"], i["before"], i["after"]) for i in body["items"]] == [
        ("b", 2, 3)
    ]
