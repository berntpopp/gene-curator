"""Synopsis in the export and on the gene page: members always, others only for a
public scope with export_evidence_public on (the evidence rule, #558)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CurationSchema, Gene, Scope, WorkflowPair
from tests.api.test_curation_export import URL, _point, pair  # noqa: F401 (fixture)

pytestmark = pytest.mark.unit
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _with_synopsis(db: Session, wp: WorkflowPair, gene: Gene, scope: Scope) -> None:
    schema = db.get(CurationSchema, wp.curation_schema_id)
    assert schema is not None
    schema.ui_configuration = {"synopsis_field": "evidence_summary"}
    db.commit()
    _point(db, wp, gene, scope, T0, evidence_data={"evidence_summary": "CKD, adult"})


def _export(client: TestClient, headers: dict[str, str] | None = None) -> object:
    r = client.get(URL, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()["items"][0]["synopsis"]


def _gene_page(
    client: TestClient, gene: Gene, headers: dict[str, str] | None = None
) -> object:
    path = "summary/full" if headers else "summary"
    r = client.get(f"/api/v1/genes/{gene.id}/{path}", headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()["scope_summaries"][0]["synopsis"]


def test_members_see_the_synopsis_of_a_private_scope(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,  # noqa: F811
    test_gene: Gene,
    test_scope: Scope,
    viewer_token: str,
) -> None:
    _with_synopsis(db_session, pair, test_gene, test_scope)
    member = {"Authorization": f"Bearer {viewer_token}"}
    assert _export(client, member) == "CKD, adult"
    assert _gene_page(client, test_gene, member) == "CKD, adult"


@pytest.mark.parametrize("public_evidence", [False, True])
def test_anonymous_callers_see_it_only_when_evidence_is_public(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,  # noqa: F811
    test_gene: Gene,
    test_public_scope: Scope,
    public_evidence: bool,
) -> None:
    test_public_scope.export_evidence_public = public_evidence
    _with_synopsis(db_session, pair, test_gene, test_public_scope)
    expected = "CKD, adult" if public_evidence else None
    assert _export(client) == expected
    assert _gene_page(client, test_gene) == expected
