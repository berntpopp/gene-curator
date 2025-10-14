"""
Authentication endpoints.
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_user, get_current_user
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    credentials_exception,
    verify_token,
)
from app.crud.user import user_crud
from app.models import User
from app.schemas.auth import (
    PasswordChange,
    Token,
    TokenRefresh,
    UserCreate,
    UserLogin,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    logger.info(
        "Login attempt",
        email=user_credentials.email,
        email_length=len(user_credentials.email),
    )

    user = user_crud.authenticate(
        db, email=user_credentials.email, password=user_credentials.password
    )

    if not user:
        logger.warning(
            "Authentication failed - invalid credentials",
            email=user_credentials.email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    elif not user_crud.is_active(user):
        logger.warning(
            "Authentication failed - inactive user",
            email=user_credentials.email,
            user_id=str(user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    # Update last login
    user_crud.update_last_login(db, str(user.id))

    logger.info(
        "Login successful",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        name=user.name,
    )

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Refresh an access token using a refresh token.
    """
    payload = verify_token(token_data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = user_crud.get(db, id=user_id)
    if user is None or not user_crud.is_active(user):
        raise credentials_exception

    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get current user.
    """
    return current_user


@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    Change current user's password.
    """
    # Verify current password
    if not user_crud.authenticate(
        db, email=current_user.email, password=password_data.current_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    # Update password
    user_crud.update_password(
        db=db, user_id=str(current_user.id), new_password=password_data.new_password
    )

    return {"message": "Password updated successfully"}


@router.post("/change-password")
async def change_password_alt(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """
    Change current user's password (alternative endpoint).
    """
    # Verify current password
    if not user_crud.authenticate(
        db, email=current_user.email, password=password_data.current_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    # Update password
    user_crud.update_password(
        db=db, user_id=str(current_user.id), new_password=password_data.new_password
    )

    return {"message": "Password updated successfully"}


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    Register a new user (public endpoint for now - can be restricted later).
    """
    # Check if user already exists
    existing_user = user_crud.get_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    user = user_crud.create(db, obj_in=user_data)
    return user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """
    Logout user (client should discard tokens).
    """
    # Note: In a production system, you might want to:
    # 1. Blacklist the token
    # 2. Store token revocation in database/cache
    # 3. Implement token invalidation strategy

    return {"message": "Successfully logged out"}


@router.get("/")
async def auth_info() -> dict[str, Any]:
    """Authentication system information."""
    return {
        "message": "Gene Curator Authentication API",
        "status": "active",
        "endpoints": {
            "login": "/api/v1/auth/login",
            "refresh": "/api/v1/auth/refresh",
            "me": "/api/v1/auth/me",
            "register": "/api/v1/auth/register",
            "logout": "/api/v1/auth/logout",
        },
        "token_type": "Bearer JWT",
        "expires_in_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }
