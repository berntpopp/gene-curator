#!/bin/bash
# Apply pending database/sql migrations once, in one transaction, recording each file in
# schema_migrations (030). Runs on an empty database too (production: the migrate image).
#   FILE=database/sql/NNN_x.sql database/migrate.sh <psql command...>   (FILE optional)
# The psql command must read stdin with -X -v ON_ERROR_STOP=1 --single-transaction;
# `make db-migrate` passes `docker exec ... psql`, database/Dockerfile a plain psql.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n ${FILE:-} ]]; then files=("$FILE"); else files=(database/sql/[0-9][0-9][0-9]_*.sql); fi
for file in "${files[@]}"; do
	[[ "$file" =~ ^database/sql/[0-9]{3}_[a-zA-Z0-9_]+\.sql$ && -f "$file" ]] || { echo "Invalid migration: $file" >&2; exit 1; }
done
{
	printf '%s\n' 'SELECT pg_advisory_xact_lock(158030);'
	cat database/sql/030_schema_migrations.sql
	for file in "${files[@]}"; do
		name=${file##*/}
		printf "SELECT NOT EXISTS (SELECT 1 FROM schema_migrations WHERE filename = '%s') AS pending \\gset\n\\if :pending\n" "$name"
		sed -E '/^(BEGIN|COMMIT);[[:space:]]*$/d' "$file"
		printf "\nINSERT INTO schema_migrations (filename) VALUES ('%s') ON CONFLICT DO NOTHING;\n\\\\endif\n" "$name"
	done
} | "$@"
