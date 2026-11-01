"""
User management API endpoints for admin users.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    get_current_active_user,
    get_current_admin_user,
    reject_personal_access_token,
)
from app.core.logging import get_logger
from app.core.search_text import MAX_SEARCH, NO_NUL
from app.crud import personal_access_token as pat_crud
from app.crud.user import user_crud
from app.models import User
from app.schemas.auth import UserCreate, UserResponse, UserUpdate
from app.schemas.personal_access_token import (
    PersonalAccessTokenCreate,
    PersonalAccessTokenCreated,
    PersonalAccessTokenResponse,
)

logger = get_logger(__name__)
router = APIRouter()


class PasswordUpdate(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


@router.get("/", response_model=list[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of users to return"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Sequence[User]:
    """
    Get all users (admin only).
    """
    users = user_crud.get_multi(db=db, skip=skip, limit=limit)
    return users


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    q: str = Query(
        ...,
        min_length=1,
        max_length=MAX_SEARCH,
        pattern=NO_NUL,
        description="Search query",
    ),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of users to return"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Sequence[User]:
    """
    Search users by name or email (admin only).
    """
    users = user_crud.search(db=db, query=q, skip=skip, limit=limit)
    return users


@router.get("/statistics")
async def get_user_statistics(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)
) -> dict[str, Any]:
    """
    Get user statistics (admin only).
    """
    stats = user_crud.get_statistics(db=db)
    return stats


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get a specific user by ID.

    - Admins can view any user's profile
    - Regular users can only view their own profile
    """
    # Check if user is trying to view their own profile OR is an admin
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile. Admin access required to view other users.",
        )

    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(reject_personal_access_token)],
)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> User:
    """
    Create a new user (admin only).
    """
    # Check if user already exists
    existing_user = user_crud.get_by_email(db=db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user = user_crud.create(db=db, obj_in=user_data)
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(reject_personal_access_token)],
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> User:
    """
    Update a user (admin only).
    """
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # An admin editing themselves must not drop admin rights or deactivate
    # (the caller is an active admin, so this is what could leave zero admins).
    if str(user.id) == str(current_user.id) and (
        user_data.is_active is False
        or (user_data.role is not None and user_data.role != "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role or deactivate your own account",
        )

    if user.is_agent and user_data.role == "admin":  # #639
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An agent account cannot be a platform admin",
        )

    # Check if email is being changed and already exists
    if user_data.email and user_data.email != user.email:
        existing_user = user_crud.get_by_email(db=db, email=user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

    updated_user = user_crud.update_user(db=db, user_id=user_id, user_update=user_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return updated_user


@router.put("/{user_id}/password", dependencies=[Depends(reject_personal_access_token)])
async def update_user_password(
    user_id: UUID,
    body: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> dict[str, str]:
    """
    Update a user's password (admin only).
    """
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user_crud.update_password(db=db, user_id=user_id, new_password=body.new_password)
    return {"message": "Password updated successfully"}


@router.put("/{user_id}/activate", dependencies=[Depends(reject_personal_access_token)])
async def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> dict[str, str]:
    """
    Activate a user account (admin only).
    """
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user_crud.update_user(
        db=db, user_id=user_id, user_update=UserUpdate(is_active=True)
    )
    return {"message": "User activated successfully"}


@router.put(
    "/{user_id}/deactivate", dependencies=[Depends(reject_personal_access_token)]
)
async def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> dict[str, str]:
    """
    Deactivate a user account (admin only).
    """
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent admin from deactivating themselves
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    user_crud.update_user(
        db=db, user_id=user_id, user_update=UserUpdate(is_active=False)
    )
    return {"message": "User deactivated successfully"}


@router.delete("/{user_id}", dependencies=[Depends(reject_personal_access_token)])
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> dict[str, str]:
    """
    Delete a user (admin only).
    """
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent admin from deleting themselves
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    user_crud.remove(db=db, id=user_id)
    return {"message": "User deleted successfully"}


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get user activity summary.

    - Admins can view any user's activity
    - Regular users can only view their own activity
    """
    # Check if user is trying to view their own activity OR is an admin
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own activity. Admin access required to view other users' activity.",
        )

    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    activity = user_crud.get_user_activity(db=db, user_id=user_id)
    return activity


@router.post(
    "/{user_id}/tokens",
    response_model=PersonalAccessTokenCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(reject_personal_access_token)],
)
def create_agent_token(
    user_id: UUID,
    token_in: PersonalAccessTokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """A token for an agent account, which has no password sign-in to create its own
    (#639). Platform admins, signed in; the plaintext is shown only here."""
    agent = user_crud.get(db=db, id=user_id)
    if agent is None or not agent.is_agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No agent account with this id")
    pat, plaintext = pat_crud.create(db, user_id=agent.id, obj_in=token_in)
    logger.info(
        "Agent token created",
        token_id=str(pat.id),
        agent_id=str(agent.id),
        admin_id=str(current_user.id),
    )
    created = PersonalAccessTokenResponse.model_validate(pat).model_dump()
    return PersonalAccessTokenCreated(**created, token=plaintext)
