#!/usr/bin/env bash
set -euo pipefail

# Example:
#   ./云端恢复现成库示例.sh /srv/lawqa/lawqa.dump

DUMP_FILE="${1:-/srv/lawqa/lawqa.dump}"

docker cp "$DUMP_FILE" lawqa_postgres:/tmp/lawqa.dump
docker exec -it lawqa_postgres bash -lc '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
  createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/lawqa.dump
'

echo "Restore complete."
