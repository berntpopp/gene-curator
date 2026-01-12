# Frontend-Backend API Endpoint Alignment

**Status**: Analysis Complete - Ready for Implementation
**Created**: 2025-10-13
**Priority**: MEDIUM - Required for full dashboard functionality
**Type**: Architecture Alignment

## Executive Summary

This document addresses API contract mismatches between frontend components, Pinia stores, API modules, and FastAPI backend endpoints. These mismatches cause the CRITICAL errors documented in `005-error-handling-fixes-using-existing-systems.md`.

**Finding**: NO Firebase remnants found in codebase. All issues stem from frontend components being built ahead of backend API implementation.

## Investigation Results

### Firebase Search Results

```bash
grep -r "firebase" frontend/src --include="*.js" --include="*.vue" --include="*.ts"
# Result: NO MATCHES FOUND
```

**Conclusion**: User's concern about Firebase remnants is **not applicable**. All frontend code uses the FastAPI structure correctly. The issue is missing backend endpoints, not migration problems.

---

## Architecture Overview

Current data flow:
```
Component
   ↓ (calls)
Store (Pinia)
   ↓ (calls)
API Module (frontend/src/api/*.js)
   ↓ (HTTP via apiClient)
FastAPI Backend (backend/app/api/v1/endpoints/*.py)
```

**Problem**: Components expect store state/methods that don't exist, because backend endpoints don't exist yet.

---

## Mismatch Analysis by Feature

### 1. Validation Dashboard

#### Component Expectations
**File**: `frontend/src/views/ValidationDashboard.vue`

```javascript
// Lines 373-375: Component expects these computed properties
const stats = computed(() => validationStore.validationStats)
const validationResults = computed(() => validationStore.validationResults)
const commonIssues = computed(() => validationStore.commonIssues)

// Lines 494-496: Component expects these store methods
await validationStore.fetchValidationResults()
await validationStore.fetchValidationStats()
await validationStore.fetchCommonIssues()

// Line 462: Component expects this method
await validationStore.refreshAllValidations()

// Line 478: Component expects this method
await validationStore.revalidateEntity(entityId, entityType)
```

#### Store Current State
**File**: `frontend/src/stores/validation.js`

```javascript
state: () => ({
  supportedFieldTypes: [],
  businessRules: [],
  validationResults: {},  // ❌ Object, component expects array
  jsonSchemas: {},
  loading: false,
  error: null
  // ❌ MISSING: validationStats
  // ❌ MISSING: commonIssues
  // ❌ MISSING: validationResultsList (array version)
})

// ❌ MISSING ACTIONS:
// - fetchValidationResults()
// - fetchValidationStats()
// - fetchCommonIssues()
// - refreshAllValidations()
// - revalidateEntity()
```

#### API Module Current State
**File**: `frontend/src/api/validation.js`

```javascript
// ✅ HAS:
- validateEvidence(validationData)
- validateSchema(schemaData)
- generateJsonSchema(schemaId)
- getSupportedFieldTypes()
- getBusinessRules()
- validateField(fieldData)

// ❌ MISSING:
- getValidationResults(params)
- getValidationStats(params)
- getCommonIssues(params)
- revalidateEntity(entityId, entityType)
```

#### Backend Current State
**File**: `backend/app/api/v1/endpoints/schema_validation.py`

```python
# ✅ HAS:
POST /api/v1/validation/validate-evidence
POST /api/v1/validation/validate-schema
GET  /api/v1/validation/generate-json-schema/{schema_id}
GET  /api/v1/validation/supported-field-types

# ❌ MISSING:
GET  /api/v1/validation/results
GET  /api/v1/validation/stats
GET  /api/v1/validation/common-issues
POST /api/v1/validation/revalidate/{entity_id}
```

#### Alignment Plan

**Option A: Backend Implementation (Recommended)**

Create missing backend endpoints to match frontend expectations:

