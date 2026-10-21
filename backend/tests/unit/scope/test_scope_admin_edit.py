"""Scope admins follow the same stage guard as creators when editing curations."""

import pytest
from sqlalchemy.orm import Session

from app.models.models import CurationStatus, WorkflowStage
from app.services.scope_permissions import ScopePermissionService
from tests.api.scopes.factories import (
    make_curation,
    make_gene,
    make_member,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("stage", "status", "allowed"),
    [
        (WorkflowStage.REVIEW, CurationStatus.IN_REVIEW, False),
        (WorkflowStage.ACTIVE, CurationStatus.ACTIVE, False),
        (WorkflowStage.CURATION, CurationStatus.DRAFT, True),
    ],
)
def test_scope_admin_edit_respects_stage(
    db_session: Session, stage: WorkflowStage, status: CurationStatus, allowed: bool
) -> None:
    scope = make_scope(db_session)
    creator = make_user(db_session)
    admin = make_user(db_session)
    make_member(db_session, scope, admin, "admin")
    curation = make_curation(
        db_session,
        scope=scope,
        gene=make_gene(db_session),
        creator=creator,
        stage=stage,
        status=status,
    )
    assert (
        ScopePermissionService.can_edit_curation(db_session, admin, curation) is allowed
    )
