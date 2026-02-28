# Archived: plan/ Directory

**Moved:** 2026-02-28
**Reason:** Consolidated all planning into `.planning/` as the single source of truth. The `plan/` directory contained historical implementation guides, enhancement proposals, and reference materials from the pre-v0.1 era.

## What's Here

### Still Relevant (reference material)

| File | Why Keep | Use When |
|------|----------|----------|
| `PLAN_2_CONFIGURABLE_FOUR_EYES.md` | Detailed 4-eyes refactoring plan with DB design | Implementing MVP Phase M1 (review workflow) |
| `enhancements/010-review-workflow-4eyes.md` | Review UI component designs and implementation steps | Implementing MVP Phase M1 |
| `SCOPE_PERMISSIONS_AUDIT_REPORT.md` | Security audit of permission system | Reference for permission-related work |
| `clingen_engine.md` | ClinGen SOP v11 scoring reference | Any ClinGen scoring changes |
| `scripts/clingen_documents/` | ClinGen reference PDFs and markdown | ClinGen compliance verification |
| `enhancements/003-retry-utils-exponential-backoff.md` | Retry utility proposal | If adding retry logic |

### Historical (completed or superseded)

| File/Dir | Status | Notes |
|----------|--------|-------|
| `README.md` | Superseded | Referenced blockers that have been resolved |
| `ISSUE_ROADMAP.md` | Superseded | GitHub milestones are the live source |
| `refactoring/` | Completed | Scope-centric refactoring was done in 2025 |
| `archive/` | Historical | Earlier snapshots and superseded plans |
| `enhancements/tracking/011-*` | Completed | DynamicForm integration done in v0.1 |
| `enhancements/tracking/012-015` | Completed | Various completed enhancements |
| `enhancements/deferred/` | Deferred | Cache, realtime, view management — post-v1.0 |
| `enhancements/006-*` | Completed | Endpoint alignment done |

## Where Things Live Now

| Topic | Active Location |
|-------|----------------|
| Project charter | `.planning/PROJECT.md` |
| Current state | `.planning/STATE.md` |
| Roadmap | `.planning/ROADMAP.md` |
| MVP plan | `.planning/MVP-PLAN.md` |
| Requirements | `.planning/REQUIREMENTS.md` |
| Milestones | `.planning/MILESTONES.md` |
| Codebase docs | `.planning/codebase/` |
| v0.2 research | `.planning/research/` |
| v0.1 phases | `.planning/phases/` |
| GitHub issues | https://github.com/berntpopp/gene-curator/issues |
