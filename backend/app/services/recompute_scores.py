"""One-off, idempotent backfill: recompute persisted ClinGen scores for every curation.

Run once after deploying 046 (Models & Rescue as one category capped at 4):
``cd backend && uv run python -m app.services.recompute_scores``. Every curation whose
class changes is logged with its gene and old -> new total and class.
"""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import set_rls_context
from app.core.logging import get_logger
from app.models.models import CurationNew, Gene, UserNew, UserRoleNew
from app.scoring.clingen import ENGINE_NAME, ClinGenEngine
from app.scoring.point_limits import scoring_configuration

logger = get_logger(__name__)


_TOP = {"genetic_evidence", "experimental_evidence", "contradictory_evidence"}
_TOP |= {"replicated_over_time", "evidence_summary"}
_GENETIC = {"case_level", "segregation", "case_control"}
_EXPERIMENTAL = {"function", "functional_alteration", "models", "rescue"}


def _has_unscored_keys(evidence: Any) -> bool:
    """True when non-empty evidence holds keys the engine does not score."""
    if not isinstance(evidence, dict):
        return bool(evidence)
    if set(evidence) - _TOP:
        return True
    for key, known in (
        ("genetic_evidence", _GENETIC),
        ("experimental_evidence", _EXPERIMENTAL),
    ):
        if isinstance(evidence.get(key), dict) and set(evidence[key]) - known:
            return True
    return False


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
    cols = (CurationNew.id, CurationNew.evidence_data, CurationNew.computed_scores)
    pin = (CurationNew.workflow_pair_id, CurationNew.methodology_version_id)
    curations = db.execute(
        select(
            *cols, CurationNew.computed_verdict, *pin, Gene.approved_symbol
        ).outerjoin(Gene, Gene.id == CurationNew.gene_id)
    ).all()
    updated = unchanged = 0
    skipped: list[str] = []
    failed = 0
    for (
        curation_id,
        evidence,
        old_scores,
        old_verdict,
        pair_id,
        version_id,
        gene,
    ) in curations:
        if _has_unscored_keys(evidence):
            skipped.append(
                str(curation_id)
            )  # never overwrite with an unjustified verdict
            continue
        try:
            config = scoring_configuration(db, pair_id, version_id)
            if config.get("engine", ENGINE_NAME) != ENGINE_NAME:
                skipped.append(
                    str(curation_id)
                )  # GenCC/qualitative: not ClinGen points
                continue
            result = engine.calculate_scores(evidence or {}, config)
        except Exception:  # one bad legacy row must not abort the backfill
            failed += 1
            logger.error(
                "Score recompute failed", curation_id=str(curation_id), exc_info=True
            )
            continue
        scores = {**result.scores, **result.evidence_breakdown}
        if (old_scores, old_verdict) == (scores, result.verdict):
            unchanged += 1
            continue
        updated += 1
        if old_verdict != result.verdict:
            logger.warning(
                "Curation class changed",
                curation_id=str(curation_id),
                gene=gene,
                total=f"{(old_scores or {}).get('total_score')} -> {result.total_score}",
                verdict=f"{old_verdict} -> {result.verdict}",
            )
        db.execute(
            update(CurationNew)
            .where(CurationNew.id == curation_id)
            .values(
                computed_scores=scores,
                computed_verdict=result.verdict,
                computed_summary=result.verdict_rationale,
                updated_at=CurationNew.updated_at,  # keep: a backfill is not an edit
            )
        )
    db.commit()
    logger.info(
        "Recomputed curation scores",
        updated=updated,
        unchanged=unchanged,
        skipped=len(skipped),
        skipped_ids=skipped,
        failed=failed,
    )
    if failed:
        raise RuntimeError(
            f"{failed} of {len(curations)} curations failed to recompute"
        )
    return updated + unchanged


if __name__ == "__main__":  # pragma: no cover
    from app.core.database import get_db

    recompute_all_scores(next(get_db()))
