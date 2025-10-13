# Gene Curator - API Reference

## Overview

Gene Curator provides comprehensive RESTful API endpoints built with FastAPI for a **scope-based, schema-agnostic** curation platform. This document details all available endpoints including clinical specialty management, multi-stage workflows with 4-eyes principle review, schema management, dynamic validation, multi-methodology scoring, and flexible curation workflows that adapt to any scientific approach.

## Base URL and Versioning

**Production**: `https://gene-curator.org/api/v1`  
**Development**: `http://localhost:8000/api/v1`

All API endpoints are versioned and follow RESTful conventions with automatic OpenAPI/Swagger documentation available at `/docs`.

## Authentication

### JWT Token Authentication

All protected endpoints require Bearer token authentication:

```http
Authorization: Bearer <jwt_token>
```

### Authentication Endpoints

#### POST /auth/register
Register a new user account.

**Request Body**:
```json
{
  "email": "curator@example.org",
  "password": "SecurePassword123!",
  "name": "Dr. Jane Curator",
  "role": "curator",
  "assigned_scopes": ["123e4567-e89b-12d3-a456-scope001", "123e4567-e89b-12d3-a456-scope002"]
}
```

**Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "curator@example.org",
  "name": "Dr. Jane Curator",
  "role": "curator",
  "is_active": true,
  "assigned_scopes": ["123e4567-e89b-12d3-a456-scope001", "123e4567-e89b-12d3-a456-scope002"],
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### POST /auth/login
Authenticate and receive JWT tokens.

**Request Body**:
```json
{
  "email": "curator@example.org",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "curator@example.org",
    "name": "Dr. Jane Curator",
    "role": "curator",
    "assigned_scopes": ["123e4567-e89b-12d3-a456-scope001", "123e4567-e89b-12d3-a456-scope002"]
  }
}
```

#### POST /auth/refresh
Refresh expired access token.

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### GET /auth/me
Get current user information.

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "curator@example.org",
  "name": "Dr. Jane Curator",
  "role": "curator",
  "is_active": true,
  "assigned_scopes": ["123e4567-e89b-12d3-a456-scope001", "123e4567-e89b-12d3-a456-scope002"],
  "last_login": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Gene Management Endpoints

### GET /genes
List genes with pagination and filtering.

**Query Parameters**:
- `skip` (int, default=0): Number of records to skip
- `limit` (int, default=50, max=500): Number of records to return
- `search` (string): Search term for gene symbol or HGNC ID
- `chromosome` (string): Filter by chromosome
- `sort_by` (string, default="approved_symbol"): Field to sort by
- `sort_order` (string, default="asc"): Sort order (asc/desc)

**Response** (200 OK):
```json
{
  "genes": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "hgnc_id": "HGNC:12345",
      "approved_symbol": "BRCA1",
      "chromosome": "17",
      "location": "17q21.31",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50,
  "has_next": false,
  "has_prev": false
}
```

### POST /genes
Create a new gene entry.

**Request Body**:
```json
{
  "hgnc_id": "HGNC:67890",
  "approved_symbol": "PKD1",
  "chromosome": "16",
  "location": "16p13.3",
  "details": {
    "gene_type": "protein_coding",
    "aliases": ["PC1", "APKD1"],
    "function": "Encodes polycystin-1 protein"
  }
}
```

