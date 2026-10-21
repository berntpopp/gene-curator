"""Checks every route into review runs (#267): /submit, /workflow transitions, bulk."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import CurationNew
from app.scoring.point_limits import enforce_clingen_point_ranges
from app.services.publication_service import evidence_pmids, unknown_pmids


def review_guards(db: Session, curation: CurationNew) -> None:
    """422 on out-of-range points or a PMID Europe PMC does not know."""
    enforce_clingen_point_ranges(
        db,
        curation.workflow_pair_id,
        curation.evidence_data,
        curation.methodology_version_id,
    )
    pmids = evidence_pmids(curation.evidence_data)
    if unknown := unknown_pmids(db, pmids) if pmids else []:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"PMID {', '.join(unknown)} not found in Europe PMC; "
            "fix or remove before submitting",
        )
