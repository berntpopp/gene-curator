# Gene Curator - Approved Enhancements Summary

## ✅ Phase 1: Core Curation Features (16-22 hours)

### 008 - Draft Auto-Save Frontend (4-6h)
- **File**: `008-draft-autosave-frontend.md`
- **Backend Status**: ✅ Ready (draft state in workflow)
- **Implementation**:
  - useAutoSave composable (auto-save every 30s + debounced)
  - CurationForm integration
  - DraftCurations list view
  - Before-unload warning
- **Value**: Prevents data loss, "save and continue later" workflow

### 009 - Dynamic Form Generation (8-10h)
- **File**: `009-dynamic-form-generation.md`
- **Backend Status**: ✅ Ready (schema validator, 12+ field types)
- **Implementation**:
  - 12+ field type components (TextField, EvidenceTable, etc.)
  - DynamicForm component (renders from schema)
  - Client-side validation from schema rules
  - CurationForm uses DynamicForm
- **Value**: **Core product differentiator** - schema-agnostic design

###010 - 4-Eyes Review Workflow (4-6h)
- **File**: `010-review-workflow-4eyes.md`
- **Backend Status**: ✅ Ready (reviews table, workflow transitions)
- **Implementation**:
  - ReviewQueue view (pending reviews)
  - CurationReview view (approve/reject/needs_revision)
  - Review notification badge
  - Workflow store integration
- **Value**: **Regulatory compliance** - mandatory for clinical curation

---

## ✅ Phase 2: Practical Infrastructure (8-12 hours)

### 003 - RetryUtils with Exponential Backoff (3-4h)
- **File**: `003-retry-utils-exponential-backoff.md`
- **Implementation**:
  - RetryConfig class
  - CircuitBreaker class
  - @retry_with_backoff decorator
  - RetryableHTTPClient wrapper
- **Value**: 95%+ success rate for external API calls (HGNC lookups)

### 004 - Expanded Makefile Workflow (2-3h)
- **File**: `004-expanded-makefile-workflow.md`
- **Implementation**:
  - Hybrid development mode (DB in Docker, API/Frontend local)
  - `make status` with real-time statistics
  - Comprehensive backup/restore commands
  - Production test mode
- **Value**: Instant developer productivity boost, zero risk

### 001 - Simple Structured Logging (2-3h)
- **File**: `001-simple-structured-logging.md`
- **Simplified**: ~100 lines (not 533 from kidney-genetics-db)
- **Implementation**:
  - StructuredFormatter with request correlation
  - get_logger() drop-in replacement
  - Request logging middleware
  - Console-only (no database persistence)
- **Value**: Better debugging without database overhead

### 006 - Simple API Configuration (1-2h)
- **File**: `006-simple-api-configuration.md`
- **Simplified**: ~150 lines (not 267 from kidney-genetics-db)
- **Implementation**:
  - backend/config/api.yaml (CORS, rate limits, timeouts)
  - Simple YAML loader with Pydantic validation
  - API-level configuration only (no workflow/schema duplication)
- **Value**: Deployment flexibility

---

## 🔴 Deferred (See `deferred/` folder)

### 002 - CacheService L1/L2 (DEFERRED)
- **Reason**: Write-heavy curation platform ≠ read-heavy API
- **Alternative**: Use `@lru_cache` for schemas/scopes (~20 lines)
- **Revisit When**: Public API with high read traffic (unlikely)

### 005 - Real-Time Progress Tracking (DEFERRED)
- **Reason**: No 30-minute batch operations exist
- **Alternative**: Defer until bulk operations confirmed
- **Revisit When**: Bulk imports, scope-wide recalculations implemented

### 007 - View Management with Topological Sort (DEFERRED)
- **Reason**: <5 views don't need topological sort
- **Alternative**: Manual view ordering in SQL
- **Revisit When**: >5 interdependent views exist

---

## Implementation Order

1. **Start with Phase 1** (Core Curation Features)
   - These are what curators actually use daily
   - Backend already ready, frontend implementation only
   - Highest business value

2. **Then Phase 2** (Practical Infrastructure)
   - Support development and operations
   - Can be implemented incrementally
   - No dependencies on Phase 1

3. **Skip Deferred** (Save 15-20 hours)
   - Premature optimization for Gene Curator's use case
   - Revisit only if needs change

---

## Total Effort Estimate

| Phase | Hours | Features |
|-------|-------|----------|
| Phase 1 | 16-22h | Draft auto-save + Dynamic forms + 4-eyes review |
| Phase 2 | 8-12h | RetryUtils + Makefile + Simple logging + Simple config |
| **Total** | **24-34h** | **7 enhancements** |
| Deferred | ~15-20h | 3 enhancements not needed for Gene Curator |

---

## Key Principle

**Gene Curator is an interactive curation tool, not a high-throughput data pipeline.**

Optimize for curator productivity (features they use), not infrastructure performance (sub-10ms API latency doesn't matter when curations take 5-10 minutes).
