"""Methodology bundle import (#575): schemas, workflow pairs and a scope default in one file."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.schema_repository import CurationSchemaCreate


class BundleWorkflowPair(BaseModel):
    """A workflow pair whose schemas are named, not referenced by id."""

    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=20)
    description: str | None = Field(None, max_length=500)
    precuration_schema: str = Field(..., description="Name of a bundle schema")
    curation_schema: str = Field(..., description="Name of a bundle schema")


class BundleScopeDefault(BaseModel):
    """Make one of the bundle's workflow pairs a scope's default."""

    scope_name: str = Field(..., min_length=1)
    workflow_pair: str = Field(..., description="Name of a bundle workflow pair")


class MethodologyBundle(BaseModel):
    """One methodology file: schemas, the pairs linking them, an optional scope default."""

    schemas: list[CurationSchemaCreate] = Field(..., max_length=50)
    workflow_pairs: list[BundleWorkflowPair] = Field(
        default_factory=list, max_length=50
    )
    scope_default: BundleScopeDefault | None = None


class ImportItem(BaseModel):
    """What the import did (or, on a dry run, would do) to one object."""

    kind: Literal["schema", "workflow_pair", "scope_default"]
    name: str
    version: str | None = None
    action: Literal["create", "unchanged", "new_version", "update"]
    id: UUID | None = Field(
        None, description="Empty for objects a dry run would create"
    )
    methodology_version: int | None = Field(
        None, description="Latest published methodology version of a schema"
    )


class MethodologyImportResult(BaseModel):
    """The plan and the validation report; nothing is written when errors is not empty."""

    dry_run: bool
    errors: list[str]
    items: list[ImportItem]
