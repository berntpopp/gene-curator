# Gene Curator - Enhancement Tracking

This directory tracks implementation progress for Gene Curator enhancements.

**Last Updated**: 2026-01-12

---

## Active Implementation Plans

| ID | Enhancement | Priority | Effort | Status | Closes |
|----|-------------|----------|--------|--------|--------|
| [011](011-DYNAMIC-FORM-INTEGRATION.md) | Wire DynamicForm to CurationFormView | **CRITICAL** | 4-6h | Ready | #62, #61, #77 |
| [010](../010-review-workflow-4eyes.md) | 4-Eyes Review Workflow | HIGH | 4-6h | Ready | #116 |
| [003](../003-retry-utils-exponential-backoff.md) | RetryUtils with Backoff | Medium | 3-4h | Ready | - |

---

## Completed / Already Implemented

| Enhancement | Status | Notes |
|-------------|--------|-------|
| Draft Auto-Save (#008) | ✅ Implemented | `useFormRecovery` composable in CurationForm (5s interval) |
| DynamicForm Component (#009) | ✅ Component exists | `frontend/src/components/dynamic/DynamicForm.vue` |
| DynamicField Component | ✅ Implemented | 8+ field types (string, number, boolean, select, array, object, date) |
| Undo/Redo | ✅ Implemented | `useHistory` composable |
| Conflict Resolution | ✅ Implemented | `useOptimisticLocking` composable |
| Session Timeout | ✅ Implemented | `useSessionTimeout` composable |

---

## Critical Finding

**The DynamicForm component EXISTS and WORKS, but is NOT WIRED to the curation workflow.**

Current state:
- `CurationForm.vue` (800+ lines) is **hardcoded for ClinGen SOP v11**
- Manual tabs: Genetic Evidence, Experimental Evidence, Contradictory Evidence
- Does NOT use DynamicForm - schema-agnosticism is broken

Enhancement #011 fixes this by:
1. Creating `SchemaDrivenCurationForm.vue` that uses DynamicForm
2. Schema resolved from workflow_pair or route param
3. Any schema renders correctly (ClinGen, GenCC, custom)

---

## Implementation Priority Order

### Tier 1: Unblock Core Workflow (8-12h total)

**Why these first?** Without them, Gene Curator cannot fulfill its core purpose.

1. **#011 - Wire DynamicForm to CurationFormView** (~4-6h)
   - Enables schema-agnostic curation (core product differentiator)
   - Closes 3 issues: #62, #61, #77
   - DynamicForm already exists - just needs wiring

2. **#010 - 4-Eyes Review UI** (~4-6h)
   - Enables mandatory peer review workflow
   - Closes #116 (multi-user approval)
   - Backend ready, needs frontend views

**After Tier 1**: Complete curator workflow (create → submit → review → activate)

### Tier 2: Infrastructure (~3-4h)

3. **#003 - RetryUtils** (~3-4h)
   - External API reliability (HGNC lookups)
   - Not blocking, but improves stability

---

## File Inventory

### Current Plans
| File | Purpose |
|------|---------|
| `011-DYNAMIC-FORM-INTEGRATION.md` | Implementation plan - what to build |
| `011-AGENTIC-IMPLEMENTATION-PROMPT.md` | Agentic prompt - how to build it |
| `GITHUB_ISSUES_COMPARISON.md` | Issue tracking by milestone |

### Removed (Superseded)
| File | Reason |
|------|--------|
| `008-draft-autosave-frontend.md` | Already implemented via `useFormRecovery` |
| `009-dynamic-form-generation.md` | Component exists, superseded by #011 |
| `REFACTOR_CLOSES_ISSUES.md` | Consolidated into #011 |

---

## Milestone Overview

| Milestone | Open Issues | Next Action |
|-----------|-------------|-------------|
| v0.4.0 - Core Curation Features | 6 | Implement #011, then #010 |
| v0.5.0 - Infrastructure & Scalability | 5 | After v0.4.0 |
| v1.0.0 - Production Ready | 6 | After v0.5.0 |
| Backlog | 6 | Future |

---

## Quick Commands

```bash
# View v0.4.0 issues
gh issue list --milestone "v0.4.0 - Core Curation Features"

# View high priority issues
gh issue list --label "priority: high"

# Check enhancement file
cat plan/enhancements/tracking/011-DYNAMIC-FORM-INTEGRATION.md
```

---

**Last Updated**: 2026-01-12
**Prepared By**: Claude Code
