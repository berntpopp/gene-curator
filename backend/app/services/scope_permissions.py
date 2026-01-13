"""Scope-based permission service for access control

This service centralizes all permission logic for scope-based operations,
implementing the four-eyes principle and role-based access control.

Design Principles:
- Single Responsibility: Only handles permission checks
- Stateless: All methods are pure functions
- Type Safety: Full type hints for all operations
- Performance: Optimized queries with minimal database hits
- DRY: Admin bypass extracted to reusable decorator
- SOLID: Protocol interface for dependency injection

Reference: https://docs.sqlalchemy.org/en/20/orm/queryguide/query
"""

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast
from uuid import UUID

from sqlalchemy import and_, exists
from sqlalchemy.orm import Query, Session

from app.core.logging import get_logger
from app.models.models import CurationNew, Scope, ScopeMembership, UserNew

if TYPE_CHECKING:
    from app.models.models import PrecurationNew

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def _is_global_admin(user: UserNew) -> bool:
    """Check if user has global admin role.

    Extracted for DRY - single source of truth for admin check.
    """
    return user.role.value == "admin"


def admin_bypass_returns_true(func: Callable[P, bool]) -> Callable[P, bool]:
    """Decorator that allows global admins to bypass permission checks.

    For methods that return bool, admins always get True.
    This follows DRY by centralizing the admin bypass logic.

    Usage:
        @admin_bypass_returns_true
        def has_scope_access(db, user, scope_id, ...) -> bool:
            # Admin check already done by decorator
            # Only membership logic needed here
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> bool:
        # Extract user from args (position 1 after db)
        # Convention: (db: Session, user: UserNew, ...)
        user: UserNew | None = None
        if len(args) > 1:
            user = cast(UserNew, args[1])
        elif "user" in kwargs:
            user = cast(UserNew, kwargs.get("user"))

        if user and _is_global_admin(user):
            logger.debug(
                "Admin bypass granted",
                user_id=str(user.id),
                function=func.__name__,
            )
            return True
        return func(*args, **kwargs)

    return wrapper


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

    @staticmethod
    @admin_bypass_returns_true
    def has_scope_access(
        db: Session,
        user: UserNew,
        scope_id: UUID,
        required_roles: list[str] | None = None,
    ) -> bool:
        """Check if user has access to scope with optional role requirement.

        Uses EXISTS subquery for optimal performance (O(1) vs O(n) for COUNT).

        Args:
            db: Database session
            user: Current user
            scope_id: Scope to check access for
            required_roles: Optional list of required roles (e.g., ["curator", "admin"])
                           If None, any active membership grants access.

        Returns:
            True if user has access, False otherwise

        Performance Note:
            Uses EXISTS instead of COUNT for O(1) early termination.
            Reference: https://docs.sqlalchemy.org/en/20/orm/queryguide/query
        """
        logger.debug(
            "Checking scope access",
            user_id=str(user.id),
            scope_id=str(scope_id),
            required_roles=required_roles,
        )

        # Validate scope exists and is active
        scope_exists = db.query(
            exists().where(and_(Scope.id == scope_id, Scope.is_active == True))  # noqa: E712
        ).scalar()

        if not scope_exists:
            logger.warning("Scope not found or inactive", scope_id=str(scope_id))
            return False

        # Build EXISTS subquery for O(1) performance
        conditions = [
            ScopeMembership.user_id == user.id,
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.is_active == True,  # noqa: E712 - SQLAlchemy requires ==
        ]

        if required_roles:
            conditions.append(ScopeMembership.role.in_(required_roles))

        # Use EXISTS for early termination (stops at first match)
        exists_query = exists().where(and_(*conditions))
        result = bool(db.query(exists_query).scalar())

        logger.debug(
            "Access check complete",
            user_id=str(user.id),
            scope_id=str(scope_id),
            has_access=result,
        )
        return result

    @staticmethod
    def get_user_scope_ids(
        db: Session,
        user: UserNew,
        required_roles: list[str] | None = None,
    ) -> list[UUID]:
        """Get list of scope IDs user has access to.

        Args:
            db: Database session
            user: Current user
            required_roles: Optional list of required roles

        Returns:
            List of scope UUIDs user can access
        """
        logger.debug(
            "Getting user scope IDs",
            user_id=str(user.id),
            required_roles=required_roles,
        )

        # Global admin gets all active scopes
        if _is_global_admin(user):
            logger.debug("Admin gets all scopes", user_id=str(user.id))
            return [
                row[0]
                for row in db.query(Scope.id)
                .filter(Scope.is_active == True)  # noqa: E712
                .all()
            ]

        # Build membership query
        query = (
            db.query(ScopeMembership.scope_id)
            .join(Scope, ScopeMembership.scope_id == Scope.id)
            .filter(
                ScopeMembership.user_id == user.id,
                ScopeMembership.is_active == True,  # noqa: E712
                Scope.is_active == True,  # noqa: E712 - Only return active scopes
            )
        )

        # Add role filter if specified
        if required_roles:
            query = query.filter(ScopeMembership.role.in_(required_roles))

        scope_ids = [row[0] for row in query.all()]
        logger.debug(
            "Retrieved user scope IDs",
            user_id=str(user.id),
            count=len(scope_ids),
        )
        return scope_ids

    @staticmethod
    def get_user_scope_role(
        db: Session,
        user_id: UUID,
        scope_id: UUID,
    ) -> str | None:
        """Get user's role in a specific scope.

        Args:
            db: Database session
            user_id: User UUID
            scope_id: Scope UUID

        Returns:
            Role string or None if not a member
        """
        logger.debug(
            "Getting user scope role",
            user_id=str(user_id),
            scope_id=str(scope_id),
        )

        membership = (
            db.query(ScopeMembership)
            .filter(
                ScopeMembership.user_id == user_id,
                ScopeMembership.scope_id == scope_id,
                ScopeMembership.is_active == True,  # noqa: E712
            )
            .first()
        )

        role = membership.role if membership else None
        logger.debug(
            "User scope role retrieved",
            user_id=str(user_id),
            scope_id=str(scope_id),
            role=role,
        )
        return role

    @staticmethod
    def can_create_precuration(db: Session, user: UserNew, scope_id: UUID) -> bool:
        """Check if user can create precuration in scope.

        Requires curator or admin role in the scope.
        """
        return ScopePermissionService.has_scope_access(
            db, user, scope_id, required_roles=["admin", "curator", "scope_admin"]
        )

    @staticmethod
    def can_approve_precuration(
        db: Session, user: UserNew, precuration: "PrecurationNew"
    ) -> bool:
        """Check if user can approve precuration (4-eyes principle).

        Requirements:
        - User must NOT be the creator (4-eyes principle)
        - User must have reviewer, curator, or admin role in scope
        """
        # Cannot approve own work - 4-eyes principle
        if precuration.created_by == user.id:
            logger.debug(
                "Cannot approve own precuration (4-eyes)",
                user_id=str(user.id),
                precuration_id=str(precuration.id),
            )
            return False

        return ScopePermissionService.has_scope_access(
            db,
            user,
            precuration.scope_id,
            required_roles=["admin", "curator", "reviewer", "scope_admin"],
        )

    @staticmethod
    def can_edit_gene_assignment(db: Session, user: UserNew, scope_id: UUID) -> bool:
        """Check if user can edit gene assignments in scope.

        Requires curator or admin role in the scope.
        """
        return ScopePermissionService.has_scope_access(
            db, user, scope_id, required_roles=["admin", "curator", "scope_admin"]
        )
