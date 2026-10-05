#!/usr/bin/env bash
# restore.sh <dump> — restore a pg_dump custom-format file into a database.
#
#   TARGET_DB      database to restore into (default: istari_restore). The
#                  database is created if missing and its schema is replaced.
#                  Restoring over the live database requires TARGET_DB=istari
#                  explicitly; the default keeps restores isolated.
#   DATABASE_URL   asyncpg DSN; only the server/credentials part is used.
set -euo pipefail

dump="${1:?usage: restore.sh <dump-file>}"
[ -f "$dump" ] || { echo "no such file: $dump" >&2; exit 1; }

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "${DATABASE_URL:-}" ] && [ -f "$here/.env" ]; then
  # Read the one variable we need; never execute .env.
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$here/.env" | tail -n 1 | cut -d= -f2- | tr -d '"'"'")"
fi
: "${DATABASE_URL:?DATABASE_URL is required}"
TARGET_DB="${TARGET_DB:-istari_restore}"

for tool in psql pg_restore; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool not found" >&2; exit 1; }
done

server="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"
server="${server%/*}"            # drop the database name
admin="$server/postgres"
target="$server/$TARGET_DB"

if ! psql "$admin" -tAc "SELECT 1 FROM pg_database WHERE datname = '$TARGET_DB'" | grep -q 1; then
  psql "$admin" -v ON_ERROR_STOP=1 -qc "CREATE DATABASE \"$TARGET_DB\""
fi

# --clean --if-exists replaces objects that already exist in the target;
# --no-owner avoids role mismatches between machines.
pg_restore --no-owner --no-privileges --clean --if-exists --exit-on-error \
  --dbname="$target" "$dump"
echo "restored $dump into database '$TARGET_DB'"
