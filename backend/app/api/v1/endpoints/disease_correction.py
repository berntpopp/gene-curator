"""POST /curations/{id}/disease-correction: a scope admin's audited correction of a legacy
curation's disease entity (#453)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.capabilities import MANAGE_MEMBERS, require
from app.core.database import get_db, raise_if_rls_denied
from app.core.deps import get_current_active_user, set_rls_context
from app.core.logging import api_endpoint, get_logger
from app.crud.disease_correction import correct_disease
from app.models import CurationNew, UserNew
from app.schemas.curation import Curation
from app.schemas.disease_correction import DiseaseCorrection

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{curation_id}/disease-correction", response_model=Curation)
@api_endpoint()
def correct_curation_disease(
    curation_id: UUID,
    body: DiseaseCorrection,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> Curation:
    """Set the curation's own disease entity (name, MONDO id, inheritance, optionally the
    relationship type) with a reason; written to the audit log with old and new values.
    Scope admins only, on a draft or sent-back curation; 409 on a stale lock_version or
    when another open curation already has that entity."""
    set_rls_context(db, current_user)
    curation = db.get(CurationNew, curation_id)
    if curation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Curation not found")
    # Scope admins: scope.members.manage is the capability only they hold
    require(db, current_user, curation.scope_id, MANAGE_MEMBERS)
    try:
        saved = correct_disease(db, curation, body, current_user)
    except DBAPIError as e:
        db.rollback()
        raise_if_rls_denied(e, "Not authorized to correct this curation")
        raise
    if not saved:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This curation changed since you loaded it; reload and try again",
        )
    db.refresh(curation)
    logger.info(
        "Curation disease entity corrected",
        curation_id=str(curation_id),
        user_id=str(current_user.id),
    )
    return Curation.model_validate(curation)
