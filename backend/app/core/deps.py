"""
FastAPI dependencies for authentication and database access.
"""

from collections.abc import Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.core.security import (
    credentials_exception,
    inactive_user_exception,
    verify_token,
)
from app.crud.user import user_crud
from app.models import UserNew

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserNew:
    """
    Get current authenticated user from JWT token.

    Args:
        db: Database session
        credentials: HTTP Bearer token credentials

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Verify token
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    # Extract user ID from token
    user_id_value: Any = payload.get("sub")
    if user_id_value is None or not isinstance(user_id_value, str):
        raise credentials_exception
    user_id: str = user_id_value

    # Get user from database
    user = user_crud.get(db, id=user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: UserNew = Depends(get_current_user),
) -> UserNew:
    """
    Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not user_crud.is_active(current_user):
        raise inactive_user_exception
    return current_user


def get_current_admin_user(
    current_user: UserNew = Depends(get_current_active_user),
) -> UserNew:
    """
    Get current admin user.

    Args:
        current_user: Current active user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not admin
    """
    if not user_crud.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


# Optional authentication (for public endpoints that can benefit from user context)
def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
) -> UserNew | None:
    """
    Get current user optionally (doesn't raise exception if no token).

    Args:
        db: Database session
        credentials: Optional HTTP Bearer token credentials

    Returns:
        Current user object or None if not authenticated
    """
    if credentials is None:
        return None

    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        if payload is None:
            return None

        # Extract user ID from token
        user_id_value: Any = payload.get("sub")
        if user_id_value is None or not isinstance(user_id_value, str):
            return None
        user_id: str = user_id_value

        # Get user from database
        user = user_crud.get(db, id=user_id)
        if user is None or not user_crud.is_active(user):
            return None

        return user
    except Exception:
        return None


# =============================================================================
# RLS Context Manager (SECURITY: Parameterized queries only)
# =============================================================================


def set_rls_context(db: Session, current_user: UserNew) -> None:
    """
    Set PostgreSQL RLS context for current user.

    SECURITY: Uses validated UUID from User model. SET LOCAL doesn't support
    bind parameters, but since user_id is a UUID from a validated User object,
    it's safe from SQL injection (UUID format is strictly validated).

    IMPORTANT: This function also expires all objects in the session to force
    SQLAlchemy to re-query the database where RLS will be enforced. Without
    this, cached objects from the identity map may bypass RLS.

    Args:
        db: Database session
        current_user: Current authenticated user

    Example:
        set_rls_context(db, current_user)
        # Now all queries respect RLS policies for this user
    """
    try:
        # ✅ SECURE: user_id is a validated UUID from User model
        # SET doesn't support bind parameters, but UUID is safe
        user_id_str = str(current_user.id)

        # Execute SET command (session-level, not LOCAL)
        # Using session-level SET ensures compatibility with savepoint-based testing
        # In production, each request gets a new session, so this is effectively request-scoped
        db.execute(text(f"SET app.current_user_id = '{user_id_str}'"))

        # Verify that the context was actually set (without flushing)
        result = db.execute(text("SHOW app.current_user_id"))
        actual_context = result.scalar()

        if actual_context != user_id_str:
            raise ValueError(
                f"RLS context verification failed: expected {user_id_str}, got {actual_context}"
            )

        # NOTE: We do NOT call db.expire_all() here because:
        # 1. RLS context is set BEFORE any queries are executed
        # 2. All subsequent queries in this transaction will respect RLS
        # 3. expire_all() would detach objects, causing FastAPI serialization to fail
        # 4. The session lifecycle (via yield in get_db) handles cleanup properly

        logger.debug(
            "RLS context set and verified",
            user_id=user_id_str,
            verified_context=actual_context,
            user_name=current_user.name,
            user_email=current_user.email,
        )
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e!s}"
        logger.error(
            "Failed to set RLS context",
            error=e,
            error_type=type(e).__name__,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set security context: {error_msg}",
        ) from e


# =============================================================================
# Scope Permission Dependencies (SECURITY: TOCTOU prevention with FOR SHARE)
# =============================================================================


