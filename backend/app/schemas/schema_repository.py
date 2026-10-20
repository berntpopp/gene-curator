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
    # Schema definition fields (matching database model)
    field_definitions: dict[str, Any] = Field(
        ..., description="Field definitions for the schema"
    )
    validation_rules: dict[str, Any] = Field(
        default_factory=dict, description="Validation rules"
    )
    workflow_states: dict[str, Any] = Field(
        ..., description="Workflow state definitions"
    )
    ui_configuration: dict[str, Any] = Field(
        ..., description="UI configuration for form rendering"
    )
    scoring_configuration: dict[str, Any] | None = Field(
        None, description="Scoring configuration for evidence scoring"
    )
    schema_hash: str | None = Field(None, description="Schema validation checksum")
    is_active: bool = Field(True, description="Whether schema is active")
    use_dynamic_form: bool = Field(
        False, description="When true, use DynamicForm instead of legacy form"
    )


class CurationSchemaCreate(CurationSchemaBase):
    """Schema for creating a new curation schema."""

    pass


class CurationSchemaUpdate(BaseModel):
    """Schema for updating a curation schema."""

    name: str | None = Field(None, min_length=1, max_length=100)
    version: str | None = Field(None, min_length=1, max_length=20)
    description: str | None = Field(None, max_length=500)
    field_definitions: dict[str, Any] | None = None
    validation_rules: dict[str, Any] | None = None
    workflow_states: dict[str, Any] | None = None
    ui_configuration: dict[str, Any] | None = None
    scoring_configuration: dict[str, Any] | None = None
    is_active: bool | None = None
    use_dynamic_form: bool | None = None


class CurationSchemaInDBBase(CurationSchemaBase):
    """Base schema with database fields."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: UUID | None = None

    class Config:
        from_attributes = True


class CurationSchema(CurationSchemaInDBBase):
    """Public schema for curation schemas."""

    pass


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
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: UUID | None = None

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


# Schema Search and Filtering


# Schema Import/Export


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
