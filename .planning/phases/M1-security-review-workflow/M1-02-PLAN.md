---
phase: M1-security-review-workflow
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/views/curation/ReviewQueueView.vue
  - frontend/src/stores/workflow.js
  - frontend/src/api/workflow.js
autonomous: true

must_haves:
  truths:
    - "ReviewQueue shows curations with status 'in_review' (not 'submitted')"
    - "ReviewQueue filters out current user's own curations (4-eyes principle)"
    - "Workflow store has fetchPendingReviewCount() that returns pending review count"
    - "Workflow API module does not call non-existent endpoints"
  artifacts:
    - path: "frontend/src/views/curation/ReviewQueueView.vue"
      provides: "Working review queue showing in_review curations"
      contains: "in_review"
    - path: "frontend/src/stores/workflow.js"
      provides: "pendingReviewCount state and fetchPendingReviewCount action"
      contains: "pendingReviewCount"
    - path: "frontend/src/api/workflow.js"
      provides: "Clean API methods without non-existent endpoint calls"
  key_links:
    - from: "frontend/src/views/curation/ReviewQueueView.vue"
      to: "curationsAPI.getCurations"
      via: "fetchPendingReviews with curation_status: 'in_review'"
      pattern: "curation_status.*in_review"
    - from: "frontend/src/stores/workflow.js"
      to: "curationsAPI.getCurations"
      via: "fetchPendingReviewCount uses in_review status"
      pattern: "in_review"
---

<objective>
Fix the ReviewQueue view to show curations actually in review, add pending review count to the workflow store, and clean up API mismatches.

Purpose: The ReviewQueueView currently fetches curations with status 'submitted' but should use 'in_review'. The workflow store lacks `fetchPendingReviewCount()` needed by the notification badge (Plan 03). The workflow API module calls non-existent backend endpoints that need to be fixed or removed.

Output: Working ReviewQueue that shows the correct curations, workflow store with pending review count capability, clean API module.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/MVP-PLAN.md
@.planning/phases/M1-security-review-workflow/M1-RESEARCH.md

Key source files:
@frontend/src/views/curation/ReviewQueueView.vue
@frontend/src/stores/workflow.js
@frontend/src/api/workflow.js
@frontend/src/views/curation/CurationDetailView.vue (reference — already has approve/reject wired correctly)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix ReviewQueueView to use correct status filter</name>
  <files>frontend/src/views/curation/ReviewQueueView.vue</files>
  <action>
In `frontend/src/views/curation/ReviewQueueView.vue`, fix the `fetchPendingReviews()` function (line 281):

1. Change the API call status filter from `'submitted'` to `'in_review'`:
```javascript
const response = await curationsAPI.getCurations({
  curation_status: 'in_review',  // FIXED: was 'submitted'
  limit: 200
})
```

The rest of the function is correct — it already:
- Maps curation data correctly (lines 286-301)
- Filters out current user's curations for 4-eyes principle (lines 303-305)
- Extracts unique scopes for the filter dropdown (lines 307-314)

No other changes needed in this file. The template, computed properties, sort/filter logic, and formatRelativeTime are all correct.

NOTE: The `useLogger` import uses `@/composables/useLogger` (correct per CLAUDE.md). The `useNotificationsStore` import uses `@/stores/notifications` (correct).
  </action>
  <verify>
Run `cd /home/bernt-popp/development/gene-curator && make test-frontend` to confirm all frontend tests pass. Then verify with: `grep -n "curation_status" frontend/src/views/curation/ReviewQueueView.vue` shows `'in_review'` (not `'submitted'`).
  </verify>
  <done>ReviewQueueView fetches curations with `curation_status: 'in_review'`. Frontend tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Add fetchPendingReviewCount to workflow store and clean up API</name>
  <files>frontend/src/stores/workflow.js, frontend/src/api/workflow.js</files>
  <action>
**Part A: Update `frontend/src/stores/workflow.js`**

1. Add `pendingReviewCount: 0` to the state (after `currentWorkflowStage: null`, around line 63).

