# Enhancement: CacheService with L1/L2 Architecture

**Priority**: High
**Complexity**: Medium
**Estimated Effort**: 6-8 hours
**Reference**: `kidney-genetics-db/backend/app/core/cache_service.py` (1,019 lines)

## Overview

Implement a unified multi-layer caching system with L1 (in-memory LRU) + L2 (PostgreSQL JSONB) layers, intelligent TTL management per namespace, and comprehensive statistics. Replace ad-hoc caching patterns with a single DRY-compliant service.

## Current State

- No unified caching system
- Potential for redundant cache implementations across the codebase
- No persistent cache layer (loses data on restart)
- No cache statistics or monitoring

## Proposed Implementation

### Architecture

```
┌─────────────────────────────────────┐
│   Application Layer                 │
├─────────────────────────────────────┤
│   CacheService                      │
│   ┌──────────┐     ┌──────────┐   │
│   │ L1 Cache │ ──> │ L2 Cache │   │
│   │ (Memory) │     │ (Postgres)│   │
│   │ <10ms    │     │ ~50ms    │   │
│   └──────────┘     └──────────┘   │
└─────────────────────────────────────┘
```

### Core Components

**1. CacheService Class** (`backend/app/core/cache_service.py`)

```python
class CacheService:
    """Unified multi-layer cache with TTL per namespace"""

    def __init__(self, db_session: Session | None = None):
        self.memory_cache = cachetools.LRUCache(maxsize=10000)
        self.db_session = db_session
        self.stats = CacheStats()

        # TTL per namespace (seconds)
        self.namespace_ttls = {
            "schemas": 3600 * 24 * 7,      # 7 days (rarely changes)
            "scopes": 3600 * 24,           # 1 day
            "genes": 3600,                 # 1 hour
            "validations": 3600,           # 1 hour
            "scoring": 1800,               # 30 minutes
            "default": 3600,               # 1 hour
        }

    # Primary API
    async def get(self, key: Any, namespace: str = "default", default: Any = None) -> Any
    async def set(self, key: Any, value: Any, namespace: str = "default", ttl: int | None = None) -> bool
    async def delete(self, key: Any, namespace: str = "default") -> bool

    # Cache-aside pattern
    async def get_or_set(self, key: Any, fetch_func: Callable, namespace: str, ttl: int | None) -> Any

    # Namespace management
    async def clear_namespace(self, namespace: str) -> int
    def clear_namespace_sync(self, namespace: str) -> int  # For thread pool execution

    # Statistics
    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]
```

**2. CacheEntry Class** (Metadata tracking)

```python
class CacheEntry:
    """Cache entry with metadata and expiration"""
    key: str
    value: Any
    namespace: str
    created_at: datetime
    expires_at: datetime | None
    access_count: int
    last_accessed: datetime

    def is_expired(self) -> bool
    def touch(self) -> None  # Update access statistics
```

**3. CacheStats Class** (Monitoring)

```python
class CacheStats:
    """Cache performance statistics"""
    hits: int
    misses: int
    sets: int
    deletes: int
    errors: int

    @property
    def hit_rate(self) -> float:
        return self.hits / (self.hits + self.misses)

    def to_dict(self) -> dict[str, Any]
```

### Database Schema

```sql
CREATE TABLE IF NOT EXISTS cache_entries (
    id BIGSERIAL PRIMARY KEY,
    cache_key VARCHAR(512) NOT NULL UNIQUE,
    namespace VARCHAR(255) NOT NULL DEFAULT 'default',
    data JSONB NOT NULL,
    data_size INTEGER,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 1,
    metadata JSONB,
    INDEX idx_cache_namespace_expires (namespace, expires_at),
    INDEX idx_cache_key (cache_key)
);

-- View for cache statistics
CREATE OR REPLACE VIEW cache_stats AS
SELECT
    namespace,
    COUNT(*) as entry_count,
    SUM(data_size) as total_size,
    AVG(access_count) as avg_access_count,
    MAX(last_accessed) as last_access
FROM cache_entries
GROUP BY namespace;
```

### Usage Pattern

```python
# Get or create cache service
from app.core.cache_service import get_cache_service

cache = get_cache_service(db_session)

# Simple get/set
await cache.set("gene:123", gene_data, namespace="genes", ttl=3600)
gene_data = await cache.get("gene:123", namespace="genes")

# Cache-aside pattern (most common)
gene_data = await cache.get_or_set(
    key=f"gene:{gene_id}",
    fetch_func=lambda: crud_gene.get_gene(db, gene_id),
    namespace="genes",
    ttl=3600
)

# Clear namespace (e.g., after schema update)
count = await cache.clear_namespace("schemas")
logger.info(f"Cleared {count} schema cache entries")

# Get statistics
stats = await cache.get_stats(namespace="genes")
# Returns: {'hits': 1250, 'misses': 85, 'hit_rate': 0.936, ...}
```

