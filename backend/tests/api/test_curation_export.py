"""Export v1 of reviewed curations (#532) through the public API."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    ActiveCuration,
    CurationNew,
    CurationSchema,
    CurationStatus,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)

pytestmark = pytest.mark.unit
URL = "/api/v1/export/curations"
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _point(
    db: Session,
    pair: WorkflowPair,
    gene: Gene,
    scope: Scope,
    at: datetime,
    status: CurationStatus = CurationStatus.ACTIVE,
    **kw: object,
) -> CurationNew:
    c = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="active",
        status=status,
        updated_at=at,
        **kw,
    )
    db.add(c)
    db.flush()
    db.add(
        ActiveCuration(
            gene_id=gene.id,
            scope_id=scope.id,
            curation_id=c.id,
            entity_key=kw.get("entity_key", ""),
            activated_at=at,
            updated_at=at,
            archived_at=at if status == CurationStatus.ARCHIVED else None,
        )
    )
    db.commit()
    return c


@pytest.fixture
def pair(db_session: Session) -> WorkflowPair:
    schema = CurationSchema(
        id=uuid4(),
        name="ClinGen SOP v11",
        version="11",
        schema_type="curation",
        field_definitions={},
        workflow_states={},
        ui_configuration={},
        schema_hash=uuid4().hex * 2,
    )
    db_session.add(schema)
    db_session.flush()
    p = WorkflowPair(id=uuid4(), name="x", version="1", curation_schema_id=schema.id)
    db_session.add(p)
    db_session.commit()
    return p


def _ids(r: object) -> list[str]:
    return [i["curation_id"] for i in r.json()["items"]]  # type: ignore[attr-defined]


def test_public_curation_exports_ids_pmids_and_methodology(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
    test_user_admin: UserNew,
) -> None:
    c = _point(
        db_session,
        pair,
        test_gene,
        test_public_scope,
        T0,
        entity_key="MONDO:0000001|AR",
        evidence_data={
            "disease_name": "BRCA1 disease",
            "mondo_id": "MONDO:0000001",
            "mode_of_inheritance": "Autosomal recessive",
            "genetic_evidence": {"rows": [{"pmid": "12"}, {"pmid": "PMID: 3"}]},
            "experimental_evidence": [{"pmid": "12"}],
        },
        computed_scores={
            "total_score": 12.5,
            "genetic_evidence_total": 10.5,
            "experimental_evidence_total": 2,
        },
        computed_verdict="Definitive",
        approved_by=test_user_admin.id,
        approved_at=T0,
    )

    r = client.get(URL, params={"scope_name": "public-scope"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["export_version"] == "1"
    assert body["next_cursor"] is None
    [item] = body["items"]
    assert item["curation_id"] == str(c.id)
    assert item["url"].endswith(f"/scopes/{test_public_scope.id}/curations/{c.id}")
    assert (item["hgnc_id"], item["approved_symbol"]) == ("HGNC:1100", "BRCA1")
    assert (item["mondo_id"], item["moi_hpo_id"]) == ("MONDO:0000001", "HP:0000007")
    assert item["entity_key"] == "MONDO:0000001|AR"
    assert item["relationship_type"] == "mendelian"
    assert item["pmids"] == ["3", "12"]
    assert item["computed_verdict"] == "Definitive"
    assert item["total_score"] == 12.5
    assert (item["genetic_score"], item["experimental_score"]) == (10.5, 2)
    assert item["methodology"]["schema_name"] == "ClinGen SOP v11"
    assert item["reviewer_name"] == "Admin User"
    assert item["status"] == "active"
    assert item["archived_at"] is None


def test_susceptibility_curation_exports_its_type_and_moi(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    """#539: the suffixed key decides, and the MOI still maps to its HPO id."""
    _point(
        db_session,
        pair,
        test_gene,
        test_public_scope,
        T0,
        entity_key="MONDO:0011037|AD|SUSCEPTIBILITY",
        evidence_data={"mondo_id": "MONDO:0011037", "mode_of_inheritance": "AD"},
        computed_scores={"genetic_total": 2, "experimental_total": 6},
    )
    [item] = client.get(URL, params={"scope_name": "public-scope"}).json()["items"]
    assert item["relationship_type"] == "susceptibility"
    # a custom point model's section keys (genetic, experimental)
    assert (item["genetic_score"], item["experimental_score"]) == (2, 6)
    assert item["moi_hpo_id"] == "HP:0000006"


