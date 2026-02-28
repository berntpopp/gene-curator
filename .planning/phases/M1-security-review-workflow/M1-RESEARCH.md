# Phase M1: Security Fix + Review Workflow - Research

**Researched:** 2026-02-28
**Domain:** SQLAlchemy array operators, FastAPI workflow API, Vue 3 + Pinia review frontend
**Confidence:** HIGH (all findings verified directly from codebase)

---

## Summary

Phase M1 has two concerns: a SQL injection fix in the gene search CRUD and completing the review workflow frontend. The backend is substantially complete. The frontend has partial scaffolding that needs wiring to the real API surface.

**SQL Injection (M1.1):** `backend/app/crud/gene.py` lines 92-93 use `text(f"'{search_params.query}' = ANY(genes.previous_symbols)")` which is a first-order SQL injection vulnerability. The fix is to use SQLAlchemy's `any_()` function with a parameterized literal. The `compatible_array_text()` type decorator means tests use SQLite (JSON-encoded list), so the fix must use cross-database compatible operators or conditionally fall back. The correct SQLAlchemy pattern for PostgreSQL array membership is `literal(value).bool_op("= ANY")(column)` or casting to use `any_()`. The safest cross-database approach is using the `Gene.previous_symbols.any(value)` (PostgreSQL only) pattern with `.contains()` fallback via `or_()`.

**Review Backend:** Fully implemented. Key endpoints: `GET /workflow/reviews/my-assignments`, `POST /workflow/{item_type}/{item_id}/assign-reviewer`, `POST /workflow/reviews/{review_id}/submit`, `POST /workflow/{item_type}/{item_id}/transition`. The `CurationDetail` schema already includes `can_review: bool` set by the curations endpoint. The `CurationDetailView.vue` already has Approve/Request Changes action buttons wired to `workflowAPI.transitionCuration()`.

**Review Frontend State:** `ReviewQueueView.vue` exists but fetches via `curationsAPI.getCurations({ curation_status: 'submitted' })` — this is wrong. Curations in review have `status: 'in_review'` (not `'submitted'`). The workflow store lacks `fetchPendingReviews()` and `getPendingReviewCount()`. `CurationDetailView.vue` already has approve/reject buttons that use `workflowAPI.transitionCuration()` — the correct approach. A dedicated `CurationReview` component is not needed; the existing detail view handles review actions.

**Primary recommendation:** Fix the SQL injection with SQLAlchemy array operators; fix ReviewQueueView to fetch `in_review` status curations (or use the `my-assignments` endpoint); add `fetchPendingReviews()` and `getPendingReviewCount()` to workflow store; wire notification badge to pending count with interval refresh.

---

## Standard Stack

### Core (Already In Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.0 | 2.0.x | ORM + query building | Already in use; `any_()` + `literal()` for parameterized array queries |
| FastAPI | Latest | API framework | Already in use; workflow endpoints exist |
| Vue 3 + Composition API | 3.x | Frontend framework | Already in use |
| Pinia | 2.x | State management | Already in use; workflow store exists |
| Vuetify 3 | 3.x | UI components | Already in use; `v-badge`, `v-btn`, `v-list` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlalchemy.dialects.postgresql` | bundled | PostgreSQL ARRAY operators | `any_()` for array membership tests |
| `sqlalchemy.sql.expression.literal` | bundled | Parameterized value binding | Replace f-string injection in `text()` calls |

### Installation
```bash
# No new dependencies required - all libraries already installed
```

---

## Architecture Patterns

### SQL Injection Fix Pattern

**What:** Replace `text(f"'{value}' = ANY(column)")` with SQLAlchemy parameterized operators.

**The vulnerability (lines 92-93 in gene.py):**
```python
# VULNERABLE - direct string interpolation into SQL
text(f"'{search_params.query}' = ANY(genes.previous_symbols)"),
text(f"'{search_params.query}' = ANY(genes.alias_symbols)"),
```

**The fix — PostgreSQL-compatible with SQLite fallback:**
```python
# Source: SQLAlchemy docs on ARRAY operators and db_types.py compatibility pattern
from sqlalchemy import literal
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy import Text

