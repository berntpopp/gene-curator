"""OAuth consent for MCP clients (#462): the signed-in user approves or denies.

Session only: a personal or OAuth access token may not mint another grant.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, reject_personal_access_token
from app.mcp import oauth
from app.models import UserNew

router = APIRouter(dependencies=[Depends(reject_personal_access_token)])


class OAuthAuthorizationRequest(BaseModel):
    """A pending MCP client authorization, as the consent page shows it."""

    client_name: str
    redirect_uri: str
    scopes: list[str]


class OAuthConsent(BaseModel):
    approve: bool


class OAuthConsentRedirect(BaseModel):
    """Where the browser goes next: the client's redirect URI with code or error."""

    redirect_url: str


_GONE = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Authorization request not found or expired; start again in your client",
)


@router.get("/authorizations/{request_id}", response_model=OAuthAuthorizationRequest)
def get_oauth_authorization(
    request_id: UUID,
    db: Session = Depends(get_db),
    _user: UserNew = Depends(get_current_active_user),
) -> OAuthAuthorizationRequest:
    """OAuth consent: the client and access an MCP client asks for."""
    found = oauth.pending_request(db, request_id)
    if found is None:
        raise _GONE
    return OAuthAuthorizationRequest(**found)


@router.post("/authorizations/{request_id}", response_model=OAuthConsentRedirect)
def decide_oauth_authorization(
    request_id: UUID,
    body: OAuthConsent,
    db: Session = Depends(get_db),
    user: UserNew = Depends(get_current_active_user),
) -> OAuthConsentRedirect:
    """OAuth consent: approve or deny an MCP client's access to your account."""
    url = oauth.consent(db, request_id, user.id, body.approve)
    if url is None:
        raise _GONE
    return OAuthConsentRedirect(redirect_url=url)
