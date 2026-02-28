---
phase: M1-security-review-workflow
plan: "05"
subsystem: ui
tags: [vue, dynamic-forms, readonly, schema-agnostic, curation-detail, review-workflow]

# Dependency graph
requires:
  - phase: M1-04
    provides: review action buttons (Approve/Request Changes) in CurationDetailView
  - phase: v0.1
    provides: DynamicForm component with readonly prop support
provides:
  - CurationDetailView renders read-only DynamicForm below score breakdown tables
  - Schema ID fetched via workflow pair (schemasAPI.getWorkflowPairById)
  - Graceful degradation when schema fetch fails (score tables still show)
affects:
  - M1-06 (final review workflow hardening and testing)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Schema-agnostic read-only display: fetch workflow_pair_id -> curation_schema_id -> render DynamicForm :readonly='true'"
    - "Graceful degradation pattern: non-fatal schema fetch failure, supplementary section omitted without breaking core view"

key-files:
  created: []
  modified:
    - frontend/src/views/curation/CurationDetailView.vue

key-decisions:
  - "v-if='curationSchemaId' gates Evidence Details section: only renders when schema successfully loaded, no error state needed since section is supplementary"
  - "title='' passed to DynamicForm: avoids redundant 'Dynamic Form' title inside card that already has 'Evidence Details' title"
  - "loadCurationSchema() is non-fatal: catches errors, logs warning, leaves curationSchemaId as null so v-if hides the section"
  - "await loadCurationSchema() called inside loadCuration() try block: schema loads immediately after curation data, before finally block sets loading=false"

patterns-established:
  - "Read-only DynamicForm embedding: import DynamicForm, fetch schema ID from workflow pair, render with :readonly='true' and :initial-data from curation.evidence_data"

# Metrics
duration: ~5min
completed: 2026-02-28
---

# Phase M1 Plan 05: Schema-Agnostic Evidence Display Summary

**DynamicForm wired read-only into CurationDetailView via workflow pair schema lookup, enabling reviewers to see all evidence fields schema-agnostically alongside the existing ClinGen score breakdown tables**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-28T10:05:51Z
- **Completed:** 2026-02-28T10:10:00Z
- **Tasks:** 1 (fully autonomous)
- **Files modified:** 1

## Accomplishments

- Imported `DynamicForm` component and `schemasAPI` into `CurationDetailView.vue`
- Added `curationSchemaId` and `loadingSchema` state refs
- Added `loadCurationSchema()` function that fetches the workflow pair by `workflow_pair_id` to extract `curation_schema_id` (non-fatal on failure)
- Called `loadCurationSchema()` from within `loadCuration()` so schema loads immediately after curation data
- Added "Evidence Details" card section in template with `<DynamicForm :schema-id="curationSchemaId" :initial-data="curation.evidence_data || {}" :readonly="true" title="" />`
- Section uses `v-if="curationSchemaId"` for graceful degradation — omitted entirely when schema unavailable
- Existing hardcoded ClinGen score breakdown tables preserved as summary view
- All 428 frontend tests pass, lint clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire DynamicForm read-only evidence display into CurationDetailView** - `cbabe47` (feat)

**Plan metadata:** `(pending)` (docs: complete plan)

## Files Created/Modified

- `frontend/src/views/curation/CurationDetailView.vue` - Added `DynamicForm` import, `schemasAPI` import, `curationSchemaId` ref, `loadingSchema` ref, `loadCurationSchema()` function, Evidence Details template section

## Decisions Made

- **Non-fatal schema fetch:** `loadCurationSchema()` uses try/catch with `logger.warn()` on failure. The Evidence Details section is supplementary — score tables remain the primary display. If schema fetch fails, the view degrades gracefully without an error state.
- **v-if="curationSchemaId":** Gates the entire Evidence Details card on successful schema ID resolution. No loading spinner needed since the main loading overlay already covers the initial load.
- **title="":** Passes empty string to `DynamicForm` title prop to prevent the default "Dynamic Form" title text from appearing inside the card that already has "Evidence Details" as its header.
- **await loadCurationSchema():** Called with `await` inside the `try` block of `loadCuration()`, ensuring schema loads atomically with curation data. If `loadCurationSchema` fails, the outer `catch` does NOT catch it (it has its own catch) — only the `finally` block runs.

## Deviations from Plan

None - plan executed exactly as written. `schemasAPI` was already exported from `@/api/index.js`, so no direct import path was needed.

## Issues Encountered

None - straightforward wiring task. DynamicForm `readonly` prop was already fully supported from v0.1.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- M1-05 complete: Evidence Details section renders all curation form fields schema-agnostically in read-only mode
- Reviewers can now see full evidence form alongside score summary in CurationDetailView
- All 428 frontend tests pass, lint clean
- Ready for M1-06: final review workflow hardening, integration testing, and E2E verification
- No blockers identified

---
*Phase: M1-security-review-workflow*
*Completed: 2026-02-28*