2. Add a new `fetchPendingReviewCount` action. This action fetches curations with `in_review` status, filters out the current user's own curations (4-eyes), and updates `pendingReviewCount`. Add it after the existing `fetchWorkflowStatistics` action (around line 190):

```javascript
async fetchPendingReviewCount() {
  try {
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

NOTE: Use dynamic imports for `curationsAPI` and `useAuthStore` to avoid circular dependency issues. The workflow store currently only imports `workflowAPI` (line 2). Adding static imports of `curationsAPI` and `useAuthStore` at the top could create circular import chains because `auth` store may import workflow-related modules.

3. Add a getter for the pending count (in the getters section, after `getWorkflowStageStats`):
```javascript
pendingReviewCount: state => state.pendingReviewCount,
```

Wait — `pendingReviewCount` is both a state property and the getter would shadow it. Pinia Options API auto-exposes state properties, so a getter with the same name would conflict. Instead, skip the getter — the state property `pendingReviewCount` is already accessible directly via `workflowStore.pendingReviewCount`.

**Part B: Clean up `frontend/src/api/workflow.js`**

The research identified two API methods that call non-existent backend endpoints:

1. `getAvailableTransitions(curationId)` calls `/workflow/curation/${curationId}/available-transitions` — this endpoint does NOT exist. However, the workflow store's `fetchAvailableTransitions` action uses it. For safety, update the URL to use the workflow state endpoint which DOES exist and returns available transitions:

```javascript
async getAvailableTransitions(curationId) {
  // Uses workflow state endpoint which returns available_transitions in response
  const response = await apiClient.get(`/workflow/curation/${curationId}/state`)
  return response.data?.available_transitions || []
},
```

2. `submitPeerReview(curationId, reviewData)` calls `/workflow/curation/${curationId}/review` — this endpoint does NOT exist. The correct approach (already used by CurationDetailView) is `transitionCuration()`. However, the workflow store has a `submitPeerReview` action that calls this method. Do NOT delete the API method — instead, redirect it to use the transition endpoint:

```javascript
async submitPeerReview(curationId, reviewData) {
  // Uses transition endpoint — the dedicated review endpoint does not exist
  // CurationDetailView already uses transitionCuration() directly for approve/reject
  const response = await apiClient.post(
    `/workflow/curation/${curationId}/transition`,
    reviewData
  )
  return response.data
},
```

This way existing code calling `submitPeerReview` won't break, and it will use the correct backend endpoint.
  </action>
  <verify>
Run `cd /home/bernt-popp/development/gene-curator && make test-frontend` to confirm all frontend tests pass. Run `make lint-frontend` to confirm no lint issues. Then verify:
- `grep -n "pendingReviewCount" frontend/src/stores/workflow.js` shows state property and action
- `grep -n "fetchPendingReviewCount" frontend/src/stores/workflow.js` shows the new action
- `grep -n "available-transitions" frontend/src/api/workflow.js` returns zero results (removed non-existent URL)
- `grep -n "/review\"" frontend/src/api/workflow.js` returns zero results (removed non-existent URL)
  </verify>
  <done>Workflow store has `pendingReviewCount` state and `fetchPendingReviewCount()` action. Workflow API methods redirect to existing backend endpoints. Frontend tests pass, lint clean.</done>
</task>

</tasks>

<verification>
1. `grep "in_review" frontend/src/views/curation/ReviewQueueView.vue` confirms correct status filter
2. `grep "pendingReviewCount" frontend/src/stores/workflow.js` shows state + action
3. `grep "available-transitions" frontend/src/api/workflow.js` returns zero (non-existent URL removed)
4. `cd frontend && npm run test:run -- --reporter=verbose` passes all tests
5. `make lint-frontend` passes
</verification>

<success_criteria>
- ReviewQueue fetches curations with 'in_review' status (not 'submitted')
- ReviewQueue still filters out current user's curations (4-eyes principle UX)
- Workflow store exposes `pendingReviewCount` state and `fetchPendingReviewCount()` action
- No API calls to non-existent backend endpoints
- All frontend tests pass, lint clean
</success_criteria>

<output>
After completion, create `.planning/phases/M1-security-review-workflow/M1-02-SUMMARY.md`
</output>
