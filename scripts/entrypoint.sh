#!/bin/sh
# entrypoint.sh — container start: migrate, seed the shipped content packs,
# create the owner account once, then serve.
#
#   DATABASE_URL           required; asyncpg DSN
#   ISTARI_SEED_ON_START   "false" skips the pack import (default: import; it is
#                          idempotent, unchanged packs are no-ops)
#   ISTARI_OWNER_USERNAME  with ISTARI_OWNER_PASSWORD: create the owner when the
#   ISTARI_OWNER_PASSWORD  database has none yet; an existing owner is left alone
#   BIND_HOST / PORT       uvicorn bind address (image defaults: 0.0.0.0, 8000)
#
# Every step fails loudly: a migration or import error stops the container
# instead of serving a half-upgraded schema.
set -eu

alembic upgrade head

if [ "${ISTARI_SEED_ON_START:-true}" = "true" ]; then
  python -m app.cli seed
fi

if [ -n "${ISTARI_OWNER_USERNAME:-}" ] && [ -n "${ISTARI_OWNER_PASSWORD:-}" ]; then
  python -m app.cli bootstrap-owner --if-missing
fi

exec uvicorn app.main:app --host "${BIND_HOST:-0.0.0.0}" --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips='*'
