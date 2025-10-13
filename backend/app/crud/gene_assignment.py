"""
CRUD operations for gene-scope assignments.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models import (
    CurationNew,
    GeneNew,
    GeneScopeAssignment,
    PrecurationNew,
    UserNew,
)
from app.schemas.gene_assignment import (
    GeneScopeAssignmentCreate,
    GeneScopeAssignmentUpdate,
)


class CRUDGeneScopeAssignment(
    CRUDBase[GeneScopeAssignment, GeneScopeAssignmentCreate, GeneScopeAssignmentUpdate]
):
    """CRUD operations for gene-scope assignments."""

    def get_by_gene_and_scope(
        self, db: Session, *, gene_id: UUID, scope_id: UUID
    ) -> GeneScopeAssignment | None:
        """Get assignment by gene and scope ID."""
        return (
            db.query(GeneScopeAssignment)
            .filter(
                and_(
                    GeneScopeAssignment.gene_id == gene_id,
                    GeneScopeAssignment.scope_id == scope_id,
                )
            )
            .first()
        )

    def get_active_assignments(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        scope_id: UUID | None = None,
        curator_id: UUID | None = None,
        gene_id: UUID | None = None,
    ) -> list[GeneScopeAssignment]:
        """Get active gene-scope assignments with filtering."""
        query = db.query(GeneScopeAssignment).filter(
            GeneScopeAssignment.is_active is True
        )

        if scope_id:
            query = query.filter(GeneScopeAssignment.scope_id == scope_id)

        if curator_id:
            query = query.filter(GeneScopeAssignment.assigned_curator_id == curator_id)

        if gene_id:
            query = query.filter(GeneScopeAssignment.gene_id == gene_id)

        return query.offset(skip).limit(limit).all()

    def get_scope_assignments(
        self,
        db: Session,
        *,
        scope_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[GeneScopeAssignment]:
        """Get all assignments for a specific scope."""
        query = db.query(GeneScopeAssignment).filter(
            GeneScopeAssignment.scope_id == scope_id
        )

        if not include_inactive:
            query = query.filter(GeneScopeAssignment.is_active is True)

        return (
            query.order_by(GeneScopeAssignment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_curator_assignments(
        self,
        db: Session,
        *,
        curator_id: UUID,
        skip: int = 0,
        limit: int = 100,
        scope_id: UUID | None = None,
    ) -> list[GeneScopeAssignment]:
        """Get all assignments for a specific curator."""
        query = db.query(GeneScopeAssignment).filter(
            and_(
                GeneScopeAssignment.assigned_curator_id == curator_id,
                GeneScopeAssignment.is_active is True,
            )
        )

        if scope_id:
            query = query.filter(GeneScopeAssignment.scope_id == scope_id)

        return (
            query.order_by(GeneScopeAssignment.assigned_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_unassigned_genes(
        self, db: Session, *, scope_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get genes available for assignment in a scope."""
        # Find genes that are not currently assigned to this scope or have inactive assignments
        subquery = (
            db.query(GeneScopeAssignment.gene_id)
            .filter(
                and_(
                    GeneScopeAssignment.scope_id == scope_id,
                    GeneScopeAssignment.is_active is True,
                )
            )
            .subquery()
        )

        available_genes = (
            db.query(GeneNew)
            .filter(~GeneNew.id.in_(subquery))
            .offset(skip)
            .limit(limit)
            .all()
        )

        result = []
        for gene in available_genes:
            result.append(
                {
                    "gene_id": gene.id,
                    "hgnc_id": gene.hgnc_id,
                    "approved_symbol": gene.approved_symbol,
                    "chromosome": gene.chromosome,
                    "location": gene.location,
                }
            )

        return result

    def create_assignment(
        self, db: Session, *, obj_in: GeneScopeAssignmentCreate, assigned_by: UUID
    ) -> GeneScopeAssignment:
        """Create new gene-scope assignment."""
        # Check if assignment already exists
        existing = self.get_by_gene_and_scope(
            db, gene_id=obj_in.gene_id, scope_id=obj_in.scope_id
        )
        if existing and existing.is_active:
            raise ValueError("Gene is already assigned to this scope")

        obj_in_data = obj_in.dict()
        obj_in_data["assigned_by"] = assigned_by
        obj_in_data["assigned_at"] = datetime.utcnow()

        db_obj = GeneScopeAssignment(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def assign_curator(
        self, db: Session, *, assignment_id: UUID, curator_id: UUID, assigned_by: UUID
    ) -> GeneScopeAssignment | None:
        """Assign a curator to a gene-scope assignment."""
        assignment = self.get(db, id=assignment_id)
        if not assignment:
            return None

        # Verify curator has access to this scope
        curator = db.query(UserNew).filter(UserNew.id == curator_id).first()
        if not curator or assignment.scope_id not in (curator.assigned_scopes or []):
            raise ValueError("Curator does not have access to this scope")

        assignment.assigned_curator_id = curator_id
        assignment.curator_assigned_by = assigned_by
        assignment.curator_assigned_at = datetime.utcnow()

        db.commit()
        db.refresh(assignment)
        return assignment

    def unassign_curator(
        self, db: Session, *, assignment_id: UUID, unassigned_by: UUID
    ) -> GeneScopeAssignment | None:
        """Remove curator from a gene-scope assignment."""
        assignment = self.get(db, id=assignment_id)
        if not assignment:
            return None

        assignment.assigned_curator_id = None
        assignment.curator_assigned_by = None
        assignment.curator_assigned_at = None
        assignment.last_updated_by = unassigned_by
        assignment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(assignment)
        return assignment

    def deactivate_assignment(
        self,
        db: Session,
        *,
        assignment_id: UUID,
        deactivated_by: UUID,
        reason: str | None = None,
    ) -> GeneScopeAssignment | None:
        """Deactivate a gene-scope assignment."""
        assignment = self.get(db, id=assignment_id)
        if not assignment:
            return None

        # Check if assignment has active work
        if self.has_active_work(db, assignment_id=assignment_id):
            raise ValueError(
                "Cannot deactivate assignment with active precurations or curations"
            )

        assignment.is_active = False
        assignment.deactivated_at = datetime.utcnow()
        assignment.deactivated_by = deactivated_by
        assignment.deactivation_reason = reason
        assignment.last_updated_by = deactivated_by
        assignment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(assignment)
        return assignment

    def reactivate_assignment(
        self, db: Session, *, assignment_id: UUID, reactivated_by: UUID
    ) -> GeneScopeAssignment | None:
        """Reactivate a gene-scope assignment."""
        assignment = self.get(db, id=assignment_id)
        if not assignment:
            return None

        assignment.is_active = True
        assignment.deactivated_at = None
        assignment.deactivated_by = None
        assignment.deactivation_reason = None
        assignment.last_updated_by = reactivated_by
        assignment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(assignment)
        return assignment

    def has_active_work(self, db: Session, *, assignment_id: UUID) -> bool:
        """Check if assignment has active precurations or curations."""
        assignment = self.get(db, id=assignment_id)
        if not assignment:
            return False

        # Check for active precurations
        precuration_count = (
            db.query(func.count(PrecurationNew.id))
            .filter(
                and_(
                    PrecurationNew.gene_id == assignment.gene_id,
                    PrecurationNew.scope_id == assignment.scope_id,
                    PrecurationNew.status.in_(["draft", "submitted", "in_review"]),
                )
            )
            .scalar()
        )

        # Check for active curations
        curation_count = (
            db.query(func.count(CurationNew.id))
            .filter(
                and_(
                    CurationNew.gene_id == assignment.gene_id,
                    CurationNew.scope_id == assignment.scope_id,
                    CurationNew.status.in_(["draft", "submitted", "in_review"]),
                )
            )
            .scalar()
        )

        return (precuration_count or 0) > 0 or (curation_count or 0) > 0

    def get_assignment_statistics(
        self, db: Session, *, assignment_id: UUID
    ) -> dict[str, Any]:
        """Get detailed statistics for a gene-scope assignment."""
        assignment = self.get(db, id=assignment_id)
        if not assignment:
            return {}

        # Count precurations
        precuration_stats = (
            db.query(PrecurationNew.status, func.count(PrecurationNew.id))
            .filter(
                and_(
                    PrecurationNew.gene_id == assignment.gene_id,
                    PrecurationNew.scope_id == assignment.scope_id,
                )
            )
            .group_by(PrecurationNew.status)
            .all()
        )

        # Count curations
        curation_stats = (
            db.query(CurationNew.status, func.count(CurationNew.id))
            .filter(
                and_(
                    CurationNew.gene_id == assignment.gene_id,
                    CurationNew.scope_id == assignment.scope_id,
                )
            )
            .group_by(CurationNew.status)
            .all()
        )

        precuration_dict = dict(precuration_stats)
        curation_dict = dict(curation_stats)

        return {
            "assignment_id": assignment_id,
            "gene_id": assignment.gene_id,
            "scope_id": assignment.scope_id,
            "assigned_curator_id": assignment.assigned_curator_id,
            "is_active": assignment.is_active,
            "assigned_at": assignment.assigned_at,
            "curator_assigned_at": assignment.curator_assigned_at,
            # Work progress
            "total_precurations": sum(precuration_dict.values()),
            "draft_precurations": precuration_dict.get("draft", 0),
            "submitted_precurations": precuration_dict.get("submitted", 0),
            "approved_precurations": precuration_dict.get("approved", 0),
            "total_curations": sum(curation_dict.values()),
            "draft_curations": curation_dict.get("draft", 0),
            "submitted_curations": curation_dict.get("submitted", 0),
            "in_review_curations": curation_dict.get("in_review", 0),
            "approved_curations": curation_dict.get("approved", 0),
            "has_active_work": self.has_active_work(db, assignment_id=assignment_id),
        }

    def bulk_assign_genes(
        self,
        db: Session,
        *,
        gene_ids: list[UUID],
        scope_id: UUID,
        curator_id: UUID | None = None,
        assigned_by: UUID,
    ) -> dict[str, Any]:
        """Bulk assign multiple genes to a scope."""
        created_assignments = []
        skipped_assignments = []
        errors = []

        for gene_id in gene_ids:
            try:
                # Check if assignment already exists
                existing = self.get_by_gene_and_scope(
                    db, gene_id=gene_id, scope_id=scope_id
                )
                if existing and existing.is_active:
                    skipped_assignments.append(
                        {
                            "gene_id": gene_id,
                            "reason": "Gene already assigned to this scope",
                        }
                    )
                    continue

                # Create assignment
                assignment_data = GeneScopeAssignmentCreate(
                    gene_id=gene_id,
                    scope_id=scope_id,
                    assigned_curator_id=curator_id,
                    priority_level="medium",
                )

                assignment = self.create_assignment(
                    db, obj_in=assignment_data, assigned_by=assigned_by
                )
                created_assignments.append(assignment)

            except Exception as e:
                errors.append({"gene_id": gene_id, "error": str(e)})

        return {
            "created_assignments": created_assignments,
            "skipped_assignments": skipped_assignments,
            "errors": errors,
            "total_processed": len(gene_ids),
            "total_created": len(created_assignments),
            "total_skipped": len(skipped_assignments),
            "total_errors": len(errors),
        }

    def get_curator_workload(
        self, db: Session, *, curator_id: UUID, scope_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get workload statistics for a curator."""
        query = db.query(GeneScopeAssignment).filter(
            and_(
                GeneScopeAssignment.assigned_curator_id == curator_id,
                GeneScopeAssignment.is_active is True,
            )
        )

        if scope_id:
            query = query.filter(GeneScopeAssignment.scope_id == scope_id)

        assignments = query.all()

        # Count by priority level
        priority_counts = {}
        for assignment in assignments:
            priority = assignment.priority_level or "medium"
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        # Count active work
        total_active_work = 0
        for assignment in assignments:
            if self.has_active_work(db, assignment_id=assignment.id):
                total_active_work += 1

        return {
            "curator_id": curator_id,
            "scope_id": scope_id,
            "total_assignments": len(assignments),
            "assignments_with_active_work": total_active_work,
            "priority_breakdown": priority_counts,
            "high_priority_assignments": priority_counts.get("high", 0),
            "medium_priority_assignments": priority_counts.get("medium", 0),
            "low_priority_assignments": priority_counts.get("low", 0),
        }


gene_assignment_crud = CRUDGeneScopeAssignment(GeneScopeAssignment)
