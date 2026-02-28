---
phase: M1-security-review-workflow
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/crud/gene.py
  - backend/app/schemas/gene.py
autonomous: true

must_haves:
  truths:
    - "Gene search uses parameterized queries (no SQL injection)"
    - "Search query length is validated (max 200 chars)"
    - "All existing 529 backend+frontend tests still pass"
  artifacts:
    - path: "backend/app/crud/gene.py"
      provides: "Parameterized gene search queries"
      contains: "bindparams"
    - path: "backend/app/schemas/gene.py"
      provides: "Query length validation on GeneSearchQuery"
      contains: "validate_query"
  key_links:
    - from: "backend/app/crud/gene.py"
      to: "sqlalchemy.text().bindparams()"
      via: "parameterized SQL instead of f-string interpolation"
      pattern: "text\\(.*bindparams"
---

<objective>
Fix the SQL injection vulnerability in gene search and add input validation as defense in depth.

Purpose: The gene search CRUD at `backend/app/crud/gene.py` lines 92-93 uses `text(f"'{search_params.query}' = ANY(...)")` which allows direct SQL injection. This must be fixed before any production use.

Output: Parameterized gene search queries using `text().bindparams()`, plus query length validation on `GeneSearchQuery`.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/MVP-PLAN.md
@.planning/phases/M1-security-review-workflow/M1-RESEARCH.md

Key source files:
@backend/app/crud/gene.py
@backend/app/schemas/gene.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix SQL injection in gene search with parameterized queries</name>
  <files>backend/app/crud/gene.py</files>
  <action>
In `backend/app/crud/gene.py`, in the `search()` method (around lines 84-95), replace the two vulnerable `text(f"...")` calls with parameterized `text().bindparams()` calls.

Current vulnerable code (lines 92-93):
```python
text(f"'{search_params.query}' = ANY(genes.previous_symbols)"),
text(f"'{search_params.query}' = ANY(genes.alias_symbols)"),
```

Replace with:
```python
text(":query_val = ANY(genes.previous_symbols)").bindparams(
    query_val=search_params.query
),
text(":query_val2 = ANY(genes.alias_symbols)").bindparams(
    query_val2=search_params.query
),
```

IMPORTANT: Use different bind parameter names (`query_val` and `query_val2`) for the two clauses. SQLAlchemy requires unique parameter names within a single statement.

IMPORTANT: Do NOT use `Gene.previous_symbols.any_()` — this is a PostgreSQL-specific operator that will fail on SQLite tests. The `text().bindparams()` approach is safe because no existing tests exercise the gene search `ANY()` clauses (verified in research), and production uses PostgreSQL which supports `ANY()`.

No other changes to the file. The rest of the `search()` method is correct.
  </action>
  <verify>
Run `cd /home/bernt-popp/development/gene-curator/backend && uv run pytest tests/ -v --tb=short` to confirm all existing tests pass. Then run `grep -n "text(f" backend/app/crud/gene.py` and confirm zero results (no more f-string SQL).
  </verify>
  <done>Lines 92-93 use `text().bindparams()` instead of `text(f"...")`. No f-string interpolation inside any `text()` call in gene.py. All existing tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Add query length validation to GeneSearchQuery schema</name>
  <files>backend/app/schemas/gene.py</files>
  <action>
In `backend/app/schemas/gene.py`, add a `field_validator` for the `query` field on the `GeneSearchQuery` class (around line 149). This provides defense-in-depth against excessively long search queries.

Add this validator to `GeneSearchQuery`:
```python
@field_validator("query")
@classmethod
def validate_query_length(cls, v: str | None) -> str | None:
    """Validate search query length."""
    if v is not None and len(v) > 200:
        raise ValueError("Search query too long (max 200 characters)")
    return v
```

Place it after the field definitions (after `sort_order`) but before the class ends. The `field_validator` import is already at the top of the file (line 9).

Also, add `max_length=200` to the `query` field definition for schema-level documentation:
```python
query: str | None = Field(
    None, max_length=200, description="Search term for gene symbol, name, or HGNC ID"
)
```
  </action>
  <verify>
Run `cd /home/bernt-popp/development/gene-curator/backend && uv run pytest tests/ -v --tb=short` to confirm all tests pass. Then run `make lint` from the project root to confirm no lint issues.
  </verify>
  <done>GeneSearchQuery.query field has max_length=200 and a field_validator that rejects queries longer than 200 characters. All tests pass, lint clean.</done>
</task>

</tasks>

<verification>
1. `grep -n "text(f" backend/app/crud/gene.py` returns zero results
2. `grep -n "bindparams" backend/app/crud/gene.py` returns two matches (previous_symbols and alias_symbols)
3. `grep -n "max_length=200" backend/app/schemas/gene.py` returns at least one match on the query field
4. `cd backend && uv run pytest tests/ -v` passes all tests
5. `make lint` passes
</verification>

<success_criteria>
- Gene search CRUD uses parameterized queries exclusively (no SQL injection vectors)
- Query length validation prevents excessively long inputs
- All existing backend tests pass
- Linting passes
</success_criteria>

<output>
After completion, create `.planning/phases/M1-security-review-workflow/M1-01-SUMMARY.md`
</output>
