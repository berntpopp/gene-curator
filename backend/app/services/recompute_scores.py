"""One-off, idempotent backfill: recompute persisted scores for every curation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.curation import _update_computed_scores
from app.models.models import CurationNew

logger = get_logger(__name__)


def recompute_all_scores(db: Session) -> int:
    """Run the engine over every curation and commit; returns the number updated."""
    curations = db.scalars(select(CurationNew)).all()
    for curation in curations:
        _update_computed_scores(curation)
    db.commit()
    logger.info("Recomputed curation scores", count=len(curations))
    return len(curations)


if __name__ == "__main__":  # pragma: no cover
    from app.core.database import get_db

    recompute_all_scores(next(get_db()))
