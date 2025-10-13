# Gene Curator Refactoring Documentation

This directory contains comprehensive documentation for major architectural refactoring efforts in Gene Curator.

## Current Refactoring Plans

### Scope-Centric Multi-Tenant Architecture

**Documents:**
- [Backend Implementation](./BACKEND_IMPLEMENTATION.md) - Secure database and API implementation
- [Frontend Implementation](./FRONTEND_IMPLEMENTATION.md) - DRY/SOLID compliant UI implementation
- [Testing Implementation](./TESTING_IMPLEMENTATION.md) - Comprehensive testing strategy (Testing Trophy model)

**Status:** Ready for Implementation

**Overview:**
Transforms Gene Curator from an application-wide role-based system into a scope-centric multi-tenant platform where curation scopes (projects) are the central organizing principle, inspired by GitHub's collaboration model.

**Key Changes:**
- Application-level roles simplified to `admin` and `user`
- Scope-level roles: `admin`, `curator`, `reviewer`, `viewer`
- Users can have different roles in different scopes
- GitHub-style scope management (title, description, due date, visibility)
- Team-based collaboration within scopes
- PostgreSQL Row-Level Security (RLS) for multi-tenant isolation
- Invitation system for scope membership

**Security & Quality:**
- ✅ SQL injection prevention with parameterized queries
- ✅ PostgreSQL RLS with FORCE protection
- ✅ TOCTOU race condition prevention
- ✅ DRY/KISS/SOLID compliance
- ✅ Performance optimization with STABLE functions
- ✅ Comprehensive error handling

**Benefits:**
- ✅ Flexible collaboration across institutions
- ✅ Domain-specific expertise recognition (admin in one scope, viewer in another)
- ✅ Public/private scopes for sharing vs proprietary work
- ✅ Team management for easier user organization
- ✅ Clear ownership and accountability per scope
- ✅ Support for both permanent specialties and temporary projects

**Rating:** 9/10 - Significantly better suited for multi-user, multi-scope collaboration

---

## Implementation Approach

1. **Backend First** (Week 1-4): Implement secure database schema and FastAPI endpoints
2. **Frontend Second** (Week 5-7): Build DRY/SOLID compliant Vue 3 UI
3. **Integration Testing** (Week 8): End-to-end testing with RLS verification
4. **Performance Testing** (Week 9): 1000+ scope load testing
5. **Deployment** (Week 10): Production rollout with monitoring

All implementation documents include:
- Exact file paths and line numbers
- Complete code examples ready to use
- Security best practices applied throughout
- Testing checklists and acceptance criteria

**Testing Strategy:**
- **Testing Trophy Model** - Integration-focused (70% integration, 20% unit, 5% E2E, 5% static)
- **pytest + FastAPI TestClient** - Modern testing framework with dependency injection
- **pytest-postgresql** - Real database testing with transaction rollback
- **Factory Boy + Hypothesis** - Test data generation and property-based testing
- **100% RLS Coverage** - All security policies tested
- **85%+ Overall Coverage** - Enforced in CI/CD

## Implementation Status

| Phase | Status | Target Date | Notes |
|-------|--------|-------------|-------|
| Planning | ✅ Complete | - | Design reviewed and approved |
| Database Schema | ⏳ Not Started | Week 1-2 | - |
| Backend API | ⏳ Not Started | Week 3-4 | - |
| Frontend UI | ⏳ Not Started | Week 5-6 | - |
| Integration & Testing | ⏳ Not Started | Week 7-8 | - |
| Documentation & Deployment | ⏳ Not Started | Week 9-10 | - |

## Related Documentation

- [Main Architecture Plan](../../PLAN.md) - Overall Gene Curator architecture
- [Schema Specifications](../../plan/SCHEMA_SPECIFICATIONS.md) - Schema format details
- [Current Database Schema](../../database/sql/001_schema_foundation.sql) - Existing schema

## Questions or Feedback

For questions or feedback on these refactoring plans, please contact the development team or open an issue in the project repository.
