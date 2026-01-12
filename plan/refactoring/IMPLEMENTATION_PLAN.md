# ClinGen SOP v11 Implementation - Master Plan

**Version**: 3.0 Final
**Date**: 2025-10-14
**Status**: Ready for Development
**Timeline**: 17 weeks (4 phases)
**Strategy**: Pragmatic MVP with deferred complexity

---

## 🚀 Quick Start

### For Developers

**1. Choose Your Phase:**
- **Backend (Phase 1)** → Read `database_implementation.md` first
- **Backend (Phase 2)** → Read `api_implementation.md` first
- **Frontend (Phase 3)** → Read `frontend_implementation.md` first

**2. Create Branch:**
```bash
git checkout -b feature/clingen-sop-v11-foundation  # Phase 1
git checkout -b feature/clingen-sop-v11-api         # Phase 2
git checkout -b feature/clingen-sop-v11-frontend    # Phase 3
```

**3. Start Development:**
```bash
make hybrid-up     # PostgreSQL:5454, Redis:6399
make backend       # API: localhost:8051
make frontend      # UI: localhost:5193
```

### Document Structure

- **This file** - Master overview, architecture, timeline
- **database_implementation.md** - Phase 1: Migrations, tables, seed data (43 KB)
- **api_implementation.md** - Phase 2: Services, endpoints, validators (58 KB)
- **frontend_implementation.md** - Phase 3: Stores, components, forms (52 KB)

---

## Executive Summary

Implement complete ClinGen SOP v11 gene-disease validity scoring system with scope-centric multi-institutional support. Fast-track approach defers advanced features (immutable versioning, dynamic forms) to Phase 2 while delivering production-ready tool in 17 weeks.

**What We're Building**:
- ✅ Complete ClinGen SOP v11 scoring engine (genetic + experimental evidence)
- ✅ External validators (HGNC, PubMed, HPO) with caching
- ✅ Scope-based organization with cross-scope aggregation
- ✅ Multi-stage workflow (Entry → Precuration → Curation → Review → Active)
- ✅ Concurrency control and permissions
- ✅ Production-ready audit trail

**What We're Deferring**:
- ⏸️ Full immutable versioning (Phase 2 - use enhanced audit log for MVP)
- ⏸️ Dynamic form generation (Phase 2 - hand-code ClinGen forms for MVP)
- ⏸️ Consensus algorithm (Phase 2 - display all scope classifications for MVP)

---

## Key Architectural Decisions

### 1. Scope-Centric Design (CRITICAL FIX)

**Decision**: Scope is the central organizing principle, not an afterthought.

**Implementation**:
```
Gene → Multiple Scopes → Multiple Curations per Scope
                     ↓
              GeneSummary (aggregates across scopes)
                     ↓
      Public View: Show all public scope curations
```

**Core Principle**: If `scope.is_public == True`, all its curations are viewable by anonymous users, aggregated by gene.

### 2. Evidence Item Extraction

**Decision**: Extract evidence from JSONB array to separate table.

**Before** (problematic):
```python
CurationNew.evidence_data = {
    "genetic_evidence": [...],  # No item IDs, can't update individually
    "experimental_evidence": [...]
}
```

**After** (clean):
```python
EvidenceItem:
    id: UUID
    curation_id: UUID
    evidence_category: str  # "case_level", "segregation", etc.
    evidence_data: JSONB
    computed_score: float
```

### 3. Simplified Audit Trail (MVP)

**Decision**: Enhanced audit log for MVP, defer full immutable versioning.

**Why**: Saves 2 weeks, meets audit requirements for non-clinical-grade MVP.

**Implementation**:
```python
AuditLogNew:
    # Enhanced with detailed change tracking
    change_type: str  # "evidence_added", "score_updated", etc.
    old_values: JSONB
    new_values: JSONB
    change_metadata: JSONB  # User agent, IP, etc.
```

**Phase 2 Migration Path**: Clear upgrade to immutable versioning documented.

### 4. Concurrency Control

**Decision**: Optimistic locking with `lock_version` field.

