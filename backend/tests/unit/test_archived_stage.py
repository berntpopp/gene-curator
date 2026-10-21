"""Archived curations/precurations get the terminal 'archived' stage (#323)."""

import pytest
from sqlalchemy.orm import Session

from app.crud.curation import curation_crud
from app.crud.precuration import precuration_crud
from app.crud.workflow_engine import workflow_engine
from app.models.models import CurationNew, CurationStatus, WorkflowStage
from app.services.scope_permissions import ScopePermissionService
from tests.unit.test_activation_supersedes import _curation

pytestmark = pytest.mark.unit


def test_soft_delete_sets_archived_stage(
    db_session: Session, test_scope, test_gene, test_workflow_pair, test_user_curator
):
    c = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    c.status = CurationStatus.DRAFT
    curation_crud.soft_delete(db_session, db_obj=c, user_id=test_user_curator.id)
    assert c.status == CurationStatus.ARCHIVED
    assert c.workflow_stage == WorkflowStage.ARCHIVED


def test_precuration_archive_sets_archived_stage(
    db_session: Session, test_precuration, test_user_curator
):
    precuration_crud.soft_delete(
        db_session, db_obj=test_precuration, user_id=test_user_curator.id
    )
    assert test_precuration.workflow_stage == WorkflowStage.ARCHIVED


def test_activation_supersede_sets_archived_stage(
    db_session: Session,
    test_scope,
    test_gene,
    test_workflow_pair,
    test_user_curator,
    test_user_admin,
):
    first = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    second = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    for c in (first, second):
        workflow_engine._transition_to_active(
            db_session, c, test_user_admin.id, None, None
        )
        db_session.commit()
    db_session.refresh(first)
    assert first.workflow_stage == WorkflowStage.ARCHIVED
    assert second.workflow_stage == WorkflowStage.ACTIVE


def test_archived_is_terminal():
    engine = workflow_engine
    assert engine.valid_transitions[WorkflowStage.ARCHIVED] == []
    assert not any(
        WorkflowStage.ARCHIVED in targets
        for targets in engine.valid_transitions.values()
    )


def test_nobody_edits_an_archived_curation(
    db_session: Session, test_scope, test_gene, test_workflow_pair, test_user_curator
):
    c: CurationNew = _curation(
        db_session, test_scope, test_gene, test_workflow_pair, test_user_curator
    )
    c.workflow_stage = WorkflowStage.ARCHIVED
    c.status = CurationStatus.ARCHIVED
    db_session.commit()
    assert not ScopePermissionService.can_edit_curation(
        db_session, test_user_curator, c
    )
