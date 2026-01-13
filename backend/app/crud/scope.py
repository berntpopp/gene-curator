"""
CRUD operations for scope management.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models import (
    ActiveCuration,
    CurationNew,
    GeneScopeAssignment,
    PrecurationNew,
    Review,
    Scope,
    UserNew,
    WorkflowPair,
)
from app.schemas.scope import ScopeCreate, ScopeUpdate


class CRUDScope(CRUDBase[Scope, ScopeCreate, ScopeUpdate]):
    """CRUD operations for scopes."""

    # Convenience methods for tests and simpler API
    def create_scope(self, db: Session, obj_in: ScopeCreate, owner_id: UUID) -> Scope:
        """Create scope (convenience wrapper for create_with_owner)."""
        return self.create_with_owner(db, obj_in=obj_in, owner_id=owner_id)

    def get_scope(self, db: Session, scope_id: UUID) -> Scope | None:
        """Get scope by ID (convenience wrapper for get)."""
        return self.get(db, id=scope_id)

    def get_scope_by_name(self, db: Session, name: str) -> Scope | None:
        """Get scope by name (convenience wrapper for get_by_name)."""
        return self.get_by_name(db, name=name)

    def get_scopes(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        institution: str | None = None,
    ) -> Sequence[Scope]:
        """Get multiple scopes (convenience wrapper for get_multi)."""
        return self.get_multi(
            db, skip=skip, limit=limit, active_only=active_only, institution=institution
        )

    def get_scope_statistics(self, db: Session, scope_id: UUID) -> dict[str, Any]:
        """Get detailed statistics for a scope (convenience wrapper)."""
        return self.get_detailed_statistics(db, scope_id=scope_id)

    def get_scopes_by_institution(
        self, db: Session, institution: str, *, active_only: bool = True
    ) -> Sequence[Scope]:
        """Get scopes filtered by institution."""
        return self.get_multi(
            db, skip=0, limit=1000, active_only=active_only, institution=institution
        )

    def update_scope(
        self, db: Session, scope_id: UUID, obj_in: ScopeUpdate | dict[str, Any]
    ) -> Scope | None:
        """Update scope by ID (convenience wrapper for update)."""
        scope = self.get(db, id=scope_id)
        if not scope:
            return None
        return self.update(db, db_obj=scope, obj_in=obj_in)

    def delete_scope(
        self, db: Session, scope_id: UUID, *, soft_delete: bool = True
    ) -> bool:
        """
        Delete scope (soft or hard delete).

        Args:
            db: Database session
            scope_id: Scope UUID
            soft_delete: If True, soft delete (set is_active=False); if False, hard delete (remove from DB)

        Returns:
            True if deleted successfully, False if not found
        """
        scope = self.get(db, id=scope_id)
        if not scope:
            return False

        if soft_delete:
            scope.is_active = False
            db.commit()
        else:
            self.remove(db, id=scope_id)

        return True

    def get_by_name(self, db: Session, *, name: str) -> Scope | None:
        """Get scope by name."""
        return db.execute(select(Scope).where(Scope.name == name)).scalars().first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        institution: str | None = None,
    ) -> Sequence[Scope]:
        """Get multiple scopes with filtering."""
        stmt = select(Scope)

        if active_only:
            stmt = stmt.where(Scope.is_active)  # Fixed: use == instead of is

        if institution:
            stmt = stmt.where(Scope.institution == institution)

        return db.execute(stmt.offset(skip).limit(limit)).scalars().all()

    def get_multi_with_counts(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        institution: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get multiple scopes with gene and member counts."""
        from app.models import ScopeMembership

        stmt = select(Scope)

        if active_only:
            stmt = stmt.where(Scope.is_active)

        if institution:
            stmt = stmt.where(Scope.institution == institution)

        scopes = db.execute(stmt.offset(skip).limit(limit)).scalars().all()

        result = []
        for scope in scopes:
            # Get gene count for this scope
            gene_count = (
                db.execute(
                    select(func.count(GeneScopeAssignment.id)).where(
                        GeneScopeAssignment.scope_id == scope.id,
                        GeneScopeAssignment.is_active,
                    )
                ).scalar()
                or 0
            )

            # Get member count for this scope
            member_count = (
                db.execute(
                    select(func.count(ScopeMembership.id)).where(
                        ScopeMembership.scope_id == scope.id,
                        ScopeMembership.is_active,
                        ScopeMembership.accepted_at.isnot(None),
                    )
                ).scalar()
                or 0
            )

            # Convert scope to dict and add counts
            scope_dict = {
                "id": scope.id,
                "name": scope.name,
                "display_name": scope.display_name,
                "description": scope.description,
                "institution": scope.institution,
                "is_public": scope.is_public,
                "scope_config": scope.scope_config,
                "is_active": scope.is_active,
                "default_workflow_pair_id": scope.default_workflow_pair_id,
                "created_at": scope.created_at,
                "updated_at": scope.updated_at,
                "created_by": scope.created_by,
                "gene_count": gene_count,
                "member_count": member_count,
            }
            result.append(scope_dict)

        return result

    def get_user_scopes(
        self, db: Session, *, user_scope_ids: list[UUID], active_only: bool = True
    ) -> Sequence[Scope]:
        """Get scopes assigned to a specific user."""
        stmt = select(Scope).where(Scope.id.in_(user_scope_ids))

        if active_only:
            stmt = stmt.where(Scope.is_active)  # Fixed: use == instead of is

        return db.execute(stmt).scalars().all()

    def create_with_owner(
        self, db: Session, *, obj_in: ScopeCreate, owner_id: UUID
    ) -> Scope:
        """Create scope with owner."""
        obj_in_data = obj_in.model_dump()
        obj_in_data["created_by"] = owner_id
        db_obj = Scope(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_with_statistics(
        self, db: Session, *, scope_id: UUID
    ) -> dict[str, Any] | None:
        """Get scope with detailed statistics."""
        scope = self.get(db, id=scope_id)
        if not scope:
            return None

        # Get basic statistics
        stats = self.get_detailed_statistics(db, scope_id=scope_id)

        return {**scope.__dict__, "statistics": stats}

    def get_detailed_statistics(self, db: Session, *, scope_id: UUID) -> dict[str, Any]:
        """Get detailed statistics for a scope."""
        # Gene assignment counts
        gene_stats_row = db.execute(
            select(
                func.count(GeneScopeAssignment.id).label("total_genes_assigned"),
                func.count(GeneScopeAssignment.assigned_curator_id).label(
                    "genes_with_curator"
                ),
            ).where(
                GeneScopeAssignment.scope_id == scope_id,
                GeneScopeAssignment.is_active,  # Fixed: use == instead of is
            )
        ).first()

        # Handle None case
        if not gene_stats_row:
            gene_stats = type(
                "obj", (), {"total_genes_assigned": 0, "genes_with_curator": 0}
            )()
        else:
            gene_stats = gene_stats_row

        # Curation stage counts
        precuration_count = (
            db.execute(
                select(func.count(PrecurationNew.id)).where(
                    PrecurationNew.scope_id == scope_id
                )
            ).scalar()
            or 0
        )

        curation_count = (
            db.execute(
                select(func.count(CurationNew.id)).where(
                    CurationNew.scope_id == scope_id
                )
            ).scalar()
            or 0
        )

        review_count = (
            db.execute(
                select(func.count(Review.id))
                .join(CurationNew, Review.curation_id == CurationNew.id)
                .where(CurationNew.scope_id == scope_id)
            ).scalar()
            or 0
        )

        active_curation_count = (
            db.execute(
                select(func.count(ActiveCuration.id)).where(
                    ActiveCuration.scope_id == scope_id,
                    ActiveCuration.archived_at.is_(None),
                )
            ).scalar()
            or 0
        )

        # Status breakdowns
        status_counts = db.execute(
            select(CurationNew.status, func.count(CurationNew.id))
            .where(CurationNew.scope_id == scope_id)
            .group_by(CurationNew.status)
        ).all()

        status_dict: dict[str, int] = {
            str(status): int(count) for status, count in status_counts
        }

        # Review metrics
        review_stats_row = db.execute(
            select(
                func.count(Review.id)
                .filter(Review.status == "pending")
                .label("pending_reviews"),
                func.count(Review.id)
                .filter(Review.status == "approved")
                .label("approved_reviews"),
                func.avg(func.extract("days", Review.reviewed_at - Review.assigned_at))
                .filter(Review.reviewed_at.isnot(None))
                .label("avg_review_time_days"),
            )
            .join(CurationNew, Review.curation_id == CurationNew.id)
            .where(CurationNew.scope_id == scope_id)
        ).first()

        # Handle None case
        if not review_stats_row:
            review_stats = type(
                "obj",
                (),
                {
                    "pending_reviews": 0,
                    "approved_reviews": 0,
                    "avg_review_time_days": None,
                },
            )()
        else:
            review_stats = review_stats_row

        # Team metrics
        # Total scope members (from scope_memberships table)
        from app.models import ScopeMembership

        member_count = (
            db.execute(
                select(func.count(ScopeMembership.id)).where(
                    ScopeMembership.scope_id == scope_id,
                    ScopeMembership.is_active,
                    ScopeMembership.accepted_at.isnot(None),
                )
            ).scalar()
            or 0
        )

        curator_count = (
            db.execute(
                select(
                    func.count(func.distinct(GeneScopeAssignment.assigned_curator_id))
                ).where(
                    GeneScopeAssignment.scope_id == scope_id,
                    GeneScopeAssignment.is_active,  # Fixed: use == instead of is
                    GeneScopeAssignment.assigned_curator_id.isnot(None),
                )
            ).scalar()
            or 0
        )

        reviewer_count = (
            db.execute(
                select(func.count(func.distinct(Review.reviewer_id)))
                .join(CurationNew, Review.curation_id == CurationNew.id)
                .where(CurationNew.scope_id == scope_id)
            ).scalar()
            or 0
        )

        # Verdict distribution
        verdict_counts = db.execute(
            select(CurationNew.computed_verdict, func.count(CurationNew.id))
            .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
            .where(
                ActiveCuration.scope_id == scope_id,
                ActiveCuration.archived_at.is_(None),
            )
            .group_by(CurationNew.computed_verdict)
        ).all()

        verdict_dict = {verdict: count for verdict, count in verdict_counts if verdict}

        # Recent activity (last 30 days)
        from datetime import UTC, datetime, timedelta

        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

        recent_curations = (
            db.execute(
                select(func.count(CurationNew.id)).where(
                    CurationNew.scope_id == scope_id,
                    CurationNew.created_at >= thirty_days_ago,
                )
            ).scalar()
            or 0
        )

        recent_activations = (
            db.execute(
                select(func.count(ActiveCuration.id)).where(
                    ActiveCuration.scope_id == scope_id,
                    ActiveCuration.activated_at >= thirty_days_ago,
                )
            ).scalar()
            or 0
        )

        return {
            "total_genes_assigned": gene_stats.total_genes_assigned or 0,
            "genes_with_curator": gene_stats.genes_with_curator or 0,
            "total_precurations": precuration_count,
            "total_curations": curation_count,
            "total_reviews": review_count,
            "active_curations": active_curation_count,
            # Status breakdowns
            "draft_curations": status_dict.get("draft", 0),
            "submitted_curations": status_dict.get("submitted", 0),
            "curations_in_review": status_dict.get("in_review", 0),
            "approved_curations": status_dict.get("approved", 0),
            "rejected_curations": status_dict.get("rejected", 0),
            # Review metrics
            "pending_reviews": review_stats.pending_reviews or 0,
            "approved_reviews": review_stats.approved_reviews or 0,
            "avg_review_time_days": (
                float(review_stats.avg_review_time_days)
                if review_stats.avg_review_time_days
                else None
            ),
            # Team metrics
            "member_count": member_count,  # Total accepted members
            "active_curators": curator_count,  # Curators with assignments
            "active_reviewers": reviewer_count,  # Reviewers with reviews
            # Verdict distribution
            "definitive_verdicts": verdict_dict.get("Definitive", 0),
            "strong_verdicts": verdict_dict.get("Strong", 0),
            "moderate_verdicts": verdict_dict.get("Moderate", 0),
            "limited_verdicts": verdict_dict.get("Limited", 0),
            # Recent activity
            "curations_last_30_days": recent_curations,
            "activations_last_30_days": recent_activations,
        }

    def has_active_assignments(self, db: Session, *, scope_id: UUID) -> bool:
        """Check if scope has active gene assignments."""
        count = db.execute(
            select(func.count(GeneScopeAssignment.id)).where(
                GeneScopeAssignment.scope_id == scope_id,
                GeneScopeAssignment.is_active,  # Fixed: use == instead of is
            )
        ).scalar()
        return (count or 0) > 0

    def get_available_workflow_pairs(
        self, db: Session, *, scope_id: UUID
    ) -> list[dict[str, Any]]:
        """Get available workflow pairs for a scope."""
        workflow_pairs = (
            db.execute(
                select(WorkflowPair).where(
                    WorkflowPair.is_active
                )  # Fixed: use == instead of is
            )
            .scalars()
            .all()
        )

        result = []
        for wp in workflow_pairs:
            result.append(
                {
                    "id": wp.id,
                    "name": wp.name,
                    "version": wp.version,
                    "description": wp.description,
                    "is_active": wp.is_active,
                    "precuration_schema_id": wp.precuration_schema_id,
                    "curation_schema_id": wp.curation_schema_id,
                }
            )

        return result

    def assign_users(self, db: Session, *, scope_id: UUID, user_ids: list[UUID]) -> int:
        """Assign users to a scope."""
        assigned_count = 0

        for user_id in user_ids:
            user = (
                db.execute(select(UserNew).where(UserNew.id == user_id))
                .scalars()
                .first()
            )
            if user:
                # Add scope to user's assigned_scopes if not already there
                current_scopes: list[UUID] = user.assigned_scopes or []
                if scope_id not in current_scopes:
                    current_scopes.append(scope_id)
                    user.assigned_scopes = current_scopes
                    assigned_count += 1

        db.commit()
        return assigned_count

    def remove_users(self, db: Session, *, scope_id: UUID, user_ids: list[UUID]) -> int:
        """Remove users from a scope."""
        removed_count = 0

        for user_id in user_ids:
            user = (
                db.execute(select(UserNew).where(UserNew.id == user_id))
                .scalars()
                .first()
            )
            if user and user.assigned_scopes:
                # Remove scope from user's assigned_scopes
                current_scopes = user.assigned_scopes
                if scope_id in current_scopes:
                    current_scopes.remove(scope_id)
                    user.assigned_scopes = current_scopes
                    removed_count += 1

        db.commit()
        return removed_count

    def get_scope_users(self, db: Session, *, scope_id: UUID) -> list[dict[str, Any]]:
        """Get users assigned to a scope."""
        users = (
            db.execute(
                select(UserNew).where(
                    UserNew.assigned_scopes.contains([str(scope_id)]), UserNew.is_active
                )  # Fixed: use == instead of is
            )
            .scalars()
            .all()
        )

        result = []
        for user in users:
            result.append(
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "user_email": user.email,
                    "user_role": user.role,
                    "assigned_at": user.created_at,  # Approximation
                }
            )

        return result

    def set_default_workflow_pair(
        self, db: Session, *, scope_id: UUID, workflow_pair_id: UUID
    ) -> Scope | None:
        """Set default workflow pair for a scope."""
        scope = self.get(db, id=scope_id)
        if scope:
            scope.default_workflow_pair_id = workflow_pair_id
            db.commit()
            db.refresh(scope)
        return scope

    def get_performance_metrics(self, db: Session, *, scope_id: UUID) -> dict[str, Any]:
        """Get performance metrics for a scope."""
        # Throughput metrics
        avg_curation_time = db.execute(
            select(
                func.avg(
                    func.extract(
                        "days", CurationNew.submitted_at - CurationNew.created_at
                    )
                )
            ).where(
                CurationNew.scope_id == scope_id, CurationNew.submitted_at.isnot(None)
            )
        ).scalar()

        avg_review_time = db.execute(
            select(
                func.avg(func.extract("days", Review.reviewed_at - Review.assigned_at))
            )
            .join(CurationNew, Review.curation_id == CurationNew.id)
            .where(CurationNew.scope_id == scope_id, Review.reviewed_at.isnot(None))
        ).scalar()

        # Quality metrics
        total_curations = (
            db.execute(
                select(func.count(CurationNew.id)).where(
                    CurationNew.scope_id == scope_id,
                    CurationNew.status.in_(["approved", "rejected"]),
                )
            ).scalar()
            or 0
        )

        approved_curations = (
            db.execute(
                select(func.count(CurationNew.id)).where(
                    CurationNew.scope_id == scope_id, CurationNew.status == "approved"
                )
            ).scalar()
            or 0
        )

        approval_rate = (
            (approved_curations / total_curations * 100)
            if total_curations > 0
            else None
        )
        rejection_rate = (
            ((total_curations - approved_curations) / total_curations * 100)
            if total_curations > 0
            else None
        )

        return {
            "avg_curation_time_days": (
                float(avg_curation_time) if avg_curation_time else None
            ),
            "avg_review_time_days": float(avg_review_time) if avg_review_time else None,
            "approval_rate": approval_rate,
            "rejection_rate": rejection_rate,
            "total_evaluated_curations": total_curations,
        }


scope_crud = CRUDScope(Scope)
