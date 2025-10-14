# Documentation Reorganization Plan

**Date**: 2025-10-14
**Objective**: Clearly separate planning/tracking content from documentation
**Status**: Ready for Implementation

---

## Executive Summary

**Problem**: Planning and tracking content has been mixed into the `docs/` directory, which should contain only user-facing documentation. This creates confusion about what is documentation vs. what is project planning.

**Solution**: Move all planning, implementation tracking, and enhancement proposals to the `plan/` directory, keeping only true documentation in `docs/`.

**Impact**:
- Clear separation of concerns (documentation vs. planning)
- Easier navigation for different stakeholders (users vs. developers)
- Better organization for AI agents and human developers

---

## Analysis Summary

### Current State

**docs/ directory contains**:
- ✅ 10 true documentation files (should stay)
- ❌ 3 planning/tracking files (should move)
- ❌ 3 entire subdirectories of planning content (should move)

**Total items to move**: ~60+ files organized into clear planning categories

### Guiding Principles

**Documentation (stays in docs/)**:
- User-facing guides and references
- API documentation
- Architecture overviews
- Setup and troubleshooting guides
- Completed implementation documentation (what exists now)

**Planning (moves to plan/)**:
- Implementation plans (what we will build)
- Roadmaps and tracking
- Enhancement proposals
- Progress summaries
- Migration plans
- Refactoring strategies

---

## Files to Stay in docs/ (True Documentation)

### Core Documentation Files
| File | Type | Rationale |
|------|------|-----------|
| `docs/README.md` | Documentation Index | Navigation hub for all docs |
| `docs/ARCHITECTURE.md` | System Documentation | Describes current architecture |
| `docs/API_REFERENCE.md` | API Documentation | Complete API reference guide |
| `docs/DATABASE_SCHEMA.md` | Schema Documentation | Current database structure |
| `docs/FRONTEND_GUIDE.md` | Development Guide | Frontend patterns and usage |
| `docs/WORKFLOW.md` | Process Documentation | How curation workflow works |
| `docs/CLINGEN_COMPLIANCE.md` | Feature Documentation | ClinGen compliance details |
| `docs/SETUP.md` | Setup Guide | How to install and configure |
| `docs/GENE_SCHEMA_COMPLETE.md` | Schema Reference | Gene schema documentation |
| `docs/SEO_IMPLEMENTATION.md` | Implementation Doc | Completed SEO features |

### Documentation Subdirectories
| Directory | Type | Rationale |
|-----------|------|-----------|
| `docs/archive/` | Historical Docs | Archived documentation |
| `docs/troubleshooting/` | User Support | Problem resolution guides |

