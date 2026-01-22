# Codebase Concerns

**Analysis Date:** 2026-01-22

## Tech Debt

### Incomplete Feature Implementation: Gene Summary Service

**Issue:** Curator count placeholder in gene summary computation
- Files: `backend/app/services/gene_summary_service.py` (line 148)
- Impact: Gene summary reports curator count as always "1", limiting visibility into multi-curator contributions
- Current code: `"curator_count": 1,  # TODO: Get from curation history`
- Fix approach: Implement curation history tracking to extract unique curator count from CurationNew records. Query curation history to count distinct users who contributed to each curation.

### Incomplete Case-Control Evidence Scoring

**Issue:** Oversimplified case-control evidence scoring in ClinGen engine
- Files: `backend/app/scoring/clingen.py` (lines 652-654)
- Impact: Case-control evidence always returns fixed score of 3.0 instead of analyzing p-values, odds ratios, and study quality per SOP v11
- Current code: `# TODO: Implement full scoring based on p-value and odds ratio`
- Fix approach: Implement p-value thresholds and odds ratio analysis. Add study quality factors (sample size, allele frequency, case/control ascertainment). Reference SOP v11 Table 4 for case-control scoring criteria.

### Missing Schema Detail View

**Issue:** Schema view endpoint not implemented
- Files: `frontend/src/views/SchemaManagement.vue` (line 270)
- Impact: Users cannot inspect detailed field definitions or validation rules for schemas before editing
- Current state: Function shows toast message only
- Fix approach: Create SchemaDetail route component. Implement schema field inspection UI. Add visual representation of field types, validation rules, and scoring metadata.

### Missing Workflow Detail and Edit Views

**Issue:** Workflow detail and edit endpoints incomplete
- Files: `frontend/src/views/WorkflowManagement.vue` (lines 271, 277, 302)
- Impact: Workflow pairs cannot be inspected or modified after creation; stage configuration UI incomplete
- Current state: Only shows "coming soon" toast messages
- Fix approach: Implement WorkflowDetail and WorkflowEditor components. Add stage configuration forms. Include schema field mapping interface.

### Missing Gene Assignment Edit

**Issue:** Gene assignment editor not implemented
- Files: `frontend/src/components/dynamic/GeneAssignmentManager.vue` (multiple lines)
- Impact: Assignment changes require deletion and recreation; no history of modifications
- Fix approach: Implement assignment edit modal with status transition rules. Add edit history tracking. Validate scope and permission constraints.

### Incomplete Notification API Integration

**Issue:** Frontend notifications store lacks backend API connectivity
- Files: `frontend/src/stores/notifications.js` (lines 18, TODO markers)
- Impact: Notification features are UI-only placeholders; no real-time updates to users about reviews or assignments
- Current state: Commented out API imports; TODO markers for API integration
- Fix approach: Uncomment API client imports. Implement endpoints for fetching/marking notifications. Add WebSocket support for real-time updates.

### Missing Error Boundary Reporting

**Issue:** Error boundary component logs errors but doesn't report to monitoring
- Files: `frontend/src/components/ErrorBoundary.vue` (line with TODO)
- Impact: UI errors captured locally only; no alerting for critical component failures
- Fix approach: Implement error reporting service integration (e.g., Sentry). Send stack traces and context to backend monitoring system.

### Missing About/Docs Page

**Issue:** Navigation references non-existent About page
- Files: `frontend/src/composables/useNavigation.js` (line with TODO)
- Impact: About link in navigation will 404 or show blank page
- Fix approach: Create About.vue component or redirect to docs site. Add project info, version, support links.

## Known Bugs

### SQL Injection Risk in Gene Search (Array Membership)

**Issue:** Potential SQL injection in gene array search
- Files: `backend/app/crud/gene.py` (lines 92-93)
- Symptoms: Unsafe SQL text() calls with user input for array membership checks
- Code: `text(f"'{search_params.query}' = ANY(genes.previous_symbols)")`
- Current mitigation: Limited to internal API, not user-facing input validation
- Trigger: Malformed gene symbols with special characters could cause SQL errors or unexpected behavior
- Fix approach: Use SQLAlchemy's proper array comparison operators instead of raw text(). Implement parameterized queries. Add input validation for gene symbol format (alphanumeric + hyphen only).

### Missing iLike Parameterization Risk

**Issue:** Similar pattern in other CRUD operations
- Files: `backend/app/crud/gene.py` (lines 51, 89), `backend/app/crud/user.py` (ilike usage)
- Impact: Pattern creates minor SQL injection surface despite SQLAlchemy's ilike protection
- Fix approach: Validate search input length and character set. Use SQLAlchemy's built-in parameter binding exclusively.

