"""Over MCP, a submit that names no reviewer goes to the scope's only eligible reviewer; with
several it is refused, naming reviewer_email and the candidates (KGDB QA: nothing
reaches review unassigned)."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.workflow_errors import WorkflowConflictError
from app.mcp.audit import request_channel
from app.models import AuditLogNew, Scope, UserNew
from app.schemas.precuration import PrecurationSubmit
from app.services.review_assignment import submit_reviewer
from tests.api.test_clingen_adoption import _member

pytestmark = pytest.mark.unit

UNNAMED = PrecurationSubmit(lock_version=0)


@pytest.fixture(autouse=True)
def over_mcp(request: pytest.FixtureRequest):
    token = request_channel.set(None if "web" in request.node.name else ("mcp", "x"))
    yield
    request_channel.reset(token)


def test_the_web_ui_submits_first_and_routes_after(
    db_session: Session, test_scope: Scope, test_user_curator: UserNew
) -> None:
    _member(db_session, test_scope, "reviewer", "Bob")
    _member(db_session, test_scope, "admin", "Ann")
    assert (
        submit_reviewer(db_session, test_scope.id, UNNAMED, test_user_curator.id)
        is None
    )


def test_the_only_reviewer_besides_the_author_is_assigned(
    db_session: Session, test_scope: Scope, test_user_curator: UserNew
) -> None:
    bob = _member(db_session, test_scope, "reviewer")
    assert submit_reviewer(
        db_session, test_scope.id, UNNAMED, test_user_curator.id
    ) == (bob.id)


def test_the_author_is_never_the_one_reviewer(
    db_session: Session, test_scope: Scope
) -> None:
    """No one else may review: refused (409), never left unrouted where nobody can
    pick it up (reviewers cannot self-assign)."""
    author = _member(db_session, test_scope, "admin")
    with pytest.raises(WorkflowConflictError, match="no eligible reviewer"):
        submit_reviewer(db_session, test_scope.id, UNNAMED, author.id)


def test_the_web_ui_still_submits_without_a_reviewer_in_reach(
    db_session: Session, test_scope: Scope
) -> None:
    author = _member(db_session, test_scope, "admin")
    assert submit_reviewer(db_session, test_scope.id, UNNAMED, author.id) is None


def test_several_reviewers_need_reviewer_email(
    db_session: Session, test_scope: Scope, test_user_curator: UserNew
) -> None:
    bob = _member(db_session, test_scope, "reviewer", "Bob")
    _member(db_session, test_scope, "admin", "Ann")
    with pytest.raises(ValueError, match="reviewer_email") as error:
        submit_reviewer(db_session, test_scope.id, UNNAMED, test_user_curator.id)
    assert bob.email in str(error.value)


def test_a_named_reviewer_is_kept(
    db_session: Session, test_scope: Scope, test_user_curator: UserNew
) -> None:
    bob = _member(db_session, test_scope, "reviewer", "Bob")
    _member(db_session, test_scope, "admin", "Ann")
    named = PrecurationSubmit(lock_version=0, reviewer_email=bob.email.upper())
    assert submit_reviewer(db_session, test_scope.id, named, test_user_curator.id) == (
        bob.id
    )


def test_a_corrector_is_skipped(
    db_session: Session, test_scope: Scope, test_user_curator: UserNew
) -> None:
    """D1: who corrected the item is never picked (it would fail with CORRECTED_OWN)."""
    item = uuid4()
    bob = _member(db_session, test_scope, "reviewer", "Bob")
    corrector = _member(db_session, test_scope, "admin", "Ann")
    db_session.add(
        AuditLogNew(
            entity_type="curation",
            entity_id=item,
            operation="UPDATE",
            change_type="disease_correction",
            user_id=corrector.id,
        )
    )
    db_session.commit()
    picked = submit_reviewer(
        db_session, test_scope.id, UNNAMED, test_user_curator.id, item_id=item
    )
    assert picked == bob.id


def test_a_scope_admin_submitter_is_skipped(
    db_session: Session, test_scope: Scope, test_user_curator: UserNew
) -> None:
    bob = _member(db_session, test_scope, "reviewer", "Bob")
    admin = _member(db_session, test_scope, "admin", "Ann")
    picked = submit_reviewer(
        db_session, test_scope.id, UNNAMED, test_user_curator.id, submitter=admin.id
    )
    assert picked == bob.id
