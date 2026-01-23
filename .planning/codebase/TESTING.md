# Testing Patterns

**Analysis Date:** 2026-01-22

## Backend Testing

### Test Framework

**Runner:**
- pytest 7.4.3+
- Config: `backend/pyproject.toml` [tool.pytest.ini_options]

**Run Commands:**
```bash
make test                    # Run all tests with coverage
make test-fast              # Run without slow tests: pytest -m "not slow"
cd backend && uv run pytest --cov=app
cd backend && uv run pytest --cov=app -k "test_curations"   # Filter tests
cd backend && uv run pytest -m integration                   # Run integration tests only
cd backend && uv run pytest -v --tb=short                   # Verbose with short tracebacks
```

**Assertion Library:**
- Python built-in: `assert expression` (pytest style)
- No extra library needed

**Test Configuration:**
```python
# pyproject.toml settings
minversion = "6.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Test File Organization

**Location:**
- Backend tests co-located with code but in separate `tests/` directory
- Structure mirrors `app/` structure:
  ```
  backend/tests/
  ├── api/           # Tests for app/api/v1/endpoints/
  ├── unit/          # Tests for app/crud/, models, schemas
  ├── services/      # Tests for app/services/
  └── conftest.py    # Shared fixtures
  ```

**Naming:**
- Test files: `test_*.py` (e.g., `test_curations.py`, `test_evidence_api.py`)
- Test classes: `Test*` (e.g., `TestCurationsList`, `TestEvidenceCreate`)
- Test functions: `test_*` (e.g., `test_create_evidence_success`)

**File Example:**
```
backend/tests/
├── conftest.py                    # Database, auth, user fixtures
├── api/
│   ├── test_curations.py         # API endpoint tests
│   ├── test_evidence_api.py       # Evidence endpoint tests
│   └── test_precurations.py       # Precuration tests
├── unit/
│   └── test_curation_schemas.py   # Schema validation tests
└── services/
    └── test_scope_permissions.py  # Permission service tests
```

### Test Structure

**Fixture-Based Organization (conftest.py):**
```python
# backend/tests/conftest.py - Provides reusable fixtures

# Database setup
@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """Create test database engine with SQLite"""
    engine = create_engine("sqlite:///:memory:")
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=test_engine)
    session = sessionmaker(bind=test_engine)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)

# FastAPI test client
@pytest.fixture
def client(db_session: Session) -> TestClient:
    """FastAPI test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# Authentication fixtures
@pytest.fixture
def admin_token(test_user_admin: UserNew) -> str:
    """JWT token for admin user"""
    return create_access_token(
        data={
            "sub": str(test_user_admin.id),
            "email": test_user_admin.email,
            "role": test_user_admin.role.value,
        }
    )

# Data fixtures
@pytest.fixture
def test_gene(db_session: Session) -> Gene:
    """Create test gene in database"""
    gene = Gene(id=uuid4(), hgnc_id="HGNC:1100", approved_symbol="BRCA1")
    db_session.add(gene)
    db_session.commit()
    db_session.refresh(gene)
    return gene
```

**Test Class Organization (Arrange-Act-Assert Pattern):**
```python
# backend/tests/api/test_curations.py
pytestmark = pytest.mark.unit

class TestCurationsList:
    """Tests for GET /curations/"""

    def test_list_curations_empty(self, client: TestClient, admin_token: str):
        """Test listing curations returns empty list when none exist."""
        # Arrange - no data needed, database is empty

        # Act
        response = client.get(
            "/api/v1/curations/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "curations" in data
        assert data["curations"] == []

    def test_list_curations_with_results(
        self, client: TestClient, admin_token: str, test_curation: CurationNew
    ):
        """Test listing curations with existing data."""
        # Arrange - test_curation fixture creates data

        # Act
        response = client.get(
            "/api/v1/curations/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["curations"]) == 1
        assert data["curations"][0]["id"] == str(test_curation.id)
```

### Mocking

**Framework:** `unittest.mock` (Python standard library)

**Pattern: Mocking External APIs**
```python
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_hgnc_api() -> Generator[MagicMock, None, None]:
    """Mock HGNC API responses"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "docs": [{
                    "symbol": "BRCA1",
                    "hgnc_id": "HGNC:1100",
                }]
            }
        }
        mock_get.return_value = mock_response
        yield mock_get
