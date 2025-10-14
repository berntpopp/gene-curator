# ClinGen Scoring Engine - SOP v11 Implementation

## Overview

The ClinGen Scoring Engine is the core business logic component that implements the ClinGen Gene-Disease Validity Standard Operating Procedure (SOP) v11. It automatically calculates evidence scores and determines classification verdicts based on structured evidence data.

## ClinGen SOP v11 Scoring Matrix

### Genetic Evidence (Maximum 12 points)

#### Case-Level Data (Maximum 12 points)
| Evidence Type | Points | Criteria |
|---------------|--------|----------|
| Variant is de novo | 2 | In individual with phenotype consistent with gene's proposed role |
| Proband with predicted/proven null variant | 1.5 | Loss of function variant in individual with phenotype |
| Proband with other variant type | 0.5 | Missense, in-frame indel, etc. |
| Two or more probands with predicted/proven null | 2 | Independent cases |
| Two or more probands with other variant types | 1 | Independent cases |

#### Segregation Data (Maximum 3 points)
| Evidence Type | Points | Criteria |
|---------------|--------|----------|
| Candidate gene sequencing | 1.5 | LOD score ≥ 2.0 |
| Exome/genome sequencing | 2 | LOD score ≥ 2.0 |
| Contradictory segregation evidence | -1 | LOD score ≤ -2.0 |

#### Case-Control Data (Maximum 6 points)
| Evidence Type | Points | Criteria |
|---------------|--------|----------|
| Case-control study (well-powered) | 4 | Odds ratio >2.0, p-value <0.05 |
| Case-control study (less well-powered) | 2 | Meets statistical significance |
| Contradictory case-control | -1 | Significant evidence against association |

### Experimental Evidence (Maximum 6 points)

#### Function (Maximum 2 points)
- Biochemical function: 0.5 points
- Protein interaction: 0.5 points
- Expression studies: 0.5 points
- Functional alteration: 1 point (patient cells/tissues)

#### Models (Maximum 4 points)
- Non-human model organism: 2 points
- Cell culture model: 1 point
- Patient cells/tissues: 2 points

#### Rescue (Maximum 4 points)
- Rescue in human: 2 points
- Rescue in non-human model: 1 point
- Rescue in cell culture: 0.5 points

## Implementation

### Core Scoring Engine

