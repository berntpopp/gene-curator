"""
FastAPI dependencies for authentication and database access.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    credentials_exception,
    inactive_user_exception,
    verify_token,
)
from app.crud.user import user_crud
from app.models import User, UserRole

# Security scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
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
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = user_crud.get(db, id=user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
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
    current_user: User = Depends(get_current_active_user),
) -> User:
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


def get_current_curator_or_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user if they are curator or admin.

    Args:
        current_user: Current active user

    Returns:
        Curator or admin user object

    Raises:
        HTTPException: If user is not curator or admin
    """
    if current_user.role not in [UserRole.CURATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Curator or admin privileges required",
        )
    return current_user


# Optional authentication (for public endpoints that can benefit from user context)
def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
) -> User | None:
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
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        # Get user from database
        user = user_crud.get(db, id=user_id)
        if user is None or not user_crud.is_active(user):
            return None

        return user
    except Exception:
        return None
