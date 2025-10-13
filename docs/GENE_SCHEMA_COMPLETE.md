# Complete Gene Schema Documentation

## Overview

The Gene Curator platform provides both **basic** and **complete** gene schemas to accommodate different use cases. The complete gene schema preserves all functionality from the original Firebase system while adding new ClinGen compliance features.

## Schema Architecture

### Basic Schema (`gene.py`)
- **Purpose**: Core CRUD operations and API endpoints  
- **Use Cases**: Simple gene management, API responses, basic curation
- **Fields**: Essential HGNC data + basic JSONB details

### Complete Schema (`gene_complete.py`)
- **Purpose**: Full-featured gene data with all legacy fields
- **Use Cases**: Data migration, advanced analytics, comprehensive curation
- **Fields**: All original fields + structured JSONB + ClinGen features

## Complete Gene Schema Structure

### Full JSON Example

Here's a complete gene record showing all available fields with realistic data:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "hgnc_id": "HGNC:9008",
  "approved_symbol": "PKD1",
  "previous_symbols": ["PKD"],
  "alias_symbols": ["PC1", "APKD1"],
  "chromosome": "16",
  "location": "16p13.3",
  "gene_type": "protein_coding",
  "details": {
    "expression": {
      "descartes_kidney_tpm": 45.2,
      "gtex_kidney_cortex": 67.8,
      "gtex_kidney_medulla": 54.3,
      "expression_score": 0.85
    },
    "constraints": {
      "pli": 0.999,
      "lof_z": 3.24,
      "mis_z": 1.87,
      "oe_lof": 0.04
    },
    "interactions": {
      "interaction_score": 0.78,
      "stringdb_normalized_score": 0.82,
      "stringdb_sum_score": 4.1,
      "stringdb_interactions": [
        "PKD2", "PKHD1", "GANAB", "DNAJB11", "SEC61B"
      ]
    },
    "clinical": {
      "clinical_groups": "Polycystic kidney disease",
      "onset_groups": "Adult onset, variable penetrance",
      "syndromic_groups": "Non-syndromic",
      "mgi_phenotype": [
        "abnormal kidney morphology",
        "polycystic kidneys",
        "enlarged kidney"
      ]
    },
    "external_summaries": {
      "clingen_summary": "PKD1 encodes polycystin-1, a large transmembrane protein involved in cell-cell and cell-matrix interactions. Loss-of-function variants cause autosomal dominant polycystic kidney disease.",
      "gencc_summary": "Definitive evidence for PKD1 in autosomal dominant polycystic kidney disease 1.",
      "omim_summary": [
        "Polycystic kidney disease 1 (PKD1) - 173900",
        "Polycystic kidney disease 1, severe early-onset - 617907"
      ],
      "clinvar_data": {
        "pathogenic": 156,
        "likely_pathogenic": 89,
        "benign": 23,
        "likely_benign": 45,
        "uncertain_significance": 234,
        "total_variants": 547,
        "last_updated": "2024-01-15"
      }
    },
    "curation_tracking": {
      "evidence_count": 47,
      "source_count_percentile": 95.2,
      "has_precuration": [
        "789e0123-e89b-12d3-a456-426614174002",
        "abc4567-e89b-12d3-a456-426614174003"
      ],
      "has_curation": [
        "def8901-e89b-12d3-a456-426614174004"
      ],
      "precurated_by": [
        "user123-e89b-12d3-a456-426614174005",
        "user456-e89b-12d3-a456-426614174006"
      ],
      "curated_by": [
        "curator789-e89b-12d3-a456-426614174007"
      ]
    },
    "custom_fields": {
      "institution_priority": "high",
      "research_focus": "kidney_disease",
      "last_literature_review": "2024-01-10",
      "notes": "High-impact gene for kidney disease research"
    }
  },
  "record_hash": "a1b2c3d4e5f6789012345678901234567890abcd",
  "previous_hash": null,
  "total_precurations": 2,
  "total_curations": 1,
  "latest_activity": "2024-01-14T15:22:33Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-14T15:22:33Z",
  "created_by": "admin123-e89b-12d3-a456-426614174000",
  "updated_by": "curator789-e89b-12d3-a456-426614174007"
}
```

### Schema Field Mapping

This table shows how original Firebase fields map to the new structured schema:

| Original Field | New Location | Type | Description |
|----------------|--------------|------|-------------|
| `cur_id` | `details.custom_fields.cur_id` | string | Original curation system ID |
| `approved_symbol` | `approved_symbol` | string | Official HGNC gene symbol |
| `hgnc_id` | `hgnc_id` | string | HGNC identifier |
| `clingen_summary` | `details.external_summaries.clingen_summary` | string | ClinGen database summary |
| `gencc_summary` | `details.external_summaries.gencc_summary` | string | GenCC summary |
| `omim_summary` | `details.external_summaries.omim_summary` | array | OMIM summaries |
| `clinical_groups_p` | `details.clinical.clinical_groups` | string | Clinical phenotype groupings |
| `onset_groups_p` | `details.clinical.onset_groups` | string | Age of onset classifications |
| `syndromic_groups_p` | `details.clinical.syndromic_groups` | string | Syndromic classifications |
| `evidence_count` | `details.curation_tracking.evidence_count` | number | Evidence item count |
| `source_count_percentile` | `details.curation_tracking.source_count_percentile` | number | Literature mention percentile |
| `clinvar` | `details.external_summaries.clinvar_data` | object | ClinVar variant data |
| `descartes_kidney_tpm` | `details.expression.descartes_kidney_tpm` | number | Descartes kidney expression |
| `gtex_kidney_cortex` | `details.expression.gtex_kidney_cortex` | number | GTEx kidney cortex expression |
| `gtex_kidney_medulla` | `details.expression.gtex_kidney_medulla` | number | GTEx kidney medulla expression |
| `expression_score` | `details.expression.expression_score` | number | Composite expression score |
| `interaction_score` | `details.interactions.interaction_score` | number | Gene interaction score |
| `lof_z` | `details.constraints.lof_z` | number | Loss of function Z-score |
| `mis_z` | `details.constraints.mis_z` | number | Missense Z-score |
| `oe_lof` | `details.constraints.oe_lof` | number | Observed/Expected LoF ratio |
| `pLI` | `details.constraints.pli` | number | Probability LoF intolerant |
| `mgi_phenotype` | `details.clinical.mgi_phenotype` | array | Mouse phenotype data |
| `stringdb_interaction_normalized_score` | `details.interactions.stringdb_normalized_score` | number | STRING-DB normalized score |
| `stringdb_interaction_string` | `details.interactions.stringdb_interactions` | array | STRING-DB interactions |
| `stringdb_interaction_sum_score` | `details.interactions.stringdb_sum_score` | number | STRING-DB sum score |
| `hasPrecuration` | `details.curation_tracking.has_precuration` | array | Precuration document IDs |
| `hasCuration` | `details.curation_tracking.has_curation` | array | Curation document IDs |
| `precuratedBy` | `details.curation_tracking.precurated_by` | array | Precurator user IDs |
| `curatedBy` | `details.curation_tracking.curated_by` | array | Curator user IDs |

### Core Fields
```python
class GeneComplete(BaseModel):
    # HGNC Core
    hgnc_id: str                           # "HGNC:1234"
    approved_symbol: str                   # "BRCA1"
    previous_symbols: Optional[List[str]]  # ["BRCC1"]
    alias_symbols: Optional[List[str]]     # ["RNF53", "PPP1R53"]
    
    # Genomic Location
    chromosome: Optional[str]              # "17"
    location: Optional[str]                # "17q21.31"
    
    # Gene type
    gene_type: Optional[str]               # "protein_coding"
    
    # Comprehensive Details (JSONB)
    details: Optional[GeneDetailsComplete]
