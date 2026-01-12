# Scoring Engine Development Guide

This guide explains how to create pluggable scoring engines for Gene Curator's schema-agnostic architecture. Scoring engines calculate verdicts/classifications from evidence data according to specific methodological rules.

## Architecture Overview

### Core Components

```
ScoringEngine (ABC) → Base interface for all scoring engines
├── ClinGenEngine → ClinGen SOP v11 implementation  
├── GenCCEngine → GenCC-based gene-disease validity classification
├── QualitativeEngine → Institution-specific qualitative assessment
└── CustomEngine → User-defined scoring logic
```

### Engine Registry

```python
# Engines are registered at startup and selected by schema configuration
SCORING_ENGINES = {
    "clingen_sop_v11": ClinGenEngine(),
    "gencc_based": GenCCEngine(),
    "qualitative_assessment": QualitativeEngine(),
    "custom_institutional": CustomEngine()
}
```

## Base Engine Interface

### ScoringEngine Abstract Base Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ScoringResult(BaseModel):
    """Result of scoring calculation."""
    scores: Dict[str, float]  # e.g., {"genetic_score": 8.5, "experimental_score": 3.0}
    total_score: float        # Combined total score
    verdict: str             # Final classification
    verdict_rationale: str   # Explanation of verdict determination
    evidence_breakdown: Dict[str, Any]  # Detailed scoring breakdown
    warnings: List[str] = [] # Any scoring warnings or issues
    metadata: Dict[str, Any] = {}  # Additional scoring metadata

class ScoringEngine(ABC):
    """Base class for all scoring engines."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Engine identifier (matches schema configuration)."""
        pass
    
    @property  
    @abstractmethod
    def version(self) -> str:
        """Engine version for compatibility tracking."""
        pass
    
    @abstractmethod
    def calculate_scores(self, 
                        evidence_data: Dict[str, Any], 
                        schema_config: Dict[str, Any]) -> ScoringResult:
        """Calculate scores and verdict from evidence data."""
        pass
    
    @abstractmethod
    def validate_evidence(self, 
                         evidence_data: Dict[str, Any], 
                         schema_config: Dict[str, Any]) -> List[str]:
        """Validate evidence data. Returns list of validation errors."""
        pass
    
    def supports_schema(self, schema_name: str, schema_version: str) -> bool:
        """Check if engine supports a specific schema version."""
        return True  # Override for version-specific support
```

## ClinGen SOP v11 Engine Implementation

### Complete Implementation Example

```python
from typing import Dict, Any, List
import math

