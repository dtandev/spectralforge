#!/usr/bin/env bash
# Export a full local copy of the live SpectralHub database using pg_dump.
#
# Run this LOCALLY, from a network that can actually reach the DB (VPN/office network).
# Uses pg_dump's custom format (-Fc): compact, compressed, handles BYTEA/arrays/PostGIS
# geometry natively — no custom (de)serialization code needed, unlike a hand-rolled
# JSON export. Read-only: never modifies the source database.
#
# Requires the PostgreSQL client tools (pg_dump) to be installed locally, e.g.:
#   brew install libpq && brew link --force libpq
#
# Usage:
#   cp .env-example .env   # fill in DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME for the LIVE db
#   ./scripts/export_live_db_snapshot.sh
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

mkdir -p db/snapshot
DUMP_FILE="db/snapshot/spectralhub.dump"

echo "Dumping ${DB_NAME}@${DB_HOST}:${DB_PORT} -> ${DUMP_FILE} ..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
  --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" --dbname="$DB_NAME" \
  --format=custom --no-owner --no-privileges \
  --file="$DUMP_FILE"

echo "Done: ${DUMP_FILE} ($(du -h "$DUMP_FILE" | cut -f1))"
echo "Next: just db-up && just db-import-snapshot"