**Response** (201 Created):
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "hgnc_id": "HGNC:67890",
  "approved_symbol": "PKD1",
  "chromosome": "16",
  "location": "16p13.3",
  "record_hash": "a1b2c3d4e5f6789...",
  "details": {
    "gene_type": "protein_coding",
    "aliases": ["PC1", "APKD1"],
    "function": "Encodes polycystin-1 protein"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

### GET /genes/{gene_id}
Get detailed gene information.

**Response** (200 OK):
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "hgnc_id": "HGNC:67890",
  "approved_symbol": "PKD1",
  "previous_symbols": ["PKD"],
  "alias_symbols": ["PC1", "APKD1"],
  "chromosome": "16",
  "location": "16p13.3",
  "record_hash": "a1b2c3d4e5f6789...",
  "details": {
    "gene_type": "protein_coding",
    "function": "Encodes polycystin-1 protein",
    "constraint_metrics": {
      "pLI": 0.999,
      "oe_lof": 0.04
    }
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000",
  "creator": {
    "name": "Dr. Jane Curator",
    "email": "curator@example.org"
  }
}
```

### GET /genes/summary
Get minimal gene information for dropdowns and selection lists.

**Response** (200 OK):
```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "hgnc_id": "HGNC:67890",
    "approved_symbol": "PKD1",
    "chromosome": "16"
  }
]
```

## Scope Management Endpoints

### GET /scopes
List available clinical specialty scopes.

**Query Parameters**:
- `skip` (int, default=0): Number of records to skip
- `limit` (int, default=50, max=500): Number of records to return
- `institution` (string): Filter by institution
- `is_active` (boolean): Filter by active status

**Response** (200 OK):
```json
{
  "scopes": [
    {
      "id": "123e4567-e89b-12d3-a456-scope001",
      "name": "kidney-genetics",
      "display_name": "Kidney Genetics",
      "description": "Curation of kidney disease genes",
      "institution": "University Hospital",
      "is_active": true,
      "default_workflow_pair": {
        "id": "pair-123-456",
        "name": "ClinGen_Complete"
      },
      "gene_count": 45,
      "active_curation_count": 12,
      "curator_count": 8,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "123e4567-e89b-12d3-a456-scope002", 
      "name": "cardio-genetics",
      "display_name": "Cardio Genetics",
      "description": "Cardiovascular disease gene curation",
      "institution": null,
      "is_active": true,
      "default_workflow_pair": {
        "id": "pair-789-012",
        "name": "GenCC_Complete"
      },
      "gene_count": 67,
      "active_curation_count": 23,
      "curator_count": 12,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 50
}
```

### POST /scopes
Create a new clinical specialty scope (Admin only).

**Request Body**:
```json
{
  "name": "neuro-genetics",
  "display_name": "Neuro Genetics",
  "description": "Neurological disease gene curation",
  "institution": "Research Institute",
  "default_workflow_pair_id": "pair-345-678"
}
```

**Response** (201 Created):
```json
{
  "id": "123e4567-e89b-12d3-a456-scope003",
  "name": "neuro-genetics",
  "display_name": "Neuro Genetics", 
  "description": "Neurological disease gene curation",
  "institution": "Research Institute",
  "is_active": true,
  "default_workflow_pair": {
    "id": "pair-345-678",
    "name": "Custom_Complete"
  },
  "gene_count": 0,
  "active_curation_count": 0,
  "curator_count": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "created_by": "admin123-456"
}
```

### GET /scopes/{scope_id}
Get detailed scope information including statistics.

**Response** (200 OK):
```json
{
  "id": "123e4567-e89b-12d3-a456-scope001",
  "name": "kidney-genetics",
  "display_name": "Kidney Genetics",
  "description": "Curation of kidney disease genes",
  "institution": "University Hospital",
  "is_active": true,
  "default_workflow_pair": {
    "id": "pair-123-456",
    "name": "ClinGen_Complete",
    "version": "1.0.0"
  },
  "statistics": {
    "gene_count": 45,
    "active_curation_count": 12,
    "total_precuration_count": 67,
    "total_curation_count": 89,
    "pending_review_count": 5,
    "curator_count": 8,
    "avg_review_time_days": 8.5
  },
  "assigned_curators": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Dr. Jane Curator",
      "email": "curator@example.org",
      "active_curations": 3
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "created_by": "admin123-456"
}
```

### POST /scopes/{scope_id}/assign-curator
Assign a curator to a scope.

**Request Body**:
```json
{
  "user_id": "456e7890-e89b-12d3-a456-426614174001"
}
```

**Response** (200 OK):
```json
{
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "user_id": "456e7890-e89b-12d3-a456-426614174001",
  "assigned_at": "2024-01-15T10:30:00Z",
  "message": "Curator assigned to scope successfully"
}
```

## Gene-Scope Assignment Endpoints

### GET /gene-scope-assignments
List gene-scope assignments with filtering.

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `gene_id` (UUID): Filter by gene
- `scope_id` (UUID): Filter by scope
- `assigned_curator_id` (UUID): Filter by assigned curator
- `is_active` (boolean): Filter by active status

**Response** (200 OK):
```json
{
  "assignments": [
    {
      "id": "assignment-001",
      "gene_id": "456e7890-e89b-12d3-a456-426614174001",
      "scope_id": "123e4567-e89b-12d3-a456-scope001",
      "assigned_curator_id": "123e4567-e89b-12d3-a456-426614174000",
      "assigned_at": "2024-01-10T10:00:00Z",
      "assigned_by": "admin123-456",
      "is_active": true,
      "gene": {
        "approved_symbol": "PKD1",
        "hgnc_id": "HGNC:67890"
      },
      "scope": {
        "name": "kidney-genetics",
        "display_name": "Kidney Genetics"
      },
      "assigned_curator": {
        "name": "Dr. Jane Curator",
        "email": "curator@example.org"
      },
      "precuration_count": 2,
      "curation_count": 3,
      "active_curation": {
        "id": "active-curation-001",
        "verdict": "Definitive"
      }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### POST /gene-scope-assignments
Assign a gene to a scope with optional curator assignment.

**Request Body**:
```json
{
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "assigned_curator_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response** (201 Created):
```json
{
  "id": "assignment-002",
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "assigned_curator_id": "123e4567-e89b-12d3-a456-426614174000",
  "assigned_at": "2024-01-15T10:30:00Z",
  "assigned_by": "admin123-456",
  "is_active": true,
  "message": "Gene assigned to scope successfully"
}
```

### POST /gene-scope-assignments/bulk
Bulk assign multiple genes to a scope.

**Request Body**:
```json
{
  "gene_ids": ["gene-001", "gene-002", "gene-003"],
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "assigned_curator_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response** (201 Created):
```json
{
  "created_assignments": 3,
  "failed_assignments": 0,
  "assignments": [
    {
      "id": "assignment-003",
      "gene_id": "gene-001",
      "scope_id": "123e4567-e89b-12d3-a456-scope001"
    }
  ],
  "message": "Bulk assignment completed successfully"
}
```

## Pre-curation Endpoints

### GET /precurations
List precurations with scope-based filtering and pagination.

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `gene_id` (UUID): Filter by gene
- `scope_id` (UUID): Filter by scope
- `status` (enum): Filter by workflow status (draft|in_review|completed)
- `is_draft` (boolean): Filter by draft status
- `precuration_schema_id` (UUID): Filter by schema
- `created_by` (UUID): Filter by creator

**Response** (200 OK):
```json
{
  "precurations": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174002",
      "gene_id": "456e7890-e89b-12d3-a456-426614174001",
      "scope_id": "123e4567-e89b-12d3-a456-scope001",
      "precuration_schema_id": "schema-pre-123",
      "status": "completed",
      "is_draft": false,
      "evidence_data": {
        "initial_assessment": {
          "mondo_id": "MONDO:0002113",
          "mode_of_inheritance": "Autosomal Dominant",
          "lumping_splitting_decision": "Lump"
        }
      },
      "auto_saved_at": null,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z",
      "gene": {
        "approved_symbol": "PKD1",
        "hgnc_id": "HGNC:67890"
      },
      "scope": {
        "name": "kidney-genetics",
        "display_name": "Kidney Genetics"
      },
      "schema": {
        "name": "ClinGen_Precuration",
        "version": "1.0.0"
      },
      "creator": {
        "name": "Dr. Jane Curator"
      }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50,
  "scope_breakdown": {
    "kidney-genetics": 1
  }
}
```

### POST /precurations
Create a new precuration within a scope.

**Request Body**:
```json
{
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "precuration_schema_id": "schema-pre-123",
  "evidence_data": {
    "initial_assessment": {
      "mondo_id": "MONDO:0002113",
      "mode_of_inheritance": "Autosomal Dominant",
      "lumping_splitting_decision": "Lump",
      "rationale": "PKD1 variants cause a spectrum of polycystic kidney disease manifestations that represent a single genetic entity with variable expressivity rather than distinct conditions."
    },
    "literature_review": {
      "supporting_pmids": ["12345678", "87654321"],
      "phenotype_spectrum": "Polycystic kidney disease with variable age of onset",
      "confidence_level": "High"
    }
  },
  "is_draft": true
}
```

**Response** (201 Created):
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174002",
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "precuration_schema_id": "schema-pre-123",
  "status": "draft",
  "is_draft": true,
  "evidence_data": {
    "initial_assessment": {
      "mondo_id": "MONDO:0002113",
      "mode_of_inheritance": "Autosomal Dominant",
      "lumping_splitting_decision": "Lump",
      "rationale": "PKD1 variants cause a spectrum of polycystic kidney disease..."
    },
    "literature_review": {
      "supporting_pmids": ["12345678", "87654321"],
      "phenotype_spectrum": "Polycystic kidney disease with variable age of onset",
      "confidence_level": "High"
    }
  },
  "record_hash": "x1y2z3a4b5c6789...",
  "auto_saved_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000",
  "gene": {
    "approved_symbol": "PKD1",
    "hgnc_id": "HGNC:67890"
  },
  "scope": {
    "name": "kidney-genetics",
    "display_name": "Kidney Genetics"
  }
}
```

### PUT /precurations/{precuration_id}
Update precuration evidence data with auto-save support.

**Request Body**:
```json
{
  "evidence_data": {
    "initial_assessment": {
      "mondo_id": "MONDO:0002113",
      "mode_of_inheritance": "Autosomal Dominant",
      "lumping_splitting_decision": "Lump",
      "rationale": "Updated rationale text..."
    }
  },
  "is_draft": true,
  "auto_save": true
}
```

**Response** (200 OK):
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174002",
  "status": "draft",
  "is_draft": true,
  "auto_saved_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "message": "Precuration auto-saved successfully"
}
```

### POST /precurations/{precuration_id}/complete
Complete precuration and make it available for curation.

**Request Body**:
```json
{
  "final_review_comments": "Precuration complete, ready for curation stage"
}
```

**Response** (200 OK):
```json
{
  "id": "789e0123-e89b-12d3-a456-426614174002",
  "status": "completed",
  "is_draft": false,
  "completed_at": "2024-01-15T10:40:00Z",
  "message": "Precuration completed successfully"
}
```

### GET /precurations/{precuration_id}/curations
List curations that reference this precuration.

**Response** (200 OK):
```json
{
  "precuration_id": "789e0123-e89b-12d3-a456-426614174002",
  "curations": [
    {
      "id": "curation-001",
      "status": "draft",
      "is_draft": true,
      "computed_verdict": null,
      "created_at": "2024-01-15T11:00:00Z",
      "creator": {
        "name": "Dr. Jane Curator"
      }
    },
    {
      "id": "curation-002", 
      "status": "pending_review",
      "is_draft": false,
      "computed_verdict": "Definitive",
      "review": {
        "status": "pending",
        "reviewer": {
          "name": "Dr. Review Curator"
        }
      },
      "created_at": "2024-01-16T09:00:00Z"
    }
  ],
  "total_curations": 2,
  "active_curation": {
    "id": "curation-003",
    "verdict": "Strong",
    "activated_at": "2024-01-14T15:00:00Z"
  }
}
```

## Curation Endpoints

### GET /curations
List curations with scope-based filtering and multi-stage workflow information.

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `gene_id` (UUID): Filter by gene
- `scope_id` (UUID): Filter by scope
- `precuration_id` (UUID): Filter by precuration reference
- `status` (enum): Filter by workflow status (draft|pending_review|completed)
- `is_draft` (boolean): Filter by draft status
- `computed_verdict` (string): Filter by computed verdict
- `curation_schema_id` (UUID): Filter by schema
- `created_by` (UUID): Filter by creator

**Response** (200 OK):
```json
{
  "curations": [
    {
      "id": "abc1234-e89b-12d3-a456-426614174003",
      "gene_id": "456e7890-e89b-12d3-a456-426614174001",
      "scope_id": "123e4567-e89b-12d3-a456-scope001",
      "precuration_id": "789e0123-e89b-12d3-a456-426614174002",
      "curation_schema_id": "schema-cur-123",
      "status": "pending_review",
      "is_draft": false,
      "computed_verdict": "Definitive",
      "computed_scores": {
        "genetic_evidence_score": 12.0,
        "experimental_evidence_score": 4.5,
        "total_score": 16.5
      },
      "auto_saved_at": null,
      "created_at": "2024-01-15T11:00:00Z",
      "updated_at": "2024-01-15T12:00:00Z",
      "gene": {
        "approved_symbol": "PKD1",
        "hgnc_id": "HGNC:67890"
      },
      "scope": {
        "name": "kidney-genetics",
        "display_name": "Kidney Genetics"
      },
      "precuration": {
        "mondo_id": "MONDO:0002113",
        "lumping_splitting_decision": "Lump"
      },
      "schema": {
        "name": "ClinGen_SOP_v11",
        "version": "1.0.0",
        "scoring_engine": "clingen_sop_v11"
      },
      "review": {
        "id": "review-001",
        "status": "pending",
        "reviewer": {
          "name": "Dr. Review Curator"
        }
      },
      "creator": {
        "name": "Dr. Jane Curator"
      }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50,
  "scope_breakdown": {
    "kidney-genetics": 1
  },
  "status_breakdown": {
    "draft": 0,
    "pending_review": 1,
    "completed": 0
  }
}
```

### POST /curations
Create a new curation referencing a completed precuration.

**Request Body**:
```json
{
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "precuration_id": "789e0123-e89b-12d3-a456-426614174002",
  "curation_schema_id": "schema-cur-123",
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "12345678",
          "proband_label": "Smith et al, Family 1",
          "variant_type": "Predicted or Proven Null",
          "points": 1.5,
          "rationale": "Truncating variant with functional validation"
        }
      ]
    },
    "experimental_evidence": {
      "models": [
        {
          "type": "Non-human model organism",
          "pmid": "11223344",
          "organism": "Mus musculus",
          "points": 2.0,
          "rationale": "Mouse model recapitulates human disease"
        }
      ]
    }
  },
  "is_draft": true
}
```

**Response** (201 Created):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "scope_id": "123e4567-e89b-12d3-a456-scope001",
  "precuration_id": "789e0123-e89b-12d3-a456-426614174002",
  "curation_schema_id": "schema-cur-123",
  "status": "draft",
  "is_draft": true,
  "computed_verdict": "Limited",
  "computed_scores": {
    "genetic_evidence_score": 1.5,
    "experimental_evidence_score": 2.0,
    "total_score": 3.5
  },
  "computed_summary": "ClinGen SOP v11: Genetic=1.5, Experimental=2.0, Total=3.5 → Limited",
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [...]
    },
    "experimental_evidence": {
      "models": [...]
    }
  },
  "record_hash": "p1q2r3s4t5u6789...",
  "auto_saved_at": "2024-01-15T11:00:00Z",
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

### PUT /curations/{curation_id}
Update curation evidence data with auto-save support.

**Request Body**:
```json
{
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "12345678",
          "proband_label": "Smith et al, Family 1",
          "variant_type": "Predicted or Proven Null",
          "points": 2.0,
          "rationale": "Updated evidence with higher confidence"
        }
      ]
    }
  },
  "is_draft": true,
  "auto_save": true
}
```

**Response** (200 OK):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "status": "draft",
  "is_draft": true,
  "computed_verdict": "Limited",
  "computed_scores": {
    "genetic_evidence_score": 2.0,
    "experimental_evidence_score": 2.0,
    "total_score": 4.0
  },
  "auto_saved_at": "2024-01-15T11:30:00Z",
  "updated_at": "2024-01-15T11:30:00Z",
  "message": "Curation auto-saved successfully"
}
```

### POST /curations/{curation_id}/submit-for-review
Submit curation for 4-eyes principle review.

**Request Body**:
```json
{
  "reviewer_id": "456e7890-e89b-12d3-a456-426614174001",
  "submission_comments": "Curation complete, ready for review"
}
```

**Response** (200 OK):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "status": "pending_review",
  "is_draft": false,
  "submitted_at": "2024-01-15T12:00:00Z",
  "review": {
    "id": "review-001",
    "status": "pending",
    "reviewer_id": "456e7890-e89b-12d3-a456-426614174001",
    "reviewer": {
      "name": "Dr. Review Curator",
      "email": "reviewer@example.org"
    },
    "created_at": "2024-01-15T12:00:00Z"
  },
  "message": "Curation submitted for review"
}
```

## Review Endpoints (4-Eyes Principle)

### GET /reviews
List pending and completed reviews.

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `reviewer_id` (UUID): Filter by reviewer
- `scope_id` (UUID): Filter by scope
- `status` (enum): Filter by review status (pending|approved|rejected|needs_revision)
- `created_after` (datetime): Filter by creation date

**Response** (200 OK):
```json
{
  "reviews": [
    {
      "id": "review-001",
      "curation_id": "abc1234-e89b-12d3-a456-426614174003",
      "reviewer_id": "456e7890-e89b-12d3-a456-426614174001",
      "status": "pending",
      "review_comments": null,
      "reviewed_at": null,
      "review_duration_minutes": null,
      "created_at": "2024-01-15T12:00:00Z",
      "curation": {
        "gene": {
          "approved_symbol": "PKD1"
        },
        "scope": {
          "name": "kidney-genetics"
        },
        "computed_verdict": "Definitive",
        "creator": {
          "name": "Dr. Jane Curator"
        }
      },
      "reviewer": {
        "name": "Dr. Review Curator",
        "email": "reviewer@example.org"
      }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50,
  "status_breakdown": {
    "pending": 1,
    "approved": 0,
    "rejected": 0,
    "needs_revision": 0
  }
}
```

### POST /reviews/{review_id}/approve
Approve a curation (4-eyes principle).

**Request Body**:
```json
{
  "review_comments": "Curation approved. Evidence is comprehensive and scoring is accurate.",
  "activate_immediately": true
}
```

**Response** (200 OK):
```json
{
  "id": "review-001",
  "status": "approved",
  "review_comments": "Curation approved. Evidence is comprehensive and scoring is accurate.",
  "reviewed_at": "2024-01-15T15:00:00Z",
  "review_duration_minutes": 180,
  "curation": {
    "id": "abc1234-e89b-12d3-a456-426614174003",
    "status": "completed",
    "is_active": true
  },
  "active_curation": {
    "id": "active-001",
    "activated_at": "2024-01-15T15:00:00Z",
    "activated_by": "456e7890-e89b-12d3-a456-426614174001"
  },
  "message": "Review approved and curation activated"
}
```

### POST /reviews/{review_id}/reject
Reject a curation with feedback.

**Request Body**:
```json
{
  "review_comments": "Evidence insufficient. Please add more case-level data and experimental validation.",
  "return_to_draft": true
}
```

**Response** (200 OK):
```json
{
  "id": "review-001",
  "status": "rejected",
  "review_comments": "Evidence insufficient. Please add more case-level data and experimental validation.",
  "reviewed_at": "2024-01-15T14:30:00Z",
  "review_duration_minutes": 90,
  "curation": {
    "id": "abc1234-e89b-12d3-a456-426614174003",
    "status": "draft",
    "is_draft": true
  },
  "message": "Review rejected, curation returned to draft"
}
```

### POST /reviews/{review_id}/request-revision
Request revisions to a curation.

**Request Body**:
```json
{
  "review_comments": "Good start, but please clarify the LOD score calculation and add functional evidence.",
  "revision_requests": [
    "Add functional evidence for the truncating variant",
    "Clarify LOD score calculation methodology",
    "Include additional segregation data if available"
  ]
}
```

**Response** (200 OK):
```json
{
  "id": "review-001",
  "status": "needs_revision",
  "review_comments": "Good start, but please clarify the LOD score calculation and add functional evidence.",
  "revision_requests": [
    "Add functional evidence for the truncating variant",
    "Clarify LOD score calculation methodology",
    "Include additional segregation data if available"
  ],
  "reviewed_at": "2024-01-15T14:15:00Z",
  "review_duration_minutes": 75,
  "curation": {
    "id": "abc1234-e89b-12d3-a456-426614174003",
    "status": "needs_revision"
  },
  "message": "Revision requested"
}
```

## Active Curation Management Endpoints

### GET /active-curations
List active curations by scope.

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `scope_id` (UUID): Filter by scope
- `gene_id` (UUID): Filter by gene
- `computed_verdict` (string): Filter by verdict
- `activated_after` (datetime): Filter by activation date

**Response** (200 OK):
```json
{
  "active_curations": [
    {
      "id": "active-001",
      "gene_id": "456e7890-e89b-12d3-a456-426614174001",
      "scope_id": "123e4567-e89b-12d3-a456-scope001",
      "curation_id": "abc1234-e89b-12d3-a456-426614174003",
      "activated_at": "2024-01-15T15:00:00Z",
      "activated_by": "456e7890-e89b-12d3-a456-426614174001",
      "replaced_curation_id": "previous-curation-001",
      "gene": {
        "approved_symbol": "PKD1",
        "hgnc_id": "HGNC:67890"
      },
      "scope": {
        "name": "kidney-genetics",
        "display_name": "Kidney Genetics"
      },
      "curation": {
        "computed_verdict": "Definitive",
        "computed_scores": {
          "total_score": 16.5
        },
        "schema": {
          "name": "ClinGen_SOP_v11"
        },
        "creator": {
          "name": "Dr. Jane Curator"
        }
      },
      "activator": {
        "name": "Dr. Review Curator"
      }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50,
  "scope_breakdown": {
    "kidney-genetics": 1
  }
}
```

### POST /active-curations/{active_curation_id}/replace
Replace active curation with a newer approved curation.

**Request Body**:
```json
{
  "new_curation_id": "new-curation-001",
  "replacement_reason": "Updated evidence with stronger classification"
}
```

**Response** (200 OK):
```json
{
  "previous_active": {
    "id": "active-001",
    "curation_id": "abc1234-e89b-12d3-a456-426614174003",
    "archived_at": "2024-01-16T10:00:00Z"
  },
  "new_active": {
    "id": "active-002",
    "curation_id": "new-curation-001",
    "activated_at": "2024-01-16T10:00:00Z",
    "activated_by": "456e7890-e89b-12d3-a456-426614174001"
  },
  "message": "Active curation replaced successfully"
}
```

## Schema Management Endpoints

### GET /schemas
List available curation schemas with filtering.

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `schema_type` (enum): Filter by type (precuration|curation|combined)
- `institution` (string): Filter by institution
- `is_active` (boolean): Filter by active status
- `search` (string): Search schema names and descriptions

**Response** (200 OK):
```json
{
  "schemas": [
    {
      "id": "schema-123-456",
      "name": "ClinGen_SOP_v11",
      "version": "1.0.0",
      "schema_type": "curation",
      "description": "ClinGen Standard Operating Procedure v11 for Gene-Disease Validity",
      "institution": null,
      "created_by": "system",
      "created_at": "2024-01-01T00:00:00Z",
      "is_active": true,
      "usage_count": 150
    },
    {
      "id": "schema-789-012",
      "name": "GenCC_Classification",
      "version": "1.0.0",
      "schema_type": "curation",
      "description": "GenCC-based gene-disease classification",
      "institution": null,
      "created_at": "2024-01-01T00:00:00Z",
      "is_active": true,
      "usage_count": 45
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 50
}
```

### POST /schemas
Create a new curation schema (Admin only).

**Request Body**:
```json
{
  "name": "Custom_Institutional",
  "version": "1.0.0",
  "schema_type": "curation",
  "description": "Custom institutional methodology",
  "institution": "University Hospital",
  "field_definitions": {
    "clinical_assessment": {
      "type": "object",
      "properties": {
        "phenotype_match": {
          "type": "enum",
          "options": ["Excellent", "Good", "Fair", "Poor"],
          "ui_component": "select",
          "required": true
        },
        "inheritance_consistency": {
          "type": "enum",
          "options": ["Consistent", "Partially Consistent", "Inconsistent"],
          "ui_component": "select",
          "required": true
        }
      }
    }
  },
  "validation_rules": {
    "required_fields": ["clinical_assessment"],
    "field_validation": {
      "clinical_assessment.phenotype_match": {
        "type": "enum_validation",
        "allowed_values": ["Excellent", "Good", "Fair", "Poor"]
      }
    }
  },
  "scoring_configuration": {
    "engine": "qualitative_assessment",
    "verdicts": {
      "Strong Association": {"min_score": 8},
      "Moderate Association": {"min_score": 5},
      "Weak Association": {"min_score": 2},
      "Insufficient Evidence": {"max_score": 1}
    }
  },
  "workflow_states": {
    "states": ["Draft", "Internal_Review", "Final_Review", "Approved", "Published"],
    "transitions": {
      "Draft": ["Internal_Review"],
      "Internal_Review": ["Draft", "Final_Review"],
      "Final_Review": ["Internal_Review", "Approved"],
      "Approved": ["Published"]
    }
  },
  "ui_configuration": {
    "layout": "two_column",
    "color_scheme": "blue",
    "form_sections": [
      {
        "title": "Clinical Assessment",
        "fields": ["clinical_assessment.phenotype_match", "clinical_assessment.inheritance_consistency"]
      }
    ]
  }
}
```

**Response** (201 Created):
```json
{
  "id": "schema-345-678",
  "name": "Custom_Institutional",
  "version": "1.0.0",
  "schema_type": "curation",
  "description": "Custom institutional methodology",
  "institution": "University Hospital",
  "created_by": "admin123-456",
  "created_at": "2024-01-15T10:30:00Z",
  "is_active": true,
  "message": "Schema created successfully"
}
```

### GET /schemas/{schema_id}
Get complete schema definition.

**Response** (200 OK):
```json
{
  "id": "schema-123-456",
  "name": "ClinGen_SOP_v11",
  "version": "1.0.0",
  "schema_type": "curation",
  "description": "ClinGen Standard Operating Procedure v11 for Gene-Disease Validity",
  "institution": null,
  "field_definitions": {
    "genetic_evidence": {
      "type": "object",
      "properties": {
        "case_level_data": {
          "type": "array",
          "ui_component": "EvidenceTable",
          "item_schema": {
            "pmid": {"type": "string", "required": true, "validation": "pmid_format"},
            "proband_label": {"type": "string", "required": true},
            "variant_type": {"type": "enum", "options": ["Null", "Missense"]},
            "points": {"type": "number", "min": 0, "max": 2}
          }
        }
      }
    }
  },
  "validation_rules": {
    "required_fields": ["genetic_evidence"],
    "field_validation": {
      "genetic_evidence.case_level_data.*.pmid": {
        "type": "regex",
        "pattern": "^[0-9]{7,8}$"
      }
    }
  },
  "scoring_configuration": {
    "engine": "clingen_sop_v11",
    "max_genetic_score": 12,
    "max_experimental_score": 6,
    "verdicts": {
      "Definitive": {"min_score": 12, "no_contradictory": true},
      "Strong": {"min_score": 7, "max_score": 11},
      "Moderate": {"min_score": 4, "max_score": 6},
      "Limited": {"min_score": 1, "max_score": 3},
      "No Known Disease Relationship": {"score": 0}
    }
  },
  "workflow_states": {
    "states": ["Draft", "In_Primary_Review", "In_Secondary_Review", "Approved", "Published"],
    "transitions": {
      "Draft": ["In_Primary_Review"],
      "In_Primary_Review": ["Draft", "In_Secondary_Review"],
      "In_Secondary_Review": ["In_Primary_Review", "Approved"],
      "Approved": ["Published"]
    }
  },
  "ui_configuration": {
    "layout": "tabbed",
    "color_scheme": "clingen_blue",
    "form_sections": [
      {
        "title": "Genetic Evidence",
        "tab": "genetic",
        "fields": ["genetic_evidence"]
      }
    ]
  },
  "created_by": "system",
  "created_at": "2024-01-01T00:00:00Z",
  "is_active": true
}
```

### GET /workflow-pairs
List available workflow pairs (precuration + curation schema combinations).

**Query Parameters**:
- `skip`, `limit`: Pagination controls
- `institution` (string): Filter by institution
- `is_active` (boolean): Filter by active status

**Response** (200 OK):
```json
{
  "workflow_pairs": [
    {
      "id": "pair-123-456",
      "name": "ClinGen_Complete",
      "version": "1.0.0",
      "description": "Complete ClinGen workflow (precuration + curation)",
      "precuration_schema": {
        "id": "schema-pre-123",
        "name": "ClinGen_Precuration",
        "version": "1.0.0"
      },
      "curation_schema": {
        "id": "schema-cur-123",
        "name": "ClinGen_SOP_v11",
        "version": "1.0.0"
      },
      "data_mapping": {
        "field_mappings": {
          "mondo_id": "disease_identifier",
          "mode_of_inheritance": "inheritance_pattern"
        }
      },
      "institution": null,
      "created_at": "2024-01-01T00:00:00Z",
      "is_active": true
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### POST /workflow-pairs
Create a new workflow pair (Admin only).

**Request Body**:
```json
{
  "name": "GenCC_Complete",
  "version": "1.0.0",
  "description": "GenCC-based workflow pair",
  "precuration_schema_id": "schema-pre-456",
  "curation_schema_id": "schema-cur-456",
  "data_mapping": {
    "field_mappings": {
      "disease_name": "phenotype_label",
      "inheritance_mode": "inheritance_pattern"
    }
  },
  "institution": "GenCC Consortium"
}
```

### GET /users/me/default-schemas
Get user's default schema preferences.

**Response** (200 OK):
```json
{
  "default_workflow_pair": {
    "id": "pair-123-456",
    "name": "ClinGen_Complete",
    "version": "1.0.0"
  },
  "institution": "University Hospital",
  "preferences": {
    "auto_calculate_scores": true,
    "show_score_breakdown": true,
    "preferred_ui_layout": "tabbed"
  }
}
```

### POST /users/me/default-schemas
Set user's default schema preferences.

**Request Body**:
```json
{
  "workflow_pair_id": "pair-789-012",
  "preferences": {
    "auto_calculate_scores": true,
    "show_score_breakdown": false,
    "preferred_ui_layout": "single_page"
  }
}
```

## Scoring Engine Endpoints

### GET /scoring/engines
List available scoring engines.

**Response** (200 OK):
```json
{
  "engines": [
    {
      "name": "clingen_sop_v11",
      "version": "1.0.0",
      "description": "ClinGen Standard Operating Procedure v11 scoring",
      "supported_schemas": ["ClinGen_SOP_v11"],
      "verdicts": ["Definitive", "Strong", "Moderate", "Limited", "No Known Disease Relationship", "Disputed"]
    },
    {
      "name": "gencc_based",
      "version": "1.0.0",
      "description": "GenCC-based confidence scoring",
      "supported_schemas": ["GenCC_Classification"],
      "verdicts": ["Definitive", "Strong", "Moderate", "Limited"]
    },
    {
      "name": "qualitative_assessment",
      "version": "1.0.0",
      "description": "Qualitative institutional assessment",
      "supported_schemas": ["Custom_Institutional"],
      "verdicts": ["Strong Association", "Moderate Association", "Weak Association", "Insufficient Evidence"]
    }
  ]
}
```

### POST /scoring/calculate
Calculate scores using specified engine.

**Request Body**:
```json
{
  "engine_name": "clingen_sop_v11",
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "12345678",
          "proband_label": "Family 1",
          "variant_type": "Null",
          "points": 2.0
        }
      ]
    },
    "experimental_evidence": {
      "function": [
        {
          "pmid": "87654321",
          "type": "Biochemical",
          "points": 1.0
        }
      ]
    }
  },
  "schema_config": {
    "engine": "clingen_sop_v11",
    "max_genetic_score": 12,
    "max_experimental_score": 6
  }
}
```

**Response** (200 OK):
```json
{
  "engine_name": "clingen_sop_v11",
  "engine_version": "1.0.0",
  "result": {
    "scores": {
      "genetic_evidence_score": 2.0,
      "experimental_evidence_score": 1.0,
      "total_score": 3.0
    },
    "total_score": 3.0,
    "verdict": "Limited",
    "verdict_rationale": "Based on ClinGen SOP v11 scoring: genetic evidence score = 2.0, experimental evidence score = 1.0, total score = 3.0. Total score 1-3 supports Limited classification.",
    "evidence_breakdown": {
      "genetic_evidence": {
        "total_score": 2.0,
        "case_level_items": 1,
        "segregation_items": 0,
        "case_control_items": 0
      },
      "experimental_evidence": {
        "total_score": 1.0,
        "function_items": 1,
        "model_items": 0,
        "rescue_items": 0
      }
    },
    "warnings": [
      "Only 1 case-level evidence items (consider adding more)"
    ],
    "metadata": {
      "sop_version": "v11",
      "engine_version": "1.0.0",
      "calculated_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

### POST /scoring/validate
Validate evidence data against schema and scoring engine.

**Request Body**:
```json
{
  "engine_name": "clingen_sop_v11",
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "invalid",
          "points": 5.0
        }
      ]
    }
  },
  "schema_config": {
    "engine": "clingen_sop_v11"
  }
}
```

**Response** (200 OK):
```json
{
  "is_valid": false,
  "errors": [
    "Case-level item 1: Invalid PMID format",
    "Case-level item 1: Points must be 0-2",
    "Case-level item 1: Proband label required"
  ],
  "warnings": [
    "No experimental evidence provided"
  ]
}
```

## Dynamic Curation Endpoints

### GET /curations
List curations with multi-methodology filtering.

**Query Parameters**:
- Standard pagination: `skip`, `limit`
- `gene_id` (UUID): Filter by gene
- `workflow_pair_id` (UUID): Filter by methodology
- `computed_verdict` (string): Filter by any verdict/classification
- `current_status` (string): Filter by workflow status  
- `institution` (string): Filter by institution
- `scoring_engine` (string): Filter by scoring engine used
- `min_total_score` (float): Minimum evidence score
- `max_total_score` (float): Maximum evidence score
- `created_after` (datetime): Filter by creation date
- `search` (string): Search gene symbols and disease names

**Response** (200 OK):
```json
{
  "curations": [
    {
      "id": "abc1234-e89b-12d3-a456-426614174003",
      "gene_id": "456e7890-e89b-12d3-a456-426614174001",
      "workflow_pair_id": "pair-123-456",
      "current_stage": "curation",
      "current_status": "Published",
      "computed_verdict": "Definitive",
      "computed_scores": {
        "genetic_evidence_score": 12.0,
        "experimental_evidence_score": 4.5,
        "total_score": 16.5
      },
      "created_at": "2024-01-05T10:30:00Z",
      "updated_at": "2024-01-12T09:00:00Z",
      "gene": {
        "approved_symbol": "PKD1",
        "hgnc_id": "HGNC:67890"
      },
      "workflow_pair": {
        "name": "ClinGen_Complete",
        "version": "1.0.0",
        "scoring_engine": "clingen_sop_v11"
      },
      "creator": {
        "name": "Dr. Jane Curator"
      }
    },
    {
      "id": "def5678-e89b-12d3-a456-426614174004",
      "gene_id": "789e0123-e89b-12d3-a456-426614174002",
      "workflow_pair_id": "pair-789-012",
      "current_stage": "curation",
      "current_status": "Draft",
      "computed_verdict": "Moderate Association",
      "computed_scores": {
        "clinical_assessment_score": 4.0,
        "literature_review_score": 3.0,
        "overall_score": 7.0
      },
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "gene": {
        "approved_symbol": "BRCA2",
        "hgnc_id": "HGNC:1101"
      },
      "workflow_pair": {
        "name": "GenCC_Complete",
        "version": "1.0.0",
        "scoring_engine": "gencc_based"
      },
      "creator": {
        "name": "Dr. GenCC Curator"
      }
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 50,
  "methodology_breakdown": {
    "ClinGen_Complete": 1,
    "GenCC_Complete": 1
  }
}
```

### POST /curations
Create a new curation with automatic schema-driven scoring.

**Request Body (ClinGen Example)**:
```json
{
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "workflow_pair_id": "pair-123-456",
  "precuration_data": {
    "mondo_id": "MONDO:0002113",
    "mode_of_inheritance": "Autosomal Dominant",
    "disease_name": "Polycystic kidney disease 1",
    "lumping_splitting_decision": "Lump"
  },
  "curation_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "12345678",
          "proband_label": "Smith et al, Family 1",
          "variant_type": "Predicted or Proven Null",
          "is_de_novo": false,
          "functional_evidence": "Protein truncation confirmed by Western blot",
          "points": 1.5,
          "rationale": "Truncating variant with functional validation"
        }
      ],
      "segregation_data": [
        {
          "pmid": "87654321",
          "family_label": "Large family study",
          "lod_score_published": 4.2,
          "points": 2.0,
          "rationale": "LOD score exceeds 3.0 threshold"
        }
      ]
    },
    "experimental_evidence": {
      "models": [
        {
          "type": "Non-human model organism",
          "pmid": "11223344",
          "organism": "Mus musculus",
          "description": "Pkd1 knockout mice develop polycystic kidneys",
          "points": 2.0,
          "rationale": "Mouse model recapitulates human disease"
        }
      ]
    }
  }
}
```

**Request Body (GenCC Example)**:
```json
{
  "gene_id": "789e0123-e89b-12d3-a456-426614174002",
  "workflow_pair_id": "pair-789-012",
  "curation_data": {
    "clinical_evidence": {
      "phenotype_overlap": "complete",
      "inheritance_pattern": "consistent",
      "population_data": 7.5
    },
    "literature_evidence": {
      "study_quality": "high",
      "evidence_strength": "strong",
      "supporting_studies": 15
    }
  }
}
```

**Request Body (Custom Institutional Example)**:
```json
{
  "gene_id": "345e6789-e89b-12d3-a456-426614174003",
  "workflow_pair_id": "pair-345-678",
  "curation_data": {
    "clinical_assessment": {
      "phenotype_match": "Excellent",
      "inheritance_consistency": "Consistent"
    },
    "literature_review": {
      "evidence_quality": "High",
      "study_design_strength": "Strong"
    },
    "expert_panel_review": {
      "consensus_reached": true,
      "confidence_level": 9.0
    }
  }
}
```

**Response** (201 Created):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "workflow_pair_id": "pair-123-456",
  "current_stage": "curation",
  "current_status": "Draft",
  "computed_verdict": "Limited",
  "computed_scores": {
    "genetic_evidence_score": 3.5,
    "experimental_evidence_score": 2.0,
    "total_score": 5.5
  },
  "computed_summary": "ClinGen SOP v11: Genetic=3.5, Experimental=2.0, Total=5.5 → Limited",
  "record_hash": "p1q2r3s4t5u6789...",
  "precuration_data": {
    "mondo_id": "MONDO:0002113",
    "mode_of_inheritance": "Autosomal Dominant",
    "disease_name": "Polycystic kidney disease 1",
    "lumping_splitting_decision": "Lump"
  },
  "curation_data": {
    "genetic_evidence": {
      "case_level_data": [...],
      "segregation_data": [...]
    },
    "experimental_evidence": {
      "models": [...]
    }
  },
  "workflow_pair": {
    "name": "ClinGen_Complete",
    "version": "1.0.0",
    "scoring_engine": "clingen_sop_v11"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

### GET /curations/{curation_id}
Get complete curation details with schema-aware data structure.

**Response** (200 OK):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "gene_id": "456e7890-e89b-12d3-a456-426614174001",
  "precuration_id": "789e0123-e89b-12d3-a456-426614174002",
  "mondo_id": "MONDO:0002113",
  "mode_of_inheritance": "Autosomal Dominant",
  "disease_name": "Polycystic kidney disease 1",
  "verdict": "Definitive",
  "genetic_evidence_score": 12.0,
  "experimental_evidence_score": 4.5,
  "total_score": 16.5,
  "has_contradictory_evidence": false,
  "summary_text": "PKD1 AND Polycystic kidney disease 1\n\nEXPERT PANEL: Kidney Disease GCEP...",
  "gcep_affiliation": "Kidney Disease GCEP",
  "sop_version": "v11",
  "status": "Published",
  "approved_at": "2024-01-10T15:00:00Z",
  "approved_by": "admin123-e89b-12d3-a456-426614174004",
  "published_at": "2024-01-12T09:00:00Z",
  "record_hash": "p1q2r3s4t5u6789...",
  "previous_hash": null,
  "details": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "12345678",
          "proband_label": "Smith et al, Family 1",
          "hpo_terms": ["HP:0000107", "HP:0000108"],
          "variant_type": "Predicted or Proven Null",
          "is_de_novo": false,
          "functional_evidence": "Protein truncation confirmed",
          "points": 1.5,
          "rationale": "Truncating variant with functional validation"
        }
      ],
      "segregation_data": [
        {
          "pmid": "87654321",
          "family_label": "Large family study",
          "sequencing_method": "Exome sequencing",
          "lod_score_published": 4.2,
          "points": 2.0,
          "rationale": "LOD score exceeds 3.0 threshold"
        }
      ]
    },
    "experimental_evidence": {
      "models": [
        {
          "type": "Non-human model organism",
          "pmid": "11223344",
          "organism": "Mus musculus",
          "description": "Pkd1 knockout mice develop polycystic kidneys",
          "phenotype_match": "Excellent",
          "points": 2.0,
          "rationale": "Mouse model recapitulates human disease"
        }
      ]
    },
    "curation_workflow": {
      "status": "Published",
      "review_log": [
        {
          "timestamp": "2024-01-05T10:30:00Z",
          "action": "created",
          "user": "curator@example.org",
          "comment": "Initial curation created"
        },
        {
          "timestamp": "2024-01-10T15:00:00Z",
          "action": "approved",
          "user": "admin@example.org",
          "comment": "Approved for publication"
        }
      ]
    }
  },
  "created_at": "2024-01-05T10:30:00Z",
  "updated_at": "2024-01-10T15:00:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000",
  "gene": {
    "approved_symbol": "PKD1",
    "hgnc_id": "HGNC:67890",
    "current_dyadic_name": "PKD1-associated polycystic kidney disease"
  },
  "precuration": {
    "lumping_splitting_decision": "Lump",
    "rationale": "Single genetic entity with variable expressivity"
  },
  "creator": {
    "name": "Dr. Jane Curator",
    "email": "curator@example.org"
  },
  "approver": {
    "name": "Dr. Admin User",
    "email": "admin@example.org"
  }
}
```

### POST /curations/{curation_id}/recalculate-scores
Recalculate scores using curation's schema-defined scoring engine.

**Response** (200 OK):
```json
{
  "engine_name": "clingen_sop_v11",
  "engine_version": "1.0.0",
  "result": {
    "scores": {
      "genetic_evidence_score": 12.0,
      "experimental_evidence_score": 4.5,
      "total_score": 16.5
    },
    "total_score": 16.5,
    "verdict": "Definitive",
    "verdict_rationale": "Based on ClinGen SOP v11 scoring: genetic evidence score = 12.0, experimental evidence score = 4.5, total score = 16.5. Total score ≥12 with no contradictory evidence supports Definitive classification.",
    "evidence_breakdown": {
      "genetic_evidence": {
        "total_score": 12.0,
        "case_level_items": 5,
        "segregation_items": 2,
        "case_control_items": 1
      },
      "experimental_evidence": {
        "total_score": 4.5,
        "function_items": 2,
        "model_items": 1,
        "rescue_items": 1
      }
    },
    "warnings": [],
    "metadata": {
      "sop_version": "v11",
      "calculated_at": "2024-01-15T10:45:00Z"
    }
  },
  "updated_at": "2024-01-15T10:45:00Z"
}
```

### GET /curations/{curation_id}/summary
Generate methodology-specific evidence summary.

**Response** (200 OK):
```json
{
  "summary_text": "PKD1 AND Polycystic kidney disease 1\n\nSCORING ENGINE: ClinGen SOP v11\nGENE-DISEASE RELATIONSHIP: Definitive\nINHERITANCE: Autosomal Dominant\nSCHEMA VERSION: 1.0.0\n\nGENETIC EVIDENCE (12.0 points):\nCase-level evidence includes 8 probands with qualifying variants (10.5 points). Segregation evidence from 2 studies (3.0 points).\n\nEXPERIMENTAL EVIDENCE (4.5 points):\nFunctional evidence demonstrates loss of polycystin-1 function (1.5 points). Model organism studies in mice recapitulate disease phenotype (2.0 points). Rescue evidence from gene therapy studies (1.0 points).\n\nTOTAL SCORE: 16.5 points\nCLASSIFICATION: Definitive",
  "methodology": "ClinGen_SOP_v11",
  "scoring_engine": "clingen_sop_v11",
  "template_version": "v5.1",
  "generated_at": "2024-01-15T10:45:00Z"
}
```

### POST /curations/validate-evidence
Validate evidence data against schema (standalone validation).

**Request Body**:
```json
{
  "workflow_pair_id": "pair-123-456",
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "invalid",
          "points": 5.0
        }
      ]
    }
  }
}
```

**Response** (200 OK):
```json
{
  "is_valid": false,
  "errors": [
    "Case-level item 1: Invalid PMID format",
    "Case-level item 1: Points must be 0-2",
    "Case-level item 1: Proband label required"
  ],
  "warnings": [
    "No experimental evidence provided"
  ],
  "schema_compliance": {
    "required_fields_present": false,
    "field_formats_valid": false,
    "scoring_rules_met": false
  },
  "methodology": "ClinGen_SOP_v11",
  "validated_at": "2024-01-15T10:45:00Z"
}
```

### POST /curations/preview-scores
Preview scoring results without creating a curation.

**Request Body**:
```json
{
  "workflow_pair_id": "pair-123-456",
  "evidence_data": {
    "genetic_evidence": {
      "case_level_data": [
        {
          "pmid": "12345678",
          "proband_label": "Test Family",
          "variant_type": "Null",
          "points": 2.0
        }
      ]
    }
  }
}
```

**Response** (200 OK):
```json
{
  "preview": true,
  "scoring_engine": "clingen_sop_v11",
  "scores": {
    "genetic_evidence_score": 2.0,
    "experimental_evidence_score": 0.0,
    "total_score": 2.0
  },
  "predicted_verdict": "Limited",
  "verdict_rationale": "Total score 1-3 supports Limited classification",
  "evidence_summary": {
    "case_level_items": 1,
    "segregation_items": 0,
    "experimental_items": 0
  },
  "recommendations": [
    "Consider adding segregation data for stronger evidence",
    "Experimental evidence would strengthen the case"
  ]
}
```

### POST /curations/{curation_id}/workflow-action
Advance curation through schema-defined workflow states.

**Request Body**:
```json
{
  "action": "submit_for_review",
  "comment": "Evidence collection complete, ready for review"
}
```

**Response** (200 OK):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "current_status": "In_Primary_Review",
  "previous_status": "Draft",
  "action_taken": "submit_for_review",
  "comment": "Evidence collection complete, ready for review",
  "timestamp": "2024-01-15T10:50:00Z",
  "workflow_schema": "ClinGen_SOP_v11",
  "available_actions": [
    {
      "action": "return_to_draft",
      "label": "Return to Draft",
      "requires_comment": true
    },
    {
      "action": "approve_for_secondary_review",
      "label": "Approve for Secondary Review",
      "requires_comment": false
    }
  ]
}
```

