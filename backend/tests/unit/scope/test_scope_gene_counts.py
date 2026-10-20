"""Gene counts behind the scope dashboard tiles and the scope list (#195)."""

from sqlalchemy.orm import Session

from app.crud.scope_counts import get_counts_for_scopes
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

    c = get_counts_for_scopes(db_session, [test_scope.id])[test_scope.id]
    total, completed = c["total"], c["completed"]

    assert (total, completed) == (2, 1)
    assert completed <= total


def test_empty_scope_has_no_genes(db_session: Session, test_scope: Scope) -> None:
    c = get_counts_for_scopes(db_session, [test_scope.id])[test_scope.id]
    assert c == {"total": 0, "completed": 0, "members": 0, "pending": 0}


def test_member_and_pending_invitation_counts_are_grouped_per_scope(
    db_session: Session, test_scope: Scope
) -> None:
    from tests.api.scopes.factories import make_member, make_scope, make_user

    other = make_scope(db_session)
    make_member(db_session, test_scope, make_user(db_session), "viewer")
    make_member(
        db_session, test_scope, make_user(db_session), "curator", accepted=False
    )
    make_member(db_session, other, make_user(db_session), "viewer")

    counts = get_counts_for_scopes(db_session, [test_scope.id, other.id])

    assert (counts[test_scope.id]["members"], counts[test_scope.id]["pending"]) == (
        1,
        1,
    )
    assert (counts[other.id]["members"], counts[other.id]["pending"]) == (1, 0)
