"""Schemas for per-item review comments and the evidence diff."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CommentStatus = Literal["open", "resolved"]
CommentKind = Literal["query", "accepted"]


def _no_nul(value: str) -> str:
    if "\x00" in value:  # PostgreSQL text cannot hold NUL
        raise ValueError("must not contain NUL characters")
    return value


class ReviewCommentCreate(BaseModel):
    item_path: str = Field(..., min_length=1, max_length=500)
    body: str | None = Field(None, min_length=1, max_length=5000)
    review_id: UUID | None = None
    kind: CommentKind = "query"

    _clean = field_validator("item_path", "body")(
        lambda v: v if v is None else _no_nul(v)
    )

    @model_validator(mode="after")
    def _body_unless_accepting(self) -> "ReviewCommentCreate":
        if self.body is None:
            if self.kind != "accepted":
                raise ValueError("body is required")
            self.body = "Accepted"
        return self


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
    kind: CommentKind
    created_at: datetime
    updated_at: datetime


class DiffItem(BaseModel):
    path: str
    change: Literal["added", "removed", "changed"]
    before: Any = None
    after: Any = None


class DiffBaseline(BaseModel):
    """The version the reviewer last saw: as of their last review decision, else the earlier submission."""

    audit_id: int
    as_of: datetime
    source: Literal["review", "previous_submission"]


class CurationDiff(BaseModel):
    """Current evidence versus the baseline; with no baseline every item is reported as added."""

    baseline: DiffBaseline | None
    items: list[DiffItem]
