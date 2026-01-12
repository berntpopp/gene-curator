#!/bin/bash
# Run ClinGen SOP v11 migrations
# This script applies migrations 008-015 to an existing database

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database connection details
DB_CONTAINER="${POSTGRES_CONTAINER:-gene_curator_postgres}"
DB_USER="${POSTGRES_USER:-dev_user}"
DB_NAME="${POSTGRES_DB:-gene_curator_dev}"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  ClinGen SOP v11 Database Migration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Migration files to execute
migrations=(
    "008_add_lock_version.sql"
    "009_create_evidence_items.sql"
    "010_create_gene_summaries.sql"
    "011_create_validation_cache.sql"
    "012_enhance_audit_logs.sql"
    "013_add_performance_indexes.sql"
    "014_seed_clingen_schema.sql"
    "015_migrate_evidence_data.sql"
)

# Counter for successful migrations
successful=0
failed=0

# Run each migration
for migration in "${migrations[@]}"; do
    echo -e "${BLUE}Running migration: ${migration}${NC}"

    if docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f "/docker-entrypoint-initdb.d/${migration}" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${migration} - SUCCESS${NC}"
        ((successful++))
    else
        echo -e "${RED}❌ ${migration} - FAILED${NC}"
        echo -e "${YELLOW}Error details:${NC}"
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f "/docker-entrypoint-initdb.d/${migration}"
        ((failed++))
    fi
    echo ""
done

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Migration Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Successful: ${successful}${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: ${failed}${NC}"
else
    echo -e "${GREEN}Failed: 0${NC}"
fi
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ All migrations completed successfully!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some migrations failed. Please review the errors above.${NC}"
    exit 1
fi