### POST /curations/{curation_id}/publish
Publish approved curation with methodology-specific formatting.

**Request Body**:
```json
{
  "publish_targets": ["gencc", "clinvar"],
  "comment": "Ready for public distribution"
}
```

**Response** (200 OK):
```json
{
  "id": "abc1234-e89b-12d3-a456-426614174003",
  "current_status": "Published",
  "published_at": "2024-01-15T10:55:00Z",
  "methodology": "ClinGen_SOP_v11",
  "publication_results": {
    "gencc": {
      "submitted": true,
      "submission_id": "GENCC_12345",
      "format": "ClinGen_standard"
    },
    "clinvar": {
      "submitted": true,
      "submission_id": "CV_67890",
      "format": "gene_disease_validity"
    }
  },
  "message": "Curation published successfully across all targets"
}
```

## User Management Endpoints

### GET /users
List users (Admin only).

**Query Parameters**:
- `skip`, `limit`: Pagination
- `role` (enum): Filter by user role
- `is_active` (boolean): Filter by active status

**Response** (200 OK):
```json
{
  "users": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "curator@example.org",
      "name": "Dr. Jane Curator",
      "role": "curator",
      "is_active": true,
      "last_login": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### PUT /users/{user_id}
Update user information (Admin only).

**Request Body**:
```json
{
  "name": "Dr. Jane Senior Curator",
  "role": "admin",
  "is_active": true
}
```

## Statistics and Analytics

### GET /statistics/overview
Get multi-methodology platform statistics.

**Response** (200 OK):
```json
{
  "total_genes": 1250,
  "total_scopes": 5,
  "total_schemas": 12,
  "active_workflow_pairs": 8,
  "total_precurations": 890,
  "total_curations": 420,
  "active_curations": 380,
  "pending_reviews": 25,
  "active_users": 45,
  "curations_by_scope": {
    "kidney-genetics": {
      "total_precurations": 245,
      "total_curations": 180,
      "active_curations": 165,
      "pending_reviews": 8,
      "avg_review_time_days": 7.2,
      "methodology_breakdown": {
        "ClinGen_SOP_v11": 160,
        "Custom_Institutional": 20
      },
      "verdict_distribution": {
        "Definitive": 85,
        "Strong": 60,
        "Moderate": 45,
        "Limited": 35
      }
    },
    "cardio-genetics": {
      "total_precurations": 356,
      "total_curations": 145,
      "active_curations": 130,
      "pending_reviews": 12,
      "avg_review_time_days": 9.1,
      "methodology_breakdown": {
        "ClinGen_SOP_v11": 100,
        "GenCC_Classification": 45
      },
      "verdict_distribution": {
        "Definitive": 45,
        "Strong": 40,
        "Moderate": 25,
        "Limited": 20
      }
    },
    "neuro-genetics": {
      "total_precurations": 289,
      "total_curations": 95,
      "active_curations": 85,
      "pending_reviews": 5,
      "avg_review_time_days": 6.8,
      "methodology_breakdown": {
        "ClinGen_SOP_v11": 60,
        "GenCC_Classification": 30,
        "Custom_Institutional": 5
      },
      "verdict_distribution": {
        "Definitive": 20,
        "Strong": 20,
        "Moderate": 15,
        "Limited": 30
      }
    }
  },
  "workflow_metrics": {
    "avg_precuration_time_days": 3.5,
    "avg_curation_time_days": 8.2,
    "avg_review_time_days": 7.8,
    "4_eyes_compliance_rate": 100.0,
    "draft_save_usage_rate": 95.3
  },
  "schema_usage": {
    "most_popular": "ClinGen_SOP_v11",
    "fastest_growing": "GenCC_Classification",
    "institutional_schemas": 3
  },
  "scoring_engines": {
    "clingen_sop_v11": 320,
    "gencc_based": 75,
    "qualitative_assessment": 25
  }
}
```

### GET /statistics/methodology/{methodology_name}
Get methodology-specific statistics.

**Response** (200 OK for ClinGen):
```json
{
  "methodology": "ClinGen_SOP_v11",
  "schema_version": "1.0.0",
  "scoring_engine": "clingen_sop_v11",
  "total_curations": 320,
  "published_curations": 295,
  "compliance_metrics": {
    "sop_compliance_rate": 98.5,
    "avg_review_time_days": 12.3,
    "evidence_quality_score": 94.8
  },
  "evidence_metrics": {
    "pmid_validation_rate": 99.2,
    "evidence_completeness": 94.8,
    "citation_accuracy": 97.1,
    "avg_genetic_score": 8.5,
    "avg_experimental_score": 3.2
  },
  "classification_distribution": {
    "Definitive": 150,
    "Strong": 120,
    "Moderate": 85,
    "Limited": 45,
    "No Known Disease Relationship": 15,
    "Disputed": 5
  },
  "workflow_metrics": {
    "avg_time_in_draft": 5.2,
    "avg_time_in_review": 7.1,
    "approval_rate": 92.1,
    "return_to_draft_rate": 15.3
  },
  "monthly_publication_rate": 28.5
}
```

**Response** (200 OK for GenCC):
```json
{
  "methodology": "GenCC_Classification",
  "schema_version": "1.0.0",
  "scoring_engine": "gencc_based",
  "total_curations": 75,
  "published_curations": 65,
  "confidence_metrics": {
    "avg_confidence_score": 6.8,
    "high_confidence_rate": 33.3,
    "validation_accuracy": 96.0
  },
  "evidence_metrics": {
    "phenotype_consistency_rate": 89.3,
    "inheritance_match_rate": 94.7,
    "population_data_availability": 78.7
  },
  "classification_distribution": {
    "Definitive": 25,
    "Strong": 20,
    "Moderate": 15,
    "Limited": 15
  },
  "workflow_metrics": {
    "avg_curation_time_days": 8.5,
    "consensus_rate": 87.5
  }
}
```

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789"
}
```

