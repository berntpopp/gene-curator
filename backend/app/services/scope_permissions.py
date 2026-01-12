"""Scope-based permission service for access control

This service centralizes all permission logic for scope-based operations,
implementing the four-eyes principle and role-based access control.

Design Principles:
- Single Responsibility: Only handles permission checks
- Stateless: All methods are pure functions
- Type Safety: Full type hints for all operations
- Performance: Optimized queries with minimal database hits
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.core.logging import get_logger
from app.models.models import CurationNew, Scope, ScopeMembership, UserNew

logger = get_logger(__name__)


class ScopePermissionService:
    """Centralized scope-based permission logic

    This service implements:
    - Public/private scope visibility
    - Scope membership verification
    - Role-based curation access (curator, reviewer, scope_admin)
    - Four-eyes principle (cannot approve own curations)
    """

    @staticmethod
    def can_view_scope(db: Session, user: UserNew | None, scope: Scope) -> bool:
        """Check if user can view scope

        Public scopes are visible to everyone (including anonymous users).
        Private scopes require authentication and membership.

        Args:
            db: Database session
            user: Current user (None for anonymous)
            scope: Scope to check

        Returns:
            True if user can view scope, False otherwise
        """
        # Public scopes: anyone can view
        if scope.is_public:
            logger.debug(
                "Scope is public", scope_id=str(scope.id), scope_name=scope.name
            )
            return True

        # Private scopes: must be authenticated and member
        if user is None:
            logger.debug(
                "Anonymous user cannot view private scope",
                scope_id=str(scope.id),
                scope_name=scope.name,
            )
            return False

        # Admin can view all
        if user.role.value == "admin":
            logger.debug(
                "Admin can view all scopes",
                user_id=str(user.id),
                scope_id=str(scope.id),
            )
            return True

        # Check if user is scope member
        is_member = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.scope_id == scope.id,
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
            )
            .count()
            > 0
        )

        logger.debug(
            "Scope membership check",
            user_id=str(user.id),
            scope_id=str(scope.id),
            is_member=is_member,
        )

        return is_member

    @staticmethod
    def can_view_curation(
        db: Session, user: UserNew | None, curation: CurationNew
    ) -> bool:
        """Check if user can view curation

        Curation visibility is determined by the scope it belongs to.

        Args:
            db: Database session
            user: Current user (None for anonymous)
            curation: Curation to check

        Returns:
            True if user can view curation, False otherwise
        """
        scope = db.query(Scope).filter(Scope.id == curation.scope_id).first()

        if not scope:
            logger.warning(
                "Curation references non-existent scope",
                curation_id=str(curation.id),
                scope_id=str(curation.scope_id),
            )
            return False

        can_view = ScopePermissionService.can_view_scope(db, user, scope)

        logger.debug(
            "Curation view permission check",
            curation_id=str(curation.id),
            scope_id=str(scope.id),
            can_view=can_view,
        )

        return can_view

    @staticmethod
    def can_create_curation(db: Session, user: UserNew, scope_id: UUID) -> bool:
        """Check if user can create curation in scope

        Only authenticated users with curator or scope_admin role can create curations.

        Args:
            db: Database session
            user: Current user (must be authenticated)
            scope_id: Scope to create curation in

        Returns:
            True if user can create curation, False otherwise
        """
        # Admin can create in all scopes
        if user.role.value == "admin":
            logger.debug(
                "Admin can create curations in all scopes",
                user_id=str(user.id),
                scope_id=str(scope_id),
            )
            return True

        # Check if scope exists
        scope = db.query(Scope).filter(Scope.id == scope_id).first()
        if not scope:
            logger.warning(
                "Scope not found for curation creation",
                scope_id=str(scope_id),
                user_id=str(user.id),
            )
            return False

        # Must be scope member with curator+ role
        member = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.scope_id == scope_id,
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
            )
            .first()
        )

        if not member:
            logger.debug(
                "User is not a member of scope",
                user_id=str(user.id),
                scope_id=str(scope_id),
            )
            return False

        can_create = member.role in ["curator", "scope_admin"]

        logger.debug(
            "Curation creation permission check",
            user_id=str(user.id),
            scope_id=str(scope_id),
            member_role=member.role,
            can_create=can_create,
        )

        return can_create

    @staticmethod
    def can_edit_curation(db: Session, user: UserNew, curation: CurationNew) -> bool:
        """Check if user can edit curation

        Editing rules:
        - Admins can edit all curations
        - Creators can edit own curations (if not in review/active stage)
        - Scope admins can edit any curation in their scope

        Args:
            db: Database session
            user: Current user (must be authenticated)
            curation: Curation to check

        Returns:
            True if user can edit curation, False otherwise
        """
        # Admin can edit all
        if user.role.value == "admin":
            logger.debug(
                "Admin can edit all curations",
                user_id=str(user.id),
                curation_id=str(curation.id),
            )
            return True

        # Creator can edit own curations (if not in review/active)
        if curation.created_by == user.id and curation.workflow_stage.value not in [
            "review",
            "active",
        ]:
            logger.debug(
                "Creator can edit own curation",
                user_id=str(user.id),
                curation_id=str(curation.id),
                stage=curation.workflow_stage.value,
            )
            return True

        # Scope admin can edit any curation in their scope
        scope_member = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.scope_id == curation.scope_id,
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
            )
            .first()
        )

        if scope_member and scope_member.role == "scope_admin":
            logger.debug(
                "Scope admin can edit curation",
                user_id=str(user.id),
                curation_id=str(curation.id),
                scope_id=str(curation.scope_id),
            )
            return True

        logger.debug(
            "User cannot edit curation",
            user_id=str(user.id),
            curation_id=str(curation.id),
            created_by=str(curation.created_by) if curation.created_by else None,
            stage=curation.workflow_stage.value,
        )

        return False

    @staticmethod
    def can_approve_curation(db: Session, user: UserNew, curation: CurationNew) -> bool:
        """Check if user can approve/activate curation (4-eyes principle)

        Approval rules (4-eyes principle):
        - Admins can approve all curations
        - Cannot approve own curation (4-eyes)
        - Must be scope member with reviewer or scope_admin role

        Args:
            db: Database session
            user: Current user (must be authenticated)
            curation: Curation to check

        Returns:
            True if user can approve curation, False otherwise
        """
        # Admin can approve all
        if user.role.value == "admin":
            logger.debug(
                "Admin can approve all curations",
                user_id=str(user.id),
                curation_id=str(curation.id),
            )
            return True

        # Cannot approve own curation (4-eyes)
        if curation.created_by == user.id:
            logger.info(
                "User cannot approve own curation (4-eyes principle)",
                user_id=str(user.id),
                curation_id=str(curation.id),
            )
            return False

        # Must be scope member with reviewer+ role
        scope_member = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.scope_id == curation.scope_id,
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
            )
            .first()
        )

        if not scope_member:
            logger.debug(
                "User is not a member of scope",
                user_id=str(user.id),
                curation_id=str(curation.id),
                scope_id=str(curation.scope_id),
            )
            return False

        can_approve = scope_member.role in ["reviewer", "scope_admin"]

        logger.debug(
            "Curation approval permission check",
            user_id=str(user.id),
            curation_id=str(curation.id),
            member_role=scope_member.role,
            can_approve=can_approve,
        )

        return can_approve

    @staticmethod
    def get_visible_scopes(db: Session, user: UserNew | None) -> list[Scope]:
        """Get all scopes visible to user

        Visibility rules:
        - Anonymous users: only public scopes
        - Admins: all active scopes
        - Authenticated users: public scopes + private scopes where user is member

        Args:
            db: Database session
            user: Current user (None for anonymous)

        Returns:
            List of visible scopes
        """
        query = db.query(Scope).filter(Scope.is_active)

        # Anonymous: only public scopes
        if user is None:
            scopes = query.filter(Scope.is_public).all()
            logger.debug("Anonymous user visible scopes", count=len(scopes))
            return scopes

        # Admin: all scopes
        if user.role.value == "admin":
            scopes = query.all()
            logger.debug(
                "Admin visible scopes",
                user_id=str(user.id),
                count=len(scopes),
            )
            return scopes

        # Authenticated: public scopes + private scopes where user is member
        public_scopes = query.filter(Scope.is_public).all()

        member_scope_ids = (
            db.query(ScopeMembership.scope_id)
            .filter(
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active,
            )
            .all()
        )

        private_scopes = (
            query.filter(
                Scope.id.in_([sid[0] for sid in member_scope_ids]),
                ~Scope.is_public,
            ).all()
            if member_scope_ids
            else []
        )

        all_scopes = public_scopes + private_scopes

        logger.debug(
            "User visible scopes",
            user_id=str(user.id),
            public_count=len(public_scopes),
            private_count=len(private_scopes),
            total_count=len(all_scopes),
        )

        return all_scopes

    @staticmethod
    def filter_visible_curations(
        db: Session, query: Query[Any], user: UserNew | None
    ) -> Query[Any]:
        """Apply visibility filter to curation query

        Filters the query to only include curations from scopes visible to the user.

        Args:
            db: Database session
            query: SQLAlchemy query to filter
            user: Current user (None for anonymous)

        Returns:
            Filtered query
        """
        visible_scope_ids = [
            s.id for s in ScopePermissionService.get_visible_scopes(db, user)
        ]

        filtered_query = query.filter(CurationNew.scope_id.in_(visible_scope_ids))

        logger.debug(
            "Filtered curation query by visible scopes",
            visible_scope_count=len(visible_scope_ids),
            user_id=str(user.id) if user else None,
        )

        return filtered_query
