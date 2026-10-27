"""MCP authentication: personal access tokens only, resolved as their owner (#462).

No service token, no service principal, no anonymous mode: every tool call reaches
the API with the caller's own token (see server._as_caller).
"""

from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from typing import Any, cast
from uuid import UUID

from fastapi import FastAPI
from fastmcp.server.auth import AccessToken, TokenVerifier
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.database import apply_rls_user, get_db
from app.core.security import PAT_PREFIX, hash_personal_access_token
from app.crud import personal_access_token as pat_crud
from app.models import PersonalAccessToken, UserNew


@contextmanager
def _session(app: FastAPI) -> Iterator[Session]:
    """The app's get_db (honours dependency overrides, so tests hit their database)."""
    factory = cast(
        Callable[[], Generator[Session, None, None]],
        app.dependency_overrides.get(get_db, get_db),
    )
    gen = factory()
    try:
        yield next(gen)
    finally:
        gen.close()


def pat_user(app: FastAPI, token: str) -> tuple[str, str] | None:
    """(owner id, application role) of a live token for the rate limiter; no commit."""
    with _session(app) as db:
        found = pat_crud.authenticate(db, token)
        if found is None:
            return None
        role = db.scalar(select(UserNew.role).where(UserNew.id == UUID(found[0])))
        return found[0], str(getattr(role, "value", role))


def pat_owner(app: FastAPI, token: str) -> tuple[str, list[str], str, str] | None:
    """(user id, scopes, token name, application role) of a live token, else None."""
    if not token.startswith(PAT_PREFIX):
        return None
    with _session(app) as db:
        found = pat_crud.authenticate(db, token)
        if found is None:
            return None
        user_id, scopes = found
        apply_rls_user(db.connection(), user_id)  # the owner may read their own row
        name = db.scalar(
            select(PersonalAccessToken.name).where(
                PersonalAccessToken.token_hash == hash_personal_access_token(token)
            )
        )
        role = db.scalar(select(UserNew.role).where(UserNew.id == UUID(user_id)))
        return user_id, scopes, name or "", str(getattr(role, "value", role))


class PersonalAccessTokenVerifier(TokenVerifier):
    """Accepts a live gc_pat_ token; scopes come from the token and only narrow."""

    def __init__(self, app: FastAPI) -> None:
        super().__init__()
        self._app = app

    async def verify_token(self, token: str) -> AccessToken | None:
        found: Any = await run_in_threadpool(pat_owner, self._app, token)
        if found is None:
            return None
        user_id, scopes, name, role = found
        # role only shapes tools/list (server.CallerToolFilter); the API re-checks it
        return AccessToken(
            token=token,
            client_id=name,
            scopes=scopes,
            claims={"sub": user_id, "role": role},
        )
