#!/bin/bash
# Database initialization script for Gene Curator Schema-Agnostic System
# Runs SQL files in order to set up the complete database

set -e

# Wait for PostgreSQL to be ready
until pg_isready -h postgres -p 5432 -U dev_user; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "PostgreSQL is ready. Initializing schema-agnostic database..."

# Set database connection parameters
export PGHOST=postgres
export PGPORT=5432
export PGUSER=dev_user
export PGDATABASE=gene_curator_dev

echo "Running schema-agnostic database initialization scripts..."

# Run SQL scripts in order
echo "1. Creating schema-agnostic foundation..."
psql -f /docker-entrypoint-initdb.d/001_schema_foundation.sql

echo "2. Setting up triggers and functions..."
psql -f /docker-entrypoint-initdb.d/002_schema_triggers.sql

echo "3. Creating views..."
psql -f /docker-entrypoint-initdb.d/003_schema_views.sql

echo "4. Inserting seed data..."
psql -f /docker-entrypoint-initdb.d/004_seed_data.sql

echo "Database initialization complete!"

# Test the setup
echo "Testing schema-agnostic system..."
psql -c "
SELECT 
    s.name as scope_name,
    cs.name as schema_name,
    cs.version,
    cs.status
FROM scopes s
LEFT JOIN curation_schemas cs ON cs.id = s.default_workflow_pair_id
LIMIT 5;
"

echo "Schema-agnostic database setup and testing complete!"