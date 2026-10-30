"""#464: the opt-in second view queued on submit never fails the submit or runs twice."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.llm import LLMRun
from app.services.llm_runs import queue_on_submit
from tests.api.llm_api_support import llm_env  # noqa: F401
from tests.services.llm_run_support import World, world_fixture  # noqa: F401

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("llm_env")]


def _runs(db: Session) -> list[LLMRun]:
    db.expire_all()
    return list(db.scalars(select(LLMRun)))


def _opt_in(db: Session, w: World, **values: object) -> None:
    w.settings.auto_second_view_on_submit = True
    w.settings.updated_by = w.scope_admin.id
    for key, value in values.items():
        setattr(w.settings, key, value)
    db.commit()


def test_off_by_default_queues_nothing(db_session: Session, world: World) -> None:
    world.settings.updated_by = world.scope_admin.id
    db_session.commit()
    queue_on_submit(db_session, world.curation)
    assert _runs(db_session) == []


def test_on_queues_once_for_the_admin_who_opted_in(
    db_session: Session, world: World
) -> None:
    _opt_in(db_session, world)
    queue_on_submit(db_session, world.curation)
    queue_on_submit(db_session, world.curation)  # still pending: not queued again
    runs = _runs(db_session)
    assert [(r.strategy, r.status) for r in runs] == [("skeptic", "queued")]
    assert runs[0].created_by == world.scope_admin.id


@pytest.mark.parametrize(
    "values",
    [
        {"daily_run_cap": 0},  # cap refusal
        {"enabled": False},  # scope opted out of LLM runs altogether
        {"updated_by": None},  # nobody to run it for
    ],
)
def test_refusals_are_logged_not_raised(
    db_session: Session, world: World, values: dict[str, object]
) -> None:
    _opt_in(db_session, world, **values)
    queue_on_submit(db_session, world.curation)
    assert _runs(db_session) == []


def test_inactive_owner_queues_nothing(db_session: Session, world: World) -> None:
    _opt_in(db_session, world)
    world.scope_admin.is_active = False
    db_session.commit()
    queue_on_submit(db_session, world.curation)
    assert _runs(db_session) == []