class ClinGenEngine(ScoringEngine):
    """ClinGen Standard Operating Procedure v11 scoring engine."""
    
    @property
    def name(self) -> str:
        return "clingen_sop_v11"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def calculate_scores(self, evidence_data: Dict[str, Any], schema_config: Dict[str, Any]) -> ScoringResult:
        """Calculate ClinGen SOP v11 scores."""
        
        # Extract evidence categories
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})
        contradictory_evidence = evidence_data.get("contradictory_evidence", [])
        
        # Calculate genetic evidence score
        genetic_score = self._calculate_genetic_score(genetic_evidence)
        
        # Calculate experimental evidence score
        experimental_score = self._calculate_experimental_score(experimental_evidence)
        
        # Total score (max 18 per SOP v11)
        total_score = min(genetic_score + experimental_score, 18.0)
        
        # Determine verdict
        verdict = self._determine_verdict(total_score, contradictory_evidence)
        
        # Generate rationale
        rationale = self._generate_rationale(genetic_score, experimental_score, total_score, verdict)
        
        # Create detailed breakdown
        breakdown = self._create_breakdown(genetic_evidence, experimental_evidence, genetic_score, experimental_score)
        
        return ScoringResult(
            scores={
                "genetic_evidence_score": genetic_score,
                "experimental_evidence_score": experimental_score,
                "total_score": total_score
            },
            total_score=total_score,
            verdict=verdict,
            verdict_rationale=rationale,
            evidence_breakdown=breakdown,
            warnings=self._check_warnings(evidence_data),
            metadata={
                "sop_version": "v11",
                "engine_version": self.version,
                "calculated_at": "2024-01-15T10:30:00Z"
            }
        )
    
    def _calculate_genetic_score(self, genetic_evidence: Dict[str, Any]) -> float:
        """Calculate genetic evidence score per SOP v11."""
        
        total_score = 0.0
        
        # Case-level data (max 12 points)
        case_level_data = genetic_evidence.get("case_level_data", [])
        case_level_score = 0.0
        
        for case in case_level_data:
            points = float(case.get("points", 0))
            case_level_score += points
        
        case_level_score = min(case_level_score, 12.0)
        
        # Segregation data (max 3 points)
        segregation_data = genetic_evidence.get("segregation_data", [])
        segregation_score = 0.0
        
        for seg in segregation_data:
            points = float(seg.get("points", 0))
            segregation_score += points
            
        segregation_score = min(segregation_score, 3.0)
        
        # Case-control data (max 6 points)
        case_control_data = genetic_evidence.get("case_control_data", [])
        case_control_score = 0.0
        
        for cc in case_control_data:
            points = float(cc.get("points", 0))
            case_control_score += points
            
        case_control_score = min(case_control_score, 6.0)
        
        # Total genetic score (overall max 12 per SOP v11)
        total_genetic = case_level_score + segregation_score + case_control_score
        return min(total_genetic, 12.0)
    
    def _calculate_experimental_score(self, experimental_evidence: Dict[str, Any]) -> float:
        """Calculate experimental evidence score per SOP v11."""
        
        total_score = 0.0
        
        # Function evidence (max 2 points)
        function_evidence = experimental_evidence.get("function", [])
        function_score = sum(float(item.get("points", 0)) for item in function_evidence)
        function_score = min(function_score, 2.0)
        
        # Model systems evidence (max 4 points)
        model_evidence = experimental_evidence.get("models", [])
        model_score = sum(float(item.get("points", 0)) for item in model_evidence)
        model_score = min(model_score, 4.0)
        
        # Rescue evidence (max 2 points)
        rescue_evidence = experimental_evidence.get("rescue", [])
        rescue_score = sum(float(item.get("points", 0)) for item in rescue_evidence)
        rescue_score = min(rescue_score, 2.0)
        
        # Total experimental score (overall max 6 per SOP v11)
        total_experimental = function_score + model_score + rescue_score
        return min(total_experimental, 6.0)
    
    def _determine_verdict(self, total_score: float, contradictory_evidence: List[Dict]) -> str:
        """Determine ClinGen verdict based on total score and contradictory evidence."""
        
        has_contradictory = len(contradictory_evidence) > 0
        
        if has_contradictory:
            return "Disputed"
        elif total_score >= 12:
            return "Definitive"
        elif total_score >= 7:
            return "Strong"
        elif total_score >= 4:
            return "Moderate"
        elif total_score >= 1:
            return "Limited"
        else:
            return "No Known Disease Relationship"
    
    def _generate_rationale(self, genetic_score: float, experimental_score: float, 
                          total_score: float, verdict: str) -> str:
        """Generate human-readable rationale for verdict."""
        
        rationale = f"Based on ClinGen SOP v11 scoring: "
        rationale += f"genetic evidence score = {genetic_score:.1f}, "
        rationale += f"experimental evidence score = {experimental_score:.1f}, "
        rationale += f"total score = {total_score:.1f}. "
        
        if verdict == "Definitive":
            rationale += "Total score ≥12 with no contradictory evidence supports Definitive classification."
        elif verdict == "Strong":
            rationale += "Total score 7-11 with no contradictory evidence supports Strong classification."
        elif verdict == "Moderate":
            rationale += "Total score 4-6 supports Moderate classification."
        elif verdict == "Limited":
            rationale += "Total score 1-3 supports Limited classification."
        elif verdict == "Disputed":
            rationale += "Contradictory evidence present, resulting in Disputed classification."
        else:
            rationale += "No evidence supporting gene-disease relationship."
        
        return rationale
    
    def _create_breakdown(self, genetic_evidence: Dict, experimental_evidence: Dict,
                         genetic_score: float, experimental_score: float) -> Dict[str, Any]:
        """Create detailed scoring breakdown."""
        
        return {
            "genetic_evidence": {
                "total_score": genetic_score,
                "case_level_items": len(genetic_evidence.get("case_level_data", [])),
                "segregation_items": len(genetic_evidence.get("segregation_data", [])),
                "case_control_items": len(genetic_evidence.get("case_control_data", []))
            },
            "experimental_evidence": {
                "total_score": experimental_score,
                "function_items": len(experimental_evidence.get("function", [])),
                "model_items": len(experimental_evidence.get("models", [])),
                "rescue_items": len(experimental_evidence.get("rescue", []))
            }
        }
    
    def _check_warnings(self, evidence_data: Dict[str, Any]) -> List[str]:
        """Check for potential issues or warnings."""
        
        warnings = []
        
        # Check for missing evidence categories
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})
        
        if not genetic_evidence:
            warnings.append("No genetic evidence provided")
        if not experimental_evidence:
            warnings.append("No experimental evidence provided")
        
        # Check for low evidence counts
        case_level_count = len(genetic_evidence.get("case_level_data", []))
        if case_level_count < 2:
            warnings.append(f"Only {case_level_count} case-level evidence items (consider adding more)")
        
        return warnings
    
    def validate_evidence(self, evidence_data: Dict[str, Any], schema_config: Dict[str, Any]) -> List[str]:
        """Validate evidence data for ClinGen compliance."""
        
        errors = []
        
        # Validate genetic evidence
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        case_level_data = genetic_evidence.get("case_level_data", [])
        
        for i, case in enumerate(case_level_data):
            # Validate PMID
            pmid = case.get("pmid", "")
            if not pmid or not pmid.isdigit() or len(pmid) < 7:
                errors.append(f"Case-level item {i+1}: Invalid PMID format")
            
            # Validate points
            points = case.get("points", 0)
            if not isinstance(points, (int, float)) or points < 0 or points > 2:
                errors.append(f"Case-level item {i+1}: Points must be 0-2")
            
            # Validate required fields
            if not case.get("proband_label"):
                errors.append(f"Case-level item {i+1}: Proband label required")
        
        return errors