# For PostgreSQL (production): use any_() with proper parameter binding
# For SQLite (tests): the column stores JSON-encoded list, use JSON_EXTRACT or LIKE
# Cross-database safe approach using SQLAlchemy's dialect-aware column operators:

# Option 1: Use column.any() - works natively on PostgreSQL ARRAY columns
# The compatible_array_text() type returns PG_ARRAY(Text) with SQLite fallback
# For PostgreSQL: Gene.previous_symbols.any_(search_params.query) - NOT AVAILABLE on mapped columns

# Option 2: Use literal + bool_op (most compatible)
Gene.previous_symbols.bool_op('@>')(
    func.array([search_params.query])
)

# Option 3: Cast and use any_() (recommended - works in PostgreSQL, graceful in SQLite)
from sqlalchemy import cast, Text as SAText
from sqlalchemy.dialects.postgresql import ARRAY

search_val = search_params.query  # parameterized automatically by SQLAlchemy
stmt = stmt.where(
    or_(
        Gene.approved_symbol.ilike(search_term),
        Gene.hgnc_id.ilike(search_term),
        Gene.details.op("->>")("gene_description").ilike(search_term),
        # Use any_() for array membership - SQLAlchemy parameterizes this
        Gene.previous_symbols.any_(search_val),  # PostgreSQL native ARRAY
        Gene.alias_symbols.any_(search_val),
    )
)
```

**IMPORTANT NOTE on test compatibility:** The `compatible_array_text()` creates `PG_ARRAY(Text).with_variant(JSONEncodedList(), "sqlite")`. SQLite stores arrays as JSON text. `.any_()` is a PostgreSQL-specific operator and will NOT work in SQLite tests. The correct cross-database fix is:

```python
# Source: Pattern from db_types.py and SQLAlchemy documentation
import sqlalchemy as sa
from sqlalchemy import text

# Use a conditional approach: on PostgreSQL use array operator, on SQLite use LIKE fallback
# Since tests use SQLite, need a safe approach

# Recommended: Strip special characters + use LIKE fallback (works on both databases)
# For simplicity in MVP, clean the search term and use a safe format:
search_safe = search_params.query.replace("'", "''")  # Still SQL injection risk

# CORRECT approach: Use bindparam to let SQLAlchemy handle parameterization
# For the `text()` construct, use :param syntax
from sqlalchemy import text, bindparam

stmt = stmt.where(
    or_(
        Gene.approved_symbol.ilike(search_term),
        Gene.hgnc_id.ilike(search_term),
        Gene.details.op("->>")("gene_description").ilike(search_term),
        # Parameterized text() - safe from injection
        text(":query = ANY(genes.previous_symbols)").bindparams(query=search_params.query),
        text(":query = ANY(genes.alias_symbols)").bindparams(query=search_params.query),
    )
)
```

**Confidence:** HIGH for the `text().bindparams()` approach (documented SQLAlchemy pattern). The `any_()` approach requires PostgreSQL dialect and may break SQLite tests.

**Input validation addition (defense in depth):**
```python
# In GeneSearchQuery schema (gene.py) - add validator
@field_validator("query")
@classmethod
def validate_query_length(cls, v: str | None) -> str | None:
    if v is not None and len(v) > 200:
        raise ValueError("Search query too long (max 200 characters)")
    return v
