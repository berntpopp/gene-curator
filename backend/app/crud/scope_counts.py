"""Grouped per-scope counts for the scope list and dashboard (no per-scope queries)."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    GeneScopeAssignment,
    ScopeMembership,
)


def get_counts_for_scopes(
    db: Session, scope_ids: Sequence[UUID]
) -> dict[UUID, dict[str, int]]:
    """Gene, completed-gene, member and pending-invitation counts for many scopes.

    Total genes: distinct genes with an active assignment or a curation.
    Completed: genes with an active curation, so completed never exceeds total.
    One grouped query per metric, not per scope.
    """
    assigned = select(GeneScopeAssignment.scope_id, GeneScopeAssignment.gene_id).where(
        GeneScopeAssignment.is_active
    )
    curated = select(CurationNew.scope_id, CurationNew.gene_id).where(
        CurationNew.status != CurationStatus.ARCHIVED
    )
    active = select(ActiveCuration.scope_id, ActiveCuration.gene_id).where(
        ActiveCuration.archived_at.is_(None)
    )
    genes = assigned.union(curated, active).subquery()
    done = active.distinct().subquery()
    members = (
        select(
            ScopeMembership.scope_id,
            ScopeMembership.accepted_at.isnot(None),
            func.count(),
        )
        .where(ScopeMembership.is_active)
        .group_by(ScopeMembership.scope_id, ScopeMembership.accepted_at.isnot(None))
    )
    counts = {
        sid: {"total": 0, "completed": 0, "members": 0, "pending": 0}
        for sid in scope_ids
    }
    for table, key in ((genes, "total"), (done, "completed")):
        for sid, n in db.execute(
            select(table.c.scope_id, func.count()).group_by(table.c.scope_id)
        ):
            if sid in counts:
                counts[sid][key] = n
    for sid, accepted, n in db.execute(members):
        if sid in counts:
            counts[sid]["members" if accepted else "pending"] = n
    return counts
