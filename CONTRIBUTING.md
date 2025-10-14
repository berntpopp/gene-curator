# Contributing to Gene Curator

Thank you for your interest in contributing to Gene Curator! This guide will help you get started.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Make (optional but recommended)
- Git
- Node.js 18+ (for local frontend development)
- Python 3.11+ with uv (for local backend development)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/halbritter-lab/gene-curator.git
cd gene-curator

# Start hybrid development mode (recommended)
make hybrid-up  # Starts DB in Docker
make backend    # Terminal 1: Starts backend API
make frontend   # Terminal 2: Starts frontend

# Or use full Docker mode
make dev        # Starts all services
```

### Access Development Environment
- **Frontend**: http://localhost:5193 (Vite) or http://localhost:3051 (Docker)
- **Backend API**: http://localhost:8051
- **API Docs**: http://localhost:8051/docs
- **Database**: localhost:5454

**Default Credentials**: admin@gene-curator.dev / admin123

## Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes
Follow the coding standards below and use the unified logging system.

### 3. Test Your Changes
```bash
make test           # Backend tests
make lint           # Backend linting
make lint-frontend  # Frontend linting
make format-all     # Auto-format all code
make check-all      # Complete quality check
```

**⚠️ All linting must pass with zero errors/warnings before committing.**

### 4. Commit Your Changes
```bash
git add .
git commit -m "feat: add new feature" # or "fix:", "docs:", "refactor:", etc.
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format.

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Coding Standards

### Backend (Python/FastAPI)

#### Logging
```python
from app.core.logging import get_logger, api_endpoint, timed_operation

logger = get_logger(__name__)  # NOT logging.getLogger()
logger.info("Operation completed", key="value")

@api_endpoint()  # Auto-timing for endpoints
async def my_endpoint(): pass

@timed_operation("operation_name", warning_threshold_ms=200)
async def expensive_operation(): pass
```

**Never use**: `logging.getLogger()`, `print()`, or f-strings for errors

#### Configuration
```python
from app.core.constants import DEFAULT_PAGE_SIZE, HTTP_200_OK
from app.core.api_config import get_cors_config, get_pagination_config
```

**Never**: Hardcode magic numbers, store secrets in YAML, put workflow config in YAML

#### SQLAlchemy Queries
```python
# ✅ CORRECT
query.filter(Model.is_active)
query.filter(~Model.is_active)

# ❌ WRONG - WILL FAIL
query.filter(Model.is_active is True)
```

**Why**: SQLAlchemy overloads `__bool__()`, `is` checks object identity not value.

### Frontend (Vue 3/JavaScript)

#### Logging
```javascript
// Composition API
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()
logger.info('Operation completed', { key: 'value' })

// Stores/utilities
import { logService } from '@/services/logService'
logService.info('Message', { key: 'value' })
```

**Never use**: `console.log()`, `console.error()`, `alert()`

**Log Viewer**: Press `Ctrl+L` (Windows/Linux) or `Cmd+L` (Mac) to toggle

#### Pinia Store Pattern
All stores follow consistent API:
```javascript
fetchItems()              // Fetch all
fetchItemById(id)         // Fetch single
createItem(data)          // Create
updateItem(id, data)      // Update
deleteItem(id)            // Delete
```

## Architecture Overview

Gene Curator uses a **schema-agnostic, scope-based architecture**:

- **Schema-Driven**: Everything configurable via `curation_schemas` table (NOT config files)
- **Scope-Based**: Clinical specialties (kidney-genetics, cardio-genetics, etc.)
- **Multi-Stage Workflow**: Entry → Precuration → Curation → Review (4-eyes) → Active
- **Pluggable Scoring**: ClinGen SOP v11, GenCC, Qualitative engines

See `PLAN.md` for complete architecture details.

## Common Tasks

### Add a New API Endpoint
1. Create endpoint in `backend/app/api/v1/endpoints/`
2. Add route to `backend/app/api/v1/api.py`
3. Create Pydantic schemas in `backend/app/schemas/`
4. Add CRUD operations in `backend/app/crud/`
5. Write tests in `backend/app/tests/`
6. Run `make lint test`

### Add a New Frontend Component
1. Create component in `frontend/src/components/`
2. Use Composition API with `<script setup>`
3. Follow existing Pinia store patterns
4. Add to relevant view in `frontend/src/views/`
5. Run `make lint-frontend`

### Add a New Scoring Engine
1. Create engine in `backend/app/scoring/` extending `ScoringEngine`
2. Register in `backend/app/scoring/registry.py`
3. Add schema example to database
4. Write tests for scoring logic
5. Document in `docs/`

### Update Database Schema
1. Create migration in `database/sql/`
2. Update SQLAlchemy models in `backend/app/models/models.py`
3. Run `make db-reset` to test
4. Update seed data in `database/sql/004_seed_data.sql`

## Testing

### Backend Tests
```bash
make test              # All tests
make test-unit         # Unit tests only
cd backend && uv run pytest --cov=app  # With coverage
```

### Frontend Tests
```bash
cd frontend && npm run test
```

### Manual Testing
Use the API docs at http://localhost:8051/docs for interactive testing.

## Documentation

When adding features:
1. Update relevant files in `docs/`
2. Update `CLAUDE.md` if changing core patterns
3. Update `PLAN.md` if changing architecture
4. Add inline code documentation
5. Update this `CONTRIBUTING.md` if changing workflow

## Getting Help

- **Questions**: Open a GitHub issue with the "question" label
- **Bugs**: Open a GitHub issue with the "bug" label
- **Feature Requests**: Open a GitHub issue with the "enhancement" label
- **Documentation**: Check `docs/` folder or `CLAUDE.md`

## Code Review Process

All contributions require:
1. ✅ All tests passing
2. ✅ All linting passing (zero errors/warnings)
3. ✅ Code follows established patterns
4. ✅ Documentation updated
5. ✅ At least one approving review

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

**Thank you for contributing to Gene Curator!**

*Last Updated: 2025-10-14*
