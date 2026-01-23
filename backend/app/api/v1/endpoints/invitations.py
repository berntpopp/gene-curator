"""
User-facing invitation management API endpoints.

This module provides endpoints for users to view and respond to their
scope membership invitations (GitHub-style invitation workflow).

Key Features:
- View pending invitations with scope details
- Accept invitations (already exists in scope_memberships.py)
- Decline invitations

Created: 2025-01-13
Author: Claude Code (Automated Implementation)
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.models import Scope, ScopeMembership, User, UserNew
from app.schemas.invitation import (
    PendingInvitationResponse,
    PendingInvitationsListResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/me/invitations", response_model=PendingInvitationsListResponse)
def get_my_pending_invitations(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    include_expired: bool = False,
) -> PendingInvitationsListResponse:
    """
    Get current user's pending scope invitations.

    Returns all pending invitations for the authenticated user,
    including scope details, inviter information, and expiration status.

    Args:
        db: Database session
        current_user: Authenticated user
        include_expired: Whether to include expired invitations

    Returns:
        PendingInvitationsListResponse with list of pending invitations
    """
    now = datetime.now(timezone.utc)

    # Query pending invitations with scope and inviter details
    stmt = (
        select(
            ScopeMembership,
            Scope.name.label("scope_name"),
            Scope.display_name.label("scope_display_name"),
            UserNew.name.label("inviter_name"),
            UserNew.email.label("inviter_email"),
        )
        .join(Scope, ScopeMembership.scope_id == Scope.id)
        .outerjoin(UserNew, ScopeMembership.invited_by == UserNew.id)
        .where(
            ScopeMembership.user_id == current_user.id,
            ScopeMembership.accepted_at.is_(None),  # Pending
            ScopeMembership.is_active.is_(True),
        )
    )

    # Filter out expired unless requested
    if not include_expired:
        stmt = stmt.where(
            (ScopeMembership.expires_at.is_(None)) | (ScopeMembership.expires_at > now)
        )

    results = db.execute(stmt).all()

    # Build response
    invitations = []
    for (
        membership,
        scope_name,
        scope_display_name,
        inviter_name,
        inviter_email,
    ) in results:
        is_expired = membership.expires_at is not None and membership.expires_at < now

        invitation = PendingInvitationResponse(
            id=membership.id,
            scope_id=membership.scope_id,
            scope_name=scope_name,
            scope_display_name=scope_display_name,
            role=ScopeRole(membership.role),
            invited_by=membership.invited_by,
            inviter_name=inviter_name,
            inviter_email=inviter_email,
            invited_at=membership.invited_at,
            expires_at=membership.expires_at,
            is_expired=is_expired,
            notes=membership.notes,
        )
        invitations.append(invitation)

    logger.debug(
        "Retrieved pending invitations for user",
        user_id=str(current_user.id),
        count=len(invitations),
        include_expired=include_expired,
    )

    return PendingInvitationsListResponse(
        invitations=invitations,
        total=len(invitations),
    )


@router.post(
    "/invitations/{invitation_id}/decline", status_code=status.HTTP_204_NO_CONTENT
)
def decline_invitation(
    *,
    db: Session = Depends(get_db),
    invitation_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """
    Decline a scope membership invitation.

    Soft-deletes the invitation by setting is_active=False.
    The user must be the invited user.

    Args:
        db: Database session
        invitation_id: Membership/invitation UUID
        current_user: Authenticated user (must match invited user)

    Raises:
        HTTPException 404: Invitation not found
        HTTPException 403: User not authorized (not the invited user)
        HTTPException 400: Invitation already accepted or declined
    """
    # Fetch the invitation
    membership = db.execute(
        select(ScopeMembership)
        .where(ScopeMembership.id == invitation_id)
        .with_for_update(read=True)  # TOCTOU prevention
    ).scalar_one_or_none()

    if not membership:
        logger.warning(
            "Decline invitation failed: not found",
            invitation_id=str(invitation_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Verify this is the invited user
    if membership.user_id != current_user.id:
        logger.warning(
            "Decline invitation failed: user mismatch",
            invitation_id=str(invitation_id),
            expected_user_id=str(membership.user_id),
            actual_user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only decline invitations sent to you",
        )

    # Verify invitation is still pending
    if membership.accepted_at is not None:
        logger.warning(
            "Decline invitation failed: already accepted",
            invitation_id=str(invitation_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot decline an already accepted invitation",
        )

    if not membership.is_active:
        logger.warning(
            "Decline invitation failed: already declined",
            invitation_id=str(invitation_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been declined",
        )

    # Soft delete the invitation
    membership.is_active = False
    db.commit()

    logger.info(
        "Scope invitation declined",
        invitation_id=str(invitation_id),
        user_id=str(current_user.id),
        scope_id=str(membership.scope_id),
        role=membership.role,
    )
