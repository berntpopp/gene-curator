"""
FastAPI dependencies for authentication and database access.
"""

from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.database import RLS_USER_KEY, AsyncSessionLocal, apply_rls_user, get_db
from app.core.enums import ScopeRole
from app.core.logging import get_logger
from app.core.security import (
    PAT_PREFIX,
    credentials_exception,
    inactive_user_exception,
    verify_token,
)
from app.crud import personal_access_token as pat_crud
from app.crud.user import user_crud
from app.models import UserNew

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def _request(request: Request) -> Request:
    return request


_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Account and identity control a personal access token may never perform, so a leaked
# token cannot take over accounts; every other call keeps the owner's full rights.
PAT_BLOCKED_OPERATIONS: tuple[tuple[str, str], ...] = (
    ("POST", "/api/v1/users/"),
    ("PUT", "/api/v1/users/{user_id}"),
    ("PUT", "/api/v1/users/{user_id}/password"),
    ("PUT", "/api/v1/users/{user_id}/activate"),
    ("PUT", "/api/v1/users/{user_id}/deactivate"),
    ("DELETE", "/api/v1/users/{user_id}"),
    ("PUT", "/api/v1/auth/me/password"),
    ("POST", "/api/v1/auth/change-password"),
    ("POST", "/api/v1/me/tokens/"),
)


def _token_user_id(db: Session, token: str, request: Request) -> str | None:
    """User id behind a JWT access token or a live personal access token, else None.

    A personal access token marks the request (request.state.personal_access_token).
    """
    if token.startswith(PAT_PREFIX):
        found = pat_crud.authenticate(db, token)
        if found is None:
            return None
        user_id, scopes = found
        if "write" not in scopes and request.method not in _SAFE_METHODS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This token is read-only"
            )
        request.state.personal_access_token = True
        return user_id
    payload = verify_token(token)
    if payload is None or payload.get("type") == "refresh":
        return None
    user_id_value: Any = payload.get("sub")
    return user_id_value if isinstance(user_id_value, str) else None


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = Depends(_request),
) -> UserNew:
    """
    Get current authenticated user from a JWT or personal access token (gc_pat_...).

    Args:
        db: Database session
        credentials: HTTP Bearer token credentials

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid, expired, revoked or user not found
    """
    user_id = _token_user_id(db, credentials.credentials, request)
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = user_crud.get(db, id=user_id)
    if user is None:
        raise credentials_exception

    set_rls_context(db, user)
    return user


def reject_personal_access_token(
    request: Request, _user: UserNew = Depends(get_current_user)
) -> None:
    """Guard for PAT_BLOCKED_OPERATIONS: only a signed-in session may call these."""
    if getattr(request.state, "personal_access_token", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed with a personal access token; sign in instead",
        )


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


async def get_async_db(
    current_user: UserNew = Depends(get_current_active_user),
) -> AsyncGenerator[AsyncSession, None]:
    """Async session bound to the caller's RLS user, like get_db + get_current_user.

    The user id is applied at every transaction begin by core.database's after_begin
    listener (the AsyncSession wraps a sync Session). Commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        session.sync_session.info[RLS_USER_KEY] = str(current_user.id)
        try:
            yield session
            await session.commit()
        except Exception as e:
            if not isinstance(e, HTTPException):
                logger.error("Async database error", error=e)
            await session.rollback()
            raise


# Optional authentication (for public endpoints that can benefit from user context)
def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    request: Request = Depends(_request),
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
        user_id = _token_user_id(db, credentials.credentials, request)
        if user_id is None:
            return None

        # Get user from database
        user = user_crud.get(db, id=user_id)
        if user is None or not user_crud.is_active(user):
            return None
    except Exception:
        return None

    set_rls_context(db, user)
    return user


# =============================================================================
# RLS Context Manager (SECURITY: Parameterized queries only)
# =============================================================================


def set_rls_context(db: Session, current_user: UserNew) -> None:
    """Bind the PostgreSQL RLS user (app.current_user_id) to this session.

    get_current_user calls this for every authenticated request, so no endpoint can
    forget it; explicit calls in endpoints are harmless repeats. The value is
    transaction-local and re-applied after each commit (see core.database), so it
    never leaks to the next request on a pooled connection. No-op on SQLite.
    """
    user_id = str(current_user.id)
    db.info[RLS_USER_KEY] = user_id
    apply_rls_user(db.connection(), user_id)


# =============================================================================
# Scope Permission Dependencies
# =============================================================================


def get_scope(
    scope_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """
    Get scope by ID with permission check.

    No row lock: under RLS, FOR SHARE must also pass the scopes UPDATE policy (scope
    admins only) and would hide the scope from other members. require_scope_role
    locks the membership row instead.

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

    scope = db.execute(select(Scope).where(Scope.id == scope_id)).scalars().first()

    # Enforce visibility in Python too: RLS is not active on every connection
    from app.services.scope_permissions import ScopePermissionService

    if not scope or not ScopePermissionService.can_view_scope(db, current_user, scope):
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
