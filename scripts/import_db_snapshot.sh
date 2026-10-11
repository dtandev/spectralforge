#!/usr/bin/env bash
# Restore a db/snapshot/spectralhub.dump (produced by scripts/export_live_db_snapshot.sh)
# into a LOCAL Postgres+PostGIS instance — normally the one started by `just db-up`.
#
# Fully offline: never touches the live/production database. Safe to re-run (--clean
# --if-exists drops conflicting objects first).
#
# Requires the PostgreSQL client tools (pg_restore) to be installed locally, e.g.:
#   brew install libpq && brew link --force libpq
#
# Usage:
#   just db-up                                 # start the local dev DB
#   cp .env-example .env                       # point DB_* at localhost:5433 (see db/docker-compose.yml)
#   ./scripts/import_db_snapshot.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DB_USER:?Set DB_USER in .env}"
: "${DB_PASSWORD:?Set DB_PASSWORD in .env}"
: "${DB_HOST:?Set DB_HOST in .env}"
: "${DB_NAME:?Set DB_NAME in .env}"
DB_PORT="${DB_PORT:-5432}"

DUMP_FILE="db/snapshot/spectralhub.dump"
if [ ! -f "$DUMP_FILE" ]; then
  echo "No dump found at ${DUMP_FILE}. Run scripts/export_live_db_snapshot.sh first (from a machine with DB access)."
  exit 1
fi

echo "Restoring ${DUMP_FILE} -> ${DB_NAME}@${DB_HOST}:${DB_PORT} ..."
PGPASSWORD="$DB_PASSWORD" pg_restore \
  --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
  --clean --if-exists --no-owner --no-privileges \
  "$DUMP_FILE"

echo "Done. Local DB now mirrors the exported snapshot."
