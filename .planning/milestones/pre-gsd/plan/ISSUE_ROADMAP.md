# Gene Curator - Issue Roadmap

**Last Updated**: 2026-01-12
**Total Open Issues**: 23
**Recent Milestone**: PR #126 merged (scope-centric refactor)

---

## Executive Summary

The major refactor (PR #126) has been merged, transforming Gene Curator from MongoDB/Firebase to PostgreSQL with a schema-agnostic, scope-based architecture. Issues have been reorganized into version-based milestones with a comprehensive label system.

### Architecture Status
- ✅ **Backend**: Complete (schema validator, scoring engines, workflow, API)
- ✅ **Database**: Complete (PostgreSQL, RLS, audit trails)
- ⚠️ **Frontend**: Partial (stores complete, dynamic forms pending)

### Key Completed Items
- 10+ issues closed by PR #126 merge
- CI/CD pipeline with GitHub Actions
- Comprehensive test suite (164 frontend, 50+ backend)
- Schema-agnostic curation system

---

## Milestone Structure

| Milestone | Issues | Priority | Target |
|-----------|--------|----------|--------|
| [v0.4.0 - Core Curation Features](https://github.com/berntpopp/gene-curator/milestone/11) | 6 | 🔴 HIGH | Phase 1 |
| [v0.5.0 - Infrastructure & Scalability](https://github.com/berntpopp/gene-curator/milestone/12) | 5 | 🟠 HIGH | Phase 2 |
| [v1.0.0 - Production Ready](https://github.com/berntpopp/gene-curator/milestone/13) | 6 | 🟡 MEDIUM | Phase 3 |
| [Backlog](https://github.com/berntpopp/gene-curator/milestone/14) | 6 | 🟢 LOW | Future |

---

## v0.4.0 - Core Curation Features

**Focus**: Complete core curation workflow with dynamic forms and review system.
**Effort**: 16-22 hours
**Dependencies**: Enhancement #008, #009, #010

| Issue | Title | Priority | Status | Effort |
|-------|-------|----------|--------|--------|
| [#116](https://github.com/berntpopp/gene-curator/issues/116) | Multi-user approval | HIGH | 70% | 4-6h |
| [#62](https://github.com/berntpopp/gene-curator/issues/62) | Enhance Curation Card | HIGH | 60% | 6-8h |
| [#61](https://github.com/berntpopp/gene-curator/issues/61) | Enhance Pre-Curation Card | HIGH | 60% | 6-8h |
| [#77](https://github.com/berntpopp/gene-curator/issues/77) | Implement Prefill Logic | MEDIUM | 40% | 3-4h |
| [#119](https://github.com/berntpopp/gene-curator/issues/119) | Gene Assignment Edit/Reassign | MEDIUM | Pending | 6-8h |
| [#118](https://github.com/berntpopp/gene-curator/issues/118) | Workflow Management Views | MEDIUM | Pending | 8-10h |

### Related Enhancements
| Enhancement | Description | Remaining | Closes |
|-------------|-------------|-----------|--------|
| #008 | Draft Auto-Save | 3-4h | - |
| #009 | Dynamic Form Generation | 6-8h | #62, #61, #77 |
| #010 | 4-Eyes Review Workflow | 4-6h | #116 |

---

## v0.5.0 - Infrastructure & Scalability

**Focus**: Production-ready performance and data management.
**Effort**: 22-30 hours
**Dependencies**: None (can be parallelized)

| Issue | Title | Priority | Status | Effort |
|-------|-------|----------|--------|--------|
| [#67](https://github.com/berntpopp/gene-curator/issues/67) | Pagination in Stores | HIGH | Pending | 4-6h |
| [#75](https://github.com/berntpopp/gene-curator/issues/75) | Search Functionality | HIGH | Pending | 3-4h |
| [#86](https://github.com/berntpopp/gene-curator/issues/86) | Backup System | HIGH | Pending | 6-8h |
| [#66](https://github.com/berntpopp/gene-curator/issues/66) | Lazy Loading/Performance | MEDIUM | Pending | 6-8h |
| [#95](https://github.com/berntpopp/gene-curator/issues/95) | Advanced Filters | MEDIUM | Pending | 3-4h |

### Implementation Notes
- **#67**: Cursor-based pagination, COUNT endpoints, UI controls
- **#75**: PostgreSQL full-text search, global search bar, typeahead
- **#86**: pg_dump automation, S3 storage, restore UI

---

## v1.0.0 - Production Ready

**Focus**: Complete feature set for first production release.
**Effort**: 18-26 hours

| Issue | Title | Priority | Status | Effort |
|-------|-------|----------|--------|--------|
| [#104](https://github.com/berntpopp/gene-curator/issues/104) | Add detailed instructions | MEDIUM | Pending | 2-3h |
| [#102](https://github.com/berntpopp/gene-curator/issues/102) | Check Clinical Groups | MEDIUM | Pending | 2-3h |
| [#105](https://github.com/berntpopp/gene-curator/issues/105) | ClinGen Classification Import | MEDIUM | Pending | 4-6h |
| [#87](https://github.com/berntpopp/gene-curator/issues/87) | Prevent Deletion of Precuration | MEDIUM | Pending | 1-2h |
| [#53](https://github.com/berntpopp/gene-curator/issues/53) | MONDO Disease Selector | LOW | Pending | 4-6h |
| [#54](https://github.com/berntpopp/gene-curator/issues/54) | OMIM Disease Selector | LOW | Pending | 4-6h |

### External API Dependencies
| API | Status | Key Required |
|-----|--------|--------------|
| MONDO (OLS) | Ready | No |
| OMIM | Needs setup | Yes (free non-commercial) |
| ClinGen | Ready | No |
| Ensembl | Ready | No |

---

## Backlog

**Focus**: Future considerations, nice-to-have features.

| Issue | Title | Priority | Reason |
|-------|-------|----------|--------|
| [#115](https://github.com/berntpopp/gene-curator/issues/115) | Add transcript to curation | LOW | Domain-specific |
| [#109](https://github.com/berntpopp/gene-curator/issues/109) | Transform TODOs into Issues | LOW | Documentation |
| [#120](https://github.com/berntpopp/gene-curator/issues/120) | Schema Read-Only Detail View | LOW | UI enhancement |
| [#30](https://github.com/berntpopp/gene-curator/issues/30) | Customizable Dashboard | LOW | Future feature |
| [#46](https://github.com/berntpopp/gene-curator/issues/46) | JSON/CSV File Uploads | LOW | Future feature |
| [#19](https://github.com/berntpopp/gene-curator/issues/19) | Curation Modal Enhancement | LOW | Superseded by #62 |

---

## Recently Closed Issues

Issues resolved by PR #126 merge:

| Issue | Title | Resolution |
|-------|-------|------------|
| #113 | Use standard JSON schema | Schema validator with 12+ field types |
| #108 | Curation Entity Not Initialized | Proper initialization |
| #107 | Make Curation Tab Visible | Navigation visibility |
| #106 | Make "Groups" mandatory | Schema-driven required fields |
| #101 | Create Log File for User Roles | Audit trail in database |
| #100 | Add User Deletion for Admin | User management endpoints |
| #99 | Update Stores for Nested Data | Pinia stores updated |
| #96 | Integration of Precuration and Gene | Unified data model |
| #110 | Replace Console Logs with Snackbar | Notification system |
| #114 | Broken link in FAQ | Fixed |

---

## Label System

### Priority Labels
| Label | Description | Color |
|-------|-------------|-------|
| `priority: critical` | P0 - Blocker | 🔴 Red |
| `priority: high` | P1 - Important | 🟠 Orange |
| `priority: medium` | P2 - Normal | 🟡 Yellow |
| `priority: low` | P3 - Nice to have | 🟢 Green |

### Type Labels
| Label | Description |
|-------|-------------|
| `type: feature` | New feature implementation |
| `type: infrastructure` | Backend/tooling |
| `type: ui/ux` | User interface |
| `type: performance` | Optimization |

### Scope Labels
| Label | Description |
|-------|-------------|
| `scope: frontend` | Vue.js changes |
| `scope: backend` | FastAPI changes |
| `scope: database` | Database changes |

### Status Labels
| Label | Description |
|-------|-------------|
| `status: blocked` | Blocked by another issue |
| `status: in-progress` | Currently being worked on |
| `status: needs-review` | Needs design review |

---

## Implementation Timeline

### Phase 1: Core Curation (v0.4.0)
**Duration**: 2-3 weeks
**Focus**: Dynamic forms, review workflow, draft auto-save

```
Week 1-2: Enhancement #009 (Dynamic Forms)
  → Closes #62, #61, #77
Week 2-3: Enhancement #010 (Review Workflow)
  → Closes #116
Week 3: Enhancement #008 (Draft Auto-Save)
  → UX polish, #119, #118
```

### Phase 2: Infrastructure (v0.5.0)
**Duration**: 3-4 weeks
**Focus**: Pagination, search, backup, performance

```
Week 1: #67 (Pagination) + #75 (Search)
Week 2: #86 (Backup System)
Week 3-4: #66 (Performance) + #95 (Filters)
```

### Phase 3: Production Ready (v1.0.0)
**Duration**: 2-3 weeks
**Focus**: Documentation, external integrations, polish

```
Week 1: #104 (Instructions) + #102 (Clinical Groups)
Week 2: #105 (ClinGen Import) + #87 (Deletion Prevention)
Week 3: #53 (MONDO) + #54 (OMIM)
```

---

## Success Metrics

### v0.4.0 (Core Curation)
- [ ] Curators can complete end-to-end workflow
- [ ] Forms render dynamically from schema
- [ ] 4-eyes review process functional
- [ ] Drafts auto-saved every 30s

### v0.5.0 (Infrastructure)
- [ ] Page load time <2.5s (LCP)
- [ ] API response time <100ms (P95)
- [ ] Search results <200ms
- [ ] Automated backups running daily

### v1.0.0 (Production)
- [ ] External disease databases integrated
- [ ] User documentation complete
- [ ] All P1/P2 issues resolved
- [ ] Zero critical bugs

---

## Risk Assessment

### 🔴 High Risk
1. **Dynamic form complexity** - May require UI/UX iteration
2. **OMIM API approval** - 2-4 week lead time

### 🟡 Medium Risk
1. **Backup automation** - Requires infrastructure setup
2. **Search performance** - May need index tuning

### 🟢 Low Risk
- All other issues have clear implementation paths
- Backend infrastructure is solid
- Comprehensive test coverage

---

## Quick Reference

### Commands
```bash
# View issues by milestone
gh issue list --milestone "v0.4.0 - Core Curation Features"

# View high priority issues
gh issue list --label "priority: high"

# View frontend scope issues
gh issue list --label "scope: frontend"
```

### Links
- [All Milestones](https://github.com/berntpopp/gene-curator/milestones)
- [Open Issues](https://github.com/berntpopp/gene-curator/issues)
- [Project Board](https://github.com/berntpopp/gene-curator/projects)

---

**Last Updated**: 2026-01-12
**Next Review**: After v0.4.0 completion
