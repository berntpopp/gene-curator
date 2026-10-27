"""One-off, idempotent backfill: recompute persisted ClinGen scores for every curation.

Run once after deploying 046 (Models & Rescue as one category capped at 4):
``cd backend && uv run python -m app.services.recompute_scores``. Every curation whose
total or class changes is logged with its gene and old -> new total and class. Rows are
scored with their pinned point model, custom categories included (reported); rows holding
evidence keys that model does not score are skipped and reported with those keys. Active
and archived curations whose rows now lack a PMID or a real variant keep their result until
edited and resubmitted; they are logged as kept_uncited.
"""

from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.core.deps import set_rls_context
from app.core.logging import get_logger
from app.models.models import CurationNew, Gene, UserNew, UserRoleNew
from app.scoring.clingen import ENGINE_NAME, ClinGenEngine
from app.scoring.evidence_items import UNCITED, has_content
from app.scoring.point_limits import scoring_configuration
from app.scoring.point_model import point_model
from app.services.evidence_ids import score_scorable
from app.services.publication_service import evidence_pmids, lookup_pmids

logger = get_logger(__name__)

_TEXT = {"evidence_summary"}  # free text the ClinGen forms write; never scored


def _unscored_keys(evidence: Any, model: dict[str, Any]) -> list[str]:
    """Non-empty evidence outside complete model type paths, override and band inputs."""
    if not isinstance(evidence, dict):
        return ["evidence_data"] if has_content(evidence) else []
    sections = {s["key"] for s in model["sections"]}
    known = {
        f"{s['key']}.{t['path']}"
        for s in model["sections"]
        for c in s["categories"]
        for t in c["types"]
    }
    known |= _TEXT | {o["when"] for o in model.get("overrides", [])}
    known |= {b["requires"] for b in model["bands"] if "requires" in b}

    def unknown(node: Any, path: str) -> list[str]:
        if path in known or not has_content(node):
            return []
        if path in sections and isinstance(node, list):
            return []  # the engine also supports legacy section lists
        if not any(k.startswith(f"{path}.") for k in known):
            return [path]
        if isinstance(node, dict):
            return [p for k, v in node.items() for p in unknown(v, f"{path}.{k}")]
        return [path]  # non-empty data where the model requires a parent object

    return sorted(p for key, value in evidence.items() for p in unknown(value, key))


def _save(
    db: Session,
    curation_id: Any,
    scores: dict[str, Any],
    result: Any,
    old_scores: dict[str, Any] | None,
    old_verdict: str | None,
    gene: str | None,
) -> bool:
    """Write the new scores; False when no row was updated (RLS refused it)."""
    written = cast(
        CursorResult[Any],
        db.execute(
            update(CurationNew)
            .where(CurationNew.id == curation_id)
            .values(
                computed_scores=scores,
                computed_verdict=result.verdict,
                computed_summary=result.verdict_rationale,
                updated_at=CurationNew.updated_at,  # keep: a backfill is not an edit
            )
        ),
    )
    if written.rowcount == 0:
        return False
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
    return True


def _keeps_result(status: Any, breakdown: dict[str, Any]) -> bool:
    """Active and archived curations keep their result (history is not rescored) until
    resubmitted when rows now lack a citation."""
    excluded = breakdown.get("excluded", [])
    kept = status in ("active", "archived")
    return kept and any(e.get("reason") in UNCITED for e in excluded)


def _raise_if_failed(failed: int, total: int) -> None:
    if failed:
        raise RuntimeError(f"{failed} of {total} curations failed to recompute")


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
            *cols,
            CurationNew.computed_verdict,
            *pin,
            Gene.approved_symbol,
            CurationNew.status,
        ).outerjoin(Gene, Gene.id == CurationNew.gene_id)
    ).all()
    # One bounded lookup for all PMIDs, as saves do: unknown ones score nothing
    pmids = set().union(*(evidence_pmids(row[1]) for row in curations))
    unknown = set(lookup_pmids(db, pmids)[0]) if pmids else set()
    updated = unchanged = 0
    skipped: list[str] = []
    kept_uncited: list[str] = []
    unscored: dict[str, list[str]] = {}
    custom: set[str] = set()
    flagged: dict[str, list[str]] = {}
    failed = 0
    for (
        curation_id,
        evidence,
        old_scores,
        old_verdict,
        pair_id,
        version_id,
        gene,
        status,
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
            result = score_scorable(engine, config, evidence or {}, unknown)
        except Exception:  # one bad legacy row must not abort the backfill
            failed += 1
            logger.error(
                "Score recompute failed", curation_id=str(curation_id), exc_info=True
            )
            continue
        flagged[str(curation_id)] = [
            flag["path"]
            for flag in result.evidence_breakdown["trace"].get("out_of_range", [])
        ]
        scores = {
            **result.scores,
            **result.evidence_breakdown,
            "warnings": result.warnings,
        }
        if (old_scores, old_verdict) == (scores, result.verdict):
            unchanged += 1
            continue
        if _keeps_result(status, scores):  # its new score differs: reported, not saved
            kept_uncited.append(str(curation_id))
            continue
        if not _save(db, curation_id, scores, result, old_scores, old_verdict, gene):
            # RLS refused it, e.g. a curation of an inactive scope (054)
            skipped.append(str(curation_id))
            continue
        updated += 1
    db.commit()
    logger.info(
        "Recomputed curation scores",
        updated=updated,
        unchanged=unchanged,
        kept_uncited=len(kept_uncited),
        kept_uncited_ids=kept_uncited,
        skipped=len(skipped),
        skipped_ids=skipped,
        unscored=unscored,
        custom_categories=sorted(custom),
        out_of_range={key: paths for key, paths in flagged.items() if paths},
        failed=failed,
    )
    _raise_if_failed(failed, len(curations))
    return updated + unchanged + len(kept_uncited)


if __name__ == "__main__":  # pragma: no cover
    from app.core.database import get_db

    recompute_all_scores(next(get_db()))