```python
# backend/app/api/v1/endpoints/schema_validation.py

@router.get("/results", response_model=List[ValidationResultResponse])
async def get_validation_results(
    skip: int = 0,
    limit: int = 100,
    scope_id: Optional[UUID] = None,
    schema_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get validation results for all entities.
    Used by ValidationDashboard to show table of validation results.
    """
    # Implementation: Query curations_new/precurations_new tables
    # and return validation results with metadata
    pass

@router.get("/stats", response_model=ValidationStatsResponse)
async def get_validation_stats(
    scope_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Get validation statistics (counts, compliance rate, etc.).
    Used by ValidationDashboard summary cards.
    """
    # Implementation: Aggregate validation results
    # Return: valid_curations, invalid_curations, warnings_count, compliance_rate
    pass

@router.get("/common-issues", response_model=List[CommonIssueResponse])
async def get_common_issues(
    scope_id: Optional[UUID] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get most common validation issues across entities.
    Used by ValidationDashboard common issues panel.
    """
    # Implementation: Group validation issues by type, count occurrences
    pass

@router.post("/revalidate/{entity_id}")
async def revalidate_entity(
    entity_id: UUID,
    entity_type: str,  # "curation" or "precuration"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Trigger revalidation of an entity.
    Used by ValidationDashboard revalidate button.
    """
    # Implementation: Fetch entity, run validation, update results
    pass
```

Then cascade down to frontend:

```javascript
// frontend/src/api/validation.js - Add methods
async getValidationResults(params = {}) {
  const response = await apiClient.get('/validation/results', { params })
  return response.data
}

async getValidationStats(params = {}) {
  const response = await apiClient.get('/validation/stats', { params })
  return response.data
}

async getCommonIssues(params = {}) {
  const response = await apiClient.get('/validation/common-issues', { params })
  return response.data
}

async revalidateEntity(entityId, entityType) {
  const response = await apiClient.post(`/validation/revalidate/${entityId}`, {
    entity_type: entityType
  })
  return response.data
}
```

```javascript
// frontend/src/stores/validation.js - Update state and add actions
state: () => ({
  // ... existing state ...
  validationStats: null,  // Add this
  commonIssues: [],       // Add this
  validationResultsList: []  // Add this (array version)
})

actions: {
  // Add these methods
  async fetchValidationResults(params = {}) {
    this.loading = true
    this.error = null
    try {
      const results = await validationAPI.getValidationResults(params)
      this.validationResultsList = results
      return results
    } catch (error) {
      this.error = error.message
      throw error
    } finally {
      this.loading = false
    }
  },

  async fetchValidationStats(params = {}) {
    this.loading = true
    this.error = null
    try {
      const stats = await validationAPI.getValidationStats(params)
      this.validationStats = stats
      return stats
    } catch (error) {
      this.error = error.message
      throw error
    } finally {
      this.loading = false
    }
  },

  async fetchCommonIssues(params = {}) {
    try {
      const issues = await validationAPI.getCommonIssues(params)
      this.commonIssues = issues
      return issues
    } catch (error) {
      this.error = error.message
      throw error
    }
  },

  async revalidateEntity(entityId, entityType) {
    this.loading = true
    this.error = null
    try {
      const result = await validationAPI.revalidateEntity(entityId, entityType)
      // Refresh results after revalidation
      await this.fetchValidationResults()
      return result
    } catch (error) {
      this.error = error.message
      throw error
    } finally {
      this.loading = false
    }
  }
}
```

**Option B: Frontend Simplification (Temporary Workaround)**

Simplify component to use only existing endpoints until backend is ready. See `005-error-handling-fixes-using-existing-systems.md` for defensive coding approach.

---

### 2. Workflow Management

#### Component Expectations
**File**: `frontend/src/views/WorkflowManagement.vue` (inferred from logs)