```python
from typing import List, Dict, Any
from pydantic import BaseModel
from enum import Enum

class CurationVerdict(str, Enum):
    DEFINITIVE = "Definitive"
    STRONG = "Strong" 
    MODERATE = "Moderate"
    LIMITED = "Limited"
    NO_KNOWN_DISEASE_RELATIONSHIP = "No Known Disease Relationship"
    DISPUTED = "Disputed"
    REFUTED = "Refuted"

class ClinGenScoringEngine:
    """
    Implements ClinGen SOP v11 evidence scoring and classification.
    
    This engine takes structured evidence data and automatically calculates
    genetic and experimental evidence scores according to the official
    ClinGen scoring matrix.
    """
    
    def __init__(self):
        self.sop_version = "v11"
        self.max_genetic_score = 12.0
        self.max_experimental_score = 6.0
        
    def calculate_genetic_evidence_score(self, genetic_evidence: Dict[str, Any]) -> float:
        """Calculate genetic evidence score per SOP v11 matrix."""
        total_score = 0.0
        
        # Case-level data scoring
        case_level_score = self._score_case_level_data(
            genetic_evidence.get('case_level_data', [])
        )
        total_score += min(case_level_score, 12.0)
        
        # Segregation data scoring
        segregation_score = self._score_segregation_data(
            genetic_evidence.get('segregation_data', [])
        )
        total_score += min(segregation_score, 3.0)
        
        # Case-control data scoring
        case_control_score = self._score_case_control_data(
            genetic_evidence.get('case_control_data', [])
        )
        total_score += min(case_control_score, 6.0)
        
        # Apply overall genetic evidence maximum
        return min(total_score, self.max_genetic_score)
    
    def _score_case_level_data(self, case_data: List[Dict[str, Any]]) -> float:
        """Score case-level evidence according to SOP v11."""
        total_score = 0.0
        de_novo_count = 0
        null_variant_count = 0
        other_variant_count = 0
        
        for case in case_data:
            variant_type = case.get('variant_type', '')
            is_de_novo = case.get('is_de_novo', False)
            
            if is_de_novo:
                total_score += 2.0
                de_novo_count += 1
            elif variant_type == 'Predicted or Proven Null':
                if null_variant_count == 0:
                    total_score += 1.5  # First null variant
                elif null_variant_count == 1:
                    total_score += 0.5  # Second null variant (total 2.0)
                null_variant_count += 1
            else:
                if other_variant_count == 0:
                    total_score += 0.5  # First other variant
                elif other_variant_count == 1:
                    total_score += 0.5  # Second other variant (total 1.0)
                other_variant_count += 1
        
        return total_score
    
    def _score_segregation_data(self, segregation_data: List[Dict[str, Any]]) -> float:
        """Score segregation evidence according to SOP v11."""
        total_score = 0.0
        
        for segregation in segregation_data:
            lod_score = segregation.get('lod_score_published', 0)
            sequencing_method = segregation.get('sequencing_method', '')
            
            if lod_score >= 2.0:
                if 'Exome' in sequencing_method or 'genome' in sequencing_method:
                    total_score += 2.0
                else:
                    total_score += 1.5
            elif lod_score <= -2.0:
                total_score -= 1.0  # Contradictory evidence
        
        return total_score
    
    def _score_case_control_data(self, case_control_data: List[Dict[str, Any]]) -> float:
        """Score case-control evidence according to SOP v11."""
        total_score = 0.0
        
        for study in case_control_data:
            odds_ratio = study.get('odds_ratio', 0)
            p_value = study.get('p_value', 1.0)
            study_type = study.get('study_type', '')
            
            if p_value < 0.05 and odds_ratio > 2.0:
                if study_type == 'Well-powered':
                    total_score += 4.0
                else:
                    total_score += 2.0
            elif p_value < 0.05 and odds_ratio < 0.5:
                total_score -= 1.0  # Contradictory evidence
        
        return total_score
    
    def calculate_experimental_evidence_score(self, experimental_evidence: Dict[str, Any]) -> float:
        """Calculate experimental evidence score per SOP v11 matrix."""
        total_score = 0.0
        
        # Function evidence (max 2 points)
        function_score = self._score_functional_evidence(
            experimental_evidence.get('function', [])
        )
        total_score += min(function_score, 2.0)
        
        # Model evidence (max 4 points)
        model_score = self._score_model_evidence(
            experimental_evidence.get('models', [])
        )
        total_score += min(model_score, 4.0)
        
        # Rescue evidence (max 4 points)
        rescue_score = self._score_rescue_evidence(
            experimental_evidence.get('rescue', [])
        )
        total_score += min(rescue_score, 4.0)
        
        return min(total_score, self.max_experimental_score)
    
    def _score_functional_evidence(self, function_data: List[Dict[str, Any]]) -> float:
        """Score functional evidence."""
        total_score = 0.0
        evidence_types = set()
        
        for evidence in function_data:
            evidence_type = evidence.get('type', '')
            
            # Avoid double-counting same evidence type
            if evidence_type not in evidence_types:
                if evidence_type == 'Biochemical Function':
                    total_score += 0.5
                elif evidence_type == 'Protein Interaction':
                    total_score += 0.5
                elif evidence_type == 'Expression':
                    total_score += 0.5
                elif evidence_type == 'Functional Alteration':
                    total_score += 1.0
                
                evidence_types.add(evidence_type)
        
        return total_score
    
    def _score_model_evidence(self, model_data: List[Dict[str, Any]]) -> float:
        """Score model organism evidence."""
        total_score = 0.0
        has_non_human_model = False
        has_cell_culture = False
        has_patient_cells = False
        
        for evidence in model_data:
            model_type = evidence.get('type', '')
            
            if model_type == 'Non-human model organism' and not has_non_human_model:
                total_score += 2.0
                has_non_human_model = True
            elif model_type == 'Cell culture model' and not has_cell_culture:
                total_score += 1.0
                has_cell_culture = True
            elif model_type == 'Patient cells/tissues' and not has_patient_cells:
                total_score += 2.0
                has_patient_cells = True
        
        return total_score
    
    def _score_rescue_evidence(self, rescue_data: List[Dict[str, Any]]) -> float:
        """Score rescue evidence."""
        total_score = 0.0
        has_human_rescue = False
        has_model_rescue = False
        has_cell_rescue = False
        
        for evidence in rescue_data:
            rescue_type = evidence.get('type', '')
            
            if rescue_type == 'Rescue in human' and not has_human_rescue:
                total_score += 2.0
                has_human_rescue = True
            elif rescue_type == 'Rescue in non-human model' and not has_model_rescue:
                total_score += 1.0
                has_model_rescue = True
            elif rescue_type == 'Rescue in cell culture' and not has_cell_rescue:
                total_score += 0.5
                has_cell_rescue = True
        
        return total_score
    
    def determine_verdict(self, genetic_score: float, experimental_score: float, 
                         has_contradictory: bool = False) -> CurationVerdict:
        """
        Determine curation verdict based on evidence scores per SOP v11.
        
        Classification rules:
        - Definitive: ≥12 points total
        - Strong: 7-11.99 points total  
        - Moderate: 3-6.99 points total
        - Limited: 1-2.99 points total
        - No Known Disease Relationship: <1 point total
        - Disputed: Evidence for and against (contradictory evidence present)
        """
        total_score = genetic_score + experimental_score
        
        # Check for contradictory evidence first
        if has_contradictory:
            return CurationVerdict.DISPUTED
        
        # Apply SOP v11 classification thresholds
        if total_score >= 12.0:
            return CurationVerdict.DEFINITIVE
        elif total_score >= 7.0:
            return CurationVerdict.STRONG
        elif total_score >= 3.0:
            return CurationVerdict.MODERATE
        elif total_score >= 1.0:
            return CurationVerdict.LIMITED
        else:
            return CurationVerdict.NO_KNOWN_DISEASE_RELATIONSHIP
    
    def validate_evidence_structure(self, evidence_data: Dict[str, Any]) -> List[str]:
        """
        Validate evidence data structure for ClinGen compliance.
        Returns list of validation errors.
        """
        errors = []
        
        # Validate genetic evidence structure
        genetic_evidence = evidence_data.get('genetic_evidence', {})
        if not genetic_evidence:
            errors.append("Genetic evidence is required")
        
        # Validate case-level data
        case_level_data = genetic_evidence.get('case_level_data', [])
        for i, case in enumerate(case_level_data):
            if not case.get('pmid'):
                errors.append(f"Case {i+1}: PMID is required")
            if not case.get('variant_type'):
                errors.append(f"Case {i+1}: Variant type is required")
            if 'rationale' not in case:
                errors.append(f"Case {i+1}: Rationale is required")
        
        # Validate experimental evidence if present
        experimental_evidence = evidence_data.get('experimental_evidence', {})
        for category in ['function', 'models', 'rescue']:
            evidence_list = experimental_evidence.get(category, [])
            for i, evidence in enumerate(evidence_list):
                if not evidence.get('pmid'):
                    errors.append(f"{category.title()} evidence {i+1}: PMID is required")
                if not evidence.get('description'):
                    errors.append(f"{category.title()} evidence {i+1}: Description is required")
        
        return errors
```

