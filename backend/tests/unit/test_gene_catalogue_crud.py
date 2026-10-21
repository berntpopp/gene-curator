"""Unit tests for app.crud.gene_catalogue (scoring helpers and catalogue queries).

Disease-name filters use JSONB operators (`->>`) and are PostgreSQL-only, so they
are not exercised on SQLite.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud import gene_catalogue as catalogue
from app.models.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.schemas.gene_catalogue import GeneCatalogueFilters

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _public_scope(db_session: Session, test_scope: Scope) -> None:
    """The catalogue shows public scopes to everyone; members' private scopes are tested below."""
    test_scope.is_public = True
    db_session.commit()


def _curation(
    db: Session,
    gene: Gene,
    scope: Scope,
    user: UserNew,
    pair: WorkflowPair,
    verdict: str | None,
    *,
    evidence: dict[str, Any] | None = None,
    scores: dict[str, Any] | None = None,
    active: bool = True,
) -> CurationNew:
    curation = CurationNew(
        id=uuid4(),
        scope_id=scope.id,
        gene_id=gene.id,
        workflow_pair_id=pair.id,
        workflow_stage="curation",
        evidence_data=evidence or {},
        computed_verdict=verdict,
        computed_scores=scores or {},
        created_by=user.id,
    )
    db.add(curation)
    db.commit()
    db.refresh(curation)
    if active:
        db.add(
            ActiveCuration(
                gene_id=gene.id,
                scope_id=scope.id,
                curation_id=curation.id,
                activated_at=datetime.now(UTC),
            )
        )
        db.commit()
    return curation


def _gene(
    db: Session, owner: UserNew, hgnc_id: str, symbol: str, chromosome: str
) -> Gene:
    gene = Gene(
        id=uuid4(),
        hgnc_id=hgnc_id,
        approved_symbol=symbol,
        record_hash=hgnc_id.ljust(64, "0")[:64],
        previous_symbols=[],
        alias_symbols=[],
        chromosome=chromosome,
        location=None,
        details={},
        created_by=owner.id,
        updated_by=owner.id,
    )
    db.add(gene)
    db.commit()
    db.refresh(gene)
    return gene


def test_summary_stats_empty_catalogue(db_session: Session) -> None:
    stats = catalogue.get_catalogue_summary_stats(db_session)

    assert stats.total_genes_curated == 0
    assert stats.total_curations == 0
    assert stats.total_scopes == 0
    assert stats.classification_summary == {}


def test_summary_stats_counts_active_only(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "Definitive",
    )
    _curation(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "limited",
    )
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "moderate",
        active=False,  # never activated: must not count
    )

    stats = catalogue.get_catalogue_summary_stats(db_session)

    assert stats.total_genes_curated == 1
    assert stats.total_curations == 2
    assert stats.total_scopes == 2
    assert stats.classification_summary == {"definitive": 1, "limited": 1}


def test_entries_filter_search_chromosome_and_scope(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    other = _gene(db_session, test_user_curator, "HGNC:9100", "ZNF999", "7")
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )
    _curation(
        db_session,
        other,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "limited",
    )

    test_gene.alias_symbols = ["ALIAS1"]
    test_gene.previous_symbols = ["PREVIOUS1"]
    db_session.commit()
    for query in ("BRCA1", "HGNC:1100", "ALIAS1", "PREVIOUS1"):
        found, _ = catalogue.get_catalogue_entries(
            db_session, GeneCatalogueFilters(search=query)
        )
        assert [entry.approved_symbol for entry in found] == ["BRCA1"]
    by_chrom, _ = catalogue.get_catalogue_entries(
        db_session, GeneCatalogueFilters(chromosome="7")
    )
    assert [e.approved_symbol for e in by_chrom] == ["ZNF999"]

    by_scope, _ = catalogue.get_catalogue_entries(
        db_session, GeneCatalogueFilters(scope_id=test_scope.id)
    )
    assert [e.approved_symbol for e in by_scope] == ["BRCA1"]


def test_entries_classification_filter_and_pagination(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    other = _gene(db_session, test_user_curator, "HGNC:9101", "AAA2", "2")
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "definitive",
    )
    _curation(
        db_session,
        other,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "Definitive",
    )

    filtered, total = catalogue.get_catalogue_entries(
        db_session, GeneCatalogueFilters(classification="DEFINITIVE")
    )
    assert total == 2
    assert {e.approved_symbol for e in filtered} == {"BRCA1", "AAA2"}

    page, total_paged = catalogue.get_catalogue_entries(
        db_session, GeneCatalogueFilters(limit=1, skip=0, sort_order="asc")
    )
    assert total_paged == 2
    assert [e.approved_symbol for e in page] == ["AAA2"]


