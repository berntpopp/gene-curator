# Gene Curator MVP Plan

**Created:** 2026-02-28
**Goal:** Ship a working MVP that enables end-to-end gene-disease curation by a team of curators and reviewers.

## Executive Summary

The platform is ~85% built. Backend API, database, auth, workflows, dynamic forms, and scoring engines are all functional. The gap is **completing the end-to-end user workflow** so a real clinical genetics team can:

1. Assign genes to curators within a scope
2. Precurate and curate genes using schema-driven forms
3. Submit curations for independent peer review (4-eyes principle)
4. Approve/reject/revise curations through the review workflow
5. Manage assignments and workflows through the admin UI

**Zero open bugs. CI green. 529 tests passing.**

---

## What "MVP" Means

An MVP is the minimum feature set where a clinical genetics team can use Gene Curator for real curation work. Specifically:

- A scope admin can create a scope, invite members, configure a workflow
- A curator can be assigned genes, precurate them, curate them with evidence
- A reviewer can independently review and approve/reject curations
- The workflow enforces quality (4-eyes principle, stage transitions)
- Forms are schema-driven (ClinGen, GenCC, or custom methodology)

**What MVP is NOT:** search, pagination optimization, backup systems, analytics dashboards, conditional form logic, AI features. These are post-MVP improvements.

---

## Current State Assessment

### What's Built and Working

| Area | Status | Details |
|------|--------|---------|
| Auth & Users | Done | JWT auth, dual-role system (app + scope), invitation flow |
| Scopes | Done | Create, configure, manage members with roles |
| Gene Catalogue | Done | HGNC integration, gene lookup, assignment |
| Schema System | Done | 4 schemas configured, JSONB field_definitions, scoring engines |
| Dynamic Forms | Done | Schema-driven rendering, tabs, validation, scoring (v0.1 shipped) |
| Workflow Engine | Done | 5-stage pipeline, state machine, transition validation |
| Precuration | Done | Create, edit, schema-driven forms, scoring |
| Curation | Done | Create, edit, evidence storage, schema-driven forms |
| Review Backend | Done | Reviews table, 4-eyes enforcement, workflow transitions |
| API Endpoints | Done | 21 endpoint modules covering all domains |
| Frontend Views | Done | 28 pages covering all major areas |
| CI/CD | Done | GitHub Actions, path filtering, security scanning |

### What's Missing for MVP

| Gap | Issue(s) | Priority | Effort |
|-----|----------|----------|--------|
| Review workflow frontend | #116 | **Critical** | 2-3 days |
| Precuration card enhancements | #61 | High | 1-2 days |
| Workflow prefill logic | #77 | Medium | 1-2 days |
| Gene assignment edit/reassign | #119 | Medium | 1 day |
| Workflow management views | #118 | Medium | 1 day |
| SQL injection fix in gene search | CONCERNS.md | **Critical** (security) | 0.5 day |
| Precuration deletion guard | #87 | Medium | 0.5 day |

---

## MVP Phases

### Phase M1: Security Fix + Review Workflow (Critical Path)

**Goal:** Fix the SQL injection vulnerability and complete the 4-eyes review workflow so curations can be approved by independent reviewers.

**Why first:** The review workflow is the #1 MVP blocker. Without it, curations cannot progress past the "submitted" stage. The SQL injection is a security issue that should be fixed before any production use.

#### Tasks

**M1.1 — Fix SQL injection in gene search** (Issue: CONCERNS.md)
- Fix `backend/app/crud/gene.py` lines 51, 89, 92-93: replace `text(f"...")` with parameterized queries
- Use SQLAlchemy array operators instead of raw SQL text
- Add input validation for gene symbol format
- Files: `backend/app/crud/gene.py`

