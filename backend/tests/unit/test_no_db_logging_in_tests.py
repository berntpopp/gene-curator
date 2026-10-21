"""Tests must not open async DB connections via the DB logger (#333)."""

import pytest
from fastapi.testclient import TestClient

from app.core.logging.database_logger import get_database_logger

pytestmark = pytest.mark.unit


def test_database_logger_is_disabled_during_requests(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert get_database_logger().enabled is False
