"""Schemas for per-item review comments and the evidence diff."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CommentStatus = Literal["open", "resolved"]


def _no_nul(value: str) -> str:
    if "\x00" in value:  # PostgreSQL text cannot hold NUL
        raise ValueError("must not contain NUL characters")
    return value


class ReviewCommentCreate(BaseModel):
    item_path: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=5000)
    review_id: UUID | None = None

    _clean = field_validator("item_path", "body")(_no_nul)


class ReviewCommentUpdate(BaseModel):
    body: str | None = Field(None, min_length=1, max_length=5000)
    status: CommentStatus | None = None

    _clean = field_validator("body")(lambda v: v if v is None else _no_nul(v))

    @model_validator(mode="after")
    def _something_changes(self) -> "ReviewCommentUpdate":
        if self.body is None and self.status is None:
            raise ValueError("provide body and/or status")
        return self


class ReviewComment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    curation_id: UUID
    review_id: UUID | None
    item_path: str
    body: str
    author_id: UUID
    status: CommentStatus
    created_at: datetime
    updated_at: datetime


class DiffItem(BaseModel):
    path: str
    change: Literal["added", "removed", "changed"]
    before: Any = None
    after: Any = None


class DiffBaseline(BaseModel):
    audit_id: int
    submitted_at: datetime


class CurationDiff(BaseModel):
    """Current evidence versus its snapshot at the last submission (baseline null: never submitted)."""

    baseline: DiffBaseline | None
    items: list[DiffItem]
