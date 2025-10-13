"""
Pydantic schemas for schema repository operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Schema Repository Base Schemas
class CurationSchemaBase(BaseModel):
    """Base schema for curation schemas."""

    name: str = Field(..., min_length=1, max_length=100, description="Schema name")
    version: str = Field(..., min_length=1, max_length=20, description="Schema version")
    schema_type: str = Field(..., description="Type of schema (precuration, curation)")
    institution: str | None = Field(
        None, max_length=100, description="Institution name"
    )
    description: str | None = Field(
        None, max_length=500, description="Schema description"
    )
    schema_data: dict[str, Any] = Field(..., description="JSON schema definition")
    is_active: bool = Field(True, description="Whether schema is active")


class CurationSchemaCreate(CurationSchemaBase):
    """Schema for creating a new curation schema."""

    pass


class CurationSchemaUpdate(BaseModel):
    """Schema for updating a curation schema."""

    name: str | None = Field(None, min_length=1, max_length=100)
    version: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = Field(None, max_length=500)
    schema_data: dict[str, Any] | None = None
    is_active: bool | None = None


class CurationSchemaInDBBase(CurationSchemaBase):
    """Base schema with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


class CurationSchema(CurationSchemaInDBBase):
    """Public schema for curation schemas."""

    pass


class CurationSchemaWithUsage(CurationSchema):
    """Schema with usage statistics."""

    workflow_pairs_count: int = Field(
        default=0, description="Number of workflow pairs using this schema"
    )
    active_curations_count: int = Field(
        default=0, description="Number of active curations using this schema"
    )
    last_used: datetime | None = Field(None, description="Last time schema was used")


# Workflow Pair Schemas
class WorkflowPairBase(BaseModel):
    """Base schema for workflow pairs."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Workflow pair name"
    )
    version: str = Field(..., min_length=1, max_length=20, description="Version")
    description: str | None = Field(None, max_length=500, description="Description")
    precuration_schema_id: UUID = Field(..., description="Precuration schema ID")
    curation_schema_id: UUID = Field(..., description="Curation schema ID")
    is_active: bool = Field(True, description="Whether workflow pair is active")


class WorkflowPairCreate(WorkflowPairBase):
    """Schema for creating a workflow pair."""

    pass


class WorkflowPairUpdate(BaseModel):
    """Schema for updating a workflow pair."""

    name: str | None = Field(None, min_length=1, max_length=100)
    version: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = Field(None, max_length=500)
    precuration_schema_id: UUID | None = None
    curation_schema_id: UUID | None = None
    is_active: bool | None = None


class WorkflowPairInDBBase(WorkflowPairBase):
    """Base schema with database fields."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


class WorkflowPair(WorkflowPairInDBBase):
    """Public schema for workflow pairs."""

    pass


class WorkflowPairWithSchemas(WorkflowPair):
    """Workflow pair with schema details."""

    precuration_schema_name: str | None = Field(
        None, description="Precuration schema name"
    )
    curation_schema_name: str | None = Field(None, description="Curation schema name")
    precuration_schema_type: str | None = Field(
        None, description="Precuration schema type"
    )
    curation_schema_type: str | None = Field(None, description="Curation schema type")


# Schema Validation Result
class SchemaValidationResult(BaseModel):
    """Result of schema validation."""

    is_valid: bool = Field(..., description="Whether schema is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    field_count: int = Field(default=0, description="Number of fields in schema")
    has_scoring: bool = Field(
        default=False, description="Whether schema has scoring configuration"
    )
    has_validation: bool = Field(
        default=False, description="Whether schema has validation rules"
    )


# Schema Statistics
class SchemaRepositoryStatistics(BaseModel):
    """Statistics for the schema repository."""

    total_schemas: int = Field(..., description="Total number of schemas")
    active_schemas: int = Field(..., description="Number of active schemas")
    total_workflow_pairs: int = Field(..., description="Total workflow pairs")
    active_workflow_pairs: int = Field(..., description="Active workflow pairs")
    schema_types: dict[str, int] = Field(
        default_factory=dict, description="Count by schema type"
    )
    institutions: list[str] = Field(
        default_factory=list, description="List of institutions"
    )
    recent_activity: list[dict[str, Any]] = Field(
        default_factory=list, description="Recent schema activity"
    )


# Schema Search and Filtering
class SchemaSearchQuery(BaseModel):
    """Schema search parameters."""

    query: str | None = Field(None, description="Search term")
    schema_type: str | None = Field(None, description="Filter by schema type")
    institution: str | None = Field(None, description="Filter by institution")
    is_active: bool | None = Field(None, description="Filter by active status")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(50, ge=1, le=200, description="Maximum number of records")
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class SchemaListResponse(BaseModel):
    """Response for paginated schema lists."""

    schemas: list[CurationSchema]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


class WorkflowPairListResponse(BaseModel):
    """Response for paginated workflow pair lists."""

    workflow_pairs: list[WorkflowPairWithSchemas]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool


# Schema Import/Export
class SchemaImportRequest(BaseModel):
    """Request for schema import."""

    schemas: list[CurationSchemaCreate] = Field(..., min_length=1, max_length=20)
    overwrite_existing: bool = Field(
        False, description="Whether to overwrite existing schemas"
    )


class SchemaImportResponse(BaseModel):
    """Response for schema import."""

    imported_schemas: list[CurationSchema]
    skipped_schemas: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    total_processed: int
    total_imported: int
    total_skipped: int
    total_errors: int


class SchemaExportResponse(BaseModel):
    """Response for schema export."""

    schemas: list[CurationSchema]
    workflow_pairs: list[WorkflowPair]
    export_metadata: dict[str, Any]
    exported_at: datetime


# Schema Templates
class SchemaTemplate(BaseModel):
    """Predefined schema template."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    schema_type: str = Field(..., description="Schema type")
    template_data: dict[str, Any] = Field(..., description="Template schema definition")
    example_data: dict[str, Any] | None = Field(
        None, description="Example evidence data"
    )


class SchemaTemplateListResponse(BaseModel):
    """Response for available schema templates."""

    templates: list[SchemaTemplate]
    categories: list[str]
    total_templates: int
