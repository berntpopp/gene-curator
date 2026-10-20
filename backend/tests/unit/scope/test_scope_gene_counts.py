"""Gene counts behind the scope dashboard tiles and the scope list (#195)."""

from sqlalchemy.orm import Session

from app.crud.scope import scope_crud
from app.models.models import (
    ActiveCuration,
    CurationNew,
    Gene,
    GeneScopeAssignment,
    Scope,
)


def _gene(db: Session, n: int) -> Gene:
    gene = Gene(
        hgnc_id=f"HGNC:{n}",
        approved_symbol=f"G{n}",
        record_hash=str(n) * 64,
        previous_symbols=[],
        alias_symbols=[],
    )
    db.add(gene)
    db.commit()
    return gene


def test_total_counts_assigned_and_curated_genes_and_completed_never_exceeds_it(
    db_session: Session, test_scope: Scope, test_curation: CurationNew
) -> None:
    # test_curation's gene has a curation but no assignment (the "Total 0 / Completed 1" case)
    db_session.add(
        ActiveCuration(
            gene_id=test_curation.gene_id,
            scope_id=test_scope.id,
            curation_id=test_curation.id,
        )
    )
    assigned = _gene(db_session, 2)
    db_session.add(
        GeneScopeAssignment(gene_id=assigned.id, scope_id=test_scope.id, is_active=True)
    )
    inactive = _gene(db_session, 3)
    db_session.add(
        GeneScopeAssignment(
            gene_id=inactive.id, scope_id=test_scope.id, is_active=False
        )
    )
    db_session.commit()

    total, completed = scope_crud.get_gene_counts(db_session, scope_id=test_scope.id)

    assert (total, completed) == (2, 1)
    assert completed <= total


def test_empty_scope_has_no_genes(db_session: Session, test_scope: Scope) -> None:
    assert scope_crud.get_gene_counts(db_session, scope_id=test_scope.id) == (0, 0)