```

**Pattern: Mocking Database Features**
```python
@pytest.fixture(autouse=True)
def mock_rls_context():
    """Mock set_rls_context for SQLite compatibility.

    SQLite doesn't support PostgreSQL's SET session variables used by RLS.
    This mock makes set_rls_context a no-op for tests.
    """
    with patch("app.api.v1.endpoints.curations.set_rls_context"):
        yield
```

**What to Mock:**
- External API calls (HGNC, PubMed, HPO/OLS)
- Database features not supported by SQLite (RLS, row-level security)
- Time-dependent operations (use `freezegun` if needed)
- File I/O

**What NOT to Mock:**
- Your own business logic - test the real code
- Database models and relationships - use test database
- FastAPI dependencies when testing endpoints - use `dependency_overrides`
- Core cryptographic functions - use real implementations

### Fixtures and Factories

**Test Data Fixtures (Provided):**
```python
# Users
@pytest.fixture
def test_user_admin(db_session: Session) -> UserNew:
    """Create test admin user"""
    user = UserNew(
        id=uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_user_curator(db_session: Session, test_scope: Scope) -> UserNew:
    """Create test curator user with scope membership"""
    user = UserNew(id=uuid4(), email="curator@test.com", ...)
    db_session.add(user)
    db_session.flush()

    membership = ScopeMembership(
        scope_id=test_scope.id,
        user_id=user.id,
        role="curator",
    )
    db_session.add(membership)
    db_session.commit()
    return user

# Core entities
@pytest.fixture
def test_scope(db_session: Session) -> Scope:
    """Create test scope"""
    scope = Scope(
        id=uuid4(),
        name="test-scope",
        display_name="Test Scope",
        is_active=True,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope

@pytest.fixture
def test_gene(db_session: Session) -> Gene:
    """Create test gene"""
    import hashlib
    gene_data = "HGNC:1100:BRCA1"
    record_hash = hashlib.sha256(gene_data.encode()).hexdigest()

    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:1100",
        approved_symbol="BRCA1",
        record_hash=record_hash,
    )
    db_session.add(gene)
    db_session.commit()
    db_session.refresh(gene)
    return gene

# Workflows
@pytest.fixture
def test_curation(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_curator: UserNew,
) -> CurationNew:
    """Create test curation"""
    curation = CurationNew(
        id=uuid4(),
        scope_id=test_scope.id,
        gene_id=test_gene.id,
        workflow_stage="curation",
        evidence_data={"status": "in_progress"},
        created_by=test_user_curator.id,
    )
    db_session.add(curation)
    db_session.commit()
    db_session.refresh(curation)
    return curation
```

**Location:**
- All shared fixtures in: `backend/tests/conftest.py`
- Endpoint-specific fixtures in test files themselves
- Never duplicate fixtures

**Creating Custom Fixtures:**
```python
# In test file or conftest.py
@pytest.fixture
def my_custom_fixture(db_session: Session, test_scope: Scope):
    """Create custom test data"""
    # Create and return test object
    return test_object
```

### Coverage

**Requirements:** No explicit minimum enforced in CI, but aim for >80%

**View Coverage:**
```bash
make test                              # Auto-generates coverage report
# View: backend/htmlcov/index.html
# Or: cd backend && uv run pytest --cov=app --cov-report=html
```

**Configuration (pyproject.toml):**
```python
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/alembic/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

---

## Frontend Testing

### Test Framework

**Runner:**
- vitest 3.2.4+ (Vite-native, fast)
- Config: `frontend/vite.config.js` [test] section
- Setup file: `frontend/src/test/setup.js` (auto-loaded)

**Run Commands:**
```bash
cd frontend && npm run test              # Watch mode (default)
cd frontend && npm run test:run          # Single run
cd frontend && npm run test:coverage     # Coverage report
cd frontend && npm run test:ui           # Interactive UI

# Specific test
cd frontend && npm run test:run -- SchemaDrivenCurationForm.spec.js
```

**Assertion Library:**
- vitest built-in: `expect(value).toBe(expected)` (Vitest/Jest style)
- No extra library needed

**Test Configuration (vite.config.js):**
```javascript
test: {
  globals: true,                  // describe, it, expect available globally
  environment: 'happy-dom',       // Lightweight DOM simulation
  setupFiles: ['./src/test/setup.js'],
  css: true,
  exclude: [
    '**/node_modules/**',
    '**/dist/**',
    '**/tests/e2e/**'            // E2E tests separate
  ],
  coverage: {
    provider: 'v8',
    reporter: ['text', 'json', 'html'],
  }
}
```

### Test File Organization

**Location:**
- Co-located with components in `__tests__/` subdirectories
- Pattern: `src/components/__tests__/ComponentName.spec.js`
- E2E tests: separate `frontend/tests/e2e/` directory

**File Structure:**
```
frontend/src/
├── components/
│   ├── EmptyState.vue
│   ├── __tests__/
│   │   └── EmptyState.spec.js
│   └── forms/
│       ├── SchemaDrivenCurationForm.vue
│       └── __tests__/
│           └── SchemaDrivenCurationForm.spec.js
├── stores/
│   ├── disclaimer.js
│   └── (__tests__ optional for stores)
├── composables/
│   ├── usePermissions.js
│   └── __tests__/
│       └── usePermissions.spec.js
└── test/
    └── setup.js                  # Global setup
```

**Naming:**
- Test files: `*.spec.js` (not `.test.js`)
- Example: `EmptyState.spec.js`, `usePermissions.spec.js`

### Test Structure

**Setup File (frontend/src/test/setup.js):**
```javascript
import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { vi } from 'vitest'

// Create Vuetify for all tests
const vuetify = createVuetify({ components, directives })
config.global.plugins = [vuetify]

// Mock browser APIs
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// Mock IntersectionObserver, ResizeObserver (for Vuetify)
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() { return [] }
}
```

**Describe-It Organization (Describe/It Pattern):**
```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from '../EmptyState.vue'

describe('EmptyState', () => {
  describe('Basic Rendering', () => {
    it('should render with required title prop', () => {
      const wrapper = mount(EmptyState, {
        props: { title: 'No data available' }
      })

      expect(wrapper.text()).toContain('No data available')
    })
  })

  describe('Icon Customization', () => {
    it('should apply custom icon size', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          iconSize: 120
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
    })
  })

  describe('Reactivity', () => {
    it('should update when title changes', async () => {
      const wrapper = mount(EmptyState, {
        props: { title: 'Initial title' }
      })

      expect(wrapper.text()).toContain('Initial title')

      await wrapper.setProps({ title: 'Updated title' })

      expect(wrapper.text()).toContain('Updated title')
    })
  })
})
```

### Mocking

**Framework:** vitest `vi.mock()` and `vi.fn()`

**Pattern: Mocking Pinia Stores**
```javascript
import { vi } from 'vitest'

vi.mock('@/stores/schemas', () => ({
  useSchemasStore: vi.fn(() => ({
    schemas: [
      {
        id: 'schema-1',
        name: 'ClinGen SOP v11',
        schema_type: 'curation',
      }
    ],
    getSchemaById: vi.fn(id => ({
      id,
      name: 'ClinGen SOP v11'
    })),
    fetchSchemaById: vi.fn()
  }))
}))
```

**Pattern: Mocking Composables**
```javascript
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    error: vi.fn()
  })
}))

vi.mock('@/composables/useFormRecovery', () => ({
  useFormRecovery: () => ({
    showRecoveryDialog: { value: false },
    recoveryData: { value: null },
    restoreRecovery: vi.fn(),
    discardRecovery: vi.fn()
  })
}))
```

**Pattern: Mocking API Calls**
```javascript
vi.mock('@/api/curations', () => ({
  default: {
    getById: vi.fn(id => Promise.resolve({
      id,
      title: 'Test Curation',
      status: 'draft'
    })),
    create: vi.fn(data => Promise.resolve({ id: '123', ...data }))
  }
}))
```

**Pattern: Mocking Browser APIs**
```javascript
// Typically done in setup.js for global use
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})
```

**What to Mock:**
- External API calls (use factory mocks)
- Pinia stores (mock entire store or individual actions)
- Composables with side effects
- Browser APIs (localStorage, matchMedia, IntersectionObserver)
- Heavy dependencies (rich text editors, maps, etc.)

**What NOT to Mock:**
- Vue components you're testing - mount them
- Event handlers - test real interactions
- Simple helper functions - test the real code
- Vuetify components - they're part of your UI

### Fixtures and Factories

**Test Data Factories (Common Pattern):**
```javascript
// Not a separate file, usually defined in test
function createMockSchema(overrides = {}) {
  return {
    id: 'schema-1',
    name: 'Test Schema',
    schema_type: 'curation',
    version: '1.0',
    ...overrides
  }
}

// Usage in test
it('should handle schema update', () => {
  const schema = createMockSchema({ name: 'Custom Name' })
  // ... test with schema
})
```

**Mount Helpers:**
```javascript
// Use Vue Test Utils directly - no factory needed
const wrapper = mount(ComponentName, {
  props: {
    title: 'Test Title',
    icon: 'mdi-inbox'
  },
  slots: {
    default: '<button>Action</button>'
  },
  global: {
    stubs: {
      // Stub heavy child components if needed
      VComplexChild: true
    }
  }
})
```

**Pinia Setup in Tests:**
```javascript
import { createPinia, setActivePinia } from 'pinia'

beforeEach(() => {
  // Create fresh Pinia instance for each test
  setActivePinia(createPinia())
})

// Now stores work naturally
const store = useMyStore()
store.doSomething()
```

### Coverage

**View Coverage:**
```bash
cd frontend && npm run test:coverage
# View: frontend/coverage/index.html
```

**Target:** Aim for >80% for critical features (forms, auth, workflows)

---

## E2E Testing (Frontend)

### Framework

**Tool:** Playwright 1.56.0+

**Config:** Playwright has own config (not in vite.config.js)

**Run Commands:**
```bash
cd frontend && npm run test:e2e           # Run E2E tests
cd frontend && npm run test:e2e:ui        # Interactive UI
cd frontend && npm run test:e2e:debug     # Debug mode
cd frontend && npm run test:e2e:report    # View report
```

**Example E2E Test:**
- Location: `frontend/tests/e2e/week1-infrastructure.spec.js`
- Tests full user workflows (not unit testing)
- Tests actual browser behavior

---

## Common Patterns

### Async Testing - Backend

**Using pytest-asyncio:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_operation(db_session: Session):
    """Test async operation"""
    result = await some_async_function()
    assert result is not None
```

### Async Testing - Frontend

**Using async/await in vitest:**
```javascript
it('should fetch data', async () => {
  const wrapper = mount(Component)

  await wrapper.vm.$nextTick()  // Vue reactivity
  await new Promise(r => setTimeout(r, 100))  // Wait for API

  expect(wrapper.find('.result').exists()).toBe(true)
})
```

### Error Testing

**Backend:**
```python
def test_create_evidence_unauthorized(client: TestClient, test_curation):
    """Test evidence creation without authentication"""
    response = client.post(
        f"/api/v1/curations/{test_curation.id}/evidence",
        json={"evidence_category": "case_level"},
    )

    assert response.status_code == 403
```

**Frontend:**
```javascript
it('should show error on failed API call', async () => {
  const mock = vi.mock('@/api/curations', () => ({
    getById: vi.fn(() => Promise.reject(new Error('API failed')))
  }))

  const wrapper = mount(Component)
  await wrapper.vm.$nextTick()

  expect(wrapper.find('.error-message').exists()).toBe(true)
})
```

### Skipping/Marking Tests

**Mark as Slow (Backend):**
```python
@pytest.mark.slow
def test_heavy_operation():
    # This test is slow
    # Run with: pytest -m "not slow"
    pass
```

**Mark as Integration (Backend):**
```python
@pytest.mark.integration
def test_full_workflow():
    # Integration test
    pass
```

**Skip Temporarily (Frontend):**
```javascript
it.skip('should do something', () => {
  // This test is temporarily disabled
})

it.todo('should implement feature', () => {
  // Not yet implemented
})
```

**CRITICAL:** Never use `.skip()` or `xit()` permanently! Always fix or delete.

---

*Testing analysis: 2026-01-22*
