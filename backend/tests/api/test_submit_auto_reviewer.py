"""Over MCP, a submit that names no reviewer goes to the scope's only eligible reviewer; with
several it is refused, naming reviewer_email and the candidates (KGDB QA: nothing
reaches review unassigned)."""

import pytest
from sqlalchemy.orm import Session

from app.mcp.audit import request_channel
from app.models import Scope, UserNew
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
    """No one else to review: it stays unrouted, as before (a reviewer may join)."""
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
