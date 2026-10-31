#!/bin/bash
# Postgres initdb hook (sourced, so not executable, after the NNN_*.sql files): loads the dev/test logins only when
# database/fixtures is mounted, which docker-compose.yml and scripts/test-postgres.sh do.
# Not a migration: db-migrate and the migrate image only apply NNN_*.sql.
if [ -f /docker-entrypoint-fixtures/dev_users.sql ]; then
    docker_process_sql -f /docker-entrypoint-fixtures/dev_users.sql
fi