**Total staying in docs/**: 12 files/directories

---

## Files to Move to plan/ (Planning Content)

### Root-Level Planning Files

#### 1. `docs/ISSUE_ROADMAP.md`
**Move to**: `plan/ISSUE_ROADMAP.md`

**Type**: Project tracking and roadmap

**Rationale**:
- Contains open issues tracking (23 issues)
- Priority matrices and phase planning
- Implementation effort estimates
- Milestone alignment
- This is clearly project management, not documentation

**Content Preview**:
```markdown
# Gene Curator - Open Issues Roadmap
**Total Open Issues**: 23
**Analysis Basis**: v2.0.0 architecture, implementation status

## Priority Matrix
### Phase 1: Curation Readiness (8-10 weeks) 🔴 CRITICAL
...
```

#### 2. `docs/DOCUMENTATION_REFACTORING_SUMMARY.md`
**Move to**: `plan/archive/DOCUMENTATION_REFACTORING_SUMMARY_2025-10-14.md`

**Type**: Meta-planning document

**Rationale**:
- Documents a planning exercise about documentation
- Historical record of refactoring work
- Should be archived as it documents a completed planning task
- Not user-facing documentation

**Content Preview**:
```markdown
# Documentation Refactoring Summary
**Date**: 2025-10-14
**Objective**: Streamline and update documentation

## Changes Made
1. CLAUDE.md - 53% reduction
...
```

### Planning Subdirectories (Complete Moves)

#### 3. `docs/enhancements/` → `plan/enhancements/`

**Type**: Enhancement proposals and tracking

**Structure**:
```
docs/enhancements/
├── README.md                    # Enhancement tracking system
├── 003-retry-utils-exponential-backoff.md
├── 006-frontend-fastapi-endpoint-alignment.md
├── 008-draft-autosave-frontend.md
├── 009-dynamic-form-generation.md
├── 010-review-workflow-4eyes.md
├── archive/                     # Completed enhancements
│   ├── 002-backend-unified-logging-system.md
│   ├── 003-frontend-unified-logging-system.md
│   └── LOGGING_CODE_REVIEW.md
├── deferred/                    # Postponed enhancements
│   ├── 002-cache-service-l1-l2.md
│   ├── 005-realtime-progress-tracking.md
│   ├── 007-view-management-topological-sort.md
│   └── README.md
├── implemented/                 # Implementation records
│   ├── 002-backend-logging-API-REFERENCE.md
│   ├── 002-backend-unified-logging-system-IMPLEMENTED.md
│   ├── 003-frontend-unified-logging-system-IMPLEMENTED.md
│   ├── 004-expanded-makefile-workflow.md
│   ├── 004-IMPLEMENTATION_SUMMARY.md
│   ├── 005-error-handling-fixes-using-existing-systems.md
│   ├── 006-simple-api-configuration.md
│   ├── 007-copilot-pr-review-fixes-IMPLEMENTED.md
│   ├── FRONTEND_LOGGING_TEST_RESULTS.md
│   ├── LOGGING_IMPLEMENTATION_GUIDE.md
│   └── README.md
└── docs/enhancements/           # Nested (seems like error)
    ├── ACTION_PLAN.md
    ├── APPROVED_ENHANCEMENTS.md
    ├── GITHUB_ISSUES_COMPARISON.md
    ├── README.md
    └── REFACTOR_CLOSES_ISSUES.md
```

**Rationale**:
- Enhancement proposals are planning documents
- Implementation tracking is project management
- Deferred items are planning decisions
- Even "implemented" subdirectory is tracking, not user docs
- The nested `docs/enhancements/docs/enhancements/` appears to be an error

**Files to Move**: ~30 files across 4 subdirectories

#### 4. `docs/navigation/` → `plan/features/navigation/`

**Type**: Feature implementation planning

**Structure**:
```
docs/navigation/
├── README.md                            # Navigation docs index
├── NAVIGATION_RESTRUCTURE_PLAN.md       # 7-phase architectural plan
├── NAVIGATION_IMPLEMENTATION_STATUS.md  # Progress tracking
├── PHASE_0_COMPLETION_SUMMARY.md        # Phase 0 completion
└── PHASE_1_COMPLETION_SUMMARY.md        # Phase 1 completion
```

**Rationale**:
- Complete 7-phase implementation plan (2363 lines)
- Implementation status tracking
- Phase completion summaries
- This is project planning, not user-facing navigation docs
- Should be organized under feature-specific planning

**Files to Move**: 5 files

**Note**: When navigation work is complete, a user-facing navigation guide could be added to `docs/` as `docs/NAVIGATION_GUIDE.md`

#### 5. `docs/refactoring/` → `plan/refactoring/`

**Type**: Architectural refactoring plans

**Structure**:
```
docs/refactoring/
├── README.md                           # Refactoring overview
├── BACKEND_IMPLEMENTATION.md           # Backend refactor plan
├── FRONTEND_IMPLEMENTATION.md          # Frontend refactor plan
├── TESTING_IMPLEMENTATION.md           # Testing strategy
├── IMPLEMENTATION_PROGRESS.md          # Progress tracking
├── MIGRATION_SQUASHING_PLAN.md         # Migration plan
├── SEED_DATA_REFACTORING.md            # Seed data plan
├── SQLALCHEMY_2.0_MIGRATION.md         # SQLAlchemy migration
├── CODE_QUALITY_LINTING_FIXES.md       # Linting fixes
├── CODE_REVIEW_2025-10-14.md           # Code review notes
└── archive/                            # Completed refactoring
    ├── RLS_TESTING_FIX_SUMMARY.md
    └── RLS_TESTING_STATUS.md
```

**Rationale**:
- Scope-centric refactoring implementation plans
- Database migration strategies
- Testing implementation plans
- Progress tracking and code reviews
- This is architectural planning, not user documentation

**Files to Move**: 12 files (10 in root, 2 in archive)

---

## Proposed New Structure

### docs/ (Documentation Only)

```
docs/
├── README.md                           # Documentation index
├── ARCHITECTURE.md                     # System architecture
├── API_REFERENCE.md                    # API documentation
├── DATABASE_SCHEMA.md                  # Database documentation
├── FRONTEND_GUIDE.md                   # Frontend guide
├── WORKFLOW.md                         # Workflow documentation
├── CLINGEN_COMPLIANCE.md               # ClinGen features
├── SETUP.md                            # Setup guide
├── GENE_SCHEMA_COMPLETE.md             # Schema reference
├── SEO_IMPLEMENTATION.md               # SEO features
├── archive/                            # Historical docs
│   └── INITIAL_PLANNING_VISION.md      # Original vision (archived)
└── troubleshooting/                    # Troubleshooting guides
    └── resolved/
        └── LOGIN_ISSUES_RESOLVED.md
```

**Total**: 10 files, 2 subdirectories

### plan/ (Planning & Tracking)

```
plan/
├── README.md                           # Planning index (UPDATE NEEDED)
├── ISSUE_ROADMAP.md                    # ← MOVED from docs/
├── IMPLEMENTATION_STATUS.md            # Overall status
├── SCHEMA_SPECIFICATIONS.md            # Schema specs
├── SCORING_ENGINE_GUIDE.md             # Scoring engine guide
├── DEPLOYMENT.md                       # Deployment plan
├── api/                                # API planning
│   ├── README.md
│   └── clingen_engine.md
├── database/                           # Database planning
│   ├── README.md
│   └── schema_design.md
├── frontend/                           # Frontend planning
│   └── README.md
├── scripts/                            # Script documentation
│   ├── README.md
│   └── clingen_documents/
│       ├── INDEX.md
│       ├── markdown/
│       └── README.md
├── enhancements/                       # ← MOVED from docs/
│   ├── README.md
│   ├── 003-retry-utils-exponential-backoff.md
│   ├── 006-frontend-fastapi-endpoint-alignment.md
│   ├── 008-draft-autosave-frontend.md
│   ├── 009-dynamic-form-generation.md
│   ├── 010-review-workflow-4eyes.md
│   ├── archive/
│   │   ├── 002-backend-unified-logging-system.md
│   │   ├── 003-frontend-unified-logging-system.md
│   │   └── LOGGING_CODE_REVIEW.md
│   ├── deferred/
│   │   ├── 002-cache-service-l1-l2.md
│   │   ├── 005-realtime-progress-tracking.md
│   │   ├── 007-view-management-topological-sort.md
│   │   └── README.md
│   ├── implemented/
│   │   ├── 002-backend-logging-API-REFERENCE.md
│   │   ├── 002-backend-unified-logging-system-IMPLEMENTED.md
│   │   ├── 003-frontend-unified-logging-system-IMPLEMENTED.md
│   │   ├── 004-expanded-makefile-workflow.md
│   │   ├── 004-IMPLEMENTATION_SUMMARY.md
│   │   ├── 005-error-handling-fixes-using-existing-systems.md
│   │   ├── 006-simple-api-configuration.md
│   │   ├── 007-copilot-pr-review-fixes-IMPLEMENTED.md
│   │   ├── FRONTEND_LOGGING_TEST_RESULTS.md
│   │   ├── LOGGING_IMPLEMENTATION_GUIDE.md
│   │   └── README.md
│   └── tracking/                       # ← MOVED from docs/enhancements/docs/enhancements/
│       ├── ACTION_PLAN.md
│       ├── APPROVED_ENHANCEMENTS.md
│       ├── GITHUB_ISSUES_COMPARISON.md
│       ├── README.md
│       └── REFACTOR_CLOSES_ISSUES.md
├── features/                           # Feature-specific planning
│   └── navigation/                     # ← MOVED from docs/navigation/
│       ├── README.md
│       ├── NAVIGATION_RESTRUCTURE_PLAN.md
│       ├── NAVIGATION_IMPLEMENTATION_STATUS.md
│       ├── PHASE_0_COMPLETION_SUMMARY.md
│       └── PHASE_1_COMPLETION_SUMMARY.md
├── refactoring/                        # ← MOVED from docs/refactoring/
│   ├── README.md
│   ├── BACKEND_IMPLEMENTATION.md
│   ├── FRONTEND_IMPLEMENTATION.md
│   ├── TESTING_IMPLEMENTATION.md
│   ├── IMPLEMENTATION_PROGRESS.md
│   ├── MIGRATION_SQUASHING_PLAN.md
│   ├── SEED_DATA_REFACTORING.md
│   ├── SQLALCHEMY_2.0_MIGRATION.md
│   ├── CODE_QUALITY_LINTING_FIXES.md
│   ├── CODE_REVIEW_2025-10-14.md
│   └── archive/
│       ├── RLS_TESTING_FIX_SUMMARY.md
│       └── RLS_TESTING_STATUS.md
└── archive/                            # Historical planning
    └── DOCUMENTATION_REFACTORING_SUMMARY_2025-10-14.md  # ← MOVED from docs/
```

---

## Migration Map

### Summary Table

| Source | Destination | Type | Files |
|--------|-------------|------|-------|
| `docs/ISSUE_ROADMAP.md` | `plan/ISSUE_ROADMAP.md` | Move | 1 |
| `docs/DOCUMENTATION_REFACTORING_SUMMARY.md` | `plan/archive/DOCUMENTATION_REFACTORING_SUMMARY_2025-10-14.md` | Move | 1 |
| `docs/enhancements/` | `plan/enhancements/` | Move Dir | ~30 |
| `docs/enhancements/docs/enhancements/` | `plan/enhancements/tracking/` | Move Dir | 5 |
| `docs/navigation/` | `plan/features/navigation/` | Move Dir | 5 |
| `docs/refactoring/` | `plan/refactoring/` | Move Dir | 12 |

**Total operations**: 6 moves (~54 files)

### Detailed Migration Commands

```bash
# 1. Create new directories
mkdir -p plan/enhancements/tracking
mkdir -p plan/features/navigation
mkdir -p plan/archive

# 2. Move root-level planning files
mv docs/ISSUE_ROADMAP.md plan/
mv docs/DOCUMENTATION_REFACTORING_SUMMARY.md plan/archive/DOCUMENTATION_REFACTORING_SUMMARY_2025-10-14.md

# 3. Move enhancements directory
mv docs/enhancements plan/

# 4. Fix nested enhancements structure
mv plan/enhancements/docs/enhancements/* plan/enhancements/tracking/
rmdir plan/enhancements/docs/enhancements
rmdir plan/enhancements/docs

# 5. Move navigation directory
mv docs/navigation plan/features/

# 6. Move refactoring directory
mv docs/refactoring plan/
```

---

## Cross-Reference Updates Needed

### Files with References to Moved Content

After moving files, these cross-references need updating:

#### 1. `docs/README.md`
**Current references**:
- Links to enhancements (now in plan/)
- Links to refactoring docs (now in plan/)
- References to roadmap (now in plan/)

**Action**: Remove planning-related links, keep only documentation links

#### 2. `plan/README.md`
**Current state**: Needs major update

**Action**:
- Add index of all planning content
- Link to moved directories (enhancements, navigation, refactoring)
- Create navigation structure for planning docs

#### 3. `CLAUDE.md`
**Current references**:
```markdown
- `docs/archive/INITIAL_PLANNING_VISION.md`: Original vision (archived)
```

**Action**:
- Update references to point to new locations
- Add note about docs/ vs plan/ separation
- Update "Important Files" section

#### 4. Individual moved files
Many files have internal cross-references like:
```markdown
- [Main Architecture Plan](../../PLAN.md)
- [Schema Specifications](../../plan/SCHEMA_SPECIFICATIONS.md)
- [Current Database Schema](../../database/sql/001_schema_foundation.sql)
```

**Action**: Update relative paths after moving files

---

## Implementation Steps

### Phase 1: Preparation (30 minutes)

1. **Create backup branch**
   ```bash
   git checkout -b docs-plan-reorganization
   ```

2. **Create directory structure**
   ```bash
   mkdir -p plan/enhancements/tracking
   mkdir -p plan/features/navigation
   mkdir -p plan/archive
   ```

3. **Verify current structure**
   ```bash
   tree docs/ -L 2 > /tmp/docs-before.txt
   tree plan/ -L 2 > /tmp/plan-before.txt
   ```

### Phase 2: File Moves (15 minutes)

Execute migration commands (see "Detailed Migration Commands" above)

### Phase 3: Reference Updates (45 minutes)

1. **Update docs/README.md**
   - Remove references to moved planning content
   - Keep only documentation-related navigation
   - Add note about where planning content is located

2. **Update plan/README.md**
   - Create comprehensive index of all planning content
   - Add sections for each subdirectory
   - Link to key planning documents

3. **Update CLAUDE.md**
   - Update "Important Files" section
   - Add note about docs/ vs plan/ separation
   - Update references to moved files

4. **Find and update cross-references**
   ```bash
   # Find all references to moved files
   grep -r "docs/enhancements" docs/ plan/ CLAUDE.md README.md
   grep -r "docs/navigation" docs/ plan/ CLAUDE.md README.md
   grep -r "docs/refactoring" docs/ plan/ CLAUDE.md README.md
   grep -r "ISSUE_ROADMAP" docs/ plan/ CLAUDE.md README.md
   ```

5. **Update relative paths in moved files**
   - Fix `../../` paths that changed due to new locations
   - Update links between planning documents

### Phase 4: Verification (30 minutes)

1. **Verify structure**
   ```bash
   tree docs/ -L 2 > /tmp/docs-after.txt
   tree plan/ -L 2 > /tmp/plan-after.txt
   diff /tmp/docs-before.txt /tmp/docs-after.txt
   diff /tmp/plan-before.txt /tmp/plan-after.txt
   ```

2. **Check for broken links**
   ```bash
   # Find all markdown links
   grep -r "\[.*\](\.\./" docs/ plan/
   # Manually verify each link works
   ```

3. **Review changes**
   ```bash
   git status
   git diff --stat
   ```

4. **Test that documentation still renders correctly**
   - Open key docs files in markdown viewer
   - Verify links work

### Phase 5: Commit & Document (15 minutes)

1. **Create commit**
   ```bash
   git add docs/ plan/ CLAUDE.md
   git commit -m "refactor: separate planning content from documentation

   - Move docs/enhancements/ → plan/enhancements/
   - Move docs/navigation/ → plan/features/navigation/
   - Move docs/refactoring/ → plan/refactoring/
   - Move docs/ISSUE_ROADMAP.md → plan/
   - Archive docs/DOCUMENTATION_REFACTORING_SUMMARY.md
   - Update all cross-references
   - Update docs/README.md and plan/README.md
   - Update CLAUDE.md references

   Rationale: Clear separation between user-facing documentation
   (docs/) and project planning/tracking content (plan/).

   Total files moved: ~54 files across 6 operations"
   ```

2. **Update this plan document status**
   ```markdown
   **Status**: ✅ Complete (2025-10-14)
   ```

---

## Benefits of Reorganization

### For Users
- ✅ **Clearer documentation**: Only user-facing docs in docs/
- ✅ **Easier navigation**: No confusion with planning content
- ✅ **Better onboarding**: Clear path to get started

### For Developers
- ✅ **Clear separation**: Know where to find planning vs docs
- ✅ **Better organization**: Related planning content together
- ✅ **Easier maintenance**: Update planning without touching docs

### For Project Management
- ✅ **Centralized planning**: All planning in one place
- ✅ **Better tracking**: Enhancement, features, refactoring organized
- ✅ **Historical records**: Archive planning decisions

### For AI Agents
- ✅ **Clearer context**: Understand what is docs vs planning
- ✅ **Better navigation**: Logical structure for finding content
- ✅ **Reduced confusion**: No mixing of different content types

---

## Success Criteria

- [x] Analysis complete: All files categorized correctly
- [ ] Directory structure created: New plan/ subdirectories exist
- [ ] Files moved: All planning content in plan/
- [ ] References updated: All cross-references point to new locations
- [ ] docs/ clean: Only documentation remains
- [ ] plan/ organized: Logical structure for all planning
- [ ] CLAUDE.md updated: References new structure
- [ ] README files updated: Both docs/ and plan/ indices current
- [ ] Git clean: No broken links or missing files
- [ ] Verification complete: All links tested

---

## Risk Mitigation

### Potential Issues

1. **Broken Links**
   - **Risk**: Cross-references break after moving files
   - **Mitigation**: Comprehensive grep-based search and update
   - **Verification**: Manual link checking

2. **Git History**
   - **Risk**: File moves lose git history
   - **Mitigation**: Use `git mv` instead of `mv` (optional)
   - **Note**: GitHub preserves history across moves

3. **External References**
   - **Risk**: External documentation (wikis, issues) link to old paths
   - **Mitigation**: Add redirects or notes in old locations
   - **Note**: Can add placeholder files with "Moved to..." messages

4. **Merge Conflicts**
   - **Risk**: Ongoing branches may conflict with moves
   - **Mitigation**: Communicate reorganization, merge recent work first
   - **Recovery**: Git handles file moves well, conflicts rare

---

## Post-Reorganization Maintenance

### Guidelines for Future Content

**Add to docs/ when**:
- User-facing guide or reference
- API/schema documentation
- Setup or troubleshooting help
- Architecture overview (current state)
- Completed feature documentation

**Add to plan/ when**:
- Implementation plan (future work)
- Enhancement proposal
- Roadmap or tracking
- Progress summary
- Migration strategy
- Refactoring plan

### Enforcement

1. **PR Reviews**: Check new files go in correct location
2. **CLAUDE.md**: Maintain guidelines about docs vs plan
3. **README files**: Keep indices updated as content added
4. **Quarterly Review**: Audit both directories for misplaced content

---

## Timeline

**Total Estimated Time**: 2-3 hours

| Phase | Duration | Tasks |
|-------|----------|-------|
| Preparation | 30 min | Backup, create dirs, verify structure |
| File Moves | 15 min | Execute 6 move operations |
| Reference Updates | 45 min | Update READMEs, CLAUDE.md, cross-refs |
| Verification | 30 min | Check structure, test links |
| Commit & Document | 15 min | Git commit, update status |
| **Total** | **2h 15min** | **5 phases** |

**Recommended Approach**: Single focused session to avoid partial state

---

## Appendix: File Inventory

### Files Moving to plan/

**Root Files (2)**:
1. `docs/ISSUE_ROADMAP.md` → `plan/ISSUE_ROADMAP.md`
2. `docs/DOCUMENTATION_REFACTORING_SUMMARY.md` → `plan/archive/DOCUMENTATION_REFACTORING_SUMMARY_2025-10-14.md`

**Enhancements Directory (~35 files)**:
- `docs/enhancements/*.md` (5 files)
- `docs/enhancements/archive/*.md` (3 files)
- `docs/enhancements/deferred/*.md` (4 files)
- `docs/enhancements/implemented/*.md` (11 files)
- `docs/enhancements/docs/enhancements/*.md` (5 files) → tracking/

**Navigation Directory (5 files)**:
- `docs/navigation/README.md`
- `docs/navigation/NAVIGATION_RESTRUCTURE_PLAN.md`
- `docs/navigation/NAVIGATION_IMPLEMENTATION_STATUS.md`
- `docs/navigation/PHASE_0_COMPLETION_SUMMARY.md`
- `docs/navigation/PHASE_1_COMPLETION_SUMMARY.md`

**Refactoring Directory (12 files)**:
- `docs/refactoring/*.md` (10 files)
- `docs/refactoring/archive/*.md` (2 files)

**Total Files Moving**: ~54 files

### Files Staying in docs/

**Root Files (10)**:
1. `docs/README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/API_REFERENCE.md`
4. `docs/DATABASE_SCHEMA.md`
5. `docs/FRONTEND_GUIDE.md`
6. `docs/WORKFLOW.md`
7. `docs/CLINGEN_COMPLIANCE.md`
8. `docs/SETUP.md`
9. `docs/GENE_SCHEMA_COMPLETE.md`
10. `docs/SEO_IMPLEMENTATION.md`

**Archive (1 file)**:
- `docs/archive/INITIAL_PLANNING_VISION.md`

**Troubleshooting (1 file)**:
- `docs/troubleshooting/resolved/LOGIN_ISSUES_RESOLVED.md`

**Total Files Staying**: 12 files

---

**Plan Created**: 2025-10-14
**Created By**: Claude Code (Anthropic)
**Status**: Ready for Implementation
**Estimated Completion**: 2-3 hours of focused work
