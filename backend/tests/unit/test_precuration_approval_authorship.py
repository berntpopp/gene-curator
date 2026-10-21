"""Auto-created curation keeps the precuration author (4-eyes) and drafts are unique."""

import pytest
from sqlalchemy.orm import Session

from app.crud.precuration import precuration_crud
from app.crud.workflow_engine import workflow_engine
from app.models import CurationStatus, WorkflowStage
from app.schemas.precuration import PrecurationCreate
from tests.api.scopes.factories import (
    make_gene,
    make_member,
    make_precuration,
    make_scope,
    make_user,
)

pytestmark = pytest.mark.unit


def _approved_curation(db: Session):
    author, reviewer = make_user(db), make_user(db)
    scope = make_scope(db)
    make_member(db, scope, author, "curator")
    make_member(db, scope, reviewer, "reviewer")
    pre = make_precuration(
        db, scope=scope, gene=make_gene(db), creator=author, stage=WorkflowStage.REVIEW
    )
    pre.status = CurationStatus.SUBMITTED
    from app.models import WorkflowPair

    db.add(
        WorkflowPair(
            name="wf-x",
            version="1.0",
            precuration_schema_id=pre.precuration_schema_id,
            is_active=True,
        )
    )
    db.commit()
    result = precuration_crud.approve_and_create_curation(
        db, db_obj=pre, approver_id=reviewer.id
    )
    assert result.curation_id
    return author, reviewer, result.curation_id


def test_auto_created_curation_is_authored_by_precuration_author(db_session: Session):
    from app.models import CurationNew

    author, reviewer, curation_id = _approved_curation(db_session)
    curation = db_session.get(CurationNew, curation_id)
    assert curation.created_by == author.id
    assert curation.updated_by == reviewer.id
    assert workflow_engine._validate_4_eyes_principle(
        db_session, author, author.id, curation, "curation"
    )
    errors = workflow_engine._validate_4_eyes_principle(
        db_session, reviewer, reviewer.id, curation, "curation"
    )
    assert not any("4-eyes" in e for e in errors)


def test_duplicate_open_draft_returns_existing(db_session: Session):
    user, scope, gene = (
        make_user(db_session),
        make_scope(db_session),
        make_gene(db_session),
    )
    pre = make_precuration(db_session, scope=scope, gene=gene, creator=user)
    again = precuration_crud.create_precuration(
        db_session,
        obj_in=PrecurationCreate(
            gene_id=gene.id,
            scope_id=scope.id,
            precuration_schema_id=pre.precuration_schema_id,
            evidence_data={},
        ),
        user_id=user.id,
    )
    assert again.id == pre.id


def test_other_integrity_errors_are_not_swallowed(db_session: Session):
    from unittest.mock import patch

    from sqlalchemy.exc import IntegrityError

    user, scope, gene = (
        make_user(db_session),
        make_scope(db_session),
        make_gene(db_session),
    )
    schema_id = make_precuration(
        db_session, scope=scope, gene=make_gene(db_session), creator=user
    ).precuration_schema_id
    with (
        patch.object(
            db_session, "commit", side_effect=IntegrityError("x", {}, Exception())
        ),
        pytest.raises(IntegrityError),
    ):
        precuration_crud.create_precuration(
            db_session,
            obj_in=PrecurationCreate(
                gene_id=gene.id,
                scope_id=scope.id,
                precuration_schema_id=schema_id,
                evidence_data={},
            ),
            user_id=user.id,
        )
