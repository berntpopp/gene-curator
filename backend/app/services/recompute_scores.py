"""One-off, idempotent backfill: recompute persisted ClinGen scores for every curation.

Run once after deploying 046 (Models & Rescue as one category capped at 4):
``cd backend && uv run python -m app.services.recompute_scores``. Every curation whose
total or class changes is logged with its gene and old -> new total and class. Rows are
scored with their pinned point model, custom categories included (reported); rows holding
evidence keys that model does not score are skipped and reported with those keys.
"""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import set_rls_context
from app.core.logging import get_logger
from app.models.models import CurationNew, Gene, UserNew, UserRoleNew
from app.scoring.clingen import ENGINE_NAME, ClinGenEngine
from app.scoring.point_limits import scoring_configuration
from app.scoring.point_model import point_model

logger = get_logger(__name__)

_TEXT = {"evidence_summary"}  # free text the ClinGen forms write; never scored


def _unscored_keys(evidence: Any, model: dict[str, Any]) -> list[str]:
    """Keys of non-empty evidence that the point model does not score, dotted and sorted:
    its sections with their types' first path segment, override and band inputs."""
    if not isinstance(evidence, dict):
        return ["evidence_data"] if evidence else []
    sections = {
        s["key"]: {t["path"].split(".")[0] for c in s["categories"] for t in c["types"]}
        for s in model["sections"]
    }
    known = {*sections, *_TEXT}
    known |= {o["when"] for o in model.get("overrides", [])}
    known |= {b["requires"] for b in model["bands"] if "requires" in b}
    unscored = set(evidence) - known
    for key, types in sections.items():
        if isinstance(evidence.get(key), dict):
            unscored |= {f"{key}.{k}" for k in set(evidence[key]) - types}
    return sorted(unscored)


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
    unscored: dict[str, list[str]] = {}
    custom: set[str] = set()
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
        try:
            config = scoring_configuration(db, pair_id, version_id)
            if config.get("engine", ENGINE_NAME) != ENGINE_NAME:
                skipped.append(
                    str(curation_id)
                )  # GenCC/qualitative: not ClinGen points
                continue
            model = point_model(config) or engine._template()
            if keys := _unscored_keys(evidence, model):
                # never overwrite with an unjustified verdict
                skipped.append(str(curation_id))
                unscored[str(curation_id)] = keys
                continue
            # keys the template would not score but the pinned model does
            custom.update(_unscored_keys(evidence, engine._template()))
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
        old_total = (old_scores or {}).get("total_score")
        if (old_total, old_verdict) != (result.total_score, result.verdict):
            logger.warning(  # clinical audit: every changed total or class
                "Curation class changed"
                if old_verdict != result.verdict
                else "Curation total changed",
                curation_id=str(curation_id),
                gene=gene,
                total=f"{old_total} -> {result.total_score}",
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
        unscored=unscored,
        custom_categories=sorted(custom),
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
