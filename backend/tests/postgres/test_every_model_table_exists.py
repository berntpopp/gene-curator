"""Every ORM table exists after the SQL migrations (publications was missing; 039)."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.models import Publication

pytestmark = pytest.mark.postgres


def test_every_model_table_exists(owner_session: Session) -> None:
    existing = set(
        owner_session.scalars(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        )
    )
    assert set(Base.metadata.tables) - existing == set()


def test_runtime_role_can_cache_and_read_publications(db: Session) -> None:
    """The API (app_user) inserts and reads cached publications under RLS."""
    db.add(Publication(pmid="99999991", title="t", authors=["A B"], journal="J"))
    db.flush()
    assert db.query(Publication).filter_by(pmid="99999991").one().title == "t"