**M1.2 — Complete ReviewQueue view** (Issue #116)
- The `ReviewQueueView.vue` already exists — assess current state and complete it
- Wire to workflow store for fetching curations in review status
- Filter by current user's assigned reviews across scopes
- Data table with gene, curator, scope, submitted date, verdict columns
- Click to navigate to curation review
- Reference: `.planning/archive/plan/enhancements/010-review-workflow-4eyes.md`

**M1.3 — Build CurationReview interface** (Issue #116)
- Read-only DynamicForm display of curation evidence
- Score and verdict display
- Review comment textarea (required for reject/needs_revision)
- Approve / Request Revision / Reject action buttons with confirmation dialog
- Previous review history timeline (for multi-round reviews)
- Reference: `.planning/archive/plan/enhancements/010-review-workflow-4eyes.md`

**M1.4 — Wire workflow store review methods** (Issue #116)
- `fetchPendingReviews()` — curations awaiting current user's review
- `submitReview(curationId, { status, comments })` — submit review decision
- `fetchReviewHistory(curationId)` — previous review rounds
- `getPendingReviewCount()` — for notification badge

**M1.5 — Review notification badge** (Issue #116)
- Badge on Review Queue nav item showing pending count
- Auto-refresh every 60 seconds
- Reference: `.planning/archive/plan/enhancements/010-review-workflow-4eyes.md`

**M1.6 — End-to-end review workflow test**
- Test: curator creates curation → submits for review → reviewer sees it in queue → reviewer approves → curation becomes active
- Test: reviewer rejects → curation returns to curator → curator edits → resubmits
- Test: reviewer cannot review own curation (4-eyes enforcement)

**Acceptance Criteria:**
- [ ] Gene search uses parameterized queries (no SQL injection)
- [ ] ReviewQueue shows pending reviews for current user
- [ ] CurationReview displays evidence read-only with score
- [ ] Approve/Reject/Request Revision all work end-to-end
- [ ] Review comments required for reject/needs_revision
- [ ] Review history displayed for multi-round reviews
- [ ] Notification badge shows pending review count
- [ ] 4-eyes principle enforced (cannot review own curation)
- [ ] All existing tests still pass

---

### Phase M2: Precuration & Curation Enhancements

**Goal:** Improve the daily curator experience with better prefilling, validation, and form flow.

**Why second:** Once the review workflow works, the next bottleneck is curator efficiency. These enhancements reduce manual data entry and prevent errors.

#### Tasks

**M2.1 — Enhance precuration card** (Issue #61)
- Input validation for lump/split recommendation fields (prevent accidental overwriting)
- Ensure prefilling from gene card data works correctly with DynamicForm
- Verify scoring display integrates properly
- Files: `frontend/src/views/CreatePrecuration.vue`, `PrecurationDetail.vue`

**M2.2 — Implement workflow prefill logic** (Issue #77)
- Read `workflow_pairs.data_mapping` to determine precuration→curation field mapping
- When creating a curation from a precuration, auto-populate mapped fields
- Provide defaults/fallbacks for unmapped fields
- Files: `frontend/src/views/CreateCuration.vue`, `frontend/src/stores/workflow.js`

**M2.3 — Prevent deletion of precuration with associated curation** (Issue #87)
- Backend check: before deleting precuration, verify no linked curations exist
- Return appropriate error message if deletion blocked
- Frontend: disable delete button or show warning when curations exist
- Files: `backend/app/crud/precuration.py`, `backend/app/api/v1/endpoints/precurations.py`

**Acceptance Criteria:**
- [ ] Lump/split fields have validation preventing accidental overwrite
- [ ] Curation form prefills from precuration data via workflow mapping
- [ ] Cannot delete precuration that has associated curations
- [ ] Error messages are clear and actionable
- [ ] All existing tests still pass

---

### Phase M3: Admin Management UI

**Goal:** Complete the admin-facing management interfaces so scope admins can manage assignments and workflows without database access.

**Why third:** These are admin features, not daily curator workflow. Important for self-service but not blocking the core curation loop.

#### Tasks

**M3.1 — Gene assignment edit/reassign dialogs** (Issue #119)
- Edit dialog: update priority, due date, notes
- Reassign dialog: select new curator from scope members, optional note transfer, audit trail
- View dialog: read-only assignment details with history
- Backend API already supports assignment CRUD at `/api/v1/gene-assignments`
- Files: `frontend/src/views/GeneAssignmentManager.vue` (replace placeholder functions at lines 565, 573, 578)

**M3.2 — Workflow management detail/edit views** (Issue #118)
- View modal: workflow pair config, schemas, stages, metadata (read-only)
- Edit dialog: update name, description, schema assignments, active status
- Stage edit dialog: update stage details, roles, order
- Follow pattern from `SchemaManagement.vue` edit dialog
- Files: `frontend/src/views/WorkflowManagement.vue` (replace placeholders at lines 268, 274, 297)

**Acceptance Criteria:**
- [ ] Assignment edit/reassign/view dialogs all functional
- [ ] Assignment changes immediately reflected in list
- [ ] Workflow view/edit/stage-edit dialogs all functional
- [ ] Audit trail maintained for reassignments
- [ ] All actions logged via unified logging system
- [ ] All existing tests still pass

---

### Phase M4: MVP Hardening

**Goal:** Fix remaining tech debt items that affect data quality and user trust before declaring MVP complete.

#### Tasks

**M4.1 — Fix gene summary curator count** (CONCERNS.md)
- Implement actual curator count from curation history (currently hardcoded to 1)
- Files: `backend/app/services/gene_summary_service.py` line 148

**M4.2 — Fix notification store API integration** (CONCERNS.md)
- Uncomment API client imports in notifications store
- Wire to backend notification endpoints
- Enable in-app notifications for review events
- Files: `frontend/src/stores/notifications.js`

**M4.3 — Smoke test all workflow paths**
- Entry → Precuration → Curation → Review → Active (happy path)
- Review → Needs Revision → Re-submit → Approve (revision loop)
- Multiple scopes with different schemas
- Permission checks (curator can't access other scope's data)

**M4.4 — Update documentation**
- Update FAQ with curation/review workflow instructions (Issue #104)
- Verify About page renders correctly
- Update CLAUDE.md if any architectural changes occurred

**Acceptance Criteria:**
- [ ] Gene summary shows actual curator count
- [ ] In-app notifications work for review events
- [ ] All workflow paths tested end-to-end
- [ ] Documentation updated for end users
- [ ] CI passes with all changes

---

## Post-MVP Roadmap (Deferred)

These milestones come AFTER the MVP is working and deployed. None are in the active roadmap.

### v0.2 Form Intelligence (Deferred 2026-02-28)
- Conditional field visibility (show/hide based on other fields)
- Cross-field validation
- Cascading selects, auto-population
- Research preserved in `.planning/research/`
- Requirements preserved in `.planning/REQUIREMENTS.md`

### v0.5.0 Infrastructure & Scalability
- #75 Search functionality
- #67 Pagination with database counters
- #86 Backup system
- #95 Advanced table filters
- #66 Lazy loading / asset optimization

### v1.0.0 Production Ready
- #105 ClinGen classification take-over
- #102 Clinical Groups validation
- #87 Precuration deletion guard (if not done in MVP)
- #104 Detailed instructions (if not done in MVP)

### Backlog
- #120 Schema read-only detail view
- #115 Add transcript to curation
- #46 JSON/CSV file uploads
- #30 Customizable analytics dashboard
- #19 Curation modal enhancement with split tabs

---

## Reference Documents

### Active (in `.planning/`)

| File | Purpose |
|------|---------|
| `.planning/PROJECT.md` | Project charter, core value, constraints |
| `.planning/STATE.md` | Current position, session continuity |
| `.planning/ROADMAP.md` | Phase execution tracking (v0.1 done, MVP in progress, v0.2 planned) |
| `.planning/REQUIREMENTS.md` | v0.2 Form Intelligence requirements |
| `.planning/MILESTONES.md` | Shipped milestone stats |
| `.planning/codebase/CONCERNS.md` | Tech debt, bugs, security issues |
| `.planning/codebase/ARCHITECTURE.md` | System architecture patterns |
| `.planning/codebase/TESTING.md` | Test framework and patterns |
| `.planning/research/FEATURES.md` | v0.2 feature research |
| `.planning/research/ARCHITECTURE.md` | v0.2 integration architecture |
| `.planning/research/PITFALLS.md` | v0.2 pitfalls and prevention |

### Archived (in `.planning/archive/`)

| Directory | Purpose |
|-----------|---------|
| `.planning/archive/docs/` | Former `docs/` directory (WORKFLOW, DATABASE_SCHEMA, etc.) |
| `.planning/archive/plan/` | Former `plan/` directory (moved 2026-02-28) |
| `.planning/archive/plan/PLAN_2_CONFIGURABLE_FOUR_EYES.md` | Detailed 4-eyes refactoring plan (reference for M1) |
| `.planning/archive/plan/enhancements/010-review-workflow-4eyes.md` | Review UI implementation plan (reference for M1) |
| `.planning/archive/plan/SCOPE_PERMISSIONS_AUDIT_REPORT.md` | Security audit findings |
| `.planning/archive/plan/clingen_engine.md` | ClinGen SOP v11 scoring reference |
| `.planning/archive/plan/refactoring/` | Historical refactoring implementation guides |
| `.planning/archive/plan/scripts/clingen_documents/` | ClinGen reference documents (PDFs + markdown) |
| `.planning/milestones/v0.1-ROADMAP.md` | v0.1 phase breakdown |
| `.planning/milestones/v0.1-REQUIREMENTS.md` | v0.1 requirement spec |
| `.planning/milestones/v0.1-MILESTONE-AUDIT.md` | v0.1 completion audit |

### GitHub Issues by Phase

| Phase | Issues |
|-------|--------|
| M1 | #116 (multi-user approval) |
| M2 | #61 (precuration card), #77 (prefill logic), #87 (deletion guard) |
| M3 | #119 (assignment dialogs), #118 (workflow views) |
| M4 | #104 (documentation) |

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| MVP before v0.2 Form Intelligence | v0.2 is form polish; MVP needs the review workflow to be usable |
| Phase M1 first (review workflow) | Without review approval, no curation can reach "active" status |
| SQL injection fix in M1 | Security fix must precede any production use |
| Precuration deletion guard in M2 not v1.0 | Data integrity issue that affects daily use |
| Keep v0.2 research intact | Research is done and valid; just deprioritized behind workflow completion |
| Move plan/ to archive | Historical docs; `.planning/` is the active system |

---

*Last updated: 2026-02-28*
*This plan supersedes the previous v0.2-first approach for milestone prioritization*
