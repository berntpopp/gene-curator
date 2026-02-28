# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)
See: .planning/MVP-PLAN.md (created 2026-02-28)

**Core value:** Every scope can use their own curation methodology with dynamically rendered forms
**Current focus:** MVP completion — end-to-end review workflow, curator UX, admin management

## Current Position

Phase: MVP Phase M2 (Precuration & Curation Enhancements) — ready to plan
Plan: M1 complete (all 5 plans + manual verification + bug fixes); M2 next
Status: M1 COMPLETE — verified 7/7 criteria, 6 manual browser tests, 3 bug fixes committed
Last activity: 2026-02-28 — M1 phase complete, badge race condition fix committed (c3b4b0c)

Progress: MVP [██████░░░░] ~55% (M1 done; M2, M3, M4 remaining)

## Performance Metrics

**Velocity (v0.1 reference):**
- Total plans completed: 11 (v0.1)
- Average duration: ~4 min/plan
- Total execution time: 44 min 25 sec (v0.1)

**By Phase (v0.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Field Rendering | 2 | ~8 min | 4 min |
| 2. Tab Structure | 2 | ~8 min | 4 min |
| 3. Field Metadata | 2 | ~8 min | 4 min |
| 4. Validation | 2 | ~8 min | 4 min |
| 5. Scoring and Integration | 3 | ~12 min | 4 min |

*MVP metrics will accumulate here as phases complete*

## Milestone Summary

### v0.1 Dynamic Forms (SHIPPED 2026-01-23)

- **Phases:** 5 (Field Rendering, Tab Structure, Field Metadata, Validation, Scoring & Integration)
- **Plans:** 12 total
- **Tests:** 219 new tests, 428 total passing
- **Duration:** 2 days (2026-01-22 to 2026-01-23)
- **Execution time:** 44 min 25 sec total

### MVP (IN PROGRESS)

- **Phases:** 4 (M1: Review Workflow, M2: Curation Enhancements, M3: Admin UI, M4: Hardening)
- **Critical path:** M1 — review workflow enables end-to-end curation
- **Blocking issues:** #116 (review workflow), SQL injection (CONCERNS.md)

## Accumulated Context

### Decisions

- MVP phases (M1-M4) prioritized before v0.2 Form Intelligence (2026-02-28)
- v0.2 research preserved in .planning/research/ (still valid, just deprioritized)
- plan/ directory archived to .planning/archive/plan/ (2026-02-28)
- **M1-01**: Use text().bindparams() over ORM any_() for gene search ANY() clauses — SQLite test compatibility (2026-02-28)
- **M1-01**: Two distinct bind param names (query_val/query_val2) required by SQLAlchemy per-clause uniqueness (2026-02-28)
- M1-02: Dynamic imports inside Pinia actions to avoid circular dependency chains (2026-02-28)
- M1-02: workflow API redirects getAvailableTransitions → /state endpoint, submitPeerReview → /transition endpoint (2026-02-28)
- M1-03: badge: null (not 0) when pendingReviewCount is 0 — hides badge entirely vs showing misleading "0" badge (2026-02-28)
- M1-03: isAuthenticated guard on onMounted prevents unauthenticated badge API calls; silent failure in refreshBadgeCount for nav resilience (2026-02-28)
- **M1-04**: Use CurationStatus.IN_REVIEW (not SUBMITTED) in _can_user_review_curation — workflow_engine sets status=in_review on submit_for_review() (2026-02-28)
- **M1-04**: Single-line fix sufficient; 4-eyes check, admin bypass, and scope role checks were all correct (2026-02-28)
- M1-05: v-if="curationSchemaId" gates Evidence Details section — graceful degradation when schema fetch fails, score tables remain (2026-02-28)
- M1-05: title="" passed to DynamicForm to suppress default "Dynamic Form" title inside the card with its own "Evidence Details" header (2026-02-28)
- M1-03 (fix): watch(isAuthenticated) added to MainNavigation for badge refresh — fixes race condition with dev quick login where auth sets after onMounted (2026-02-28)
- M1 verification: use_dynamic_form migration must be run on dev DB — column defined in model but missing from initial schema (2026-02-28)

v0.2 decisions (pre-implementation, from research — deferred, revisit post-MVP):
- Research preserved in `.planning/research/` and `.planning/REQUIREMENTS.md`
- v0.2 removed from active roadmap on 2026-02-28 to focus on MVP

### Pending Todos

None.

### Blockers/Concerns

- ~~SQL injection in gene search (backend/app/crud/gene.py)~~ — FIXED in M1-01
- Pre-existing lint issue in CurationDetailView.vue (unused authStore variable) — not blocking builds
- 6 manual testing scenarios from v0.1 audit still required before production
- v0.2 research gaps (deferred): MONDO API availability, SchemaValidator null-skip behavior — revisit when v0.2 resumes

## Session Continuity

Last session: 2026-02-28
Stopped at: M1 phase complete, ready for M2 planning

**Next steps:**
- Plan and execute M2 (Precuration & Curation Enhancements)
- M3 (Admin Management UI) can run in parallel with M2
- M4 (MVP Hardening) after M2 + M3

**Archives:**
- `.planning/milestones/v0.1-ROADMAP.md`
- `.planning/milestones/v0.1-REQUIREMENTS.md`
- `.planning/milestones/v0.1-MILESTONE-AUDIT.md`
- `.planning/archive/plan/` (former plan/ directory, moved 2026-02-28)
- `.planning/archive/docs/` (former docs/ directory)

---
*Updated: 2026-02-28 after M1 phase completion*