```

## GenCC-Based Engine Implementation  

### GenCC Gene-Disease Validity Classification Engine

```python
class GenCCEngine(ScoringEngine):
    """GenCC-based gene-disease validity classification scoring engine."""
    
    @property
    def name(self) -> str:
        return "gencc_based"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def calculate_scores(self, evidence_data: Dict[str, Any], schema_config: Dict[str, Any]) -> ScoringResult:
        """Calculate GenCC-based classification."""
        
        genetic_evidence = evidence_data.get("genetic_evidence", {})
        experimental_evidence = evidence_data.get("experimental_evidence", {})
        contradictory_evidence = evidence_data.get("contradictory_evidence", [])
        
        # Calculate evidence scores using GenCC-adapted methodology
        genetic_score = self._calculate_genetic_score(genetic_evidence)
        experimental_score = self._calculate_experimental_score(experimental_evidence)
        
        # Total score
        total_score = genetic_score + experimental_score
        
        # Determine classification
        classification = self._determine_gencc_classification(total_score, contradictory_evidence)
        
        # Generate rationale
        rationale = self._generate_gencc_rationale(genetic_score, experimental_score, total_score, classification)
        
        return ScoringResult(
            scores={
                "genetic_evidence_score": genetic_score,
                "experimental_evidence_score": experimental_score,
                "total_score": total_score
            },
            total_score=total_score,
            verdict=classification,
            verdict_rationale=rationale,
            evidence_breakdown=self._create_gencc_breakdown(genetic_evidence, experimental_evidence),
            metadata={"guidelines": "GenCC_Based", "engine_version": self.version}
        )
    
    def _calculate_genetic_score(self, genetic_evidence: Dict[str, Any]) -> float:
        """Calculate genetic evidence score using GenCC-adapted methodology."""
        
        # Similar to ClinGen but adapted for GenCC framework
        case_level_data = genetic_evidence.get("case_level_data", [])
        segregation_data = genetic_evidence.get("segregation_data", [])
        case_control_data = genetic_evidence.get("case_control_data", [])
        
        # Calculate scores with GenCC-specific maximums
        case_level_score = min(sum(float(item.get("points", 0)) for item in case_level_data), 12.0)
        segregation_score = min(sum(float(item.get("points", 0)) for item in segregation_data), 3.0)
        case_control_score = min(sum(float(item.get("points", 0)) for item in case_control_data), 6.0)
        
        return min(case_level_score + segregation_score + case_control_score, 12.0)
    
    def _calculate_experimental_score(self, experimental_evidence: Dict[str, Any]) -> float:
        """Calculate experimental evidence score using GenCC-adapted methodology."""
        
        function_evidence = experimental_evidence.get("function", [])
        model_evidence = experimental_evidence.get("models", [])
        rescue_evidence = experimental_evidence.get("rescue", [])
        
        function_score = min(sum(float(item.get("points", 0)) for item in function_evidence), 2.0)
        model_score = min(sum(float(item.get("points", 0)) for item in model_evidence), 4.0)
        rescue_score = min(sum(float(item.get("points", 0)) for item in rescue_evidence), 2.0)
        
        return min(function_score + model_score + rescue_score, 6.0)
    
    def _determine_gencc_classification(self, total_score: float, contradictory_evidence: List[Dict]) -> str:
        """Determine GenCC classification based on total score."""
        
        has_contradictory = len(contradictory_evidence) > 0
        
        if has_contradictory:
            return "Disputed"
        elif total_score >= 12:
            return "Definitive"
        elif total_score >= 7:
            return "Strong"
        elif total_score >= 4:
            return "Moderate"
        elif total_score >= 1:
            return "Limited"
        else:
            return "No Known Disease Relationship"
    
    def _generate_gencc_rationale(self, genetic_score: float, experimental_score: float, 
                                 total_score: float, classification: str) -> str:
        """Generate GenCC classification rationale."""
        
        rationale = f"GenCC-based classification: "
        rationale += f"genetic evidence = {genetic_score:.1f}, "
        rationale += f"experimental evidence = {experimental_score:.1f}, "
        rationale += f"total score = {total_score:.1f}. "
        
        if classification == "Definitive":
            rationale += "Total score ≥12 supports Definitive gene-disease validity."
        elif classification == "Strong":
            rationale += "Total score 7-11 supports Strong gene-disease validity."
        elif classification == "Moderate":
            rationale += "Total score 4-6 supports Moderate gene-disease validity."
        elif classification == "Limited":
            rationale += "Total score 1-3 supports Limited gene-disease validity."
        elif classification == "Disputed":
            rationale += "Contradictory evidence present, resulting in Disputed classification."
        else:
            rationale += "No evidence supporting gene-disease relationship."
        
        return rationale
    
    def _create_gencc_breakdown(self, genetic_evidence: Dict, experimental_evidence: Dict) -> Dict[str, Any]:
        """Create detailed GenCC evidence breakdown."""
        
        return {
            "genetic_evidence": {
                "case_level_items": len(genetic_evidence.get("case_level_data", [])),
                "segregation_items": len(genetic_evidence.get("segregation_data", [])),
                "case_control_items": len(genetic_evidence.get("case_control_data", []))
            },
            "experimental_evidence": {
                "function_items": len(experimental_evidence.get("function", [])),
                "model_items": len(experimental_evidence.get("models", [])),
                "rescue_items": len(experimental_evidence.get("rescue", []))
            }
        }
