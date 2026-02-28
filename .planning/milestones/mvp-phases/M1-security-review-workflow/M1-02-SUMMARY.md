---
phase: M1-security-review-workflow
plan: "02"
subsystem: ui
tags: [vue, pinia, workflow, review-queue, api]

# Dependency graph
requires: []
provides:
  - ReviewQueueView fetches curations with correct 'in_review' status filter
  - Workflow store exposes pendingReviewCount state and fetchPendingReviewCount() action
  - Workflow API module uses only existing backend endpoints
affects:
  - M1-03 (notification badge will call fetchPendingReviewCount())
  - M1-04 (review workflow UI depends on correct queue data)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dynamic imports in Pinia store actions to avoid circular dependency chains"
    - "4-eyes principle: filter own curations client-side after fetching in_review set"

key-files:
  created: []
  modified:
    - frontend/src/views/curation/ReviewQueueView.vue
    - frontend/src/stores/workflow.js
    - frontend/src/api/workflow.js

key-decisions:
  - "Use dynamic imports (import('@/api'), import('@/stores/auth')) inside fetchPendingReviewCount to avoid circular deps since workflow store is imported broadly"
  - "Redirect getAvailableTransitions to /state endpoint (returns available_transitions in response body)"
  - "Redirect submitPeerReview to /transition endpoint (dedicated /review endpoint does not exist)"

patterns-established:
  - "Dynamic imports pattern: use import() inside Pinia actions when static top-level imports risk circular dependency"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase M1 Plan 02: Review Queue Fix and Workflow Store Enhancement Summary

**ReviewQueueView corrected to use 'in_review' status filter; workflow store gains pendingReviewCount state and fetchPendingReviewCount() action; workflow API redirected from non-existent endpoints to existing /state and /transition endpoints**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T09:00:38Z
- **Completed:** 2026-02-28T09:01:53Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Fixed ReviewQueueView to fetch curations with `curation_status: 'in_review'` instead of `'submitted'` - the queue now shows curations that are actually in the review stage
- Added `pendingReviewCount: 0` state and `fetchPendingReviewCount()` action to workflow store, enabling the notification badge in Plan M1-03 to display live counts
- Fixed two non-existent API endpoint calls: `getAvailableTransitions` now uses `/state` endpoint (which returns `available_transitions`), and `submitPeerReview` now uses `/transition` endpoint

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix ReviewQueueView to use correct status filter** - `65b5544` (fix)
2. **Task 2: Add fetchPendingReviewCount to workflow store and clean up API** - `e43c36f` (feat)

**Plan metadata:** `(pending)` (docs: complete plan)

## Files Created/Modified

- `frontend/src/views/curation/ReviewQueueView.vue` - Changed `curation_status: 'submitted'` to `'in_review'` in `fetchPendingReviews()`
- `frontend/src/stores/workflow.js` - Added `pendingReviewCount: 0` state; added `fetchPendingReviewCount()` action using dynamic imports
- `frontend/src/api/workflow.js` - Fixed `getAvailableTransitions` (now hits `/state`), fixed `submitPeerReview` (now hits `/transition`)

## Decisions Made

- **Dynamic imports in fetchPendingReviewCount:** Used `await import('@/api')` and `await import('@/stores/auth')` inside the action body rather than static top-level imports. The workflow store is imported widely; static imports of `curationsAPI` and `useAuthStore` could create circular dependency chains because `auth` store and `api` module may transitively import workflow-related modules.
- **No getter for pendingReviewCount:** Pinia Options API auto-exposes state properties directly. A getter with the same name would shadow or conflict with state, so the state property `workflowStore.pendingReviewCount` is used directly by consumers.
- **Keep submitPeerReview method:** Rather than deleting the non-existent `/review` endpoint call, redirected it to `/transition`. Existing code calling `submitPeerReview` in the workflow store won't break, and it will hit the correct backend endpoint.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all changes were straightforward. ESLint auto-formatter collapsed the multiline `submitPeerReview` call to a single line (cosmetic only, no logic change).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ReviewQueue correctly shows `in_review` curations, ready for M1-04 (review action buttons)
- `fetchPendingReviewCount()` ready for M1-03 (notification badge to call on mount/interval)
- All 428 frontend tests passing, lint clean (0 errors, 12 pre-existing warnings)
- No blockers for M1-03

---
*Phase: M1-security-review-workflow*
*Completed: 2026-02-28*