def test_mondo_id_is_exported_as_a_curie(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    """#615: mondo_id as typed (MONDO_, lower case, spaces) is exported as MONDO:."""
    _point(
        db_session,
        pair,
        test_gene,
        test_public_scope,
        T0,
        entity_key="MONDO:0009633|AD",
        evidence_data={
            "mondo_id": " mondo_0009633",
            "mode_of_inheritance": "AD",
            "risk_allele": "rs1",  # stray: a Mendelian entity has no risk allele
        },
    )
    [item] = client.get(URL, params={"scope_name": "public-scope"}).json()["items"]
    assert item["mondo_id"] == "MONDO:0009633"
    assert item["risk_allele"] is None


def test_susceptibility_export_names_its_allele_and_association_score(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    """#614: the association points get their own field (scores.association_total
    stays), and an allele-keyed entity is still susceptibility with its MOI mapped."""
    _point(
        db_session,
        pair,
        test_gene,
        test_public_scope,
        T0,
        entity_key="MONDO:0009633|UNDETERMINED|SUSCEPTIBILITY|RS4664308A",
        evidence_data={
            "mondo_id": "MONDO:0009633",
            "mode_of_inheritance": "HP:0000005",
            "risk_allele": "rs4664308 A",
        },
        computed_scores={"association_total": 5, "experimental_total": 1},
    )
    [item] = client.get(URL, params={"scope_name": "public-scope"}).json()["items"]
    assert item["relationship_type"] == "susceptibility"
    assert item["moi_hpo_id"] == "HP:0000005"
    assert item["association_score"] == 5
    assert item["risk_allele"] == "rs4664308 A"
    assert item["genetic_score"] is None


def test_private_scope_hidden_from_anonymous_and_archived_shown_to_members(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_scope: Scope,
    viewer_token: str,
) -> None:
    old = _point(db_session, pair, test_gene, test_scope, T0, CurationStatus.ARCHIVED)
    new = _point(db_session, pair, test_gene, test_scope, T0 + timedelta(days=1))

    assert client.get(URL).json()["items"] == []
    assert client.get(URL, params={"scope_name": "test-scope"}).status_code == 404

    r = client.get(URL, headers={"Authorization": f"Bearer {viewer_token}"})
    assert _ids(r) == [str(old.id), str(new.id)]
    assert r.json()["items"][0]["archived_at"] is not None
    assert r.json()["items"][0]["status"] == "archived"


def test_deleted_curation_is_exported_as_archived_to_incremental_sync(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_scope: Scope,
    viewer_token: str,
    admin_token: str,
) -> None:
    c = _point(db_session, pair, test_gene, test_scope, T0)
    admin = {"Authorization": f"Bearer {admin_token}"}
    assert client.delete(f"/api/v1/curations/{c.id}", headers=admin).status_code == 204
    since = (T0 + timedelta(hours=1)).isoformat()  # after the export, before the delete
    r = client.get(
        URL,
        params={"updated_since": since},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    [item] = r.json()["items"]
    assert (item["curation_id"], item["status"]) == (str(c.id), "archived")
    assert item["archived_at"] is not None
    assert item["archive_reason"] == "Curation deleted"


def test_archived_curation_of_public_scope_hidden_from_anonymous(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    _point(db_session, pair, test_gene, test_public_scope, T0, CurationStatus.ARCHIVED)
    assert client.get(URL).json()["items"] == []


def test_pages_by_cursor_and_filters_by_updated_since(
    client: TestClient,
    db_session: Session,
    pair: WorkflowPair,
    test_gene: Gene,
    test_public_scope: Scope,
) -> None:
    made = [
        _point(
            db_session,
            pair,
            test_gene,
            test_public_scope,
            T0 + timedelta(hours=h),
            entity_key=f"MONDO:000000{h}|AD",  # one active curation per entity
        )
        for h in (2, 0, 1)
    ]
    ordered = [str(c.id) for c in (made[1], made[2], made[0])]

    seen, cursor = [], None
    for _ in range(3):
        # sent raw: next_cursor must be URL-safe (W11 A5)
        r = client.get(f"{URL}?limit=1" + (f"&cursor={cursor}" if cursor else ""))
        assert r.status_code == 200, r.text
        seen += _ids(r)
        cursor = r.json()["next_cursor"]
    assert seen == ordered
    assert cursor is None

    since = (T0 + timedelta(hours=1)).isoformat()
    assert _ids(client.get(URL, params={"updated_since": since})) == ordered[1:]


def test_cursor_of_an_offset_time_is_url_safe(client: TestClient) -> None:
    """W11 A5: "+00:00" in a raw query string decoded to a space and a 422."""
    from app.crud.curation_export import encode_cursor

    cursor = encode_cursor(T0.replace(tzinfo=UTC), uuid4())
    assert cursor.replace("-", "").replace("_", "").isalnum()
    assert client.get(f"{URL}?cursor={cursor}").status_code == 200


@pytest.mark.parametrize("cursor", ["junk", "2026-01-01T00:00:00|nope", "!!"])
def test_bad_cursor_is_refused(client: TestClient, cursor: str) -> None:
    assert client.get(URL, params={"cursor": cursor}).status_code == 422


def test_page_size_is_capped(client: TestClient) -> None:
    assert client.get(URL, params={"limit": 501}).status_code == 422
