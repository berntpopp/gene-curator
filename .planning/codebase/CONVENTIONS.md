# Coding Conventions

**Analysis Date:** 2026-01-22

## Backend (Python) Conventions

### Naming Patterns

**Files:**
- Module files: `lowercase_with_underscores.py` (e.g., `unified_logger.py`, `schema_validators.py`)
- Test files: `test_*.py` (e.g., `test_curations.py`, `test_evidence_api.py`)
- CRUD modules: `crud_*.py` or direct entity names (e.g., `curation.py`, `gene.py`)

**Functions:**
- Snake case: `def get_user_scope_role()`, `def can_user_edit_curation()`, `def _format_console_message()`
- Private/internal: prefix with underscore `_can_user_review_curation()`, `_get_current_context()`
- Async functions: same convention `async def fetch_schema_by_id()`

**Variables:**
- Snake case: `test_user_admin`, `db_session`, `evidence_data`, `mock_response`
- Constants: UPPERCASE `SQLALCHEMY_TEST_DATABASE_URL`, `DISCLAIMER_KEY`, `CURRENT_DISCLAIMER_VERSION`
- Type aliases: PascalCase `PyUUID` (see `models.py`)

**Classes:**
- PascalCase: `UnifiedLogger`, `DatabaseLogger`, `CRUDBase`, `ScopeMembership`
- Enums: PascalCase `UserRoleNew`, `WorkflowStage`, `ReviewStatus`, `CurationStatus`
- Test classes: `Test*` prefix (e.g., `TestCurationsList`, `TestEvidenceCreate`)

**Type Hints:**
- Modern type union syntax: `str | None` (not `Optional[str]`)
- Union types: `str | dict[str, Any]`
- Full qualified imports: `from typing import Any`

### Code Style

**Formatting:**
- Tool: `ruff` with line-length = 88
- Quote style: double quotes `"string"`
- Indent: 4 spaces
- No trailing commas (per ruff config)

**Linting:**
- Tool: `ruff` with strict rules (E, W, F, I, C, B, UP, N, S, T20, SIM, RUF)
- Type checking: `mypy` with strict=true
- Security: `bandit` (flake8-bandit enabled)

**Key Rules Applied:**
- `E`, `W`: PEP 8 style
- `I`: Import sorting (first-party imports: `app`)
- `B`: Bugbear patterns
- `S101`: assert allowed in tests only
- `B008`: FastAPI Depends() exceptions allowed
- `T201`: print statements allowed in scripts
- `N805`: class method naming exceptions

### Import Organization

**Order (enforced by ruff isort):**
```python
# 1. Standard library
import asyncio
import hashlib
import uuid
from collections.abc import Generator
from typing import Any, TYPE_CHECKING
from uuid import UUID as PyUUID

# 2. Third-party
import pytest
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# 3. First-party (app)
from app.core.database import Base, get_db
from app.core.logging import get_logger, api_endpoint
from app.models.models import Scope, UserNew
from app.schemas.curation import CurationCreate
```

**Path Aliases:**
- `from app.*`: First-party root imports throughout codebase
- No relative imports in app code
- Local imports in functions only when avoiding circular dependencies

**Type Imports:**
- Circular dependencies: Use `TYPE_CHECKING` guard
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from .database_logger import DatabaseLogger
  ```

### Error Handling

**Patterns:**
- FastAPI exceptions for HTTP errors: `HTTPException(status_code=404, detail="Not found")`
- Custom exceptions for business logic (check `app/core/exceptions.py` if exists)
- Context managers for resource cleanup:
  ```python
  with TestClient(app) as test_client:
      yield test_client
  ```

**Logging Errors:**
- Always use structured logging: `logger.error("Message", error=exception, key="value")`
- Never: `logger.error(f"Error: {e}")` or `print(e)`
- Include context: operation IDs, user IDs, resource IDs

**Async Patterns:**
- `async def` for async functions
- `await` for async calls
- Auto-detect async context: no separate sync/async methods
  ```python
  def _log_async_or_sync(self, level: str, message: str):
      """Auto-detect async context"""
      try:
          asyncio.get_running_loop()
          # Async context - schedule async task
      except RuntimeError:
          # Sync context - handle synchronously
  ```

### Logging

**Framework:** Custom `UnifiedLogger` (NOT `logging.getLogger()`)

**Usage:**
```python
from app.core.logging import get_logger, api_endpoint, timed_operation

