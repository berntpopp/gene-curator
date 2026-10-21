"""One-off, idempotent backfill: recompute persisted scores for every curation."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import set_rls_context
from app.core.logging import get_logger
from app.models.models import CurationNew, UserNew, UserRoleNew
from app.scoring.clingen import ClinGenEngine

logger = get_logger(__name__)


def recompute_all_scores(db: Session) -> int:
    """Run the engine over every curation under an admin RLS context; returns the count."""
    admin = db.scalars(
        select(UserNew).where(UserNew.role == UserRoleNew.ADMIN, UserNew.is_active)
    ).first()
    if admin is None:
        raise RuntimeError("No active application admin found for the RLS context")
    if db.get_bind().dialect.name == "postgresql":
        set_rls_context(db, admin)
    engine = ClinGenEngine()
    curations = db.execute(select(CurationNew.id, CurationNew.evidence_data)).all()
    failed = 0
    for curation_id, evidence in curations:
        try:
            result = engine.calculate_scores(evidence or {}, {})
        except Exception:  # one bad legacy row must not abort the backfill
            failed += 1
            logger.error(
                "Score recompute failed", curation_id=str(curation_id), exc_info=True
            )
            continue
        db.execute(
            update(CurationNew)
            .where(CurationNew.id == curation_id)
            .values(
                computed_scores={**result.scores, **result.evidence_breakdown},
                computed_verdict=result.verdict,
                computed_summary=result.verdict_rationale,
                updated_at=CurationNew.updated_at,  # keep: a backfill is not an edit
            )
        )
    db.commit()
    logger.info(
        "Recomputed curation scores", count=len(curations) - failed, failed=failed
    )
    if failed:
        raise RuntimeError(
            f"{failed} of {len(curations)} curations failed to recompute"
        )
    return len(curations)


if __name__ == "__main__":  # pragma: no cover
    from app.core.database import get_db

    recompute_all_scores(next(get_db()))
