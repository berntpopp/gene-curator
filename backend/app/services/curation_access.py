"""Who may edit, review or delete a curation, and the scope access check of its endpoints."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.capabilities import MANAGE_SCOPE, holds
from app.crud.review_round import (
    corrected_by,
    holds_review_capability,
    in_current_round,
)
from app.models import (
    AuditLogNew,
    CurationNew,
    CurationStatus,
    PrecurationNew,
    Review,
    ReviewStatus,
    ScopeMembership,
    UserNew,
)
from app.services.scope_permissions import ScopePermissionService


def _get_user_scope_role(db: Session, user_id: UUID, scope_id: UUID) -> str | None:
    """Get user's role for a specific scope from scope_memberships."""
    membership = (
        db.query(ScopeMembership)
        .filter(
            ScopeMembership.user_id == user_id,
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.is_active,
            ScopeMembership.accepted_at.isnot(None),
        )
        .first()
    )
    return membership.role if membership else None


def may_edit_curation(
    db: Session, user: UserNew, item: CurationNew | PrecurationNew
) -> bool:
    """The creator, a scope admin of its scope (#284 matrix) or a platform admin; for a
    curation or a precuration."""
    return (
        user.role == "admin"
        or item.created_by == user.id
        or holds(db, user.id, item.scope_id, MANAGE_SCOPE)
    )


def record_edit_by_other(
    db: Session, user: UserNew, item: CurationNew | PrecurationNew
) -> None:
    """D1 (#609 review): someone saving another person's curation or precuration did part
    of its work, so they may not review it (draft_edit is one of review_round.correctors).
    Added before the save, whose commit writes it."""
    if item.created_by != user.id:
        db.add(
            AuditLogNew(
                entity_type="curations"
                if isinstance(item, CurationNew)
                else "precurations",
                entity_id=item.id,
                operation="UPDATE",
                change_type="draft_edit",
                scope_id=item.scope_id,
                user_id=user.id,
            )
        )


def _can_user_edit_curation(
    db: Session, user: UserNew, curation: "CurationNew"
) -> bool:
    """Same rule as save-draft and submit: the creator (curator or scope admin), a scope
    admin of its scope or a platform admin."""
    # an adoption in review still takes diagnostics (update_curation, #613)
    adopted = curation.clingen_adoption and curation.status == CurationStatus.IN_REVIEW
    if curation.status not in [CurationStatus.DRAFT, CurationStatus.REJECTED] and not (
        adopted
    ):
        return False
    if not curation.scope.is_active:
        return False
    if user.role == "admin":
        return True
    if not may_edit_curation(db, user, curation):
        return False
    # Check scope-specific role (valid scope roles: admin, curator, reviewer, viewer)
    scope_role = _get_user_scope_role(db, user.id, curation.scope_id)
    return scope_role in ["admin", "curator"]


def _can_user_review_curation(
    db: Session, user: UserNew, curation: "CurationNew"
) -> bool:
    """
    Check if user can review (approve/reject) this curation.
    Enforces 4-eyes principle: user cannot review their own work.
    """
    # Cannot review own work (4-eyes principle)
    if curation.created_by == user.id or corrected_by(db, curation.id, user.id):
        return False

    # Must be in review status/stage
    if curation.status != CurationStatus.IN_REVIEW:
        return False

    # REVIEW capability by membership; platform admins get no bypass
    return holds_review_capability(db, user.id, curation.scope_id)


def _has_approved(db: Session, user: UserNew, curation: CurationNew) -> bool:
    """The user approved in the open review round; same rule as approving_reviewers (D1)."""
    return curation.created_by != user.id and (
        db.scalar(
            select(Review.id).where(
                Review.curation_id == curation.id,
                Review.reviewer_id == user.id,
                Review.status == ReviewStatus.APPROVED,
                Review.recommendation == "approve",
                in_current_round,
            )
        )
        is not None
    )


def _can_user_delete_curation(
    db: Session, user: UserNew, curation: "CurationNew"
) -> bool:
    """Check if user can delete this curation."""
    if not curation.scope.is_active:
        return False
    # Admin can delete anything
    if user.role == "admin":
        return True

    # Only drafts can be deleted by non-admins
    if curation.status != CurationStatus.DRAFT:
        return False

    # Creator can delete their own drafts
    if curation.created_by == user.id:
        return True

    # Scope admin (admin role within scope) can delete drafts in their scope
    scope_role = _get_user_scope_role(db, user.id, curation.scope_id)
    return scope_role == "admin"


def _check_scope_access(
    db: Session,
    current_user: UserNew,
    scope_id: UUID,
    action: str = "access",
) -> None:
    """
    Check if user has access to the specified scope using ScopePermissionService.
    Raises HTTPException if access denied.
    Uses scope_memberships table for proper scope-specific role checking.
    """
    if current_user.role == "admin":
        return  # Admin bypasses scope checks

    # Use ScopePermissionService to check membership via scope_memberships table
    from app.models import Scope

    scope = db.query(Scope).filter(Scope.id == scope_id).first()
    if not scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found",
        )

    if not ScopePermissionService.can_view_scope(db, current_user, scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} curations in this scope",
        )
