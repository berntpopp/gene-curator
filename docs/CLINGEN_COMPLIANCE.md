# Gene Curator - ClinGen SOP v11 Compliance

## Overview

Gene Curator implements native support for ClinGen Standard Operating Procedure (SOP) v11 for Gene-Disease Clinical Validity Curation. This document details the complete implementation of ClinGen requirements, including evidence scoring, classification criteria, and summary generation.

## ClinGen SOP v11 Implementation

### Core Compliance Features

1. **Evidence Scoring Engine**: Automated calculation of genetic and experimental evidence scores
2. **Summary Generator**: Programmatic generation of evidence summaries per Template v5.1
3. **Classification System**: Automated verdict assignment based on evidence scores
4. **Workflow Integration**: Multi-stage review process aligned with expert panel procedures

### Evidence Framework

#### Genetic Evidence (Maximum 12 points)

The genetic evidence category encompasses three sub-categories with specific point allocations:

##### Case-Level Data (Maximum 12 points total)
Evidence from individual probands with variants in the gene of interest.

**Scoring Criteria**:
- **Variant Type**: Predicted/Proven Null vs Other
- **De Novo Status**: De novo variants receive higher scores
- **Functional Evidence**: Supporting functional impact data
- **Phenotype Match**: HPO term alignment with expected phenotype

**Point Allocation Examples**:
```json
{
  "case_level_data": [
    {
      "variant_type": "Predicted or Proven Null",
      "is_de_novo": true,
      "functional_evidence": "Western blot shows no protein",
      "points": 2.0,
      "max_individual": 2.0,
      "rationale": "De novo null variant with functional validation"
    },
    {
      "variant_type": "Other Variant Type", 
      "is_de_novo": false,
      "functional_evidence": "Missense variant, computational prediction",
      "points": 0.5,
      "max_individual": 1.5,
      "rationale": "Inherited missense with moderate prediction confidence"
    }
  ]
}
```

**Database Validation**:
```sql
-- Automatic validation in scoring trigger
CONSTRAINT case_level_maximum CHECK (
    (SELECT SUM((evidence->>'points')::NUMERIC) 
     FROM jsonb_array_elements(details->'genetic_evidence'->'case_level_data') AS evidence) <= 12.0
);
```

##### Segregation Data (Maximum 3 points total)
Evidence from family studies demonstrating co-segregation of variants with disease.

**Scoring Criteria**:
- Published LOD score ≥ 3.0: 2 points
- Published LOD score 2.0-2.99: 1 point  
- Unpublished segregation data: Variable points based on family structure

**Point Allocation Examples**:
```json
{
  "segregation_data": [
    {
      "study_type": "Published LOD score",
      "lod_score": 3.2,
      "family_count": 1,
      "points": 2.0,
      "pmid": "12345678",
      "rationale": "LOD score exceeds 3.0 threshold"
    }
  ]
}
```

##### Case-Control Data (Maximum 6 points total)
Population-based studies comparing variant frequencies between cases and controls.

**Scoring Criteria**:
- Single well-powered study: Up to 4 points
- Multiple smaller studies: Up to 6 points total
- Effect size and statistical significance considered

**Point Allocation Examples**:
```json
{
  "case_control_data": [
    {
      "study_type": "Single study",
      "odds_ratio": 4.9,
      "confidence_interval": "1.4-17.7", 
      "p_value": 0.015,
      "case_count": 150,
      "control_count": 500,
      "points": 2.0,
      "pmid": "87654321",
      "rationale": "Significant association with adequate power"
    }
  ]
}
```

#### Experimental Evidence (Maximum 6 points)

Evidence from functional studies demonstrating the biological mechanism.

##### Function Evidence
**Categories**:
- Biochemical Function: Enzyme assays, binding studies
- Protein Interaction: Interaction disruption studies
- Expression: Gene expression analysis

**Scoring**: 0.5 points per study, maximum varies by category

##### Model Systems Evidence
**Categories**:
- Cell Culture Models: 1-2 points
- Non-human Model Organisms: 2-4 points  
- Patient-derived Models: Variable points

**Example Implementation**:
```json
{
  "models": [
    {
      "type": "Non-human model organism",
      "organism": "Danio rerio",
      "phenotype_recapitulation": "Cardiac defects match human",
      "rescue_performed": true,
      "points": 2.0,
      "pmid": "11223344",
      "rationale": "Zebrafish model recapitulates key disease features"
    }
  ]
}
```

##### Rescue Evidence
**Categories**:
- Rescue in Human: Cell/tissue-level rescue
- Rescue in Non-human Model: Functional complementation
- Patient Phenotype Rescue: Clinical improvement

**Maximum Points**: 2 points per category, 4 points total

