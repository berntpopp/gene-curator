"""Loggers created at import time, before configure_logging(), must still reach system_logs."""

from unittest.mock import MagicMock

import pytest

from app.core.logging import database_logger as dbl


def test_initialize_configures_logger_obtained_before_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dbl, "_db_logger", None)
    early = dbl.get_database_logger()  # what get_logger() captures at import time
    factory = MagicMock()

    dbl.initialize_database_logger(factory)

    assert early.session_factory is factory
    assert dbl.get_database_logger() is early
