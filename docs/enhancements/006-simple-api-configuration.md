# Enhancement: Simple API Configuration (YAML)

**Priority**: Medium
**Complexity**: Low
**Estimated Effort**: 1-2 hours
**Reference**: Simplified from kidney-genetics-db configuration system

## Overview

Implement YAML-based configuration for API-level settings (rate limits, CORS, timeouts) only. Unlike kidney-genetics-db's full system (267 lines for datasources, keywords, workflows), this focuses on deployment-specific API configuration without duplicating Gene Curator's schema-agnostic design.

## Current State

- API configuration scattered in Settings class
- CORS origins, rate limits, timeouts hardcoded
- No easy way to adjust per deployment

## Why Simplified?

**kidney-genetics-db needs**:
- YAML configuration for datasources (PanelApp, HPO, ClinGen URLs)
- Keyword configuration (kidney disease terms)
- 267 lines of pydantic-settings integration

**Gene Curator needs**:
- API-level configuration (rate limits, CORS, timeouts)
- **NOT** workflow/schema configuration (that's what the schema repository is for!)

**Key Insight**: Gene Curator's schema repository **already provides methodology configuration**. YAML config for workflows/scoring would duplicate this and violate the schema-agnostic design.

## Proposed Implementation

### Configuration File

**api.yaml** (`backend/config/api.yaml`)

```yaml
# API Configuration for Gene Curator
# Override with environment variables: GENE_CURATOR_API__<key>

api:
  # CORS settings
  cors:
    allow_origins:
      - "http://localhost:3001"   # Development frontend
      - "http://localhost:5173"   # Vite dev server
    allow_credentials: true
    allow_methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allow_headers: ["*"]

  # Rate limiting
  rate_limits:
    default:
      requests_per_minute: 60
      burst_size: 10
    authenticated:
      requests_per_minute: 300
      burst_size: 50
    admin:
      requests_per_minute: 1000
      burst_size: 100

  # Timeouts
  timeouts:
    default_seconds: 30
    long_running_seconds: 300  # Bulk operations
    external_api_seconds: 10   # HGNC lookups, etc.

  # Pagination
  pagination:
    default_page_size: 50
    max_page_size: 1000

  # File uploads
  uploads:
    max_file_size_mb: 10
    allowed_extensions: [".xlsx", ".csv", ".json"]
```

### Simple YAML Loader

**Configuration Module** (`backend/app/core/api_config.py`)

```python
"""
Simple YAML configuration for API settings.

Only handles deployment-specific API configuration.
Does NOT handle schema/workflow configuration (that's in the database).
"""

from pathlib import Path
from typing import Any, Dict
import yaml
from functools import lru_cache
from pydantic import BaseModel
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CORSConfig(BaseModel):
    """CORS configuration"""
    allow_origins: list[str]
    allow_credentials: bool = True
    allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allow_headers: list[str] = ["*"]


class RateLimitConfig(BaseModel):
    """Rate limit configuration"""
    requests_per_minute: int
    burst_size: int


class TimeoutConfig(BaseModel):
    """Timeout configuration"""
    default_seconds: int = 30
    long_running_seconds: int = 300
    external_api_seconds: int = 10


class PaginationConfig(BaseModel):
    """Pagination configuration"""
    default_page_size: int = 50
    max_page_size: int = 1000


class UploadConfig(BaseModel):
    """File upload configuration"""
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = [".xlsx", ".csv", ".json"]


class APIConfig(BaseModel):
    """Complete API configuration"""
    cors: CORSConfig
    rate_limits: Dict[str, RateLimitConfig]
    timeouts: TimeoutConfig
    pagination: PaginationConfig
    uploads: UploadConfig


@lru_cache(maxsize=1)
def load_api_config() -> APIConfig:
    """Load API configuration from YAML file"""
    config_path = Path("backend/config/api.yaml")

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        # Return defaults
        return APIConfig(
            cors=CORSConfig(allow_origins=["http://localhost:3001"]),
            rate_limits={
                "default": RateLimitConfig(requests_per_minute=60, burst_size=10)
            },
            timeouts=TimeoutConfig(),
            pagination=PaginationConfig(),
            uploads=UploadConfig()
        )

    with open(config_path) as f:
        data = yaml.safe_load(f)

    logger.info(f"Loaded API configuration from {config_path}")
    return APIConfig(**data["api"])


# Singleton instance
api_config = load_api_config()


# Convenience accessors
def get_cors_config() -> CORSConfig:
    """Get CORS configuration"""
    return api_config.cors


def get_rate_limit(limit_type: str = "default") -> RateLimitConfig:
    """Get rate limit configuration"""
    return api_config.rate_limits.get(
        limit_type,
        api_config.rate_limits.get("default")
    )


def get_timeout_config() -> TimeoutConfig:
    """Get timeout configuration"""
    return api_config.timeouts


def get_pagination_config() -> PaginationConfig:
    """Get pagination configuration"""
    return api_config.pagination


def get_upload_config() -> UploadConfig:
    """Get upload configuration"""
    return api_config.uploads
```

### Usage Pattern

**CORS Setup** (`backend/app/main.py`)

```python
from app.core.api_config import get_cors_config

# Configure CORS from YAML
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config.allow_origins,
    allow_credentials=cors_config.allow_credentials,
    allow_methods=cors_config.allow_methods,
    allow_headers=cors_config.allow_headers,
)
```

**Rate Limiting** (if implemented)

```python
from app.core.api_config import get_rate_limit

@router.get("/api/v1/genes")
async def list_genes(user: User = Depends(get_current_user)):
    # Get rate limit based on user role
    limit_type = "admin" if user.role == "admin" else "authenticated"
    rate_limit = get_rate_limit(limit_type)

    # Apply rate limit (using slowapi or similar)
    # ...
```

**Pagination**

```python
from app.core.api_config import get_pagination_config

@router.get("/api/v1/curations")
async def list_curations(
    page: int = 1,
    page_size: int | None = None
):
    pagination = get_pagination_config()
    page_size = page_size or pagination.default_page_size

    # Enforce max page size
    if page_size > pagination.max_page_size:
        page_size = pagination.max_page_size

    # Query with pagination
    # ...
```

### Environment Variable Overrides

```bash
# .env file
# Override YAML values with environment variables
GENE_CURATOR_API__CORS__ALLOW_ORIGINS='["https://production.example.com"]'
GENE_CURATOR_API__RATE_LIMITS__DEFAULT__REQUESTS_PER_MINUTE=120
GENE_CURATOR_API__TIMEOUTS__DEFAULT_SECONDS=60
```

## Implementation Steps

1. **Create config directory**
   ```bash
   mkdir -p backend/config
   ```

2. **Create api.yaml** with CORS, rate limits, timeouts, pagination, uploads

3. **Implement api_config.py** (~150 lines)
   - Pydantic models for each config section
   - load_api_config() function
   - Convenience accessors

4. **Integrate with FastAPI**
   - CORS middleware in main.py
   - Pagination in list endpoints
   - Timeouts in HTTP clients (when using RetryUtils)

5. **Update CLAUDE.md**
   ```markdown
   ## Configuration

   - API configuration: `backend/config/api.yaml`
   - Override with env vars: `GENE_CURATOR_API__<key>`
   - **Do NOT** put workflow/schema configuration in YAML (use schema repository)
   ```

## What We're NOT Configuring (vs kidney-genetics-db)

❌ **Datasource URLs** (Gene Curator doesn't aggregate external data)
❌ **Keyword lists** (Gene Curator isn't search-based)
❌ **Workflow configuration** (that's in the schema repository!)
❌ **Scoring thresholds** (that's in the schema repository!)
❌ **267 lines of pydantic-settings complexity**

**Key Principle**: Don't duplicate Gene Curator's schema-agnostic design. Schemas define workflows, not YAML files.

## Benefits

- **Deployment Flexibility**: Adjust CORS, rate limits per environment
- **Simple**: ~150 lines total, not 267
- **Type-Safe**: Pydantic validation for all config values
- **DRY**: Single source of truth for API configuration
- **Respects Architecture**: Doesn't duplicate schema repository

## Testing

```python
# tests/unit/test_api_config.py
def test_api_config_loading():
    """Test YAML config loading"""
    from app.core.api_config import load_api_config

    config = load_api_config()
    assert config.cors.allow_origins
    assert config.rate_limits["default"].requests_per_minute > 0

def test_cors_config():
    """Test CORS configuration"""
    from app.core.api_config import get_cors_config

    cors = get_cors_config()
    assert "http://localhost:3001" in cors.allow_origins

def test_rate_limit_config():
    """Test rate limit configuration"""
    from app.core.api_config import get_rate_limit

    default_limit = get_rate_limit("default")
    assert default_limit.requests_per_minute == 60

    admin_limit = get_rate_limit("admin")
    assert admin_limit.requests_per_minute > default_limit.requests_per_minute
```

## Dependencies

- `pyyaml` - YAML parsing (add to pyproject.toml)
- Pydantic (already in project)

## Acceptance Criteria

- [ ] backend/config/api.yaml created with all sections
- [ ] api_config.py module implemented (~150 lines)
- [ ] CORS middleware configured from YAML
- [ ] Pagination configured from YAML
- [ ] Environment variable overrides working
- [ ] Unit tests for config loading and accessors
- [ ] CLAUDE.md updated with configuration guidelines
- [ ] **Verified**: No workflow/schema configuration in YAML (kept in database)

---

**Key Difference from kidney-genetics-db**: API-level configuration only. Schema/workflow configuration stays in the schema repository (Gene Curator's core design).
