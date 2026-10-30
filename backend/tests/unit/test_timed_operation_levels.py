"""timed_operation logs a refused request (4xx) as a warning, real failures as errors."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.logging.performance import api_endpoint

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("exc", "level"),
    [
        (HTTPException(404, "nope"), "warning"),
        (HTTPException(503), "error"),
        (RuntimeError("x"), "error"),
    ],
)
@pytest.mark.asyncio
async def test_failure_level_follows_the_status(exc: Exception, level: str) -> None:
    logger = MagicMock()

    @api_endpoint()
    def sync() -> None:
        raise exc

    @api_endpoint()
    async def coro() -> None:
        raise exc

    with patch("app.core.logging.performance._get_logger", return_value=logger):
        with pytest.raises(type(exc)):
            sync()
        with pytest.raises(type(exc)):
            await coro()
    assert getattr(logger, level).call_count == 2
    other = "error" if level == "warning" else "warning"
    assert getattr(logger, other).call_count == 0
