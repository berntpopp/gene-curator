---
phase: M1-security-review-workflow
plan: "03"
subsystem: ui
tags: [vue, pinia, navigation, badge, workflow, polling]

# Dependency graph
requires:
  - phase: M1-02
    provides: fetchPendingReviewCount() action in workflow store
  - phase: M1-01
    provides: parameterized gene search queries (SQL injection fix)
provides:
  - Review Queue nav item shows live pending review count badge
  - 60-second auto-refresh interval with cleanup on unmount
  - End-to-end M1 review workflow verified via Playwright
affects:
  - M1-04 (review workflow UI for curation detail view)
  - M1-05 (review actions may update badge count in real time)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Badge polling pattern: onMounted interval fetch, onUnmounted clearInterval cleanup, silent failure to prevent nav breakage"
    - "Computed map with conditional badge: null when count is 0 (hides badge), count value when > 0"

key-files:
  created: []
  modified:
    - frontend/src/components/navigation/MainNavigation.vue

key-decisions:
  - "Silent failure in refreshBadgeCount: badge refresh errors are caught and suppressed to prevent navigation from breaking on transient API failures"
  - "badge: null vs badge: 0 — returning null hides the badge entirely when count is 0; returning 0 shows a '0' badge which is misleading"
  - "isAuthenticated guard on onMounted: interval only starts when user is logged in, avoids unauthenticated API calls"

patterns-established:
  - "Badge polling: use setInterval on onMounted, clearInterval on onUnmounted, silent try/catch for resilience"

# Metrics
duration: ~15min
completed: 2026-02-28
---

# Phase M1 Plan 03: Navigation Badge and E2E Verification Summary

**Review Queue nav badge wired to live pendingReviewCount with 60s auto-refresh; full M1 review workflow (SQL injection fix, queue filter, badge) verified end-to-end via Playwright with all 101 backend and 428 frontend tests passing**

## Performance

- **Duration:** ~15 min (including E2E Playwright verification)
- **Started:** 2026-02-28T09:05:00Z
- **Completed:** 2026-02-28T10:06:01Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Wired `fetchPendingReviewCount()` (added in M1-02) into `MainNavigation.vue` with 60-second polling interval
- Badge on Review Queue nav item shows pending count when > 0; hidden (null) when count is 0
- Interval is properly cleared in `onUnmounted` — no memory leaks
- isAuthenticated guard prevents unauthenticated API calls during badge refresh
- E2E verification via Playwright confirmed: login works, SQL injection payload treated as literal text, Review Queue page loads correctly, badge correctly hidden when 0 reviews
- All 101 backend tests pass, all 428 frontend tests pass, lint clean on both sides

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire review notification badge to Review Queue nav item** - `2789922` (feat)
2. **Task 2: Human-verify checkpoint** - no commit (approval only)

**Plan metadata:** `(pending)` (docs: complete plan)

## Files Created/Modified

- `frontend/src/components/navigation/MainNavigation.vue` - Added `ref`, `onMounted`, `onUnmounted` imports; added `useWorkflowStore` import; added `pendingReviewCount` ref, `badgeRefreshInterval`, `refreshBadgeCount()`, and lifecycle hooks; updated `curationItems` computed to include conditional badge; passed `:badge` and `:badge-color` props to `BaseNavigationItem`

## Decisions Made

- **Silent failure in badge refresh:** `refreshBadgeCount()` wraps the store call in try/catch and silently suppresses errors. Navigation must not break due to badge API failures; the badge is informational only.
- **badge: null when count is 0:** Returning `null` hides the badge entirely. Returning `0` would render a misleading "0" badge. This matches UX convention — only show the badge when there is something to act on.
- **isAuthenticated guard on mount:** The interval only starts when `isAuthenticated.value` is true, preventing unnecessary API calls for unauthenticated users (e.g., on the login page).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all changes were straightforward. E2E verification via Playwright confirmed all M1 functionality works correctly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full M1 security + navigation badge layer is complete: SQL injection fixed (M1-01), ReviewQueue filter correct (M1-02), notification badge live (M1-03)
- All 101 backend tests pass, all 428 frontend tests pass, both lint checks clean
- Ready for M1-04: review action buttons (Approve/Request Changes) wired end-to-end in CurationDetailView
- No blockers identified

---
*Phase: M1-security-review-workflow*
*Completed: 2026-02-28*