```

## Custom Qualitative Engine

### Institution-Specific Assessment

```python
class QualitativeEngine(ScoringEngine):
    """Qualitative assessment engine for institutional use."""
    
    @property
    def name(self) -> str:
        return "qualitative_assessment"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def calculate_scores(self, evidence_data: Dict[str, Any], schema_config: Dict[str, Any]) -> ScoringResult:
        """Calculate qualitative assessment."""
        
        clinical_assessment = evidence_data.get("clinical_assessment", {})
        literature_review = evidence_data.get("literature_review", {})
        
        # Qualitative scoring based on categorical assessments
        clinical_score = self._assess_clinical_evidence(clinical_assessment)
        literature_score = self._assess_literature_evidence(literature_review)
        
        # Combine assessments
        overall_assessment = self._combine_assessments(clinical_score, literature_score)
        
        return ScoringResult(
            scores={
                "clinical_assessment_score": clinical_score,
                "literature_review_score": literature_score,
                "overall_score": overall_assessment["score"]
            },
            total_score=overall_assessment["score"],
            verdict=overall_assessment["verdict"],
            verdict_rationale=overall_assessment["rationale"],
            evidence_breakdown={
                "clinical_assessment": clinical_assessment,
                "literature_review": literature_review
            }
        )
    
    def _assess_clinical_evidence(self, clinical_assessment: Dict[str, Any]) -> float:
        """Assess clinical evidence quality."""
        
        phenotype_match = clinical_assessment.get("phenotype_match", "")
        inheritance_consistency = clinical_assessment.get("inheritance_consistency", "")
        
        score = 0.0
        
        # Phenotype match scoring
        if phenotype_match == "Excellent":
            score += 3.0
        elif phenotype_match == "Good":
            score += 2.0
        elif phenotype_match == "Fair":
            score += 1.0
        
        # Inheritance consistency scoring
        if inheritance_consistency == "Consistent":
            score += 2.0
        elif inheritance_consistency == "Partially Consistent":
            score += 1.0
        
        return score
    
    def _assess_literature_evidence(self, literature_review: Dict[str, Any]) -> float:
        """Assess literature evidence quality."""
        
        evidence_quality = literature_review.get("evidence_quality", "")
        study_design = literature_review.get("study_design_strength", "")
        
        score = 0.0
        
        # Evidence quality scoring
        if evidence_quality == "High":
            score += 3.0
        elif evidence_quality == "Moderate":
            score += 2.0
        elif evidence_quality == "Low":
            score += 1.0
        
        # Study design scoring
        if study_design == "Strong":
            score += 2.0
        elif study_design == "Adequate":
            score += 1.0
        
        return score
    
    def _combine_assessments(self, clinical_score: float, literature_score: float) -> Dict[str, Any]:
        """Combine clinical and literature assessments."""
        
        total_score = clinical_score + literature_score
        
        # Determine verdict based on combined score
        if total_score >= 8:
            verdict = "Strong Association"
            rationale = "Excellent clinical and literature evidence support strong gene-disease association."
        elif total_score >= 5:
            verdict = "Moderate Association"
            rationale = "Good clinical and/or literature evidence support moderate gene-disease association."
        elif total_score >= 2:
            verdict = "Weak Association"
            rationale = "Limited evidence suggests possible gene-disease association."
        else:
            verdict = "Insufficient Evidence"
            rationale = "Insufficient evidence to support gene-disease association."
        
        return {
            "score": total_score,
            "verdict": verdict,
            "rationale": rationale
        }
