#!/usr/bin/env bash
# Verified PostgreSQL backup: pg_dump (custom format) -> pg_restore --list check -> keep newest N.
# Usage: scripts/backup.sh [dir]   (default: backups/)
# Env: POSTGRES_USER, POSTGRES_DB (required), POSTGRES_CONTAINER (default gene_curator_postgres),
#      BACKUP_KEEP (default 14). Schedule it with cron, e.g.
#      0 2 * * * cd /srv/gene-curator && set -a && . ./.env.dev && set +a && scripts/backup.sh
set -euo pipefail

dir=${1:-backups}
keep=${BACKUP_KEEP:-14}
container=${POSTGRES_CONTAINER:-gene_curator_postgres}
: "${POSTGRES_USER:?POSTGRES_USER is required}" "${POSTGRES_DB:?POSTGRES_DB is required}"
[[ $keep =~ ^[1-9][0-9]*$ ]] || { echo "BACKUP_KEEP must be a positive integer" >&2; exit 1; }

mkdir -p "$dir"
file="$dir/backup_$(date +%Y%m%d_%H%M%S).dump"
partial="$file.partial"
trap 'rm -f "$partial"' EXIT

docker exec "$container" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c > "$partial"
# A truncated or corrupt archive fails to list its table of contents.
docker exec -i "$container" pg_restore --list > /dev/null < "$partial"
mv "$partial" "$file"

# Retention: newest $keep backups stay; only files this script names are touched.
mapfile -t old < <(ls -1t "$dir"/backup_*.dump | tail -n +$((keep + 1)))
((${#old[@]} == 0)) || rm -f -- "${old[@]}"
echo "$file"