**Implementation**:
```python
CurationNew:
    lock_version: int  # Increments on each update

# Update logic
if rows_affected == 0:
    raise ConcurrentModificationError("Modified by another user")
```

### 5. Hand-Coded Forms (MVP)

**Decision**: Build ClinGen SOP v11 forms manually, defer dynamic generation.

**Why**: Saves 2 weeks, allows rapid iteration with clinical geneticists.

**Phase 2**: Extract patterns and build schema-driven generator.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  ClinGen     │  │   Scope      │  │  Gene        │      │
│  │  Forms       │  │   Summary    │  │  Summary     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Curation    │  │  Validation  │  │  Gene        │      │
│  │  Endpoints   │  │  Service     │  │  Summary     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Scope           │  │  ClinGen         │                │
│  │  Permission      │  │  Scoring         │                │
│  │  Service         │  │  Engine          │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Curation │  │ Evidence │  │  Gene    │  │Validation│   │
│  │  New     │  │  Item    │  │ Summary  │  │  Cache   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
          │                                    │
          └────────────────┬───────────────────┘
                           ▼
                    PostgreSQL 15+
```

---

## Implementation Timeline: 17 Weeks

### Phase 1: Foundation (Weeks 1-4)
**Goal**: Database schema + core scoring engine ready

**Deliverables**:
- ✅ Database migrations (GeneSummary, EvidenceItem, ValidationCache, lock_version)
- ✅ Enhanced AuditLogNew for detailed tracking
- ✅ ClinGen scoring engine (complete genetic + experimental evidence)
- ✅ LOD score calculator
- ✅ Unit tests for scoring logic

**Milestone**: Scoring engine can process evidence and return accurate scores

**Detailed Plan**: `plan/refactoring/database_implementation.md`

---

### Phase 2: API Layer (Weeks 5-9)
**Goal**: Complete API with validators and permissions

**Deliverables**:
- ✅ External validators (HGNC, PubMed, HPO) with caching
- ✅ ScopePermissionService with complete access control
- ✅ GeneSummaryCRUD with cross-scope aggregation
- ✅ Evidence CRUD (create/update/delete individual items)
- ✅ Concurrency control middleware
- ✅ Enhanced curation endpoints

**Milestone**: API can handle complete curation lifecycle with validation

**Detailed Plan**: `plan/refactoring/api_implementation.md`

---

### Phase 3: Frontend (Weeks 10-14)
**Goal**: User-facing interface for curators

**Deliverables**:
- ✅ Hand-coded ClinGen evidence forms (genetic + experimental)
- ✅ Validation composables (useValidation, ValidatedInput.vue)
- ✅ GeneSummaryView.vue (cross-scope display)
- ✅ ScopeSummaryCard.vue
- ✅ Enhanced curation workflow UI
- ✅ Conflict display (when scopes disagree)

**Milestone**: Clinical geneticists can enter complete ClinGen curations

**Detailed Plan**: `plan/refactoring/frontend_implementation.md`

---

### Phase 4: Testing & Polish (Weeks 15-17)
**Goal**: Production-ready with documentation

**Deliverables**:
- ✅ Unit tests (90%+ coverage on scoring, validators)
- ✅ Integration tests (concurrent updates, cross-scope queries)
- ✅ E2E tests (complete curation workflow)
- ✅ Performance optimization (indexes, caching)
- ✅ User documentation
- ✅ API documentation updates
- ✅ Clinical geneticist review & feedback

**Milestone**: Production deployment ready

---

## Database Schema Changes

**New Tables**:
- `gene_summaries` - Cross-scope aggregation
- `evidence_items` - Individual evidence with metadata
- `validation_cache` - External validator results

**Modified Tables**:
- `curations` - Add `lock_version` field
- `audit_logs` - Enhance with `old_values`, `new_values`, `change_metadata`

**Details**: See `plan/refactoring/database_implementation.md`

---

## API Endpoints (New)

### Evidence Management
```
POST   /api/v1/curations/{curation_id}/evidence          # Add evidence item
PUT    /api/v1/curations/{curation_id}/evidence/{item_id} # Update item
DELETE /api/v1/curations/{curation_id}/evidence/{item_id} # Delete item
GET    /api/v1/curations/{curation_id}/evidence          # List all items
```

### Gene Summaries
```
GET    /api/v1/genes/{gene_id}/summary                   # Public summary
GET    /api/v1/genes/{gene_id}/summary/full              # Authenticated full
GET    /api/v1/genes/{gene_id}/scopes                    # Scopes curating gene
```

### Validation
```
POST   /api/v1/validation/validate                       # Batch validate
POST   /api/v1/validation/hgnc                           # Validate gene symbol
POST   /api/v1/validation/pubmed                         # Validate PMID
POST   /api/v1/validation/hpo                            # Validate HPO term
```

**Details**: See `plan/refactoring/api_implementation.md`

---

## Success Criteria

### Functional Requirements
- [ ] Clinical geneticist can create complete ClinGen SOP v11 curation in < 30 minutes
- [ ] System correctly calculates scores matching ClinGen examples (100% accuracy)
- [ ] Cross-scope gene summary displays all public curations
- [ ] External validators catch 95%+ of invalid gene symbols/PMIDs
- [ ] Concurrent updates handled gracefully with user-friendly error messages
- [ ] Audit trail captures all changes with timestamps and user attribution

### Non-Functional Requirements
- [ ] API response time < 500ms for 95th percentile
- [ ] Frontend loads in < 3 seconds on 3G connection
- [ ] Zero data loss under concurrent access
- [ ] 90%+ test coverage on critical paths
- [ ] Documentation complete for clinical geneticist onboarding

### Clinical Validation
- [ ] 3 clinical geneticists successfully complete test curations
- [ ] Scoring results match manual ClinGen calculations
- [ ] UI terminology matches ClinGen SOP v11 language

---

## Risk Management

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| External API downtime (HGNC, PubMed) | High | Medium | Caching + graceful degradation |
| Scope requirements misunderstood | Low | High | Fixed in this plan (user validated) |
| Performance issues at scale | Medium | Medium | Indexed queries + Phase 2 optimization |
| User adoption (form complexity) | Medium | High | Hand-coded forms + user testing |
| Concurrent update bugs | Medium | High | Optimistic locking + integration tests |

---

## Technical Debt & Phase 2 Roadmap

### Accepted Technical Debt (MVP)
1. **No full immutable versioning** - Using enhanced audit log
   - **Upgrade Path**: Documented migration to immutable pattern
   - **Effort**: 3 weeks in Phase 2

2. **No dynamic form generation** - Hand-coded ClinGen forms
   - **Upgrade Path**: Extract patterns, build schema-driven generator
   - **Effort**: 4 weeks in Phase 2

3. **No consensus algorithm** - Display all scope classifications
   - **Upgrade Path**: Evidence deduplication + voting algorithm
   - **Effort**: 2 weeks in Phase 2

4. **Basic error handling** - External APIs have retries but no circuit breaker
   - **Upgrade Path**: Add circuit breaker pattern
   - **Effort**: 1 week in Phase 2

### Phase 2 Features (Post-MVP)
- Full immutable versioning (3 weeks)
- Dynamic schema-driven forms (4 weeks)
- Consensus algorithm (2 weeks)
- Advanced performance optimization (2 weeks)
- Additional scoring engines (GenCC - 3 weeks)
- Bulk import/export (2 weeks)

**Total Phase 2**: ~16 weeks (can be parallelized)

---

## Development Setup

### Prerequisites
```bash
# Ensure hybrid mode is set up
make hybrid-up     # PostgreSQL:5454, Redis:6399
make backend       # API: localhost:8051
make frontend      # UI: localhost:5193
```

### Branch Strategy
```
feature/clingen-sop-v11-foundation    # Phase 1 (weeks 1-4)
feature/clingen-sop-v11-api           # Phase 2 (weeks 5-9)
feature/clingen-sop-v11-frontend      # Phase 3 (weeks 10-14)
feature/clingen-sop-v11-testing       # Phase 4 (weeks 15-17)
```

### Daily Workflow
```bash
# Morning: Pull latest, check status
git pull origin feature/clingen-sop-v11-foundation
make status

