"""
Pydantic schemas for schema repository operations.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator(
        "name",
        "version",
        "field_definitions",
        "validation_rules",
        "workflow_states",
        "ui_configuration",
        "is_active",
        "use_dynamic_form",
    )
    @classmethod
    def _not_null(cls, v: Any) -> Any:
        """Required response fields: omit to keep the value; explicit null is invalid."""
        if v is None:
            raise ValueError("must not be null")
        return v


class CurationSchemaInDBBase(CurationSchemaBase):
    """Base schema with database fields."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: UUID | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


class CurationSchema(CurationSchemaInDBBase):
    """Public schema for curation schemas."""

    pass


class CurationSchemaSubtree(BaseModel):
    """One evidence field of a schema (get_curation_schema with path=), no envelope."""

    schema_id: UUID
    path: str
    field: Any = Field(..., description="The field definition at path")
    validation_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Rules a field here names or that name the path",
    )
    point_ranges: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per evidence type under path: points range and category cap",
    )


class CurationSchemaSummary(BaseModel):
    """One row of the schema list; detail=true lists full schemas."""

    id: UUID
    name: str
    version: str
    schema_type: str
    institution: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class MethodologyVersion(BaseModel):
    """An immutable, numbered snapshot of a curation schema."""

    id: UUID
    schema_id: UUID
    version: int
    snapshot: dict[str, Any]
    published_at: datetime
    created_by: UUID | None
    created_at: datetime | None = None
    derived_from_version_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class MethodologyVersionImpact(BaseModel):
    """A curation whose total or class changes when re-scored with a newer version."""

    curation_id: UUID
    gene_id: UUID
    scope_id: UUID
    from_version: int
    old_total: float
    old_class: str
    new_total: float
    new_class: str


class MethodologyDerive(BaseModel):
    """Name and version of the inactive schema derived from a methodology version."""

    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=20)


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
    is_default: bool = Field(
        False, description="Used by create_scope when no workflow pair is given"
    )

    model_config = ConfigDict(
        from_attributes=True,
    )


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