```

### Structured JSONB Details

The `details` field contains organized substructures for different types of gene data:

#### 1. Expression Data
```python
class ExpressionData(BaseModel):
    descartes_kidney_tpm: Optional[float]      # Kidney expression from Descartes
    gtex_kidney_cortex: Optional[float]        # GTEx kidney cortex expression
    gtex_kidney_medulla: Optional[float]       # GTEx kidney medulla expression
    expression_score: Optional[float]          # Composite expression score
```

#### 2. Constraint Metrics
```python
class ConstraintMetrics(BaseModel):
    pli: Optional[float]           # Probability of Loss-of-function Intolerance
    lof_z: Optional[float]         # Loss of function Z-score
    mis_z: Optional[float]         # Missense Z-score  
    oe_lof: Optional[float]        # Observed/Expected LoF ratio
```

#### 3. Interaction Data
```python
class InteractionData(BaseModel):
    interaction_score: Optional[float]                 # Composite interaction score
    stringdb_normalized_score: Optional[float]         # STRING-DB normalized score
    stringdb_sum_score: Optional[float]                # STRING-DB sum score
    stringdb_interactions: Optional[List[str]]         # List of interacting genes
```

#### 4. Clinical Data
```python
class ClinicalData(BaseModel):
    clinical_groups: Optional[str]         # Clinical phenotype groupings
    onset_groups: Optional[str]            # Age of onset classifications
    syndromic_groups: Optional[str]        # Syndromic vs non-syndromic
    mgi_phenotype: Optional[List[str]]     # Mouse Genome Informatics phenotypes
