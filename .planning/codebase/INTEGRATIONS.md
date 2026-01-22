# External Integrations

**Analysis Date:** 2026-01-22

## APIs & External Services

**Gene & Nomenclature Reference:**
- HGNC (HUGO Gene Nomenclature Committee)
  - What it's used for: Gene symbol validation, canonical gene names, aliases, chromosome location
  - SDK/Client: `httpx` (async HTTP client)
  - Implementation: `backend/app/services/validators/hgnc_validator.py`
  - Auth: Email-based (default: "gene-curator@example.com")
  - Base URL: `https://rest.genenames.org`
  - Timeout: 10 seconds
  - Features: Search with wildcard, symbol validation, HGNC ID lookup, suggestions for misspelled genes
  - Caching: 30-day TTL on validation results

**Publication Data:**
- PubMed NCBI E-utilities
  - What it's used for: PMID validation, publication metadata retrieval (title, authors, journal, DOI, publication date)
  - SDK/Client: `httpx` (async HTTP client)
  - Implementation: `backend/app/services/validators/pubmed_validator.py`
  - Auth: Email-based (polite usage), optional NCBI API key for increased rate limits
  - Base URL: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`
  - XML parsing: `defusedxml` (with XXE protection)
  - Timeout: 10 seconds
  - Features: PMID validation, batch validation, author extraction
  - Caching: 90-day TTL (publications immutable)

**Phenotype & Disease Ontologies:**
- Human Phenotype Ontology (HPO)
  - What it's used for: HPO term validation (e.g., HP:0001250), term names, synonyms, definitions
  - SDK/Client: `httpx` (async HTTP client)
  - Implementation: `backend/app/services/validators/hpo_validator.py`
  - Base URL: `https://www.ebi.ac.uk/ols/api` (OLS - Ontology Lookup Service)
  - Timeout: 10 seconds
  - Features: Term validation, search with suggestions
  - Caching: 14-day TTL (ontologies update regularly)

- MONDO (Monarch Disease Ontology)
  - What it's used for: Disease term search and validation
  - SDK/Client: `httpx` (async HTTP client)
  - Implementation: `backend/app/services/ontology_service.py`
  - Base URL: `https://www.ebi.ac.uk/ols4/api/v2`
  - Features: Autocomplete-friendly search, disease term suggestions

- OMIM (Online Mendelian Inheritance in Man)
  - What it's used for: Disease-gene relationships, genetic inheritance patterns
  - SDK/Client: `httpx` (async HTTP client)
  - Implementation: `backend/app/services/ontology_service.py`
  - Base URL: `https://ontology.jax.org/api/network`
  - Features: Disease search, gene association lookup

- HPO (Human Phenotype Ontology) - JAX API
  - What it's used for: Disease-phenotype associations, inheritance pattern lookup
  - SDK/Client: `httpx` (async HTTP client)
  - Implementation: `backend/app/services/ontology_service.py`
  - Base URL: `https://ontology.jax.org/api/hp`
  - Features: Inheritance pattern retrieval with caching

**Configuration:**
- External API settings in `backend/config/api.yaml`:
  - HGNC base URL: `https://rest.genenames.org`
  - Timeout: 10 seconds per API call
  - Retry: 3 attempts with 1-second delay
  - Caching: Enabled by default, 3600-second TTL
  - Enable/disable: `external_apis.enabled` flag

## Data Storage

**Databases:**
- PostgreSQL 15+ (Primary)
  - Connection: `DATABASE_URL` environment variable (`postgresql://user:password@host:port/database`)
  - Client: SQLAlchemy 2.0 ORM with asyncpg (async) and psycopg2-binary (sync)
  - Tables: 18 core models including users, scopes, genes, curations, validations, audit logs, system logs
  - Features: UUID primary keys, JSONB for flexible field storage, arrays for list fields, full-text search on curations
  - Pool size: 10 (configurable via `database.pool_size` in api.yaml)
  - Max overflow: 20 connections
  - Async support: AsyncSessionLocal for non-blocking database operations

**File Storage:**
- Local filesystem only (no S3 or external blob storage)
  - Upload directory: `./uploads` (configurable via `uploads.upload_dir` in api.yaml)
  - Max file size: 10MB (configurable via `uploads.max_file_size_mb`)
  - Allowed formats: `.xlsx`, `.csv`, `.json` (configurable in api.yaml)
  - Validation: Content-type validation enabled
  - Use cases: Bulk gene import files, curation exports, gene summary exports

