"""Move a schema's curations to a newer methodology version (#591). Platform admin only;
on /mcp/full, not /mcp."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.core.database import get_db
from app.models import UserNew
from app.services.version_move import (
    StaleVersionError,
    VersionMoveResult,
    VersionNotFoundError,
    move_to_version as move,
)

router = APIRouter()


@router.post(
    "/curation-schemas/{schema_id}/move-to-version", response_model=VersionMoveResult
)
def move_to_version(
    *,
    db: Session = Depends(get_db),
    schema_id: UUID,
    version: int | None = Query(
        None, ge=1, description="The planned target; refused unless still the latest"
    ),
    dry_run: bool = Query(True, description="Return the plan; write nothing"),
    current_user: UserNew = Depends(deps.get_current_admin_user),
) -> VersionMoveResult:
    """Move every curation and precuration of the schema to its latest methodology version.

    A dry run (the default) lists per row the fields kept and dropped, new required fields
    now empty and old -> new score and class. Apply re-pins, drops the gone fields,
    rescores and audit-logs every row in one transaction. An active curation whose class
    changes, or that misses a new required field, stays active: an open copy on the new
    version goes to review (its earlier reviewers are asked again) or to draft and
    replaces it once approved (4-eyes). Running it twice changes nothing. ``version``
    (the planned target) must still be the latest, else 409.
    """
    try:
        result = move(
            db, schema_id, version=version, user_id=current_user.id, dry_run=dry_run
        )
    except VersionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except StaleVersionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return result
