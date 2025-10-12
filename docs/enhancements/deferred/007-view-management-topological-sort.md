# Enhancement: Database View Management with Topological Sort

**Priority**: Low
**Complexity**: Medium
**Estimated Effort**: 3-4 hours
**Reference**: `kidney-genetics-db/backend/app/db/views.py` and `replaceable_objects.py`

## Overview

Implement a sophisticated database view management system with automatic dependency tracking and topological sorting. Enable safe view refresh operations without manual ordering, and provide tools for view inspection and validation.

## Current State

- Database views created in SQL migration files
- No automatic dependency tracking between views
- Manual ordering required for view drop/create operations
- Difficult to refresh views without breaking dependencies
- No tooling for view health checks

## Proposed Implementation

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ View Management System                              │
├─────────────────────────────────────────────────────┤
│ 1. View Registry (Python definitions)              │
│    ↓                                                │
│ 2. Dependency Graph Builder                        │
│    ↓                                                │
│ 3. Topological Sort (Safe Order)                   │
│    ↓                                                │
│ 4. View Drop (Reverse Order)                       │
│ 5. View Create (Dependency Order)                  │
└─────────────────────────────────────────────────────┘
```

### View Dependency Example

```sql
-- Tier 1: Base views (no dependencies)
active_curations_view → genes_new, curations_new

-- Tier 2: Intermediate views (depend on Tier 1)
curation_summary_view → active_curations_view, scopes

-- Tier 3: Aggregate views (depend on Tier 2)
scope_statistics_view → curation_summary_view, gene_scope_assignments
```

### Core Components

**1. View Registry** (`backend/app/db/views.py`)

```python
"""Database view registry with dependency tracking"""

from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class ViewDefinition:
    """Definition of a database view"""
    name: str
    sql: str
    depends_on: List[str] = None  # List of table/view names this view depends on

    def __post_init__(self):
        self.depends_on = self.depends_on or []

# View definitions registry
VIEW_DEFINITIONS = [
    ViewDefinition(
        name="active_curations_view",
        sql="""
        SELECT
            c.id AS curation_id,
            c.gene_id,
            c.scope_id,
            g.symbol AS gene_symbol,
            s.name AS scope_name,
            c.verdict,
            c.score,
            c.status,
            c.created_at,
            c.updated_at
        FROM curations_new c
        JOIN genes_new g ON c.gene_id = g.id
        JOIN scopes s ON c.scope_id = s.id
        WHERE c.status = 'active'
        """,
        depends_on=["curations_new", "genes_new", "scopes"]
    ),

    ViewDefinition(
        name="curation_summary_view",
        sql="""
        SELECT
            scope_name,
            COUNT(DISTINCT gene_id) AS total_genes,
            COUNT(DISTINCT curation_id) AS total_curations,
            AVG(score) AS avg_score,
            MAX(updated_at) AS last_updated
        FROM active_curations_view
        GROUP BY scope_name
        """,
        depends_on=["active_curations_view"]  # Depends on another view
    ),

    ViewDefinition(
        name="scope_statistics_view",
        sql="""
        SELECT
            s.id AS scope_id,
            s.name AS scope_name,
            cs.total_genes,
            cs.total_curations,
            cs.avg_score,
            COUNT(DISTINCT gsa.gene_id) AS assigned_genes,
            COUNT(DISTINCT gsa.curator_id) AS curators
        FROM scopes s
        LEFT JOIN curation_summary_view cs ON s.name = cs.scope_name
        LEFT JOIN gene_scope_assignments gsa ON s.id = gsa.scope_id
        GROUP BY s.id, s.name, cs.total_genes, cs.total_curations, cs.avg_score
        """,
        depends_on=["scopes", "curation_summary_view", "gene_scope_assignments"]
    ),
]
```

**2. Topological Sort Algorithm** (`backend/app/db/view_manager.py`)

```python
"""View management with topological sorting"""

from typing import List, Dict, Set
from app.db.views import VIEW_DEFINITIONS, ViewDefinition
from app.core.logging import get_logger

logger = get_logger(__name__)

