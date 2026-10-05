#!/usr/bin/env bash
# backup.sh — pg_dump (custom format) of the Istari database.
#
#   DATABASE_URL   asyncpg DSN from .env (postgresql+asyncpg://...); the
#                  "+asyncpg" is stripped for libpq.
#   BACKUP_DIR     where dumps land (default: ./backups)
#
# Output: $BACKUP_DIR/istari-<UTC timestamp>.dump
# The dump contains learning history, notes and the owner password hash:
# treat it as sensitive. backups/ is gitignored.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -z "${DATABASE_URL:-}" ] && [ -f "$here/.env" ]; then
  # Read the one variable we need; never execute .env.
  DATABASE_URL="$(grep -E '^DATABASE_URL=' "$here/.env" | tail -n 1 | cut -d= -f2- | tr -d '"'"'")"
fi
: "${DATABASE_URL:?DATABASE_URL is required (set it or create .env)}"
BACKUP_DIR="${BACKUP_DIR:-$here/backups}"
mkdir -p "$BACKUP_DIR"

command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump not found (install postgresql client tools)" >&2; exit 1; }

dsn="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/istari-$stamp.dump"

pg_dump --format=custom --no-owner --no-privileges --file="$out" "$dsn"
chmod 600 "$out"
echo "backup written: $out ($(du -h "$out" | cut -f1))"