### Automated Scoring Engine

#### Database-Level Implementation

The scoring engine is implemented as PostgreSQL triggers that automatically calculate evidence scores:

```sql
CREATE OR REPLACE FUNCTION calculate_clingen_scores()
RETURNS TRIGGER AS $$
DECLARE
    genetic_score NUMERIC(4,2) := 0.0;
    experimental_score NUMERIC(4,2) := 0.0;
    case_level_total NUMERIC(4,2);
    segregation_total NUMERIC(4,2);
    case_control_total NUMERIC(4,2);
    experimental_total NUMERIC(4,2);
BEGIN
    -- Calculate genetic evidence components
    SELECT COALESCE(SUM((evidence->>'points')::NUMERIC), 0)
    INTO case_level_total
    FROM jsonb_array_elements(NEW.details->'genetic_evidence'->'case_level_data') AS evidence;
    
    SELECT COALESCE(SUM((evidence->>'points')::NUMERIC), 0)
    INTO segregation_total
    FROM jsonb_array_elements(NEW.details->'genetic_evidence'->'segregation_data') AS evidence;
    
    SELECT COALESCE(SUM((evidence->>'points')::NUMERIC), 0)
    INTO case_control_total
    FROM jsonb_array_elements(NEW.details->'genetic_evidence'->'case_control_data') AS evidence;
    
    -- Apply SOP v11 maximums and calculate total genetic score
    genetic_score := LEAST(
        LEAST(case_level_total, 12.0) + 
        LEAST(segregation_total, 3.0) + 
        LEAST(case_control_total, 6.0),
        12.0  -- Overall genetic evidence maximum
    );
    
    -- Calculate experimental evidence score
    SELECT COALESCE(SUM((evidence->>'points')::NUMERIC), 0)
    INTO experimental_total
    FROM (
        SELECT evidence FROM jsonb_array_elements(NEW.details->'experimental_evidence'->'function') AS evidence
        UNION ALL
        SELECT evidence FROM jsonb_array_elements(NEW.details->'experimental_evidence'->'models') AS evidence
        UNION ALL
        SELECT evidence FROM jsonb_array_elements(NEW.details->'experimental_evidence'->'rescue') AS evidence
    ) AS all_evidence;
    
    experimental_score := LEAST(experimental_total, 6.0);
    
    -- Update calculated scores
    NEW.genetic_evidence_score := genetic_score;
    NEW.experimental_evidence_score := experimental_score;
    -- total_score is computed column: genetic + experimental
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

#### Classification Logic

**Automated Verdict Assignment**:
```python
def assign_verdict(total_score: float, has_contradictory: bool) -> CurationVerdict:
    """Assign ClinGen verdict based on evidence scores."""
    if has_contradictory:
        return CurationVerdict.DISPUTED
    
    if total_score >= 12.0:
        return CurationVerdict.DEFINITIVE
    elif total_score >= 7.0:
        return CurationVerdict.STRONG
    elif total_score >= 4.0:
        return CurationVerdict.MODERATE
    elif total_score >= 1.0:
        return CurationVerdict.LIMITED
    else:
        return CurationVerdict.NO_KNOWN_DISEASE_RELATIONSHIP
```

**Classification Thresholds**:

| Score Range | Contradictory Evidence | Classification | Confidence Level |
|-------------|------------------------|----------------|------------------|
| ≥12.0       | No                     | Definitive     | High             |
| 7.0-11.99   | No                     | Strong         | High             |
| 4.0-6.99    | No                     | Moderate       | Medium           |
| 1.0-3.99    | No                     | Limited        | Low              |
| 0.0-0.99    | No                     | No Known       | N/A              |
| Any         | Yes                    | Disputed       | Conflicted       |

### Evidence Summary Generation

#### Template v5.1 Implementation

Gene Curator automatically generates evidence summaries following the ClinGen Evidence Summary Template v5.1:

```python
def generate_evidence_summary(curation: Curation) -> str:
    """Generate ClinGen-compliant evidence summary."""
    
    template = """
{gene_symbol} AND {disease_name}

EXPERT PANEL: {gcep_affiliation}
GENE-DISEASE RELATIONSHIP: {verdict}  
MOI: {mode_of_inheritance}
SOP: {sop_version}

GENETIC EVIDENCE ({genetic_score} points):
{genetic_evidence_summary}

EXPERIMENTAL EVIDENCE ({experimental_score} points): 
{experimental_evidence_summary}

{contradictory_evidence_section}

TOTAL SCORE: {total_score} points
CLASSIFICATION: {verdict}

{additional_considerations}
"""
    
    return template.format(
        gene_symbol=curation.gene.approved_symbol,
        disease_name=curation.disease_name,
        gcep_affiliation=curation.gcep_affiliation,
        verdict=curation.verdict.value,
        mode_of_inheritance=curation.mode_of_inheritance,
        sop_version=curation.sop_version,
        genetic_score=curation.genetic_evidence_score,
        experimental_score=curation.experimental_evidence_score,
        total_score=curation.total_score,
        genetic_evidence_summary=format_genetic_evidence(curation.details),
        experimental_evidence_summary=format_experimental_evidence(curation.details),
        contradictory_evidence_section=format_contradictory_evidence(curation.details),
        additional_considerations=format_additional_considerations(curation.details)
    )
