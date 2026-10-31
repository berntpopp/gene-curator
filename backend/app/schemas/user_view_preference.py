"""Saved views of the signed-in user (#276)."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.gene_catalogue_matrix import MAX_MATRIX_SCOPES


class CatalogueView(BaseModel):
    """The catalogue's shown scope columns, in display order; empty means the defaults."""

    scope_ids: list[UUID] = Field(default_factory=list, max_length=MAX_MATRIX_SCOPES)
