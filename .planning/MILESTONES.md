# Project Milestones: Gene Curator

## v0.1 Dynamic Forms (Shipped: 2026-01-23)

**Delivered:** Schema-driven dynamic form rendering enabling any scope to use their own curation methodology without frontend code changes.

**Phases completed:** 1-5 (12 plans total)

**Key accomplishments:**

- Schema-driven dynamic form rendering with fields, tabs, and sections from database configuration
- Component registry with 5 specialized evidence components (MONDO, PMID, HPO, OMIM)
- Schema-agnostic live scoring for ClinGen, GenCC, and Qualitative engines
- Client-side validation from schema constraints with backend error integration
- Feature flag infrastructure for gradual rollout with legacy data migration
- Comprehensive test coverage (219 new tests, 428 total passing)

**Stats:**

- 61 files created/modified
- +17,581 / -1,228 lines (55,478 LOC frontend total)
- 5 phases, 12 plans, ~80 tasks
- 2 days from start to ship (2026-01-22 to 2026-01-23)

**Git range:** `feat(01-01)` to `docs(05)` (69 commits)

---

## MVP (In Progress: 2026-02-28)

**Goal:** Complete end-to-end curation workflow so a clinical genetics team can use Gene Curator for real curation work.

**Phases planned:** 4

| Phase | Name | Focus | Issues |
|-------|------|-------|--------|
| M1 | Security Fix + Review Workflow | SQL injection fix, 4-eyes review UI | #116 |
| M2 | Precuration & Curation Enhancements | Prefill logic, validation, deletion guard | #61, #77, #87 |
| M3 | Admin Management UI | Assignment dialogs, workflow views | #119, #118 |
| M4 | MVP Hardening | Tech debt fixes, smoke tests, docs | #104 |

**Key context:**
- Backend API is complete; gaps are frontend UI
- Zero open bugs; CI green; 529 tests passing
- Review workflow backend exists; frontend pending
- Detailed plan: `.planning/MVP-PLAN.md`

---

## v0.2 Form Intelligence (Deferred)

**Status:** Deferred 2026-02-28. Focus shifted to MVP completion first.
**Research preserved:** `.planning/research/` (FEATURES.md, ARCHITECTURE.md, PITFALLS.md)
**Requirements preserved:** `.planning/REQUIREMENTS.md` (10 requirements: COND-01..05, XVAL-01..03, DEPS-01..02)

Will revisit after MVP ships.

---

*Last updated: 2026-02-28 — v0.2 deferred, MVP is sole active milestone*
