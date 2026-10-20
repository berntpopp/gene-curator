"""Scope statistics use PostgreSQL-only SQL (EXTRACT), so they are tested here, not on SQLite."""

import pytest
from sqlalchemy.orm import Session

from app.crud.scope import scope_crud
from app.models.models import Scope, UserNew
from tests.api.scopes.factories import make_member, make_user
from tests.postgres.test_scope_crud import (  # noqa: F401 (fixtures)
    admin_user,
    test_scope,
)

pytestmark = pytest.mark.postgres


def test_detailed_statistics_counts_only_accepted_members(
    db: Session,
    admin_user: UserNew,  # noqa: F811
    test_scope: Scope,  # noqa: F811
) -> None:
    make_member(db, test_scope, make_user(db), "viewer")
    make_member(
        db, test_scope, make_user(db), "curator", accepted=False
    )  # pending invite

    stats = scope_crud.get_detailed_statistics(db, scope_id=test_scope.id)

    assert stats["member_count"] == 1


def test_performance_metrics_empty_scope(
    db: Session,
    admin_user: UserNew,  # noqa: F811
    test_scope: Scope,  # noqa: F811
) -> None:
    metrics = scope_crud.get_performance_metrics(db, scope_id=test_scope.id)

    assert metrics["approval_rate"] is None
