"""Evidence CRUD operations for ClinGen SOP v11"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.base import CRUDBase
from app.models.models import EvidenceItem
from app.schemas.evidence import EvidenceItemCreate, EvidenceItemUpdate

logger = get_logger(__name__)


class CRUDEvidence(CRUDBase[EvidenceItem, EvidenceItemCreate, EvidenceItemUpdate]):
    """CRUD operations for evidence items"""

    def create_with_curation(
        self,
        db: Session,
        *,
        obj_in: EvidenceItemCreate,
        curation_id: UUID,
        user_id: UUID,
    ) -> EvidenceItem:
        """Create evidence item for curation"""
        db_obj = EvidenceItem(
            **obj_in.model_dump(),
            curation_id=curation_id,
            created_by=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Evidence item created",
            evidence_id=str(db_obj.id),
            curation_id=str(curation_id),
            category=db_obj.evidence_category,
            type=db_obj.evidence_type,
        )

        return db_obj

    def get_by_curation(
        self,
        db: Session,
        *,
        curation_id: UUID,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EvidenceItem]:
        """Get all evidence items for curation"""
        stmt = (
            select(EvidenceItem)
            .filter(EvidenceItem.curation_id == curation_id)
            .order_by(EvidenceItem.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if not include_deleted:
            stmt = stmt.filter(EvidenceItem.is_deleted == False)  # noqa: E712

        return list(db.execute(stmt).scalars().all())

    def get_by_category(
        self,
        db: Session,
        *,
        curation_id: UUID,
        category: str,
        include_deleted: bool = False,
    ) -> list[EvidenceItem]:
        """Get evidence items by category"""
        stmt = (
            select(EvidenceItem)
            .filter(
                EvidenceItem.curation_id == curation_id,
                EvidenceItem.evidence_category == category,
            )
            .order_by(EvidenceItem.created_at.desc())
        )

        if not include_deleted:
            stmt = stmt.filter(EvidenceItem.is_deleted == False)  # noqa: E712

        return list(db.execute(stmt).scalars().all())

    def update_with_user(
        self,
        db: Session,
        *,
        db_obj: EvidenceItem,
        obj_in: EvidenceItemUpdate,
        updated_by: UUID,
    ) -> EvidenceItem:
        """Update evidence item with user tracking"""
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_by"] = updated_by

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Evidence item updated",
            evidence_id=str(db_obj.id),
            updated_by=str(updated_by),
        )

        return db_obj

    def soft_delete(
        self, db: Session, *, db_obj: EvidenceItem, deleted_by: UUID
    ) -> EvidenceItem:
        """Soft delete evidence item (preserves audit trail)"""
        db_obj.is_deleted = True
        db_obj.deleted_at = datetime.now()
        db_obj.deleted_by = deleted_by

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Evidence item soft deleted",
            evidence_id=str(db_obj.id),
            deleted_by=str(deleted_by),
        )

        return db_obj

    def restore(self, db: Session, *, db_obj: EvidenceItem) -> EvidenceItem:
        """Restore soft-deleted evidence item"""
        db_obj.is_deleted = False
        db_obj.deleted_at = None
        db_obj.deleted_by = None

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info("Evidence item restored", evidence_id=str(db_obj.id))

        return db_obj

    def update_validation_status(
        self,
        db: Session,
        *,
        db_obj: EvidenceItem,
        status: str,
        errors: dict[str, Any] | None = None,
    ) -> EvidenceItem:
        """Update validation status for evidence item"""
        db_obj.validation_status = status
        db_obj.validation_errors = errors
        db_obj.validated_at = datetime.now()

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(
            "Evidence validation updated",
            evidence_id=str(db_obj.id),
            status=status,
        )

        return db_obj

    def update_score(
        self,
        db: Session,
        *,
        db_obj: EvidenceItem,
        score: float,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceItem:
        """Update computed score for evidence item"""
        db_obj.computed_score = score
        db_obj.score_metadata = metadata

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info("Evidence score updated", evidence_id=str(db_obj.id), score=score)

        return db_obj


evidence_crud = CRUDEvidence(EvidenceItem)