```

## Engine Registration and Usage

### Registry Management

```python
# backend/app/scoring/registry.py
from typing import Dict, List, Optional
from .base import ScoringEngine
from .clingen import ClinGenEngine
from .gencc import GenCCEngine
from .qualitative import QualitativeEngine

class ScoringEngineRegistry:
    """Registry for scoring engines."""
    
    def __init__(self):
        self._engines: Dict[str, ScoringEngine] = {}
        self._register_default_engines()
    
    def _register_default_engines(self):
        """Register built-in scoring engines."""
        self.register(ClinGenEngine())
        self.register(GenCCEngine())
        self.register(QualitativeEngine())
    
    def register(self, engine: ScoringEngine):
        """Register a scoring engine."""
        self._engines[engine.name] = engine
    
    def get_engine(self, name: str) -> Optional[ScoringEngine]:
        """Get a scoring engine by name."""
        return self._engines.get(name)
    
    def list_engines(self) -> List[str]:
        """List all registered engine names."""
        return list(self._engines.keys())
    
    def supports_schema(self, engine_name: str, schema_name: str, schema_version: str) -> bool:
        """Check if an engine supports a specific schema."""
        engine = self.get_engine(engine_name)
        return engine.supports_schema(schema_name, schema_version) if engine else False

# Global registry instance
scoring_registry = ScoringEngineRegistry()
```

### API Integration

```python
# backend/app/api/v1/scoring.py
from fastapi import APIRouter, HTTPException, Depends
from app.scoring.registry import scoring_registry
from app.schemas.scoring import ScoringRequest, ScoringResponse

router = APIRouter(prefix="/scoring", tags=["scoring"])