class ViewManager:
    """Manage database views with dependency tracking"""

    def __init__(self, view_definitions: List[ViewDefinition] = None):
        self.views = view_definitions or VIEW_DEFINITIONS
        self.dependency_graph = self._build_dependency_graph()

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build dependency graph from view definitions"""
        graph = {}
        for view in self.views:
            # Only track dependencies on other views (not base tables)
            view_names = {v.name for v in self.views}
            view_deps = [dep for dep in view.depends_on if dep in view_names]
            graph[view.name] = set(view_deps)
        return graph

    def topological_sort(self) -> List[str]:
        """
        Sort views in dependency order using Kahn's algorithm.

        Returns views in order where dependencies come before dependents.
        """
        # Calculate in-degree for each view
        in_degree = {view.name: 0 for view in self.views}
        for view_name, deps in self.dependency_graph.items():
            for dep in deps:
                if dep in in_degree:  # Only count view dependencies
                    in_degree[dep] += 0  # Will be incremented below

        # Recalculate in-degrees correctly
        for view_name, deps in self.dependency_graph.items():
            in_degree[view_name] = len([d for d in deps if d in in_degree])

        # Queue of views with no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        sorted_views = []

        while queue:
            # Remove a view with no dependencies
            view_name = queue.pop(0)
            sorted_views.append(view_name)

            # Reduce in-degree for dependent views
            for other_view, deps in self.dependency_graph.items():
                if view_name in deps:
                    in_degree[other_view] -= 1
                    if in_degree[other_view] == 0:
                        queue.append(other_view)

        # Check for circular dependencies
        if len(sorted_views) != len(self.views):
            raise ValueError("Circular dependency detected in views")

        logger.debug(f"Topological sort result: {sorted_views}")
        return sorted_views

    def get_create_order(self) -> List[ViewDefinition]:
        """Get views in safe creation order"""
        sorted_names = self.topological_sort()
        view_map = {v.name: v for v in self.views}
        return [view_map[name] for name in sorted_names]

    def get_drop_order(self) -> List[ViewDefinition]:
        """Get views in safe drop order (reverse of create)"""
        return list(reversed(self.get_create_order()))

    def generate_create_sql(self) -> str:
        """Generate SQL to create all views in safe order"""
        sql_statements = []
        for view in self.get_create_order():
            sql_statements.append(f"CREATE OR REPLACE VIEW {view.name} AS\n{view.sql};")
        return "\n\n".join(sql_statements)

    def generate_drop_sql(self) -> str:
        """Generate SQL to drop all views in safe order"""
        sql_statements = []
        for view in self.get_drop_order():
            sql_statements.append(f"DROP VIEW IF EXISTS {view.name} CASCADE;")
        return "\n\n".join(sql_statements)

    def show_dependency_tree(self) -> str:
        """Generate ASCII dependency tree"""
        lines = ["View Dependency Hierarchy:", ""]

        # Group by dependency level
        sorted_views = self.topological_sort()
        levels = {}
        for view_name in sorted_views:
            max_dep_level = 0
            for dep in self.dependency_graph.get(view_name, []):
                if dep in levels:
                    max_dep_level = max(max_dep_level, levels[dep] + 1)
            levels[view_name] = max_dep_level

        # Print by level
        for level in sorted(set(levels.values())):
            views_at_level = [name for name, lvl in levels.items() if lvl == level]
            indent = "  " * level
            for view_name in views_at_level:
                deps = self.dependency_graph.get(view_name, set())
                deps_str = f" (depends on: {', '.join(deps)})" if deps else " (no view dependencies)"
                lines.append(f"{indent}├─ {view_name}{deps_str}")

        return "\n".join(lines)
```

**3. Management Commands** (`backend/app/db/replaceable_objects.py`)

```python
"""Database view management commands"""

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.view_manager import ViewManager
from app.core.logging import get_logger

logger = get_logger(__name__)

def refresh_all_views(db: Session) -> None:
    """Refresh all database views in safe order"""
    manager = ViewManager()

    logger.info("Refreshing all database views...")

    # Drop views in reverse dependency order
    drop_sql = manager.generate_drop_sql()
    logger.debug(f"Drop SQL:\n{drop_sql}")
    db.execute(text(drop_sql))

    # Create views in dependency order
    create_sql = manager.generate_create_sql()
    logger.debug(f"Create SQL:\n{create_sql}")
    db.execute(text(create_sql))

    db.commit()
    logger.info(f"✅ Refreshed {len(manager.views)} views successfully")

def verify_all_views(db: Session) -> Dict[str, bool]:
    """Verify all views exist and are queryable"""
    manager = ViewManager()
    results = {}

    for view in manager.views:
        try:
            db.execute(text(f"SELECT 1 FROM {view.name} LIMIT 1"))
            results[view.name] = True
        except Exception as e:
            logger.error(f"View {view.name} verification failed: {e}")
            results[view.name] = False

    return results

def show_view_dependencies(db: Session) -> str:
    """Show view dependency tree"""
    manager = ViewManager()
    return manager.show_dependency_tree()
```

**4. Make Commands** (Integration with Makefile)

```makefile
# Database view management commands
db-refresh-views:
	@echo "Refreshing all database views..."
	@cd backend && uv run python -c "\
		from app.db.replaceable_objects import refresh_all_views; \
		from app.core.database import get_db; \
		db = next(get_db()); \
		refresh_all_views(db)"
	@echo "✅ Views refreshed"

db-show-view-deps:
	@echo "📊 View Dependency Hierarchy:"
	@cd backend && uv run python -c "\
		from app.db.replaceable_objects import show_view_dependencies; \
		from app.core.database import get_db; \
		db = next(get_db()); \
		print(show_view_dependencies(db))"

db-verify-views:
	@echo "🔍 Verifying all views..."
	@cd backend && uv run python -c "\
		from app.db.replaceable_objects import verify_all_views; \
		from app.core.database import get_db; \
		db = next(get_db()); \
		results = verify_all_views(db); \
		for view, ok in results.items(): \
			print(f'  {view}: {'✅' if ok else '❌'}');"
```

**5. API Endpoint** (`backend/app/api/v1/endpoints/admin.py`)

```python
from app.db.replaceable_objects import (
    refresh_all_views,
    verify_all_views,
    show_view_dependencies
)

@router.post("/admin/views/refresh")
async def refresh_views(db: Session = Depends(get_db)):
    """Refresh all database views (admin only)"""
    refresh_all_views(db)
    return {"message": "Views refreshed successfully"}

@router.get("/admin/views/verify")
async def verify_views(db: Session = Depends(get_db)):
    """Verify all views are working"""
    results = verify_all_views(db)
    return {"views": results, "all_ok": all(results.values())}

@router.get("/admin/views/dependencies")
async def view_dependencies(db: Session = Depends(get_db)):
    """Show view dependency tree"""
    tree = show_view_dependencies(db)
    return {"dependency_tree": tree}
```

### Usage Patterns

**Pattern 1: Refresh Views After Schema Change**

```bash
# After adding a new column to curations_new table
make db-refresh-views
```

**Pattern 2: Verify Views in CI/CD**

```bash
# In CI pipeline
make db-verify-views
# Exit code 0 if all views OK, 1 otherwise
```

**Pattern 3: Show View Dependencies**

```bash
make db-show-view-deps

# Output:
# View Dependency Hierarchy:
#
# ├─ active_curations_view (depends on: curations_new, genes_new, scopes)
#   ├─ curation_summary_view (depends on: active_curations_view)
#     ├─ scope_statistics_view (depends on: curation_summary_view)
```

## Implementation Steps

1. **Create view management modules**
   - `backend/app/db/views.py` - View definitions registry
   - `backend/app/db/view_manager.py` - Topological sort logic
   - `backend/app/db/replaceable_objects.py` - Management commands

2. **Define all existing views** in VIEW_DEFINITIONS
   ```python
   # Document all views with dependencies
   active_curations_view
   curation_summary_view
   scope_statistics_view
   ```

3. **Add Make commands** to Makefile
   - `make db-refresh-views`
   - `make db-show-view-deps`
   - `make db-verify-views`

4. **Add admin API endpoints**
   - POST /admin/views/refresh
   - GET /admin/views/verify
   - GET /admin/views/dependencies

5. **Update CLAUDE.md**
   ```markdown
   ## Database View Management

   - View definitions: `backend/app/db/views.py`
   - Automatic dependency tracking with topological sort
   - Refresh views: `make db-refresh-views`
   - Verify views: `make db-verify-views`
   ```

6. **Create migration for initial views**
   ```sql
   -- database/sql/XXX_create_views.sql
   -- Generated from: backend/app/db/view_manager.py
   ```

## Benefits

- **Safety**: Topological sort ensures views created in correct order
- **Maintainability**: Views defined once in Python, not scattered in SQL files
- **Automation**: `make db-refresh-views` handles all complexity
- **Validation**: `make db-verify-views` catches broken views in CI
- **Documentation**: Dependency tree shows view relationships

## Testing

```python
# tests/unit/test_view_manager.py
def test_topological_sort():
    """Test views sorted in dependency order"""
    manager = ViewManager()
    sorted_views = manager.topological_sort()

    # active_curations_view should come before curation_summary_view
    assert sorted_views.index("active_curations_view") < sorted_views.index("curation_summary_view")

def test_circular_dependency_detection():
    """Test circular dependency detection"""
    # Create views with circular dependency
    circular_views = [
        ViewDefinition("view_a", "SELECT 1", depends_on=["view_b"]),
        ViewDefinition("view_b", "SELECT 1", depends_on=["view_a"])
    ]

    manager = ViewManager(circular_views)
    with pytest.raises(ValueError, match="Circular dependency"):
        manager.topological_sort()

def test_view_refresh(db_session):
    """Test view refresh in database"""
    refresh_all_views(db_session)

    # Verify views exist
    results = verify_all_views(db_session)
    assert all(results.values())
```

## Dependencies

- SQLAlchemy (already in project)
- Standard library: `dataclasses`, `typing`

## References

- kidney-genetics-db: `backend/app/db/views.py` and `replaceable_objects.py`
- Topological sort: Kahn's algorithm (O(V + E) complexity)
- PostgreSQL view dependencies: `pg_depend` system catalog

## Acceptance Criteria

- [ ] ViewDefinition dataclass and VIEW_DEFINITIONS registry created
- [ ] ViewManager with topological sort algorithm implemented
- [ ] refresh_all_views(), verify_all_views() functions working
- [ ] Make commands (db-refresh-views, db-verify-views, db-show-view-deps) added
- [ ] Admin API endpoints for view management implemented
- [ ] All existing views documented in VIEW_DEFINITIONS
- [ ] Topological sort tested with complex dependency graph
- [ ] Circular dependency detection tested
- [ ] CLAUDE.md updated with view management guidelines
- [ ] Integration tested with real database schema
