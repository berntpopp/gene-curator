"""Methodology bundle import endpoint (#575). Platform admin only; on /mcp/full, not /mcp."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.crud.methodology_import import import_bundle
from app.models import UserNew
from app.schemas.methodology_import import MethodologyBundle, MethodologyImportResult

router = APIRouter()


@router.post("/methodologies/import", response_model=MethodologyImportResult)
def import_methodology(
    *,
    db: Session = Depends(get_db),
    bundle: MethodologyBundle,
    dry_run: bool = Query(
        False, description="Return the plan and report; write nothing"
    ),
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> MethodologyImportResult:
    """Import a methodology bundle (schemas, workflow pairs, optional scope default).

    Re-importing the same bundle changes nothing; a schema whose content changed is
    overwritten and published as its next methodology version. Every schema runs the
    publish gate; any error refuses the whole import (422 with the report).
    """
    result = import_bundle(db, bundle, user_id=current_user.id, dry_run=dry_run)
    if result.errors and not dry_run:
        raise HTTPException(status_code=422, detail=result.model_dump(mode="json"))
    return result
