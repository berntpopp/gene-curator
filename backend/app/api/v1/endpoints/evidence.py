"""Evidence item management endpoints

Provides CRUD operations for evidence items associated with curations.
Implements scope-based permissions and four-eyes principle.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.crud.evidence import evidence_crud
from app.models.models import CurationNew, UserNew
from app.schemas.evidence import (
    EvidenceItem,
    EvidenceItemCreate,
    EvidenceItemUpdate,
)
from app.services.scope_permissions import ScopePermissionService

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/curations/{curation_id}/evidence",
    response_model=EvidenceItem,
    status_code=status.HTTP_201_CREATED,
)
@api_endpoint()
async def create_evidence_item(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    evidence_in: EvidenceItemCreate,
    current_user: UserNew = Depends(get_current_active_user),
) -> EvidenceItem:
    """Create new evidence item for curation

    Requires curator or scope_admin role in the curation's scope.

    Args:
        db: Database session
        curation_id: UUID of the curation to add evidence to
        evidence_in: Evidence item data
        current_user: Current authenticated user

    Returns:
        Created evidence item

    Raises:
        HTTPException: 404 if curation not found
        HTTPException: 403 if user lacks permission
    """
    # Get curation and check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()

    if not curation:
        logger.warning(
            "Curation not found for evidence creation",
            curation_id=str(curation_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    # Check edit permission
    if not ScopePermissionService.can_edit_curation(db, current_user, curation):
        logger.warning(
            "User lacks permission to add evidence",
            curation_id=str(curation_id),
            user_id=str(current_user.id),
            curation_stage=curation.workflow_stage.value,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit this curation",
        )

    # Create evidence item
    evidence = evidence_crud.create_with_curation(
        db,
        obj_in=evidence_in,
        curation_id=curation_id,
        user_id=current_user.id,
    )

    logger.info(
        "Evidence item created",
        evidence_id=str(evidence.id),
        curation_id=str(curation_id),
        category=evidence.evidence_category,
        user_id=str(current_user.id),
    )

    return evidence  # type: ignore[return-value]


@router.put(
    "/curations/{curation_id}/evidence/{item_id}",
    response_model=EvidenceItem,
)
@api_endpoint()
async def update_evidence_item(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    item_id: UUID,
    evidence_in: EvidenceItemUpdate,
    current_user: UserNew = Depends(get_current_active_user),
) -> EvidenceItem:
    """Update evidence item

    Requires curator or scope_admin role in the curation's scope.

    Args:
        db: Database session
        curation_id: UUID of the curation
        item_id: UUID of the evidence item to update
        evidence_in: Evidence item update data
        current_user: Current authenticated user

    Returns:
        Updated evidence item

    Raises:
        HTTPException: 404 if curation or evidence item not found
        HTTPException: 403 if user lacks permission
    """
    # Get curation and check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    if not ScopePermissionService.can_edit_curation(db, current_user, curation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit this curation",
        )

    # Get evidence item
    evidence = evidence_crud.get(db, id=item_id)

    if not evidence or evidence.curation_id != curation_id:
        logger.warning(
            "Evidence item not found or curation mismatch",
            item_id=str(item_id),
            curation_id=str(curation_id),
            found_curation_id=str(evidence.curation_id) if evidence else None,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found",
        )

    # Update evidence item
    evidence = evidence_crud.update_with_user(
        db,
        db_obj=evidence,
        obj_in=evidence_in,
        updated_by=current_user.id,
    )

    logger.info(
        "Evidence item updated",
        evidence_id=str(evidence.id),
        curation_id=str(curation_id),
        user_id=str(current_user.id),
    )

    return evidence  # type: ignore[return-value]


@router.delete(
    "/curations/{curation_id}/evidence/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@api_endpoint()
async def delete_evidence_item(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    item_id: UUID,
    current_user: UserNew = Depends(get_current_active_user),
) -> None:
    """Delete evidence item (soft delete)

    Requires curator or scope_admin role in the curation's scope.

    Args:
        db: Database session
        curation_id: UUID of the curation
        item_id: UUID of the evidence item to delete
        current_user: Current authenticated user

    Raises:
        HTTPException: 404 if curation or evidence item not found
        HTTPException: 403 if user lacks permission
    """
    # Get curation and check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    if not ScopePermissionService.can_edit_curation(db, current_user, curation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit this curation",
        )

    # Get evidence item
    evidence = evidence_crud.get(db, id=item_id)

    if not evidence or evidence.curation_id != curation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found",
        )

    # Soft delete
    evidence_crud.soft_delete(db, db_obj=evidence, deleted_by=current_user.id)

    logger.info(
        "Evidence item deleted",
        evidence_id=str(evidence.id),
        curation_id=str(curation_id),
        user_id=str(current_user.id),
    )


@router.get(
    "/curations/{curation_id}/evidence",
    response_model=list[EvidenceItem],
)
@api_endpoint()
async def list_evidence_items(
    *,
    db: Session = Depends(get_db),
    curation_id: UUID,
    current_user: UserNew = Depends(get_current_active_user),
) -> list[EvidenceItem]:
    """Get all evidence items for curation

    Returns all non-deleted evidence items for the curation if user has view permission.

    Args:
        db: Database session
        curation_id: UUID of the curation
        current_user: Current authenticated user

    Returns:
        List of evidence items

    Raises:
        HTTPException: 404 if curation not found
        HTTPException: 403 if user lacks permission
    """
    # Get curation and check permissions
    curation = db.query(CurationNew).filter(CurationNew.id == curation_id).first()

    if not curation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curation not found",
        )

    if not ScopePermissionService.can_view_curation(db, current_user, curation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view this curation",
        )

    # Get evidence items
    evidence_items = evidence_crud.get_by_curation(db, curation_id=curation_id)

    logger.debug(
        "Listed evidence items",
        curation_id=str(curation_id),
        count=len(evidence_items),
        user_id=str(current_user.id),
    )

    return evidence_items  # type: ignore[return-value]
