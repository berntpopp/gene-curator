# GitHub Issues - Organized Tracking

**Last Updated**: 2026-01-12
**PR #126**: Merged to master
**Total Open Issues**: 23

---

## Milestone Overview

| Milestone | Open Issues | Priority | Target |
|-----------|-------------|----------|--------|
| **v0.4.0 - Core Curation Features** | 6 | HIGH | Phase 1 complete |
| **v0.5.0 - Infrastructure & Scalability** | 5 | HIGH | Production scalability |
| **v1.0.0 - Production Ready** | 6 | MEDIUM | First production release |
| **Backlog** | 6 | LOW | Future consideration |

---

## v0.4.0 - Core Curation Features

**Focus**: Complete core curation workflow with dynamic forms and review system.

| Issue | Title | Priority | Labels | Status |
|-------|-------|----------|--------|--------|
| [#116](https://github.com/berntpopp/gene-curator/issues/116) | Multi-user approval | HIGH | `type: feature`, `scope: frontend`, `scope: backend` | 70% - Backend complete |
| [#62](https://github.com/berntpopp/gene-curator/issues/62) | Enhance Curation Card | HIGH | `type: feature`, `scope: frontend` | 60% - Store complete |
| [#61](https://github.com/berntpopp/gene-curator/issues/61) | Enhance Pre-Curation Card | HIGH | `type: feature`, `scope: frontend` | 60% - Store complete |
| [#77](https://github.com/berntpopp/gene-curator/issues/77) | Implement Prefill Logic | MEDIUM | `type: feature`, `scope: frontend` | 40% - Backend ready |
| [#119](https://github.com/berntpopp/gene-curator/issues/119) | Gene Assignment Edit/Reassign | MEDIUM | `type: ui/ux`, `scope: frontend` | Pending |
| [#118](https://github.com/berntpopp/gene-curator/issues/118) | Workflow Management Views | MEDIUM | `type: ui/ux`, `scope: frontend` | Pending |

### Related Enhancements
- **#008** Draft Auto-Save (3-4h remaining)
- **#009** Dynamic Form Generation (6-8h remaining) → Closes #62, #61, #77
- **#010** 4-Eyes Review Workflow (4-6h remaining) → Closes #116

---

## v0.5.0 - Infrastructure & Scalability

**Focus**: Production-ready performance and data management.

| Issue | Title | Priority | Labels | Effort |
|-------|-------|----------|--------|--------|
| [#67](https://github.com/berntpopp/gene-curator/issues/67) | Pagination in Stores | HIGH | `type: performance`, `scope: frontend`, `scope: backend` | 4-6h |
| [#75](https://github.com/berntpopp/gene-curator/issues/75) | Search Functionality | HIGH | `type: feature`, `scope: frontend`, `scope: backend` | 3-4h |
| [#86](https://github.com/berntpopp/gene-curator/issues/86) | Backup System | HIGH | `type: infrastructure`, `scope: backend`, `scope: database` | 6-8h |
| [#66](https://github.com/berntpopp/gene-curator/issues/66) | Lazy Loading/Performance | MEDIUM | `type: performance`, `scope: frontend` | 6-8h |
| [#95](https://github.com/berntpopp/gene-curator/issues/95) | Advanced Filters | MEDIUM | `type: ui/ux`, `scope: frontend` | 3-4h |

**Total Effort**: ~22-30h

---

## v1.0.0 - Production Ready

**Focus**: Complete feature set for first production release.

| Issue | Title | Priority | Labels | Effort |
|-------|-------|----------|--------|--------|
| [#104](https://github.com/berntpopp/gene-curator/issues/104) | Add detailed instructions | MEDIUM | `documentation` | 2-3h |
| [#102](https://github.com/berntpopp/gene-curator/issues/102) | Check Clinical Groups | MEDIUM | `scope: backend` | 2-3h |
| [#105](https://github.com/berntpopp/gene-curator/issues/105) | ClinGen Classification Import | MEDIUM | `type: feature`, `scope: backend` | 4-6h |
| [#87](https://github.com/berntpopp/gene-curator/issues/87) | Prevent Deletion of Precuration | MEDIUM | `type: feature`, `scope: backend`, `scope: database` | 1-2h |
| [#53](https://github.com/berntpopp/gene-curator/issues/53) | MONDO Disease Selector | LOW | `type: feature`, `scope: frontend` | 4-6h |
| [#54](https://github.com/berntpopp/gene-curator/issues/54) | OMIM Disease Selector | LOW | `type: feature`, `scope: frontend` | 4-6h |

**Total Effort**: ~18-26h

---

## Backlog

**Focus**: Future considerations, nice-to-have features.

| Issue | Title | Priority | Labels | Reason |
|-------|-------|----------|--------|--------|
| [#115](https://github.com/berntpopp/gene-curator/issues/115) | Add transcript to curation | LOW | `type: feature` | Domain-specific |
| [#109](https://github.com/berntpopp/gene-curator/issues/109) | Transform TODOs into Issues | LOW | `documentation` | Documentation task |
| [#120](https://github.com/berntpopp/gene-curator/issues/120) | Schema Read-Only Detail View | LOW | `type: ui/ux` | UI enhancement |
| [#30](https://github.com/berntpopp/gene-curator/issues/30) | Customizable Dashboard | LOW | `type: feature` | Future feature |
| [#46](https://github.com/berntpopp/gene-curator/issues/46) | JSON/CSV File Uploads | LOW | `type: feature` | Future feature |
| [#19](https://github.com/berntpopp/gene-curator/issues/19) | Curation Modal Enhancement | LOW | `type: ui/ux` | Superseded by #62 |

---

## Recently Closed Issues

Issues closed by PR #126 merge:

| Issue | Title | Resolution |
|-------|-------|------------|
| #113 | Use standard JSON schema | JSON Schema validation implemented |
| #108 | Curation Entity Not Initialized | Proper initialization in new system |
| #107 | Make Curation Tab Visible | Navigation visibility logic |
| #106 | Make "Groups" mandatory | Schema-driven required fields |
| #101 | Create Log File for User Roles | Audit trail in database |
| #100 | Add User Deletion for Admin | User management endpoints |
| #99 | Update Stores for Nested Data | Pinia stores updated |
| #96 | Integration of Precuration and Gene | Unified data model |
| #110 | Replace Console Logs with Snackbar | Notification system |
| #114 | Broken link in FAQ | Fixed |

---

## Label System

### Priority
| Label | Color | Description |
|-------|-------|-------------|
| `priority: critical` | 🔴 Red | P0 - Blocker, must fix immediately |
| `priority: high` | 🟠 Orange | P1 - Important, should fix soon |
| `priority: medium` | 🟡 Yellow | P2 - Normal priority |
| `priority: low` | 🟢 Green | P3 - Nice to have |

### Type
| Label | Color | Description |
|-------|-------|-------------|
| `type: feature` | 🔵 Blue | New feature implementation |
| `type: infrastructure` | 🟣 Purple | Backend/tooling infrastructure |
| `type: ui/ux` | 🔵 Light Blue | User interface/experience |
| `type: performance` | 🟠 Peach | Performance optimization |

### Scope
| Label | Color | Description |
|-------|-------|-------------|
| `scope: frontend` | Teal | Vue.js changes |
| `scope: backend` | Purple | FastAPI changes |
| `scope: database` | Pink | Database schema/queries |

### Status
| Label | Color | Description |
|-------|-------|-------------|
| `status: blocked` | 🔴 Red | Blocked by another issue/PR |
| `status: in-progress` | 🟢 Green | Currently being worked on |
| `status: needs-review` | 🟡 Yellow | Needs design/architecture review |

---

## Implementation Roadmap

### Phase 1: Core Curation (16-22h)
1. Enhancement #008: Draft auto-save (3-4h)
2. Enhancement #009: Dynamic forms (6-8h)
3. Enhancement #010: Review workflow (4-6h)

### Phase 2: Infrastructure (22-30h)
1. #67: Pagination (4-6h)
2. #75: Search (3-4h)
3. #86: Backup (6-8h)
4. #66: Lazy loading (6-8h)
5. #95: Filters (3-4h)

### Phase 3: Production Ready (18-26h)
- Complete v1.0.0 milestone issues
- Final documentation
- Production deployment

---

**Last Updated**: 2026-01-12
**Status**: Issues reorganized, labeled, and assigned to milestones
