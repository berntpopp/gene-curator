"""
Schema validation API endpoints.
Provides validation services for evidence data and schema definitions.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import deps
from app.core.schema_validator import schema_validator
from app.crud.schema_repository import schema_crud
from app.models import UserNew

router = APIRouter()


# Request/Response Models
class ValidationRequest(BaseModel):
    """Request for evidence data validation."""

    evidence_data: dict[str, Any]
    schema_id: UUID | None = None
    schema_definition: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class ValidationResponse(BaseModel):
    """Response for validation request."""

    is_valid: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    field_validations: dict[str, dict[str, Any]]
    business_rule_violations: list[dict[str, Any]]
    score_calculations: dict[str, float]
    completeness_score: float
    required_fields_missing: list[str]
    suggested_improvements: list[str]


class SchemaValidationRequest(BaseModel):
    """Request for schema definition validation."""

    schema_definition: dict[str, Any]


class JSONSchemaResponse(BaseModel):
    """Response containing generated JSON Schema."""

    json_schema: dict[str, Any]
    field_count: int
    validation_rules_count: int


# ========================================
# VALIDATION ENDPOINTS
# ========================================


@router.post("/validate-evidence", response_model=ValidationResponse)
def validate_evidence_data(
    *,
    db: Session = Depends(deps.get_db),
    validation_request: ValidationRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ValidationResponse:
    """
    Validate evidence data against a schema definition.
    """
    if current_user.role not in ["admin", "scope_admin", "curator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Get schema definition
    schema_definition = validation_request.schema_definition

    if not schema_definition and validation_request.schema_id:
        schema = schema_crud.get(db, id=validation_request.schema_id)
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        schema_definition = schema.schema_data

    if not schema_definition:
        raise HTTPException(
            status_code=400,
            detail="Either schema_id or schema_definition must be provided",
        )

    # Validate evidence data
    try:
        result = schema_validator.validate_evidence_data(
            validation_request.evidence_data,
            schema_definition,
            validation_request.context,
        )

        return ValidationResponse(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
            field_validations=result.field_validations,
            business_rule_violations=result.business_rule_violations,
            score_calculations=result.score_calculations,
            completeness_score=result.completeness_score,
            required_fields_missing=result.required_fields_missing,
            suggested_improvements=result.suggested_improvements,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {e!s}") from e


@router.post("/validate-schema", response_model=ValidationResponse)
def validate_schema_definition(
    *,
    db: Session = Depends(deps.get_db),
    schema_request: SchemaValidationRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> ValidationResponse:
    """
    Validate a schema definition for correctness and completeness.
    """
    if current_user.role not in ["admin", "scope_admin", "curator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        result = schema_validator.validate_schema_definition(
            schema_request.schema_definition
        )

        return ValidationResponse(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
            field_validations=result.field_validations,
            business_rule_violations=result.business_rule_violations,
            score_calculations=result.score_calculations,
            completeness_score=result.completeness_score,
            required_fields_missing=result.required_fields_missing,
            suggested_improvements=result.suggested_improvements,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Schema validation error: {e!s}"
        ) from e


@router.post("/generate-json-schema", response_model=JSONSchemaResponse)
def generate_json_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_request: SchemaValidationRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> JSONSchemaResponse:
    """
    Generate JSON Schema from a curation schema definition.
    """
    if current_user.role not in ["admin", "scope_admin", "curator", "viewer"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        json_schema = schema_validator.generate_json_schema(
            schema_request.schema_definition
        )

        field_count = len(schema_request.schema_definition.get("field_definitions", {}))
        validation_rules_count = len(
            schema_request.schema_definition.get("validation_rules", {})
        )

        return JSONSchemaResponse(
            json_schema=json_schema,
            field_count=field_count,
            validation_rules_count=validation_rules_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"JSON Schema generation error: {e!s}"
        ) from e


@router.get("/schema/{schema_id}/json-schema", response_model=JSONSchemaResponse)
def get_json_schema_for_schema(
    *,
    db: Session = Depends(deps.get_db),
    schema_id: UUID,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> JSONSchemaResponse:
    """
    Get JSON Schema for an existing curation schema.
    """
    if current_user.role not in ["admin", "scope_admin", "curator", "viewer"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    schema = schema_crud.get(db, id=schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    try:
        json_schema = schema_validator.generate_json_schema(schema.schema_data)

        field_count = len(schema.schema_data.get("field_definitions", {}))
        validation_rules_count = len(schema.schema_data.get("validation_rules", {}))

        return JSONSchemaResponse(
            json_schema=json_schema,
            field_count=field_count,
            validation_rules_count=validation_rules_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"JSON Schema generation error: {e!s}"
        ) from e


# ========================================
# FIELD VALIDATION ENDPOINTS
# ========================================


class FieldValidationRequest(BaseModel):
    """Request for individual field validation."""

    field_name: str
    field_value: Any
    field_config: dict[str, Any]


class FieldValidationResponse(BaseModel):
    """Response for field validation."""

    field_name: str
    is_valid: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    suggestions: list[str]


@router.post("/validate-field", response_model=FieldValidationResponse)
def validate_single_field(
    *,
    db: Session = Depends(deps.get_db),
    field_request: FieldValidationRequest,
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> FieldValidationResponse:
    """
    Validate a single field value against its configuration.
    """
    if current_user.role not in ["admin", "scope_admin", "curator"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # Create a minimal schema for field validation
        schema_definition = {
            "field_definitions": {field_request.field_name: field_request.field_config}
        }

        evidence_data = {field_request.field_name: field_request.field_value}

        result = schema_validator.validate_evidence_data(
            evidence_data, schema_definition
        )

        field_errors = result.field_validations.get(field_request.field_name, {}).get(
            "errors", []
        )
        field_warnings = result.field_validations.get(field_request.field_name, {}).get(
            "warnings", []
        )

        return FieldValidationResponse(
            field_name=field_request.field_name,
            is_valid=len(field_errors) == 0,
            errors=field_errors,
            warnings=field_warnings,
            suggestions=result.suggested_improvements,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Field validation error: {e!s}"
        ) from e


# ========================================
# VALIDATION UTILITIES ENDPOINTS
# ========================================


@router.get("/supported-field-types")
def get_supported_field_types(
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, Any]:
    """
    Get list of supported field types and their configurations.
    """
    if current_user.role not in ["admin", "scope_admin", "curator", "viewer"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    field_types = {
        "text": {
            "description": "Text input field",
            "supported_config": ["min_length", "max_length", "pattern", "required"],
            "example": {
                "type": "text",
                "label": "Gene Description",
                "min_length": 10,
                "max_length": 500,
                "required": True,
            },
        },
        "number": {
            "description": "Numeric input field",
            "supported_config": [
                "min_value",
                "max_value",
                "decimal_places",
                "required",
            ],
            "example": {
                "type": "number",
                "label": "Evidence Score",
                "min_value": 0,
                "max_value": 12,
                "decimal_places": 2,
                "required": True,
            },
        },
        "boolean": {
            "description": "Boolean (true/false) field",
            "supported_config": ["required"],
            "example": {
                "type": "boolean",
                "label": "Has Contradictory Evidence",
                "required": False,
            },
        },
        "array": {
            "description": "Array of values",
            "supported_config": ["min_items", "max_items", "items", "required"],
            "example": {
                "type": "array",
                "label": "Publication IDs",
                "min_items": 1,
                "items": {"type": "pmid"},
                "required": True,
            },
        },
        "object": {
            "description": "Nested object with properties",
            "supported_config": ["properties", "required"],
            "example": {
                "type": "object",
                "label": "Case Information",
                "properties": {
                    "count": {"type": "number", "min_value": 0},
                    "description": {"type": "text", "max_length": 200},
                },
                "required": True,
            },
        },
        "date": {
            "description": "Date field (ISO format)",
            "supported_config": ["min_date", "max_date", "required"],
            "example": {
                "type": "date",
                "label": "Publication Date",
                "min_date": "2000-01-01",
                "required": False,
            },
        },
        "select": {
            "description": "Single selection from options",
            "supported_config": ["options", "required"],
            "example": {
                "type": "select",
                "label": "Classification",
                "options": [
                    {"value": "definitive", "label": "Definitive"},
                    {"value": "strong", "label": "Strong"},
                ],
                "required": True,
            },
        },
        "multiselect": {
            "description": "Multiple selection from options",
            "supported_config": ["options", "required"],
            "example": {
                "type": "multiselect",
                "label": "Evidence Types",
                "options": [
                    {"value": "case_level", "label": "Case Level"},
                    {"value": "segregation", "label": "Segregation"},
                ],
                "required": False,
            },
        },
        "email": {
            "description": "Email address field",
            "supported_config": ["required"],
            "example": {"type": "email", "label": "Contact Email", "required": False},
        },
        "url": {
            "description": "URL field",
            "supported_config": ["required"],
            "example": {"type": "url", "label": "Reference URL", "required": False},
        },
        "pmid": {
            "description": "PubMed ID field",
            "supported_config": ["required"],
            "example": {"type": "pmid", "label": "PubMed ID", "required": True},
        },
        "hgnc_id": {
            "description": "HGNC Gene ID field",
            "supported_config": ["required"],
            "example": {"type": "hgnc_id", "label": "Gene ID", "required": True},
        },
        "score": {
            "description": "Score field with additional validation",
            "supported_config": [
                "min_value",
                "max_value",
                "decimal_places",
                "required",
            ],
            "example": {
                "type": "score",
                "label": "Genetic Evidence Score",
                "min_value": 0,
                "max_value": 12,
                "decimal_places": 2,
                "required": True,
            },
        },
    }

    return {"field_types": field_types, "total_supported_types": len(field_types)}


@router.get("/business-rules")
def get_supported_business_rules(
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, Any]:
    """
    Get list of supported business rules and their descriptions.
    """
    if current_user.role not in ["admin", "scope_admin", "curator", "viewer"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    business_rules = {
        "clingen_genetic_evidence": {
            "description": "ClinGen SOP v11 genetic evidence validation",
            "validates": [
                "Maximum genetic evidence score of 12 points",
                "Case-level and segregation data mutual exclusivity warnings",
                "Score calculation consistency",
            ],
        },
        "clingen_experimental_evidence": {
            "description": "ClinGen SOP v11 experimental evidence validation",
            "validates": [
                "Maximum experimental evidence score of 6 points",
                "Functional, model system, and rescue evidence scoring",
            ],
        },
        "clingen_contradictory_evidence": {
            "description": "ClinGen contradictory evidence validation",
            "validates": [
                "Required description when contradictory evidence is present",
                "Impact on final classification",
            ],
        },
        "gencc_classification": {
            "description": "GenCC classification validation",
            "validates": [
                "Valid GenCC classification terms",
                "Confidence level consistency",
            ],
        },
        "institutional_review": {
            "description": "Institution-specific review requirements",
            "validates": [
                "Custom institutional requirements",
                "Local policy compliance",
            ],
        },
    }

    return {"business_rules": business_rules, "total_rules": len(business_rules)}


# ========================================
# VALIDATION TESTING ENDPOINTS
# ========================================


@router.post("/test-validation")
def test_validation_with_examples(
    *,
    db: Session = Depends(deps.get_db),
    current_user: UserNew = Depends(deps.get_current_active_user),
) -> dict[str, Any]:
    """
    Test validation system with example data.
    """
    if current_user.role not in ["admin", "scope_admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Example schema definition
    test_schema = {
        "field_definitions": {
            "gene_symbol": {
                "type": "text",
                "label": "Gene Symbol",
                "min_length": 1,
                "max_length": 50,
                "required": True,
            },
            "genetic_evidence_score": {
                "type": "score",
                "label": "Genetic Evidence Score",
                "min_value": 0,
                "max_value": 12,
                "decimal_places": 2,
                "required": True,
            },
            "experimental_evidence_score": {
                "type": "score",
                "label": "Experimental Evidence Score",
                "min_value": 0,
                "max_value": 6,
                "decimal_places": 2,
                "required": False,
            },
            "classification": {
                "type": "select",
                "label": "Classification",
                "options": [
                    {"value": "definitive", "label": "Definitive"},
                    {"value": "strong", "label": "Strong"},
                    {"value": "moderate", "label": "Moderate"},
                ],
                "required": True,
            },
        },
        "validation_rules": {
            "total_score_check": {
                "type": "condition",
                "condition": "genetic_evidence_score + experimental_evidence_score <= 18",
                "message": "Total evidence score should not exceed 18 points",
            }
        },
        "business_rules": ["clingen_genetic_evidence", "clingen_experimental_evidence"],
        "scoring_configuration": {"engine": "clingen"},
    }

    # Test cases
    test_cases = [
        {
            "name": "Valid Complete Data",
            "data": {
                "gene_symbol": "BRCA1",
                "genetic_evidence_score": 8.0,
                "experimental_evidence_score": 4.0,
                "classification": "definitive",
            },
        },
        {
            "name": "Missing Required Field",
            "data": {"genetic_evidence_score": 10.0, "classification": "strong"},
        },
        {
            "name": "Invalid Score Range",
            "data": {
                "gene_symbol": "BRCA2",
                "genetic_evidence_score": 15.0,  # Exceeds maximum
                "classification": "definitive",
            },
        },
        {
            "name": "Invalid Classification",
            "data": {
                "gene_symbol": "TP53",
                "genetic_evidence_score": 6.0,
                "classification": "invalid_option",
            },
        },
    ]

    results = {}

    for test_case in test_cases:
        try:
            result = schema_validator.validate_evidence_data(
                test_case["data"], test_schema
            )

            results[test_case["name"]] = {
                "is_valid": result.is_valid,
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "completeness_score": result.completeness_score,
                "score_calculations": result.score_calculations,
            }
        except Exception as e:
            results[test_case["name"]] = {"error": str(e)}

    return {
        "test_schema": test_schema,
        "test_results": results,
        "validation_system_status": "operational",
    }
