# Gene Curator - Enhancement Issues

This directory contains detailed enhancement proposals **tailored specifically for Gene Curator's interactive curation workflow**. After critical review, these have been refined to align with Gene Curator's actual needs (not kidney-genetics-db's high-throughput pipeline needs).

## ⚠️ Important: Scope-Specific Enhancements

These enhancements are designed for:
- ✅ **Interactive manual curation** (5-10 min/curation)
- ✅ **~20 authenticated curators** (not thousands of public users)
- ✅ **Write-heavy workflows** (creating unique records, not reading cached data)
- ✅ **Schema-agnostic design** (supporting any methodology through configuration)

## Enhancement Index

### ✅ Approved for Implementation

| ID | Enhancement | Priority | Effort | Value |
|----|-------------|----------|--------|-------|
| [003](003-retry-utils-exponential-backoff.md) | RetryUtils with Backoff | Medium | 3-4h | ✅ External API calls (HGNC) |
| [004](004-expanded-makefile-workflow.md) | Expanded Makefile | Medium | 2-3h | ✅ Developer productivity |
| [001](001-simple-structured-logging.md) | Simple Structured Logging | High | 2-3h | ✅ Request correlation (simplified from 533→100 lines) |
| [006](006-simple-api-configuration.md) | Simple API Configuration | Medium | 1-2h | ✅ Deployment flexibility (simplified from 267→150 lines) |
| [008](008-draft-autosave-frontend.md) | Draft Auto-Save | High | 4-6h | ✅ **Core curation feature** |
| [009](009-dynamic-form-generation.md) | Dynamic Form Generation | High | 8-10h | ✅ **Core product differentiator** |
| [010](010-review-workflow-4eyes.md) | 4-Eyes Review Workflow | High | 4-6h | ✅ **Regulatory compliance** |

**Total Effort**: 24-33 hours

### 🔴 Deferred (See [`deferred/`](deferred/) folder)

| ID | Enhancement | Reason for Deferral |
|----|-------------|---------------------|
| 002 | CacheService L1/L2 | Write-heavy curation ≠ read-heavy API. Use simple memoization instead. |
| 005 | Real-Time Progress | No 30-minute batch operations exist. Defer until confirmed need. |
| 007 | View Management | <5 views don't need topological sort. Manually order in SQL. |

**Estimated Savings**: 15-20 hours

---

## Implementation Strategy

### Phase 1: Core Curation Features (16-22 hours) 🎯

**Priority**: Build what Gene Curator actually needs - features that improve curator workflows.

1. **[008 - Draft Auto-Save](008-draft-autosave-frontend.md)** (4-6h)
   - Auto-save every 30s + debounced on input
   - Resume incomplete curations
   - Prevent data loss from browser crashes
   - **Value**: Prevents curator frustration

2. **[009 - Dynamic Form Generation](009-dynamic-form-generation.md)** (8-10h)
   - Render forms from schema definitions
   - 12+ field types (text, evidence_table, select, etc.)
   - **Value**: Core product differentiator (schema-agnostic design)

3. **[010 - 4-Eyes Review Workflow](010-review-workflow-4eyes.md)** (4-6h)
   - Independent peer review (mandatory)
   - Review queue and approval interface
   - **Value**: Regulatory compliance for clinical curation

**Why Start Here?**
- These are **actual curation features** that curators interact with daily
- Without these, Gene Curator cannot fulfill its core purpose
- Backend is already ready, only frontend implementation needed

### Phase 2: Infrastructure Basics (8-12 hours)

**Priority**: Simple, practical infrastructure improvements.

4. **[003 - RetryUtils](003-retry-utils-exponential-backoff.md)** (3-4h)
   - Exponential backoff for HGNC lookups
   - 95%+ success rate for transient failures
   - **Value**: Reliable external API integration

5. **[004 - Expanded Makefile](004-expanded-makefile-workflow.md)** (2-3h)
   - Hybrid development mode (DB in Docker, local API/Frontend)
   - `make status` with real-time statistics
   - **Value**: Instant developer productivity boost

6. **[001 - Simple Structured Logging](001-simple-structured-logging.md)** (2-3h)
   - Console-based structured logging (~100 lines, not 533)
   - Request correlation IDs
   - **Value**: Better debugging, no database overhead

7. **[006 - Simple API Configuration](006-simple-api-configuration.md)** (1-2h)
   - YAML for CORS, rate limits, timeouts (~150 lines, not 267)
   - **Value**: Deployment flexibility

**Why Second?**
- These support development and operations, not core functionality
- Simplified versions (not kidney-genetics-db's full systems)
- Can be implemented incrementally

---

## What We Removed (And Why)

### 🔴 Removed: Complex Infrastructure Not Needed

**CacheService L1/L2** (1,019 lines, 6-8h)
- **Reason**: Optimized for 95% cache hit rates in read-heavy public APIs
- **Reality**: Gene Curator is write-heavy (creating unique curation records)
- **Alternative**: Use simple `@lru_cache` for schemas/scopes (~20 lines)

**Real-Time Progress Tracking** (453 lines, 6-8h)
- **Reason**: Built for 30-minute pipeline runs processing 571 genes
- **Reality**: Gene Curator has interactive workflows (5-10 min/curation, user is watching)
- **Alternative**: Defer until confirmed need for bulk operations

**View Management with Topological Sort** (300 lines, 3-4h)
- **Reason**: Manages complex view hierarchies in data aggregation pipelines
- **Reality**: Gene Curator likely has <5 simple views
- **Alternative**: Manually order views in SQL until complexity justifies automation

### ⚠️ Simplified: Right-Sized for Gene Curator

**Unified Logger**: 533 lines → 100 lines
- Removed: Database log persistence (20 curators don't need PostgreSQL logging)
- Removed: Performance decorators (curator time is bottleneck, not API latency)
- Kept: Structured logging with request correlation

**YAML Configuration**: 267 lines → 150 lines
- Removed: Workflow/schema configuration (duplicates schema repository)
- Removed: Complex pydantic-settings integration
- Kept: API-level configuration (CORS, rate limits, timeouts)

---

## Key Design Principles

### 1. DRY (Don't Repeat Yourself)
- **Structured Logging**: Single `get_logger()` interface, no scattered logging
- **RetryUtils**: `@retry_with_backoff` decorator, no custom retry loops
- **Dynamic Forms**: One set of field components, reused for all schemas

### 2. KISS (Keep It Simple, Stupid)
- **Console logging** (not database persistence) for 20 users
- **Simple memoization** (not L1/L2 cache) for rarely-changing data
- **Manual view ordering** (not topological sort) for <5 views
- **API-level YAML only** (not duplicating schema repository)

### 3. SOLID Principles
- **Single Responsibility**: Each component has one clear purpose
- **Open/Closed**: Extend via schema configuration, not code changes
- **Dependency Inversion**: Inject services (db_session, api_config)

### 4. Modularization
- **Layered Architecture**: API → Services → Core → Data Access
- **Reusable Components**: Field types, auto-save, review workflow
- **Configuration-Driven**: Schemas define behavior, not hardcoded logic

---

## ROI Analysis

| Approach | Time | Outcome |
|----------|------|---------|
| **Original Plan** | 28-36h | +3,500 lines infrastructure, optimized for wrong use case |
| **Revised Plan** | 24-33h | Draft auto-save + dynamic forms + review workflow |
| **Savings** | 15-20h deferred | Focus on actual curation features, not premature optimization |

**Value Delivered**:
- ✅ **3 core curation features** curators use daily
- ✅ **4 practical infrastructure improvements** (retry, makefile, logging, config)
- ✅ **Right-sized for Gene Curator** (not kidney-genetics-db)

---

## How to Use These Issues

### Step-by-Step Process

1. **Select an Enhancement**
   - Start with Phase 1 (Core Curation Features)
   - Read the entire enhancement document

2. **Create a Branch**
   ```bash
   git checkout -b enhancement/008-draft-autosave
   ```

3. **Follow Implementation Steps**
   - Each enhancement has numbered steps
   - Test incrementally as you build

4. **Verify Acceptance Criteria**
   - Check off each criterion as completed
   - All must be ✅ before PR

5. **Update CLAUDE.md**
   - Add usage patterns for new features
   - Document any new conventions

6. **Create Pull Request**
   - Reference the enhancement document
   - Include screenshots/videos for UI features

---

## Production Lessons from kidney-genetics-db

These enhancements **reference** battle-tested patterns from kidney-genetics-db but are **adapted** for Gene Curator's use case:

### What We Learned (And Applied Selectively)

✅ **Keep**:
- RetryUtils pattern (external APIs need reliability)
- Makefile workflow (universally useful)
- Structured logging pattern (request correlation is good)
- Dynamic forms (core to schema-agnostic design)

⚠️ **Simplify**:
- Logging: Console-only (no database persistence)
- Configuration: API-level only (no duplicating schema repository)

🔴 **Skip**:
- L1/L2 caching (wrong for write-heavy workflows)
- WebSocket progress (no long-running batch operations)
- Complex view management (not enough views to justify)

### Production Metrics (kidney-genetics-db Context)

These metrics are from kidney-genetics-db's **high-throughput pipeline** use case:
- **Cache hit rates**: 75-95% (public read-heavy API)
- **Event loop blocking**: <1ms (optimizing high-throughput operations)
- **WebSocket stability**: 100% (30-minute pipeline runs)

**Gene Curator's metrics will differ** because it's an interactive curation tool, not a data aggregation pipeline.

---

## References

### kidney-genetics-db Project
- **Repository**: https://github.com/halbritter-lab/kidney-genetics-db
- **Status**: Production-ready Alpha (v0.1.0)
- **Use Case**: Automated data aggregation from 9 sources (571 genes)

### Gene Curator Project
- **Architecture**: Schema-agnostic curation platform
- **Use Case**: Interactive manual curation with 4-eyes review
- **Users**: ~20 authenticated curators (not thousands)

### Key Insight
**kidney-genetics-db and Gene Curator solve different problems.** Infrastructure that's essential for high-throughput data aggregation is over-engineering for interactive curation workflows.

---

## Questions or Issues?

- **General Questions**: Check the individual enhancement documents
- **Implementation Help**: Follow numbered implementation steps
- **Design Decisions**: Always ask "Does Gene Curator actually need this?"
- **Testing Guidance**: Each enhancement includes test examples
- **GitHub Issues**: See [GITHUB_ISSUES_COMPARISON.md](GITHUB_ISSUES_COMPARISON.md) for detailed comparison with existing issues

---

## Related Documentation

- **[GITHUB_ISSUES_COMPARISON.md](GITHUB_ISSUES_COMPARISON.md)**: Detailed comparison with 29 GitHub issues
- **[Curations Implementation Plan](../../CURATIONS_IMPLEMENTATION_PLAN_v2.1.md)**: Current critical blocker
- **[Enhancements Overview](../README.md)**: Main enhancement tracking status

### Archived Documents

The following documents have been archived to `plan/archive/2026-01-12/`:
- `ACTION_PLAN.md` - Superseded by curations plan
- `APPROVED_ENHANCEMENTS.md` - Consolidated into enhancements README

---

**Last Updated**: 2026-01-12
**Review Status**: ✅ Scope-adjusted for Gene Curator's actual needs + Compared with GitHub issues
**Prepared By**: Claude Code (Anthropic)