### Evidence Summary Generator

```python
class EvidenceSummaryGenerator:
    """
    Generates ClinGen-compliant evidence summaries per Template v5.1.
    
    Creates structured summary text that follows the official ClinGen 
    Evidence Summary Template format.
    """
    
    def __init__(self):
        self.template_version = "v5.1"
    
    def generate_summary(self, curation_data: Dict[str, Any]) -> str:
        """Generate complete evidence summary text."""
        sections = [
            self._generate_entity_description(curation_data),
            self._generate_evidence_description(curation_data),
            self._generate_summary_statement(curation_data)
        ]
        
        return "\n\n".join(filter(None, sections))
    
    def _generate_entity_description(self, curation_data: Dict[str, Any]) -> str:
        """Generate the entity description section."""
        gene_symbol = curation_data.get('gene_symbol', 'GENE')
        disease_name = curation_data.get('disease_name', 'disease')
        mode_of_inheritance = curation_data.get('mode_of_inheritance', 'autosomal recessive')
        
        # Use lumping/splitting details if provided
        lumping_splitting = curation_data.get('lumping_splitting_details', '')
        if lumping_splitting:
            entity_description = f"The {gene_symbol} gene has been associated with {disease_name} with {mode_of_inheritance} inheritance. {lumping_splitting}"
        else:
            entity_description = f"The {gene_symbol} gene has been associated with {disease_name} with {mode_of_inheritance} inheritance."
        
        return entity_description
    
    def _generate_evidence_description(self, curation_data: Dict[str, Any]) -> str:
        """Generate the evidence description section."""
        sections = []
        
        # Genetic evidence description
        genetic_desc = self._describe_genetic_evidence(
            curation_data.get('genetic_evidence', {})
        )
        if genetic_desc:
            sections.append(genetic_desc)
        
        # Experimental evidence description
        experimental_desc = self._describe_experimental_evidence(
            curation_data.get('experimental_evidence', {})
        )
        if experimental_desc:
            sections.append(experimental_desc)
        
        # Contradictory evidence
        contradictory = curation_data.get('contradictory_evidence', [])
        if contradictory:
            contradictory_desc = self._describe_contradictory_evidence(contradictory)
            sections.append(contradictory_desc)
        
        return " ".join(sections)
    
    def _generate_summary_statement(self, curation_data: Dict[str, Any]) -> str:
        """Generate verdict-specific summary statement."""
        verdict = curation_data.get('verdict')
        gene_symbol = curation_data.get('gene_symbol', 'GENE')
        disease_name = curation_data.get('disease_name', 'disease')
        
        templates = {
            CurationVerdict.DEFINITIVE: 
                f"In summary, there is definitive evidence to support the relationship between {gene_symbol} and {disease_name}. This has been repeatedly demonstrated in both the research and clinical diagnostic settings and has been upheld over time.",
            
            CurationVerdict.STRONG:
                f"In summary, there is strong evidence to support the relationship between {gene_symbol} and {disease_name}. This has been demonstrated in multiple cases and studies with consistent findings.",
            
            CurationVerdict.MODERATE:
                f"In summary, there is moderate evidence to support the relationship between {gene_symbol} and {disease_name}. Additional evidence would strengthen this association.",
            
            CurationVerdict.LIMITED:
                f"In summary, there is limited evidence to support the relationship between {gene_symbol} and {disease_name}. Significantly more evidence is needed to establish this association.",
            
            CurationVerdict.NO_KNOWN_DISEASE_RELATIONSHIP:
                f"In summary, there is currently no convincing evidence to support the relationship between {gene_symbol} and {disease_name}.",
            
            CurationVerdict.DISPUTED:
                f"In summary, the relationship between {gene_symbol} and {disease_name} is disputed due to contradictory evidence.",
        }
        
        return templates.get(verdict, f"In summary, the relationship between {gene_symbol} and {disease_name} requires further evaluation.")
```

