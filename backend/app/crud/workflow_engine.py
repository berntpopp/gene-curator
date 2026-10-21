"""
Multi-stage workflow engine for schema-agnostic curation system.
Implements the 5-stage pipeline: Entry → Precuration → Curation → Review → Active
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ScopeRole
from app.crud.activation import activate_item
from app.crud.review_round import (
    all_reviews_approved,
    check_review_open,
    in_current_round,
    pending_reviews,
    reassign_earlier_reviewers,
)
from app.crud.workflow_statistics import compute_workflow_statistics
from app.models import (
    ActiveCuration,
    CurationNew,
    CurationStatus,
    NotificationNew,
    NotificationType,
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
                WorkflowStage.REVIEW,
                WorkflowStage.ENTRY,
            ],  # Can go back to entry
            # Curation workflow
            WorkflowStage.CURATION: [
                WorkflowStage.REVIEW,
                WorkflowStage.PRECURATION,
            ],  # Can go back to precuration
            # Review workflow
            WorkflowStage.REVIEW: [
                WorkflowStage.PRECURATION,
                WorkflowStage.ACTIVE,
                WorkflowStage.CURATION,
            ],  # Can send back to curation
            WorkflowStage.ACTIVE: [
                WorkflowStage.REVIEW
            ],  # Can be sent back for re-review
            WorkflowStage.ARCHIVED: [],  # terminal
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
                is_valid=False,
                errors=errors,
                warnings=warnings,
                requirements=requirements,
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
            errors.extend(
                self._validate_4_eyes_principle(db, user, user_id, item, item_type)
            )

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

        try:
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

            # Emit notifications for workflow transitions
            self._emit_transition_notification(
                db, item, item_type, current_stage, target_stage, user_id
            )

            transition = WorkflowTransition(
                item_id=item_id,
                item_type=item_type,
                from_stage=current_stage,
                to_stage=target_stage,
                executed_by=user_id,
                executed_at=datetime.now(UTC),
                notes=notes,
                metadata=metadata or {},
                **transition_result,
            )
            db.commit()
            return transition
        except Exception:
            db.rollback()
            raise

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
                item.updated_at if hasattr(item, "updated_at") else datetime.now(UTC)
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
        # Review.curation_id references curations only; precurations cannot be reviewed
        if item_type != "curation":
            raise ValueError("Peer review is only supported for curations")

        current_stage, _item = self._get_current_stage_and_item(db, item_id, item_type)

        if current_stage != WorkflowStage.REVIEW:
            raise ValueError("Item must be in review stage to assign peer reviewer")

        # Validate reviewer is different from creator
        curation_result = (
            db.execute(select(CurationNew).where(CurationNew.id == item_id))
            .scalars()
            .first()
        )
        if not curation_result:
            raise ValueError("Curation not found")
        if reviewer_id == curation_result.created_by:
            raise ValueError(
                "4-eyes principle violation: Cannot assign original creator as reviewer"
            )

        # Create review assignment
        review = Review(
            curation_id=item_id,
            reviewer_id=reviewer_id,
            assigned_by=assigned_by,
            status=ReviewStatus.PENDING,
            assigned_at=datetime.now(UTC),
        )

        try:
            db.add(review)
            db.flush()

            # Notify the assigned reviewer

            gene_symbol = "Unknown"
            if (
                item_type == "curation"
                and curation_result
                and hasattr(curation_result, "gene")
                and curation_result.gene
            ):
                gene_symbol = getattr(
                    curation_result.gene, "approved_symbol", "Unknown"
                )

            db.add(
                NotificationNew(
                    user_id=reviewer_id,
                    type=NotificationType.REVIEW_ASSIGNED,
                    title="New review assigned",
                    message=f"New review assigned: {gene_symbol}",
                    link=f"/scopes/{curation_result.scope_id}/curations/{item_id}",
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

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

    @staticmethod
    def _return_to_curator(
        db: Session, curation: CurationNew | None, decision: str
    ) -> None:
        """Editing is gated on DRAFT/REJECTED, so hand the curation back (#354)."""
        if curation and decision != "approve":
            curation.workflow_stage = WorkflowStage.CURATION
            curation.status = (
                CurationStatus.REJECTED
                if decision == "reject"
                else CurationStatus.DRAFT
            )
            db.flush()

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

        check_review_open(db, review)

        # Valid decisions
        valid_decisions = ["approve", "request_changes", "reject"]
        if decision not in valid_decisions:
            raise ValueError(f"Invalid decision. Must be one of: {valid_decisions}")

        try:
            # Update review
            review.status = {
                "approve": ReviewStatus.APPROVED,
                "request_changes": ReviewStatus.NEEDS_REVISION,
                "reject": ReviewStatus.REJECTED,
            }[decision]
            review.recommendation = decision
            review.comments = comments
            review.feedback_data = suggested_changes or {}
            review.reviewed_at = func.now()  # DB clock, like audit timestamps

            db.flush()

            # Notify the curation creator of the review decision

            curation = (
                db.execute(
                    select(CurationNew).where(CurationNew.id == review.curation_id)
                )
                .scalars()
                .first()
            )
            self._return_to_curator(db, curation, decision)

            if curation and curation.created_by and curation.created_by != reviewer_id:
                gene_symbol = "Unknown"
                if hasattr(curation, "gene") and curation.gene:
                    gene_symbol = getattr(curation.gene, "approved_symbol", "Unknown")

                notification_config = {
                    "reject": (
                        NotificationType.CURATION_REJECTED,
                        "Curation rejected",
                        f"Curation rejected: {gene_symbol}",
                    ),
                    "request_changes": (
                        NotificationType.REVISION_REQUESTED,
                        "Revision requested",
                        f"Revision requested: {gene_symbol}",
                    ),
                }.get(decision)

                if notification_config:
                    notification_type, title, message = notification_config
                    db.add(
                        NotificationNew(
                            user_id=curation.created_by,
                            type=notification_type,
                            title=title,
                            message=message,
                            link=f"/scopes/{curation.scope_id}/curations/{curation.id}",
                        )
                    )

            all_reviews_complete = (
                decision == "approve"
                and self._check_all_reviews_complete(
                    db, review.curation_id, item_type="curation"
                )
            )
            if all_reviews_complete:
                self.execute_transition(
                    db,
                    review.curation_id,
                    "curation",
                    WorkflowStage.ACTIVE,
                    reviewer_id,
                    notes="All peer reviews approved - automatically activated",
                )
            else:
                db.commit()
        except Exception:
            db.rollback()
            raise

        return {
            "review_id": review_id,
            "decision": decision,
            "status": "completed",
            "auto_transitioned": all_reviews_complete,
        }

    def get_workflow_statistics(
        self, db: Session, scope_id: UUID | None = None, days: int = 30
    ) -> WorkflowStatistics:
        """Get workflow performance statistics."""
        return compute_workflow_statistics(
            db, scope_id, days, self._calculate_average_stage_time
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
        curator_roles = ["curator", "admin"]
        review_roles = [*curator_roles, "reviewer"]
        role_matrix = {
            (WorkflowStage.ENTRY, WorkflowStage.PRECURATION): curator_roles,
            (WorkflowStage.PRECURATION, WorkflowStage.CURATION): curator_roles,
            (WorkflowStage.PRECURATION, WorkflowStage.REVIEW): curator_roles,
            (WorkflowStage.CURATION, WorkflowStage.REVIEW): curator_roles,
            (WorkflowStage.REVIEW, WorkflowStage.ACTIVE): review_roles,
            # Backwards transitions
            (WorkflowStage.PRECURATION, WorkflowStage.ENTRY): curator_roles,
            (WorkflowStage.CURATION, WorkflowStage.PRECURATION): curator_roles,
            (WorkflowStage.REVIEW, WorkflowStage.PRECURATION): ["reviewer", "admin"],
            (WorkflowStage.REVIEW, WorkflowStage.CURATION): review_roles,
            (WorkflowStage.ACTIVE, WorkflowStage.REVIEW): ["admin"],
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
            # Keep only valid scope roles (admin, curator, reviewer, viewer)
            scope_role_requirements = [r for r in role_requirements if r in ScopeRole]

            membership = (
                db.query(ScopeMembership)
                .filter(
                    ScopeMembership.user_id == user.id,
                    ScopeMembership.scope_id == scope_id,
                    ScopeMembership.is_active,
                    ScopeMembership.accepted_at.isnot(None),
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
            eligible_scope_roles = [r.value for r in ScopeRole if r != ScopeRole.VIEWER]
            membership = (
                db.query(ScopeMembership)
                .filter(
                    ScopeMembership.user_id == user.id,
                    ScopeMembership.scope_id == item.scope_id,
                    ScopeMembership.is_active,
                    ScopeMembership.accepted_at.isnot(None),
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
        db.flush()
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
        db.flush()
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
        if isinstance(item, CurationNew):
            item.submitted_at = datetime.now(UTC)  # starts a new review round
            item.submitted_by = user_id
        if isinstance(item, PrecurationNew):
            item.status = CurationStatus.SUBMITTED
            item.is_draft = False
            item.updated_by = user_id
            item.updated_at = datetime.now(UTC)
        db.flush()
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
        activate_item(db, item, user_id)
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
        db.flush()
        return {"success": True, "message": "Transitioned back to entry"}

    def _emit_transition_notification(
        self,
        db: Session,
        item: Any,
        item_type: str,
        from_stage: WorkflowStage,
        to_stage: WorkflowStage,
        acted_by: UUID,
    ) -> None:
        """Emit notifications for workflow state transitions."""

        # Determine gene symbol for notification message
        gene_symbol = "Unknown"
        if hasattr(item, "gene") and item.gene:
            gene_symbol = getattr(item.gene, "approved_symbol", "Unknown")

        creator_id = getattr(item, "created_by", None)

        # CURATION → REVIEW: earlier reviewers get a new review in the new round
        if (
            from_stage == WorkflowStage.CURATION
            and to_stage == WorkflowStage.REVIEW
            and isinstance(item, CurationNew)
        ):
            for reviewer_id in reassign_earlier_reviewers(db, item, acted_by):
                db.add(
                    NotificationNew(
                        user_id=reviewer_id,
                        type=NotificationType.REVIEW_ASSIGNED,
                        title="New review assigned",
                        message=f"New review assigned: {gene_symbol}",
                        link=f"/scopes/{item.scope_id}/curations/{item.id}",
                    )
                )

        # REVIEW → ACTIVE: notify the curator (creator) of approval
        elif from_stage == WorkflowStage.REVIEW and to_stage == WorkflowStage.ACTIVE:
            if creator_id and creator_id != acted_by:
                db.add(
                    NotificationNew(
                        user_id=creator_id,
                        type=NotificationType.CURATION_APPROVED,
                        title="Curation approved",
                        message=f"Curation approved: {gene_symbol}",
                        link=f"/scopes/{item.scope_id}/curations/{item.id}",
                    )
                )

        # REVIEW → CURATION: notify the curator of rejection/revision request
        elif (
            from_stage == WorkflowStage.REVIEW
            and to_stage == WorkflowStage.CURATION
            and creator_id
            and creator_id != acted_by
        ):
            db.add(
                NotificationNew(
                    user_id=creator_id,
                    type=NotificationType.REVISION_REQUESTED,
                    title="Revision requested",
                    message=f"Revision requested: {gene_symbol}",
                    link=f"/scopes/{item.scope_id}/curations/{item.id}",
                )
            )

    def _get_workflow_history(
        self, db: Session, item_id: UUID, item_type: str
    ) -> list[dict[str, Any]]:
        """Get workflow transition history."""
        # This would query the audit log for workflow transitions
        return []

    def _get_pending_reviews(
        self, db: Session, item_id: UUID, item_type: str
    ) -> list[dict[str, Any]]:
        """Get pending peer reviews (current round) for an item."""
        return pending_reviews(db, item_id)

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
        return all_reviews_approved(db, item_id)

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
        eligible_scope_roles = [r.value for r in ScopeRole if r != ScopeRole.VIEWER]

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
                    ScopeMembership.accepted_at.isnot(None),
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
                    in_current_round,
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
