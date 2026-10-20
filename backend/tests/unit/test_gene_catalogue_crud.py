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


# ---------------------------------------------------------------------------
# Pure scoring helpers
# ---------------------------------------------------------------------------


def test_sum_points_ignores_missing_and_none() -> None:
    items: list[dict[str, Any]] = [{"points": 2}, {"points": None}, {}, {"points": 1.5}]
    assert catalogue._sum_points_from_list(items) == 3.5
    assert catalogue._sum_points_from_list([{"x": 4}], key="x") == 4


def test_genetic_score_sums_all_contributing_sections() -> None:
    genetic: dict[str, Any] = {
        "case_level": {
            "autosomal_dominant_or_x_linked": {
                "predicted_or_proven_null": [{"proband_counted_points": 3}],
                "other_variant_type": [{"proband_counted_points": 1}],
            },
            "autosomal_recessive": {
                "predicted_or_proven_null": [{"proband_counted_points": 2}],
            },
        },
        "segregation": [{"points": 1}],
        "case_control": {
            "single_variant_analysis": [{"points": 0.5}],
            "aggregate_variant_analysis": [{"points": 0.5}],
        },
    }
    assert catalogue._calc_genetic_score(genetic) == 8.0


def test_experimental_score_sums_function_models_and_rescue() -> None:
    experimental: dict[str, Any] = {
        "function": {
            "biochemical_function": [{"points": 2}],
            "expression": [{"points": 1}],
        },
        "functional_alteration": {"patient_cells": [{"points": 1}]},
        "models": {"cell_culture_model": [{"points": 1}]},
        "rescue": {"human": [{"points": 1}], "patient_cells": [{"points": 0.5}]},
    }
    assert catalogue._calc_experimental_score(experimental) == 6.5


@pytest.mark.parametrize(
    ("genetic", "total", "expected"),
    [
        (6.0, 12.0, "definitive"),
        (4.5, 12.0, "strong"),
        (3.0, 9.0, "moderate"),
        (0.0, 1.0, "limited"),
        (0.0, 0.5, "no_known"),
        (5.9, 11.9, "moderate"),  # just below each boundary
    ],
)
def test_classification_thresholds(genetic: float, total: float, expected: str) -> None:
    assert catalogue._determine_classification(genetic, total) == expected


def test_scores_from_evidence_handles_empty_and_zero() -> None:
    assert catalogue._calculate_scores_from_evidence({}) == (None, None, None, None)
    assert catalogue._calculate_scores_from_evidence({"genetic_evidence": {}}) == (
        None,
        None,
        None,
        None,
    )


def test_scores_from_evidence_applies_caps() -> None:
    evidence: dict[str, Any] = {
        "genetic_evidence": {"segregation": [{"points": 20}]},
        "experimental_evidence": {"models": {"cell_culture_model": [{"points": 10}]}},
    }
    genetic, experimental, total, classification = (
        catalogue._calculate_scores_from_evidence(evidence)
    )
    assert genetic == 12.0  # capped
    assert experimental == 6.0  # capped
    assert total == 18.0
    assert classification == "definitive"


# ---------------------------------------------------------------------------
# Catalogue queries (SQLite)
# ---------------------------------------------------------------------------


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

    # Text search casts ARRAY columns (PostgreSQL-only), so it is not exercised here.
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


def test_entry_falls_back_to_evidence_when_scores_missing(
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
    assert scope_view.genetic_score == 7.0
    assert scope_view.classification == "limited"  # derived: total 7 falls in limited
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
    assert catalogue.get_available_classifications(db_session) == []
    assert catalogue.get_available_scopes_for_catalogue(db_session) == []

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

    assert catalogue.get_available_classifications(db_session) == ["limited"]

    scopes = catalogue.get_available_scopes_for_catalogue(db_session)
    assert {s["scope_name"] for s in scopes} == {"test-scope", "public-scope"}
    assert {s["is_public"] for s in scopes} == {False, True}