def test_entry_does_not_invent_scores_when_persisted_scores_missing(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    evidence: dict[str, Any] = {
        "disease_name": "Test disease",
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "AD",
        "genetic_evidence": {"segregation": [{"points": 7}]},
        "experimental_evidence": {},
    }
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        None,
        evidence=evidence,
        scores={},
    )

    entries, _ = catalogue.get_catalogue_entries(db_session, GeneCatalogueFilters())

    assert len(entries) == 1
    entry = entries[0]
    assert entry.total_curations == 1
    assert entry.scope_count == 1
    assert entry.diseases == ["Test disease"]
    scope_view = entry.scope_curations[0]
    assert scope_view.genetic_score is None
    assert scope_view.classification is None
    assert scope_view.curator_name == "Curator User"
    assert scope_view.mondo_id == "MONDO:0000001"


def test_get_gene_catalogue_combines_entries_and_flags(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "strong",
    )

    response = catalogue.get_gene_catalogue(
        db_session, GeneCatalogueFilters(limit=1, skip=0)
    )

    assert response.total == 1
    assert response.has_next is False
    assert response.has_prev is False
    assert response.summary.total_curations == 1
    assert response.entries[0].classifications == {"strong": 1}

    default = catalogue.get_gene_catalogue(db_session)
    assert default.total == 1


def test_available_classifications_and_scopes(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    test_scope.is_public = False  # visible to its member (the curator) only
    db_session.commit()
    uid = test_user_curator.id
    assert catalogue.get_available_classifications(db_session, uid) == []
    assert catalogue.get_available_scopes_for_catalogue(db_session, uid) == []

    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "Limited",
    )
    _curation(
        db_session,
        test_gene,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        None,
    )

    assert catalogue.get_available_classifications(db_session, uid) == ["limited"]
    # anonymous: the private scope is hidden
    anon = catalogue.get_available_scopes_for_catalogue(db_session)
    assert {s["name"] for s in anon} == {"public-scope"}

    scopes = catalogue.get_available_scopes_for_catalogue(db_session, uid)
    assert {s["name"] for s in scopes} == {"test-scope", "public-scope"}
    assert {s["is_public"] for s in scopes} == {False, True}
    from app.api.v1.endpoints.gene_catalogue import get_available_scopes

    options = get_available_scopes(db=db_session, current_user=test_user_curator)
    assert {option.id for option in options} == {
        str(test_scope.id),
        str(test_public_scope.id),
    }
    assert {option.name for option in options} == {"test-scope", "public-scope"}


@pytest.mark.parametrize("curation_disease", [None, "", "Curated disease"])
def test_catalogue_uses_precuration_disease_without_extra_queries(
    db_session: Session,
    test_curation: CurationNew,
    test_precuration,
    curation_disease: str | None,
) -> None:
    from sqlalchemy import event

    from app.crud.curation import curation_crud

    test_precuration.evidence_data = {
        "disease_name": "NAA10-related syndrome",
        "mondo_id": "MONDO:0000001",
        "mode_of_inheritance": "X-linked",
    }
    test_curation.precuration_id = test_precuration.id
    test_curation.evidence_data = {"disease_name": curation_disease}
    db_session.add(
        ActiveCuration(
            gene_id=test_curation.gene_id,
            scope_id=test_curation.scope_id,
            curation_id=test_curation.id,
            activated_at=datetime.now(UTC),
        )
    )
    db_session.commit()
    db_session.expire_all()
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", record)
    try:
        entries, _ = catalogue.get_catalogue_entries(db_session, GeneCatalogueFilters())
    finally:
        event.remove(db_session.bind, "before_cursor_execute", record)

    expected = curation_disease or "NAA10-related syndrome"
    detail = entries[0].scope_curations[0]
    assert entries[0].diseases == [expected]
    assert detail.disease_name == expected
    assert detail.mondo_id == "MONDO:0000001"
    assert detail.mode_of_inheritance == "X-linked"
    assert len(statements) == 3  # count, genes, curations with joined precurations
    summaries, _ = curation_crud.get_multi_filtered(db_session)
    assert summaries[0].disease_name == detail.disease_name


def test_classification_list_hides_private_scope_verdicts(
    db_session: Session,
    test_gene: Gene,
    test_scope: Scope,
    test_public_scope: Scope,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> None:
    test_scope.is_public = False  # the curator is its member
    db_session.commit()
    _curation(
        db_session,
        test_gene,
        test_scope,
        test_user_curator,
        test_workflow_pair,
        "Refuted",
    )
    other = _gene(db_session, test_user_curator, "HGNC:777", "OTHR", "1")
    _curation(
        db_session,
        other,
        test_public_scope,
        test_user_curator,
        test_workflow_pair,
        "Strong",
    )

    assert catalogue.get_available_classifications(db_session) == ["strong"]
    assert catalogue.get_available_classifications(
        db_session, test_user_curator.id
    ) == [
        "refuted",
        "strong",
    ]