```

#### Summary Components

**Genetic Evidence Summary**:
```python
def format_genetic_evidence(details: dict) -> str:
    """Format genetic evidence section of summary."""
    genetic = details.get('genetic_evidence', {})
    summary_parts = []
    
    # Case-level evidence
    case_level = genetic.get('case_level_data', [])
    if case_level:
        case_points = sum(float(item.get('points', 0)) for item in case_level)
        summary_parts.append(
            f"Case-level evidence includes {len(case_level)} probands "
            f"with qualifying variants ({case_points} points)"
        )
    
    # Segregation evidence  
    segregation = genetic.get('segregation_data', [])
    if segregation:
        seg_points = sum(float(item.get('points', 0)) for item in segregation)
        summary_parts.append(
            f"Segregation evidence from {len(segregation)} studies "
            f"({seg_points} points)"
        )
    
    # Case-control evidence
    case_control = genetic.get('case_control_data', [])
    if case_control:
        cc_points = sum(float(item.get('points', 0)) for item in case_control)
        summary_parts.append(
            f"Case-control evidence from {len(case_control)} studies "
            f"({cc_points} points)"
        )
    
    return ". ".join(summary_parts) + "."
```

### Contradictory Evidence Handling

#### Evidence Categories
- **Case-level contradictory evidence**: Cases that don't fit expected phenotype
- **Segregation contradictory evidence**: Families where variants don't co-segregate
- **Case-control contradictory evidence**: Studies showing no association
- **Functional contradictory evidence**: Studies refuting proposed mechanism

#### Implementation
```json
{
  "contradictory_evidence": [
    {
      "category": "Case-control",
      "pmid": "44455566",
      "description": "Large case-control study (n=1000 cases, n=2000 controls) found no significant association",
      "statistical_power": "Well-powered",
      "impact_assessment": "Contradicts genetic evidence",
      "curator_comment": "Study population may have different genetic background"
    }
  ]
}
```

#### Impact on Classification
- **Any contradictory evidence** → Classification becomes "Disputed"
- **Refuting evidence** → Classification becomes "Refuted"  
- **Weak contradictory evidence** → May be overcome by strong supporting evidence

### Quality Control Measures

#### Evidence Validation Rules

**PMID Validation**:
```python
def validate_pmid(pmid: str) -> bool:
    """Validate PubMed ID format and accessibility."""
    if not pmid.isdigit():
        return False
    
    # Check PubMed API for accessibility
    response = requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}")
    return response.status_code == 200 and "error" not in response.text.lower()
```

**Point Assignment Validation**:
```python
def validate_evidence_points(evidence_category: str, points: float) -> bool:
    """Validate evidence points against SOP v11 rules."""
    max_points = {
        'case_level_individual': 2.0,
        'case_level_total': 12.0,
        'segregation_total': 3.0,
        'case_control_total': 6.0,
        'experimental_total': 6.0
    }
    
    return 0 <= points <= max_points.get(evidence_category, float('inf'))
```

#### Scientific Review Process

**Primary Review Checklist**:
- [ ] All evidence entries have valid PMIDs
- [ ] Point assignments follow SOP v11 guidelines  
- [ ] Evidence descriptions are accurate and complete
- [ ] Contradictory evidence is appropriately considered
- [ ] Classification matches evidence strength

**Secondary Review Checklist**:
- [ ] Literature interpretation is scientifically sound
- [ ] Methodology of cited studies is appropriate
- [ ] Evidence quality assessment is accurate
- [ ] Summary accurately reflects the evidence
- [ ] Ready for expert panel publication

### GCEP Integration

#### Gene Curation Expert Panel (GCEP) Support

**GCEP Affiliations**:
- Cardiovascular GCEP
- Hearing Loss GCEP  
- Kidney Disease GCEP
- Cancer GCEP
- Neurological GCEP
- And others as established by ClinGen

**Workflow Integration**:
```python
class GCEPWorkflow:
    def __init__(self, gcep_affiliation: str):
        self.gcep = gcep_affiliation
        self.review_requirements = self.get_gcep_requirements()
    
    def get_gcep_requirements(self) -> dict:
        """Get GCEP-specific review requirements."""
        requirements = {
            "Cardiovascular GCEP": {
                "min_reviewers": 2,
                "domain_expertise_required": True,
                "phenotype_specificity": "high"
            },
            "Kidney Disease GCEP": {
                "min_reviewers": 2, 
                "inheritance_focus": ["autosomal_recessive", "autosomal_dominant"],
                "phenotype_ontology": "HP:0000077"  # Abnormality of the kidney
            }
        }
        return requirements.get(self.gcep, {})
