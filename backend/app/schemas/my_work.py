"""Schemas for the My Work inbox (GET /me/work)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.curation import RelationshipType

WorkTab = Literal["needs_you", "waiting", "done"]
WorkKind = Literal[
    "assignment", "draft", "changes_requested", "review", "waiting", "done"
]


class WorkItem(BaseModel):
    kind: WorkKind
    tab: WorkTab
    verb: str = Field(..., description="Next action, e.g. 'Review curation'")
    item_type: Literal["assignment", "precuration", "curation"]
    item_id: UUID
    gene_id: UUID
    gene_symbol: str
    scope_id: UUID
    scope_name: str
    link: str = Field(..., description="Frontend route that opens the work")
    updated_at: datetime | None = None
    due_date: date | None = Field(None, description="Assignment due date")
    disease_name: str | None = None
    mode_of_inheritance: str | None = None
    relationship_type: RelationshipType = "mendelian"
    stage: str | None = Field(None, description="Workflow stage; null for assignments")
    classification: str | None = Field(
        None, description="Calculated classification (curations only)"
    )


class MyWorkResponse(BaseModel):
    items: list[WorkItem]
    counts: dict[WorkTab, int] = Field(
        ..., description="needs_you equals the rail badge count"
    )