```javascript
// Component expects these computed properties
const workflowPairs = computed(() => workflowStore.workflowPairs)
const workflowStages = computed(() => workflowStore.workflowStages)

// Component expects these methods (inferred)
await workflowStore.fetchWorkflowPairs()
await workflowStore.fetchWorkflowStages()
```

#### Store Current State
**File**: `frontend/src/stores/workflow.js`

```javascript
state: () => ({
  analytics: null,
  statistics: null,
  peerReviewers: [],
  curationTransitions: {},
  curationHistory: {},
  loading: false,
  error: null,
  currentWorkflowStage: null
  // ❌ MISSING: workflowPairs
  // ❌ MISSING: workflowStages
})

// ❌ MISSING ACTIONS:
// - fetchWorkflowPairs()
// - fetchWorkflowStages()
```

#### API Module Current State
**File**: `frontend/src/api/workflow.js`

```javascript
// ✅ HAS:
- getWorkflowAnalytics(params)
- transitionCuration(curationId, transitionData)
- getAvailableTransitions(curationId)
- getPeerReviewers(params)
- submitPeerReview(curationId, reviewData)
- getCurationWorkflowHistory(curationId)
- getWorkflowStatistics(params)

// ❌ MISSING:
- getWorkflowPairs(params)
- getWorkflowStages(params)
- createWorkflowPair(pairData)
- updateWorkflowPair(pairId, pairData)
- deleteWorkflowPair(pairId)
```

#### Backend Current State
**File**: `backend/app/api/v1/endpoints/workflow.py`

```python
# ✅ HAS:
GET  /api/v1/workflow/analytics
POST /api/v1/workflow/curation/{curation_id}/transition
GET  /api/v1/workflow/curation/{curation_id}/available-transitions
GET  /api/v1/workflow/peer-reviewers

# ❌ MISSING:
GET    /api/v1/workflow/pairs
POST   /api/v1/workflow/pairs
GET    /api/v1/workflow/pairs/{pair_id}
PUT    /api/v1/workflow/pairs/{pair_id}
DELETE /api/v1/workflow/pairs/{pair_id}
GET    /api/v1/workflow/stages
```

#### Alignment Plan

**Database Schema** (`database/sql/001_schema_foundation.sql`):

```sql
-- ✅ Table already exists
CREATE TABLE workflow_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    precuration_schema_id UUID NOT NULL REFERENCES curation_schemas(id),
    curation_schema_id UUID NOT NULL REFERENCES curation_schemas(id),
    scope_id UUID REFERENCES scopes(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Backend Implementation Needed**:

```python
# backend/app/api/v1/endpoints/workflow.py