# Development: Run tests frequently
make test                # Backend tests
make test-frontend       # Frontend tests (when available)

# Before commit: Quality checks
make lint lint-frontend format-all
```

---

## Team Composition (Recommended)

### Phase 1-2 (Backend Heavy)
- 2 Senior Backend Developers (Python, FastAPI, SQLAlchemy)
- 1 Database Engineer (PostgreSQL, migrations)
- 1 Clinical Geneticist (domain validation, part-time)

### Phase 3 (Frontend Heavy)
- 2 Frontend Developers (Vue 3, TypeScript, Vuetify)
- 1 Backend Developer (API support)
- 1 Clinical Geneticist (UI review, part-time)

### Phase 4 (QA)
- 1 QA Engineer (testing, automation)
- 1 Technical Writer (documentation)
- 2-3 Clinical Geneticists (user acceptance testing)

---

## Communication & Tracking

### Daily Standup (15 min)
- What I completed yesterday
- What I'm working on today
- Any blockers

### Weekly Review (Friday, 1 hour)
- Demo completed features
- Review metrics (test coverage, performance)
- Adjust timeline if needed

### Phase Gate Reviews
- End of Phase 1: Scoring engine demo
- End of Phase 2: API integration demo
- End of Phase 3: Full workflow demo
- End of Phase 4: Go/No-Go for production

---

## Detailed Implementation Plans

This master plan provides the overview and strategy. For detailed implementation specifications, see:

1. **Database**: `plan/refactoring/database_implementation.md`
   - Complete schema definitions
   - Migration scripts
   - Indexes and constraints
   - Seed data requirements

2. **API**: `plan/refactoring/api_implementation.md`
   - Complete endpoint specifications
   - Service layer architecture
   - Request/response schemas
   - Error handling patterns

3. **Frontend**: `plan/refactoring/frontend_implementation.md`
   - Component hierarchy
   - Store patterns
   - Form specifications
   - UI/UX guidelines

---

## Appendix: Key References

### ClinGen Documentation
- **SOP v11**: `plan/scripts/clingen_documents/markdown/gene_disease_validity_sop_v11.md`

### Code References
- **Current Models**: `backend/app/models/models.py`
- **Current Scoring**: `backend/app/scoring/clingen.py`
- **Schema Endpoint**: `backend/app/api/v1/endpoints/schemas.py`

### External APIs
- **HGNC REST API**: https://rest.genenames.org/
- **NCBI E-utilities**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **OLS API**: https://www.ebi.ac.uk/ols/api

---

## FAQ

**Q: Where do I start?**
**A**: Read this file first for overview, then read your phase-specific document (database/api/frontend).

**Q: What if I find issues with the plan?**
**A**: Update the relevant document and notify team. Plans are living documents.

**Q: Should I follow the plan exactly?**
**A**: Use your judgment. Document significant deviations with rationale.

**Q: When do we implement dynamic forms?**
**A**: Phase 2 (post-MVP). MVP uses hand-coded forms for speed.

**Q: When do we implement immutable versioning?**
**A**: Phase 2 (post-MVP). MVP uses enhanced audit log which meets audit requirements.

**Q: Why 17 weeks instead of the original 19?**
**A**: We deferred 2 complex features (immutable versioning, dynamic forms) to Phase 2 while actually improving the architecture (extracted evidence items, added concurrency control).

---

## Version History

- **v1.0** (2025-10-14): Initial plan with 14-week timeline
- **v2.0** (2025-10-14): Added validators and immutable versioning (19 weeks)
- **v3.0** (2025-10-14): **FINAL** - Pragmatic MVP, fixed scope-centric design, 17 weeks

---

**Status**: ✅ Ready for development - awaiting resource allocation

**Next Action**: Create Phase 1 task breakdown and begin database implementation

**Approval Required**: Product Owner sign-off on 17-week timeline and Phase 2 technical debt
