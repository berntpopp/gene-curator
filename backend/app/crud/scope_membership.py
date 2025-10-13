"""
CRUD operations for scope memberships (multi-tenant user-scope relationships).

This module provides database operations for managing scope memberships,
including invitations, role management, and member queries with user details.

Created: 2025-10-13
Author: Claude Code (Automated Implementation)
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.models import Scope, ScopeMembership, UserNew
from app.schemas.scope_membership import (
    ScopeMemberListResponse,
    ScopeMembershipCreate,
    ScopeMembershipResponse,
    ScopeMembershipUpdate,
)

logger = get_logger(__name__)


class ScopeMembershipCRUD(CRUDBase[ScopeMembership, ScopeMembershipCreate, ScopeMembershipUpdate]):
    """
    CRUD operations for scope memberships.

    Extends CRUDBase with specialized methods for invitation workflow,
    role management, and member queries with user details.
    """

    def create_invitation(
        self,
        db: Session,
        *,
        scope_id: UUID,
        invited_by_id: UUID,
        obj_in: ScopeMembershipCreate,
    ) -> ScopeMembership:
        """
        Create a new scope membership invitation.

        Args:
            db: Database session
            scope_id: Scope UUID
            invited_by_id: UUID of user creating invitation
            obj_in: Invitation data (user_id or email, role, notes)

        Returns:
            Created ScopeMembership object (pending acceptance if user exists)

        Raises:
            ValueError: If user_id provided but user doesn't exist
            ValueError: If user is already a member
        """
        # Validate user exists if user_id provided
        if obj_in.user_id:
            user = db.query(UserNew).filter(UserNew.id == obj_in.user_id).first()
            if not user:
                logger.warning(
                    "Invitation creation failed: user not found",
                    user_id=str(obj_in.user_id),
                    scope_id=str(scope_id),
                )
                raise ValueError("User not found")

            # Check if user is already a member
            existing = (
                db.query(ScopeMembership)
                .filter(
                    ScopeMembership.scope_id == scope_id,
                    ScopeMembership.user_id == obj_in.user_id,
                )
                .first()
            )
            if existing:
                logger.warning(
                    "Invitation creation failed: user already a member",
                    user_id=str(obj_in.user_id),
                    scope_id=str(scope_id),
                    existing_membership_id=str(existing.id),
                )
                raise ValueError("User is already a member of this scope")

        # Create membership
        membership = ScopeMembership(
            scope_id=scope_id,
            user_id=obj_in.user_id,  # May be None for email invitations
            role=obj_in.role.value,
            invited_by=invited_by_id,
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow() if obj_in.user_id else None,  # Auto-accept for existing users
            is_active=True,
            team_id=obj_in.team_id,
            notes=obj_in.notes,
        )

        db.add(membership)
        db.commit()
        db.refresh(membership)

        logger.info(
            "Scope membership invitation created",
            membership_id=str(membership.id),
            scope_id=str(scope_id),
            user_id=str(obj_in.user_id) if obj_in.user_id else None,
            email=obj_in.email,
            role=obj_in.role.value,
            invited_by=str(invited_by_id),
        )

        return membership

    def accept_invitation(
        self,
        db: Session,
        *,
        membership_id: UUID,
        user_id: UUID,
    ) -> ScopeMembership:
        """
        Accept a pending scope membership invitation.

        Args:
            db: Database session
            membership_id: Membership UUID
            user_id: UUID of user accepting invitation

        Returns:
            Updated ScopeMembership object

        Raises:
            ValueError: If membership not found or not pending
            ValueError: If user_id doesn't match membership
        """
        # Query with SELECT FOR SHARE (TOCTOU prevention)
        membership = (
            db.query(ScopeMembership)
            .filter(ScopeMembership.id == membership_id)
            .with_for_update(read=True)
            .first()
        )

        if not membership:
            logger.warning(
                "Accept invitation failed: membership not found",
                membership_id=str(membership_id),
                user_id=str(user_id),
            )
            raise ValueError("Invitation not found")

        if membership.user_id != user_id:
            logger.warning(
                "Accept invitation failed: user mismatch",
                membership_id=str(membership_id),
                expected_user_id=str(membership.user_id),
                actual_user_id=str(user_id),
            )
            raise ValueError("Invitation is not for this user")

        if membership.accepted_at is not None:
            logger.warning(
                "Accept invitation failed: already accepted",
                membership_id=str(membership_id),
                accepted_at=membership.accepted_at.isoformat(),
            )
            raise ValueError("Invitation already accepted")

        # Accept invitation
        membership.accepted_at = datetime.utcnow()
        db.commit()
        db.refresh(membership)

        logger.info(
            "Scope membership invitation accepted",
            membership_id=str(membership_id),
            user_id=str(user_id),
            scope_id=str(membership.scope_id),
            role=membership.role,
        )

        return membership

    def list_members(
        self,
        db: Session,
        *,
        scope_id: UUID,
        include_pending: bool = False,
    ) -> ScopeMemberListResponse:
        """
        List all members of a scope with user details.

        Performs JOIN with users_new table to include user information.
        Computes statistics (active count, pending count, role counts).

        Args:
            db: Database session
            scope_id: Scope UUID
            include_pending: Whether to include pending invitations

        Returns:
            ScopeMemberListResponse with members and statistics
        """
        # Base query with JOIN to users_new
        query = (
            db.query(
                ScopeMembership,
                UserNew.username,
                UserNew.email,
                UserNew.full_name,
                UserNew.orcid,
            )
            .join(UserNew, ScopeMembership.user_id == UserNew.id)
            .filter(ScopeMembership.scope_id == scope_id)
        )

        # Filter by acceptance status
        if not include_pending:
            query = query.filter(ScopeMembership.accepted_at.isnot(None))

        # Execute query
        results = query.all()

        # Build response objects
        members = []
        for membership, username, email, full_name, orcid in results:
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
                user_username=username,
                user_email=email,
                user_full_name=full_name,
                user_orcid=orcid,
            )
            members.append(member_response)

        # Compute statistics
        total = len(members)
        active_count = sum(1 for m in members if m.is_active and not m.is_pending)
        pending_count = sum(1 for m in members if m.is_pending)

        # Count by role
        role_counts: dict[str, int] = {}
        for role in ScopeRole:
            role_counts[role.value] = sum(
                1 for m in members if m.role == role and m.is_active and not m.is_pending
            )

        logger.debug(
            "Listed scope members",
            scope_id=str(scope_id),
            total=total,
            active_count=active_count,
            pending_count=pending_count,
            role_counts=role_counts,
        )

        return ScopeMemberListResponse(
            scope_id=scope_id,
            total=total,
            members=members,
            active_count=active_count,
            pending_count=pending_count,
            role_counts=role_counts,
        )

    def update_role(
        self,
        db: Session,
        *,
        membership_id: UUID,
        new_role: ScopeRole,
        updated_by_id: UUID,
    ) -> ScopeMembership:
        """
        Update a member's role in a scope.

        Args:
            db: Database session
            membership_id: Membership UUID
            new_role: New ScopeRole
            updated_by_id: UUID of user making the change

        Returns:
            Updated ScopeMembership object

        Raises:
            ValueError: If membership not found
        """
        # Query with SELECT FOR SHARE (TOCTOU prevention)
        membership = (
            db.query(ScopeMembership)
            .filter(ScopeMembership.id == membership_id)
            .with_for_update(read=True)
            .first()
        )

        if not membership:
            logger.warning(
                "Update role failed: membership not found",
                membership_id=str(membership_id),
            )
            raise ValueError("Membership not found")

        old_role = membership.role
        membership.role = new_role.value
        db.commit()
        db.refresh(membership)

        logger.info(
            "Scope membership role updated",
            membership_id=str(membership_id),
            user_id=str(membership.user_id),
            scope_id=str(membership.scope_id),
            old_role=old_role,
            new_role=new_role.value,
            updated_by=str(updated_by_id),
        )

        return membership

    def remove_member(
        self,
        db: Session,
        *,
        membership_id: UUID,
        removed_by_id: UUID,
    ) -> ScopeMembership:
        """
        Remove a member from a scope (soft delete - sets is_active=False).

        Args:
            db: Database session
            membership_id: Membership UUID
            removed_by_id: UUID of user removing the member

        Returns:
            Deactivated ScopeMembership object

        Raises:
            ValueError: If membership not found
        """
        # Query with SELECT FOR SHARE (TOCTOU prevention)
        membership = (
            db.query(ScopeMembership)
            .filter(ScopeMembership.id == membership_id)
            .with_for_update(read=True)
            .first()
        )

        if not membership:
            logger.warning(
                "Remove member failed: membership not found",
                membership_id=str(membership_id),
            )
            raise ValueError("Membership not found")

        membership.is_active = False
        db.commit()
        db.refresh(membership)

        logger.info(
            "Scope membership removed",
            membership_id=str(membership_id),
            user_id=str(membership.user_id),
            scope_id=str(membership.scope_id),
            role=membership.role,
            removed_by=str(removed_by_id),
        )

        return membership

    def get_user_scopes(
        self,
        db: Session,
        *,
        user_id: UUID,
        role_filter: ScopeRole | None = None,
    ) -> list[tuple[Scope, ScopeMembership]]:
        """
        Get all scopes a user is a member of, with membership details.

        Args:
            db: Database session
            user_id: User UUID
            role_filter: Optional role filter (e.g., only scopes where user is admin)

        Returns:
            List of (Scope, ScopeMembership) tuples
        """
        query = (
            db.query(Scope, ScopeMembership)
            .join(ScopeMembership, Scope.id == ScopeMembership.scope_id)
            .filter(
                ScopeMembership.user_id == user_id,
                ScopeMembership.is_active == True,  # noqa: E712
                ScopeMembership.accepted_at.isnot(None),
            )
        )

        if role_filter:
            query = query.filter(ScopeMembership.role == role_filter.value)

        results = query.all()

        logger.debug(
            "Retrieved user scopes",
            user_id=str(user_id),
            role_filter=role_filter.value if role_filter else None,
            count=len(results),
        )

        return results

    def get_user_role_in_scope(
        self,
        db: Session,
        *,
        user_id: UUID,
        scope_id: UUID,
    ) -> ScopeRole | None:
        """
        Get a user's role in a specific scope.

        Args:
            db: Database session
            user_id: User UUID
            scope_id: Scope UUID

        Returns:
            ScopeRole if user is an active member, None otherwise
        """
        membership = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.user_id == user_id,
                ScopeMembership.scope_id == scope_id,
                ScopeMembership.is_active == True,  # noqa: E712
                ScopeMembership.accepted_at.isnot(None),
            )
            .first()
        )

        if membership:
            return ScopeRole(membership.role)
        return None


# Create singleton instance
scope_membership_crud = ScopeMembershipCRUD(ScopeMembership)