def get_scope(
    scope_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """
    Get scope by ID with permission check.

    SECURITY: Uses SELECT FOR SHARE to prevent TOCTOU race conditions.

    Args:
        scope_id: UUID of scope to retrieve
        db: Database session
        current_user: Current authenticated user

    Returns:
        Scope object if user has access

    Raises:
        HTTPException: 404 if scope not found or user lacks access
    """
    from app.models import Scope  # Import here to avoid circular dependency

    # Set RLS context for current user
    set_rls_context(db, current_user)

    # Query with SELECT FOR SHARE (prevents TOCTOU)
    scope = (
        db.execute(
            select(Scope)
            .where(Scope.id == scope_id)
            .with_for_update(read=True)  # SELECT FOR SHARE
        )
        .scalars()
        .first()
    )

    if not scope:
        logger.warning(
            "Scope not found or access denied",
            scope_id=str(scope_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scope not found or access denied",
        )

    logger.debug(
        "Scope access granted",
        scope_id=str(scope_id),
        scope_name=scope.name,
        user_id=str(current_user.id),
    )

    return scope


def require_scope_role(required_role: ScopeRole) -> Callable[..., Any]:
    """
    Factory function to create scope role requirement dependencies.

    Creates a dependency that verifies user has required role in scope.
    Uses SELECT FOR SHARE to prevent TOCTOU race conditions.

    Args:
        required_role: Minimum required ScopeRole

    Returns:
        Dependency function that checks scope membership and role

    Example:
        @router.post("/scopes/{scope_id}/curations")
        def create_curation(
            scope: Scope = Depends(require_scope_role(ScopeRole.CURATOR))
        ):
            # User is guaranteed to be at least curator in this scope
            pass
    """

    def _check_scope_role(
        scope_id: UUID,
        db: Session = Depends(get_db),
        current_user: UserNew = Depends(get_current_active_user),
    ) -> Any:
        """Check if user has required role in scope."""
        from app.models import (
            ScopeMembership,
        )  # Import here to avoid circular dependency

        # Application admins bypass scope role checks
        if user_crud.is_admin(current_user):
            logger.debug(
                "Application admin bypassing scope role check",
                user_id=str(current_user.id),
                scope_id=str(scope_id),
                required_role=required_role.value,
            )
            return get_scope(scope_id, db, current_user)

        # Set RLS context
        set_rls_context(db, current_user)

        # Query membership with SELECT FOR SHARE (TOCTOU prevention)
        membership = (
            db.execute(
                select(ScopeMembership)
                .where(
                    ScopeMembership.scope_id == scope_id,
                    ScopeMembership.user_id == current_user.id,
                    ScopeMembership.is_active == True,  # noqa: E712
                    ScopeMembership.accepted_at.isnot(None),
                )
                .with_for_update(read=True)  # SELECT FOR SHARE
            )
            .scalars()
            .first()
        )

        if not membership:
            logger.warning(
                "User not a member of scope",
                user_id=str(current_user.id),
                scope_id=str(scope_id),
                required_role=required_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this scope",
            )

        # Check role permissions using ScopeRole enum methods
        user_role = ScopeRole.from_string(membership.role)

        # Role-specific permission checks
        has_permission = False
        if required_role == ScopeRole.VIEWER:
            has_permission = user_role.can_view()
        elif required_role == ScopeRole.REVIEWER:
            has_permission = user_role.can_review()
        elif required_role == ScopeRole.CURATOR:
            has_permission = user_role.can_curate()
        elif required_role == ScopeRole.ADMIN:
            has_permission = user_role.can_manage_scope()

        if not has_permission:
            logger.warning(
                "Insufficient scope permissions",
                user_id=str(current_user.id),
                scope_id=str(scope_id),
                user_role=user_role.value,
                required_role=required_role.value,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )

        logger.debug(
            "Scope role check passed",
            user_id=str(current_user.id),
            scope_id=str(scope_id),
            user_role=user_role.value,
            required_role=required_role.value,
        )

        return get_scope(scope_id, db, current_user)

    return _check_scope_role


# =============================================================================
# Convenience Typed Dependencies
# =============================================================================

# Type-annotated dependencies for clean endpoint signatures
RequireScopeMember = Annotated[UserNew, Depends(require_scope_role(ScopeRole.VIEWER))]
RequireScopeReviewer = Annotated[
    UserNew, Depends(require_scope_role(ScopeRole.REVIEWER))
]
RequireScopeCurator = Annotated[UserNew, Depends(require_scope_role(ScopeRole.CURATOR))]
RequireScopeAdmin = Annotated[UserNew, Depends(require_scope_role(ScopeRole.ADMIN))]