```

### Review Queue API Usage Pattern

**What:** ReviewQueueView should use `/workflow/reviews/my-assignments` (already implemented in backend) instead of `curationsAPI.getCurations({ curation_status: 'submitted' })`.

**Current wrong approach:**
```javascript
// ReviewQueueView.vue (current - WRONG)
const response = await curationsAPI.getCurations({
  curation_status: 'submitted',  // WRONG: in_review status is 'in_review', not 'submitted'
  limit: 200
})
```

**Correct approach:**
```javascript
// Add to workflow.js API module
async getMyReviewAssignments(params = {}) {
  // GET /workflow/reviews/my-assignments
  // Returns: list[PeerReviewRequest] with review_id, item_id, item_type, status
  const response = await apiClient.get('/workflow/reviews/my-assignments', { params })
  return response.data
},
```

**Backend response shape for `/workflow/reviews/my-assignments`:**
```json
[
  {
    "review_id": "uuid",
    "item_id": "curation-uuid",
    "item_type": "curation",
    "reviewer_id": "user-uuid",
    "assigned_by": "user-uuid",
    "review_type": "peer_review",
    "assigned_at": "2026-01-01T00:00:00Z",
    "status": "pending"
  }
]
```

**Gap:** The `PeerReviewRequest` schema returned by `my-assignments` does NOT include gene_symbol, scope_name, curator_name, score — only IDs. The ReviewQueueView needs to either:
1. Fetch full curation details for each review assignment (N+1 problem), OR
2. Use a different endpoint: `curationsAPI.getCurations({ curation_status: 'in_review' })` filtered client-side by `created_by !== current_user.id`

**Recommendation:** Fix ReviewQueueView to use `curation_status: 'in_review'` (the correct status value) and keep the existing client-side 4-eyes filter. The `my-assignments` endpoint is better architecturally but requires enriched response data from the backend.

### Workflow Store Review Methods Pattern

**What:** Add review-specific methods to `useWorkflowStore`.

**Pattern (follows existing store patterns in workflow.js):**
```javascript
// Add to workflow store state:
pendingReviews: [],
pendingReviewCount: 0,

// Add actions:
async fetchPendingReviews(params = {}) {
  this.loading = true
  this.error = null
  try {
    // Use curations endpoint with in_review filter
    const response = await curationsAPI.getCurations({
      curation_status: 'in_review',
      limit: 200,
      ...params
    })
    const userId = authStore.user?.id
    // Apply 4-eyes filter
    this.pendingReviews = (response.curations || []).filter(c => c.created_by !== userId)
    this.pendingReviewCount = this.pendingReviews.length
    return this.pendingReviews
  } catch (error) {
    this.error = error.message
    throw error
  } finally {
    this.loading = false
  }
},