@router.get("/pairs", response_model=List[WorkflowPairResponse])
async def get_workflow_pairs(
    scope_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all workflow pairs (precuration + curation schema combinations)."""
    pass

@router.get("/stages", response_model=List[WorkflowStageResponse])
async def get_workflow_stages(db: Session = Depends(get_db)):
    """Get all workflow stages (enum values from workflow_stage)."""
    # Return: entry, precuration, curation, review, active
    pass

@router.post("/pairs", response_model=WorkflowPairResponse)
async def create_workflow_pair(
    pair: WorkflowPairCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new workflow pair."""
    pass
```

Then cascade to frontend (same pattern as validation).

---

### 3. Gene Assignment Manager

#### Issue

**File**: `frontend/src/views/GeneAssignmentManager.vue` (from logs)

```javascript
// Component calls this (WRONG)
await assignmentsStore.fetchWorkloadSummary()

// But store has this (CORRECT)
await assignmentsStore.fetchCuratorWorkload(curatorId)
```

#### Current State - CORRECT

Store correctly implements the API:

```javascript
// frontend/src/stores/assignments.js
async fetchCuratorWorkload(curatorId) {
  const workload = await assignmentsAPI.getCuratorWorkload(curatorId)
  this.curatorWorkloads[curatorId] = workload
  return workload
}

// frontend/src/api/assignments.js
async getCuratorWorkload(curatorId) {
  const response = await apiClient.get(`/gene-assignments/curator/${curatorId}/workload`)
  return response.data
}

// backend/app/api/v1/endpoints/gene_assignments.py
@router.get("/curator/{curator_id}/workload")
async def get_curator_workload(curator_id: UUID, db: Session = Depends(get_db)):
    """Get workload summary for curator."""
    pass
```

#### Alignment Plan

**Fix component** to use correct method name (already documented in `005-error-handling-fixes-using-existing-systems.md`).

---

### 4. Schema Management

#### Issue

**File**: `frontend/src/views/SchemaManagement.vue`

```javascript
// Component calls this
await schemasStore.fetchSchemas()

// Store calls this
const response = await schemasAPI.getSchemas(params)

// API calls this
const response = await apiClient.get('/schemas', { params })

// Backend endpoint - DOES NOT EXIST
// Expected: GET /api/v1/schemas
// Actual: 404 Not Found
```

#### Backend Current State

```bash
# Check backend endpoints
grep -r "router.get.*schemas" backend/app/api/v1/endpoints/

# Result: No GET /schemas endpoint found
```

Checking `backend/app/api/v1/endpoints/schemas.py`:

```python
# File may not exist or may have different endpoint structure
```

#### Alignment Plan

**Check if endpoint exists under different path**:

```bash
grep -r "curation_schemas" backend/app/api/v1/endpoints/
```

If endpoint doesn't exist, need to implement:

```python
# backend/app/api/v1/endpoints/schemas.py

@router.get("/", response_model=List[SchemaResponse])
async def get_schemas(
    skip: int = 0,
    limit: int = 100,
    schema_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """Get all curation schemas."""
    # Query curation_schemas table
    pass

@router.get("/{schema_id}", response_model=SchemaResponse)
async def get_schema(schema_id: UUID, db: Session = Depends(get_db)):
    """Get schema by ID."""
    pass

@router.post("/", response_model=SchemaResponse)
async def create_schema(
    schema: SchemaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new schema."""
    pass
```

---

## Summary of Missing Backend Endpoints

### High Priority (Blocks current frontend)

| Endpoint | Method | Purpose | Used By |
|----------|--------|---------|---------|
| `/validation/results` | GET | Get all validation results | ValidationDashboard |
| `/validation/stats` | GET | Get validation statistics | ValidationDashboard |
| `/validation/common-issues` | GET | Get common issues | ValidationDashboard |
| `/validation/revalidate/{id}` | POST | Revalidate entity | ValidationDashboard |
| `/workflow/pairs` | GET | Get workflow pairs | WorkflowManagement |
| `/workflow/stages` | GET | Get workflow stages | WorkflowManagement |

### Medium Priority (Enhances functionality)

| Endpoint | Method | Purpose | Used By |
|----------|--------|---------|---------|
| `/schemas` | GET | List all schemas | SchemaManagement |
| `/schemas/{id}` | GET | Get schema details | SchemaManagement |
| `/schemas` | POST | Create schema | SchemaManagement |
| `/workflow/pairs` | POST | Create workflow pair | WorkflowManagement |
| `/workflow/pairs/{id}` | PUT | Update workflow pair | WorkflowManagement |
| `/workflow/pairs/{id}` | DELETE | Delete workflow pair | WorkflowManagement |

---

## Implementation Strategy

### Phase 1: Backend API Implementation (4-6 hours)

1. **Validation Endpoints** (2 hours)
   - Implement `/validation/results`
   - Implement `/validation/stats`
   - Implement `/validation/common-issues`
   - Implement `/validation/revalidate/{id}`

2. **Workflow Endpoints** (1.5 hours)
   - Implement `/workflow/pairs` (GET, POST, PUT, DELETE)
   - Implement `/workflow/stages` (GET)

3. **Schema Endpoints** (1.5 hours)
   - Implement `/schemas` (GET, POST)
   - Implement `/schemas/{id}` (GET, PUT, DELETE)

4. **Testing** (1 hour)
   - Unit tests for all new endpoints
   - Integration tests for data flow

### Phase 2: Frontend API Module Updates (1 hour)

1. Add missing methods to `frontend/src/api/validation.js`
2. Add missing methods to `frontend/src/api/workflow.js`
3. Verify `frontend/src/api/schemas.js` matches backend

### Phase 3: Store Updates (1 hour)

1. Add missing state properties to stores
2. Add missing action methods to stores
3. Ensure proper error handling (use existing pattern)

### Phase 4: Component Updates (30 minutes)

1. Update computed properties to use new store state
2. Update `onMounted` to call new store methods
3. Verify error handling uses existing `logService`

### Phase 5: Integration Testing (1 hour)

1. Test ValidationDashboard end-to-end
2. Test WorkflowManagement end-to-end
3. Test all error scenarios
4. Verify logging works correctly

**Total Estimated Time**: 8-10 hours

---

## API Contract Documentation Template

For each new endpoint, document:

```markdown
### Endpoint Name

**URL**: `/api/v1/path`
**Method**: GET/POST/PUT/DELETE
**Authentication**: Required (JWT Bearer token)

**Query Parameters**:
- `param_name` (type, optional): Description

**Request Body** (for POST/PUT):
```json
{
  "field": "value"
}
```

**Response** (200 OK):
```json
{
  "data": []
}
```

**Error Responses**:
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

**Used By**:
- Component: `ComponentName.vue`
- Store: `storeName.fetchMethod()`
- API Module: `apiModule.methodName()`
```

---

## Testing Checklist

### Backend Tests

- [ ] Unit tests for validation CRUD operations
- [ ] Unit tests for workflow pair CRUD operations
- [ ] Unit tests for schema CRUD operations
- [ ] Integration tests for validation statistics aggregation
- [ ] Integration tests for common issues grouping

### Frontend Tests

- [ ] API module methods call correct endpoints
- [ ] Store actions properly handle responses
- [ ] Store actions properly handle errors
- [ ] Components render with new store state
- [ ] Components handle loading states
- [ ] Components handle error states

### End-to-End Tests

- [ ] ValidationDashboard loads without errors
- [ ] ValidationDashboard displays statistics
- [ ] ValidationDashboard displays results table
- [ ] ValidationDashboard revalidation works
- [ ] WorkflowManagement loads without errors
- [ ] WorkflowManagement displays pairs
- [ ] SchemaManagement loads schemas

---

## Migration Notes

### For Developers

1. **Always check backend first**: Before adding frontend code, verify backend endpoint exists
2. **Follow existing patterns**: All stores use same error handling pattern
3. **Test incrementally**: Test each layer (backend → API module → store → component)
4. **Use existing logging**: Never use `console.*`, always use `logService`

### For Code Reviewers

1. Verify endpoint exists in backend before approving frontend PR
2. Check that store method matches API module method
3. Check that component uses correct store state/methods
4. Verify error handling follows existing pattern
5. Verify logging uses `logService` not `console.*`

---

## Related Documentation

- `005-error-handling-fixes-using-existing-systems.md` - Defensive coding fixes
- `CLAUDE.md` - Project architecture and API documentation
- `backend/app/api/v1/api.py` - API router configuration
- `database/sql/001_schema_foundation.sql` - Database schema

---

## Conclusion

**Key Finding**: NO Firebase remnants. Issues stem from frontend built ahead of backend.

**Resolution Strategy**:
1. Implement missing backend endpoints (8-10 hours)
2. OR use defensive coding workaround (3.5 hours) until backend ready

**Recommendation**: Implement backend endpoints for full functionality. Use defensive coding (doc 005) as temporary fix to prevent CRITICAL errors while backend is in development.
