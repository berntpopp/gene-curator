# MVP Completion Design: Phases M3 + M4

**Date:** 2026-02-28
**Status:** Approved
**Execution Order:** Sequential — M3 (Admin Management UI) then M4 (MVP Hardening)

---

## Context

MVP is ~70% complete. M1 (Security + Review Workflow) and M2 (Precuration & Curation Enhancements) are done. This design covers the remaining two phases to ship the MVP.

**What's built:** Auth, scopes, gene catalogue, schema system, dynamic forms, workflow engine, precuration, curation, review workflow (frontend + backend), precuration deletion guard, L/S validation, workflow prefill.

**What's missing:** Admin management dialogs (M3), notification system, curator count fix, documentation (M4).

---

## Phase M3: Admin Management UI

### M3.1: Gene Assignment Dialogs

Three dialogs replace stubs in `GeneAssignmentManager.vue` (lines 565, 571, 578).

**View Dialog** (read-only v-dialog):
- Fields: gene symbol, disease, assigned curator, scope, priority, due date, status, created/updated timestamps
- Assignment history (who assigned, when, reassignments)
- Uses existing store data — no new endpoints
- Close button only

**Edit Dialog** (form v-dialog):
- Editable: priority (v-select: low/medium/high/critical), due date (v-date-input), notes (v-textarea)
- Wires to `assignmentsAPI.updateAssignment(id, data)` — API exists, needs store wrapper
- Save/Cancel with validation, toast on success

**Reassign Dialog** (form v-dialog):
- Curator dropdown from scope members API (filtered to curator+ roles)
- Optional transfer note
- Wires to `assignmentsAPI.assignCurator(assignmentId, curatorId)`
- Confirmation step before submission
- Toast on success

**Cleanup:**
- Disable/hide bulk assign, rebalance workload, export buttons (unimplemented store methods)
- Fix or remove `workloadSummary` computed property (references non-existent store property)

**Files touched:**
- `frontend/src/components/dynamic/GeneAssignmentManager.vue` — add 3 dialogs, cleanup stubs
- `frontend/src/stores/assignments.js` — add `updateAssignment()` store wrapper

### M3.2: Workflow Management Dialogs

Two dialogs replace stubs in `WorkflowManagement.vue` (lines 269, 275).

**View Dialog** (read-only v-dialog):
- Workflow pair name, description, active status
- Linked schemas: precuration + curation schema names
- Data mapping configuration display
- Stage pipeline visualization (reuse existing card layout)
- Created/updated timestamps
- Uses existing `schemasStore` data

**Edit Dialog** (form v-dialog):
- Editable: name (v-text-field), description (v-textarea), active status (v-switch)
- Non-editable (read-only display): linked schemas, stages
- Wires to existing schema store update method
- Save/Cancel with validation

**Stage edit: deferred** — stub remains with "coming soon" toast.

**Files touched:**
- `frontend/src/views/WorkflowManagement.vue` — add 2 dialogs, wire stubs

### M3 Acceptance Criteria

- [ ] Gene assignment edit/reassign/view dialogs all functional
- [ ] Assignment changes immediately reflected in data table
- [ ] Workflow view/edit dialogs functional
- [ ] Broken bulk/rebalance/export buttons disabled or hidden
- [ ] All existing tests still pass

---

## Phase M4: MVP Hardening

### M4.1: Fix Gene Summary Curator Count

**Current:** Hardcoded to `1` in `gene_summary_service.py:148`.

**Fix:** Count distinct `created_by` users from `CurationNew` for the gene within the scope. Falls back to `0` if no curations exist.

**Files touched:**
- `backend/app/services/gene_summary_service.py` — replace hardcoded value with query
- `backend/tests/` — unit test for curator count

### M4.2: Full Notification System

**Backend Model** — `NotificationNew`:

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| type | Enum | review_assigned, review_completed, revision_requested, curation_approved, curation_rejected |
| title | str | Short title |
| message | str | Detail message |
| link | str (nullable) | Relative URL to relevant page |
| is_read | bool | Default False |
| created_at | datetime | Auto-set |

**Backend Migration:** Alembic migration for `notifications` table.

**Backend Endpoints** (`/api/v1/notifications`):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List current user's notifications (paginated, filterable by `is_read`) |
| PATCH | `/{id}/read` | Mark single notification as read |
| PATCH | `/read-all` | Mark all as read for current user |

RLS context applied — users only see their own notifications.

