"""
CRUD operations for scope management.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func
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

    def get_by_name(self, db: Session, *, name: str) -> Scope | None:
        """Get scope by name."""
        return db.query(Scope).filter(Scope.name == name).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        institution: str | None = None,
    ) -> list[Scope]:
        """Get multiple scopes with filtering."""
        query = db.query(Scope)

        if active_only:
            query = query.filter(Scope.is_active is True)

        if institution:
            query = query.filter(Scope.institution == institution)

        return query.offset(skip).limit(limit).all()

    def get_user_scopes(
        self, db: Session, *, user_scope_ids: list[UUID], active_only: bool = True
    ) -> list[Scope]:
        """Get scopes assigned to a specific user."""
        query = db.query(Scope).filter(Scope.id.in_(user_scope_ids))

        if active_only:
            query = query.filter(Scope.is_active is True)

        return query.all()

    def create_with_owner(
        self, db: Session, *, obj_in: ScopeCreate, owner_id: UUID
    ) -> Scope:
        """Create scope with owner."""
        obj_in_data = obj_in.dict()
        obj_in_data["created_by"] = owner_id
        db_obj = Scope(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_with_statistics(self, db: Session, *, scope_id: UUID) -> dict[str, Any]:
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
        gene_stats = (
            db.query(
                func.count(GeneScopeAssignment.id).label("total_genes_assigned"),
                func.count(GeneScopeAssignment.assigned_curator_id).label(
                    "genes_with_curator"
                ),
            )
            .filter(
                GeneScopeAssignment.scope_id == scope_id,
                GeneScopeAssignment.is_active is True,
            )
            .first()
        )

        # Curation stage counts
        precuration_count = (
            db.query(func.count(PrecurationNew.id))
            .filter(PrecurationNew.scope_id == scope_id)
            .scalar()
            or 0
        )

        curation_count = (
            db.query(func.count(CurationNew.id))
            .filter(CurationNew.scope_id == scope_id)
            .scalar()
            or 0
        )

        review_count = (
            db.query(func.count(Review.id))
            .join(CurationNew, Review.curation_id == CurationNew.id)
            .filter(CurationNew.scope_id == scope_id)
            .scalar()
            or 0
        )

        active_curation_count = (
            db.query(func.count(ActiveCuration.id))
            .filter(
                ActiveCuration.scope_id == scope_id,
                ActiveCuration.archived_at.is_(None),
            )
            .scalar()
            or 0
        )

        # Status breakdowns
        status_counts = (
            db.query(CurationNew.status, func.count(CurationNew.id))
            .filter(CurationNew.scope_id == scope_id)
            .group_by(CurationNew.status)
            .all()
        )

        status_dict = dict(status_counts)

        # Review metrics
        review_stats = (
            db.query(
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
            .filter(CurationNew.scope_id == scope_id)
            .first()
        )

        # Team metrics
        curator_count = (
            db.query(func.count(func.distinct(GeneScopeAssignment.assigned_curator_id)))
            .filter(
                GeneScopeAssignment.scope_id == scope_id,
                GeneScopeAssignment.is_active is True,
                GeneScopeAssignment.assigned_curator_id.isnot(None),
            )
            .scalar()
            or 0
        )

        reviewer_count = (
            db.query(func.count(func.distinct(Review.reviewer_id)))
            .join(CurationNew, Review.curation_id == CurationNew.id)
            .filter(CurationNew.scope_id == scope_id)
            .scalar()
            or 0
        )

        # Verdict distribution
        verdict_counts = (
            db.query(CurationNew.computed_verdict, func.count(CurationNew.id))
            .join(ActiveCuration, ActiveCuration.curation_id == CurationNew.id)
            .filter(
                ActiveCuration.scope_id == scope_id,
                ActiveCuration.archived_at.is_(None),
            )
            .group_by(CurationNew.computed_verdict)
            .all()
        )

        verdict_dict = {verdict: count for verdict, count in verdict_counts if verdict}

        # Recent activity (last 30 days)
        from datetime import datetime, timedelta

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        recent_curations = (
            db.query(func.count(CurationNew.id))
            .filter(
                CurationNew.scope_id == scope_id,
                CurationNew.created_at >= thirty_days_ago,
            )
            .scalar()
            or 0
        )

        recent_activations = (
            db.query(func.count(ActiveCuration.id))
            .filter(
                ActiveCuration.scope_id == scope_id,
                ActiveCuration.activated_at >= thirty_days_ago,
            )
            .scalar()
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
            "active_curators": curator_count,
            "active_reviewers": reviewer_count,
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
        count = (
            db.query(func.count(GeneScopeAssignment.id))
            .filter(
                GeneScopeAssignment.scope_id == scope_id,
                GeneScopeAssignment.is_active is True,
            )
            .scalar()
        )
        return count > 0

    def get_available_workflow_pairs(
        self, db: Session, *, scope_id: UUID
    ) -> list[dict[str, Any]]:
        """Get available workflow pairs for a scope."""
        workflow_pairs = (
            db.query(WorkflowPair).filter(WorkflowPair.is_active is True).all()
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
            user = db.query(UserNew).filter(UserNew.id == user_id).first()
            if user:
                # Add scope to user's assigned_scopes if not already there
                current_scopes = user.assigned_scopes or []
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
            user = db.query(UserNew).filter(UserNew.id == user_id).first()
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
            db.query(UserNew)
            .filter(UserNew.assigned_scopes.any(scope_id), UserNew.is_active is True)
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
    ) -> Scope:
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
        avg_curation_time = (
            db.query(
                func.avg(
                    func.extract(
                        "days", CurationNew.submitted_at - CurationNew.created_at
                    )
                )
            )
            .filter(
                CurationNew.scope_id == scope_id, CurationNew.submitted_at.isnot(None)
            )
            .scalar()
        )

        avg_review_time = (
            db.query(
                func.avg(func.extract("days", Review.reviewed_at - Review.assigned_at))
            )
            .join(CurationNew, Review.curation_id == CurationNew.id)
            .filter(CurationNew.scope_id == scope_id, Review.reviewed_at.isnot(None))
            .scalar()
        )

        # Quality metrics
        total_curations = (
            db.query(func.count(CurationNew.id))
            .filter(
                CurationNew.scope_id == scope_id,
                CurationNew.status.in_(["approved", "rejected"]),
            )
            .scalar()
            or 0
        )

        approved_curations = (
            db.query(func.count(CurationNew.id))
            .filter(CurationNew.scope_id == scope_id, CurationNew.status == "approved")
            .scalar()
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
