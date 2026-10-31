#!/usr/bin/env bash
# PostgreSQL lane: build a throwaway database from database/sql plus the dev logins in
# database/fixtures (like a fresh dev volume), then run the tests marked `postgres`
# (RLS policies, scope CRUD) against it.
# The tests connect as app_user (no superuser, no BYPASSRLS) like the API does; fixtures that
# need DDL or seed data use OWNER_DATABASE_URL.
# Same script locally (`make test-postgres`) and in CI. Never touches the dev database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="gene-curator-pgtest-$$"
PORT="${PGTEST_PORT:-55461}"
IMAGE="${PGTEST_IMAGE:-postgres:15-alpine@sha256:54e0dd8e8cddcdbb9156c2486eed5a43eccb7214d7c6828097d41ce049fb3984}"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$NAME" \
  -e POSTGRES_DB=gene_curator_dev -e POSTGRES_USER=dev_user -e POSTGRES_PASSWORD=dev_password \
  -e APP_DB_PASSWORD=app_password \
  -p "127.0.0.1:$PORT:5432" \
  -v "$ROOT/database/sql:/docker-entrypoint-initdb.d:ro" \
  -v "$ROOT/database/fixtures:/docker-entrypoint-fixtures:ro" "$IMAGE" >/dev/null

# initdb runs every migration, then restarts the server; an SQL error stops the container.
for _ in $(seq 120); do
  if docker logs "$NAME" 2>&1 | grep -q "PostgreSQL init process complete"; then break; fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" != "true" ]; then
    docker logs "$NAME" 2>&1 | grep -E "ERROR|FATAL" >&2
    echo "Fresh database build from database/sql failed" >&2
    exit 1
  fi
  sleep 1
done
until docker exec "$NAME" pg_isready -q -h 127.0.0.1 -U dev_user -d gene_curator_dev; do sleep 1; done

cd "$ROOT/backend"
OWNER_DATABASE_URL="postgresql://dev_user:dev_password@localhost:$PORT/gene_curator_dev" \
DATABASE_URL="postgresql://app_user:app_password@localhost:$PORT/gene_curator_dev" \
APP_DB_PASSWORD=app_password \
  uv run pytest -m postgres "$@"
