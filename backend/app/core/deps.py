"""
FastAPI dependencies for authentication and database access.
"""

from collections.abc import AsyncGenerator, Callable
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.capabilities import require
from app.core.database import RLS_USER_KEY, AsyncSessionLocal, apply_rls_user, get_db
from app.core.logging import get_logger
from app.core.security import (
    PAT_PREFIX,
    credentials_exception,
    inactive_user_exception,
    verify_token,
)
from app.crud import personal_access_token as pat_crud
from app.crud.user import user_crud
from app.models import Scope, UserNew

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
    ("POST", "/api/v1/users/{user_id}/tokens"),  # an agent account's token (#639)
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


def is_session_request(request: Request) -> bool:
    """False for a personal access token, an MCP OAuth token (a PAT row) or an MCP call."""
    from app.mcp.audit import is_internal  # app.mcp imports this module

    return not (
        getattr(request.state, "personal_access_token", False)
        or is_internal(request.scope)
    )


def require_signed_in_approver(
    request: Request, scope: Scope | None, what: str = "Approvals"
) -> None:
    """403 when scope.approvals_require_session and the caller is no signed-in person (#560)."""
    if (
        scope is not None
        and scope.approvals_require_session
        and not is_session_request(request)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{what} in this scope need a signed-in person, not a token or "
            "MCP call; comments, requested changes and rejections still work",
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
            # The async engine refused the connection (an outage of the async pool, or the
            # SQLite test lane's unreachable engine): 503, not 500
            if isinstance(e, ConnectionError):
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable"
                ) from e
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


def require_capability(capability: str, active_only: bool = True) -> Callable[..., Any]:
    """Dependency: the caller holds `capability` in the path's scope (core.capabilities.require).

    Returns the scope. Platform admins pass; non-members and lacking roles get 403, an
    unknown scope 404. active_only=False for managing the scope itself (settings,
    members), which must also work while it is inactive.

    Example:
        @router.patch("/scopes/{scope_id}")
        def update_scope(scope: Scope = Depends(require_capability(MANAGE_SCOPE))): ...
    """

    def _check_capability(
        scope_id: UUID,
        db: Session = Depends(get_db),
        current_user: UserNew = Depends(get_current_active_user),
    ) -> Any:
        require(db, current_user, scope_id, capability, active_only)
        return get_scope(scope_id, db, current_user)

    return _check_capability