### Decorator Pattern (Optional)

```python
# backend/app/core/cache_decorator.py
from functools import wraps

def cache(namespace: str, ttl: int = 3600):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_service = get_cache_service()
            key = f"{func.__name__}:{args}:{kwargs}"
            return await cache_service.get_or_set(
                key=key,
                fetch_func=lambda: func(*args, **kwargs),
                namespace=namespace,
                ttl=ttl
            )
        return wrapper
    return decorator

# Usage
@cache(namespace="genes", ttl=3600)
async def get_gene_details(gene_id: int):
    # Automatically cached for 1 hour
    return await fetch_gene_from_db(gene_id)
```

## Implementation Steps

1. **Create cache service module** (`backend/app/core/cache_service.py`)
   - Implement CacheService, CacheEntry, CacheStats classes (~1,019 lines)
   - Support both sync/async database sessions
   - Handle serialization for complex types (Pydantic models, DataFrames)

2. **Add cache_entries table migration**
   ```bash
   cd database/sql
   # Add to new migration file
   ```

3. **Create factory function** for dependency injection
   ```python
   # Singleton pattern with session binding
   def get_cache_service(db_session: Session | None = None) -> CacheService
   ```

4. **Add cache management endpoint** (`backend/app/api/v1/endpoints/cache.py`)
   ```python
   @router.get("/cache/stats")
   async def get_cache_stats(namespace: str | None = None):
       """Get cache statistics"""

   @router.delete("/cache/namespace/{namespace}")
   async def clear_namespace(namespace: str):
       """Clear all entries in a namespace"""
   ```

5. **Integrate with existing CRUD operations**
   ```python
   # Example: Schema CRUD
   async def get_schema_by_id(db: Session, schema_id: int):
       cache = get_cache_service(db)
       return await cache.get_or_set(
           key=f"schema:{schema_id}",
           fetch_func=lambda: _fetch_schema_from_db(db, schema_id),
           namespace="schemas",
           ttl=3600 * 24 * 7  # 7 days
       )
   ```

6. **Update CLAUDE.md** with DRY principle
   ```markdown
   ## Caching (MUST USE)
   - ALWAYS use `get_cache_service(db_session)`
   - NEVER create custom cache implementations
   - Use namespaces for logical grouping
   ```

## Benefits

- **Performance**: <10ms L1 cache, 75-95% hit rates (proven in production)
- **Persistence**: L2 cache survives restarts, shared across instances
- **DRY**: Single caching interface, no more scattered cache dictionaries
- **Observability**: Built-in statistics (hit rate, entry count, size)
- **Flexibility**: TTL per namespace, configurable per use case

## Testing

```python
# tests/unit/test_cache_service.py
async def test_cache_set_get():
    cache = CacheService()
    await cache.set("key", "value", namespace="test")
    value = await cache.get("key", namespace="test")
    assert value == "value"

async def test_cache_expiration():
    cache = CacheService()
    await cache.set("key", "value", namespace="test", ttl=1)
    await asyncio.sleep(2)
    value = await cache.get("key", namespace="test")
    assert value is None  # Expired

async def test_cache_l1_l2_fallback(db_session):
    cache = CacheService(db_session)
    await cache.set("key", "value", namespace="test")
    # Clear L1, verify L2 fallback works
    cache.memory_cache.clear()
    value = await cache.get("key", namespace="test")
    assert value == "value"  # Retrieved from L2

def test_cache_statistics():
    cache = CacheService()
    stats = cache.stats
    assert stats.hit_rate == 0.0  # No hits yet
```

## Dependencies

- `cachetools` - LRU cache implementation
- SQLAlchemy - Database persistence
- Standard library: `hashlib`, `json`, `datetime`

## References

- kidney-genetics-db: `backend/app/core/cache_service.py` (1,019 lines)
- Production metrics: <10ms cached, 75-95% hit rates
- Documentation: `docs/implementation-notes/completed/cache-refactor.md`

## Acceptance Criteria

- [ ] CacheService implemented with L1/L2 layers
- [ ] cache_entries table created via migration
- [ ] get_cache_service() factory function working
- [ ] Cache statistics endpoint implemented
- [ ] At least 3 CRUD operations integrated with cache
- [ ] TTL per namespace configured for Gene Curator domains
- [ ] CLAUDE.md updated with DRY caching guidelines
- [ ] Unit tests covering L1/L2 fallback, expiration, statistics
- [ ] Cache hit rate >70% after integration (verify in logs)
