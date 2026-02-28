# Project Milestones: Gene Curator

## v0.1 Dynamic Forms (Shipped: 2026-01-23)

**Delivered:** Schema-driven dynamic form rendering enabling any scope to use their own curation methodology without frontend code changes.

**Phases:** 5 (12 plans total)
**Duration:** 2 days (2026-01-22 to 2026-01-23)
**Tests:** 219 new, 428 total passing
**Stats:** 61 files, +17,581 / -1,228 lines, ~80 tasks
**Git range:** `feat(01-01)` to `docs(05)` (69 commits)
**Archives:** `milestones/v0.1-*`, `milestones/v0.1-phases/`

---

## MVP (Shipped: 2026-02-28)

**Delivered:** Complete end-to-end curation workflow — a clinical genetics team can assign genes, curate with schema-driven forms, and approve via independent 4-eyes review.

**Phases:** 4

| Phase | Name | Key Deliverables |
|-------|------|-----------------|
| M1 | Security + Review Workflow | SQL injection fix, review queue, 4-eyes review UI, notification badge |
| M2 | Curation Enhancements | Lump/split validation, workflow prefill, precuration deletion guard |
| M3 | Admin Management UI | Assignment edit/reassign/view dialogs, workflow view/edit dialogs |
| M4 | MVP Hardening | Curator count fix, notification system, FAQ, smoke tests |

**Duration:** 1 day (2026-02-28)
**Tests:** 529+ passing
**Key commits:** aa9ebc3 (M2), 36d980d-19f4ae0 (M3), 7590b74-c33558c (M4)
**Merge:** 7f6f857 (feature/mvp-m3-m4-implementation → master)
**Archives:** `milestones/mvp-*`, `milestones/mvp-phases/`

---

## v0.2 Form Intelligence (Deferred)

**Status:** Deferred 2026-02-28. Research complete, will revisit post-MVP.
**Archives:** `milestones/v0.2-deferred/` (research/ + REQUIREMENTS.md)
**Requirements:** 10 defined (COND-01..05, XVAL-01..03, DEPS-01..02)

---

*Last updated: 2026-02-28*
