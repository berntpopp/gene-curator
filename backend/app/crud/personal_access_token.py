"""Personal access token data access (#462)."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.security import generate_personal_access_token, hash_personal_access_token
from app.models import PersonalAccessToken
from app.schemas.personal_access_token import PersonalAccessTokenCreate

LAST_USED_RESOLUTION = timedelta(seconds=60)  # same as 056


def authenticate(db: Session, token: str) -> tuple[str, list[str]] | None:
    """Owner id and scopes of a live token; stamps last_used_at at most once a minute."""
    token_hash = hash_personal_access_token(token)
    if db.get_bind().dialect.name == "postgresql":
        # No RLS user yet: the SECURITY DEFINER function (056) does the same lookup.
        row = db.execute(
            text("SELECT user_id, scopes FROM authenticate_personal_access_token(:h)"),
            {"h": token_hash},
        ).first()
        return (str(row.user_id), list(row.scopes)) if row else None
    now = datetime.now(UTC)
    pat = db.scalar(
        select(PersonalAccessToken).where(
            PersonalAccessToken.token_hash == token_hash,
            PersonalAccessToken.revoked_at.is_(None),
            PersonalAccessToken.expires_at > now,
        )
    )
    if pat is None:
        return None
    last = pat.last_used_at
    # SQLite returns naive datetimes; values are stored in UTC
    if last is None or last.replace(tzinfo=UTC) < now - LAST_USED_RESOLUTION:
        pat.last_used_at = now
    return str(pat.user_id), list(pat.scopes)


def create(
    db: Session, *, user_id: UUID, obj_in: PersonalAccessTokenCreate
) -> tuple[PersonalAccessToken, str]:
    """Store a new token for user_id; returns the row and the one-time plaintext."""
    plaintext = generate_personal_access_token()
    pat = PersonalAccessToken(
        user_id=user_id,
        name=obj_in.name,
        token_hash=hash_personal_access_token(plaintext),
        token_prefix=plaintext[:12],
        scopes=sorted(set(obj_in.scopes)),
        expires_at=obj_in.expires_at,
    )
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat, plaintext


def list_for_user(db: Session, *, user_id: UUID) -> Sequence[PersonalAccessToken]:
    return db.scalars(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.user_id == user_id)
        .order_by(PersonalAccessToken.created_at.desc())
    ).all()


def revoke(db: Session, *, user_id: UUID, token_id: UUID) -> bool:
    """Revoke the user's own token; False if it is not theirs or does not exist."""
    pat = db.scalar(
        select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.user_id == user_id,
        )
    )
    if pat is None:
        return False
    if pat.revoked_at is None:
        pat.revoked_at = datetime.now(UTC)
        db.commit()
    return True