## Security Considerations

### Broad Exception Handling in API Endpoints

**Issue:** Generic Exception catching masks specific error types
- Files: `backend/app/api/v1/endpoints/schema_validation.py` (multiple except Exception blocks)
- Risk: Attacker can't distinguish between validation errors and system errors; internal error details potentially leaked to clients
- Current mitigation: All exceptions return 500 status codes
- Recommendations:
  1. Create custom exception hierarchy (ValidationError, PermissionError, NotFoundError, etc.)
  2. Log full stack traces only for true server errors
  3. Return specific HTTP status codes (400, 403, 404)
  4. Never expose internal stack traces to clients

### Hardcoded Credentials in Tests

**Issue:** Test fixtures use hardcoded default passwords
- Files: `backend/app/tests/unit/test_auth.py` (noqa: S105 markers throughout)
- Risk: Password patterns leaked in test code; if test fixtures copied to other contexts, credentials exposed
- Current state: Suppressed with noqa directives (acknowledged but not fixed)
- Recommendations:
  1. Move test credentials to environment variables or secure fixture system
  2. Use randomized passwords per test run
  3. Remove hardcoded seed passwords from models

### JSONB Field Injection Potential

**Issue:** scope_config and other JSONB fields accept arbitrary JSON
- Files: `backend/app/models/models.py` (lines 123, 175, etc.)
- Risk: Malicious JSON structures could bypass validation if not properly handled
- Current mitigation: No documented validation on JSONB input
- Recommendations:
  1. Implement JSON schema validation for all JSONB fields
  2. Document expected JSON structure for each field
  3. Add Pydantic validation at API boundaries

## Performance Bottlenecks

### N+1 Query Pattern in Curation Loading

**Issue:** Multiple sequential queries when loading curations with related data
- Files: `backend/app/crud/curation.py`, `backend/app/crud/gene.py` (lines with .all() and subsequent loops)
- Problem: Fetches curation list, then iterates fetching scopes, evidence, etc. separately
- Symptom: Gene detail views with 100+ curations will execute 100+ additional queries
- Current performance: Linear time complexity O(n) for n curations
- Improvement path:
  1. Use SQLAlchemy relationship eager loading (joinedload, selectinload)
  2. Implement single query with LEFT JOIN for related data
  3. Cache frequently accessed scope data
  4. Add database indices on foreign keys (already partially done)

### Inefficient Gene Summary Computation

**Issue:** Full recomputation on every call for stale summaries
- Files: `backend/app/services/gene_summary_service.py` (lines 232-238)
- Problem: Marks stale and recomputes immediately; no background job scheduling
- Symptom: Long gene list views may trigger 100+ recomputations
- Limit: Scales linearly; breaks at ~1000 genes with real-time requests
- Scaling path:
  1. Implement job queue (Celery, RQ) for async recomputation
  2. Cache summaries with TTL (5-15 minutes)
  3. Mark stale but serve cached version while recomputing in background
  4. Add database trigger to update is_stale flag asynchronously

### No Query Result Pagination for Large Gene Datasets

**Issue:** Evidence items and related data loaded fully into memory
- Files: `backend/app/crud/gene_catalogue.py`, `backend/app/api/v1/endpoints/genes.py`
- Impact: Loading gene with 10,000 evidence items loads entire list into Python objects
- Scaling: Fails with OOM errors at ~100k records
- Limit: Current pagination doesn't apply to nested evidence/curation data
- Improvement path:
  1. Paginate evidence items separately
  2. Return evidence count with lazy-load option
  3. Implement streaming JSON responses for large datasets
  4. Add database-level filtering before application layer

### Unoptimized Schema Validator Lookups

**Issue:** Schema validator instantiated on every validation call
- Files: `backend/app/core/schema_validator.py` (1160 lines)
- Problem: No caching of validator instances; re-parses schema config each time
- Symptom: Batch validation of 100 curations creates 100 validator instances
- Improvement path:
  1. Cache validator instances with schema version as key
  2. Implement LRU cache with 50-100 schema limit
  3. Invalidate cache on schema updates
  4. Pre-warm cache on application startup

## Fragile Areas

### Gene Summary Consensus Logic

**Issue:** Simple majority voting ignores classification strength
- Files: `backend/app/services/gene_summary_service.py` (lines 180-190)
- Why fragile: Multiple classifications with same vote count produce arbitrary "consensus"; doesn't account for confidence scores or classification quality
- Current approach: `max(classification_summary, key=...)` picks first alphabetically on tie
- Safe modification: Add weighted voting system. Account for score confidence (e.g., definitive = higher weight than limited). Document tie-breaking behavior.
- Test coverage: No unit tests for consensus calculation with tied votes
- Risk: Conflicting classifications reported as consensus instead of disputed

