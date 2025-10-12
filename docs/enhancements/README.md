# Gene Curator - Enhancement Issues

This directory contains detailed enhancement proposals inspired by battle-tested patterns from the [kidney-genetics-db](https://github.com/halbritter-lab/kidney-genetics-db) project. Each enhancement is designed following **DRY**, **KISS**, **SOLID**, and **modularization** principles.

## Overview

These enhancements address infrastructure gaps identified through comparative analysis of Gene Curator vs kidney-genetics-db. All proposals are **production-proven** with documented performance metrics and real-world usage.

## Enhancement Index

| ID | Enhancement | Priority | Effort | Status |
|----|-------------|----------|--------|--------|
| [001](001-unified-logger-system.md) | Unified Logger System | High | 4-6h | 📋 Planned |
| [002](002-cache-service-l1-l2.md) | CacheService with L1/L2 | High | 6-8h | 📋 Planned |
| [003](003-retry-utils-exponential-backoff.md) | RetryUtils with Backoff | Medium | 3-4h | 📋 Planned |
| [004](004-expanded-makefile-workflow.md) | Expanded Makefile | Medium | 2-3h | 📋 Planned |
| [005](005-realtime-progress-tracking.md) | Real-Time Progress | Low-Medium | 6-8h | 📋 Planned |
| [006](006-yaml-configuration-system.md) | YAML Configuration | Medium | 4-5h | 📋 Planned |
| [007](007-view-management-topological-sort.md) | View Management | Low | 3-4h | 📋 Planned |

**Total Estimated Effort**: 28-36 hours

## Implementation Strategy

### Phase 1: Core Infrastructure (High Priority)
**Estimated: 13-18 hours**

Establish foundational systems that eliminate code duplication and improve observability:

1. **[001 - Unified Logger System](001-unified-logger-system.md)** (4-6h)
   - Structured logging with request correlation
   - Dual output (console + database)
   - Performance monitoring decorators

2. **[002 - CacheService L1/L2](002-cache-service-l1-l2.md)** (6-8h)
   - Multi-layer caching (memory + PostgreSQL)
   - 75-95% hit rates (proven)
   - TTL per namespace

3. **[003 - RetryUtils](003-retry-utils-exponential-backoff.md)** (3-4h)
   - Exponential backoff with jitter
   - Circuit breaker pattern
   - 95%+ success rate for transient failures

**Why Start Here?**
- These are **dependency-free** and provide immediate value
- Logger + Cache + Retry = foundation for all other features
- Establishes DRY patterns early in development

### Phase 2: Developer Experience (Medium Priority)
**Estimated: 6-8 hours**

Improve daily development workflow and configuration management:

4. **[004 - Expanded Makefile](004-expanded-makefile-workflow.md)** (2-3h)
   - Hybrid development mode (DB in Docker, local API/Frontend)
   - `make status` command with real-time statistics
   - Comprehensive backup/restore commands

5. **[006 - YAML Configuration](006-yaml-configuration-system.md)** (4-5h)
   - Externalized configuration
   - Environment-based overrides
   - No more hardcoded values

**Why Second?**
- Makefile improvements = instant productivity boost
- YAML configuration enables deployment flexibility

### Phase 3: Advanced Features (Optional)
**Estimated: 9-12 hours**

Add sophisticated features for production deployments:

6. **[005 - Real-Time Progress](005-realtime-progress-tracking.md)** (6-8h)
   - WebSocket-based progress updates
   - Event bus architecture
   - 100% WebSocket stability (proven)

7. **[007 - View Management](007-view-management-topological-sort.md)** (3-4h)
   - Topological sort for view dependencies
   - Safe view refresh operations
   - Dependency visualization

**Why Last?**
- Nice-to-have but not critical for core functionality
- Can be implemented after production launch

## How to Use These Issues

### For Developers

Each enhancement file follows a consistent structure:

```markdown
# Enhancement: [Name]

**Priority**: High/Medium/Low
**Complexity**: Low/Medium/High
**Estimated Effort**: X-Y hours
**Reference**: kidney-genetics-db implementation

## Overview
[High-level description]

## Current State
[What Gene Curator lacks]

## Proposed Implementation
[Detailed architecture, code examples, usage patterns]

## Implementation Steps
[Step-by-step guide]

## Benefits
[Why implement this]

## Testing
[Test examples]

## Acceptance Criteria
[Checklist for completion]
```

### Step-by-Step Process

1. **Select an Enhancement**
   - Start with Phase 1 (Core Infrastructure)
   - Read the entire enhancement document

2. **Study the Reference**
   - Review kidney-genetics-db implementation
   - Understand the patterns and architecture

3. **Create a Branch**
   ```bash
   git checkout -b enhancement/001-unified-logger
   ```

4. **Follow Implementation Steps**
   - Each enhancement has numbered steps
   - Test incrementally as you build

5. **Verify Acceptance Criteria**
   - Check off each criterion as completed
   - All must be ✅ before PR

6. **Update CLAUDE.md**
   - Add DRY/KISS guidelines for new features
   - Document usage patterns

7. **Create Pull Request**
   - Reference the enhancement document
   - Include before/after examples

## Design Principles

All enhancements follow these principles:

### 1. DRY (Don't Repeat Yourself)
- **UnifiedLogger**: Single logging interface, no scattered `logging.getLogger()`
- **CacheService**: One cache implementation, used everywhere
- **RetryUtils**: No custom retry loops, use `@retry_with_backoff`

### 2. KISS (Keep It Simple, Stupid)
- **Configuration over code**: YAML files, not hardcoded values
- **Composition over complexity**: Small, reusable utilities
- **PostgreSQL features**: Use JSONB, views instead of complex app logic

### 3. SOLID Principles
- **Single Responsibility**: Each class has one job (Logger logs, Cache caches)
- **Open/Closed**: Extend via configuration (scoring engines, field types)
- **Dependency Inversion**: Inject dependencies (cache_service, db_session)

### 4. Modularization
- **Layered Architecture**: API → Business Logic → Core Utilities → Data Access
- **Base Classes**: Inherit from base patterns (BaseAnnotationSource equivalent)
- **Namespaces**: Logical grouping (cache namespaces, log contexts)

## Production Metrics (kidney-genetics-db)

These enhancements are backed by real production data:

### UnifiedLogger
- **Overhead**: <10ms per log entry
- **Request Correlation**: 100% (every log tagged with request_id)
- **Database Logging**: Async, non-blocking

### CacheService
- **L1 Cache**: <10ms response time
- **L2 Cache**: ~50ms response time (PostgreSQL)
- **Hit Rate**: 75-95% (proven in production)
- **Coverage**: 95%+ annotation coverage (retry logic fixed gaps)

### RetryUtils
- **Success Rate**: 95%+ for transient failures
- **Circuit Breaker**: <0.1% error rate after implementation
- **Rate Limit Handling**: Automatic Retry-After header parsing

### WebSocket Progress
- **Stability**: 100% uptime during 30-minute pipeline runs
- **Latency**: <100ms update propagation
- **No Polling**: Event-driven, reduces API load by 90%

## References

### kidney-genetics-db Project
- **Repository**: https://github.com/halbritter-lab/kidney-genetics-db
- **Status**: Production-ready Alpha (v0.1.0)
- **Metrics**: 571+ genes, 9 data sources, <10ms cached response times

### Key Files Studied
- `backend/app/core/logging/` (533 lines unified_logger.py)
- `backend/app/core/cache_service.py` (1,019 lines)
- `backend/app/core/retry_utils.py` (409 lines)
- `backend/app/core/progress_tracker.py` (453 lines)
- `backend/app/core/datasource_config.py` (267 lines YAML config)
- `Makefile` (638 lines, 50+ commands)

### Documentation
- [kidney-genetics-db CLAUDE.md](https://github.com/halbritter-lab/kidney-genetics-db/blob/main/CLAUDE.md) - Comprehensive development guidelines
- [Architecture docs](https://github.com/halbritter-lab/kidney-genetics-db/tree/main/docs/architecture)
- [Implementation notes](https://github.com/halbritter-lab/kidney-genetics-db/tree/main/docs/implementation-notes)

## Questions or Issues?

- **General Questions**: Check the individual enhancement documents
- **Implementation Help**: Reference kidney-genetics-db implementation
- **Design Decisions**: Follow DRY, KISS, SOLID, modularization principles
- **Testing Guidance**: Each enhancement includes test examples

## Contributing

When implementing these enhancements:

1. ✅ Follow the implementation steps exactly
2. ✅ Reference kidney-genetics-db patterns
3. ✅ Write tests before marking as complete
4. ✅ Update CLAUDE.md with DRY guidelines
5. ✅ Document all configuration options
6. ✅ Verify acceptance criteria checklist

## License

These enhancement proposals are part of the Gene Curator project and follow the same license as the main repository.

---

**Last Updated**: 2025-01-12
**Source Analysis**: kidney-genetics-db v0.1.0-alpha
**Prepared By**: Claude Code (Anthropic)
