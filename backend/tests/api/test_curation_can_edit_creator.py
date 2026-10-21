"""can_edit follows the save rule: only the creator (or a platform admin) may save a draft."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CurationStatus, WorkflowStage
from tests.api.scopes.factories import (
    auth_headers,
    make_curation,
    make_gene,
    make_member,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def no_rls_on_sqlite() -> Iterator[None]:
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield


@pytest.mark.parametrize(
    ("who", "can_edit"),
    [("creator", True), ("other_curator", False), ("platform_admin", True)],
)
def test_can_edit_matches_who_may_save(
    client: TestClient, db_session: Session, who: str, can_edit: bool
) -> None:
    scope = make_scope(db_session)
    alice, carol = make_user(db_session), make_user(db_session)
    for user in (alice, carol):
        make_member(db_session, scope, user, "curator")
    users = {
        "creator": alice,
        "other_curator": carol,
        "platform_admin": make_user(db_session, role="admin"),
    }
    curation = make_curation(
        db_session,
        scope=scope,
        gene=make_gene(db_session),
        creator=alice,
        stage=WorkflowStage.CURATION,
        status=CurationStatus.DRAFT,
    )
    response = client.get(
        f"/api/v1/curations/{curation.id}", headers=auth_headers(users[who])
    )
    assert response.status_code == 200, response.text
    assert response.json()["can_edit"] is can_edit
