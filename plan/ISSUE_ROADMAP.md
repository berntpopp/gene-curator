# Gene Curator - Open Issues Roadmap

**Generated**: 2025-10-13
**Total Open Issues**: 23 (4 completed, 3 new created from TODO analysis)
**Analysis Basis**: v2.0.0 architecture, implementation status, milestone alignment

---

## Executive Summary

**Total Estimated Effort**: 183-254 hours (4.5-6.5 months with 1 FTE)
**Recommended Timeline**: 3 phases over 3-4 months with 2 developers
**Completed Issues**:
- #34 (Feedback System - GitHub-based implementation)
- #39 (Disclaimer Popup - phentrieve-inspired implementation)
- #42 (SEO Metadata - Comprehensive structured data & OG tags)
- #109 (Transform TODOs - 1 bug fixed, 3 tracking issues created)

**New Issues Created** (from TODO analysis #109):
- #118 (Workflow Management Detail/Edit Views - Low priority, UX enhancement)
- #119 (Gene Assignment Edit/Reassign Dialogs - Medium priority, v0.3.0)
- #120 (Schema Read-Only Detail View - Low priority, UX enhancement)

### Key Findings
- **10 issues** are critical for v0.3.0 curation readiness
- **Backend infrastructure** is 90% complete (schema validator, scoring engines, workflow)
- **Frontend gaps** are the primary bottleneck (dynamic forms, external API integration)
- **External API dependencies** required: OMIM, ClinGen, MONDO, Ensembl

---

## Priority Matrix

### Phase 1: Curation Readiness (8-10 weeks) 🔴 CRITICAL
*Target: v0.3.0 production launch*

| Issue | Title | Priority | Complexity | Effort | Status |
|-------|-------|----------|------------|--------|--------|
| #61 | Pre-curation enhancements | 9.5 | Medium | 8-12h | 60% complete |
| #62 | Curation enhancements | 9.5 | High | 12-16h | Backend ready |
| #75 | Search functionality | 8.5 | Medium | 10-12h | Not implemented |
| #19 | Curation modal enhancements | 8.5 | High | 16-20h | Needs specialized UI |
| #87 | Prevent precuration deletion | 8.0 | Low | 3-4h | DB ready, needs logic |
| #77 | Prefill logic | 8.0 | Low-Med | 4-6h | Backend 100% ready |
| #105 | ClinGen import | 8.0 | High | 16-20h | Infrastructure ready |
| #119 | Gene assignment edit/reassign | 7.5 | Medium | 6-8h | Backend ready, UI needed |
| #54 | OMIM selector | 7.5 | Medium | 8-10h | DB ready, needs API |
| #53 | MONDO selector | 7.5 | Medium | 8-10h | DB ready, needs API |
| #102 | Validate clinical groups | 7.5 | Medium | 6-8h | Validation needed |

**Total**: 98-136 hours (~2.5-3.5 months, 1 developer)

---

### Phase 2: Performance & UX (4-6 weeks) 🟡 HIGH
*Target: Production optimization*

| Issue | Title | Priority | Complexity | Effort | Status |
|-------|-------|----------|------------|--------|--------|
| #67 | Pagination with counter | 7.0 | Low | 4-6h | Backend ready |
| #95 | Advanced filters | 7.0 | Low-Med | 6-8h | Backend supports |
| #104 | Detailed instructions | 7.0 | Low | 4-6h | FAQ exists |
| #86 | Backup system | 7.0 | Med-High | 8-12h | Manual backups exist |
| #66 | Lazy loading optimization | 6.5 | Medium | 6-8h | Backend excellent |
| #115 | Transcript selector | 6.5 | Medium | 6-8h | DB ready |
| #118 | Workflow management views | 6.0 | Medium | 8-10h | Backend ready, UI needed |
| #30 | Customizable dashboard | 6.0 | Medium | 8-12h | Basic dashboard exists |
| #116 | Multi-user approval | 6.0 | Med-High | 12-16h | 4-eyes exists |
| #120 | Schema read-only view | 5.5 | Low | 2-3h | Backend ready, modal needed |

**Total**: 64-89 hours (~1.5-2.5 months, 1 developer)

---

### Phase 3: Generalization & Polish (3-4 weeks) 🟢 MEDIUM
*Target: Broader adoption readiness*

| Issue | Title | Priority | Complexity | Effort | Status |
|-------|-------|----------|------------|--------|--------|
| #55 | Initial setup wizard | 5.5 | High | 12-16h | Not implemented |
| #46 | File uploads (JSON/CSV) | 5.0 | Medium | 8-10h | Bulk API exists |
| ~~#109~~ | ~~Transform TODOs~~ | ~~4.0~~ | ~~Low~~ | ~~2-4h~~ | ✅ **Complete** (1 bug fixed, 3 issues created) |
| ~~#39~~ | ~~Disclaimer popup~~ | ~~4.0~~ | ~~Low~~ | ~~2-3h~~ | ✅ **Complete** (phentrieve-inspired) |
| ~~#34~~ | ~~Feedback system~~ | ~~4.0~~ | ~~Medium~~ | ~~6-8h~~ | ✅ **Complete** (GitHub-based) |
| ~~#42~~ | ~~SEO metadata~~ | ~~3.0~~ | ~~Low~~ | ~~3-4h~~ | ✅ **Complete** (comprehensive implementation) |

**Total**: 20-26 hours (~2.5-3.5 weeks, 1 developer)

---

## Category Breakdown

### 🎯 Core Curation Workflow (4 issues)
Critical path for production readiness

- **#61** Pre-curation card - Validation for lump/split decisions
- **#62** Curation card - External APIs (MONDO, OMIM, PubMed)
- **#19** Curation modal - Evidence table UI
- **#77** Prefill logic - Frontend reads schema defaults

**Key Dependency**: Dynamic form generation (Enhancement #009)

---

### 🔗 External API Integration (5 issues)
Requires API keys and service integration

- **#105** ClinGen import - API integration + schema mapping
- **#54** OMIM selector - API key + autocomplete
- **#53** MONDO selector - OLS API + autocomplete
- **#115** Transcript selector - Ensembl API
- **#62** (overlap) - PubMed E-utilities

**Required API Keys**:
- OMIM: https://www.omim.org/api (free for non-commercial)
- ClinGen: https://clinicalgenome.org/tools/web-api/ (public)
- MONDO: https://www.ebi.ac.uk/ols/api/ (public)
- Ensembl: https://rest.ensembl.org (public, no key)

---

### 🔍 Search & Discovery (2 issues)
Essential UX improvements

- **#75** Global search - PostgreSQL full-text search
- **#95** Advanced filters - Filter chips + UI

**Implementation**: PostgreSQL GIN indexes + Vue filter components

---

### 🛡️ Data Integrity (4 issues)
Production-critical safety

- **#87** Prevent deletion - Soft delete pattern
- **#102** Validate scopes - ClinGen/GenCC/HPO taxonomy
- **#86** Backup system - Automated pg_dump + S3
- **#116** Multi-approval - n-of-m consensus logic

**Risk**: #86 (Backup) is production blocker

---

### ⚡ Performance (2 issues)
Optimization for scale

- **#67** Pagination - Add COUNT queries + caching
- **#66** Lazy loading - Vue route splitting, bundle optimization

**Targets**: LCP <2.5s, API P95 <100ms, Search <200ms

---

### 📖 User Experience (3 issues)
Documentation and guidance

- **#104** Instructions - Tooltips, help modals, FAQ expansion
- **#30** Dashboard - Customizable widgets (vue-grid-layout)
- ~~**#39** Disclaimer - ✅ **Complete** (research use disclaimer with localStorage)~~

---

### 🚀 Generalization (2 issues)
Future-proofing

- **#55** Setup wizard - Multi-step onboarding for new installations
- **#46** File uploads - CSV/JSON parser + bulk import UI

---

### 🔧 Operations (3 issues)
Production readiness

- ~~**#42** SEO - ✅ **Complete** (30+ meta tags, dual JSON-LD schemas, 400+ line docs)~~
- ~~**#34** Feedback - ✅ **Complete** (GitHub issue forms implemented)~~
- ~~**#109** TODOs - ✅ **Complete** (1 bug fixed, 3 tracking issues created: #118, #119, #120)~~

---

## Implementation Dependencies

### Backend (✅ Complete)
- Schema validator (12+ field types)
- Scoring engines (ClinGen SOP v11, GenCC, Qualitative)
- Multi-stage workflow (entry → precuration → curation → review → active)
- JSONB evidence storage (methodology-agnostic)
- Comprehensive API (10 modules, 30+ routes)
- JWT authentication + 5-tier RBAC

### Frontend (⚠️ Gaps)
- ❌ Dynamic form generation (Enhancement #009 pending)
- ❌ Evidence table component (complex data entry)
- ❌ External API autocomplete components
- ❌ Global search bar + results view
- ❌ Advanced filter UI with chips

### External Services (📋 Required)
- OMIM API key (application needed)
- ClinGen API endpoint configuration
- MONDO OLS API integration
- Ensembl REST API client

---

## Risk Assessment

### 🔴 High Risk (Potential Blockers)
1. **OMIM API approval** - May take 2-4 weeks
2. **ClinGen API changes** - Dependency on external service
3. **Backup system** - Production blocker if not implemented
4. **Evidence table complexity** - May require UI/UX expertise

### 🟡 Medium Risk
1. **Dynamic form generation** - Complex but well-scoped
2. **Multi-approval logic** - Requires workflow engine changes
3. **Bundle optimization** - May need Vite expertise

### 🟢 Low Risk
- All other issues have clear implementation paths
- Backend infrastructure is solid
- Database schema supports all features

---

## Milestone Alignment

**v0.3.0 - Curation Readiness** (Current Focus)
- #61, #62, #102, #104, #105 ✅ In milestone

**Performance Optimization**
- #66, #67 ✅ In milestone

**Curation Process Enhancement**
- #95 ✅ In milestone

**Data Integrity and Management**
- #87 ✅ In milestone

**App Functionality Expansion**
- #75, #86 ✅ In milestone

**App Generalization and Distribution**
- #55 ✅ In milestone

**Unassigned (Need Milestones)**
- #116, #115, #109, #77, #54, #53, #46, #30, #19

---

## Recommended Action Plan

### Immediate Actions (Week 1-2)
1. **Apply for OMIM API key** - Lead time required
2. **Implement #87** (Prevent deletion) - Quick win, 3-4h
3. **Implement #77** (Prefill logic) - Backend ready, 4-6h
4. **Start #75** (Search) - Critical UX gap

### Short-Term (Month 1)
1. Complete Phase 1 top 5 issues (#61, #62, #75, #19, #87)
2. Set up external API integrations (#54, #53)
3. Implement backup automation (#86)

### Medium-Term (Months 2-3)
1. Complete Phase 1 remaining issues
2. Launch v0.3.0 with curation readiness
3. Begin Phase 2 (performance + UX)

### Long-Term (Months 4+)
1. Complete Phase 2
2. Implement Phase 3 (generalization)
3. Monitor and optimize production deployment

---

## Success Metrics

### Phase 1 (Curation Readiness)
- ✅ All curators can complete end-to-end workflow
- ✅ External disease databases integrated (OMIM, MONDO)
- ✅ Search functionality operational
- ✅ No data integrity issues

### Phase 2 (Performance)
- ✅ Page load time <2.5s (LCP)
- ✅ API response time <100ms (P95)
- ✅ Search results <200ms
- ✅ Automated backups running

### Phase 3 (Polish)
- ✅ New installation setup <10 minutes
- ✅ User documentation complete
- ✅ ~~Feedback system collecting data~~ **Complete** (GitHub issue forms)

---

## Technical Notes

### Schema-Agnostic Architecture
All implementations must respect flexible schema definitions. No hardcoded field names. Use `field_definitions` from `curation_schemas` table.

### Scope-Based RBAC
Every API route enforces scope-based permissions. Users see only data from their assigned scopes (clinical specialties).

### 4-Eyes Principle
Independent reviewer required before curation activation. `reviews` table tracks approval status.

### Multi-Curation Support
Multiple curations per gene-scope, but only one active. Previous active curations automatically archived.

### External API Caching
Implement 90-day TTL cache for OMIM/MONDO/Ensembl data to reduce API load and improve performance.

---

## Resource Requirements

### Team Composition
- **Optimal**: 2 developers (1 backend + 1 frontend) = 2.5-3 months
- **Minimum**: 1 full-stack developer = 4.5-6 months

### Infrastructure
- PostgreSQL 15+ (already deployed)
- Redis for caching (already deployed)
- S3-compatible storage for backups (TBD)
- External API rate limits to monitor

### Budget Considerations
- OMIM API: Free for non-commercial
- Cloud storage: ~$20/month for backups
- Monitoring tools: Consider Sentry for error tracking

---

**Last Updated**: 2025-10-13
**Next Review**: After Phase 1 completion (target: Q1 2026)