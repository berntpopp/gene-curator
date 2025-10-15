"""Evidence item Pydantic schemas for ClinGen SOP v11"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItemBase(BaseModel):
    """Base schema for evidence items"""

    evidence_category: str = Field(
        ...,
        description="Evidence category: case_level, segregation, case_control, expression, protein_function, models, rescue",
    )
    evidence_type: str = Field(
        ..., description="Evidence type: genetic or experimental"
    )
    evidence_data: dict[str, Any] = Field(
        ..., description="Complete evidence data structure (JSONB)"
    )


class EvidenceItemCreate(EvidenceItemBase):
    """Schema for creating evidence item"""

    pass


class EvidenceItemUpdate(BaseModel):
    """Schema for updating evidence item"""

    evidence_data: dict[str, Any] | None = Field(
        None, description="Updated evidence data"
    )
    validation_status: str | None = Field(
        None, description="Validation status: pending, valid, invalid"
    )


class EvidenceItem(EvidenceItemBase):
    """Complete evidence item schema"""

    id: UUID
    curation_id: UUID
    computed_score: float | None = Field(
        None, description="Individual item score (from scoring engine)"
    )
    score_metadata: dict[str, Any] | None = Field(
        None, description="Scoring calculation details"
    )
    validation_status: str = Field(..., description="Validation status")
    validation_errors: dict[str, Any] | None = Field(
        None, description="Validation errors if any"
    )
    validated_at: datetime | None = Field(None, description="Validation timestamp")
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID | None = None
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemWithDetails(EvidenceItem):
    """Evidence item with creator details"""

    creator_name: str | None = None
    creator_email: str | None = None

    model_config = ConfigDict(from_attributes=True)
