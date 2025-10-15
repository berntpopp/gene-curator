"""Scoring Pydantic schemas for ClinGen SOP v11 scoring engine"""

from typing import Any

from pydantic import BaseModel, Field


class ScoringResult(BaseModel):
    """Result of scoring calculation"""

    total_score: float = Field(..., description="Total combined score")
    classification: str = Field(
        ...,
        description="Classification: definitive, strong, moderate, limited, no_known, disputed, refuted",
    )
    score_breakdown: dict[str, Any] = Field(
        ..., description="Detailed score breakdown by evidence category"
    )
    is_valid: bool = Field(..., description="Whether scoring was successful")
    validation_errors: list[str] = Field(
        default=[], description="Validation errors if any"
    )
    calculation_metadata: dict[str, Any] | None = Field(
        None, description="Additional calculation metadata"
    )


class GeneticEvidenceScore(BaseModel):
    """Genetic evidence scoring details"""

    case_level_score: float = Field(
        ..., description="Case-level evidence score (max 12)"
    )
    segregation_score: float = Field(
        ..., description="Segregation evidence score (max 7)"
    )
    case_control_score: float = Field(
        ..., description="Case-control evidence score (max 6)"
    )
    total_genetic_score: float = Field(..., description="Total genetic score (max 12)")
    case_level_items: list[dict[str, Any]] = Field(
        default=[], description="Scored case-level items"
    )
    segregation_items: list[dict[str, Any]] = Field(
        default=[], description="Scored segregation items"
    )
    case_control_items: list[dict[str, Any]] = Field(
        default=[], description="Scored case-control items"
    )


class ExperimentalEvidenceScore(BaseModel):
    """Experimental evidence scoring details"""

    expression_score: float = Field(
        ..., description="Expression evidence score (max 2)"
    )
    function_score: float = Field(..., description="Protein function score (max 2)")
    models_score: float = Field(..., description="Model systems score (max 4)")
    rescue_score: float = Field(..., description="Rescue evidence score (max 2)")
    total_experimental_score: float = Field(
        ..., description="Total experimental score (max 6)"
    )
    expression_items: list[dict[str, Any]] = Field(
        default=[], description="Scored expression items"
    )
    function_items: list[dict[str, Any]] = Field(
        default=[], description="Scored function items"
    )
    models_items: list[dict[str, Any]] = Field(
        default=[], description="Scored model items"
    )
    rescue_items: list[dict[str, Any]] = Field(
        default=[], description="Scored rescue items"
    )


class LODScoreCalculation(BaseModel):
    """LOD score calculation details"""

    family_count: int = Field(..., description="Number of families")
    lod_score: float = Field(..., description="Calculated LOD score")
    inheritance_pattern: str = Field(
        ...,
        description="Inheritance pattern: autosomal_dominant, autosomal_recessive, x_linked",
    )
    points_awarded: float = Field(..., description="Points awarded for this LOD score")
    calculation_method: str = Field(..., description="Method used for calculation")


class ClassificationThresholds(BaseModel):
    """Classification thresholds (ClinGen SOP v11)"""

    definitive: float = Field(default=12.0, description="Definitive threshold")
    strong: float = Field(default=7.0, description="Strong threshold")
    moderate: float = Field(default=2.0, description="Moderate threshold")
    limited: float = Field(default=0.1, description="Limited threshold")
    no_known: float = Field(default=0.0, description="No known threshold")
    disputed: float = Field(default=-1.0, description="Disputed threshold")
    refuted: float = Field(default=-2.0, description="Refuted threshold")
