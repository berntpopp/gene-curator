---
phase: M1-security-review-workflow
verified: 2026-02-28T10:12:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "Approve/Reject/Request Revision all work end-to-end — _can_user_review_curation now checks CurationStatus.IN_REVIEW (fix in commit 8a325ef)"
    - "CurationReview displays evidence read-only with score and verdict — DynamicForm wired in CurationDetailView with :readonly='true' (commit cbabe47)"
  gaps_remaining: []
  regressions: []
---

# Phase M1: Security Fix + Review Workflow Verification Report

**Phase Goal:** Fix SQL injection vulnerability and complete the 4-eyes review workflow frontend so curations can be approved by independent reviewers
**Verified:** 2026-02-28T10:12:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (commits 8a325ef, cbabe47, 90615d4)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Gene search uses parameterized queries (no SQL injection) | VERIFIED | `backend/app/crud/gene.py` lines 92-97: `text(":query_val = ANY(genes.previous_symbols)").bindparams(query_val=...)` and `text(":query_val2 = ANY(genes.alias_symbols)").bindparams(query_val2=...)`. Zero `text(f"...")` patterns remain. |
| 2 | ReviewQueue shows pending reviews for current user across scopes | VERIFIED | `frontend/src/views/curation/ReviewQueueView.vue` line 282: `curation_status: 'in_review'`. Lines 303-305 filter out `created_by === userId` (4-eyes). Real filter/sort UI with scope dropdown, search, and sort controls. |
| 3 | CurationReview displays evidence read-only with score and verdict | VERIFIED | `CurationDetailView.vue` line 529: `import DynamicForm from '@/components/dynamic/DynamicForm.vue'`. Lines 326-343: `<v-row v-if="curationSchemaId">` containing `<DynamicForm :schema-id="curationSchemaId" :initial-data="curation.evidence_data || {}" :readonly="true" title="" />`. Lines 741-771: `loadCurationSchema()` fetches `schemasAPI.getWorkflowPairById(curation.value.workflow_pair_id)` and sets `curationSchemaId.value`. Function called from `loadCuration()` after data is loaded. |
| 4 | Approve/Reject/Request Revision all work end-to-end | VERIFIED | `backend/app/api/v1/endpoints/curations.py` line 90: `if curation.status != CurationStatus.IN_REVIEW: return False` (fixed from SUBMITTED). `CurationDetailView.vue` line 690-693: `canReview` computed reads `curation.value?.can_review`. Buttons at lines 188-215 render when `canReview` is true. 3 new tests (`TestCanReviewPermission`) confirm correct behavior: can_review=True for IN_REVIEW curations by others, False for drafts, False for own curations. |
| 5 | 4-eyes principle enforced (cannot review own curation) | VERIFIED | `backend/app/api/v1/endpoints/curations.py` line 86: `if curation.created_by == user.id: return False`. Test `test_can_review_false_for_own_curation` (line 614) confirms this. Backend `workflow_engine.py` also enforces at transition execution. |
| 6 | Review notification badge shows pending count | VERIFIED | `MainNavigation.vue`: `pendingReviewCount` ref (line 82), `refreshBadgeCount()` (line 85), `setInterval(refreshBadgeCount, 60000)` on mount (line 96), `clearInterval` on unmount. `curationItems` computed (lines 139-143): `badge: route.name === 'review-queue' && pendingReviewCount.value > 0 ? pendingReviewCount.value : null`. Badge wired to `BaseNavigationItem` via `:badge` and `:badge-color` props. |
| 7 | All existing tests still pass (plus new regression tests) | VERIFIED | Backend: 104 passed (101 original + 3 new `TestCanReviewPermission` tests). Frontend: 428 passed (unchanged). Total: 532 (up from 529). |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/crud/gene.py` | Parameterized gene search queries | VERIFIED | Lines 92-97: `text().bindparams()` for both `previous_symbols` and `alias_symbols` array clauses. No f-string SQL. 508 lines, substantive. |
| `backend/app/schemas/gene.py` | Query length validation on GeneSearchQuery | VERIFIED | Lines 152-177: `max_length=200` field param + `validate_query_length` field_validator enforcing 200-char limit. 348 lines, substantive. |
| `frontend/src/views/curation/ReviewQueueView.vue` | Working review queue showing in_review curations | VERIFIED | 350+ lines, fetches `in_review`, filters own curations, real UI with scope/search/sort controls. |
| `frontend/src/stores/workflow.js` | `pendingReviewCount` state and `fetchPendingReviewCount` action | VERIFIED | Line 64: `pendingReviewCount: 0` state. Lines 193-210: `fetchPendingReviewCount()` action with dynamic import, in_review filter, 4-eyes client-side filter. |
| `frontend/src/api/workflow.js` | Clean API methods without non-existent endpoint calls | VERIFIED | `getAvailableTransitions` uses `/state` endpoint. `submitPeerReview` uses `/transition` endpoint. No dead endpoint URLs. |
| `frontend/src/components/navigation/MainNavigation.vue` | Review Queue badge with pending count and auto-refresh | VERIFIED | Lines 82-105: ref, refreshBadgeCount, onMounted interval, onUnmounted cleanup. Lines 139-143: conditional badge in curationItems computed. Template: `:badge` and `:badge-color` props passed to BaseNavigationItem. |
| `backend/app/api/v1/endpoints/curations.py` | Correct can_review logic using IN_REVIEW status | VERIFIED | Line 90: `if curation.status != CurationStatus.IN_REVIEW: return False`. No `CurationStatus.SUBMITTED` references remain in `_can_user_review_curation`. |
| `frontend/src/views/curation/CurationDetailView.vue` | Read-only DynamicForm rendering evidence fields | VERIFIED | Line 529: import. Lines 326-343: template with `v-if="curationSchemaId"`, `DynamicForm :readonly="true"`. Lines 553-554: `curationSchemaId = ref(null)`, `loadingSchema = ref(false)`. Lines 741-771: `loadCurationSchema()` fetches workflow pair, sets curationSchemaId. Called from `loadCuration()`. |
| `backend/tests/api/test_curations.py` | Tests for can_review field correctness | VERIFIED | Lines 550-648: `TestCanReviewPermission` class with 3 tests: `test_can_review_true_for_in_review_curation`, `test_can_review_false_for_draft_curation`, `test_can_review_false_for_own_curation`. All pass (104 total backend tests). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `gene.py:CRUDGene.search()` | `sqlalchemy.text().bindparams()` | parameterized SQL | WIRED | Lines 92-97: both array-check clauses use bindparams |
| `ReviewQueueView.vue:fetchPendingReviews()` | `curationsAPI.getCurations` | `curation_status: 'in_review'` | WIRED | Line 282: correct status filter |
| `workflow.js:fetchPendingReviewCount()` | `curationsAPI.getCurations` | dynamic import + in_review filter | WIRED | Lines 195-206: dynamic import, in_review query, 4-eyes filter |
| `MainNavigation.vue` | `workflowStore.fetchPendingReviewCount()` | setInterval 60s + onMounted | WIRED | Lines 85-98: interval started on mount, stopped on unmount |
| `MainNavigation.vue curationItems` | `BaseNavigationItem :badge` | computed conditional badge | WIRED | Lines 139-143: badge is count when > 0, null when 0 |
| `CurationDetailView.vue canReview` | `curation.can_review` (backend) | API response field | WIRED | `canReview` computed reads `curation.value?.can_review` which is now correctly True for eligible reviewers |
| `_can_user_review_curation()` | `CurationStatus.IN_REVIEW` | status check | WIRED | Line 90: `!= CurationStatus.IN_REVIEW`. Fix confirmed by grep: no SUBMITTED reference in this function. |
| `CurationDetailView.vue:loadCurationSchema()` | `schemasAPI.getWorkflowPairById` | workflow_pair_id lookup | WIRED | Line 745: `await schemasAPI.getWorkflowPairById(curation.value.workflow_pair_id)`. `schemasAPI` exported from `@/api/index.js` line 3. |
| `CurationDetailView.vue template` | `DynamicForm :schema-id :readonly` | `v-if="curationSchemaId"` | WIRED | Lines 326-343: DynamicForm renders when schema ID is loaded; passes evidence_data as initial-data |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| SQL injection fix (M1-01) | SATISFIED | Parameterized queries verified |
| Query length validation (M1-01) | SATISFIED | field_validator + max_length verified |
| ReviewQueue correct status filter (M1-02) | SATISFIED | in_review filter verified |
| ReviewQueue 4-eyes client filter (M1-02) | SATISFIED | created_by filter verified |
| Workflow store pendingReviewCount (M1-02) | SATISFIED | State + action verified |
| Workflow API clean endpoints (M1-02) | SATISFIED | Redirected to existing endpoints |
| Navigation badge (M1-03) | SATISFIED | Badge wiring verified |
| Approve/Reject end-to-end (M1-04) | SATISFIED | can_review now True for IN_REVIEW curations; buttons render |
| 4-eyes enforcement (M1-04) | SATISFIED | Backend enforces at _can_user_review_curation + workflow_engine |
| Read-only evidence display (M1-05) | SATISFIED | DynamicForm :readonly="true" wired via schema fetch |
| Test regression (all tests pass) | SATISFIED | 104 backend + 428 frontend = 532 total passing |

### Anti-Patterns Found

None. No blocker anti-patterns detected in modified files.

### Human Verification Required

The following items require manual browser testing to confirm end-to-end behavior. All automated checks pass, but the goal "curations can be approved by independent reviewers" requires human interaction to fully verify.

#### 1. Approve Button Renders for Eligible Reviewer

**Test:** Log in as User A (curator). Create a curation and submit it for review. Log in as User B (different curator or reviewer in the same scope). Navigate to the Review Queue. Click the curation. Check the action bar.
**Expected:** Approve and Request Changes buttons are visible. The "No actions available" message is NOT shown.
**Why human:** Button rendering depends on the backend returning `can_review: true`, which requires a live database session with real workflow transitions.

#### 2. Approve Transition Works End-to-End

**Test:** As User B (not the creator), click Approve on a curation in IN_REVIEW status.
**Expected:** Curation status changes to ACTIVE. A success notification appears. The page updates to show the new status. The curation disappears from the Review Queue.
**Why human:** Requires live API call to `/curations/{id}/transition` and real PostgreSQL RLS context to verify the full transition DAG.

#### 3. Request Changes Transition Works End-to-End

**Test:** As User B, click Request Changes on a curation in IN_REVIEW status. Enter a comment.
**Expected:** Curation returns to CURATION stage. Original curator can see the review comment. Badge count decreases.
**Why human:** Requires live workflow engine execution and comment persistence.

#### 4. 4-Eyes Enforcement in Browser

**Test:** Log in as User A. Submit a curation for review. Navigate to that same curation's detail view while still logged in as User A.
**Expected:** No Approve or Request Changes buttons appear. "No actions available" message is shown.
**Why human:** Requires live session to confirm `can_review: false` is returned and UI gate works.

#### 5. Evidence Details Section Renders

**Test:** Navigate to any curation detail view that has a `workflow_pair_id` set.
**Expected:** Below the "Evidence Score Breakdown" card, an "Evidence Details" card appears with read-only form fields populated from the curation's evidence data.
**Why human:** Depends on a curation having a valid `workflow_pair_id` that maps to a real workflow pair with a `curation_schema_id`. The DynamicForm is schema-driven and its rendering depends on real schema data in the database.

#### 6. Review Queue Badge Count Updates

**Test:** Log in as User B. Observe the "Review Queue" nav item badge. Have User A submit a curation for review. Wait up to 60 seconds (auto-refresh interval).
**Expected:** The badge count increases by 1 to reflect the new pending review.
**Why human:** Real-time behavior that depends on the setInterval polling cycle and live database state.

### Gaps Summary

No gaps remain. Both previously identified gaps have been resolved:

1. **Gap 1 closed (M1-04):** `_can_user_review_curation()` in `curations.py` now correctly checks `CurationStatus.IN_REVIEW` (was `CurationStatus.SUBMITTED`). Three new regression tests confirm correct behavior. The `canReview` computed in `CurationDetailView.vue` will now be `true` for eligible reviewers, rendering the Approve and Request Changes buttons.

2. **Gap 2 closed (M1-05):** `CurationDetailView.vue` now imports `DynamicForm` and renders it in read-only mode below the existing score breakdown tables. The schema ID is fetched via `schemasAPI.getWorkflowPairById(curation.workflow_pair_id)` to obtain `curation_schema_id`. The section renders conditionally via `v-if="curationSchemaId"` so graceful degradation applies if the schema fetch fails.

All 7 success criteria from the ROADMAP are now satisfied at the structural verification level. Human browser testing is required to confirm end-to-end behavior in a live environment.

---

_Verified: 2026-02-28T10:12:00Z_
_Verifier: Claude (gsd-verifier)_