logger = get_logger(__name__)  # Always use this

# Structured logging with context
logger.info("Event occurred", operation_id="123", duration_ms=456, user_id="uuid")
logger.error("Error occurred", error=exception, context_key="value")

# Performance decorators
@api_endpoint()  # Auto-timing for endpoints
async def my_endpoint(): pass

@timed_operation("complex_calc", warning_threshold_ms=200)
async def calculate(): pass
```

**Never:**
- ❌ `logging.getLogger()` - Use `get_logger()`
- ❌ `print()` - Use logger
- ❌ `f"Error: {e}"` - Use structured kwargs: `error=exception`
- ❌ Plain text messages - Always include key context

### Comments

**When to Comment:**
- Complex business logic: explain WHY (not WHAT)
- Workarounds: explain why standard approach doesn't work
- Non-obvious algorithm decisions
- Module docstrings: required for all modules, classes, public functions

**JSDoc/docstrings:**
- Triple-quoted docstring style:
  ```python
  def get_user_scope_role(db: Session, user_id: UUID, scope_id: UUID) -> str | None:
      """Get user's role for a specific scope from scope_memberships.

      Args:
          db: Database session
          user_id: User UUID
          scope_id: Scope UUID

      Returns:
          Role string if membership exists, None otherwise
      """
  ```
- Module docstrings explain architecture/purpose:
  ```python
  """
  Unified logging system for Gene Curator.

  This module provides structured logging with dual output:
  - Console (sync) for immediate visibility
  - Database (async) for 90-day persistence

  Usage:
      from app.core.logging import get_logger
      logger = get_logger(__name__)
  """
  ```

### Function Design

**Size:** Keep functions focused on single responsibility
- Helper functions: 10-30 lines
- Endpoint handlers: 20-50 lines
- Complex logic: extract to separate functions

**Parameters:**
- Positional: core required parameters first
- Keyword-only: use explicit `db: Session, user: UserNew` style
- Avoid single-letter names except `db`, `id`

**Return Values:**
- Type hints always present: `-> str | None` (not `-> Optional[str]`)
- Return immediately on error (fail-fast):
  ```python
  if not user:
      return None
  # Continue with valid user
  ```

### Module Design

**Exports:**
- Public functions/classes: define and use directly
- Private helpers: prefix with `_`
- `__all__` list in modules with many exports (e.g., `__init__.py`)

**Barrel Files:**
- Used in `app/core/logging/__init__.py` to expose unified interface
- Consolidate imports: `from .unified_logger import get_logger`

**CRUD Classes:**
- Base class: `CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]`
- Standard methods: `get()`, `get_multi()`, `create()`, `update()`, `delete()`
- Custom methods: add specific query logic

---

## Frontend (Vue 3 + JavaScript) Conventions

### Naming Patterns

**Files:**
- Components: PascalCase `EmptyState.vue`, `SchemaDrivenCurationForm.vue`
- Views: PascalCase `UserManagement.vue`, `GeneDetail.vue`
- Stores: camelCase `disclaimer.js`, `evidence.js`, `workflow.js`
- Composables: camelCase `usePermissions.js`, `useFormRecovery.js`
- Tests: `*.spec.js` (e.g., `EmptyState.spec.js`, `SchemaDrivenCurationForm.spec.js`)
- Services: camelCase `logService.js`, `scopeService.js`

**Components:**
- PascalCase in templates: `<EmptyState />`, `<LoadingState />`
- Multi-word required: `<SchemaSelect />` not `<Select />`
- Props: camelCase `icon`, `title`, `description`
- Events: kebab-case in templates, camelCase in JS: `@item-selected` → `itemSelected`

**Variables/Functions:**
- camelCase: `isAcknowledged`, `acknowledgmentTimestamp`, `formattedAcknowledgmentDate`
- Constants: UPPERCASE: `DISCLAIMER_KEY`, `CURRENT_DISCLAIMER_VERSION`
- Booleans: prefix with `is`, `can`, `has`, `should`: `isLoading`, `canEdit`, `hasError`
- Getters: descriptive: `formattedAcknowledgmentDate`, `isCurrentVersionAcknowledged`

**Pinia Stores:**
- Composition API style (newer pattern):
  ```javascript
  export const useUserStore = defineStore('user', () => {
    const state = ref({})
    const getters = {}
    const actions = {}
    return { state, getters, actions }
  })
  ```
- Options API style (legacy but still used):
  ```javascript
  export const useDisclaimerStore = defineStore('disclaimer', {
    state: () => ({ isAcknowledged: false }),
    getters: { isCurrentVersionAcknowledged: state => {} },
    actions: { initialize() {} }
  })
  ```

### Code Style

**Formatting:**
- Tool: Prettier with custom config
- Quote style: single quotes `'string'`
- Line length: 100 characters
- Semicolons: false (no trailing semicolons)
- Tab width: 2 spaces
- Trailing commas: none (same as Prettier)

**Linting:**
- Tool: ESLint with vue3-recommended config
- Rules: vue3-specific (multi-word components, prop naming, etc.)
- Key rules:
  - `vue/component-definition-name-casing`: PascalCase
  - `vue/component-name-in-template-casing`: PascalCase
  - `vue/prop-name-casing`: camelCase
  - `vue/attribute-hyphenation`: always use kebab-case
  - `vue/v-bind-style`: shorthand (`:prop=` instead of `v-bind:prop=`)
  - `vue/v-on-style`: shorthand (`@click=` instead of `v-on:click=`)
  - `no-console`: warn in production, off in dev
  - `no-debugger`: error in production

### Import Organization

**Order (ESLint enforced):**
```javascript
// 1. Vue/library imports
import { defineStore } from 'pinia'
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// 2. Vuetify/UI imports
import { createVuetify } from 'vuetify'

