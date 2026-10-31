# One-shot migrate image: applies database/sql to the production database and exits.
# psql only (no server, no gosu); a newer psql drives the PostgreSQL 15 server fine.
# Base image pinned by digest; Dependabot (docker ecosystem) bumps tag and digest together.
FROM alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a
# hadolint ignore=DL3018
RUN apk add --no-cache bash postgresql17-client \
    && adduser -D -H -u 10001 migrate
WORKDIR /app
# Schema and reference data only: .dockerignore keeps out the dev fixtures and test files.
COPY migrate.sh database/
COPY sql/ database/sql/
USER migrate
# Connection from libpq env (PGHOST, PGUSER = POSTGRES_USER, PGPASSWORD, PGDATABASE);
# 031 also reads APP_DB_PASSWORD. Idempotent: applied files are skipped (schema_migrations).
ENTRYPOINT ["/app/database/migrate.sh", "psql", "-X", "-v", "ON_ERROR_STOP=1", "--single-transaction", "-q"]
