"""Adopt ClinGen classifications in bulk (#105); on /mcp as adopt_clingen_classifications."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user, set_rls_context
from app.models import UserNew
from app.schemas.clingen_adoption import ClinGenAdoptionRequest, ClinGenAdoptionResult
from app.services.clingen_adoption import adopt

router = APIRouter()


@router.post("/clingen-adoptions", response_model=ClinGenAdoptionResult)
def adopt_clingen_classifications(
    *,
    db: Session = Depends(get_db),
    request: ClinGenAdoptionRequest,
    dry_run: bool = Query(
        False, description="Return the plan and report; write nothing"
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> ClinGenAdoptionResult:
    """Adopt ClinGen classifications for entities ClinGen already curated (curator). Rows:
    the entity plus the GeneFoundry clingen_get_gene_validity record verbatim (perm_id as
    cggv_id, raw_sha256 as record_sha256, recommended_citation as citation). Gene, MONDO and
    MOI must match the entity, the class the schema's. Each curation goes to review with an
    automatic re-score comment; another reviewer approves. Same record again: unchanged; an
    entity with an open curation or any invalid row: 422, nothing written."""
    set_rls_context(db, current_user)
    result = adopt(db, request.rows, current_user, dry_run=dry_run)
    if result.errors and not dry_run:
        raise HTTPException(status_code=422, detail=result.model_dump(mode="json"))
    return result
