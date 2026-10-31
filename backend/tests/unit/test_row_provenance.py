"""Row authorship stamps (#593): kept, changed or added, beside the evidence."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import UserNew
from app.services.audit_trail import _name
from app.services.row_provenance import _stamp, actor

pytestmark = pytest.mark.unit

ALICE = {"id": "a", "name": "Alice"}
BOB = {"id": "b", "name": "Bob", "agent": {"model": "m"}}


def test_stamps_follow_the_rows_and_never_touch_the_evidence() -> None:
    first_ev = {"t": {"rows": [{"id": 1, "v": "x"}, {"v": "y"}]}}
    first = _stamp(None, first_ev, {}, ALICE, "t1")
    added = {"added_by": ALICE, "added_at": "t1"}
    assert first == {"t.rows#1": added, "t.rows[1]": added}  # by id, else by index
    second_ev = {
        "t": {
            "rows": [
                {"id": 1, "v": "x2"},  # edited, matched by id
                {"v": "y"},  # unchanged
                {"v": "z"},  # new
                {"v": ""},  # blank: no stamp
            ]
        },
        "n": [1, 2],
    }
    second = _stamp(first_ev, second_ev, first, BOB, "t2")
    assert second["t.rows#1"] == {**added, "changed_by": BOB, "changed_at": "t2"}
    assert second["t.rows[1]"] == added
    assert second["t.rows[2]"] == {"added_by": BOB, "added_at": "t2"}
    assert "t.rows[3]" not in second
    assert second_ev["t"]["rows"][0] == {"id": 1, "v": "x2"}  # evidence untouched


def test_rows_without_ids_match_by_position_or_content() -> None:
    first = _stamp(None, {"rows": [{"v": "a"}, {"v": "b"}]}, {}, ALICE, "t1")
    assert set(first) == {"rows[0]", "rows[1]"}
    # Row b moved up: matched by content, keeps its stamp at the new index
    moved = _stamp(
        {"rows": [{"v": "a"}, {"v": "b"}]}, {"rows": [{"v": "b"}]}, first, BOB, "t2"
    )
    assert moved == {"rows[0]": {"added_by": ALICE, "added_at": "t1"}}
    edited = _stamp({"rows": [{"v": "a"}]}, {"rows": [{"v": "c"}]}, first, BOB, "t2")
    assert edited["rows[0]"]["changed_by"] == BOB
    assert edited["rows[0]"]["added_by"] == ALICE
    legacy = _stamp({"rows": [{"v": "a"}]}, {"rows": [{"v": "a"}]}, {}, BOB, "t2")
    assert legacy == {}  # an untouched legacy row stays unstamped


def test_a_nameless_user_never_shows_their_email(db_session: Session) -> None:
    """Review #602 item 7: provenance and the history reach the public export."""
    user = UserNew(
        id=uuid4(),
        email="hidden@example.org",
        name="",
        hashed_password="x",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    assert actor(db_session, user.id)["name"] is None
    assert _name(db_session, user.id) is None
