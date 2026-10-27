"""Async sessions carry the caller's RLS user (#386)."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.database import RLS_USER_KEY
from app.core.deps import get_async_db
from app.models import UserNew

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_async_session_is_bound_to_the_caller(
    test_user_curator: UserNew,
) -> None:
    sessions = get_async_db(test_user_curator)
    session = await anext(sessions)
    assert session.sync_session.info[RLS_USER_KEY] == str(test_user_curator.id)
    session.commit = AsyncMock()  # type: ignore[method-assign]
    with pytest.raises(StopAsyncIteration):
        await anext(sessions)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_session_rolls_back_on_error(test_user_curator: UserNew) -> None:
    sessions = get_async_db(test_user_curator)
    session = await anext(sessions)
    session.rollback = AsyncMock()  # type: ignore[method-assign]
    with pytest.raises(HTTPException):
        await sessions.athrow(HTTPException(status_code=403))
    session.rollback.assert_awaited_once()
