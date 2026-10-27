"""Personal access tokens: create, list and revoke your own (#462)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, reject_personal_access_token
from app.core.logging import get_logger
from app.crud import personal_access_token as pat_crud
from app.models import UserNew
from app.schemas.personal_access_token import (
    PersonalAccessTokenCreate,
    PersonalAccessTokenCreated,
    PersonalAccessTokenResponse,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=list[PersonalAccessTokenResponse])
def list_tokens(
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """List your own tokens (never their plaintext)."""
    return pat_crud.list_for_user(db, user_id=current_user.id)


@router.post(
    "/",
    response_model=PersonalAccessTokenCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(reject_personal_access_token)],
)
def create_token(
    token_in: PersonalAccessTokenCreate,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Any:
    """Create a token; the response is the only time its plaintext is shown."""
    pat, plaintext = pat_crud.create(db, user_id=current_user.id, obj_in=token_in)
    logger.info("Personal access token created", token_id=str(pat.id))
    created = PersonalAccessTokenResponse.model_validate(pat).model_dump()
    return PersonalAccessTokenCreated(**created, token=plaintext)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Response:
    """Revoke one of your own tokens; it stops working immediately."""
    if not pat_crud.revoke(db, user_id=current_user.id, token_id=token_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )
    logger.info("Personal access token revoked", token_id=str(token_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