// 3. First-party imports from @/ alias
import { logService } from '@/services/logService'
import { usePermissions } from '@/composables/usePermissions'
import EmptyState from '@/components/EmptyState.vue'
```

**Path Aliases:**
- `@/`: src directory root (configured in vite.config.js)
- Import from: `@/stores/`, `@/services/`, `@/components/`, `@/composables/`

### Error Handling

**Patterns:**
- Try-catch for API calls:
  ```javascript
  try {
    const result = await apiCall()
    return result
  } catch (error) {
    logService.error('Operation failed', { error: error.message })
    throw error
  }
  ```

**Logging Errors:**
- Use logService: `logService.error('Message', { error: error.message })`
- Never: ❌ `console.error()`, ❌ `alert()`, ❌ `throw error;`
- Structured: always include error context

**User Feedback:**
- Toast notifications via store: `notificationsStore.addToast()`
- Error dialogs in components
- Never show raw error messages to users

### Logging

**Framework:** `logService` (NOT `console.log()`)

**Usage:**
```javascript
import { logService } from '@/services/logService'

// In components (Composition API)
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()
logger.info('Event', { key: 'value' })

// In stores/services
logService.info('Message', { context: 'value' })
logService.error('Error occurred', { error: exception.message })

// Log viewer: Ctrl+L / Cmd+L
```

**Never:**
- ❌ `console.log()` - Use logger
- ❌ `console.error()` - Use logger
- ❌ `alert()` - Use notifications
- ❌ `debugger` - Use DevTools

### Comments

**When to Comment:**
- Complex state logic: explain state transitions
- Workarounds: explain browser/library compatibility issues
- Non-obvious props/slots: document purpose and usage

**JSDoc:**
- Required for components (top of template):
  ```javascript
  /**
   * EmptyState Component
   *
   * Displays an empty state with icon, title, and optional action
   *
   * Props:
   *   - title (String, required): Empty state title
   *   - icon (String): Icon name (default: mdi-inbox)
   *   - description (String): Optional subtitle
   *
   * Slots:
   *   - default: Action buttons or content
   */
  ```

- For stores:
  ```javascript
  /**
   * Disclaimer store
   * Manages disclaimer acknowledgment state
   */
  ```

### Component Design

**Composition API (Recommended for new code):**
```javascript
<script setup>
import { ref, computed } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()

