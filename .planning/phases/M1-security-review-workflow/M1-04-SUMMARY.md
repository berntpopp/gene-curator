---
phase: M1-security-review-workflow
plan: "04"
subsystem: backend
tags: [fastapi, permissions, review-workflow, 4-eyes, testing, curations]

# Dependency graph
requires:
  - phase: M1-03
    provides: Navigation badge + E2E review workflow verified
  - phase: M1-02
    provides: Review queue filter and workflow store actions
  - phase: M1-01
    provides: Parameterized gene search queries (SQL injection fix)
provides:
  - _can_user_review_curation correctly returns True for IN_REVIEW curations by other users
  - 4-eyes principle enforced: cannot review own curation
  - 3 regression tests covering can_review field behavior
affects:
  - M1-05 (review action buttons in CurationDetailView depend on can_review=True)
  - Future review workflow tests (TestCanReviewPermission as reference pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "can_review permission check: IN_REVIEW status + 4-eyes principle (created_by != current_user) + scope role check"
    - "TestCanReviewPermission: inline CurationNew creation in tests with explicit status/workflow_stage for permission boundary testing"

key-files:
  created: []
  modified:
    - backend/app/api/v1/endpoints/curations.py
    - backend/tests/api/test_curations.py

key-decisions:
  - "Use CurationStatus.IN_REVIEW (not SUBMITTED) in _can_user_review_curation: workflow_engine.submit_for_review() sets status=in_review, not submitted"
  - "Comment on line 89 already said 'Must be in review status/stage' — code was using wrong enum value, single-line fix sufficient"
  - "TestCanReviewPermission tests create CurationNew directly in db_session rather than going through the API, for precise status control"

patterns-established:
  - "Permission boundary tests: create model objects directly in db_session with exact status values, then GET via client to inspect computed permission fields"

# Metrics
duration: ~5min
completed: 2026-02-28
---

# Phase M1 Plan 04: Fix _can_user_review_curation Status Check Summary

**Fixed 1-line bug where `_can_user_review_curation` checked `CurationStatus.SUBMITTED` instead of `CurationStatus.IN_REVIEW`, unblocking Approve/Request Changes buttons; added 3 regression tests covering the 4-eyes principle and status boundary — 104 backend tests now passing**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-28T10:05:33Z
- **Completed:** 2026-02-28T10:10:00Z
- **Tasks:** 2 (both auto)
- **Files modified:** 2

## Accomplishments

- Fixed `_can_user_review_curation()` in `curations.py`: line 90 now checks `CurationStatus.IN_REVIEW` instead of `CurationStatus.SUBMITTED`
- The workflow engine sets `status=in_review` (not `submitted`) when a curation is submitted for review — the old check caused `can_review` to always return False, blocking the entire review UI
- Admin bypass (line 94) and 4-eyes check (line 86) and scope role check (lines 98-99) were all correct and left unchanged
- Added `TestCanReviewPermission` class with 3 tests:
  - `test_can_review_true_for_in_review_curation`: can_review is True for IN_REVIEW curation created by different user
  - `test_can_review_false_for_draft_curation`: can_review is False for draft curations
  - `test_can_review_false_for_own_curation`: can_review is False even for IN_REVIEW when admin is the creator (4-eyes)
- Total backend tests: 104 passing (101 + 3 new)
- Linting passes with no issues

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix _can_user_review_curation status check** - `8a325ef` (fix)
2. **Task 2: Add tests for _can_user_review_curation** - `90615d4` (test)

**Plan metadata:** `(pending)` (docs: complete plan)

## Files Created/Modified

- `backend/app/api/v1/endpoints/curations.py` - Line 90: `CurationStatus.SUBMITTED` → `CurationStatus.IN_REVIEW`
- `backend/tests/api/test_curations.py` - Added `TestCanReviewPermission` class with 3 new tests

## Decisions Made

- **Single-line fix only:** The comment on line 89 already said "Must be in review status/stage" — only the wrong enum value needed correcting; no other logic changes required
- **IN_REVIEW is the correct status:** `workflow_engine.py::submit_for_review()` sets `status=CurationStatus.IN_REVIEW`; the `SUBMITTED` value exists but is not used in this code path
- **Inline model creation in tests:** Tests create `CurationNew` directly in `db_session` with explicit `status="in_review"` rather than going through workflow transitions, giving precise control over permission boundary conditions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The fix was exactly 1 line as predicted. All 3 tests passed on first run. Linting was clean.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `can_review` now correctly returns True for reviewable curations — Approve/Request Changes buttons in CurationDetailView will render
- All 104 backend tests pass, lint clean
- Ready for M1-05: wire Approve/Request Changes/Reject action buttons in CurationDetailView to the backend peer review endpoint
- No blockers identified

---
*Phase: M1-security-review-workflow*
*Completed: 2026-02-28*