async getPendingReviewCount() {
  try {
    await this.fetchPendingReviews()
    return this.pendingReviewCount
  } catch {
    return 0
  }
},
```

### Notification Badge Auto-Refresh Pattern

**What:** Poll for pending review count every 60 seconds and show on nav item.

**What exists:** `NotificationBadge.vue` component with `count` prop and `priority` prop. `BaseNavigationItem.vue` accepts a `badge` prop that shows inline `v-badge`. `MainNavigation.vue` renders the curation dropdown items using `BaseNavigationItem`.

**Pattern:**
```javascript
// In a composable useReviewBadge.js or in App.vue / MainNavigation.vue
import { ref, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'

const workflowStore = useWorkflowStore()
const pendingCount = ref(0)
let refreshInterval = null

onMounted(async () => {
  await refreshCount()
  refreshInterval = setInterval(refreshCount, 60000) // 60s
})

onUnmounted(() => {
  clearInterval(refreshInterval)
})

async function refreshCount() {
  try {
    pendingCount.value = await workflowStore.getPendingReviewCount()
  } catch {
    // Silent fail for badge refresh
  }
}
```

**Wiring to navigation:** The "Review Queue" route already has `showInDropdown: 'curation'` and `icon: 'mdi-clipboard-check-outline'`. `MainNavigation.vue` uses `BaseNavigationItem` which accepts a `badge` prop. To add the badge count, the curation dropdown item for Review Queue needs to receive the count. The simplest approach is to add badge support to `MainNavigation.vue` for the Review Queue specifically, or add a composable that provides the count reactively.

### Existing Review Actions in CurationDetailView

**Critical finding:** `CurationDetailView.vue` already implements the review interface. It has:
- `approveCuration()` — calls `workflowAPI.transitionCuration(id, { target_stage: 'active' })`
- `rejectCuration()` — calls `workflowAPI.transitionCuration(id, { target_stage: 'curation' })`
- `canReview` computed — reads `curation.value?.can_review`
- Approve/Request Changes buttons with confirmation dialogs

**What's missing from CurationDetailView for M1.3:**
- "Request Revision" is called "Request Changes" — maps to `target_stage: 'curation'` (sends back)
- Review history timeline is not displayed (just shows current state)
- There is no "Reject" (hard reject) separate from "Request Changes" — the current `rejectCuration()` sends back to curation stage, not archives

**Assessment:** M1.3 (CurationReview interface) is largely done in `CurationDetailView.vue`. The tasks are to verify read-only DynamicForm display works and add review history.

### Recommended Project Structure (No Changes Needed)

The existing structure is correct for M1:
```
frontend/src/
├── api/workflow.js              # Add getMyReviewAssignments()
├── stores/workflow.js           # Add fetchPendingReviews(), getPendingReviewCount()
├── views/curation/
│   └── ReviewQueueView.vue     # Fix curation_status filter to 'in_review'
└── components/navigation/
    └── MainNavigation.vue       # Add badge count to Review Queue item

backend/app/crud/
└── gene.py                      # Fix SQL injection in search()
```

### Anti-Patterns to Avoid

- **`text(f"...")`:** Never use Python f-strings inside SQLAlchemy `text()`. Use `.bindparams()` instead.
- **N+1 on review queue:** Do not fetch curation details for each review assignment — filter by `in_review` status directly.
- **Polling without cleanup:** Always clear `setInterval` in `onUnmounted` to prevent memory leaks.
- **`submitted` status for review filter:** The status after a curator submits is `in_review`, not `submitted`. `submitted` is a transient state; the workflow engine transitions it to `in_review` immediately.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Array membership SQL | Custom raw SQL | `text().bindparams()` or `any_()` | SQLAlchemy handles parameterization |
| Badge counts | Custom badge component | `NotificationBadge.vue` already exists | Already tested, accessible |
| Review decision UI | New component | Extend `CurationDetailView.vue` | Already has Approve/Request Changes buttons |
| Polling/intervals | Complex WebSocket | `setInterval` with cleanup | Sufficient for 60s refresh |
| Review form | New form component | `DynamicForm` with `readonly: true` | Already supports read-only mode |

**Key insight:** The codebase has most pieces built. The work is connecting them correctly, not building new infrastructure.

---

## Common Pitfalls

### Pitfall 1: Wrong CurationStatus for Review Queue

**What goes wrong:** `ReviewQueueView.vue` fetches `curation_status: 'submitted'`. Curations in the review stage have `status: 'in_review'`. The `submitted` status only briefly exists before the workflow engine transitions to `in_review`.

**Why it happens:** The `CurationStatus` enum has both `SUBMITTED = "submitted"` and `IN_REVIEW = "in_review"`. The frontend was written before this distinction was clear.

**How to avoid:** Use `curation_status: 'in_review'` in the API call. The `workflow_stage` is `REVIEW` when status is `IN_REVIEW`.

**Warning signs:** ReviewQueue shows zero items even when curations have been submitted.

### Pitfall 2: SQL Injection via text() f-strings

**What goes wrong:** `text(f"'{search_params.query}' = ANY(genes.previous_symbols)")` — attacker sends `'; DROP TABLE genes; --` as search query.

**Why it happens:** Developer used Python f-string interpolation instead of SQLAlchemy's parameterized query system.

**How to avoid:** Use `text("... = ANY(...)").bindparams(param=value)`. SQLAlchemy will use proper placeholder binding for the database driver.

**Warning signs:** Any `text(f"...")` pattern in CRUD files. Check with `grep -n "text(f" backend/app/crud/`.

### Pitfall 3: SQLite Test Compatibility for Array Operators

**What goes wrong:** `Gene.previous_symbols.any_(value)` works in PostgreSQL but fails in SQLite tests because `JSONEncodedList` doesn't support `.any_()`.

**Why it happens:** `compatible_array_text()` uses `with_variant(JSONEncodedList(), "sqlite")` — SQLite stores arrays as JSON text strings, not true PostgreSQL ARRAYs.

**How to avoid:** Use `text("... = ANY(...)").bindparams()` which PostgreSQL understands natively. For SQLite tests, mock the array query or test it specifically against PostgreSQL. Alternatively, accept that array search tests only run against PostgreSQL.

**Warning signs:** `AttributeError: 'JSONEncodedList' object has no attribute 'any_'` in test runs.

### Pitfall 4: 4-Eyes Filter Only on Frontend

**What goes wrong:** ReviewQueue filters `created_by !== userId` only in JavaScript. Backend doesn't enforce this for the list endpoint.

**Why it happens:** The `can_review` field on `CurationDetail` is set by the backend correctly, but the list endpoint (`GET /curations/`) doesn't filter by 4-eyes.

**How to avoid:** Frontend filter is acceptable for the list view (it's a UX filter, not security). The workflow engine enforces 4-eyes at the transition level: `_validate_4_eyes_principle()` in `workflow_engine.py` raises an error if `item.created_by == user_id` when transitioning `REVIEW -> ACTIVE`. The backend is the enforcer.

**Warning signs:** Reviewer sees their own curations in the queue (cosmetic), but approval still fails at backend (security correct).

### Pitfall 5: Notification Badge Interval Without Cleanup

**What goes wrong:** `setInterval` registered in `onMounted` but not cleared in `onUnmounted`. Memory leak + multiple timers accumulate on navigation.

**How to avoid:** Always pair `setInterval` with `clearInterval` in `onUnmounted`. Or use a composable that encapsulates the lifecycle.

### Pitfall 6: `submitPeerReview` API Mismatch

**What goes wrong:** The workflow store's `submitPeerReview(curationId, reviewData)` calls `workflowAPI.submitPeerReview(curationId, reviewData)` which hits `/workflow/curation/${curationId}/review` — this endpoint does NOT EXIST in the backend.

**Backend reality:** Review submission uses:
1. Assign reviewer: `POST /workflow/curation/{id}/assign-reviewer`
2. Submit decision: `POST /workflow/reviews/{review_id}/submit`
3. OR transition directly: `POST /workflow/curation/{id}/transition` with `target_stage: 'active'`

**How to avoid:** The `CurationDetailView.vue` already uses the correct approach: `workflowAPI.transitionCuration(id, { target_stage: 'active' })`. Do not use the `submitPeerReview` workflow store action — it calls a non-existent endpoint. The transition-based approach is the correct integration pattern for MVP.

---

## Code Examples

### M1.1: SQL Injection Fix

```python
# Source: backend/app/crud/gene.py (fixed version)
# Uses text().bindparams() — SQLAlchemy documented pattern
from sqlalchemy import and_, func, or_, select, text

@timed_operation("gene_search", warning_threshold_ms=500)
def search(self, db: Session, *, search_params: GeneSearchQuery) -> Sequence[Gene]:
    """Advanced gene search with multiple filters."""
    stmt = select(Gene)

    if search_params.query:
        search_term = f"%{search_params.query}%"
        stmt = stmt.where(
            or_(
                Gene.approved_symbol.ilike(search_term),
                Gene.hgnc_id.ilike(search_term),
                Gene.details.op("->>")("gene_description").ilike(search_term),
                # FIXED: Use bindparams instead of f-string interpolation
                text(":query_val = ANY(genes.previous_symbols)").bindparams(
                    query_val=search_params.query
                ),
                text(":query_val2 = ANY(genes.alias_symbols)").bindparams(
                    query_val2=search_params.query
                ),
            )
        )
    # ... rest unchanged
```

### M1.2: ReviewQueueView Fix

```javascript
// Source: frontend/src/views/curation/ReviewQueueView.vue (fixed fetchPendingReviews)
async function fetchPendingReviews() {
  loading.value = true
  try {
    // FIXED: Use 'in_review' status (not 'submitted')
    const response = await curationsAPI.getCurations({
      curation_status: 'in_review',
      limit: 200
    })

    const userId = authStore.user?.id
    // Apply 4-eyes filter (UX only - backend enforces at transition)
    curations.value = (response.curations || [])
      .filter(c => c.created_by !== userId)
      .map(c => ({ /* same mapping as before */ }))

    // ... rest unchanged
  } catch (error) {
    logger.error('Failed to fetch pending reviews', { error: error.message })
    notificationStore.addToast('Failed to load review queue', 'error')
  } finally {
    loading.value = false
  }
}
```

### M1.4: Workflow Store Additions

```javascript
// Source: frontend/src/stores/workflow.js (additions)
// Add to state:
pendingReviewCount: 0,

// Add to actions:
async fetchPendingReviewCount() {
  try {
    // Use curations endpoint with in_review filter
    const { curationsAPI } = await import('@/api')
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()

    const response = await curationsAPI.getCurations({
      curation_status: 'in_review',
      limit: 200
    })
    const userId = authStore.user?.id
    const myReviews = (response.curations || []).filter(c => c.created_by !== userId)
    this.pendingReviewCount = myReviews.length
    return this.pendingReviewCount
  } catch {
    return 0
  }
},
```

### M1.5: Navigation Badge

```vue
<!-- Source: MainNavigation.vue (curation dropdown item for review queue) -->
<BaseNavigationItem
  v-for="item in curationItems"
  :key="item.name"
  :to="item.to"
  :icon="item.icon"
  :label="item.label"
  :badge="item.name === 'review-queue' ? pendingReviewCount : null"
  badge-color="warning"
/>
```

```javascript
// In MainNavigation.vue <script setup>:
import { ref, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'

const workflowStore = useWorkflowStore()
const pendingReviewCount = ref(0)
let badgeRefreshInterval = null

onMounted(async () => {
  if (isAuthenticated.value) {
    await refreshBadgeCount()
    badgeRefreshInterval = setInterval(refreshBadgeCount, 60000)
  }
})

onUnmounted(() => {
  if (badgeRefreshInterval) clearInterval(badgeRefreshInterval)
})

async function refreshBadgeCount() {
  pendingReviewCount.value = await workflowStore.fetchPendingReviewCount()
}
```

### M1.6: Backend Test Pattern for Review Workflow

```python
# Source: follows pattern from backend/tests/api/test_curations.py
from unittest.mock import patch
from uuid import uuid4
import pytest

class TestReviewWorkflow:
    """Tests for 4-eyes review workflow."""

    @pytest.fixture(autouse=True)
    def mock_rls(self):
        with patch("app.api.v1.endpoints.workflow.set_rls_context", side_effect=lambda *a: None):
            yield

    def test_curator_cannot_review_own_curation(
        self, client, db_session, test_scope, test_user_curator, curator_token
    ):
        """4-eyes principle: curator cannot approve their own curation."""
        # Create curation in review stage
        curation = CurationNew(
            id=uuid4(),
            gene_id=...,
            scope_id=test_scope.id,
            workflow_stage=WorkflowStage.REVIEW,
            status=CurationStatus.IN_REVIEW,
            created_by=test_user_curator.id,
            ...
        )
        db_session.add(curation)
        db_session.commit()

        # Attempt to approve own curation
        response = client.post(
            f"/api/v1/workflow/curation/{curation.id}/transition",
            json={"target_stage": "active"},
            headers={"Authorization": f"Bearer {curator_token}"}
        )
        assert response.status_code == 400
        assert "4-eyes principle" in response.json()["detail"]
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `text(f"'{val}' = ANY(col)")` | `text("... = ANY(...)").bindparams(val=value)` | Eliminates SQL injection |
| Fetch `status: 'submitted'` for review queue | Fetch `status: 'in_review'` | Shows actual curations in review |
| No pending count in nav | Badge with 60s refresh | Reviewers see pending work |

**Deprecated/outdated:**
- `workflowAPI.submitPeerReview(curationId, reviewData)`: calls non-existent `/workflow/curation/{id}/review` endpoint. Not to be used for MVP — use `transitionCuration()` instead.
- `workflowAPI.getAvailableTransitions(curationId)`: calls non-existent `/workflow/curation/{id}/available-transitions`. Use `workflowAPI.getWorkflowState('curation', id)` which returns `available_transitions` in the response.

---

## Open Questions

1. **Array membership in SQLite tests**
   - What we know: `text("... = ANY(...)").bindparams()` will fail on SQLite because SQLite doesn't support PostgreSQL's `ANY()` syntax
   - What's unclear: Do existing tests cover the gene search function? If yes, they need mocking or the array comparison must have a SQLite-compatible path
   - Recommendation: Check if gene search tests exist (`backend/tests/` has no test_genes.py found). If no tests cover `search()`, add PostgreSQL-only tests or mock the database dialect check

2. **Review history endpoint**
   - What we know: `_log_workflow_transition()` in `workflow_engine.py` is a no-op (just `pass`) — no audit trail is persisted
   - What's unclear: M1.3 requires "previous review history timeline" but there is no stored history
   - Recommendation: Display only the current review state and comments from the `reviews` table; skip timeline for MVP since there's no audit log data

3. **Assign reviewer vs transition for review approval**
   - What we know: Two parallel mechanisms exist — the `assign-reviewer` endpoint creates a `Review` record, and the `transition` endpoint changes workflow stage. `CurationDetailView.vue` uses only `transitionCuration()` for approve/reject
   - What's unclear: Should `assign-reviewer` be used before `transitionCuration`? The MVP-PLAN mentions "Approve/Reject/Request Revision all work" but the `Review` table assignment may not be required for the transition to succeed
   - Recommendation: The `execute_transition()` validates 4-eyes principle directly; a `Review` record assignment is optional for MVP. Keep `CurationDetailView.vue`'s existing transition approach and skip explicit reviewer assignment for MVP

---

## Sources

### Primary (HIGH confidence)
- Direct file read: `backend/app/crud/gene.py` — SQL injection patterns at lines 92-93
- Direct file read: `backend/app/api/v1/endpoints/workflow.py` — all workflow endpoints, confirmed `my-assignments` exists
- Direct file read: `backend/app/crud/workflow_engine.py` — 4-eyes principle enforcement logic
- Direct file read: `backend/app/models/models.py` — `Review`, `CurationStatus`, `WorkflowStage` models
- Direct file read: `frontend/src/views/curation/ReviewQueueView.vue` — current incomplete state
- Direct file read: `frontend/src/stores/workflow.js` — missing `fetchPendingReviews`, `pendingReviewCount`
- Direct file read: `frontend/src/api/workflow.js` — `submitPeerReview` calls non-existent endpoint
- Direct file read: `frontend/src/views/curation/CurationDetailView.vue` — approve/reject already implemented
- Direct file read: `frontend/src/components/navigation/MainNavigation.vue` — badge integration point
- Direct file read: `frontend/src/components/navigation/BaseNavigationItem.vue` — `badge` prop exists
- Direct file read: `frontend/src/components/navigation/NotificationBadge.vue` — standalone badge component
- Direct file read: `backend/app/core/db_types.py` — SQLite compatibility layer for arrays
- Direct file read: `backend/app/schemas/curation.py` — `CurationDetail.can_review` field confirmed
- Direct file read: `backend/tests/conftest.py` — test fixture patterns

### Secondary (MEDIUM confidence)
- Direct file read: `.planning/archive/plan/enhancements/010-review-workflow-4eyes.md` — original review workflow design

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- SQL injection fix (bindparams approach): HIGH — documented SQLAlchemy pattern, confirmed vulnerability in code
- SQLite test compatibility for array fix: MEDIUM — db_types.py examined, but no gene search tests found to verify behavior
- Review queue status fix ('in_review' vs 'submitted'): HIGH — CurationStatus enum confirmed, workflow engine confirmed
- API endpoint mismatches: HIGH — confirmed by direct comparison of frontend calls vs backend route definitions
- Notification badge pattern: HIGH — NotificationBadge.vue + BaseNavigationItem badge prop both verified
- Review history (open question): LOW — `_log_workflow_transition` is a no-op, confirmed by code read

**Research date:** 2026-02-28
**Valid until:** 2026-03-30 (stable codebase, 30-day window)
