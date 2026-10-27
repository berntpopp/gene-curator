#!/usr/bin/env bash
# Isolated monkey-test stack: db 5455, api 8052, vite 5190. Never touches the dev stack.
# usage: monkey-stack.sh up <git-ref> | down
set -euo pipefail
MAIN=$(readlink -f "$(dirname "$0")/../..") WT=/home/bernt-popp/development/gc-wt/monkey
LOG=$MAIN/.planning/orchestration; C=gc-monkey-db
down() {
  for p in 8052 5190; do fuser -k -TERM "$p/tcp" >/dev/null 2>&1 || true; done
  docker rm -f $C >/dev/null 2>&1 || true
  git -C "$MAIN" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
  git -C "$MAIN" worktree prune
}
case "${1:-}" in
down) down ;;
up)
  REF=${2:?git ref}; down
  git -C "$MAIN" worktree add -q --detach "$WT" "$REF"
  ln -s "$MAIN/frontend/node_modules" "$WT/frontend/node_modules"
  # same init as docker-compose / scripts/test-postgres.sh: mount database/sql as initdb.d
  docker run -d --name $C -e POSTGRES_DB=gene_curator_dev -e POSTGRES_USER=dev_user \
    -e POSTGRES_PASSWORD=dev_password -e APP_DB_PASSWORD=app_password -p 127.0.0.1:5455:5432 \
    -v "$WT/database/sql:/docker-entrypoint-initdb.d:ro" postgres:15-alpine >/dev/null
  for _ in $(seq 120); do
    docker logs $C 2>&1 | grep -q "PostgreSQL init process complete" && break
    [ "$(docker inspect -f '{{.State.Running}}' $C)" = true ] || { docker logs $C 2>&1 | grep -E "ERROR|FATAL"; exit 1; }
    sleep 1
  done
  until docker exec $C pg_isready -q -h 127.0.0.1 -U dev_user -d gene_curator_dev; do sleep 1; done
  (cd "$WT/backend" && uv sync --extra dev --frozen -q)
  O='["http://localhost:5190","http://127.0.0.1:5190"]'
  cd "$WT/backend"; DATABASE_URL=postgresql://app_user:app_password@localhost:5455/gene_curator_dev \
    ENVIRONMENT=development DEBUG=true SECRET_KEY=monkey_secret ALLOWED_ORIGINS=$O \
    GENE_CURATOR_API__CORS__ALLOW_ORIGINS=$O \
    nohup uv run uvicorn app.main:app --host 127.0.0.1 --port 8052 >"$LOG/monkey-api.log" 2>&1 </dev/null 9>&- &
  cd "$WT/frontend"; VITE_API_BASE_URL=http://localhost:8052 VITE_ENABLE_DEV_LOGIN=true \
    nohup npm run dev -- --host 127.0.0.1 --port 5190 --strictPort >"$LOG/monkey-vite.log" 2>&1 </dev/null 9>&- &
  for u in http://localhost:8052/health http://localhost:5190/; do
    for _ in $(seq 90); do curl -sf -o /dev/null "$u" && continue 2; sleep 1; done
    echo "timeout: $u (see $LOG/monkey-*.log)" >&2; exit 1
  done
  echo "API http://localhost:8052  UI http://localhost:5190  DB localhost:5455 (dev_user/app_user)" ;;
*) echo "usage: $0 up <git-ref> | down" >&2; exit 2 ;;
esac