### Curation History Tracking Incomplete

**Issue:** No formal history table for curation mutations
- Files: Core curation CRUD lacks audit trail mechanism
- Why fragile: State changes (draft→submitted→approved→active) not tracked; rollback/audit impossible
- Safe modification: Implement audit trigger on curation updates. Store version history. Add who/when/what tracking.
- Test coverage: No integration tests for state transitions
- Risk: Lose change provenance; cannot trace who approved a curation

### Workflow Engine State Machine

**Issue:** Five-stage workflow lacks explicit state validation
- Files: `backend/app/crud/workflow_engine.py` (1148 lines)
- Why fragile: Direct status updates could bypass workflow rules (e.g., jump from entry to active)
- Safe modification: Implement explicit state machine with allowed transitions. Validate each transition has required actors (4-eyes reviewer). Block invalid transitions.
- Test coverage: Limited integration tests for workflow transitions
- Risk: Data integrity violations; curations bypass peer review

### Dynamic Form Generation from Schema

**Issue:** Frontend form generation from JSONB field definitions (not yet fully implemented)
- Files: `frontend/src/components/dynamic/DynamicForm.vue` (referenced in router but incomplete)
- Why fragile: Schema field definitions could be malformed (missing type, invalid validation); form generator may fail silently or expose raw data
- Safe modification: Add schema validation with JSON Schema. Implement form field type guards. Add fallback rendering for unknown field types.
- Test coverage: No unit tests for schema→form conversion
- Risk: Hidden fields, missing validators, forms that don't match curator expectations

### Permission Cache Invalidation

**Issue:** Scope membership changes don't immediately invalidate permission caches
- Files: `backend/app/services/scope_permissions.py` (689 lines)
- Why fragile: User permissions cached but no cache invalidation hook on membership updates
- Safe modification: Implement cache key pattern (user_id:scope_id). Invalidate on ScopeMembership insert/update/delete. Use Redis or TTL-based cache.
- Test coverage: No tests for permission cache expiration
- Risk: Users retain old permissions; security boundary violation

## Scaling Limits

### Gene Catalogue Scalability

**Current capacity:** ~50,000 genes with reasonable response time (<2s)
**Limit:** Database queries slow at 100,000+ genes
- Issue: Full table scans on gene searches without proper indices
- Scaling path:
  1. Add composite indices on (approved_symbol, hgnc_id, chromosome)
  2. Implement full-text search (PostgreSQL GIN index)
  3. Consider gene search microservice with Elasticsearch for >500k genes

### Active Curation Per Gene

**Current capacity:** ~10 scopes per gene (10 active curations)
**Limit:** Query performance degrades at 50+ curations per gene
- Issue: No indexing on (gene_id, scope_id) for ActiveCuration table
- Scaling path:
  1. Add index on (gene_id, archived_at)
  2. Partition ActiveCuration by gene_id ranges
  3. Archive old curations to separate table

### Concurrent Workflow Operations

**Current capacity:** ~100 concurrent workflow state transitions
**Limit:** Database lock contention at 500+ concurrent requests
- Issue: Pessimistic locking on workflow table updates
- Scaling path:
  1. Implement optimistic locking (version column)
  2. Use event sourcing for workflow state
  3. Separate write (command) and read (query) models

### User Session/Permission Load

**Current capacity:** ~1,000 active users
**Limit:** Token validation queries become bottleneck
- Issue: Every request validates JWT against user table
- Scaling path:
  1. Cache user permissions in Redis (5-min TTL)
  2. Use JWT claims for basic permissions
  3. Implement service mesh with embedded auth checks

## Dependencies at Risk

### ClinGen SOP Version Lock

**Risk:** Engine hardcoded to SOP v11.0.0 methodology
- Files: `backend/app/scoring/clingen.py` (line 75, version constant)
- Impact: Cannot support newer SOP versions without code changes
- Migration plan:
  1. Make SOP version configurable per schema
  2. Implement SOP v12 engine alongside v11
  3. Add schema validation to ensure evidence format matches SOP version
  4. Document upgrade path for existing curations

### PostgreSQL JSONB Dependency

**Risk:** Heavy reliance on JSONB for schema-agnostic fields
- Files: Multiple model fields use compatible_jsonb()
- Impact: Migration to other databases (MySQL, MongoDB) extremely difficult
- Mitigation: JSONB usage is intentional for schema flexibility; acceptable for PostgreSQL-only deployments
- Fallback: Could use TEXT + JSON validation if needed, but loses database-level validation benefits

### Vue 3 Composition API Adoption