## Testing Strategy

### Unit Tests
- Individual scoring functions with known inputs/outputs
- Edge cases (maximum scores, zero scores, contradictory evidence)
- Evidence structure validation

### Integration Tests  
- Complete scoring workflows with real curation examples
- Summary generation with various evidence combinations
- SOP v11 compliance verification

### Validation Tests
- Compare against manually scored ClinGen examples
- Expert panel review of generated summaries
- Regression testing for scoring accuracy

## Usage Examples

```python
# Initialize scoring engine
engine = ClinGenScoringEngine()

# Example evidence data
evidence_data = {
    "genetic_evidence": {
        "case_level_data": [
            {
                "pmid": "12345678",
                "proband_label": "Smith et al, Proband 1",
                "variant_type": "Predicted or Proven Null",
                "is_de_novo": True,
                "rationale": "De novo frameshift variant"
            }
        ]
    },
    "experimental_evidence": {
        "function": [
            {
                "type": "Biochemical Function",
                "pmid": "87654321", 
                "description": "Loss of enzymatic activity demonstrated"
            }
        ]
    }
}

# Calculate scores
genetic_score = engine.calculate_genetic_evidence_score(evidence_data["genetic_evidence"])
experimental_score = engine.calculate_experimental_evidence_score(evidence_data["experimental_evidence"])

# Determine verdict
verdict = engine.determine_verdict(genetic_score, experimental_score)

print(f"Genetic Evidence: {genetic_score}/12")
print(f"Experimental Evidence: {experimental_score}/6") 
print(f"Verdict: {verdict}")
```

This implementation provides a robust, testable foundation for ClinGen SOP v11 compliance within the FastAPI backend.