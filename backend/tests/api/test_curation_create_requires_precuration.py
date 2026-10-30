"""POST /curations/ needs an approved precuration or an active curation (re-curation)."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationStatus, WorkflowStage
from app.models.models import Gene, PrecurationNew, Scope, UserNew, WorkflowPair
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_scope,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite() -> Iterator[None]:
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


def _create(
    client: TestClient,
    user: UserNew,
    scope: Scope,
    gene: Gene,
    pair: WorkflowPair,
    **extra: str,
) -> int:
    body = {
        "gene_id": str(gene.id),
        "scope_id": str(scope.id),
        "workflow_pair_id": str(pair.id),
        "evidence_data": {},
        **extra,
    }
    response = client.post("/api/v1/curations/", json=body, headers=auth_headers(user))
    if (
        response.status_code == 400
    ):  # refused by the precuration rule, not another check
        assert "approved precuration" in response.json()["detail"]
    return response.status_code


def test_without_precuration_is_rejected(
    client: TestClient,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
) -> None:
    assert (
        _create(client, test_user_admin, test_scope, test_gene, test_workflow_pair)
        == 400
    )


def test_unapproved_precuration_is_rejected(
    client: TestClient,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    test_precuration: PrecurationNew,
) -> None:
    assert (
        _create(
            client,
            test_user_admin,
            test_scope,
            test_gene,
            test_workflow_pair,
            precuration_id=str(test_precuration.id),
        )
        == 400
    )


@pytest.mark.parametrize("linked", [False, True])
def test_approved_precuration_allows_create(
    client: TestClient,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    approved_precuration: PrecurationNew,
    linked: bool,
) -> None:
    extra = {"precuration_id": str(approved_precuration.id)} if linked else {}
    assert (
        _create(
            client, test_user_admin, test_scope, test_gene, test_workflow_pair, **extra
        )
        == 201
    )


def test_active_curation_allows_recuration(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
) -> None:
    make_curation(
        db_session,
        scope=test_scope,
        gene=test_gene,
        creator=test_user_admin,
        stage=WorkflowStage.ACTIVE,
        status=CurationStatus.ACTIVE,
    )
    assert (
        _create(client, test_user_admin, test_scope, test_gene, test_workflow_pair)
        == 201
    )


@pytest.mark.parametrize("other", ["gene", "scope"])
def test_approved_precuration_of_other_gene_or_scope_is_rejected(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    approved_precuration: PrecurationNew,
    other: str,
) -> None:
    """precuration_id must belong to the curation's own gene and scope."""
    gene = make_gene(db_session) if other == "gene" else test_gene
    scope = make_scope(db_session) if other == "scope" else test_scope
    assert (
        _create(
            client,
            test_user_admin,
            scope,
            gene,
            test_workflow_pair,
            precuration_id=str(approved_precuration.id),
        )
        == 400
    )


@pytest.mark.parametrize(
    "open_status",
    [
        CurationStatus.DRAFT,
        CurationStatus.SUBMITTED,
        CurationStatus.IN_REVIEW,
        CurationStatus.REJECTED,
    ],
)
def test_open_curation_blocks_another(
    client: TestClient,
    db_session: Session,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    approved_precuration: PrecurationNew,
    open_status: CurationStatus,
) -> None:
    """One open curation per gene and scope: a second is refused with the open one's id."""
    make_curation(  # the active one being re-curated does not count as open
        db_session,
        scope=test_scope,
        gene=test_gene,
        creator=test_user_admin,
        stage=WorkflowStage.ACTIVE,
        status=CurationStatus.ACTIVE,
    )
    existing = make_curation(
        db_session,
        scope=test_scope,
        gene=test_gene,
        creator=test_user_admin,
        stage=WorkflowStage.CURATION,
        status=open_status,
    )
    body = {
        "gene_id": str(test_gene.id),
        "scope_id": str(test_scope.id),
        "workflow_pair_id": str(test_workflow_pair.id),
        "evidence_data": {},
    }
    response = client.post(
        "/api/v1/curations/", json=body, headers=auth_headers(test_user_admin)
    )
    assert response.status_code == 409
    assert response.json()["detail"]["curation_id"] == str(existing.id)

    existing.status = CurationStatus.ARCHIVED
    db_session.commit()
    assert (
        _create(client, test_user_admin, test_scope, test_gene, test_workflow_pair)
        == 201
    )


def test_create_keeps_the_curator_classification(
    client: TestClient,
    test_user_admin: UserNew,
    test_scope: Scope,
    test_gene: Gene,
    test_workflow_pair: WorkflowPair,
    approved_precuration: PrecurationNew,
) -> None:
    """W9 monkey: a new curation (re-curation prefill) may carry the curator's call."""
    body = {
        "gene_id": str(test_gene.id),
        "scope_id": str(test_scope.id),
        "workflow_pair_id": str(test_workflow_pair.id),
        "precuration_id": str(approved_precuration.id),
        "evidence_data": {},
        "curator_classification": "Strong",
        "curator_classification_rationale": "Expert panel call",
    }
    headers = auth_headers(test_user_admin)
    r = client.post("/api/v1/curations/", json=body, headers=headers)
    assert r.status_code == 201, r.text
    detail = client.get(f"/api/v1/curations/{r.json()['id']}", headers=headers).json()
    assert detail["curator_classification"] == "strong"
    assert detail["curator_classification_rationale"] == "Expert panel call"
    body = {**body, "curator_classification": "nonsense"}
    bad = client.post("/api/v1/curations/", json=body, headers=headers)
    assert bad.status_code == 422, bad.text  # refused before the open-curation check