**Caching:**
- Redis 7+ (Optional, in-memory data store)
  - Connection: `REDIS_URL` environment variable (`redis://host:port/db`)
  - Client: `redis` Python library
  - Default port (development): 6399
  - Default port (production): 6379 (internal)
  - Use cases: API response caching (3600s TTL for external API calls), validation result caching
  - Container name: `gene_curator_redis`
  - Status: Optional (graceful degradation if unavailable)

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based implementation
  - Implementation: `backend/app/core/security.py`
  - Token type: JWT (JSON Web Tokens)
  - Algorithm: HS256 (HMAC with SHA-256)
  - Signing key: `SECRET_KEY` environment variable (32+ characters required)
  - Access token expiration: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
  - Refresh token expiration: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
  - Password hashing: bcrypt via passlib
  - Token library: python-jose
  - Session timeout: 60 minutes (configurable via api.yaml)
  - Max concurrent sessions: 5 per user (configurable)

**Authorization:**
- Role-Based Access Control (RBAC) + Scope-Based Permissions
  - User roles: admin (platform), user (default)
  - Scope roles: admin, curator, reviewer, viewer (via ScopeMembership model)
  - Permissions managed per scope (kidney-genetics, cardio-genetics, neuro-genetics, etc.)
  - Implementation: `backend/app/services/scope_permissions.py`

**User Management:**
- Database-backed user store in `scopes` and `users` tables
- Default development credentials: admin@gene-curator.dev, curator@gene-curator.dev, viewer@gene-curator.dev
- No external identity provider (LDAP, OAuth2, SAML) currently integrated

## Monitoring & Observability

**Error Tracking:**
- Not externally integrated (no Sentry, Datadog, etc.)
- Error logging to `SystemLog` table with 90-day retention
- Error export: Available via `/api/v1/logs/recent-errors` endpoint

**Logs:**
- Unified logging system (custom implementation)
  - Backend: `app.core.logging` module with request correlation tracking
  - Frontend: `logService` with real-time viewer (Ctrl+L / Cmd+L)
  - Persistence: `SystemLog` model in PostgreSQL
  - Retention: Configurable 30-90 days (api.yaml: `logging.retention_days`)
  - Features: Auto-sanitization of sensitive fields, request correlation IDs, performance timing
  - Performance tracking: Enabled by default, slow operation threshold 1000ms (configurable)

**Performance Monitoring:**
- Built-in performance decorators: `@timed_operation()`, `@api_endpoint()`
- Database query performance tracking (configurable via api.yaml)
- External API call performance tracking
- Slow operation threshold: 1000ms (configurable)

## CI/CD & Deployment

**Hosting:**
- Docker Compose (development and production)
- Docker images: PostgreSQL 15-Alpine, Redis 7-Alpine, custom FastAPI+Python, custom Node+Vue
- Network: Bridge network `gene_curator_network` for inter-service communication

**CI Pipeline:**
- Not externally configured (no GitHub Actions, GitLab CI, Jenkins detected)
- Local testing via `make` commands
- Makefile supports: hybrid-up, backend, frontend, test, lint, format-all, check-all, ci

**Deployment:**
- Production target in Dockerfile multi-stage builds
- Environment-based configuration via .env files
- Database migrations: Alembic (manual via CLI)
- Health checks: PostgreSQL readiness probe (10s interval, 5 retries)

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - PostgreSQL connection string (production) or local for hybrid mode
- `SECRET_KEY` - JWT signing key (minimum 32 characters for security)
- `ENVIRONMENT` - "production" or "development"
- `DEBUG` - true/false (enables SQL echo, verbose logging)
- `BACKEND_PORT` or `PORT` - API server port (default 8000, dev uses 8051)
- `VITE_API_BASE_URL` - Frontend API endpoint (default http://localhost:8051)
- `VITE_ENVIRONMENT` - "development" or "production"

**Optional env vars:**
- `REDIS_URL` - Redis connection for caching (if None, caching disabled)
- `LOG_LEVEL` - Logging verbosity (debug, info, warning, error)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - JWT expiration (default 30)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration (default 7)
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` - Email configuration (not actively used)
- `ALLOWED_ORIGINS` - CORS whitelist (deprecated in favor of api.yaml)

**Secrets location:**
- `.env` and `.env.dev` files (Git-ignored)
- Environment variables injected at runtime
- No secrets stored in code or configuration files
- Development credentials embedded in database seed data only

## Webhooks & Callbacks

**Incoming:**
- None currently implemented

**Outgoing:**
- None currently implemented
- Note: Celery dependency declared in `pyproject.toml` but not actively used in codebase

---

*Integration audit: 2026-01-22*