```

### External System Integration

#### GenCC Submission Format

```python
def prepare_gencc_submission(curation: Curation) -> dict:
    """Prepare curation for GenCC submission."""
    return {
        "gene_symbol": curation.gene.approved_symbol,
        "hgnc_id": curation.gene.hgnc_id,
        "disease_name": curation.disease_name,
        "mondo_id": curation.mondo_id,
        "mode_of_inheritance": curation.mode_of_inheritance,
        "classification": curation.verdict.value,
        "evidence_level": map_verdict_to_evidence_level(curation.verdict),
        "submitter": curation.gcep_affiliation,
        "submission_date": curation.published_at.isoformat(),
        "evidence_summary": curation.summary_text,
        "sop_version": curation.sop_version
    }
```

#### ClinVar Integration (Future)

```python
def prepare_clinvar_submission(curation: Curation) -> dict:
    """Prepare variant-level data for ClinVar submission."""
    variants = extract_variants_from_evidence(curation.details)
    
    return {
        "submitter_id": "gene_curator_platform",
        "gene_symbol": curation.gene.approved_symbol,
        "condition": curation.disease_name,
        "variants": [
            {
                "variant_description": var["description"],
                "clinical_significance": map_evidence_to_clinvar(var),
                "evidence_summary": var["rationale"],
                "pmid": var.get("pmid")
            }
            for var in variants
        ]
    }
```

### Monitoring and Compliance Metrics

#### Compliance Dashboard Metrics

**Evidence Quality Metrics**:
- Average evidence entries per curation
- PMID validation success rate
- Point assignment accuracy
- Review completion time

**Classification Metrics**:
- Distribution of verdicts (Definitive vs Strong vs Moderate vs Limited)
- Contradiction rate (evidence conflicts)
- Appeal/revision frequency
- Expert panel agreement rate

**Scientific Rigor Metrics**:
- Citation accuracy rate
- Methodology appropriateness score
- Reproducibility assessment
- External validation rate

#### Automated Compliance Checking

```python
def check_sop_compliance(curation: Curation) -> ComplianceReport:
    """Generate automated compliance report."""
    issues = []
    
    # Check evidence score maximums
    if curation.genetic_evidence_score > 12.0:
        issues.append("Genetic evidence exceeds SOP v11 maximum (12 points)")
    
    if curation.experimental_evidence_score > 6.0:
        issues.append("Experimental evidence exceeds SOP v11 maximum (6 points)")
    
    # Check evidence-verdict consistency
    expected_verdict = assign_verdict(
        curation.total_score, 
        curation.has_contradictory_evidence
    )
    if curation.verdict != expected_verdict:
        issues.append(f"Verdict {curation.verdict} inconsistent with score {curation.total_score}")
    
    # Check required evidence categories
    genetic_evidence = curation.details.get('genetic_evidence', {})
    if not any(genetic_evidence.values()):
        issues.append("No genetic evidence provided")
    
    return ComplianceReport(
        compliant=len(issues) == 0,
        issues=issues,
        score=calculate_compliance_score(issues)
    )
```

---

## Related Documentation

- [Database Schema](./DATABASE_SCHEMA.md) - ClinGen schema implementation
- [Workflow Documentation](./WORKFLOW.md) - Review and approval processes  
- [API Reference](./API_REFERENCE.md) - ClinGen-specific endpoints
- [Frontend Guide](./FRONTEND_GUIDE.md) - Evidence entry interfaces
- [Architecture](./ARCHITECTURE.md) - Overall system design

## External References

- [ClinGen Gene-Disease Clinical Validity SOP v11](https://clinicalgenome.org/docs/gene-disease-clinical-validity-standard-operating-procedures-version-11/)
- [ClinGen Evidence Summary Template v5.1](https://clinicalgenome.org/docs/gene-disease-clinical-validity-evidence-summary-template-version-5-1/)
- [GenCC Gene-Disease Relationship Classifications](https://thegencc.org/faq.html#validity-termsdefinitions-panel)
- [ClinGen Expert Panel Process](https://clinicalgenome.org/curation-activities/gene-disease-validity/)