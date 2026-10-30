"""get_db logs real database errors, not HTTPExceptions raised by endpoints (m13)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError

from app.core import database

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("error", "logged"),
    [
        (HTTPException(status_code=403), False),
        # a body missing lock_version is a client error (422), not a database error
        (RequestValidationError([{"loc": ("body", "lock_version")}]), False),
        (OperationalError("SELECT 1", {}, Exception("down")), True),
    ],
)
def test_get_db_logs_only_database_errors(error: Exception, logged: bool) -> None:
    session = MagicMock()
    logger = MagicMock()
    with (
        patch.object(database, "Session") as session_cls,
        patch("app.core.logging.get_logger", return_value=logger),
    ):
        session_cls.return_value.__enter__.return_value = session
        gen = database.get_db()
        assert next(gen) is session
        with pytest.raises(type(error)) as raised:
            gen.throw(error)
    assert raised.value is error
    session.rollback.assert_called_once()
    assert logger.error.called is logged