// State
const isLoading = ref(false)

// Computed
const displayText = computed(() => props.title.toUpperCase())

// Methods
const handleClick = () => {
  logger.info('Clicked')
}
</script>
```

**Options API (Legacy, still used):**
```javascript
export default {
  name: 'ComponentName',
  props: { title: String },
  data() { return { isLoading: false } },
  computed: { displayText() {} },
  methods: { handleClick() {} }
}
```

**Props:**
- Always define with type: `title: String`, `icon: String`, `iconSize: [String, Number]`
- With validation: `maxWidth: { type: Number, default: 400 }`
- Never: ❌ props without types

**Slots:**
- Named slots: `<slot name="actions"></slot>`
- Scoped slots for lists: `<slot :item="item" />`
- Document in JSDoc

**Emits:**
- Define: `const emit = defineEmits(['update', 'delete'])`
- Usage: `emit('update', value)`

### Store Design (Pinia)

**Structure (Options API - common in codebase):**
```javascript
export const useDisclaimerStore = defineStore('disclaimer', {
  state: () => ({
    isAcknowledged: false,
    acknowledgmentTimestamp: null
  }),

  getters: {
    formattedAcknowledgmentDate: state => {
      // Computed values
    },
    shouldShowDisclaimer: state => {
      // Boolean getters
    }
  },

  actions: {
    initialize() {
      // Fetch/load data
    },
    acknowledge() {
      // Modify state
    }
  }
})
```

**Standard Methods (ALL stores follow this pattern):**
- `fetchItems()` - Get list
- `fetchItemById(id)` - Get single
- `createItem(data)` - Create
- `updateItem(id, data)` - Update
- `deleteItem(id)` - Delete
- `initialize()` - Load from storage/API

**State Persistence:**
- Use localStorage for user preferences
- Use sessionStorage for temporary data
- Pattern: save to storage in actions

---

## Shared Conventions

### Boolean Filters (CRITICAL - SQLAlchemy)

**CORRECT:**
```python
query.filter(Model.is_active)                    # Truthy check
query.filter(~Model.is_active)                   # Negation
query.filter(Model.is_active == True)            # Explicit equality
query.filter(Model.is_active != False)           # Explicit inequality
```

**WRONG (WILL FAIL):**
```python
query.filter(Model.is_active is True)    # ❌ SQLAlchemy overloads __bool__
query.filter(Model.is_active is False)   # ❌ Identity check, not value check
```

**Why:** SQLAlchemy overrides `__bool__()` for column expressions. Use explicit `==` instead.

### Testing Patterns - Backend

**Markers:**
- `@pytest.mark.unit` - Unit tests (default)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (excluded with `-m "not slow"`)

**Arrange-Act-Assert:**
```python
def test_create_evidence_success(client: TestClient, curator_token: str):
    # Arrange
    evidence_data = { "evidence_category": "case_level" }

    # Act
    response = client.post(
        f"/api/v1/curations/{curation_id}/evidence",
        json=evidence_data,
        headers={"Authorization": f"Bearer {curator_token}"}
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["evidence_category"] == "case_level"
```

**Comments in Tests:** Explain test setup when non-obvious:
```python
def test_create_evidence_unauthorized(client: TestClient, test_curation):
    """Test evidence creation without authentication

    Note: FastAPI's HTTPBearer returns 403 (not 401) when no credentials
    are provided, per OAuth 2.0 Bearer Token spec (RFC 6750).
    """
```

### Testing Patterns - Frontend

**Test Setup:**
- Framework: `vitest` (https://vitest.dev)
- Runner: `happy-dom` environment
- Setup file: `src/test/setup.js` (auto-loaded)

**Structure:**
```javascript
describe('ComponentName', () => {
  describe('Specific Feature', () => {
    it('should do something', () => {
      const wrapper = mount(Component, { props: {} })
      expect(wrapper.text()).toContain('expected')
    })
  })
})
```

**Mocking:**
```javascript
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: '123', name: 'Test' },
    isLoggedIn: true
  }))
}))
```

---

*Convention analysis: 2026-01-22*
