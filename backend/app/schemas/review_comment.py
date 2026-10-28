"""Schemas for per-item review comments and the evidence diff."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

# One limit for a query and for the request-changes feedback built from the open queries.
REVIEW_TEXT_MAX = 2000
CommentStatus = Literal["open", "resolved"]
CommentKind = Literal["query", "accepted"]


def _no_nul(value: str) -> str:
    if "\x00" in value:  # PostgreSQL text cannot hold NUL
        raise ValueError("must not contain NUL characters")
    return value


class ReviewCommentCreate(BaseModel):
    item_path: str = Field(..., min_length=1, max_length=500)
    body: str | None = Field(None, min_length=1, max_length=REVIEW_TEXT_MAX)
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
    body: str | None = Field(None, min_length=1, max_length=REVIEW_TEXT_MAX)
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
    """The version the reviewer last saw: their own last review decision, else anyone's latest decision,
    else the earlier submission, else the active curation a re-curation replaces (no audit row)."""

    audit_id: int | None
    as_of: datetime
    source: Literal[
        "review",
        "any_review",
        "previous_submission",
        "active_curation",
        "submitted",
        "audit",
    ]
    note: str | None = Field(
        None,
        description="Set when baseline=submitted is the current evidence of a resubmitted "
        "curation: names the earlier submission to compare with",
    )


class CurationDiff(BaseModel):
    """Current evidence versus the baseline; with no baseline every item is reported as added."""

    baseline: DiffBaseline | None
    items: list[DiffItem]

    @computed_field  # type: ignore[prop-decorator]  # pydantic's documented idiom
    @property
    def changed(self) -> bool:
        """True when the evidence differs from the baseline."""
        return bool(self.items)