**Backend CRUD:** `CRUDBase` subclass with `create_for_user()` helper.

**Workflow Engine Hooks** — emit notifications at transition points:

| Transition | Recipient | Notification |
|------------|-----------|--------------|
| `submit_for_review()` | Assigned reviewer | "New review assigned: {gene_symbol}" |
| `approve_curation()` | Curator (creator) | "Curation approved: {gene_symbol}" |
| `reject_curation()` | Curator (creator) | "Curation rejected: {gene_symbol}" |
| `request_revision()` | Curator (creator) | "Revision requested: {gene_symbol}" |

**Frontend API Module** — `frontend/src/api/notifications.js`:
- `getNotifications(params)` → GET /api/v1/notifications
- `markAsRead(id)` → PATCH /api/v1/notifications/{id}/read
- `markAllAsRead()` → PATCH /api/v1/notifications/read-all

**Frontend Store Wiring** — `frontend/src/stores/notifications.js`:
- Uncomment API client import
- Replace mock `fetchNotifications()` with real API call
- Wire `markAsRead()` and `markAllAsRead()` to endpoints
- Add 60-second polling interval (matching existing badge pattern)
- `unreadCount` getter drives existing UI badge

**Files touched:**
- `backend/app/models/models.py` — add NotificationNew model
- `backend/app/schemas/notification.py` — Pydantic schemas
- `backend/app/crud/notification.py` — CRUD operations
- `backend/app/api/v1/endpoints/notifications.py` — REST endpoints
- `backend/app/api/v1/api.py` — register router
- `backend/app/crud/workflow_engine.py` — emit notification hooks
- `backend/tests/` — notification endpoint tests
- `frontend/src/api/notifications.js` — new API module
- `frontend/src/stores/notifications.js` — wire to real API
- Alembic migration file

### M4.3: Manual Smoke Test Checklist

Document these workflow paths for manual verification:

1. **Happy path:** Gene assignment → Precuration → Curation → Submit for review → Approve → Active
2. **Revision loop:** Submit → Request revision → Edit → Resubmit → Approve
3. **Rejection:** Submit → Reject → Back to curation stage
4. **4-eyes enforcement:** Curator cannot review own curation
5. **Multi-scope:** Same user has different roles in different scopes
6. **Admin dialogs:** Edit assignment, reassign gene, view/edit workflow
7. **Notification flow:** Review actions generate notifications, mark-as-read works

Written as a markdown checklist (location TBD — likely FAQ or separate testing doc).

### M4.4: FAQ Content Expansion

Add 5-6 new FAQ entries to `frontend/src/views/Faq.vue`:

- "How do I precurate a gene?"
- "How does the review workflow work?"
- "What happens when a curation is rejected?"
- "Can I work across multiple scopes?"
- "How do I manage gene assignments as an admin?"
- "Where do I see my notifications?"

### M4 Acceptance Criteria

- [ ] Gene summary shows actual curator count (not hardcoded 1)
- [ ] Notification model, endpoints, and CRUD all working
- [ ] Workflow transitions emit notifications to relevant users
- [ ] Frontend notification store wired to real API with 60s polling
- [ ] All 7 smoke test paths verified manually
- [ ] FAQ updated with workflow-specific content
- [ ] CI passes with all changes

---

## Execution Plan Summary

| Step | Phase | Scope | Est. Effort |
|------|-------|-------|-------------|
| 1 | M3.1 | Gene assignment dialogs (view/edit/reassign) + cleanup | 4-6h |
| 2 | M3.2 | Workflow management dialogs (view/edit) | 3-4h |
| 3 | M4.1 | Curator count fix | 1-2h |
| 4 | M4.2 | Full notification system (backend + frontend) | 6-8h |
| 5 | M4.3 | Manual smoke testing | 2-3h |
| 6 | M4.4 | FAQ expansion | 1-2h |
| **Total** | | | **17-25h** |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Sequential M3→M4 | Clean dependency chain; M4 smoke tests cover M3 output |
| Core dialogs only (M3) | Bulk/rebalance/export deferred to post-MVP; YAGNI |
| Read-only detail + basic edit (workflows) | Stage editing risks breaking workflow integrity |
| Full notification system (M4) | Real-time feedback on review events is essential for team workflows |
| Manual smoke test | Faster to ship; automated E2E deferred to post-MVP |
| HTTP polling (60s) | Matches existing badge refresh; WebSocket deferred |

---

*Approved: 2026-02-28*
