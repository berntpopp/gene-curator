---
phase: M1-security-review-workflow
plan: 01
subsystem: api
tags: [sqlalchemy, pydantic, security, sql-injection, parameterized-queries, input-validation]

# Dependency graph
requires: []
provides:
  - Parameterized gene search queries (SQLAlchemy text().bindparams())
  - Query length validation on GeneSearchQuery (max 200 chars)
  - SQL injection vector eliminated from gene search endpoint
affects:
  - M1-02-and-later: all subsequent plans benefit from secure gene search
  - production: must be deployed before any public access

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Use text().bindparams() for raw SQL fragments, never text(f'...')"
    - "field_validator with max_length for defense-in-depth on search inputs"

key-files:
  created: []
  modified:
    - backend/app/crud/gene.py
    - backend/app/schemas/gene.py

key-decisions:
  - "Used text().bindparams() over Gene.previous_symbols.any_() to preserve SQLite test compatibility"
  - "Distinct bind parameter names (query_val/query_val2) required by SQLAlchemy per-clause uniqueness"
  - "Added field_validator in addition to max_length Field() for runtime enforcement at validation layer"

patterns-established:
  - "Parameterized SQL: text(':param_name = ANY(table.col)').bindparams(param_name=value)"
  - "Schema validators: @field_validator with explicit None guard before len() check"

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase M1 Plan 01: SQL Injection Fix + Query Validation Summary

**Eliminated SQL injection in gene search by replacing f-string text() clauses with SQLAlchemy text().bindparams(), and added 200-char max_length validation on GeneSearchQuery.query**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-28T08:59:57Z
- **Completed:** 2026-02-28T09:01:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced two vulnerable `text(f"'{search_params.query}' = ANY(...)")` calls with fully parameterized `text(":param = ANY(...)").bindparams(param=value)` in `CRUDGene.search()`
- Added `max_length=200` to `GeneSearchQuery.query` Field definition for OpenAPI schema documentation
- Added `field_validator("query") validate_query_length()` that raises ValueError for queries exceeding 200 characters
- All 101 backend tests pass, ruff/mypy/bandit lint clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix SQL injection in gene search with parameterized queries** - `aa8ebc1` (fix)
2. **Task 2: Add query length validation to GeneSearchQuery schema** - `e43c36f` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/app/crud/gene.py` - `CRUDGene.search()` lines 92-97: parameterized ANY() clauses
- `backend/app/schemas/gene.py` - `GeneSearchQuery`: max_length=200 on query field + field_validator

## Decisions Made

- **text().bindparams() over ORM any_()**: `Gene.previous_symbols.any_()` is PostgreSQL-specific and fails on SQLite test backend. The `text().bindparams()` approach keeps the same SQL semantics while being safe. No tests exercise the ANY() path directly, so risk is minimal.
- **Two distinct bind param names**: SQLAlchemy requires unique parameter names within a compiled statement. Used `query_val` and `query_val2` to satisfy this constraint without wrapping in a subquery.
- **field_validator alongside max_length**: `max_length=200` on Field() provides documentation and schema-level enforcement; the explicit `field_validator` provides programmatic enforcement with a clear error message. Both are kept for defense-in-depth.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff formatting violation after schema edit**

- **Found during:** Task 2 verification (make lint)
- **Issue:** The new validator block in gene.py triggered ruff's formatter check (line wrapping difference)
- **Fix:** Ran `uv run ruff format app/schemas/gene.py` — applied automatically, no logic change
- **Files modified:** backend/app/schemas/gene.py
- **Verification:** `make lint` all 5 checks passed after format
- **Committed in:** e43c36f (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking - formatting)
**Impact on plan:** Auto-fix was a pure formatting correction with no logic change. No scope creep.

## Issues Encountered

None beyond the formatting deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SQL injection vulnerability eliminated; gene search is safe for production use
- Ready for M1-02 (review workflow implementation)
- No blockers introduced

---
*Phase: M1-security-review-workflow*
*Completed: 2026-02-28*
