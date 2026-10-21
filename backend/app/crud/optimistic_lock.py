"""Atomic compare-and-increment for optimistic locking (curations and precurations)."""

from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session


def update_if_version(
    db: Session, model: Any, pk: UUID, expected: int, values: dict[str, Any]
) -> bool:
    """`UPDATE ... SET values, lock_version = lock_version + 1 WHERE id = ? AND lock_version = ?`.

    One statement, so two writers cannot both pass the check: the loser matches no row. Commits
    on success, rolls back (and returns False) when the version is stale.
    """
    result = db.execute(
        update(model)
        .where(model.id == pk, model.lock_version == expected)
        .values(**values, lock_version=model.lock_version + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        return False
    db.commit()
    return True
