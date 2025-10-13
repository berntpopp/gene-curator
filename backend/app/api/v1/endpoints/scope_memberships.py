"""
Scope membership management API endpoints (RLS-based multi-tenant architecture).

This module provides endpoints for managing scope memberships, including invitations,
role updates, and member removal. All operations use RLS for secure access control.

Key Features:
- Invitation workflow (invite, accept, pending status)
- Role-based access control (admin can manage, members can view)
- Member listing with user details (JOIN query)
- Soft delete support (deactivation instead of hard delete)

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import deps
from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.crud.scope_membership import scope_membership_crud
from app.models import Scope, User
from app.schemas.scope_membership import (
    ScopeMemberListResponse,
    ScopeMembershipAccept,
    ScopeMembershipCreate,
    ScopeMembershipResponse,
    ScopeMembershipUpdate,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/{scope_id}/invitations",
    response_model=ScopeMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    invitation_in: ScopeMembershipCreate,
    scope: Scope = Depends(deps.require_scope_role(ScopeRole.ADMIN)),
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeMembershipResponse:
    """
    Invite a member to a scope (scope admin only).

    Creates a new scope membership invitation. If user_id is provided (existing user),
    the invitation is auto-accepted. If only email is provided (future feature),
    the invitation remains pending.

    Args:
        db: Database session
        scope_id: Scope UUID
        invitation_in: Invitation data (user_id or email, role, notes)
        scope: Scope object (dependency ensures admin access)
        current_user: Current user (inviter)

    Returns:
        Created ScopeMembershipResponse

    Raises:
        HTTPException 400: User not found or already a member
    """
    try:
        membership = scope_membership_crud.create_invitation(
            db,
            scope_id=scope_id,
            invited_by_id=current_user.id,
            obj_in=invitation_in,
        )

        logger.info(
            "Scope membership invitation created",
            scope_id=str(scope_id),
            scope_name=scope.name,
            invited_user_id=str(invitation_in.user_id)
            if invitation_in.user_id
            else None,
            invited_email=invitation_in.email,
            role=invitation_in.role.value,
            invited_by=str(current_user.id),
            invited_by_username=current_user.name,
        )

        # Build response with user details
        member_response = ScopeMembershipResponse(
            id=membership.id,
            scope_id=membership.scope_id,
            user_id=membership.user_id,
            role=ScopeRole(membership.role),
            invited_by=membership.invited_by,
            invited_at=membership.invited_at,
            accepted_at=membership.accepted_at,
            is_active=membership.is_active,
            is_pending=membership.accepted_at is None,
            team_id=membership.team_id,
            notes=membership.notes,
            user_username=None,  # Will be populated if user exists
            user_email=None,
            user_full_name=None,
            user_orcid=None,
        )

        return member_response

    except ValueError as e:
        logger.warning(
            "Scope membership invitation failed",
            scope_id=str(scope_id),
            error=str(e),
            invited_by=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{scope_id}/invitations/{membership_id}/accept",
    response_model=ScopeMembershipResponse,
)
def accept_invitation(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    membership_id: UUID,
    accept_data: ScopeMembershipAccept | None = None,
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeMembershipResponse:
    """
    Accept a scope membership invitation.

    The current user must be the invited user. This endpoint is for accepting
    pending invitations (when accepted_at is NULL).

    Args:
        db: Database session
        scope_id: Scope UUID
        membership_id: Membership UUID
        accept_data: Optional acceptance message
        current_user: Current user (must be invited user)

    Returns:
        Updated ScopeMembershipResponse

    Raises:
        HTTPException 400: Invitation not found, user mismatch, or already accepted
    """
    try:
        membership = scope_membership_crud.accept_invitation(
            db,
            membership_id=membership_id,
            user_id=current_user.id,
        )

        logger.info(
            "Scope membership invitation accepted",
            scope_id=str(scope_id),
            membership_id=str(membership_id),
            user_id=str(current_user.id),
            user_username=current_user.name,
            role=membership.role,
        )

        # Build response
        member_response = ScopeMembershipResponse(
            id=membership.id,
            scope_id=membership.scope_id,
            user_id=membership.user_id,
            role=ScopeRole(membership.role),
            invited_by=membership.invited_by,
            invited_at=membership.invited_at,
            accepted_at=membership.accepted_at,
            is_active=membership.is_active,
            is_pending=False,
            team_id=membership.team_id,
            notes=membership.notes,
            user_username=current_user.name,
            user_email=current_user.email,
            user_full_name=current_user.name,
            user_orcid=current_user.orcid_id,
        )

        return member_response

    except ValueError as e:
        logger.warning(
            "Accept invitation failed",
            scope_id=str(scope_id),
            membership_id=str(membership_id),
            user_id=str(current_user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{scope_id}/members", response_model=ScopeMemberListResponse)
def list_members(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    include_pending: bool = False,
    scope: Scope = Depends(deps.require_scope_role(ScopeRole.VIEWER)),
) -> ScopeMemberListResponse:
    """
    List all members of a scope with statistics.

    Any scope member can view the member list. Returns member details including
    user information, roles, and membership statistics.

    Args:
        db: Database session
        scope_id: Scope UUID
        include_pending: Include pending invitations
        scope: Scope object (dependency ensures member access)

    Returns:
        ScopeMemberListResponse with members and statistics
    """
    member_list = scope_membership_crud.list_members(
        db,
        scope_id=scope_id,
        include_pending=include_pending,
    )

    logger.debug(
        "Listed scope members",
        scope_id=str(scope_id),
        total_members=member_list.total,
        active_members=member_list.active_count,
        pending_invitations=member_list.pending_count,
    )

    return member_list


@router.patch("/{scope_id}/members/{user_id}", response_model=ScopeMembershipResponse)
def update_member_role(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    user_id: UUID,
    update_data: ScopeMembershipUpdate,
    scope: Scope = Depends(deps.require_scope_role(ScopeRole.ADMIN)),
    current_user: User = Depends(deps.get_current_active_user),
) -> ScopeMembershipResponse:
    """
    Update a member's role in a scope (scope admin only).

    Scope admins can update member roles, active status, and notes.
    Cannot update invitation fields (invited_by, invited_at, accepted_at).

    Args:
        db: Database session
        scope_id: Scope UUID
        user_id: User UUID to update
        update_data: Update data (role, is_active, notes)
        scope: Scope object (dependency ensures admin access)
        current_user: Current user (updater)

    Returns:
        Updated ScopeMembershipResponse

    Raises:
        HTTPException 404: Membership not found
        HTTPException 400: Invalid update (e.g., last admin)
    """
    # Get membership by scope_id and user_id
    membership = (
        db.query(deps.ScopeMembership)
        .filter(
            deps.ScopeMembership.scope_id == scope_id,
            deps.ScopeMembership.user_id == user_id,
        )
        .first()
    )

    if not membership:
        logger.warning(
            "Update member failed: membership not found",
            scope_id=str(scope_id),
            user_id=str(user_id),
            updated_by=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Update role if provided
    if update_data.role:
        membership = scope_membership_crud.update_role(
            db,
            membership_id=membership.id,
            new_role=update_data.role,
            updated_by_id=current_user.id,
        )

    # Update is_active if provided
    if update_data.is_active is not None:
        membership.is_active = update_data.is_active
        db.commit()
        db.refresh(membership)

    # Update notes if provided
    if update_data.notes is not None:
        membership.notes = update_data.notes
        db.commit()
        db.refresh(membership)

    logger.info(
        "Scope membership updated",
        scope_id=str(scope_id),
        membership_id=str(membership.id),
        user_id=str(user_id),
        new_role=update_data.role.value if update_data.role else None,
        updated_by=str(current_user.id),
        updated_by_username=current_user.name,
    )

    # Build response
    member_response = ScopeMembershipResponse(
        id=membership.id,
        scope_id=membership.scope_id,
        user_id=membership.user_id,
        role=ScopeRole(membership.role),
        invited_by=membership.invited_by,
        invited_at=membership.invited_at,
        accepted_at=membership.accepted_at,
        is_active=membership.is_active,
        is_pending=membership.accepted_at is None,
        team_id=membership.team_id,
        notes=membership.notes,
        user_username=None,  # Could join with UserNew here if needed
        user_email=None,
        user_full_name=None,
        user_orcid=None,
    )

    return member_response


@router.delete("/{scope_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    *,
    db: Session = Depends(deps.get_db),
    scope_id: UUID,
    user_id: UUID,
    scope: Scope = Depends(deps.require_scope_role(ScopeRole.ADMIN)),
    current_user: User = Depends(deps.get_current_active_user),
) -> None:
    """
    Remove a member from a scope (scope admin only).

    Performs soft delete by setting is_active=False. The membership record is retained
    for audit purposes. Scope admins cannot remove themselves if they are the last admin.

    Args:
        db: Database session
        scope_id: Scope UUID
        user_id: User UUID to remove
        scope: Scope object (dependency ensures admin access)
        current_user: Current user (remover)

    Raises:
        HTTPException 404: Membership not found
        HTTPException 400: Cannot remove last admin
    """
    # Get membership
    membership = (
        db.query(deps.ScopeMembership)
        .filter(
            deps.ScopeMembership.scope_id == scope_id,
            deps.ScopeMembership.user_id == user_id,
        )
        .first()
    )

    if not membership:
        logger.warning(
            "Remove member failed: membership not found",
            scope_id=str(scope_id),
            user_id=str(user_id),
            removed_by=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Prevent removing last admin
    if membership.role == ScopeRole.ADMIN.value:
        admin_count = (
            db.query(deps.ScopeMembership)
            .filter(
                deps.ScopeMembership.scope_id == scope_id,
                deps.ScopeMembership.role == ScopeRole.ADMIN.value,
                deps.ScopeMembership.is_active == True,  # noqa: E712
                deps.ScopeMembership.accepted_at.isnot(None),
            )
            .count()
        )

        if admin_count <= 1:
            logger.warning(
                "Remove member failed: cannot remove last admin",
                scope_id=str(scope_id),
                user_id=str(user_id),
                removed_by=str(current_user.id),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin from a scope",
            )

    # Remove member (soft delete)
    scope_membership_crud.remove_member(
        db,
        membership_id=membership.id,
        removed_by_id=current_user.id,
    )

    logger.info(
        "Scope member removed",
        scope_id=str(scope_id),
        membership_id=str(membership.id),
        user_id=str(user_id),
        removed_by=str(current_user.id),
        removed_by_username=current_user.name,
    )