@router.post("/calculate", response_model=ScoringResponse)
async def calculate_scores(request: ScoringRequest):
    """Calculate scores using specified engine."""
    
    engine = scoring_registry.get_engine(request.engine_name)
    if not engine:
        raise HTTPException(status_code=400, detail=f"Unknown scoring engine: {request.engine_name}")
    
    try:
        result = engine.calculate_scores(request.evidence_data, request.schema_config)
        return ScoringResponse(
            engine_name=engine.name,
            engine_version=engine.version,
            result=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring calculation failed: {str(e)}")

@router.get("/engines")
async def list_scoring_engines():
    """List all available scoring engines."""
    return {
        "engines": [
            {
                "name": engine_name,
                "version": scoring_registry.get_engine(engine_name).version
            }
            for engine_name in scoring_registry.list_engines()
        ]
    }
```

## Testing Scoring Engines

### Unit Testing Framework

```python
# tests/scoring/test_clingen_engine.py
import pytest
from app.scoring.clingen import ClinGenEngine

class TestClinGenEngine:
    
    def setup_method(self):
        self.engine = ClinGenEngine()
    
    def test_definitive_classification(self):
        """Test definitive classification (≥12 points)."""
        
        evidence_data = {
            "genetic_evidence": {
                "case_level_data": [
                    {"pmid": "12345678", "points": 2.0, "proband_label": "Test 1"},
                    {"pmid": "87654321", "points": 2.0, "proband_label": "Test 2"}
                ],
                "segregation_data": [
                    {"pmid": "11223344", "points": 3.0, "family_label": "Family A"}
                ],
                "case_control_data": [
                    {"pmid": "55667788", "points": 6.0, "study_type": "Aggregate"}
                ]
            },
            "experimental_evidence": {
                "function": [
                    {"pmid": "99887766", "points": 1.0, "type": "Biochemical"}
                ]
            },
            "contradictory_evidence": []
        }
        
        result = self.engine.calculate_scores(evidence_data, {})
        
        assert result.verdict == "Definitive"
        assert result.scores["genetic_evidence_score"] == 12.0  # Max genetic
        assert result.scores["experimental_evidence_score"] == 1.0
        assert result.total_score == 13.0
    
    def test_disputed_classification(self):
        """Test disputed classification (contradictory evidence)."""
        
        evidence_data = {
            "genetic_evidence": {
                "case_level_data": [
                    {"pmid": "12345678", "points": 10.0, "proband_label": "Test 1"}
                ]
            },
            "contradictory_evidence": [
                {"pmid": "99999999", "description": "Contradictory study"}
            ]
        }
        
        result = self.engine.calculate_scores(evidence_data, {})
        
        assert result.verdict == "Disputed"
        assert "contradictory evidence" in result.verdict_rationale.lower()
    
    def test_validation_errors(self):
        """Test evidence validation."""
        
        evidence_data = {
            "genetic_evidence": {
                "case_level_data": [
                    {"pmid": "invalid", "points": 5.0},  # Invalid PMID, invalid points
                    {"pmid": "12345678", "proband_label": ""}  # Missing proband label
                ]
            }
        }
        
        errors = self.engine.validate_evidence(evidence_data, {})
        
        assert len(errors) >= 3  # Should catch multiple validation errors
        assert any("Invalid PMID" in error for error in errors)
        assert any("Points must be" in error for error in errors)
        assert any("Proband label required" in error for error in errors)
```

## Best Practices

### Engine Development Guidelines

1. **Immutable Calculations**: Engines should be stateless and produce consistent results
2. **Comprehensive Validation**: Validate all input data thoroughly
3. **Clear Rationales**: Generate human-readable explanations for verdicts
4. **Error Handling**: Gracefully handle malformed or missing data
5. **Performance**: Optimize for sub-second calculation times
6. **Testing**: Comprehensive unit tests with edge cases
7. **Documentation**: Document scoring rules and methodology references

### Schema Integration

1. **Engine Selection**: Schema specifies which engine to use
2. **Configuration**: Engine behavior customizable via schema config
3. **Version Compatibility**: Engines should support schema versioning
4. **Validation Alignment**: Engine validation should match schema field definitions

### Performance Considerations

1. **Caching**: Cache frequently used calculations
2. **Lazy Loading**: Load heavy resources only when needed
3. **Batch Processing**: Support bulk scoring operations
4. **Memory Management**: Clean up resources after calculations

This guide provides the foundation for creating robust, flexible scoring engines that integrate seamlessly with Gene Curator's schema-agnostic architecture.