```

#### 5. External Summaries
```python
class ExternalSummaries(BaseModel):
    clingen_summary: Optional[str]                 # ClinGen database summary
    gencc_summary: Optional[str]                   # GenCC summary
    omim_summary: Optional[List[str]]              # OMIM summaries
    clinvar_data: Optional[Dict[str, Any]]         # ClinVar pathogenicity data
```

#### 6. Curation Tracking
```python
class CurationTracking(BaseModel):
    evidence_count: Optional[int]              # Number of evidence items
    source_count_percentile: Optional[float]  # Literature mention percentile
    has_precuration: Optional[List[str]]      # Precuration document IDs
    has_curation: Optional[List[str]]         # Curation document IDs
    precurated_by: Optional[List[str]]        # User IDs who precurated
    curated_by: Optional[List[str]]           # User IDs who curated
```

## Usage Examples

### Creating a Complete Gene

```python
from app.schemas.gene_complete import GeneCreateComplete, GeneDetailsComplete
from app.schemas.gene_complete import ExpressionData, ConstraintMetrics

# Create expression data
expression = ExpressionData(
    gtex_kidney_cortex=45.2,
    gtex_kidney_medulla=38.7,
    expression_score=0.85
)

# Create constraint metrics
constraints = ConstraintMetrics(
    pli=0.999,
    lof_z=3.24,
    oe_lof=0.04
)

# Assemble complete details
details = GeneDetailsComplete(
    expression=expression,
    constraints=constraints
)

# Create complete gene
gene = GeneCreateComplete(
    hgnc_id="HGNC:1100",
    approved_symbol="BRCA1",
    chromosome="17", 
    location="17q21.31",
    details=details
)
```

### Migrating Legacy Data

```python
from app.schemas.gene_complete import LegacyGeneData

# Legacy Firebase data
legacy_data = {
    "approved_symbol": "PKD1",
    "hgnc_id": "HGNC:9008", 
    "pLI": 0.999,
    "gtex_kidney_cortex": 67.8,
    "clinvar": {"pathogenic": 45, "benign": 12},
    "mgi_phenotype": ["abnormal kidney morphology", "polycystic kidneys"]
}

# Convert to modern schema
legacy_gene = LegacyGeneData(**legacy_data)
complete_gene = legacy_gene.to_complete_gene()

# Result: GeneCreateComplete with properly structured details
print(complete_gene.details.constraints.pli)  # 0.999
print(complete_gene.details.expression.gtex_kidney_cortex)  # 67.8
```

### Validating Gene Completeness

```python
from app.schemas.gene_complete import validate_gene_completeness

# Check if gene is ready for curation
completeness = validate_gene_completeness(gene)

print(completeness)
# {
#   "has_basic_info": True,
#   "has_location": True, 
#   "has_external_summaries": True,
#   "has_expression_data": True,
#   "has_constraint_data": True,
#   "has_phenotype_data": False,
#   "ready_for_curation": True
# }
```

### API Integration

```python
# FastAPI endpoint using complete schema
from app.schemas.gene_complete import GeneResponseComplete