**Risk:** Mixed Composition API and Options API in components
- Files: Some components use Composition API (setup), others use Options API
- Impact: Inconsistent patterns make onboarding harder; refactoring more complex
- Migration plan: Gradually convert remaining Options API components to Composition API. Document pattern standards.

### Pinia Store Duplication

**Risk:** workflowPairs stored in schemasStore instead of workflowStore (architectural inconsistency)
- Files: `frontend/src/views/WorkflowManagement.vue` (comments on lines 207-208)
- Impact: Confusing API surface; future refactoring difficult
- Fix approach: Move workflowPairs to dedicated store. Update all component imports. Update tests.

## Missing Critical Features

### Draft Auto-Save

**Problem:** No automatic saving of in-progress curations
- Blocks: Long-form curation entries vulnerable to data loss
- Current state: Documented in CLAUDE.md as "Pending"
- Implementation: Add draft save on field change. Track dirty state. Show unsaved indicator. Implement conflict resolution for concurrent edits.

### Export/Import Functionality

**Problem:** No way to bulk export or import curations
- Blocks: Data portability; backup/restore; multi-scope collaboration
- Impact: Manual data entry only; scales poorly for 100+ curations
- Implementation: Add CSV/JSON export endpoints. Implement import validation. Add mapping UI for field alignment.

### Advanced Reporting

**Problem:** No analytics dashboard or custom report generation
- Blocks: Data visibility; discovery of gaps in curation coverage
- Current state: Logs exist but no aggregation/reporting
- Implementation: Build analytics store. Add dashboard with charts (curations per scope, reviewer workload, gene coverage). Implement scheduled report exports.

### Peer Review Audit Trail

**Problem:** No detailed record of review comments and conditions
- Blocks: Transparency in approval decisions
- Current implementation: Status tracking only; no comment/feedback model
- Implementation: Add ReviewComment model. Implement threaded comments. Track reviewer identity and timestamp.

## Test Coverage Gaps

### Dynamic Form Generation Tests

**Untested area:** Schema field validation and form component generation
- Files: `frontend/src/components/dynamic/DynamicForm.vue` (incomplete implementation)
- What's not tested: Field type mapping, validation rule enforcement, error display, nested field rendering
- Risk: Schema malformation goes undetected; forms render incorrectly in production
- Priority: High (blocking complete form integration)

### Workflow State Machine Tests

**Untested area:** Transition validation between workflow stages
- Files: `backend/app/crud/workflow_engine.py` (1148 lines, limited test coverage)
- What's not tested: Invalid transition attempts, role-based stage access, 4-eyes enforcement, rejected→revision flow
- Risk: Data corruption from invalid state transitions; security bypass of peer review
- Priority: High (security-critical)

### Permission Cache Invalidation Tests

**Untested area:** Scope membership cache expiration
- Files: `backend/app/services/scope_permissions.py`
- What's not tested: Cache invalidation after membership add/remove, TTL expiration, concurrent update handling
- Risk: Users retain stale permissions after role changes
- Priority: High (security)

### Gene Summary Consensus Tests

**Untested area:** Multi-scope classification consensus
- Files: `backend/app/services/gene_summary_service.py`
- What's not tested: Tied vote handling, conflicted classifications, confidence weighting, edge cases (1 scope, 100 scopes)
- Risk: Incorrect consensus reports; hidden conflicts marked as agreement
- Priority: Medium

### Error Boundary Integration Tests

**Untested area:** Component-level error handling and recovery
- Files: `frontend/src/components/ErrorBoundary.vue`
- What's not tested: Error capture, logging, UI state after error, recovery mechanisms
- Risk: Silent failures; error states not properly communicated
- Priority: Medium

### Case-Control Evidence Validation Tests

**Untested area:** ClinGen SOP v11 case-control scoring edge cases
- Files: `backend/app/scoring/clingen.py` (lines 636-654)
- What's not tested: Missing p-values, extreme odds ratios, study quality factors, boundary conditions
- Risk: Invalid scores accepted; evidence quality not assessed
- Priority: Medium (score-critical)

### SQL Injection Prevention Tests

**Untested area:** Gene search query parameter injection
- Files: `backend/app/crud/gene.py` (array membership and ilike searches)
- What's not tested: Special characters in search, array injection attempts, SQL operators in input
- Risk: Query parsing errors; potential injection vectors exposed
- Priority: High (security)

### Cross-Scope Permission Tests

**Untested area:** Permission enforcement across multiple scopes
- Files: Various endpoint tests
- What's not tested: User with mixed roles (curator in scope A, viewer in scope B), bulk operations respecting scope boundaries
- Risk: Data access violations; users see/modify data outside their scopes
- Priority: High (security)

---

*Concerns audit: 2026-01-22*
