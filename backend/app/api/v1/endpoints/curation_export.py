"""Export v1 of reviewed curations for downstream publishers (#532). Contract: docs/EXPORT.md."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.core.logging import api_endpoint
from app.crud.curation_export import export_curations
from app.crud.scope_visibility import scope_id_for
from app.models import UserNew
from app.schemas.curation_export import CurationExportPage

# Public, but a signed-in caller's RLS context adds the private scopes they belong to.
router = APIRouter(dependencies=[Depends(get_current_user_optional)])

MAX_PAGE = 500


def _cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if not cursor:
        return None
    try:
        at, _, row_id = cursor.partition("|")
        return datetime.fromisoformat(at), UUID(row_id)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Invalid cursor: pass next_cursor from the previous page unchanged",
        ) from None


@router.get("/curations", response_model=CurationExportPage)
@api_endpoint()
def export_reviewed_curations(
    db: Session = Depends(get_db),
    scope_name: str | None = Query(None, max_length=255, description="Scope name"),
    scope_id: UUID | None = Query(None, description="Scope UUID"),
    updated_since: datetime | None = Query(
        None, description="Only curations changed at or after this time (ISO 8601)"
    ),
    cursor: str | None = Query(
        None, max_length=100, description="next_cursor of the previous page"
    ),
    limit: int = Query(100, ge=1, le=MAX_PAGE, description="Page size"),
    current_user: UserNew | None = Depends(get_current_user_optional),
) -> CurationExportPage:
    """Active and archived curations of the scopes the caller may see, oldest change first.

    Anonymous callers see active curations of public scopes; members also see their
    scopes' archived ones. Retracted curations are deleted and never appear."""
    user_id = current_user.id if current_user else None
    return export_curations(
        db,
        user_id,
        scope_id_for(db, user_id, scope_id, scope_name),
        updated_since,
        _cursor(cursor),
        limit,
    )