@app.get("/genes/{gene_id}/complete", response_model=GeneResponseComplete)
async def get_complete_gene(gene_id: str):
    """Get gene with all available data."""
    gene = await gene_service.get_complete_gene(gene_id)
    return gene

@app.post("/genes/import/legacy", response_model=List[GeneResponseComplete])
async def import_legacy_genes(genes: List[LegacyGeneData]):
    """Import genes from legacy Firebase format."""
    complete_genes = [gene.to_complete_gene() for gene in genes]
    return await gene_service.bulk_create_complete(complete_genes)
```

## Database Storage

### PostgreSQL Table Structure

The complete gene data is stored in the existing `genes` table with the `details` JSONB column:

```sql
-- Example of stored data
SELECT 
    approved_symbol,
    hgnc_id,
    details->'expression'->>'gtex_kidney_cortex' as kidney_expression,
    details->'constraints'->>'pli' as pli_score,
    details->'curation_tracking'->>'evidence_count' as evidence_count
FROM genes 
WHERE hgnc_id = 'HGNC:1100';
```

### JSONB Queries

```sql
-- Find genes with high pLI scores
SELECT approved_symbol, hgnc_id
FROM genes 
WHERE (details->'constraints'->>'pli')::float > 0.9;

-- Find genes with kidney expression data
SELECT approved_symbol, 
       details->'expression'->>'gtex_kidney_cortex' as kidney_expr
FROM genes 
WHERE details->'expression'->>'gtex_kidney_cortex' IS NOT NULL;

-- Find genes ready for curation (have multiple data types)
SELECT approved_symbol
FROM genes 
WHERE details->'external_summaries' IS NOT NULL
  AND details->'constraints' IS NOT NULL  
  AND details->'expression' IS NOT NULL;
```

### Performance Optimizations

```sql
-- Create GIN indexes for common queries
CREATE INDEX idx_genes_details_expression 
ON genes USING GIN ((details->'expression'));

CREATE INDEX idx_genes_details_constraints 
ON genes USING GIN ((details->'constraints'));

CREATE INDEX idx_genes_details_curation_tracking 
ON genes USING GIN ((details->'curation_tracking'));

-- Create functional indexes for specific fields
CREATE INDEX idx_genes_pli_score 
ON genes ((details->'constraints'->>'pli')::float) 
WHERE details->'constraints'->>'pli' IS NOT NULL;
```

## Migration Strategy

### 1. Assessment Phase
```python
# Analyze current data completeness
from collections import Counter

completeness_stats = Counter()
for gene in legacy_genes:
    completeness = validate_gene_completeness(gene)
    completeness_stats[tuple(sorted(completeness.items()))] += 1

print("Completeness distribution:", completeness_stats)
```

### 2. Migration Phase
```python
# Batch migration with validation
async def migrate_gene_batch(legacy_batch: List[dict]) -> List[GeneResponseComplete]:
    results = []
    errors = []
    
    for legacy_data in legacy_batch:
        try:
            # Convert legacy data
            legacy_gene = LegacyGeneData(**legacy_data)
            complete_gene = legacy_gene.to_complete_gene()
            
            # Validate completeness
            completeness = validate_gene_completeness(complete_gene)
            
            # Store with completeness metadata if needed
            if completeness.get("ready_for_curation"):
                complete_gene.details.custom_fields = {
                    "curation_ready": True
                }
            
            result = await gene_service.create_complete(complete_gene)
            results.append(result)
            
        except Exception as e:
            errors.append({"data": legacy_data, "error": str(e)})
    
    return results, errors
```

### 3. Validation Phase
```python
# Post-migration validation
async def validate_migration():
    """Validate that all legacy data was properly migrated."""
    
    # Check field preservation
    legacy_count = await legacy_db.count_genes()
    migrated_count = await new_db.count_genes()
    
    assert legacy_count == migrated_count, "Gene count mismatch"
    
    # Spot check data integrity
    sample_genes = await new_db.get_random_genes(100)
    for gene in sample_genes:
        completeness = validate_gene_completeness(gene)
        assert completeness["has_basic_info"], f"Missing basic info: {gene.hgnc_id}"
        
        # Verify legacy data preservation
        if gene.details.custom_fields:
            assert "cur_id" in gene.details.custom_fields, "Original CUR ID not preserved"
