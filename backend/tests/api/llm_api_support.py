"""Shared fixtures for the LLM API tests."""

import json
import socket
from collections.abc import Iterator
from typing import Any

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import event, func, select

from app.core.config import settings
from app.models import AuditLogNew


@pytest.fixture
def llm_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Key ring, public DNS, and audit_log ids on SQLite (no BigInteger autoincrement)."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "LLM_CREDENTIAL_KEYS", json.dumps({"k1": key}))
    monkeypatch.setattr(settings, "LLM_CREDENTIAL_ACTIVE_KID", "k1")
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))
        ],
    )

    def assign_id(mapper: Any, connection: Any, target: AuditLogNew) -> None:
        if target.id is None:
            target.id = (
                connection.scalar(select(func.coalesce(func.max(AuditLogNew.id), 0)))
                + 1
            )

    event.listen(AuditLogNew, "before_insert", assign_id)
    yield
    event.remove(AuditLogNew, "before_insert", assign_id)
