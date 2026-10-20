"""Shared fixtures for WorkflowEngine unit tests (scope with curator, reviewer)."""

import pytest
from sqlalchemy.orm import Session

from app.crud.workflow_engine import WorkflowEngine
from app.models.models import Scope, UserNew
from tests.api.scopes.factories import make_member, make_scope, make_user


@pytest.fixture
def engine() -> WorkflowEngine:
    return WorkflowEngine()


@pytest.fixture
def scope(db_session: Session) -> Scope:
    return make_scope(db_session)


@pytest.fixture
def creator(db_session: Session, scope: Scope) -> UserNew:
    user = make_user(db_session, name="Creator")
    make_member(db_session, scope, user, "curator")
    return user


@pytest.fixture
def reviewer(db_session: Session, scope: Scope) -> UserNew:
    user = make_user(db_session, name="Reviewer")
    make_member(db_session, scope, user, "reviewer")
    return user
