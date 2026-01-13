"""
Multi-stage workflow engine for schema-agnostic curation system.
Implements the 5-stage pipeline: Entry → Precuration → Curation → Review → Active
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    PrecurationNew,
    Review,
    ReviewStatus,
    UserNew,
    WorkflowStage,
)
from app.schemas.workflow_engine import (
    PeerReviewRequest,
    WorkflowStateInfo,
    WorkflowStatistics,
    WorkflowTransition,
    WorkflowValidationResult,
)


class WorkflowEngine:
    """
    Core workflow engine managing multi-stage curation process.
    Enforces business rules, state transitions, and 4-eyes principle.
    """

    def __init__(self) -> None:
        self.valid_transitions = {
            # Precuration workflow
            WorkflowStage.ENTRY: [WorkflowStage.PRECURATION],
            WorkflowStage.PRECURATION: [
                WorkflowStage.CURATION,
                WorkflowStage.ENTRY,
            ],  # Can go back to entry
            # Curation workflow
            WorkflowStage.CURATION: [
                WorkflowStage.REVIEW,
                WorkflowStage.PRECURATION,
            ],  # Can go back to precuration
            # Review workflow
            WorkflowStage.REVIEW: [
                WorkflowStage.ACTIVE,
                WorkflowStage.CURATION,
            ],  # Can send back to curation
            # Active state
            WorkflowStage.ACTIVE: [
                WorkflowStage.REVIEW
            ],  # Can be sent back for re-review
        }

    def _load_item_for_validation(
        self,
        db: Session,
        item_id: UUID,
        item_type: str,
    ) -> tuple[CurationNew | PrecurationNew | None, UUID | None]:
        """Load item and return (item, scope_id) for validation."""
        if item_type == "curation":
            curation = (
                db.execute(select(CurationNew).where(CurationNew.id == item_id))
                .scalars()
                .first()
            )
            return (curation, curation.scope_id) if curation else (None, None)
        elif item_type == "precuration":
            precuration = (
                db.execute(select(PrecurationNew).where(PrecurationNew.id == item_id))
                .scalars()
                .first()
            )
            return (precuration, precuration.scope_id) if precuration else (None, None)
        return (None, None)

    def _validate_4_eyes_principle(
        self,
        db: Session,
        user: UserNew,
        user_id: UUID,
        item: CurationNew | PrecurationNew | None,
        item_type: str,
    ) -> list[str]:
        """Validate 4-eyes principle and return list of errors."""
        errors: list[str] = []
        if not item:
            return errors

        # Check if user is reviewing their own work
        if item.created_by == user_id:
            errors.append("4-eyes principle violation: Cannot review your own work")

        # Check review permissions for curations
        if item_type == "curation" and not self._has_review_permissions(db, user, item):
            errors.append("Insufficient permissions for peer review")

        return errors

    def validate_transition(
        self,
        db: Session,
        current_stage: WorkflowStage,
        target_stage: WorkflowStage,
        user_id: UUID,
        item_id: UUID,
        item_type: str,
    ) -> WorkflowValidationResult:
        """Validate if a workflow transition is allowed."""
        errors: list[str] = []
        warnings: list[str] = []
        requirements: list[str] = []

        # Check if transition is valid
        if target_stage not in self.valid_transitions.get(current_stage, []):
            errors.append(
                f"Invalid transition from {current_stage.value} to {target_stage.value}"
            )

        # Get user for permission checks
        user = (
            db.execute(select(UserNew).where(UserNew.id == user_id)).scalars().first()
        )
        if not user:
            errors.append("User not found")
            return WorkflowValidationResult(
                is_valid=False, errors=errors, warnings=warnings, requirements=requirements
            )

        # Load item to get scope_id for scope-specific role check
        item, scope_id = self._load_item_for_validation(db, item_id, item_type)

        # Role-based transition validation (check global OR scope-specific role)
        role_requirements = self._get_role_requirements(current_stage, target_stage)
        if not self._check_role_authorization(db, user, role_requirements, scope_id):
            errors.append(
                f"User not authorized for this transition (requires one of: "
                f"{', '.join(role_requirements)})"
            )

        # 4-eyes principle validation
        if self._requires_peer_review(current_stage, target_stage):
            errors.extend(self._validate_4_eyes_principle(db, user, user_id, item, item_type))

        # Content validation requirements
        requirements.extend(self._get_content_requirements(current_stage, target_stage))

        # Stage-specific validations
        stage_validation = self._validate_stage_requirements(
            db, current_stage, target_stage, item_id, item_type
        )
        errors.extend(stage_validation.get("errors", []))
        warnings.extend(stage_validation.get("warnings", []))
        requirements.extend(stage_validation.get("requirements", []))

        return WorkflowValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requirements=requirements,
        )

    def execute_transition(
        self,
        db: Session,
        item_id: UUID,
        item_type: str,
        target_stage: WorkflowStage,
        user_id: UUID,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowTransition:
        """Execute a workflow state transition."""

        # Get current item and stage
        current_stage, item = self._get_current_stage_and_item(db, item_id, item_type)
        if not item or current_stage is None:
            raise ValueError(f"{item_type} not found")

        # Validate transition
        validation = self.validate_transition(
            db, current_stage, target_stage, user_id, item_id, item_type
        )
        if not validation.is_valid:
            raise ValueError(f"Invalid transition: {', '.join(validation.errors)}")

        # Execute the transition based on target stage
        transition_result = None

        if target_stage == WorkflowStage.PRECURATION:
            transition_result = self._transition_to_precuration(
                db, item, user_id, notes, metadata
            )

        elif target_stage == WorkflowStage.CURATION:
            transition_result = self._transition_to_curation(
                db, item, user_id, notes, metadata
            )

        elif target_stage == WorkflowStage.REVIEW:
            transition_result = self._transition_to_review(
                db, item, user_id, notes, metadata
            )

        elif target_stage == WorkflowStage.ACTIVE:
            transition_result = self._transition_to_active(
                db, item, user_id, notes, metadata
            )

        elif target_stage == WorkflowStage.ENTRY:
            transition_result = self._transition_to_entry(
                db, item, user_id, notes, metadata
            )

        else:
            raise ValueError(f"Unsupported target stage: {target_stage}")

        # Log the transition in audit trail
        self._log_workflow_transition(
            db,
            item_id,
            item_type,
            current_stage,
            target_stage,
            user_id,
            notes,
            metadata,
        )

        return WorkflowTransition(
            item_id=item_id,
            item_type=item_type,
            from_stage=current_stage,
            to_stage=target_stage,
            executed_by=user_id,
            executed_at=datetime.utcnow(),
            notes=notes,
            metadata=metadata or {},
            **transition_result,
        )

    def get_workflow_state(
        self, db: Session, item_id: UUID, item_type: str
    ) -> WorkflowStateInfo:
        """Get current workflow state information for an item."""
        current_stage, item = self._get_current_stage_and_item(db, item_id, item_type)

        if not item or current_stage is None:
            raise ValueError(f"{item_type} not found")

        # Get available transitions
        available_transitions = self.valid_transitions.get(current_stage, [])

        # Get workflow history
        history = self._get_workflow_history(db, item_id, item_type)

        # Get pending reviews if in review stage
        pending_reviews = []
        if current_stage == WorkflowStage.REVIEW:
            pending_reviews = self._get_pending_reviews(db, item_id, item_type)

        # Calculate progress metrics
        progress_metrics = self._calculate_progress_metrics(current_stage, history)

        return WorkflowStateInfo(
            item_id=item_id,
            item_type=item_type,
            current_stage=current_stage,
            available_transitions=available_transitions,
            workflow_history=history,
            pending_reviews=pending_reviews,
            progress_metrics=progress_metrics,
            last_updated=(
                item.updated_at if hasattr(item, "updated_at") else datetime.utcnow()
            ),
            last_updated_by=item.updated_by if hasattr(item, "updated_by") else None,
        )

    def assign_peer_reviewer(
        self,
        db: Session,
        item_id: UUID,
        item_type: str,
        reviewer_id: UUID,
        assigned_by: UUID,
        review_type: str = "peer_review",
    ) -> PeerReviewRequest:
        """Assign a peer reviewer to an item in review stage."""

        current_stage, item = self._get_current_stage_and_item(db, item_id, item_type)

        if current_stage != WorkflowStage.REVIEW:
            raise ValueError("Item must be in review stage to assign peer reviewer")

        # Validate reviewer is different from creator
        if item_type == "curation":
            curation_result = (
                db.execute(select(CurationNew).where(CurationNew.id == item_id))
                .scalars()
                .first()
            )
            if not curation_result:
                raise ValueError("Curation not found")
            original_creator = curation_result.created_by
        else:
            precuration_result = (
                db.execute(select(PrecurationNew).where(PrecurationNew.id == item_id))
                .scalars()
                .first()
            )
            if not precuration_result:
                raise ValueError("Precuration not found")
            original_creator = precuration_result.created_by

        if reviewer_id == original_creator:
            raise ValueError(
                "4-eyes principle violation: Cannot assign original creator as reviewer"
            )

        # Create review assignment
        review = Review(
            curation_id=item_id,
            reviewer_id=reviewer_id,
            assigned_by=assigned_by,
            status=ReviewStatus.PENDING,
            assigned_at=datetime.utcnow(),
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        return PeerReviewRequest(
            review_id=review.id,
            item_id=item_id,
            item_type=item_type,
            reviewer_id=reviewer_id,
            assigned_by=assigned_by,
            review_type=review_type,
            assigned_at=review.assigned_at,
            status=review.status,
        )

    def submit_peer_review(
        self,
        db: Session,
        review_id: UUID,
        reviewer_id: UUID,
        decision: str,
        comments: str | None = None,
        suggested_changes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a peer review decision."""

        review = (
            db.execute(select(Review).where(Review.id == review_id)).scalars().first()
        )
        if not review:
            raise ValueError("Review not found")

        if review.reviewer_id != reviewer_id:
            raise ValueError("Only assigned reviewer can submit this review")

        if review.status != ReviewStatus.PENDING:
            raise ValueError("Review has already been completed")

        # Valid decisions
        valid_decisions = ["approve", "request_changes", "reject"]
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision. Must be one of: {valid_decisions}")

        # Update review
        review.status = ReviewStatus.APPROVED
        review.recommendation = decision
        review.comments = comments
        review.feedback_data = suggested_changes or {}
        review.reviewed_at = datetime.utcnow()

        db.commit()

        # If approved, check if all required reviews are complete
        if decision == "approve":
            all_reviews_complete = self._check_all_reviews_complete(
                db, review.curation_id, item_type="curation"
            )
            if all_reviews_complete:
                # Automatically transition to active if all reviews approved
                self.execute_transition(
                    db,
                    review.curation_id,
                    "curation",
                    WorkflowStage.ACTIVE,
                    reviewer_id,
                    notes="All peer reviews approved - automatically activated",
                )

        return {
            "review_id": review_id,
            "decision": decision,
            "status": "completed",
            "auto_transitioned": decision == "approve" and all_reviews_complete,
        }

    def get_workflow_statistics(
        self, db: Session, scope_id: UUID | None = None, days: int = 30
    ) -> WorkflowStatistics:
        """Get workflow performance statistics."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Base queries
        precuration_stmt = select(PrecurationNew).where(
            PrecurationNew.created_at >= cutoff_date
        )
        curation_stmt = select(CurationNew).where(CurationNew.created_at >= cutoff_date)
        review_stmt = select(Review).where(Review.assigned_at >= cutoff_date)
        active_stmt = select(ActiveCuration).where(
            ActiveCuration.activated_at >= cutoff_date
        )

        if scope_id:
            precuration_stmt = precuration_stmt.where(
                PrecurationNew.scope_id == scope_id
            )
            curation_stmt = curation_stmt.where(CurationNew.scope_id == scope_id)
            # Reviews and active curations would need JOIN to filter by scope

        # Stage counts
        from sqlalchemy import func as sqlalchemy_func

        stage_counts: dict[str, int] = {
            "entry": 0,  # Would need to be calculated based on unstarted assignments
            "precuration": db.execute(
                select(sqlalchemy_func.count()).select_from(
                    precuration_stmt.where(
                        PrecurationNew.status == CurationStatus.DRAFT
                    ).subquery()
                )
            ).scalar()
            or 0,
            "curation": db.execute(
                select(sqlalchemy_func.count()).select_from(
                    curation_stmt.where(
                        CurationNew.status == CurationStatus.DRAFT
                    ).subquery()
                )
            ).scalar()
            or 0,
            "review": db.execute(
                select(sqlalchemy_func.count()).select_from(
                    review_stmt.where(Review.status == ReviewStatus.PENDING).subquery()
                )
            ).scalar()
            or 0,
            "active": db.execute(
                select(sqlalchemy_func.count()).select_from(active_stmt.subquery())
            ).scalar()
            or 0,
        }

        # Transition metrics
        total_transitions = sum(stage_counts.values())
        completed_workflows = (
            db.execute(
                select(sqlalchemy_func.count()).select_from(active_stmt.subquery())
            ).scalar()
            or 0
        )

        # Time-based metrics
        avg_precuration_time = self._calculate_average_stage_time(
            db, "precuration", cutoff_date, scope_id
        )
        avg_curation_time = self._calculate_average_stage_time(
            db, "curation", cutoff_date, scope_id
        )
        avg_review_time = self._calculate_average_stage_time(
            db, "review", cutoff_date, scope_id
        )

        # Review metrics
        total_reviews = (
            db.execute(
                select(sqlalchemy_func.count()).select_from(review_stmt.subquery())
            ).scalar()
            or 0
        )
        completed_reviews = (
            db.execute(
                select(sqlalchemy_func.count()).select_from(
                    review_stmt.where(Review.status == ReviewStatus.APPROVED).subquery()
                )
            ).scalar()
            or 0
        )
        pending_reviews = total_reviews - completed_reviews

        # Quality metrics
        approval_rate = 0.0
        if completed_reviews > 0:
            approved_reviews = (
                db.execute(
                    select(sqlalchemy_func.count()).select_from(
                        review_stmt.where(
                            and_(
                                Review.status == ReviewStatus.APPROVED,
                                Review.recommendation == "approve",
                            )
                        ).subquery()
                    )
                ).scalar()
                or 0
            )
            approval_rate = approved_reviews / completed_reviews

        return WorkflowStatistics(
            scope_id=scope_id,
            time_period_days=days,
            stage_counts=stage_counts,
            total_transitions=total_transitions,
            completed_workflows=completed_workflows,
            avg_precuration_time_hours=avg_precuration_time,
            avg_curation_time_hours=avg_curation_time,
            avg_review_time_hours=avg_review_time,
            total_reviews=total_reviews,
            completed_reviews=completed_reviews,
            pending_reviews=pending_reviews,
            approval_rate=approval_rate,
            bottleneck_stage=(
                max(stage_counts, key=lambda k: stage_counts[k])
                if stage_counts
                else None
            ),
        )

    # Private helper methods

    def _get_stage_from_curation_status(
        self, curation_item: CurationNew
    ) -> WorkflowStage:
        """Derive workflow stage from curation status (backwards compatibility)."""
        status_to_stage = {
            CurationStatus.DRAFT: WorkflowStage.CURATION,
            CurationStatus.SUBMITTED: WorkflowStage.CURATION,
            CurationStatus.IN_REVIEW: WorkflowStage.REVIEW,
            CurationStatus.ACTIVE: WorkflowStage.ACTIVE,
        }
        return status_to_stage.get(curation_item.status, WorkflowStage.CURATION)

    def _get_current_stage_and_item(
        self, db: Session, item_id: UUID, item_type: str
    ) -> tuple[WorkflowStage | None, Any]:
        """Get current workflow stage and item object."""
        if item_type == "precuration":
            precuration_item = (
                db.execute(select(PrecurationNew).where(PrecurationNew.id == item_id))
                .scalars()
                .first()
            )
            if precuration_item:
                stage = getattr(precuration_item, "workflow_stage", None)
                return stage or WorkflowStage.PRECURATION, precuration_item

        elif item_type == "curation":
            curation_item = (
                db.execute(select(CurationNew).where(CurationNew.id == item_id))
                .scalars()
                .first()
            )
            if curation_item:
                # Use workflow_stage field if set, else derive from status
                stage = getattr(curation_item, "workflow_stage", None)
                if not stage:
                    stage = self._get_stage_from_curation_status(curation_item)
                return stage, curation_item

        elif item_type == "active":
            active_item = (
                db.execute(select(ActiveCuration).where(ActiveCuration.id == item_id))
                .scalars()
                .first()
            )
            if active_item:
                return WorkflowStage.ACTIVE, active_item

        return None, None

    def _get_role_requirements(
        self, current_stage: WorkflowStage, target_stage: WorkflowStage
    ) -> list[str]:
        """Get required user roles for a transition."""
        role_matrix = {
            (WorkflowStage.ENTRY, WorkflowStage.PRECURATION): [
                "curator",
                "admin",
                "scope_admin",
            ],
            (WorkflowStage.PRECURATION, WorkflowStage.CURATION): [
                "curator",
                "admin",
                "scope_admin",
            ],
            (WorkflowStage.CURATION, WorkflowStage.REVIEW): [
                "curator",
                "admin",
                "scope_admin",
            ],
            (WorkflowStage.REVIEW, WorkflowStage.ACTIVE): [
                "curator",
                "admin",
                "scope_admin",
            ],
            # Backwards transitions (less restrictive)
            (WorkflowStage.PRECURATION, WorkflowStage.ENTRY): [
                "curator",
                "admin",
                "scope_admin",
            ],
            (WorkflowStage.CURATION, WorkflowStage.PRECURATION): [
                "curator",
                "admin",
                "scope_admin",
            ],
            (WorkflowStage.REVIEW, WorkflowStage.CURATION): [
                "curator",
                "admin",
                "scope_admin",
            ],
            (WorkflowStage.ACTIVE, WorkflowStage.REVIEW): [
                "admin",
                "scope_admin",
            ],  # More restrictive
        }

        return role_matrix.get((current_stage, target_stage), ["admin"])

    def _check_role_authorization(
        self,
        db: Session,
        user: UserNew,
        role_requirements: list[str],
        scope_id: UUID | None,
    ) -> bool:
        """
        Check if user has authorization based on global role OR scope-specific role.
        Uses scope_memberships table for scope-specific roles.
        """
        from app.models import ScopeMembership

        # Admin always has authorization
        if user.role == "admin":
            return True

        # Check global user role
        if user.role in role_requirements:
            return True

        # Check scope-specific role if scope_id is provided
        if scope_id:
            # Valid scope roles: admin, curator, reviewer, viewer
            # Map global role requirements to valid scope roles
            valid_scope_roles = ["admin", "curator", "reviewer", "viewer"]
            scope_role_requirements = [
                r for r in role_requirements if r in valid_scope_roles
            ]
            # Always include "reviewer" for scope-specific checks as they can review
            if "reviewer" not in scope_role_requirements:
                scope_role_requirements.append("reviewer")

            membership = (
                db.query(ScopeMembership)
                .filter(
                    ScopeMembership.user_id == user.id,
                    ScopeMembership.scope_id == scope_id,
                    ScopeMembership.is_active,
                    ScopeMembership.role.in_(scope_role_requirements),
                )
                .first()
            )
            if membership:
                return True

        return False

    def _requires_peer_review(
        self, current_stage: WorkflowStage, target_stage: WorkflowStage
    ) -> bool:
        """
        Check if transition requires peer review (4-eyes principle).

        Note: The 4-eyes principle applies at APPROVAL time (REVIEW -> ACTIVE),
        not at SUBMISSION time (CURATION -> REVIEW). A curator can submit their
        own work for review, but a different reviewer must approve it.
        """
        peer_review_transitions = [
            # Only approval requires 4-eyes - a different person must approve
            (WorkflowStage.REVIEW, WorkflowStage.ACTIVE),
        ]
        return (current_stage, target_stage) in peer_review_transitions

    def _has_review_permissions(self, db: Session, user: UserNew, item: Any) -> bool:
        """
        Check if user has permissions to review this item.
        Uses scope_memberships table for scope-specific role checking.
        """
        from app.models import ScopeMembership

        # Admin always has review permissions
        if user.role == "admin":
            return True

        # User must have access to the item's scope via scope_memberships
        if hasattr(item, "scope_id") and item.scope_id:
            # Check scope membership with eligible review role
            # Valid scope roles: admin, curator, reviewer, viewer
            eligible_scope_roles = ["admin", "curator", "reviewer"]
            membership = (
                db.query(ScopeMembership)
                .filter(
                    ScopeMembership.user_id == user.id,
                    ScopeMembership.scope_id == item.scope_id,
                    ScopeMembership.is_active,
                    ScopeMembership.role.in_(eligible_scope_roles),
                )
                .first()
            )
            if not membership:
                return False

        return True

    def _get_content_requirements(
        self, current_stage: WorkflowStage, target_stage: WorkflowStage
    ) -> list[str]:
        """Get content requirements for a transition."""
        requirements = []

        if target_stage == WorkflowStage.CURATION:
            requirements.extend(
                [
                    "Precuration must be completed",
                    "Disease association must be documented",
                    "Lumping/splitting decision must be made",
                ]
            )

        elif target_stage == WorkflowStage.REVIEW:
            requirements.extend(
                [
                    "All evidence fields must be completed",
                    "Scoring must be calculated",
                    "Summary must be generated",
                ]
            )

        elif target_stage == WorkflowStage.ACTIVE:
            requirements.extend(
                [
                    "All peer reviews must be completed",
                    "All reviewers must approve",
                    "Final quality checks must pass",
                ]
            )

        return requirements

    def _validate_stage_requirements(
        self,
        db: Session,
        current_stage: WorkflowStage,
        target_stage: WorkflowStage,
        item_id: UUID,
        item_type: str,
    ) -> dict[str, list[str]]:
        """Validate stage-specific requirements."""
        errors: list[str] = []
        warnings: list[str] = []
        requirements: list[str] = []

        # Add specific validation logic based on stages
        if target_stage == WorkflowStage.REVIEW and item_type == "curation":
            curation = (
                db.execute(select(CurationNew).where(CurationNew.id == item_id))
                .scalars()
                .first()
            )
            if curation:
                # Check if evidence data exists
                if not curation.evidence_data:
                    errors.append("Evidence data is required before review")
                else:
                    # Summary is recommended but not required for submission
                    if not curation.evidence_data.get("summary"):
                        warnings.append(
                            "Evidence summary not provided - consider adding one"
                        )

                # Check if scoring is complete (warning only)
                if not curation.computed_scores:
                    warnings.append("Final score not calculated")

        return {"errors": errors, "warnings": warnings, "requirements": requirements}

    def _transition_to_precuration(
        self,
        db: Session,
        item: Any,
        user_id: UUID,
        notes: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle transition to precuration stage."""
        # Update workflow stage
        if hasattr(item, "workflow_stage"):
            item.workflow_stage = WorkflowStage.PRECURATION
        db.commit()
        return {"success": True, "message": "Transitioned to precuration"}

    def _transition_to_curation(
        self,
        db: Session,
        item: Any,
        user_id: UUID,
        notes: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle transition to curation stage."""
        # Update workflow stage and status (when returning from review)
        if hasattr(item, "workflow_stage"):
            item.workflow_stage = WorkflowStage.CURATION
        if hasattr(item, "status"):
            item.status = CurationStatus.DRAFT
        db.commit()
        return {"success": True, "message": "Transitioned to curation"}

    def _transition_to_review(
        self,
        db: Session,
        item: Any,
        user_id: UUID,
        notes: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle transition to review stage."""
        # Update workflow stage
        if hasattr(item, "workflow_stage"):
            item.workflow_stage = WorkflowStage.REVIEW
        # Update status
        if hasattr(item, "status"):
            item.status = CurationStatus.IN_REVIEW
        db.commit()
        return {"success": True, "message": "Transitioned to review"}

    def _transition_to_active(
        self,
        db: Session,
        item: Any,
        user_id: UUID,
        notes: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle transition to active stage."""
        # Update workflow stage and status on the item
        if hasattr(item, "workflow_stage"):
            item.workflow_stage = WorkflowStage.ACTIVE
        if hasattr(item, "status"):
            item.status = CurationStatus.ACTIVE

        # Create active curation record
        if hasattr(item, "gene_id") and hasattr(item, "scope_id"):
            # Check for existing active curation for this gene-scope pair
            existing_active = (
                db.query(ActiveCuration)
                .filter(
                    ActiveCuration.gene_id == item.gene_id,
                    ActiveCuration.scope_id == item.scope_id,
                    ActiveCuration.archived_at.is_(None),
                )
                .first()
            )

            replaced_curation_id = None
            if existing_active:
                # Archive the existing active curation
                existing_active.archived_at = datetime.utcnow()
                existing_active.archived_by = user_id
                existing_active.archive_reason = "Replaced by new active curation"
                replaced_curation_id = existing_active.curation_id

            # Create new active curation record
            active_curation = ActiveCuration(
                gene_id=item.gene_id,
                scope_id=item.scope_id,
                curation_id=item.id if hasattr(item, "id") else None,
                activated_by=user_id,
                activated_at=datetime.utcnow(),
                replaced_curation_id=replaced_curation_id,
                # Audit fields required by audit trigger
                created_by=user_id,
                updated_by=user_id,
            )
            db.add(active_curation)

        db.commit()
        return {"success": True, "message": "Transitioned to active"}

    def _transition_to_entry(
        self,
        db: Session,
        item: Any,
        user_id: UUID,
        notes: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Handle transition back to entry stage."""
        # Update workflow stage
        if hasattr(item, "workflow_stage"):
            item.workflow_stage = WorkflowStage.ENTRY
        db.commit()
        return {"success": True, "message": "Transitioned back to entry"}

    def _log_workflow_transition(
        self,
        db: Session,
        item_id: UUID,
        item_type: str,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage,
        user_id: UUID,
        notes: str | None,
        metadata: dict[str, Any] | None,
    ) -> None:
        """Log workflow transition in audit trail."""
        # This would log to the audit_log table
        pass

    def _get_workflow_history(
        self, db: Session, item_id: UUID, item_type: str
    ) -> list[dict[str, Any]]:
        """Get workflow transition history."""
        # This would query the audit log for workflow transitions
        return []

    def _get_pending_reviews(
        self, db: Session, item_id: UUID, item_type: str
    ) -> list[dict[str, Any]]:
        """Get pending peer reviews for an item."""
        reviews = (
            db.execute(
                select(Review).where(
                    and_(
                        Review.curation_id == item_id,
                        Review.status == ReviewStatus.PENDING,
                    )
                )
            )
            .scalars()
            .all()
        )

        return [
            {
                "review_id": review.id,
                "reviewer_id": review.reviewer_id,
                "assigned_at": review.assigned_at,
            }
            for review in reviews
        ]

    def _calculate_progress_metrics(
        self, current_stage: WorkflowStage, history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate workflow progress metrics."""
        stage_order = [
            WorkflowStage.ENTRY,
            WorkflowStage.PRECURATION,
            WorkflowStage.CURATION,
            WorkflowStage.REVIEW,
            WorkflowStage.ACTIVE,
        ]

        current_index = (
            stage_order.index(current_stage) if current_stage in stage_order else 0
        )
        total_stages = len(stage_order)

        return {
            "current_stage_index": current_index,
            "total_stages": total_stages,
            "progress_percentage": (current_index / max(1, total_stages - 1)) * 100,
            "stages_completed": current_index,
            "stages_remaining": total_stages - current_index - 1,
        }

    def _check_all_reviews_complete(
        self, db: Session, item_id: UUID, item_type: str
    ) -> bool:
        """Check if all required reviews are complete and approved."""
        from sqlalchemy import func as sqlalchemy_func

        pending_reviews = db.execute(
            select(sqlalchemy_func.count()).select_from(
                select(Review)
                .where(
                    and_(
                        Review.curation_id == item_id,
                        Review.status == ReviewStatus.PENDING,
                    )
                )
                .subquery()
            )
        ).scalar()

        # All reviews must be completed
        if pending_reviews and pending_reviews > 0:
            return False

        # All completed reviews must be approved
        rejected_reviews = db.execute(
            select(sqlalchemy_func.count()).select_from(
                select(Review)
                .where(
                    and_(
                        Review.curation_id == item_id,
                        Review.status == ReviewStatus.APPROVED,
                        Review.recommendation != "approve",
                    )
                )
                .subquery()
            )
        ).scalar()

        return rejected_reviews == 0 if rejected_reviews is not None else True

    def _calculate_average_stage_time(
        self, db: Session, stage: str, cutoff_date: datetime, scope_id: UUID | None
    ) -> float:
        """Calculate average time spent in a workflow stage."""
        # This would need to analyze audit log data to calculate time differences
        # For now, return a placeholder
        return 24.0  # 24 hours average

    def get_eligible_peer_reviewers(
        self,
        db: Session,
        scope_id: UUID | None = None,
        exclude_user_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get eligible peer reviewers for assignment.

        Filters:
        - Active users only
        - If scope_id provided, must be member of that scope with reviewer-capable role
        - Excludes exclude_user_id (4-eyes principle)

        Returns users with pending review count.
        """
        from sqlalchemy import func as sqlalchemy_func

        from app.models.models import Review, ReviewStatus, ScopeMembership

        # Eligible roles within a scope for reviewing
        eligible_scope_roles = ["admin", "curator", "reviewer", "scope_admin"]

        # Base query for active users
        query = db.query(UserNew).filter(UserNew.is_active == True)  # noqa: E712

        # Exclude current user (4-eyes principle)
        if exclude_user_id:
            query = query.filter(UserNew.id != exclude_user_id)

        # Filter by scope membership if scope_id provided
        if scope_id:
            # Subquery to get user IDs with eligible roles in the scope
            scope_member_ids = (
                db.query(ScopeMembership.user_id)
                .filter(
                    ScopeMembership.scope_id == scope_id,
                    ScopeMembership.is_active == True,  # noqa: E712
                    ScopeMembership.role.in_(eligible_scope_roles),
                )
                .subquery()
            )
            query = query.filter(UserNew.id.in_(select(scope_member_ids)))

        users = query.order_by(UserNew.name).all()

        # Get pending review counts and scope roles
        result = []
        for user in users:
            pending_count = (
                db.query(sqlalchemy_func.count(Review.id))
                .filter(
                    Review.reviewer_id == user.id,
                    Review.status == ReviewStatus.PENDING,
                )
                .scalar()
                or 0
            )

            # Get scope roles for this user
            scope_roles_query = db.query(ScopeMembership.role).filter(
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active == True,  # noqa: E712
            )
            if scope_id:
                scope_roles_query = scope_roles_query.filter(
                    ScopeMembership.scope_id == scope_id
                )

            scope_roles = list({r[0] for r in scope_roles_query.all()})

            result.append(
                {
                    "id": user.id,
                    "name": user.name or user.email.split("@")[0],
                    "email": user.email,
                    "role": user.role.value
                    if hasattr(user.role, "value")
                    else user.role,
                    "institution": user.institution,
                    "expertise_areas": user.expertise_areas or [],
                    "is_active": user.is_active,
                    "pending_review_count": pending_count,
                    "scope_roles": scope_roles,
                }
            )

        return result


# Create singleton instance
workflow_engine = WorkflowEngine()