```

## Advanced Features

### Analytics and Reporting

```python
from app.schemas.gene_complete import GeneAnalytics

# Generate gene analytics
async def generate_gene_analytics(gene_id: str) -> GeneAnalytics:
    """Generate comprehensive analytics for a gene."""
    
    gene = await get_complete_gene(gene_id)
    precurations = await get_gene_precurations(gene_id)
    curations = await get_gene_curations(gene_id)
    
    return GeneAnalytics(
        gene_id=gene_id,
        precuration_count=len(precurations),
        curation_count=len(curations),
        published_curation_count=len([c for c in curations if c.status == "Published"]),
        total_evidence_entries=sum(count_evidence_entries(c) for c in curations),
        unique_contributors=len(set(c.created_by for c in curations + precurations)),
        first_precuration_date=min([p.created_at for p in precurations]) if precurations else None,
        latest_curation_date=max([c.updated_at for c in curations]) if curations else None
    )
```

### Bulk Operations

```python
# Bulk update with complete schema
async def bulk_update_expression_data(updates: Dict[str, ExpressionData]):
    """Update expression data for multiple genes."""
    
    for hgnc_id, expression_data in updates.items():
        gene = await get_gene_by_hgnc_id(hgnc_id)
        if gene.details is None:
            gene.details = GeneDetailsComplete()
        
        gene.details.expression = expression_data
        await update_complete_gene(gene.id, gene)
```

### Export and Integration

```python
from app.schemas.gene_complete import GeneExportOptions

# Export complete gene data
async def export_genes_complete(options: GeneExportOptions) -> str:
    """Export genes with complete data in specified format."""
    
    genes = await get_genes_filtered(options.filter_criteria)
    
    if options.format_type == "json":
        return export_genes_json(genes, options)
    elif options.format_type == "csv":
        return export_genes_csv(genes, options)
    elif options.format_type == "xlsx":
        return export_genes_excel(genes, options)
```

## Best Practices

### 1. Choose the Right Schema
- **Basic Schema**: Use for simple CRUD operations, API responses
- **Complete Schema**: Use for data migration, analytics, comprehensive displays

### 2. Handle Missing Data Gracefully
```python
# Always check for None values in optional fields
if gene.details and gene.details.constraints and gene.details.constraints.pli:
    pli_score = gene.details.constraints.pli
else:
    pli_score = None
```

### 3. Use Validation Functions
```python
# Validate before creating curations
completeness = validate_gene_completeness(gene)
if not completeness["ready_for_curation"]:
    raise ValueError("Gene lacks sufficient data for curation")
```

### 4. Preserve Original Identifiers
```python
# Preserve original identifiers if needed
if legacy_data.get("cur_id"):
    gene.details.custom_fields = {"cur_id": legacy_data.get("cur_id")}
```

### 5. Index for Performance
```sql
-- Create indexes for commonly queried fields
CREATE INDEX idx_genes_curation_ready 
ON genes ((details->'constraints' IS NOT NULL AND details->'external_summaries' IS NOT NULL));
```

## Schema Evolution

The complete gene schema is designed for extensibility:

1. **Custom Fields**: Use `details.custom_fields` for institution-specific data
2. **Data Preservation**: Use `details.custom_fields` for any additional institutional data  
3. **Structured Growth**: Add new organized substructures to `GeneDetailsComplete`
4. **Migration Support**: Built-in conversion from legacy formats

This approach ensures that Gene Curator can accommodate both current needs and future expansion while maintaining data integrity and performance.

---

## Related Documentation

- [Database Schema](./DATABASE_SCHEMA.md) - PostgreSQL table structures
- [API Reference](./API_REFERENCE.md) - Gene endpoint documentation
- [Architecture](./ARCHITECTURE.md) - Overall system design
- [Frontend Guide](./FRONTEND_GUIDE.md) - UI component integration