### Common HTTP Status Codes
- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

### Validation Error Details
```json
{
  "detail": [
    {
      "loc": ["body", "mondo_id"],
      "msg": "MONDO ID must be in format MONDO:#### where #### is a number",
      "type": "value_error",
      "ctx": {"pattern": "^MONDO:[0-9]+$"}
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

## Rate Limiting

**Limits**:
- Authenticated users: 1000 requests/hour
- Unauthenticated users: 100 requests/hour
- Admin users: 5000 requests/hour

**Headers**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642248000
```

## Pagination

**Standard Parameters**:
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Number of records to return (default: 50, max: 500)

**Response Format**:
```json
{
  "items": [...],
  "total": 1250,
  "skip": 0,
  "limit": 50,
  "has_next": true,
  "has_prev": false
}
```

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

## SDK Examples

### Python Client Example
```python
import httpx
from typing import Optional

class GeneCuratorClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url
        self.client = httpx.Client()
        if token:
            self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    async def login(self, email: str, password: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.client.headers.update({"Authorization": f"Bearer {data['access_token']}"})
        return data
    
    async def create_curation(self, curation_data: dict) -> dict:
        response = await self.client.post(
            f"{self.base_url}/curations",
            json=curation_data
        )
        response.raise_for_status()
        return response.json()
    
    async def get_curation(self, curation_id: str) -> dict:
        response = await self.client.get(
            f"{self.base_url}/curations/{curation_id}"
        )
        response.raise_for_status()
        return response.json()

# Usage
client = GeneCuratorClient("https://gene-curator.org/api/v1")
await client.login("curator@example.org", "password")
curation = await client.get_curation("abc1234-e89b-12d3-a456-426614174003")
```

### JavaScript Client Example
```javascript
class GeneCuratorAPI {
  constructor(baseURL, token = null) {
    this.baseURL = baseURL;
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    this.token = data.access_token;
    return data;
  }

  async getCurations(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/curations?${queryString}`);
  }

  async createCuration(curationData) {
    return this.request('/curations', {
      method: 'POST',
      body: JSON.stringify(curationData)
    });
  }
}

// Usage
const api = new GeneCuratorAPI('https://gene-curator.org/api/v1');
await api.login('curator@example.org', 'password');
const curations = await api.getCurations({ verdict: 'Definitive', limit: 10 });
```

---

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - Schema-agnostic system design
- [Database Schema](./DATABASE_SCHEMA.md) - Flexible database structure with JSONB storage
- [Workflow Documentation](./WORKFLOW.md) - Multi-methodology business processes
- [Frontend Guide](./FRONTEND_GUIDE.md) - Dynamic UI component integration
- [Schema Examples](./SCHEMA_EXAMPLES.md) - ClinGen, GenCC, and custom methodology examples
- [Scoring Engine Guide](../plan/SCORING_ENGINE_GUIDE.md) - Pluggable scoring system development